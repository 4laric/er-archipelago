#!/usr/bin/env python3
"""check_wizard_census_js.py -- differential gate: the wizard's JS seed-size math vs Python's.

The number a player actually reads is computed in JavaScript, inside `wizard/wizard.html`'s
`wizard-core` block (`ERW.seedSize`). Every other gate in this repo proves things about the census
DATA; none of them execute that function, so a JS-side mistake would ship silently behind four green
Python gates.

WHAT IT DOES. Extracts the `wizard-core` script and the injected census blob from wizard.html, runs
`ERW.seedSize` under node for a fixed matrix of option sets, and compares each result against an
independent Python evaluation of the SAME rule in this file. Two implementations, one expectation --
a real differential test, not a restatement: the Python side here is the reference, and the Python
side is itself pinned to REAL BUILT WORLDS by
`worlds/eldenring/tests/test_gf_region_census.py::test_check_count_identity_against_real_worlds`.
So the chain is JS == Python == a world Archipelago actually generated.

DETERMINISM is what makes this comparable at all: `ERW.seedSize` draws from a seeded mulberry32 with
a fixed seed, so a given option set has ONE answer. The Python side re-implements mulberry32 and the
same draw order rather than sampling independently -- comparing two Monte Carlo runs would only ever
prove they agree to within noise, which is not a gate.

NEEDS NODE. Exits 4 (SKIP) when node is absent, so a box without it reports honestly instead of
passing vacuously. `greenfield/ci-linux.sh` and `run_ci.ps1` treat exit 4 as SKIP; CI runners have
node, so the gate is live there.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIZARD_HTML = os.path.join(ROOT, "wizard", "wizard.html")

# The option sets the gate compares. Spans: the default; the two draw sizes players ask about; the
# whole-map branch (n=0, a DIFFERENT code path -- no sampling); a base-game seed; a dlc_only seed
# (the finale must drop out); and a narrowed + widened progression surface, which is the axis the
# combination union exists for.
# The yaml the wizard hands a player has to name a game Archipelago actually has. `buildYaml` carried
# the game name as a LITERAL ("EldenRing") while the world has been "Elden Ring" for months, so every
# emitted yaml named a game that does not exist -- Copy/Download produced a file that cannot
# generate, and Generate & host 422'd on every click. The option KEYS were metadata-driven and fine;
# only the three strings carrying the game name were typed, and nothing read them.
CASES = [
    {"numRegions": 6, "enableDlc": True, "dlcOnly": False},
    {"numRegions": 1, "enableDlc": True, "dlcOnly": False},
    {"numRegions": 12, "enableDlc": True, "dlcOnly": False},
    {"numRegions": 0, "enableDlc": True, "dlcOnly": False},
    {"numRegions": 6, "enableDlc": False, "dlcOnly": False},
    {"numRegions": 4, "enableDlc": True, "dlcOnly": True},
    {"numRegions": 6, "enableDlc": True, "dlcOnly": False, "surfaceClasses": ["MajorBoss"]},
    {"numRegions": 6, "enableDlc": True, "dlcOnly": False,
     "surfaceClasses": ["MajorBoss", "Remembrance", "GreatRune", "Boss", "Legendary"]},
    # The SweepSlot axis. It is not a tag, so it moves the surface band without touching `combos`,
    # and it moves DIFFERENTLY per dungeon_sweep value -- three rungs and the off switch, because a
    # single case would pass with the rung ignored on either side.
    {"numRegions": 6, "enableDlc": True, "dlcOnly": False,
     "surfaceClasses": ["MajorBoss", "SweepSlot"], "dungeonSweep": "bosses"},
    {"numRegions": 6, "enableDlc": True, "dlcOnly": False,
     "surfaceClasses": ["MajorBoss", "SweepSlot"], "dungeonSweep": "all"},
    {"numRegions": 6, "enableDlc": True, "dlcOnly": False,
     "surfaceClasses": ["MajorBoss", "SweepSlot"], "dungeonSweep": "minidungeons"},
    {"numRegions": 6, "enableDlc": True, "dlcOnly": False,
     "surfaceClasses": ["MajorBoss", "SweepSlot"], "dungeonSweep": "none"},
    {"numRegions": 6, "enableDlc": True, "dlcOnly": False,
     "surfaceClasses": ["MajorBoss", "SweepSlotMajor"], "dungeonSweep": "bosses"},
    {"numRegions": 6, "enableDlc": True, "dlcOnly": False,
     "surfaceClasses": ["MajorBoss", "SweepSlotMinor"], "dungeonSweep": "bosses"},
    # ...and the DEFAULT surface, which now contains SweepSlot: the case a player actually gets.
    {"numRegions": 6, "enableDlc": True, "dlcOnly": False, "dungeonSweep": "bosses"},
]


def _metadata(html):
    m = re.search(r'<script id="er-options-metadata" type="application/json">\n(.*?)</script>',
                  html, re.S)
    if not m:
        sys.exit("[FAIL] no er-options-metadata blob in wizard.html")
    return json.loads(m.group(1))


def _extract():
    # `newline=""` is the INJECTOR's convention (a rewrite must not churn the file's endings) and
    # this gate inherited it by copy. It only READS, and every pattern below is written with \n,
    # so on a Windows checkout each one missed and the gate blamed the page. Normalise on read.
    html = open(WIZARD_HTML, "r", encoding="utf-8", newline="").read().replace("\r\n", "\n")
    core = re.search(r'<script id="wizard-core">(.*?)</script>', html, re.S)
    if not core:
        sys.exit("[FAIL] wizard-core block not found in wizard.html")
    blob = re.search(r'<script id="er-region-census" type="application/json">\n(.*?)</script>',
                     html, re.S)
    if not blob:
        sys.exit("[FAIL] er-region-census blob not found in wizard.html -- run "
                 "`python tools/build_region_census.py`")
    return core.group(1), json.loads(blob.group(1))


def _mulberry32(a):
    """Bit-exact port of the wizard's PRNG. int32 wrap and Math.imul are explicit."""
    state = a & 0xFFFFFFFF

    def _imul(x, y):
        r = (x * y) & 0xFFFFFFFF
        return r - 0x100000000 if r >= 0x80000000 else r

    def nxt():
        nonlocal state
        state = (state + 0x6D2B79F5) & 0xFFFFFFFF
        t = _imul(state ^ (state >> 15), 1 | state) & 0xFFFFFFFF
        # `^` binds LOOSER than `+` in JS, so the wizard's
        #     t = t + Math.imul(...) ^ t
        # is `(t + imul) ^ t`, not `t + (imul ^ t)`. Dropping that trailing `^ t` on the first
        # port produced a stream that agreed to within sampling noise -- medians within 1% --
        # which is exactly the failure a differential gate exists to catch and eyeballing does not.
        t = ((t + _imul(t ^ (t >> 7), 61 | t)) ^ t) & 0xFFFFFFFF
        t = (t ^ (t >> 14)) & 0xFFFFFFFF
        return t / 4294967296.0
    return nxt


def _combo_hits(region, sel, rung="bosses"):
    n = 0
    for combo, count in region["combos"].items():
        if sel & set(combo.split("|")):
            n += count
    # SweepSlot is DERIVED: it carries no tag, so it is not in `combos` and its size depends on
    # dungeon_sweep (64 checks corpus-wide at `minidungeons`, 215 at `bosses`, 0 at `none`). This
    # differential exists precisely to catch a JS/Python split like this one, and the first run after
    # the JS learned about it reported surface 394 vs 179 -- a gap of exactly the 215 sweep slots.
    sweep_by_class = region.get("sweep_slots_by_class") or {}
    if "SweepSlot" in sel:
        n += (sweep_by_class.get("SweepSlot") or region.get("sweep_slots") or {}).get(rung or "bosses", 0)
    else:
        for cls in ("SweepSlotMajor", "SweepSlotMinor"):
            if cls in sel:
                n += (sweep_by_class.get(cls) or {}).get(rung or "bosses", 0)
    return n


def seed_size(census, opts):
    """The reference implementation. Mirrors ERW.seedSize step for step, including draw order."""
    sel = set(opts.get("surfaceClasses") or census["default_classes"])
    rung = opts.get("dungeonSweep") or "bosses"
    R = census["regions"]
    eligible = [n for n in sorted(R)
                if R[n]["rollable"] and (R[n]["dlc"] if opts["dlcOnly"]
                                         else (opts["enableDlc"] or not R[n]["dlc"]))]
    if not eligible:
        return None
    elig = set(eligible)
    fin = (census.get("finale") or {}).get("region")
    finale_on = bool(fin and fin in R) and any(not R[n]["dlc"] for n in eligible)
    hub = census["hub_region"]
    base = R[hub]["checks"] + (R[fin]["checks"] if finale_on else 0)
    base_surf = (_combo_hits(R[hub], sel, rung)
                 + (_combo_hits(R[fin], sel, rung) if finale_on else 0))

    n = int(opts["numRegions"])
    whole = (n <= 0 or n >= len(eligible))
    trials = 1 if whole else 4000
    rnd = _mulberry32(0x45524147)
    checks, surf, kept = [], [], []
    for _ in range(trials):
        if whole:
            kept_set = set(eligible)
        else:
            pool = list(eligible)
            kept_set = set()
            for _i in range(n):
                kept_set.add(pool.pop(int(rnd() * len(pool))))
            grew = True
            while grew:
                grew = False
                for r in sorted(kept_set):
                    p = census["parent"].get(r)
                    if p and p in elig and p not in kept_set:
                        kept_set.add(p)
                        grew = True
        c, s = base, base_surf
        for r in kept_set:
            c += R[r]["checks"]
            s += _combo_hits(R[r], sel, rung)
        checks.append(c)
        surf.append(s)
        kept.append(len(kept_set))

    def band(a):
        a = sorted(a)
        q = lambda p: a[int(p * (len(a) - 1))]
        return {"min": q(0), "p10": q(0.10), "median": q(0.5), "p90": q(0.90), "max": q(1)}
    return {"whole": whole, "trials": trials, "eligible": len(eligible), "finale": finale_on,
            "checks": band(checks), "surface": band(surf), "kept": band(kept)}


def _run_node(core, census, cases):
    harness = (core + "\nconst __census = " + json.dumps(census) + ";\n"
               + "const __cases = " + json.dumps(cases) + ";\n"
               + "console.log(JSON.stringify(__cases.map(c => ERW.seedSize(__census, c))));\n")
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "harness.js")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(harness)
        out = subprocess.run(["node", path], capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit("[FAIL] node harness failed:\n" + (out.stderr or "")[-4000:])
    return json.loads(out.stdout.strip().splitlines()[-1])


def check_yaml_names_the_game(core, meta):
    """buildYaml's `game:` line and its option section must both be meta.game."""
    harness = (core + "\nconst __meta = " + json.dumps(meta) + ";\n"
               + "const m = ERW.loadMeta(__meta);\n"
               + "const st = { name:'Player', presetId:null, presetTitle:'Defaults', values:{} };\n"
               + "console.log(JSON.stringify(ERW.buildYaml(m, st)));\n")
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "yaml.js")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(harness)
        out = subprocess.run(["node", path], capture_output=True, text=True)
    if out.returncode != 0:
        return ["buildYaml harness failed:\n" + (out.stderr or "")[-2000:]]
    text = json.loads(out.stdout.strip().splitlines()[-1])
    game = meta["game"]
    bad = []
    if ("game: %s" % game) not in text:
        bad.append("emitted yaml does not say %r -- it says %r"
                   % ("game: " + game,
                      next((l for l in text.splitlines() if l.startswith("game:")), "<no game line>")))
    if not any(l.startswith(game + ":") for l in text.splitlines()):
        bad.append("emitted yaml has no %r option section" % (game + ":"))
    return bad


def main():
    if not shutil.which("node"):
        print("[SKIP] node not on PATH -- the wizard's JS seed-size math is NOT gated on this box.")
        return 4
    # `newline=""` is the INJECTOR's convention (a rewrite must not churn the file's endings) and
    # this gate inherited it by copy. It only READS, and every pattern below is written with \n,
    # so on a Windows checkout each one missed and the gate blamed the page. Normalise on read.
    html = open(WIZARD_HTML, "r", encoding="utf-8", newline="").read().replace("\r\n", "\n")
    core, census = _extract()
    cases = [dict(c) for c in CASES]
    js = _run_node(core, census, cases)
    bad = []
    for case, got in zip(cases, js):
        want = seed_size(census, case)
        if got != want:
            bad.append("  case %s\n    js     %s\n    python %s" % (json.dumps(case), got, want))
    game_bad = check_yaml_names_the_game(core, _metadata(html))
    if game_bad:
        print("[FAIL] the yaml the wizard emits names the wrong game:")
        for b in game_bad:
            print("   ", b)
        return 1
    if bad:
        print("[FAIL] wizard JS seed-size disagrees with the Python reference:")
        print("\n".join(bad))
        return 1
    print("[ok] wizard JS seed-size matches the Python reference on %d option set(s)" % len(cases))
    return 0


if __name__ == "__main__":
    sys.exit(main())
