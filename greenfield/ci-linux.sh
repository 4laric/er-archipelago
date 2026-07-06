#!/usr/bin/env bash
# greenfield/ci-linux.sh -- Linux-native twin of the run_ci.ps1 GREENFIELD step.
#
# Runs the greenfield sub-gates natively under Python 3.11 (no Windows, no Cowork mount):
#   (a) DATA DRIFT   regen data.py + region_open_flags.py; fail if they differ (line-ending-
#                    normalized). SKIPS if elden_ring_artifacts/ is absent -- those grace anchors
#                    are licensing-restricted and NOT in git, so a fresh clone can't regenerate.
#                    data.py/region_open_flags.py are committed and still validated by GEN/WORLD.
#   (b) PURE UNIT    direct unittest on data.py invariants (no AP import)
#   (c) ISOLATED GEN install the world into the AP runtime + Generate.py a greenfield seed
#   (d) WORLD UNIT   WorldTestBase suite (fill/goal/slot_data) against the installed world
# Exits non-zero if any gate FAILS (SKIP does not fail). Auto-provisions the env if missing.
#
#   bash greenfield/ci-linux.sh
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GF="$HERE"; REPO="$(cd "$GF/.." && pwd)"
CACHE="${GF_CI_HOME:-$HOME/.greenfield-ci}"
VENV="$CACHE/.venv"; AP="$CACHE/ap"; PY="$VENV/bin/python"

if [ ! -x "$PY" ] || [ ! -d "$AP" ]; then
  echo "[ci-linux] env missing -> provisioning ..."
  bash "$GF/provision-linux-env.sh" || { echo "provision failed"; exit 2; }
fi

fail=0; declare -a RESULTS
step(){ printf '\n==== %s\n' "$1"; }
record(){ RESULTS+=("$1|$2"); [ "$2" = PASS ] || [ "$2" = SKIP ] || fail=1; }
nhash(){ [ -f "$1" ] && tr -d '\r' < "$1" | sha256sum | cut -d' ' -f1 || echo NONE; }

step "GREENFIELD (a) DATA DRIFT"
dataPy="$GF/eldenring_gf/data.py"; openPy="$GF/eldenring_gf/region_open_flags.py"
if [ ! -f "$REPO/elden_ring_artifacts/grace_flags.tsv" ]; then
  echo "  SKIP: elden_ring_artifacts/ absent (licensing-restricted, not in git). data.py +"
  echo "        region_open_flags.py are committed and validated by GEN/WORLD; run drift where"
  echo "        the grace anchors live (or set GF_ARTIFACTS out-of-band)."
  record DRIFT SKIP
else
  bossPy="$GF/eldenring_gf/boss_data.py"; gracePy="$GF/eldenring_gf/region_graces.py"; sweepPy="$GF/eldenring_gf/boss_sweeps.py"; shopPy="$GF/eldenring_gf/shop_data.py"; itemPy="$GF/eldenring_gf/item_ids.py"; tierPy="$GF/eldenring_gf/item_tiers.py"
  b1=$(nhash "$dataPy"); b2=$(nhash "$openPy"); b3=$(nhash "$bossPy"); b4=$(nhash "$gracePy"); b5=$(nhash "$sweepPy"); b6=$(nhash "$shopPy"); b7=$(nhash "$itemPy"); b8=$(nhash "$tierPy")
  if ( cd "$GF" && "$PY" gen_data.py ); then
    if [ "$b1" = "$(nhash "$dataPy")" ] && [ "$b2" = "$(nhash "$openPy")" ] && [ "$b3" = "$(nhash "$bossPy")" ] && [ "$b4" = "$(nhash "$gracePy")" ] && [ "$b5" = "$(nhash "$sweepPy")" ] && [ "$b6" = "$(nhash "$shopPy")" ] && [ "$b7" = "$(nhash "$itemPy")" ] && [ "$b8" = "$(nhash "$tierPy")" ]; then record DRIFT PASS
    else echo "  STALE: gen_data.py regenerated different data -- commit it."; record DRIFT FAIL; fi
  else record DRIFT FAIL; fi
fi

step "GREENFIELD (b) PURE UNIT"
if "$PY" "$GF/eldenring_gf/tests/test_gf_data.py"; then record PURE PASS; else record PURE FAIL; fi

step "GREENFIELD (c) ISOLATED GEN"
rm -rf "$AP/worlds/eldenring_gf"; cp -r "$GF/eldenring_gf" "$AP/worlds/eldenring_gf"
out="$CACHE/out"; rm -rf "$out"; mkdir -p "$out"
if ( cd "$AP" && AP_NONINTERACTIVE=1 SKIP_REQUIREMENTS_UPDATE=1 \
      "$PY" Generate.py --player_files_path "$GF/players" --outputpath "$out" ) \
   && ls "$out"/AP_*.zip >/dev/null 2>&1; then record GEN PASS; else record GEN FAIL; fi

step "GREENFIELD (d) WORLD UNIT"
if ( cd "$AP" && AP_NONINTERACTIVE=1 SKIP_REQUIREMENTS_UPDATE=1 \
      "$PY" -m pytest "worlds/eldenring_gf/tests/" -q -p no:cacheprovider \
        --ignore="worlds/eldenring_gf/tests/test_gf_data.py" ); then
  record WORLD PASS; else record WORLD FAIL; fi

step "GREENFIELD VERDICT"
for r in "${RESULTS[@]}"; do printf '  %-6s %s\n' "${r%%|*}" "${r##*|}"; done
if [ "$fail" -eq 0 ]; then echo "  GREENFIELD: PASS"; exit 0; else echo "  GREENFIELD: FAIL"; exit 1; fi
