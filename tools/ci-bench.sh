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
# Unconditional and idempotent. The first version of this gated on `command -v python3`, which is
# present on every Ubuntu image ever made -- so on a fresh CX43 the apt step never ran, and the
# failure surfaced much later as a missing ensurepip.
say "packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git curl ca-certificates tar >/dev/null

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
# 🛑🛑 INSIDE THE REPO, at .ap-test/ -- gf_test.py's own default, and not negotiable.
# The first version put this at $WORK/ap, one directory up. That is a documented trap: an --ap-dir
# OUTSIDE the repo makes the tools/ gates SKIP, and the first real run duly reported 395 skips
# against a committed census of 70. The suite still passed, still printed a confident wall time,
# and was quietly measuring ~2300 of CI's ~2600 tests -- a benchmark of a different workload than
# the one being sized for.
AP="$WORK/repo/.ap-test"
if [ ! -d "$AP/worlds" ]; then
  say "cloning upstream Archipelago $PIN -> .ap-test (inside the repo)"
  git clone --depth 1 --branch "$PIN" https://github.com/ArchipelagoMW/Archipelago.git "$AP"
fi

# 🛑🛑 CI RUNS PYTHON 3.12 (.github/workflows/tests.yaml pins it), SO THIS MUST TOO.
#
# The system interpreter is whatever the image ships -- Ubuntu 26.04 gives 3.14, and there is no
# python3.14-venv to install. Using it anyway would be worse than the error: a bench on a different
# interpreter is an answer to a different question, which is the exact failure this repo already
# has a name for (the dev box gating the apworld against a fork's Fill.py, 661 tests vs CI's 686).
# Interpreter version moves GC behaviour, dict/str internals and startup cost -- all of which this
# bench is measuring.
#
# So: a self-contained CPython 3.12 from python-build-standalone. No PPA, no ensurepip, no apt
# dependency on what the base image happens to package, and it carries its own pip.
PY_DIR="$WORK/py312"
if [ ! -x "$PY_DIR/python/bin/python3.12" ]; then
  say "fetching CPython 3.12 (python-build-standalone)"
  if [ -z "${PBS_URL:-}" ]; then
    # The download URL percent-encodes the `+` in the version, so match loosely and extract.
    PBS_URL="$(curl -fsSL https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest \
      | grep -oE '"browser_download_url": *"[^"]*cpython-3\.12\.[^"]*x86_64-unknown-linux-gnu-install_only_stripped\.tar\.gz"' \
      | head -1 | sed 's/.*"browser_download_url": *"//; s/"$//')"
  fi
  test -n "$PBS_URL" \
    || { echo "could not resolve a CPython 3.12 tarball (API rate limit?). Set PBS_URL=<url> and re-run."; exit 1; }
  echo "  $PBS_URL"
  mkdir -p "$PY_DIR"
  curl -fsSL "$PBS_URL" -o "$WORK/py312.tar.gz"
  tar -xzf "$WORK/py312.tar.gz" -C "$PY_DIR"
fi
PY="$PY_DIR/python/bin/python3.12"
# Assert rather than trust. A bench that silently ran on the wrong interpreter would still produce
# a confident table, and nothing downstream would question it.
"$PY" -c 'import sys; assert sys.version_info[:2] == (3, 12), sys.version' \
  || { echo "the interpreter at $PY is not 3.12 -- refusing to benchmark a different question"; exit 1; }
"$PY" -V

if [ ! -f "$WORK/.deps-installed" ]; then
  say "requirements (Archipelago $PIN)"
  "$PY" -m pip install -q --upgrade pip
  "$PY" -m pip install -q "setuptools<80"          # AP 0.6.x vs pkg_resources removal in >= 80
  "$PY" -m pip install -q -r "$AP/requirements.txt"
  "$PY" -m pip install -q pytest pytest-xdist
  touch "$WORK/.deps-installed"
fi

say "installing the world"
export SKIP_REQUIREMENTS_UPDATE=1 AP_NONINTERACTIVE=1
"$PY" tools/gen_inputs.py --ensure elden_ring_artifacts >/dev/null
"$PY" tools/gf_test.py --install-only --ap-dir "$AP" >/dev/null

COLLECTED="$(cd "$AP" && "$PY" -m pytest --co -q -p no:cacheprovider worlds/eldenring/tests 2>/dev/null | grep -c '::' || true)"
echo "collected=$COLLECTED" | tee -a "$OUT/box.txt"

# ------------------------------------------------------------------------------ 3. steal sampling
# /proc/stat's 8th field is `steal` -- time this vCPU was runnable but the hypervisor ran someone
# else. On dedicated hardware it stays 0. On a throttled shared vCPU it climbs, and it climbs
# BEFORE anyone notices the wall time, which is what makes it the useful instrument.
steal_now() { awk '/^cpu /{print $9+0; exit}' /proc/stat; }
total_now() { awk '/^cpu /{s=0; for(i=2;i<=11;i++) s+=$i; print s; exit}' /proc/stat; }

# cgroup CFS throttling, which is NOT the same thing as steal and does not show up in /proc/stat.
throttled_now() {
  if [ -r /sys/fs/cgroup/cpu.stat ]; then                       # cgroup v2
    awk '/^throttled_usec/{print $2; f=1} END{if(!f) print 0}' /sys/fs/cgroup/cpu.stat
  elif [ -r /sys/fs/cgroup/cpu/cpu.stat ]; then                 # cgroup v1 (usec -> from nsec)
    awk '/^throttled_time/{printf "%d", $2/1000; f=1} END{if(!f) print 0}' /sys/fs/cgroup/cpu/cpu.stat
  else
    echo 0
  fi
}

# ⭐ THE INSTRUMENT THAT ACTUALLY WORKS, and the lesson from run 1.
#
# On the first real box, steal read 0.00 on every run while wall time degraded 43% across three
# passes. Whether the accounting is not exposed to the guest or the cap sits somewhere steal cannot
# see, the counter said "clean" while the box was demonstrably not. So do not ask the platform how
# fast it is -- MEASURE IT, with fixed work, and compare the answer to itself over time.
#
# Two numbers, ten seconds:
#   single   -- fixed single-threaded work. Comparable ACROSS BOXES, so a CX43, a CCX33 and an AX42
#               can be ranked without re-running a 30-minute suite on each.
#   effective-- the same work on every core at once. (single * NPROC / allcore) is how many cores
#               the box will ACTUALLY give you under load. A dedicated 8-core answers ~8 (less SMT
#               losses); a shared vCPU plan capped near its baseline answers ~2-3, which is exactly
#               the shape that makes -n 8 lose to -n 4.
cpu_probe() {  # echoes "single_s allcore_s effective_cores"
  "$PY" - "$NPROC" <<'PYEOF'
import sys, time, multiprocessing as mp
N = int(sys.argv[1])
def work(_=None):
    x = 0
    for _i in range(20_000_000):   # ~1s of work: big enough that scheduler noise does not dominate
        x = (x * 1103515245 + 12345) & 0x7FFFFFFF
    return x
work()                                    # warm the interpreter, do not time it
t0 = time.perf_counter(); work(); single = time.perf_counter() - t0
t0 = time.perf_counter()
with mp.Pool(N) as pool:
    pool.map(work, range(N))
allc = time.perf_counter() - t0
print("%.3f %.3f %.2f" % (single, allc, (single * N / allc) if allc > 0 else 0))
PYEOF
}

run_suite() {  # $1 = -n value ; echoes "wall steal_pct throttled_s skipped"
  local n="$1" s0 t0 s1 t1 h0 h1 start end skipped
  s0="$(steal_now)"; t0="$(total_now)"; h0="$(throttled_now)"; start="$(date +%s.%N)"
  ( cd "$AP" && "$PY" -m pytest -q -p no:cacheprovider -n "$n" --dist loadfile \
      worlds/eldenring/tests >"$OUT/run-n$n.log" 2>&1 ) || true
  end="$(date +%s.%N)"; s1="$(steal_now)"; t1="$(total_now)"; h1="$(throttled_now)"
  skipped="$(grep -oE '[0-9]+ skipped' "$OUT/run-n$n.log" | head -1 | grep -oE '[0-9]+' || echo 0)"
  awk -v a="$start" -v b="$end" -v s0="$s0" -v s1="$s1" -v t0="$t0" -v t1="$t1" \
      -v h0="$h0" -v h1="$h1" -v sk="$skipped" \
    'BEGIN{d=t1-t0; printf "%.1f %.2f %.1f %s", b-a, (d>0? (s1-s0)*100.0/d : 0), (h1-h0)/1000000.0, sk}'
}

# ------------------------------------------------------------------------------ 4. the sweep
say "scaling sweep: -n over [$WORKERS], $REPEATS pass(es)"
echo "pass,workers,wall_seconds,steal_pct,throttled_s,skipped,probe_single_s,probe_effective_cores" \
  > "$OUT/sweep.csv"

# The layout check, ONCE, before anything is timed. `expected_skips_ci.json` is the committed
# inventory of what CI skips; if this box skips a wildly different number, the bench is measuring a
# different suite and every wall time below is an answer to a different question. Run 1 shipped 395
# against a census of 70 and nothing said a word.
CENSUS_TOTAL="$("$PY" -c 'import json;print(sum(f["count"] for f in json.load(open("greenfield/eldenring/tests/expected_skips_ci.json"))["families"]))' 2>/dev/null || echo 0)"
echo "  census expects $CENSUS_TOTAL skip(s)"

for pass in $(seq 1 "$REPEATS"); do
  for n in $WORKERS; do
    read -r psingle pall peff <<<"$(cpu_probe)"
    read -r wall steal thr skipped <<<"$(run_suite "$n")"
    tail -1 "$OUT/run-n$n.log" | sed 's/^/    /'
    if [ "$CENSUS_TOTAL" -gt 0 ] && [ "$skipped" -gt $((CENSUS_TOTAL * 2)) ]; then
      echo "  🛑 $skipped skips vs a census of $CENSUS_TOTAL -- this is NOT CI's suite; fix the"
      echo "     layout before quoting any number from this run."
    fi
    printf '%s,%s,%s,%s,%s,%s,%s,%s\n' \
      "$pass" "$n" "$wall" "$steal" "$thr" "$skipped" "$psingle" "$peff" | tee -a "$OUT/sweep.csv"
  done
done

# ------------------------------------------------------------------------------ 5. the floor file
# Every file in its OWN process, serially. This is the number that caps every other number: under
# --dist loadfile the suite can never finish faster than its slowest single file, so it decides
# where the -n curve MUST flatten regardless of how many cores are bought.
if [ "$PER_FILE" = "1" ]; then
  say "per-file wall (serial, one process each) -- this is the slow part"
  echo "file,wall_seconds" > "$OUT/per_file.csv"
  ( cd "$AP" && ls worlds/eldenring/tests/test_*.py ) | while read -r f; do
    st="$(date +%s.%N)"
    ( cd "$AP" && "$PY" -m pytest -q -p no:cacheprovider "$f" >/dev/null 2>&1 ) || true
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
print("| -n | best wall | median | steal% | throttled | speedup vs -n2 | marginal gain |")
print("|---:|---:|---:|---:|---:|---:|---:|")
base = min(w for w, _ in by_n[min(by_n)])
prev = None
regressed = []
for n in sorted(by_n):
    walls = [w for w, _ in by_n[n]]
    steal = max(s for _, s in by_n[n])
    thr = max(float(r["throttled_s"]) for r in rows if int(r["workers"]) == n)
    best = min(walls)
    gain = "-" if prev is None else "%.0f%%" % ((prev - best) / prev * 100)
    if prev is not None and best > prev:
        regressed.append(n)
    print("| %d | %.0fs | %.0fs | %.1f | %.0fs | %.2fx | %s |"
          % (n, best, statistics.median(walls), steal, thr, base / best, gain))
    prev = best

# The CPU probe is the honest per-core number, and the one comparable between boxes.
probes = [(float(r["probe_single_s"]), float(r["probe_effective_cores"])) for r in rows
          if r.get("probe_single_s")]
if probes:
    singles = [p for p, _ in probes]
    effs = [e for _, e in probes]
    import os as _os
    print("\n## What this box really gives you\n")
    print("  fixed single-core work : %.2fs best, %.2fs worst  (lower is faster; compare BOXES with this)"
          % (min(singles), max(singles)))
    print("  effective cores        : %.1f best, %.1f worst  of %s advertised"
          % (max(effs), min(effs), _os.cpu_count()))
    if max(effs) < _os.cpu_count() * 0.6:
        print("  🛑 the box delivers well under its advertised core count under load. That is a CAP,")
        print("     not a scaling limit of the suite -- do not read the -n curve below as a fact")
        print("     about the test suite.")
    if max(singles) > min(singles) * 1.25:
        print("  🛑 single-core speed MOVED between runs by %.0f%% -- the box is not a stable ruler."
              % ((max(singles) / min(singles) - 1) * 100))

if regressed:
    print("\n  NOTE: -n %s was SLOWER than the step below it. More workers than real cores means"
          % ", ".join(str(n) for n in regressed))
    print("  contention, not parallelism; read it with the effective-core number above.")

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
