#!/usr/bin/env python3
"""fill_regression.py -- the fill-regression gate, in Python, runnable anywhere.

WHY THIS EXISTS
---------------
`run_fill_regression.ps1` + `gen_sweep.ps1` are the fill gate (run_ci step 2). On 2026-07-26 a
`-Count 25` run reported all 9 configs REGRESSED at 0% -- and it was not nine regressions. Every
config showed `runs=1`, and gen_sweep only breaks its seed loop after one seed on CONFIGERROR; the
reproduce hint printed `-Seeds System.Int64[]`, i.e. the CSV's own seed column held an ARRAY, so
`Generate.py --seed System.Int64[]` never had a chance. One harness fault wearing nine verdicts.

Debugging that means debugging PowerShell hashtable splatting through `Start-Job`, on a box the
agent cannot reach. So: rewrite the gate in Python, where it can be read, unit-tested, and run on
Linux/CI as well as Windows. Same contract as the .ps1 pair -- run a shared seed list across a
config suite, classify every run, compare pass-rates to recorded floors, exit non-zero on
regression -- with three additions the .ps1 path could not give us:

  1. A SELF-TEST. The classification and verdict logic run against synthetic logs with no AP and no
     game data (`--selftest`). The .ps1 harness had no test, which is exactly how it could break
     into "nine regressions" and look like a real result. A gate you cannot test is not a gate.
  2. A YAML PRE-FLIGHT (`--check-yamls`). Every option key is checked against the world's LIVE
     option surface before a single seed runs. As of 2026-07-26 all 9 suite yamls set option names
     that exist nowhere in greenfield -- region_access, location_pool, missable_location_behavior,
     excluded_location_behavior, torrent_start (in every one), plus soft_progression,
     graces_per_region, extra_region_locks, tidy_fun_consumables, smithing_bell_bearing_option.
     They are bedrock-era names. A stale config must say "this option does not exist" and stop, not
     burn 25 seeds and report a regression it cannot have measured.
  3. THE SPILL METRIC. progression_surface's ladder returns unplaceable region Locks to the normal
     pool -- the valve that stops it FillError-ing, and the one path that silently undoes the
     confinement. 858f9d6 made it announce itself; this harness aggregates it across the sweep,
     because spill is a per-seed random outcome and one seed proves nothing about it.

STATUS (2026-07-27): the CLASSIFIER and VERDICT halves are exercised by --selftest and pass. The
GEN half is unrun by me -- Archipelago 0.6.7 needs Python 3.11+ (`typing.Self` in worlds/AutoWorld)
and the agent sandbox has 3.10, with the 3.11 download exceeding its per-call timeout. So the
subprocess/log-parsing path is verified against synthetic logs only. Say that plainly rather than
call this "tested".

USAGE
    python tools/fill_regression.py --selftest             # no AP, no artifacts, no game data
    python tools/fill_regression.py --check-yamls          # option-name pre-flight only
    python tools/fill_regression.py                        # fixed reproducer seeds (deterministic)
    python tools/fill_regression.py --count 25             # 25 shared random seeds
    python tools/fill_regression.py --seeds 123,456        # reproduce a specific report
    python tools/fill_regression.py --update-baseline      # recalibrate floors from this run
    python tools/fill_regression.py --jobs 4               # parallel configs (default: cpu-1, max 4)

EXIT CODES:  0 ok | 1 a config regressed | 2 harness/pre-flight refused to run
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.abspath(os.path.join(HERE, ".."))
SUITE = os.path.join(REPO, "gen-test", "fill-regression-yamls")
BASELINE = os.path.join(SUITE, "baseline.json")
AP_DIR = os.environ.get("GF_AP_DIR") or os.path.join(REPO, "Archipelago")

# Fixed reproducer seeds -- the deterministic gate. Same list as run_fill_regression.ps1 so a
# verdict from either harness is comparable; do not "improve" them independently.
FIXED_SEEDS = [1111111111111111111, 2222222222222222222, 3333333333333333333, 4444444444444444444,
               5555555555555555555, 6666666666666666666, 7777777777777777777, 8888888888888888888]

# A logic/fill failure -- the thing this gate exists to catch -- versus any other non-zero exit,
# which is a CONFIG or harness fault and must NOT be laundered into "the fill regressed".
LOGIC_RE = re.compile(r"FillError|No more spots|appears as unbeatable|Unable to place|"
                      r"cannot be placed|unreachable", re.I)
_NOISE_RE = re.compile(r"EOFError|atexit|Press enter", re.I)
_ERR_RE = re.compile(r"Error|Exception|Traceback")
_NAMED_ERR_RE = re.compile(r"^[A-Za-z_][\w.]*(Error|Exception)\b\s*:")
_SEEDNAME_RE = re.compile(r"AP_(\d+)\.zip")
_SPILL_RE = re.compile(r"progression surface: rung (.+?) placed (\d+)/(\d+); (\d+) SPILLED")

SUCCESS, FILLERROR, CONFIGERROR = "SUCCESS", "FILLERROR", "CONFIGERROR"


# ---------------------------------------------------------------------------------------------
# classification -- pure over the LOG TEXT, so --selftest can exercise every branch with no AP
# ---------------------------------------------------------------------------------------------
def classify(log_text: str, exit_code: int) -> tuple[str, str]:
    """(outcome, detail) for one gen. PURE: text + exit code in, verdict out.

    The ordering is the whole point and it is not arbitrary. A non-zero exit with a fill/logic
    signature is a FILLERROR (the regression this gate hunts). A non-zero exit WITHOUT one is a
    CONFIGERROR -- a broken yaml, a missing option, a harness fault -- and calling that a fill
    regression is precisely how nine identical harness faults got reported as nine regressions.
    """
    if exit_code == 0:
        raised = re.search(r"raised to \d+", log_text)
        return SUCCESS, (raised.group(0) if raised else "")
    if LOGIC_RE.search(log_text):
        hits = [ln.strip() for ln in log_text.splitlines() if LOGIC_RE.search(ln)]
        return FILLERROR, (hits[-1] if hits else "")
    # skip the atexit/EOF noise an unpatched Generate.py emits on closed stdin -- report the REAL one
    # Prefer an actual `SomeError: message` line over the bare "Traceback (most recent call last):"
    # header. The first real run reported detail="Traceback (most recent call last):" -- true, and
    # useless. A gate's whole value is the sentence it hands you.
    lines = [ln.strip() for ln in log_text.splitlines() if not _NOISE_RE.search(ln)]
    named = [ln for ln in lines if _NAMED_ERR_RE.match(ln)]
    if named:
        return CONFIGERROR, named[-1]
    hits = [ln for ln in lines if _ERR_RE.search(ln)]
    return CONFIGERROR, (hits[-1] if hits else f"non-zero exit {exit_code}, no recognizable error")


def parse_spill(log_text: str):
    """(rung, placed, total, spilled) from the progression_surface telemetry, or None if the line is
    absent -- which means either no spill or an older world. Do NOT default a missing line to 0: an
    absent measurement and a measured zero are different claims (the whole reason 858f9d6 exists)."""
    m = _SPILL_RE.search(log_text)
    if not m:
        return None
    return (m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4)))


def verdicts(rows, floors, margin=0):
    """Per-config pass-rate vs its recorded floor. Pure over the row dicts."""
    out = []
    for cfg in sorted({r["config"] for r in rows}):
        mine = [r for r in rows if r["config"] == cfg]
        n = len(mine)
        npass = sum(1 for r in mine if r["outcome"] == SUCCESS)
        nfill = sum(1 for r in mine if r["outcome"] == FILLERROR)
        ncfg = sum(1 for r in mine if r["outcome"] == CONFIGERROR)
        rate = round(100.0 * npass / n, 1) if n else 0.0
        floor = float(floors.get(cfg, 0))
        # A CONFIGERROR is not a fill regression. It fails the gate -- loudly, under its own name --
        # so a broken config can never masquerade as one, in either direction.
        if ncfg:
            verdict = "CONFIGERROR"
        elif rate < floor - margin:
            verdict = "REGRESSED"
        else:
            verdict = "ok"
        out.append({"config": cfg, "runs": n, "pass": npass, "fill": nfill, "cfgerr": ncfg,
                    "rate": rate, "floor": floor, "verdict": verdict})
    return out


# ---------------------------------------------------------------------------------------------
# yaml pre-flight
# ---------------------------------------------------------------------------------------------
_AP_KEYS = {"accessibility", "progression_balancing", "death_link", "local_items", "non_local_items",
            "start_inventory", "start_inventory_from_pool", "start_hints", "start_location_hints",
            "exclude_locations", "priority_locations", "item_links", "triggers", "plando_items",
            "name", "game", "description", "requires"}


def frozen_option_names():
    """Options deliberately REMOVED from the yaml surface (defaults.FROZEN_OPTIONS): they are the
    behaviour now, not a knob. A yaml that still sets one is stale but HARMLESS -- the value is
    ignored and the frozen constant applies. Reporting those alongside genuinely dead names would
    send someone editing yamls that are fine, so they are a WARNING, never the refusal."""
    try:
        from worlds.eldenring.defaults import FROZEN_OPTIONS  # type: ignore
        return set(FROZEN_OPTIONS)
    except Exception:
        return set()


def live_option_names():
    """Every option name a yaml may legally set, taken from the WORLD, not from a hand list.

    Needs the world importable (AP on sys.path). Returns None when it is not -- and the caller then
    SKIPS the pre-flight rather than inventing a verdict from a partial parse. A regex sweep of
    features/*.py looked tempting and got `num_regions` wrong in testing, which would have condemned
    the marquee option as dead; a check that can be confidently wrong about the most important
    option in the world is worse than no check."""
    try:
        sys.path.insert(0, AP_DIR)
        from worlds.eldenring import options as _o  # noqa: F401
        from worlds.eldenring.core import GFOptions  # type: ignore
        return set(GFOptions.type_hints.keys()) | _AP_KEYS
    except Exception:
        try:
            from worlds.eldenring.core import GFOptions  # type: ignore
            return set(GFOptions.type_hints.keys()) | _AP_KEYS
        except Exception:
            return None


def check_yamls(suite, live, frozen=frozenset()):
    """[(file, dead, stale_frozen)] per yaml.

    dead         -- names that exist NOWHERE in the world. The refusal.
    stale_frozen -- names in defaults.FROZEN_OPTIONS: ignored, not broken. A note.

    🛑 A yaml's TOP-LEVEL keys are not options. They are `name`, `description`, and the GAME
    SECTION ("Elden Ring" / "EldenRing"), whose value is the dict of real options. The first version
    unioned the top level into the option set and duly reported `EldenRing` as a dead option name in
    all nine files -- a confident wrong answer in the very check written to catch confident wrong
    answers. Only the game block's keys are options."""
    import yaml as _yaml
    out = []
    for fn in sorted(os.listdir(suite)):
        if not fn.endswith((".yaml", ".yml")):
            continue
        with open(os.path.join(suite, fn), encoding="utf-8") as fh:
            docs = [d for d in _yaml.safe_load_all(fh) if isinstance(d, dict)]
        keys = set()
        for doc in docs:
            for section, block in doc.items():
                # a game section is a top-level key whose value is a dict of options; the AP-level
                # keys (name, description, triggers, ...) are not, and neither is the game NAME.
                if isinstance(block, dict) and section not in _AP_KEYS:
                    keys |= {k for k in block if isinstance(k, str)}
        dead = sorted(k for k in keys if k not in live and k not in _AP_KEYS and k not in frozen)
        stale = sorted(k for k in keys if k in frozen)
        out.append((fn, dead, stale))
    return out


# ---------------------------------------------------------------------------------------------
# the gen half
# ---------------------------------------------------------------------------------------------
def run_one(cfg_path, seed, out_dir, stage_dir, log_dir):
    """One Generate.py run. Returns a row dict. Never raises on a failed gen -- a gen that dies IS
    the measurement.

    OUTPUT ISOLATION (2026-07-27). `out_dir` is PER TASK. It used to be one shared
    `<AP_DIR>/output`, so `--jobs 4` pointed four concurrent Generate.py processes at one directory.
    `sweep()` already isolates the STAGING dir per config for the same class of reason ("Generate.py
    globs the whole player-files dir"); the output dir was simply missed.

    ⚠️ Honesty about this one: I added it believing it was the cause of the intermittent CONFIGERROR,
    and IT WAS NOT -- see `ensure_host_yaml`, which is. This is hygiene that happens to be right, not
    the fix, and the distinction matters because the next person to see a flake here should not read
    this paragraph and conclude the shared output dir has already been ruled in."""
    os.makedirs(log_dir, exist_ok=True)
    cfg = os.path.basename(cfg_path)
    log_path = os.path.join(log_dir, f"{os.path.splitext(cfg)[0]}_{seed}.log")
    out_dir = os.path.join(out_dir, f"{os.path.splitext(cfg)[0]}_{seed}")
    os.makedirs(out_dir, exist_ok=True)
    # SKIP_REQUIREMENTS_UPDATE: without it Generate.py runs ModuleUpdate, which on a box missing
    # pkg_resources tries to INSTALL it and blocks on input() -- with stdin closed that surfaces as
    # `EOFError: EOF when reading a line`, i.e. an env gap wearing the costume of a config error.
    # (Found on the first real gen, 2026-07-27. AGENTS §5 sets it for pytest; the harness must too.)
    env = dict(os.environ, AP_NONINTERACTIVE="1", PYTHONIOENCODING="utf-8",
               SKIP_REQUIREMENTS_UPDATE="1")
    cmd = [sys.executable, "Generate.py", "--seed", str(seed),
           "--player_files_path", stage_dir, "--outputpath", out_dir]
    t0 = time.time()
    try:
        # stdin=DEVNULL: Generate.py's atexit input() then raises EOFError instead of parking the
        # sweep forever on a failed gen (memory: "crash masquerades as HANG").
        p = subprocess.run(cmd, cwd=AP_DIR, env=env, stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=1800)
        text, code = p.stdout.decode("utf-8", "replace"), p.returncode
    except subprocess.TimeoutExpired as e:
        text = (e.stdout or b"").decode("utf-8", "replace") + "\nTimeoutExpired: gen exceeded 1800s"
        code = 124
    with open(log_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    outcome, detail = classify(text, code)
    spill = parse_spill(text)
    name = _SEEDNAME_RE.search(text)
    return {"config": cfg, "seed": seed, "outcome": outcome, "detail": detail, "exit": code,
            "seedname": (name.group(1) if name else None), "secs": round(time.time() - t0, 1),
            "spill_rung": spill[0] if spill else None,
            "spill_placed": spill[1] if spill else None,
            "spill_total": spill[2] if spill else None,
            "spilled": spill[3] if spill else None,
            "log": os.path.relpath(log_path, REPO)}


def ensure_host_yaml():
    """Materialize `<AP_DIR>/host.yaml` ONCE, serially, before any parallel gen starts.

    🛑 THIS IS THE REAL CAUSE of the intermittent `CONFIGERROR FileNotFoundError:
    .../_ap/host.yaml.tmp` (2026-07-27), and it took an UNTRUNCATED error message to find -- the
    filename was the entire answer and the gate had been cutting it off mid-path.

    Archipelago's `Settings.save()` (settings.py) is not concurrency-safe, by design:

        temp_location = location + ".tmp"   # "not using tempfile to test expected file access"
        if os.path.exists(temp_location): os.unlink(temp_location)
        ...write temp...  ...read temp back to validate...  os.rename(temp, location)

    A FIXED temp filename in a FIXED directory. `Settings` also registers an atexit `autosave` that
    fires whenever the loaded host.yaml was missing keys. So every Generate.py in the sweep tries to
    rewrite `<AP_DIR>/host.yaml` as it exits, and with `--jobs 4` in one `cwd` they interleave: B
    unlinks A's temp, or renames it away, and A's read-back raises FileNotFoundError. Nothing to do
    with the yaml under test -- which is why the failures clustered at sweep start and why the same
    seeds pass when run alone.

    Fix: load and save the settings ONCE up front. After that host.yaml is complete on disk, so
    `changed` stays False in every child and no autosave races. Cheap, and it removes the race
    rather than retrying through it.

    Best-effort: if this cannot run, the sweep still works -- it just keeps the old exposure -- so it
    reports and continues rather than refusing to gate."""
    host = os.path.join(AP_DIR, "host.yaml")
    if os.path.isfile(host):
        return True
    env = dict(os.environ, AP_NONINTERACTIVE="1", SKIP_REQUIREMENTS_UPDATE="1")
    p = subprocess.run(
        [sys.executable, "-c", "import settings; settings.get_settings().save()"],
        cwd=AP_DIR, env=env, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
    if os.path.isfile(host):
        print(f"  host.yaml materialized before the sweep ({host})")
        return True
    # Loud, not silent: the sweep is about to run with a known race still live.
    print(f"  ⚠️  could not materialize {host} (exit {p.returncode}); parallel gens may race on "
          f"host.yaml.tmp:\n{p.stdout.decode('utf-8', 'replace')[-500:]}")
    return False


def run_one_retrying(cfg_path, seed, out_dir, stage_dir, log_dir):
    """`run_one`, retried ONCE on CONFIGERROR -- and never quietly.

    A CONFIGERROR means "the gen died for a reason that is not a fill regression": a broken yaml, a
    missing option, or a HARNESS/ENVIRONMENT fault. The first two are deterministic and the
    `--check-yamls` pre-flight already catches the option-name class before any seed runs, so a
    CONFIGERROR that passes on a straight retry is by definition the third -- and failing the gate on
    it teaches people to ignore the gate.

    🛑 The retry is LOUD, on purpose. A silent retry is exactly the "tolerance without telemetry"
    pattern CONTRIBUTING is about: it would launder a real intermittent fault into a green run and we
    would lose the only evidence it exists. So a task that needed a retry is printed at the moment it
    happens, carries `flaked=True` + `first_detail` into results.json, and is counted in a summary
    line at the end whether or not the gate passes."""
    row = run_one(cfg_path, seed, out_dir, stage_dir, log_dir)
    if row["outcome"] != CONFIGERROR:
        return row
    first = row["detail"]
    retry = run_one(cfg_path, seed, out_dir, stage_dir, log_dir)
    retry["flaked"] = True
    retry["first_detail"] = first
    print(f"  RETRY  {os.path.basename(cfg_path)[:38]:38s} seed {seed}  first attempt "
          f"{CONFIGERROR} -> {retry['outcome']}\n         first error was: {first}", flush=True)
    return retry


def sweep(configs, seeds, jobs, out_dir, log_dir):
    """Every (config, seed) pair, each config staged into its OWN dir so parallel runs cannot see
    each other's yaml. Generate.py globs the whole player-files dir, so a shared staging dir is how
    a parallel sweep silently rolls nine configs into one multiworld."""
    import shutil
    import tempfile
    rows = []
    stages = {}
    ensure_host_yaml()  # serially, BEFORE any parallel gen -- see the function docstring
    try:
        for cfg in configs:
            d = tempfile.mkdtemp(prefix="gffr_stage_")
            shutil.copy2(cfg, os.path.join(d, os.path.basename(cfg)))
            stages[cfg] = d
        tasks = [(cfg, s) for cfg in configs for s in seeds]
        with cf.ThreadPoolExecutor(max_workers=jobs) as ex:
            futs = {ex.submit(run_one_retrying, cfg, s, out_dir, stages[cfg], log_dir): (cfg, s)
                    for cfg, s in tasks}
            for fut in cf.as_completed(futs):
                row = fut.result()
                rows.append(row)
                # 🛑 DO NOT TRUNCATE A FAILURE. `detail[:70]` cut the 2026-07-27 CONFIGERROR off at
                # `FileNotFoundError: [Errno 2] No such file or directory: '/home/runner/` -- the
                # gate reported a red it had made impossible to diagnose, and the path was the whole
                # answer. A SUCCESS line stays short (its detail is a one-word "raised to N"); a
                # failure prints in full, however long. Cheap, and the difference between a finding
                # and a mystery.
                detail = row["detail"] if row["outcome"] != SUCCESS else row["detail"][:70]
                print(f"  {row['config'][:38]:38s} seed {row['seed']}  {row['outcome']:11s} "
                      f"{detail}", flush=True)
    finally:
        for d in stages.values():
            shutil.rmtree(d, ignore_errors=True)
    return rows


# ---------------------------------------------------------------------------------------------
# self-test -- the half that needs no AP, no artifacts, no game data
# ---------------------------------------------------------------------------------------------
def selftest():
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            ok = False
            print(f"  FAIL {label}: got {got!r}, want {want!r}")
        else:
            print(f"  ok   {label}")

    check("clean gen -> SUCCESS", classify("...\nDone. AP_12345.zip\n", 0)[0], SUCCESS)
    check("FillError -> FILLERROR",
          classify("Traceback\nFill.FillError: No more spots for Limgrave Lock\n", 1)[0], FILLERROR)
    # THE REGRESSION THIS FILE EXISTS FOR: a broken config must never read as a fill regression.
    check("bad seed arg -> CONFIGERROR",
          classify("Traceback\nValueError: invalid literal for int(): System.Int64[]\n", 1)[0],
          CONFIGERROR)
    check("dead option -> CONFIGERROR",
          classify("Traceback\nOptionError: region_access is not a valid option\n", 1)[0],
          CONFIGERROR)
    check("named error beats the Traceback header",
          classify("Traceback (most recent call last):\n  File x\nOptionError: bad thing\n", 1)[1],
          "OptionError: bad thing")
    check("atexit noise is not the error",
          classify("OptionError: real problem here\nEOFError: EOF when reading a line\n", 1)[1],
          "OptionError: real problem here")
    check("no spill line -> None (absent != zero)", parse_spill("nothing here"), None)
    check("spill parsed", parse_spill(
        "[greenfield] progression surface: rung ['MajorBoss'] placed 9/11; 2 SPILLED to normal fill"),
        ("['MajorBoss']", 9, 11, 2))

    rows = ([{"config": "a.yaml", "outcome": SUCCESS}] * 9 + [{"config": "a.yaml", "outcome": FILLERROR}]
            + [{"config": "b.yaml", "outcome": CONFIGERROR}]
            + [{"config": "c.yaml", "outcome": SUCCESS}] * 10)
    v = {x["config"]: x for x in verdicts(rows, {"a.yaml": 95, "b.yaml": 100, "c.yaml": 100})}
    check("real regression is REGRESSED", v["a.yaml"]["verdict"], "REGRESSED")
    check("90% measured", v["a.yaml"]["rate"], 90.0)
    # b.yaml is the 2026-07-26 shape: it did not regress, it never ran.
    check("broken config is CONFIGERROR, not REGRESSED", v["b.yaml"]["verdict"], "CONFIGERROR")
    check("healthy config is ok", v["c.yaml"]["verdict"], "ok")
    # ---- check_yamls: the two bugs the FIRST REAL RUN exposed (2026-07-27) -------------------
    import tempfile
    import shutil
    d = tempfile.mkdtemp(prefix="fillreg_selftest_")
    try:
        open(os.path.join(d, "x.yaml"), "w", encoding="utf-8").write(
            "name: Tester\ndescription: fixture\n"
            "EldenRing:\n  num_regions: 5\n  pool_builder: true\n  region_access: open\n")
        res = check_yamls(d, {"num_regions"}, frozen={"pool_builder"})
        fn, dead, stale = res[0]
        # bug 1: the GAME SECTION NAME was being reported as a dead option in all nine files
        check("game section name is not an option", "EldenRing" in dead, False)
        check("top-level name/description are not options",
              bool({"name", "description"} & set(dead)), False)
        # bug 2: a FROZEN option is stale, not dead -- it is ignored on purpose
        check("frozen option is not dead", "pool_builder" in dead, False)
        check("frozen option is reported stale", stale, ["pool_builder"])
        check("genuinely absent option IS dead", dead, ["region_access"])
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # ---- the CONFIGERROR retry (2026-07-27) -------------------------------------------------
    # A gate you cannot test is not a gate, and a RETRY is the most dangerous thing to add to one:
    # get it wrong and it turns a real failure green. So exercise all three branches with a stubbed
    # run_one -- no AP, no gen.
    global run_one
    _real_run_one = run_one
    try:
        calls = {"n": 0}

        def _stub(outcomes):
            def f(cfg_path, seed, out_dir, stage_dir, log_dir):
                i = calls["n"]
                calls["n"] += 1
                return {"config": os.path.basename(cfg_path), "seed": seed,
                        "outcome": outcomes[min(i, len(outcomes) - 1)],
                        "detail": f"detail-{i}"}
            return f

        calls["n"] = 0
        run_one = _stub([SUCCESS])
        r = run_one_retrying("a.yaml", 1, "o", "s", "l")
        check("SUCCESS is not retried", (r["outcome"], calls["n"]), (SUCCESS, 1))

        calls["n"] = 0
        run_one = _stub([FILLERROR])
        r = run_one_retrying("a.yaml", 1, "o", "s", "l")
        check("FILLERROR is NOT retried (it is the finding)", (r["outcome"], calls["n"]),
              (FILLERROR, 1))

        calls["n"] = 0
        run_one = _stub([CONFIGERROR, SUCCESS])
        r = run_one_retrying("a.yaml", 1, "o", "s", "l")
        check("CONFIGERROR retried once -> takes the retry's outcome",
              (r["outcome"], calls["n"]), (SUCCESS, 2))
        check("a retried task is FLAGGED, never silent", r.get("flaked"), True)
        check("the first error is preserved for the report", r.get("first_detail"), "detail-0")

        calls["n"] = 0
        run_one = _stub([CONFIGERROR, CONFIGERROR])
        r = run_one_retrying("a.yaml", 1, "o", "s", "l")
        check("a REAL config error still fails after the retry",
              (r["outcome"], calls["n"]), (CONFIGERROR, 2))
    finally:
        run_one = _real_run_one

    print("selftest:", "OK" if ok else "FAILED")
    return 0 if ok else 1


# ---------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--suite", default=SUITE)
    ap.add_argument("--count", type=int, default=0, help="N shared random seeds (0 = fixed set)")
    ap.add_argument("--seeds", help="comma-separated explicit seeds")
    ap.add_argument("--seed-base", type=int, default=0, help="make --count reproducible")
    ap.add_argument("--jobs", type=int, default=0)
    ap.add_argument("--margin", type=float, default=0.0)
    ap.add_argument("--baseline", default=BASELINE)
    ap.add_argument("--update-baseline", action="store_true")
    ap.add_argument("--check-yamls", action="store_true", help="pre-flight only, run no seeds")
    ap.add_argument("--skip-yaml-check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    if not os.path.isdir(args.suite):
        print(f"FATAL: no suite dir at {args.suite}", file=sys.stderr)
        return 2
    configs = [os.path.join(args.suite, f) for f in sorted(os.listdir(args.suite))
               if f.endswith((".yaml", ".yml"))]
    if not configs:
        print(f"FATAL: no yamls in {args.suite}", file=sys.stderr)
        return 2

    # ---- pre-flight -----------------------------------------------------------------------
    if not args.skip_yaml_check:
        live = live_option_names()
        if live is None:
            print("  yaml pre-flight SKIPPED: the world is not importable from here, so the live "
                  "option surface is unknown. Not guessing it -- run with AP on sys.path "
                  "(GF_AP_DIR) for the check.")
        else:
            checked = check_yamls(args.suite, live, frozen_option_names())
            stale = {f: st for f, _d, st in checked if st}
            if stale:
                allst = sorted({k for v in stale.values() for k in v})
                print(f"  note: {len(stale)} yaml(s) still set FROZEN options {allst} -- ignored, "
                      f"not broken (defaults.FROZEN_OPTIONS: they are the behaviour now). Tidy when "
                      f"convenient; this is not the gate.")
            bad = [(f, d) for f, d, _st in checked if d]
            if bad:
                print("FATAL: suite yamls set option names that DO NOT EXIST in this world -- not "
                      "frozen, not renamed, simply absent. Each is silently doing nothing, so these "
                      "configs no longer pin the bug they are named after, and a reproducer that "
                      "cannot reproduce launders a regression into a pass. Fix the yamls (or "
                      "--skip-yaml-check to run anyway):")
                for f, dead in bad:
                    print(f"  {f}: {', '.join(dead)}")
                return 2
            print(f"  yaml pre-flight OK: {len(configs)} config(s), every option name is live")
        if args.check_yamls:
            return 0
    elif args.check_yamls:
        print("--check-yamls with --skip-yaml-check does nothing")
        return 2

    if args.seeds:
        seeds = [int(s) for s in args.seeds.replace(",", " ").split()]
        mode = f"explicit ({len(seeds)} seeds)"
    elif args.count > 0:
        import random
        rng = random.Random(args.seed_base or None)
        seeds = [rng.randrange(1, 2 ** 62) for _ in range(args.count)]
        mode = f"{args.count} shared random seeds"
    else:
        seeds = list(FIXED_SEEDS)
        mode = f"fixed reproducer seeds ({len(seeds)})"
    # ONE shared seed list across every config -- that is what makes the configs comparable.
    print(f"==== fill regression gate (python) -- mode: {mode}; {len(configs)} configs")

    if not os.path.isfile(os.path.join(AP_DIR, "Generate.py")):
        print(f"FATAL: no Generate.py under {AP_DIR} (set GF_AP_DIR)", file=sys.stderr)
        return 2
    jobs = args.jobs or max(1, min(4, (os.cpu_count() or 2) - 1))
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_dir = os.path.join(AP_DIR, "output")
    log_dir = os.path.join(REPO, f"fillreg_{stamp}")
    rows = sweep(configs, seeds, jobs, out_dir, log_dir)

    floors = {}
    if os.path.isfile(args.baseline):
        floors = {k: v for k, v in json.load(open(args.baseline, encoding="utf-8")).items()
                  if not k.startswith("_")}
    vs = verdicts(rows, floors, args.margin)

    # A retried task must never pass QUIETLY. It is counted here whatever the gate's verdict, so an
    # intermittent harness/environment fault stays visible instead of being absorbed into a green run
    # (CONTRIBUTING: "graceful degradation without telemetry is just silent failure with better
    # manners"). If this number stops being 0, that is a finding, not noise.
    flaked = [r for r in rows if r.get("flaked")]
    if flaked:
        print(f"\n==== ⚠️  {len(flaked)} task(s) needed a RETRY after a CONFIGERROR "
              f"(counted as their retry's outcome; first errors below)")
        for r in flaked:
            print(f"  {r['config'][:38]:38s} seed {r['seed']}  -> {r['outcome']}")
            print(f"         {r.get('first_detail', '')}")

    print("\n==== VERDICT (floor from baseline.json; margin %g)" % args.margin)
    print(f"{'config':44s} {'runs':>4} {'pass':>4} {'fill':>4} {'cfg':>4} {'pass%':>6} "
          f"{'floor%':>6}  verdict")
    for v in vs:
        print(f"{v['config'][:44]:44s} {v['runs']:4d} {v['pass']:4d} {v['fill']:4d} "
              f"{v['cfgerr']:4d} {v['rate']:6.1f} {v['floor']:6.1f}  {v['verdict']}")

    # ---- the spill metric ------------------------------------------------------------------
    measured = [r for r in rows if r["spilled"] is not None]
    if not measured:
        print("\nprogression-surface spill: NOT MEASURED in any run (no telemetry line). Either no "
              "seed spilled, or this world predates 858f9d6 -- those are different facts and this "
              "harness will not merge them.")
    else:
        dist = Counter(r["spilled"] for r in measured)
        print(f"\nprogression-surface spill over {len(measured)} measured run(s): "
              f"{dict(sorted(dist.items()))}  (0 = fully confined)")

    if args.update_baseline:
        obj = {"_comment": "Auto-written by tools/fill_regression.py --update-baseline. Floors = "
                           "observed pass-rates from that run; subtract a margin by hand for headroom."}
        obj.update({v["config"]: v["rate"] for v in vs})
        with open(args.baseline, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(obj, fh, indent=2)
        print(f"\n  baseline rewritten -> {args.baseline}")

    with open(os.path.join(log_dir, "results.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"stamp": stamp, "mode": mode, "seeds": seeds, "rows": rows, "verdicts": vs},
                  fh, indent=2)
    print(f"  logs + results.json -> {os.path.relpath(log_dir, REPO)}")

    bad = [v for v in vs if v["verdict"] != "ok"]
    if bad:
        print(f"  GATE: FAIL -- {len(bad)} config(s): "
              + ", ".join(f"{v['config']} ({v['verdict']})" for v in bad))
        return 1
    print("  GATE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
