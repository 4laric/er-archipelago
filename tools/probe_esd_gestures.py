#!/usr/bin/env python3
"""probe_esd_gestures.py -- WHAT does a talk ESD call when an NPC TEACHES you a gesture?

READ-ONLY. Writes nothing, emits no table, changes no data. Run it, paste the output.

WHY THIS EXISTS
---------------
gen_data._gesture_derive builds GESTURE_AWARD_FLAGS from EMEVD only -- the two parameterized common
events (90005570 / 900005571) plus literal `AwardGesture` sites in map EMEVDs. A gesture an NPC
teaches IN DIALOGUE has no EMEVD award site at all, so widening that scan can never reach it. All 14
entries are EMEVD-derived, and "Sitting Sideways" (Roderika, Stormhill Shack) is not among them:
she teaches it, the player learns the vanilla gesture, and nothing fires. Alaric, in-game
2026-07-26; kanban #217.

The ESD corpus is already mined for two other verbs -- `OpenRegularShop` (esd_gates.tsv) and
`AwardItemLot` (esd_gifts.tsv) -- by tools/datamine_esd_gates.py, whose call-site resolver handles
the parameterized `assert t.._x3(lot1=N) -> AwardItemLot(lot1)` chain that a literal-only read
misses (99 of 105 gift sites are parameterized). Adding a third verb is a small extension of that
machinery -- ONCE WE KNOW WHAT THE VERB IS CALLED.

That is the one thing the sandbox cannot answer: the decompiled ESD is a Windows-only artifact.
So this probe measures it instead of guessing it. Guessing an ESDLang function name and shipping a
datamine around it is precisely the failure CONTRIBUTING's "no invented IDs" section bans -- a
regex that matches nothing returns a confident empty result, and an empty result reads exactly like
"this NPC teaches no gestures."

WHAT IT REPORTS
---------------
  1. Every call in the corpus whose function name mentions "gesture" (case-insensitive), with its
     argument shape -- the vocabulary question.
  2. The same, narrowed to the talk ids passed with --talk (default: Roderika's, derived from
     esd_gifts.tsv rather than typed -- the rows that hand over lot 101900, her Spirit Jellyfish
     Ashes).
  3. If GestureParam.csv is present: gesture id -> itemId for every id seen, so the award can be
     named without anyone guessing which of her two gesture-band flags is Sitting Sideways.
  4. A NEGATIVE result is reported as loudly as a positive one. "No gesture verb in the corpus"
     is a real, useful answer -- it would mean the award rides an EMEVD or an item lot instead, and
     the fix belongs somewhere else entirely.

INPUT: ESDLang-decompiled Python, the same corpus datamine_esd_flags.py / _gates.py read:
    ESDLang.exe -er -esddir elden_ring_artifacts\\talk -writepy elden_ring_artifacts\\esd_py\\%e.py
    (or wherever you put it -- pass --pydir)

USAGE (PowerShell, from the repo root):
    python tools\\probe_esd_gestures.py
    python tools\\probe_esd_gestures.py --pydir elden_ring_artifacts\\esd_py --all
"""
import argparse
import ast
import collections
import csv
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.abspath(os.path.join(HERE, ".."))
ART = os.path.join(REPO, "elden_ring_artifacts")
PYDIR_DEFAULT = os.path.join(ART, "talk")
GESTURE_PARAM = os.path.join(ART, "vanilla_er", "vanilla_er", "GestureParam.csv")
ESD_GIFTS = os.path.join(REPO, "greenfield", "esd_gifts.tsv")
ESD_FLAGS = os.path.join(REPO, "greenfield", "esd_flags.tsv")

# Roderika's Spirit Jellyfish Ashes lot. The ONE literal in this file, cited to
# greenfield/flag_lots.tsv line 390: `400190  map  101900  1  1  236000  1  7`.
LOT_SPIRIT_JELLYFISH_ASHES = 101900
GESTURE_FLAG_BAND = range(60800, 60900)


def _call_name(node):
    f = node.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def _shape(node):
    """A compact, lossless-enough rendering of a call's arguments: literals as numbers, everything
    else by ast class. Enough to write the real resolver against, short enough to paste."""
    def one(a):
        if isinstance(a, ast.Constant):
            return repr(a.value)
        if isinstance(a, ast.Name):
            return f"<name {a.id}>"
        if isinstance(a, ast.Attribute):
            return f"<attr .{a.attr}>"
        if isinstance(a, ast.Call):
            return f"<call {_call_name(a)}()>"
        return f"<{type(a).__name__}>"
    args = [one(a) for a in node.args]
    args += [f"{k.arg}={one(k.value)}" for k in node.keywords]
    return "(" + ", ".join(args) + ")"


def _talk_id(path):
    """t123456.py / 123456.py -> '123456'. The corpus names files after the talk id."""
    base = os.path.splitext(os.path.basename(path))[0]
    return base[1:] if base.startswith("t") and base[1:].isdigit() else base


def _map_of(path):
    d = os.path.basename(os.path.dirname(os.path.abspath(path)))
    for suf in ("-only", "-talkesdbnd-dcx"):
        if d.endswith(suf):
            d = d[: -len(suf)]
    return d


def _roderika_talks():
    """DERIVED, not typed: the talk ESDs that hand over lot 101900 (esd_gifts.tsv)."""
    if not os.path.isfile(ESD_GIFTS):
        return set()
    out = set()
    with open(ESD_GIFTS, encoding="utf-8") as fh:
        for ln in fh:
            if ln.startswith("#") or ln.startswith("talk_id"):
                continue
            p = ln.rstrip("\n").split("\t")
            if len(p) == 4 and p[3].isdigit() and int(p[3]) == LOT_SPIRIT_JELLYFISH_ASHES:
                out.add(p[0])
    return out


def _gesture_band_flags(talks):
    """Gesture-band flags those talks SET (esd_flags.tsv) -- the candidates the award must explain."""
    if not os.path.isfile(ESD_FLAGS):
        return set()
    out = set()
    with open(ESD_FLAGS, encoding="utf-8") as fh:
        for ln in fh:
            if ln.startswith("#") or ln.startswith("flag\t"):
                continue
            p = ln.rstrip("\n").split("\t")
            if len(p) >= 5 and p[0].isdigit() and p[2] in talks and int(p[0]) in GESTURE_FLAG_BAND:
                out.add(int(p[0]))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pydir", default=PYDIR_DEFAULT, help="ESDLang-decompiled .py root")
    ap.add_argument("--talk", action="append", default=[],
                    help="talk id to narrow on (repeatable; default = derived from esd_gifts.tsv)")
    ap.add_argument("--all", action="store_true", help="print EVERY site, not just a sample")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.pydir, "**", "*.py"), recursive=True))
    if not files:
        sys.exit(f"FATAL: no .py under {args.pydir!r}. Decompile the talk ESDs first "
                 f"(see tools/datamine_esd_gates.py docstring), or pass --pydir.")
    print(f"corpus: {len(files)} decompiled talk ESD file(s) under {args.pydir}")

    talks = set(args.talk) or _roderika_talks()
    cands = _gesture_band_flags(talks)
    print(f"narrowing talk ids: {sorted(talks) or '(none -- esd_gifts.tsv absent?)'}")
    print(f"gesture-band flags those talks SET (esd_flags.tsv): {sorted(cands) or '(none)'}")
    print(f"  -> exactly one of these should be Sitting Sideways. Which one is what item 3 answers.")

    verbs = collections.Counter()          # fn name -> call count
    shapes = collections.defaultdict(collections.Counter)
    sites = collections.defaultdict(list)  # fn name -> [(talk, map, shape)]
    gesture_ids = collections.Counter()
    parse_fail = 0
    for path in files:
        try:
            tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
        except SyntaxError:
            parse_fail += 1
            continue
        t, m = _talk_id(path), _map_of(path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _call_name(node)
            if not name or "gesture" not in name.lower():
                continue
            sh = _shape(node)
            verbs[name] += 1
            shapes[name][sh] += 1
            sites[name].append((t, m, sh))
            for a in node.args:
                if isinstance(a, ast.Constant) and isinstance(a.value, int):
                    gesture_ids[a.value] += 1
    if parse_fail:
        print(f"WARNING: {parse_fail} file(s) failed to parse -- they were SKIPPED, so every count "
              f"below is a floor, not a total.")

    print("\n=== 1. gesture vocabulary across the whole corpus ===")
    if not verbs:
        print("  NONE. No call in any talk ESD has 'gesture' in its name.")
        print("  That is a REAL ANSWER, not a failed run: it would mean the ESD does not award")
        print("  gestures directly, and the award rides something else (an EMEVD the talk triggers,")
        print("  or an item lot). Next probe: grep the corpus for the candidate flags above and see")
        print("  what is set alongside them.")
    for name, n in verbs.most_common():
        print(f"  {name}  x{n}")
        for sh, k in shapes[name].most_common(6):
            print(f"      {k:5d}  {name}{sh}")

    print("\n=== 2. sites on the narrowed talk ids ===")
    hit = [(name, t, m, sh) for name, lst in sites.items() for (t, m, sh) in lst if t in talks]
    if not hit:
        print(f"  none on talks {sorted(talks)}."
              + ("" if verbs else " (consistent with an empty item 1.)"))
    for name, t, m, sh in sorted(hit):
        print(f"  talk {t} ({m}): {name}{sh}")

    if not args.all and sum(verbs.values()) > 40:
        print(f"\n  ({sum(verbs.values())} sites total; pass --all to print every one)")
    elif verbs:
        print("\n  all sites:")
        for name, lst in sorted(sites.items()):
            for t, m, sh in sorted(lst):
                print(f"  talk {t} ({m}): {name}{sh}")

    print("\n=== 3. GestureParam join for every integer seen at a gesture call ===")
    if not os.path.isfile(GESTURE_PARAM):
        print(f"  GestureParam.csv not at {GESTURE_PARAM} -- skipped. (Pass --pydir's sibling, or "
              f"run from a tree with elden_ring_artifacts/.)")
    elif not gesture_ids:
        print("  no integer literals at any gesture call -- the ids are PARAMETERS, resolved at the")
        print("  $Initialize-style call site. That is the same shape as the 99/105 parameterized")
        print("  AwardItemLot sites, so datamine_esd_gates.py's resolver already handles it.")
    else:
        g2i = {}
        with open(GESTURE_PARAM, newline="", encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                if str(r.get("ID", "")).lstrip("-").isdigit():
                    g2i[int(r["ID"])] = int(r.get("itemId") or 0)
        for gid, n in gesture_ids.most_common():
            if gid in g2i:
                print(f"  gesture {gid:6d} (seen x{n}) -> GestureParam.itemId {g2i[gid]}  "
                      f"[goods flag 0x40000000|itemId = {0x40000000 | g2i[gid]}]")
    print("\ndone -- paste this whole output back.")


if __name__ == "__main__":
    main()
