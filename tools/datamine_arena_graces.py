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
MAPSTUDIO = os.path.join(AR, "mapstudio")
EVENT = os.path.join(AR, "event")
OUT = os.path.join(ROOT, "greenfield", "arena_graces.tsv")

# A boss arena is small. Radahn's is the outlier (a whole beach), so a generous default still
# under-reaches there rather than over-reaching into ordinary graces. Tuned so that the three
# KNOWN-BAD graces (71300 Maliketh, 76414/76416 Redmane) are caught and the known-good ones are not.
DEFAULT_RADIUS = 40.0


def boss_ids_by_map():
    """map_id -> {boss entity id}. From the authoritative DisplayBossHealthBar EMEVD sweep."""
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
    return out


def enemy_positions(map_id):
    """entity id -> (x, y, z) from the witchy'd MSB Part/Enemy xml."""
    d = os.path.join(MAPSTUDIO, f"{map_id}-msb-dcx", "Part", "Enemy")
    if not os.path.isdir(d):
        return None                      # MSB not unpacked -> caller reports as UNRESOLVED
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
            near = [(dist(gp, ep[b]), b) for b in bosses[map_id] if b in ep]
            if not near:
                continue
            d, b = min(near)
            if d < args.radius:
                hits.append((flag, tile, map_id, b, round(d, 1)))

    hits.sort()
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"# ARENA GRACES -- derived: distance(grace, nearest boss enemy spawn) < {args.radius}m\n")
        f.write("# sources: EMEVD DisplayBossHealthBar (boss set) + witchy'd MSB Part/Enemy (positions)\n")
        f.write("#          + grace_flags.tsv (BonfireWarpParam grace positions). NO hand lists.\n")
        f.write("grace_flag\tmap_tile\tmap_id\tboss_entity\tdistance_m\n")
        for h in hits:
            f.write("\t".join(str(x) for x in h) + "\n")

    print(f"arena_graces: {len(hits)} grace(s) inside a boss arena (<{args.radius}m) -> {args.out}")
    for flag, tile, map_id, b, d in hits:
        print(f"  grace {flag:<7} {tile:<12} boss {b:<12} {d:>6.1f}m")
    if unresolved:
        print(f"\n  ! {len(unresolved)} map(s) with a boss have NO unpacked MSB -- not adjudicated:")
        print("    " + ", ".join(sorted(unresolved)[:12]) + (" ..." if len(unresolved) > 12 else ""))
        print("    (witchy those .msb.dcx to close the gap)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
