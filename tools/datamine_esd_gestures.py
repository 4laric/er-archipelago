#!/usr/bin/env python3
"""datamine_esd_gestures.py -- the gestures NPCs TEACH YOU IN DIALOGUE, and the flag each one sets.

THE THIRD AWARD CORPUS
----------------------
`gen_data._gesture_derive` builds GESTURE_AWARD_FLAGS from EMEVD only: the two parameterized common
events (90005570 / 900005571) and the literal `AwardGesture` sites in map EMEVDs. A gesture an NPC
teaches in DIALOGUE has no EMEVD award site at all, so no widening of that scan can ever reach it --
all 14 entries are EMEVD-derived and "Sitting Sideways" (Roderika, Stormhill Shack) is not among
them. She teaches it, the player learns the vanilla gesture, and nothing fires. (Alaric, in-game
2026-07-26; kanban #217. Same class as "By My Sword" paying vanilla in Leyndell, 2026-07-14 -- one
corpus down.)

THE VERB IS `AcquireGesture`, NOT `AwardGesture`. MEASURED, not guessed: `tools/probe_esd_gestures.py`
on the 2026-07-26 corpus reports 58 `AcquireGesture(<int>)` sites and no other gesture verb. The
EMEVD spelling is `AwardGesture`; a datamine written on the EMEVD name would have matched nothing and
returned a confident empty table that reads exactly like "no NPC teaches a gesture". That near-miss
is why the probe exists and why this file does not name the verb from memory.

THE PAIRING RULE (and why it is a rule, not arithmetic)
-------------------------------------------------------
A check needs the ACQUISITION FLAG, and `AcquireGesture(g)` carries only the gesture id. In the ESD
the two sit side by side in one state body: `AcquireGesture(93); SetEventFlag(60835, FlagState.On)`.
So this tool pairs each award with the NEAREST gesture-band `SetEventFlag(..., On)` in the same
enclosing state -- the identical proximity discipline `_gesture_derive` already uses on EMEVD, and
equidistant candidates are a FATAL, never a coin flip.

🛑 It deliberately does NOT pair by arithmetic, even though the low band tempts you: the committed
table has 60801->1, 60802->2, 60809->9 and 60832->90, 60833->91, 60836->94, which looks like
`flag == 60800 + gesture`. It is FALSE globally -- the same table has 60819->41, 60822->52,
60824->54, 60826->60, 60829->72. A rule that holds on the cases you looked at and breaks on the
ones you did not is this project's house bug.

OVERLAP IS EXPECTED, AND IT IS A POSITIVE CONTROL, NOT A COLLISION TO SUPPRESS
------------------------------------------------------------------------------
Two flags are ALREADY in GESTURE_AWARD_FLAGS and are also ESD-set: 60819 (gesture 41) and 60832
(gesture 90), both Patches. One physical interaction, two script sources. `_gesture_derive`'s
existing `_collide8` guard FATALs on exactly that, and it is right to -- the consumer must keep
exactly ONE location per flag. The value of the overlap here is that it independently corroborates
the pairing rule on rows whose answer is already known: if this tool pairs 60819 with anything other
than gesture 41, the rule is wrong and everything else it emits is suspect. `--probe` checks that
and says so.

INPUT:  ESDLang-decompiled Python (Windows one-time step; see tools/datamine_esd_gates.py docstring).
OUTPUT: greenfield/esd_gestures.tsv -- gesture_id, flag, talk_id, map_id, how, scope

  how   = literal | arg | argsum   (from the shared resolver in datamine_esd_flags.py -- this tool
          does not re-implement the ESD call graph, it imports the reviewed one)
  scope = state    (paired inside the enclosing ESD state body -- the strong case)
        | file     (no gesture-band flag in the state; paired within the file. WEAKER: reported
                   separately, never silently merged into the strong count)

USAGE (PowerShell, from the repo root):
    python tools\\datamine_esd_gestures.py --probe    # print what was parsed, write NOTHING
    python tools\\datamine_esd_gestures.py            # write greenfield/esd_gestures.tsv

TIER 2 (AGENTS.md §5a): this table is a gen_data INPUT. `build.ps1 -All` does NOT emit it. Run the
emit FIRST, commit the tsv, and only then does gen_data pick it up. Order is emit -> gen_data.
"""
import argparse
import ast
import collections
import glob
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.abspath(os.path.join(HERE, ".."))
ART = os.path.join(REPO, "elden_ring_artifacts")
PYDIR_DEFAULT = os.path.join(ART, "talk")
OUT = os.path.join(REPO, "greenfield", "esd_gestures.tsv")
ESD_FLAGS_TSV = os.path.join(REPO, "greenfield", "esd_flags.tsv")
DATA_PY = os.path.join(REPO, "greenfield", "eldenring", "data.py")

sys.path.insert(0, HERE)
import datamine_esd_flags as esdf   # noqa: E402  -- the reviewed ESD call-graph resolver

_ACQUIRE_FNS = {"AcquireGesture"}
# ER gesture acquisition flags are group-allocated in one contiguous band; every one of the 14
# committed GESTURE_AWARD_FLAGS entries falls in it. Used ONLY to filter SetEventFlag targets down to
# plausible pairing candidates -- never to derive a flag from a gesture id.
GESTURE_FLAG_BAND = range(60800, 60900)
# Corroboration rows: ESD-set flags whose gesture id the EMEVD scan already knows (see the docstring).
# Populated from data.py at runtime rather than typed here.


def _pos(node):
    """A linear position proxy for proximity. Ordering within a body is all this needs to be."""
    return (getattr(node, "lineno", 0), getattr(node, "col_offset", 0))


def _dist(a, b):
    (l1, c1), (l2, c2) = _pos(a), _pos(b)
    return abs((l1 * 1000 + c1) - (l2 * 1000 + c2))


def _committed_gesture_flags():
    """data.GESTURE_AWARD_FLAGS = {flag: (gesture_id, goods_fullid, name)} -- the EMEVD-derived table
    this tool is corroborated against. Empty dict if data.py isn't here (probe degrades, says so)."""
    if not os.path.isfile(DATA_PY):
        return {}
    spec = importlib.util.spec_from_file_location("_gf_data_for_esd_gestures", DATA_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return dict(getattr(mod, "GESTURE_AWARD_FLAGS", {}) or {})


def _scan_file(path, pydir):
    """-> (rows, unpaired, ambiguous, unresolved_gesture) for one decompiled talk ESD.

    rows: (gesture_id, flag, talk_id, map_id, how, scope)
    """
    src = open(path, encoding="utf-8", errors="replace").read()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return [], [], [], [("<parse error>", path)]
    talk, mapid = esdf._talk_id_of(path), esdf._map_of(path, pydir)
    lit, fwd = esdf._bindings(tree)
    owner = esdf._enclosing_fns(tree)

    def scope_of(node):
        chain = owner.get(node) or [""]
        return chain[0]

    # every SetEventFlag(<gesture-band>, On) in the file, with its enclosing state
    setters = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call) or esdf._fn_name(n) not in esdf._SETFLAG_FNS:
            continue
        if len(n.args) < 2 or esdf._sense_of(n.args[1]) != "on":
            continue
        vals, how = esdf._flag_values(n.args[0], scope_of(n), lit, fwd)
        band = {v for v in vals if v in GESTURE_FLAG_BAND}
        if len(band) == 1:
            setters.append((n, band.pop(), how, scope_of(n)))

    # ---- acquisition sites, gesture id resolved (literal, else through the call graph) ----------
    acquires = []
    unresolved = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call) or esdf._fn_name(n) not in _ACQUIRE_FNS or not n.args:
            continue
        gid = esdf._const_int(n.args[0])
        if gid is None and isinstance(n.args[0], ast.Name):
            got = esdf._resolve_param((scope_of(n), n.args[0].id), lit, fwd)
            gid = got.pop() if len(got) == 1 else None
        if gid is None:
            unresolved.append((talk, mapid, ast.dump(n.args[0])[:60]))
            continue
        acquires.append((n, gid))

    rows, unpaired, ambiguous = [], [], []
    # ---- PASS 1: the strong pairing -- nearest gesture-band setter in the SAME state body --------
    leftover = []
    for n, gid in acquires:
        pool = [s for s in setters if s[3] == scope_of(n)]
        if not pool:
            leftover.append((n, gid))
            continue
        ranked = sorted(((_dist(n, s[0]), s[1], s[2]) for s in pool), key=lambda t: (t[0], t[1]))
        if len(ranked) > 1 and ranked[1][0] == ranked[0][0] and ranked[1][1] != ranked[0][1]:
            ambiguous.append((talk, mapid, gid, [r[1] for r in ranked[:2]], "state"))
            continue
        rows.append((gid, ranked[0][1], talk, mapid, ranked[0][2], "state"))

    # ---- PASS 2: leftovers, file scope -- and ONLY when the answer is forced -----------------
    # A leftover may pair to a flag set in a SIBLING state (ESD machines split across states), but
    # "nearest setter anywhere in the file" is not a derivation, it is a coin flip with good manners:
    # on the smoke fixture it cheerfully handed an unflagged award the flag belonging to a DIFFERENT
    # gesture, and the corroboration control is what caught it. So a leftover is paired only if,
    # after removing every flag PASS 1 already claimed, exactly ONE gesture-band flag remains in the
    # file. Anything else is UNPAIRED and gets reported -- an unpaired award is a check the flag poll
    # cannot see, which is worth a human minute and never worth a guess.
    claimed = {f for (_g, f, _t, _m, _h, _s) in rows}
    free = sorted({s[1] for s in setters} - claimed)
    for n, gid in leftover:
        if len(free) == 1:
            how = next(s[2] for s in setters if s[1] == free[0])
            rows.append((gid, free[0], talk, mapid, how, "file"))
        else:
            unpaired.append((talk, mapid, gid))
    return rows, unpaired, ambiguous, unresolved


# ---- SELF-TEST -------------------------------------------------------------------------------
# The real corpus is a Windows-only artifact, so the PAIRING RULE would otherwise ship unexercised.
# This builds a synthetic ESD in a temp dir and asserts the three behaviours that matter, including
# the one that already bit: on the first draft the file-scope fallback handed an award with no flag
# of its own the flag belonging to a DIFFERENT gesture, and only the corroboration control caught it.
# Runs anywhere, needs no artifacts:  python tools/datamine_esd_gestures.py --selftest
_FIXTURE = {
    # Roderika: two gestures, each beside its own flag -> both must pair, state-scoped.
    "m11_10_00_00-only/t320001110.py": """
def t320001110():
    def State1():
        AcquireGesture(3)
        SetEventFlag(60803, FlagState.On)
    def State2():
        AcquireGesture(93)
        SetEventFlag(60835, FlagState.On)
        AwardItemLot(101900)
""",
    # Patches: the two flags the committed EMEVD table already knows (60819->41, 60832->90) --
    # the positive control -- plus a THIRD award with no flag anywhere, which must come out
    # UNPAIRED rather than stealing one of theirs.
    "m31_00_00_00-only/t309003100.py": """
def t309003100():
    def S1():
        AcquireGesture(41)
        SetEventFlag(60819, FlagState.On)
    def S2():
        AcquireGesture(90)
        SetEventFlag(60832, FlagState.On)
    def S3():
        AcquireGesture(7)
""",
}


def _selftest():
    import shutil
    import tempfile
    root = tempfile.mkdtemp(prefix="esd_gesture_selftest_")
    try:
        for rel, body in _FIXTURE.items():
            path = os.path.join(root, *rel.split("/"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "w", encoding="utf-8").write(body)
        rows, unpaired, ambiguous, unresolved = [], [], [], []
        for p in sorted(glob.glob(os.path.join(root, "**", "*.py"), recursive=True)):
            r, u, a, x = _scan_file(p, root)
            rows += r
            unpaired += u
            ambiguous += a
            unresolved += x
        got = {(g, f) for (g, f, _t, _m, _h, _s) in rows}
        assert got == {(3, 60803), (93, 60835), (41, 60819), (90, 60832)}, got
        assert all(s == "state" for (_g, _f, _t, _m, _h, s) in rows), rows
        assert [(t, g) for (t, _m, g) in unpaired] == [("309003100", 7)], unpaired
        assert not ambiguous and not unresolved, (ambiguous, unresolved)
        print("selftest OK: 4 state-scoped pairings; the flagless award stayed UNPAIRED instead of "
              "stealing a neighbour's flag; both EMEVD-corroborated rows (60819->41, 60832->90) "
              "agree with the committed table.")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pydir", default=PYDIR_DEFAULT)
    ap.add_argument("--probe", action="store_true", help="print findings, write nothing")
    ap.add_argument("--selftest", action="store_true",
                    help="exercise the pairing rule on a synthetic corpus; needs no artifacts")
    ap.add_argument("--allow-unpaired", action="store_true",
                    help="emit even though some award site could not be paired to a flag "
                         "(review the printed list FIRST -- each one is a check we would lose)")
    args = ap.parse_args()

    if args.selftest:
        return _selftest()

    files = sorted(glob.glob(os.path.join(args.pydir, "**", "*.py"), recursive=True))
    if not files:
        sys.exit(f"FATAL: no .py under {args.pydir!r}. Decompile the talk ESDs first "
                 f"(see tools/datamine_esd_gates.py docstring), or pass --pydir.")

    rows, unpaired, ambiguous, unresolved = [], [], [], []
    for p in files:
        r, u, a, x = _scan_file(p, args.pydir)
        rows += r
        unpaired += u
        ambiguous += a
        unresolved += x

    # DEDUPE on the whole tuple: one gesture can be taught on several dialogue paths in one talk.
    rows = sorted(set(rows))
    by_scope = collections.Counter(r[5] for r in rows)
    by_flag = collections.defaultdict(set)
    for gid, flag, _t, _m, _h, _s in rows:
        by_flag[flag].add(gid)

    print(f"corpus: {len(files)} decompiled talk ESD file(s) under {args.pydir}")
    print(f"AcquireGesture rows: {len(rows)} "
          f"(state-scoped {by_scope['state']}, file-scoped {by_scope['file']}) "
          f"over {len(by_flag)} distinct flag(s)")

    # ---- a filter with no tally is a lie -------------------------------------------------------
    if unresolved:
        print(f"UNRESOLVED gesture id at {len(unresolved)} site(s) -- the argument is neither a "
              f"literal nor a uniquely-resolvable parameter:")
        for t, m, shape in unresolved[:20]:
            print(f"  talk {t} ({m}): AcquireGesture({shape})")
    if unpaired:
        print(f"UNPAIRED: {len(unpaired)} award site(s) with NO gesture-band SetEventFlag anywhere "
              f"in the file. Each is a gesture the flag poll cannot see -- i.e. a check we would "
              f"LOSE, not a row to drop quietly:")
        for t, m, g in unpaired:
            print(f"  talk {t} ({m}): AcquireGesture({g}) -- no acquisition flag")
    if ambiguous:
        print(f"AMBIGUOUS: {len(ambiguous)} site(s) where two DIFFERENT gesture-band flags are "
              f"equidistant. Proximity cannot choose; resolve by hand:")
        for t, m, g, cands, scope in ambiguous:
            print(f"  talk {t} ({m}): AcquireGesture({g}) <- {cands} ({scope} scope)")

    # a flag that awards two different gestures is not one check
    multi = {f: sorted(g) for f, g in by_flag.items() if len(g) > 1}
    if multi:
        print(f"SPLIT: flag(s) paired to MORE THAN ONE gesture -- the pairing rule broke here: {multi}")

    # ---- POSITIVE CONTROL: rows the EMEVD scan already knows the answer to -----------------------
    committed = _committed_gesture_flags()
    if not committed:
        print("WARNING: greenfield/eldenring/data.py not readable -- the positive control did NOT "
              "run, so nothing here is corroborated. Treat the output as unverified.")
    else:
        shared = sorted(set(by_flag) & set(committed))
        if not shared:
            print("POSITIVE CONTROL DID NOT RUN: no emitted flag is also in GESTURE_AWARD_FLAGS. "
                  "The 2026-07-26 corpus shares 60819 and 60832 (both Patches); if that is now zero, "
                  "the corpus or the scan changed shape -- find out WHICH before trusting this run.")
        for f in shared:
            mine, theirs = sorted(by_flag[f])[0], committed[f][0]
            verdict = "AGREE" if mine == theirs else "*** DISAGREE ***"
            print(f"  control f{f}: ESD says gesture {mine}, EMEVD says {theirs}  {verdict}")
        bad = [f for f in shared if sorted(by_flag[f])[0] != committed[f][0]]
        if bad:
            sys.exit(f"FATAL: the pairing rule disagrees with the committed EMEVD table on {bad}. "
                     f"Every row this tool emits is suspect until that is explained -- do NOT emit.")

    # ---- cross-check against the sibling table --------------------------------------------------
    if os.path.isfile(ESD_FLAGS_TSV):
        known = set()
        with open(ESD_FLAGS_TSV, encoding="utf-8") as fh:
            for ln in fh:
                if ln.startswith("#") or ln.startswith("flag\t"):
                    continue
                p = ln.rstrip("\n").split("\t")
                if len(p) >= 3 and p[0].isdigit():
                    known.add((int(p[0]), p[2]))
        missing = sorted({(f, t) for (_g, f, t, _m, _h, _s) in rows} - known)
        print(f"esd_flags.tsv agreement: {len(missing)} emitted (flag, talk) pair(s) that table does "
              f"not carry" + (f" -- {missing[:10]}" if missing else ""))

    if not rows:
        sys.exit("FATAL: zero AcquireGesture rows -- an empty result is a failure, not a clean run. "
                 "Check the decompiled .py is ESDLang output and re-run tools/probe_esd_gestures.py.")
    if args.probe:
        print("\n--- rows (probe; nothing written) ---")
        for r in rows:
            print("  gesture %-4d flag %-8d talk %-10s %-14s %-7s %s" % r)
        return
    if (unpaired or ambiguous) and not args.allow_unpaired:
        sys.exit("REFUSING TO EMIT: unpaired and/or ambiguous award sites above. Each one is a "
                 "gesture with no acquisition flag = a check the flag poll can never see. Resolve "
                 "them, or re-run with --allow-unpaired once you have decided they are not checks.")

    with open(OUT, "w", newline="\n", encoding="utf-8") as fh:
        fh.write("# AUTO-GENERATED by tools/datamine_esd_gestures.py -- DO NOT EDIT, re-emit.\n")
        fh.write("# Gestures NPCs TEACH IN DIALOGUE (ESDLang `AcquireGesture`), paired to the\n")
        fh.write("# acquisition flag set beside them. gen_data._gesture_derive is EMEVD-only and is\n")
        fh.write("# structurally blind to this corpus; this table is how it sees them.\n")
        fh.write("# scope=state is the strong pairing; scope=file is weaker -- see the tool docstring.\n")
        fh.write("# MEASURED THIS RUN: %d rows | %d distinct flags | state %d / file %d\n"
                 % (len(rows), len(by_flag), by_scope["state"], by_scope["file"]))
        fh.write("gesture_id\tflag\ttalk_id\tmap_id\thow\tscope\n")
        for r in rows:
            fh.write("%d\t%d\t%s\t%s\t%s\t%s\n" % r)
    print(f"\nwrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
