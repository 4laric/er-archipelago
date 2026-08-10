#!/usr/bin/env python3
r"""datamine_check_nearest_boss.py -- per CHECK, the nearest boss ARENA SPAWN and its distance.

WHY
---
Checks already carry a boss, via `DUNGEON_SWEEPS` (3732 member links over 219 triggers; 90% of the
436 ambiguous checks from #524 are in one). That association is NOT an independent signal:

    checks whose OWN region != their sweep boss's SWEEP_REGION:  0        (measured 2026-08-10)

Zero repo-wide, because `SWEEP_REGION` and the member labels come from the same derivation. Exposing
it as a per-check attribute would restate the label and look like evidence.

Distance is different. "This check is 18 m from the Divine Beast Dancing Lion" is a fact about the
world, independent of graces, tiles and buckets -- the three things that disagree in #523/#527.

WHAT IT IS FOR (and what it is NOT)
-----------------------------------
  * RANKING LEADS. #527 has 12 checks labelled Rauh Base whose nearest grace is an Ancient Ruins one
    and whose tiles no PlayArea volume carves. Their distance to the Dancing Lion vs Rugalea is the
    discrimination that question currently lacks.
  * AUDITING SWEEP MEMBERSHIP (#523). The Tree Sentinel's 28 members span five tiles and two side
    dungeons. A distance column makes that a number instead of something you find by decoding flags.
  * `in_arena` (<40 m, the same radius `datamine_arena_graces` uses on graces) marks a check that
    stands INSIDE a fight.

🛑 It does NOT settle a region. It is proximity, exactly like `nearest_grace.tsv`, and a check can
stand near a boss that belongs to the region next door -- which is the whole subject of #523. Treat a
disagreement as a QUESTION and record the answer in `region_overrides.tsv` with its reason.

🛑 Map pins were tried first and REJECTED (2026-08-10). `WorldMapPointParam` is in the gen_inputs
bundle and needs no MSBs, but there are only 209 NAMED overworld pins: 12 of #527's 13 checks resolve
to the same pin ("Miquella's Cross") at 56-309 m. Too sparse to region a check. Recorded so nobody
spends the afternoon I didn't.

DERIVATION -- imported, not reimplemented
-----------------------------------------
`datamine_arena_graces.py` already reads the authoritative boss set (EMEVD `DisplayBossHealthBar`)
and boss positions (witchy'd MSB `Part/Enemy` `<EntityID>`/`<Position>`), and its radius is tuned on
known-bad graces. This imports that machinery so the grace answer and the check answer cannot drift.

⭐ PER-BOSS, NOT PER-MAP (the #522 lesson). A `DisplayBossHealthBar` entity that is not an MSB Part
has no position and is silently skipped. A check whose true nearest boss is one of those gets a
CONFIDENT answer naming some farther boss. Every row therefore carries `map_bosses_unresolved`, and
a row with a non-zero count is a LEAD, NOT A MEASUREMENT.

NEEDS THE MSBs -- Tier 2 (AGENTS.md 5a). The gen_inputs bundle deliberately omits `map/`, so unlike
`datamine_check_ground.py` this cannot run in the sandbox.

Run:  python tools/datamine_check_nearest_boss.py            # report
      python tools/datamine_check_nearest_boss.py --emit     # + greenfield/nearest_boss.tsv
      python tools/datamine_check_nearest_boss.py --flags 2046467010,2045477060   # just these
"""
import argparse
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
GF = os.path.join(REPO, "greenfield")
OUT = os.path.join(GF, "nearest_boss.tsv")

sys.path.insert(0, HERE)
from datamine_arena_graces import (            # noqa: E402  the calibrated machinery
    DEFAULT_RADIUS, boss_ids_by_map, enemy_positions, dist,
)

# Floor on the BOSS side, not the check side: this table is only as good as the MSB coverage behind
# it, and that number is already known -- arena_graces.tsv's header records 108 of 118 boss maps
# adjudicated. Refuse to emit a table built from a collapsed MSB set. Raise, never lower.
MIN_ADJUDICATED_MAPS = 100


def _boss_names():
    """{entity: name} from the generated boss_healthbars module (committed, no artifacts needed)."""
    p = os.path.join(GF, "eldenring", "boss_healthbars.py")
    src = open(p, encoding="utf-8").read()
    return {int(e): n for e, n in
            re.findall(r"(\d+):\s*\('[^']*',\s*'[^']*',\s*'[^']*',\s*'([^']*)'\)", src)}


def _sweep_trigger():
    """{ap_id: trigger flag} and {ap_id: check flag} from the generated modules."""
    src = open(os.path.join(GF, "eldenring", "boss_sweeps.py"), encoding="utf-8").read()
    i = src.index("DUNGEON_SWEEPS = {")
    j = src.index("\n}", i)
    trig = {}
    for m in re.finditer(r"(\d+):\s*\[([^\]]*)\]", src[i:j]):
        for ap in m.group(2).replace("\n", "").split(","):
            if ap.strip():
                trig[int(ap)] = int(m.group(1))
    data = open(os.path.join(GF, "eldenring", "data.py"), encoding="utf-8").read()
    # data.py rows are (label, ap_id, flag); the label may be single- OR double-quoted
    # (Charo's had an apostrophe), so match both or the region column comes out empty.
    flag_of = {}
    region_of = {}
    for m in re.finditer(r"\(\s*(?:'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\")\s*,\s*(\d+)\s*,\s*(\d+)\s*\)",
                         data):
        lbl = m.group(1) or m.group(2)
        flag_of[int(m.group(3))] = int(m.group(4))
        region_of[int(m.group(3))] = lbl.split(" :: ")[0]
    # BOTH dicts are keyed by AP_ID, not by check flag -- mixing them up returns None for every
    # row and the region column ships empty (caught by the 2026-08-10 smoke test, not by a reader).
    return trig, flag_of, region_of


def _check_positions():
    """[(flag, map_id, tile_key, (x,y,z))] for the `item` rows, MSB variants collapsed."""
    seen, out = set(), []
    for ln in open(os.path.join(GF, "item_grace_coords.tsv"), encoding="utf-8"):
        if not ln.startswith("item\t"):
            continue
        p = ln.rstrip("\n").split("\t")
        if len(p) < 6 or not p[1].isdigit():
            continue
        try:
            pos = (float(p[3]), float(p[4]), float(p[5]))
        except ValueError:
            continue
        key = (int(p[1]), p[2][:9], tuple(round(v, 2) for v in pos))
        if key in seen:                       # the _00/_10 variants are the SAME site
            continue
        seen.add(key)
        out.append((int(p[1]), p[2], p[2][:9], pos))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit", action="store_true", help="write %s" % OUT)
    ap.add_argument("--radius", type=float, default=DEFAULT_RADIUS,
                    help="in_arena threshold (default %.0f, the arena-grace radius)" % DEFAULT_RADIUS)
    ap.add_argument("--flags", help="comma-separated check flags to report (diagnostic)")
    args = ap.parse_args()

    bosses = boss_ids_by_map()
    names = _boss_names()
    trig, flag_of, region_of = _sweep_trigger()
    ap_of = {f: a for a, f in flag_of.items()}

    poscache, unresolved_bosses, adjudicated = {}, defaultdict(list), set()
    want = {int(x) for x in args.flags.split(",")} if args.flags else None

    rows = []
    for flag, map_id, tile, pos in _check_positions():
        if want and flag not in want:
            continue
        cands = [k for k in bosses if k.startswith(tile + "_") or k == tile]
        best, miss = None, 0
        for map_id2 in cands:
            if map_id2 not in poscache:
                poscache[map_id2] = enemy_positions(map_id2)
            ep = poscache[map_id2]
            if ep is None:
                continue
            adjudicated.add(map_id2)
            gone = [b for b in bosses[map_id2] if b not in ep]
            if gone:
                unresolved_bosses[map_id2] = sorted(gone)
            miss += len(gone)
            for b in bosses[map_id2]:
                if b not in ep:
                    continue
                d = dist(pos, ep[b])
                if best is None or d < best[0]:
                    best = (d, b)
        if best is None:
            continue
        a = ap_of.get(flag)
        rows.append((flag, map_id, best[1], names.get(best[1], "?"), round(best[0], 1),
                     "yes" if best[0] < args.radius else "no",
                     trig.get(a, ""), region_of.get(a, ""), miss))
    rows.sort()

    if len(adjudicated) < MIN_ADJUDICATED_MAPS and not want:
        raise SystemExit(
            "FATAL: only %d boss map(s) had an unpacked MSB (floor %d). arena_graces.tsv records 108 "
            "of 118 adjudicated -- witchy the .msb.dcx rather than emitting a thinner table that "
            "still looks like an answer." % (len(adjudicated), MIN_ADJUDICATED_MAPS))

    in_arena = sum(1 for r in rows if r[5] == "yes")
    tainted = sum(1 for r in rows if r[8])
    print("nearest_boss: %d check(s) resolved across %d adjudicated map(s); %d stand INSIDE an arena "
          "(<%.0fm)" % (len(rows), len(adjudicated), in_arena, args.radius))
    print("  %d row(s) sit on a map with an UNRESOLVED boss -- those are LEADS, not measurements"
          % tainted)
    if unresolved_bosses:
        n = sum(len(v) for v in unresolved_bosses.values())
        print("  %d boss(es) across %d map(s) have no MSB Part/Enemy position:" % (n, len(unresolved_bosses)))
        for m, bs in sorted(unresolved_bosses.items())[:10]:
            print("    %-12s %s" % (m, ", ".join("%d %s" % (b, names.get(b, "?")) for b in bs)))
    if want:
        print("\n  flag         nearest boss                    dist   in_arena  region")
        for r in rows:
            print("  %-12d %-30s %7.1f  %-8s %s" % (r[0], r[3], r[4], r[5], r[7]))

    if args.emit and not want:
        with open(OUT, "w", encoding="utf-8", newline="\n") as f:
            f.write("# AUTO-GENERATED by tools/datamine_check_nearest_boss.py --emit -- DO NOT EDIT.\n")
            f.write("# Per CHECK: the nearest boss ARENA SPAWN (EMEVD DisplayBossHealthBar joined to\n")
            f.write("#   witchy'd MSB Part/Enemy positions) and the distance to it.\n")
            f.write("# 🛑 PROXIMITY, NOT A REGION. A check can stand near a boss the next region owns --\n")
            f.write("#   that is the subject of #523, not a defect this table settles. A disagreement\n")
            f.write("#   with `region` below is a QUESTION; the answer belongs in region_overrides.tsv.\n")
            f.write("# 🛑 map_bosses_unresolved > 0 means a boss on that map had NO MSB position and was\n")
            f.write("#   skipped, so a nearer boss may exist. Such a row is a LEAD, NOT A MEASUREMENT.\n")
            f.write("# in_arena uses the arena-grace radius (%.0fm).\n" % args.radius)
            f.write("check_flag\tmap_id\tboss_entity\tboss_name\tdistance_m\tin_arena\t"
                    "sweep_trigger\tregion\tmap_bosses_unresolved\n")
            for r in rows:
                f.write("\t".join(str(x) for x in r) + "\n")
        print("\n-> %s (%d rows)" % (OUT, len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
