#!/usr/bin/env bash
# Measure how this suite SCALES, on a box, before renting one to run it on (#865).
#
# WHY THIS EXISTS
# ---------------
# The `tests` job is ~2100 CPU-seconds and `--dist loadfile` cannot go below the single heaviest
# test FILE, so "how many cores are worth paying for" is decided by two numbers nobody has:
#
#   1. where the -n curve FLATTENS -- the point past which more workers buy nothing;
#   2. the true per-file floor -- estimated at ~80s from one sandbox timing, never measured properly.
#
# Guessing them wrong is a EUR 97/mo standing order in one direction and a slow CI in the other.
# A Hetzner CX43 bills at ~$0.03/h, so this whole question costs a few dollars to ANSWER instead.
#
# It also watches for the thing a shared-vCPU box fails at silently: Hetzner's shared plans are
# baseline-plus-burst with an undocumented throttle, and a throttled runner does not error, it just
# gets slower over days. So every run records CPU STEAL alongside wall time, and the sweep is
# repeated -- a rising steal fraction or a drifting wall across repeats is the signature, and it is
# the one result that says "do not put the permanent runner here" no matter how good pass 1 looked.
#
# Provisioning is deliberately the same shape the real runner needs, so none of this is throwaway.
#
# Usage, on a FRESH Ubuntu 24.04 box as root:
#     curl -fsSL <raw-url>/tools/ci-bench.sh -o ci-bench.sh && bash ci-bench.sh
#
#     WORKERS="2 4 8 16"   which -n values to sweep      (default: derived from nproc)
#     REPEATS=3            sweep passes, for drift       (default: 3)
#     PER_FILE=1           also time every file alone    (default: 1 -- slow, ~40 min, do it once)
#     REPO_URL=...         override the clone source
#     OUT=/root/ci-bench   results directory
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/4laric/er-archipelago.git}"
OUT="${OUT:-$HOME/ci-bench}"
WORK="${WORK:-$HOME/ci-bench-work}"
REPEATS="${REPEATS:-3}"
PER_FILE="${PER_FILE:-1}"

NPROC="$(nproc)"
if [ -z "${WORKERS:-}" ]; then
  WORKERS="2 4"
  [ "$NPROC" -ge 8 ]  && WORKERS="$WORKERS 8"
  [ "$NPROC" -ge 16 ] && WORKERS="$WORKERS 16"
  [ "$NPROC" -ge 32 ] && WORKERS="$WORKERS 32"
  # One past the core count on purpose: if -n (nproc*2) still improves, the box is not the ceiling
  # and the NEXT size up is worth pricing. If it regresses, we have found the flat spot honestly.
  WORKERS="$WORKERS $((NPROC * 2))"
fi

mkdir -p "$OUT"
say() { printf '\n=== %s\n' "$*"; }

# ------------------------------------------------------------------------------ 1. the box itself
say "box"
{
  echo "date=$(date -Is)"
  echo "nproc=$NPROC"
  echo "model=$(awk -F': ' '/model name/{print $2; exit}' /proc/cpuinfo)"
  echo "mem_gb=$(awk '/MemTotal/{printf "%.1f", $2/1048576}' /proc/meminfo)"
  echo "virt=$(systemd-detect-virt 2>/dev/null || echo unknown)"
} | tee "$OUT/box.txt"

# ------------------------------------------------------------------------------ 2. provisioning
if ! command -v git >/dev/null || ! command -v python3 >/dev/null; then
  say "installing packages"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq git curl python3 python3-venv python3-pip nodejs >/dev/null
fi
python3 --version

if [ ! -d "$WORK/repo/.git" ]; then
  say "cloning $REPO_URL"
  mkdir -p "$WORK"
  git clone --depth 50 "$REPO_URL" "$WORK/repo"
fi
cd "$WORK/repo"
# THE CLIENT, AT THE GITLINK. Only 3.5 MB, and without it the cross-side mirror suites SKIP -- a
# bench run that is missing 17 tests is measuring a different suite than CI runs.
git submodule update --init --depth 1 from-software-archipelago-clients >/dev/null 2>&1 || true
test -d from-software-archipelago-clients/crates \
  || echo "WARNING: no client checkout -- cross-side gates will SKIP and the timing is not CI's"

PIN="$(cat .ap-version)"
if [ ! -d "$WORK/ap/worlds" ]; then
  say "cloning upstream Archipelago $PIN"
  git clone --depth 1 --branch "$PIN" https://github.com/ArchipelagoMW/Archipelago.git "$WORK/ap"
fi

if [ ! -x "$WORK/venv/bin/python" ]; then
  say "venv + requirements"
  python3 -m venv "$WORK/venv"
  "$WORK/venv/bin/pip" install -q --upgrade pip
  "$WORK/venv/bin/pip" install -q "setuptools<80"
  "$WORK/venv/bin/pip" install -q -r "$WORK/ap/requirements.txt"
  "$WORK/venv/bin/pip" install -q pytest pytest-xdist
fi
PY="$WORK/venv/bin/python"

say "installing the world"
export SKIP_REQUIREMENTS_UPDATE=1 AP_NONINTERACTIVE=1
"$PY" tools/gen_inputs.py --ensure elden_ring_artifacts >/dev/null
"$PY" tools/gf_test.py --install-only --ap-dir "$WORK/ap" >/dev/null

COLLECTED="$(cd "$WORK/ap" && "$PY" -m pytest --co -q -p no:cacheprovider worlds/eldenring/tests 2>/dev/null | grep -c '::' || true)"
echo "collected=$COLLECTED" | tee -a "$OUT/box.txt"

# ------------------------------------------------------------------------------ 3. steal sampling
# /proc/stat's 8th field is `steal` -- time this vCPU was runnable but the hypervisor ran someone
# else. On dedicated hardware it stays 0. On a throttled shared vCPU it climbs, and it climbs
# BEFORE anyone notices the wall time, which is what makes it the useful instrument.
steal_now() { awk '/^cpu /{print $9+0; exit}' /proc/stat; }
total_now() { awk '/^cpu /{s=0; for(i=2;i<=11;i++) s+=$i; print s; exit}' /proc/stat; }

run_suite() {  # $1 = -n value ; echoes "wall_seconds steal_pct"
  local n="$1" s0 t0 s1 t1 start end
  s0="$(steal_now)"; t0="$(total_now)"; start="$(date +%s.%N)"
  ( cd "$WORK/ap" && "$PY" -m pytest -q -p no:cacheprovider -n "$n" --dist loadfile \
      worlds/eldenring/tests >"$OUT/run-n$n.log" 2>&1 ) || true
  end="$(date +%s.%N)"; s1="$(steal_now)"; t1="$(total_now)"
  awk -v a="$start" -v b="$end" -v s0="$s0" -v s1="$s1" -v t0="$t0" -v t1="$t1" \
    'BEGIN{d=t1-t0; printf "%.1f %.2f", b-a, (d>0? (s1-s0)*100.0/d : 0)}'
}

# ------------------------------------------------------------------------------ 4. the sweep
say "scaling sweep: -n over [$WORKERS], $REPEATS pass(es)"
echo "pass,workers,wall_seconds,steal_pct" > "$OUT/sweep.csv"
for pass in $(seq 1 "$REPEATS"); do
  for n in $WORKERS; do
    read -r wall steal <<<"$(run_suite "$n")"
    tail -1 "$OUT/run-n$n.log" | sed 's/^/    /'
    printf '%s,%s,%s,%s\n' "$pass" "$n" "$wall" "$steal" | tee -a "$OUT/sweep.csv"
  done
done

# ------------------------------------------------------------------------------ 5. the floor file
# Every file in its OWN process, serially. This is the number that caps every other number: under
# --dist loadfile the suite can never finish faster than its slowest single file, so it decides
# where the -n curve MUST flatten regardless of how many cores are bought.
if [ "$PER_FILE" = "1" ]; then
  say "per-file wall (serial, one process each) -- this is the slow part"
  echo "file,wall_seconds" > "$OUT/per_file.csv"
  ( cd "$WORK/ap" && ls worlds/eldenring/tests/test_*.py ) | while read -r f; do
    st="$(date +%s.%N)"
    ( cd "$WORK/ap" && "$PY" -m pytest -q -p no:cacheprovider "$f" >/dev/null 2>&1 ) || true
    en="$(date +%s.%N)"
    awk -v f="$f" -v a="$st" -v b="$en" 'BEGIN{printf "%s,%.1f\n", f, b-a}' >> "$OUT/per_file.csv"
  done
  sort -t, -k2 -rn "$OUT/per_file.csv" | head -25 > "$OUT/per_file_top25.csv"
fi

# ------------------------------------------------------------------------------ 6. the report
say "report"
"$PY" - "$OUT" <<'PYEOF'
import csv, os, statistics, sys
out = sys.argv[1]
rows = list(csv.DictReader(open(os.path.join(out, "sweep.csv"))))
by_n = {}
for r in rows:
    by_n.setdefault(int(r["workers"]), []).append((float(r["wall_seconds"]), float(r["steal_pct"])))

print("\n## Scaling\n")
print("| -n | best wall | median | steal% | speedup vs -n2 | marginal gain |")
print("|---:|---:|---:|---:|---:|---:|")
base = min(w for w, _ in by_n[min(by_n)])
prev = None
for n in sorted(by_n):
    walls = [w for w, _ in by_n[n]]
    steal = max(s for _, s in by_n[n])
    best = min(walls)
    gain = "-" if prev is None else "%.0f%%" % ((prev - best) / prev * 100)
    print("| %d | %.0fs | %.0fs | %.1f | %.2fx | %s |"
          % (n, best, statistics.median(walls), steal, base / best, gain))
    prev = best

print("\n## Drift across passes (the throttling tell)\n")
for n in sorted(by_n):
    walls = [w for w, _ in by_n[n]]
    if len(walls) > 1:
        spread = (max(walls) - min(walls)) / min(walls) * 100
        flag = "  <-- LOOK" if spread > 15 else ""
        print("  -n %-3d %s  spread %.0f%%%s"
              % (n, " ".join("%.0fs" % w for w in walls), spread, flag))
if any(s > 1 for n in by_n for _, s in by_n[n]):
    print("\n  🛑 non-zero CPU steal -- this box is sharing cores with someone. On a shared-vCPU")
    print("     plan that is expected; it is also the thing that makes a permanent runner here")
    print("     degrade quietly rather than fail. Weigh it before committing to a monthly box.")

pf = os.path.join(out, "per_file.csv")
if os.path.exists(pf):
    files = sorted(((float(r["wall_seconds"]), r["file"]) for r in csv.DictReader(open(pf))),
                   reverse=True)
    total = sum(w for w, _ in files)
    print("\n## The floor\n")
    print("  heaviest file : %s (%.0fs)" % (files[0][1].split("/")[-1], files[0][0]))
    print("  serial total  : %.0fs across %d files" % (total, len(files)))
    print("  => no -n can beat %.0fs, and the curve must flatten by about -n %d"
          % (files[0][0], max(1, round(total / files[0][0]))))
    print("\n  top 10:")
    for w, f in files[:10]:
        print("    %6.1fs  %s" % (w, f.split("/")[-1]))
print("\nraw: %s\n" % out)
PYEOF
