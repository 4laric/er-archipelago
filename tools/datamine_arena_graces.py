#!/usr/bin/env python3
"""DERIVE the arena-grace class: a grace whose spawn point sits INSIDE a boss arena.

WHY
---
`gen_data._ARENA_GRACE_FLAGS` is a HAND-MAINTAINED skip list, and every entry in it was added after a
playtester walked into the bug -- Maliketh (71300, 2026-07-07), ashen Leyndell, Redmane Castle
(76414/76416, 2026-07-11: the plaza grace sits in the Misbegotten Warrior + Crucible Knight duo arena,
so the Caelid lock warped the player into a live duo fight). That is pinning the symptom. CONTRIBUTING
says derive the datum.

THE PREDICATE
-------------
A region lock force-lights ("grants") every grace in its region so the player can warp in. That is only
safe if the grace's spawn point is somewhere you can safely stand. It is NOT safe if the grace sits
inside a boss arena -- warping there drops you on a live boss.

So:  distance(grace_spawn, nearest boss enemy spawn) < RADIUS   =>   ARENA GRACE, never force-light.

Tile co-location is NOT a usable proxy -- 172 granted graces share a map/tile with a boss (all seven
Stormveil graces sit on Godrick's tile). It over-matches ~5x. Only the distance works.

SOURCES (all ground truth, no hand lists)
-----------------------------------------
  boss ids   : EMEVD `DisplayBossHealthBar(Enabled, <entity>, ...)` -- the authoritative boss set
               (same oracle as tools/datamine_boss_healthbars.py).
  boss pos   : witchy'd MSB  <map>-msb-dcx/Part/Enemy/*.xml  -> <EntityID> + <Position><X/Y/Z>.
  grace pos  : grace_flags.tsv (BonfireWarpParam) -> warpUnlockFlag, mapTile, posX/posY/posZ.
Both position sets are MAP-LOCAL, so they are directly comparable within a map.

USAGE
  python tools/datamine_arena_graces.py                 # report + write greenfield/arena_graces.tsv
  python tools/datamine_arena_graces.py --radius 45
"""
import argparse
import os
import re
import sys
import glob
import math
import csv
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AR = os.path.join(ROOT, "elden_ring_artifacts")
# TWO directories hold witchy'd MSBs and they are NOT the same set (2026-07-11):
#     elden_ring_artifacts/mapstudio  -> 1034 unpacked  (PARTIAL -- only 66 of the 118 boss maps)
#     elden_ring_artifacts/map        -> 1347 unpacked  (COMPLETE -- 117 of 118)
# I pointed this tool at `mapstudio`, found 52 boss maps "missing", and told Alaric to unpack them --
# they were unpacked the whole time, one directory over. Search BOTH, prefer whichever has the map.
MSB_DIRS = [os.path.join(AR, "map"), os.path.join(AR, "mapstudio")]
EVENT = os.path.join(AR, "event")
OUT = os.path.join(ROOT, "greenfield", "arena_graces.tsv")

# A boss arena is small. Radahn's is the outlier (a whole beach), so a generous default still
# under-reaches there rather than over-reaching into ordinary graces. Tuned so that the three
# KNOWN-BAD graces (71300 Maliketh, 76414/76416 Redmane) are caught and the known-good ones are not.
DEFAULT_RADIUS = 40.0


def _healthbar_bosses():
    """{map_id: {entity}} from the GENERATED greenfield/eldenring/boss_healthbars.py.

    🛑 WHY THIS EXISTS (2026-08-10). The literal sweep below matches
    `DisplayBossHealthBar(Enabled, <id>, ...)` written out in the tile's own EMEVD. **72 of the 231
    bosses are not written that way** -- they are raised through `$InitializeCommonEvent(0, 900058xx,
    <entity>, ...)`, so the literal regex never sees them, and the 70 tiles that hold ONLY such
    bosses never entered `adjudicated_tiles` at all. The Divine Beast Dancing Lion (2046460800,
    m61_46_46) is one: `grep 2046460800` finds 74 EMEVD lines and not one is a literal
    DisplayBossHealthBar, so its arena has never been checked for graces standing in it.

    `datamine_boss_healthbars.py` already resolves BOTH forms; its output is the authoritative set
    and is committed, so this needs no artifacts. Union, never replace -- the literal sweep stays as
    the independent read of the corpus.
    """
    p = os.path.join(ROOT, "greenfield", "eldenring", "boss_healthbars.py")
    out = defaultdict(set)
    if not os.path.isfile(p):
        return out
    src = open(p, encoding="utf-8").read()
    for ent, _grp, tile, _cls, _nm in re.findall(
            r"(\d+):\s*\('([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)'\)", src):
        # boss_healthbars tiles are 3-part overworld (m61_46_46) or 2-part interior (m12_01);
        # EMEVD/MSB names are 4-part.
        n = tile.count("_")
        out[tile + ("_00" if n == 2 else "_00_00" if n == 1 else "")].add(int(ent))
    return out


def boss_ids_by_map():
    """map_id -> {boss entity id}. The authoritative boss set.

    UNION of two reads of the same EMEVD corpus: the literal `DisplayBossHealthBar` sweep, and the
    common-event-aware set resolved by datamine_boss_healthbars. See _healthbar_bosses for why the
    literal sweep alone is a 159-of-231 lower bound.
    """
    out = defaultdict(set)
    for fp in glob.glob(os.path.join(EVENT, "*.emevd.dcx.js")):
        b = os.path.basename(fp).split(".")[0]
        if b.startswith("common"):
            continue
        try:
            t = open(fp, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for m in re.finditer(r"DisplayBossHealthBar\(Enabled,\s*(\d+)", t):
            out[b].add(int(m.group(1)))
    _lit = sum(len(v) for v in out.values())
    for mid, ents in _healthbar_bosses().items():
        out[mid] |= ents
    _tot = sum(len(v) for v in out.values())
    if _tot > _lit:
        print("  boss set: %d from the literal DisplayBossHealthBar sweep, %d after unioning "
              "boss_healthbars (common-event-raised bosses the literal regex cannot see)"
              % (_lit, _tot))
    return out


def enemy_positions(map_id):
    """entity id -> (x, y, z) from the witchy'd MSB Part/Enemy xml."""
    d = next((os.path.join(m, f"{map_id}-msb-dcx", "Part", "Enemy") for m in MSB_DIRS
              if os.path.isdir(os.path.join(m, f"{map_id}-msb-dcx", "Part", "Enemy"))), None)
    if d is None:
        return None                      # MSB not unpacked in EITHER dir -> caller reports UNRESOLVED
    pos = {}
    for fp in glob.glob(os.path.join(d, "*.xml")):
        try:
            t = open(fp, encoding="utf-8-sig", errors="replace").read()
        except OSError:
            continue
        eid = re.search(r"<EntityID>(-?\d+)</EntityID>", t)
        p = re.search(r"<Position>\s*<X>(-?[\d.eE+]+)</X>\s*<Y>(-?[\d.eE+]+)</Y>\s*<Z>(-?[\d.eE+]+)</Z>", t)
        if eid and p and int(eid.group(1)) > 0:
            pos[int(eid.group(1))] = (float(p.group(1)), float(p.group(2)), float(p.group(3)))
    return pos


def graces():
    """[(flag, mapTile, (x,y,z))] from grace_flags.tsv (BonfireWarpParam)."""
    fp = os.path.join(AR, "grace_flags.tsv")
    out = []
    with open(fp, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            try:
                fl = int(row["warpUnlockFlag"])
                p = (float(row["posX"]), float(row["posY"]), float(row["posZ"]))
            except (KeyError, ValueError, TypeError):
                continue
            if fl <= 200:                       # 200 = the BonfireWarpParam default/template row
                continue
            out.append((fl, row["mapTile"], p))
    return out


def dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--radius", type=float, default=DEFAULT_RADIUS)
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    bosses = boss_ids_by_map()
    poscache = {}
    hits, unresolved = [], set()
    adjudicated_tiles = set()      # map_id whose MSB WAS unpacked (the old, per-MAP notion)
    unresolved_bosses = {}         # map_id -> sorted[boss entity with NO MSB Part position]

    for flag, tile, gp in graces():
        # grace_flags mapTile is 3-part (m60_51_36 / m10_00); EMEVD + MSB names are 4-part (…_00).
        cands = [k for k in bosses if k.startswith(tile + "_") or k == tile]
        for map_id in cands:
            if map_id not in poscache:
                poscache[map_id] = enemy_positions(map_id)
            ep = poscache[map_id]
            if ep is None:
                unresolved.add(map_id)
                continue
            adjudicated_tiles.add(map_id)
            # 🛑 PER-BOSS, NOT PER-MAP. `b in ep` silently drops any DisplayBossHealthBar entity that
            # is not an MSB Part/Enemy (script-spawned, or placed under a different EntityID). Before
            # 2026-08-10 that boss just vanished from the distance computation while its map still
            # counted as "adjudicated" -- so a grace standing in its arena came out CLEAN and the
            # header said the derivation had looked. It had not. Record the misses.
            missing = sorted(b for b in bosses[map_id] if b not in ep)
            if missing:
                unresolved_bosses[map_id] = missing
            near = [(dist(gp, ep[b]), b) for b in bosses[map_id] if b in ep]
            if not near:
                continue
            d, b = min(near)
            if d < args.radius:
                hits.append((flag, tile, map_id, b, round(d, 1)))

    hits.sort()
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"# DERIVED arena graces: distance(grace spawn, nearest boss enemy spawn) < {args.radius}m\n")
        f.write("# A region lock force-lights every grace in its region so you can warp in. A grace INSIDE a\n")
        f.write("# boss arena must never be force-lit -- warping there drops you on a live boss.\n")
        f.write("# sources: EMEVD DisplayBossHealthBar + witchy'd MSB Part/Enemy <EntityID>/<Position>\n")
        f.write("#          + grace_flags.tsv. tools/datamine_arena_graces.py\n")
        f.write("#\n")
        f.write("# 🛑 ABSENCE IS NEVER AN ANSWER, AND IT IS PER-BOSS.\n")
        f.write("#   adjudicated_tiles: the map's MSB was unpacked. It does NOT mean every boss on it was\n")
        f.write("#     located -- a DisplayBossHealthBar entity that is not an MSB Part has no position and\n")
        f.write("#     is skipped. Reading 'tile adjudicated + grace absent' as 'measured safe' is the\n")
        f.write("#     2026-08-10 mistake (76931 Shadow Keep Back Gate, in front of Commander Gaius).\n")
        f.write("#   unresolved_bosses: the bosses that had NO position. A grace on one of these tiles is\n")
        f.write("#     UNADJUDICATED for that boss; gen_data's hand list stays LOAD-BEARING for it.\n")
        f.write("# adjudicated_tiles: %s\n" % ",".join(sorted(adjudicated_tiles)))
        f.write("# unresolved_bosses: %s\n"
                % ",".join("%s:%s" % (m, "+".join(str(b) for b in bs))
                           for m, bs in sorted(unresolved_bosses.items())))
        f.write("grace_flag\tmap_tile\tboss_entity\tdistance_m\n")
        for flag, tile, map_id, b, d in hits:
            f.write("%d\t%s\t%d\t%s\n" % (flag, tile, b, d))

    print(f"arena_graces: {len(hits)} grace(s) inside a boss arena (<{args.radius}m) -> {args.out}")
    for flag, tile, map_id, b, d in hits:
        print(f"  grace {flag:<7} {tile:<12} boss {b:<12} {d:>6.1f}m")
    if unresolved:
        print(f"\n  ! {len(unresolved)} map(s) with a boss have NO unpacked MSB -- not adjudicated:")
        print("    " + ", ".join(sorted(unresolved)[:12]) + (" ..." if len(unresolved) > 12 else ""))
        print("    (witchy those .msb.dcx to close the gap)")
    if unresolved_bosses:
        n = sum(len(v) for v in unresolved_bosses.values())
        print(f"\n  ! {n} boss(es) across {len(unresolved_bosses)} ADJUDICATED map(s) have no MSB "
              "Part/Enemy position -- their arenas were NOT measured:")
        for m, bs in sorted(unresolved_bosses.items())[:12]:
            print("    %-12s %s" % (m, ", ".join(str(b) for b in bs)))
        print("    A grace on one of these tiles is UNADJUDICATED. Do NOT retire its hand-list entry.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
