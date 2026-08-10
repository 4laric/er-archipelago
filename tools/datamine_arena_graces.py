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
#
# 🛑 THAT TUNING IS NOW OUT OF DATE (2026-08-10). It was fitted while the boss set was a
# 159-of-231 lower bound that happened to exclude most FIELD bosses. Unioning boss_healthbars added
# 72 of them and the radius immediately over-matched: 41 -> 48 hits, and FIVE of the six new ones
# are graces that should NOT be withheld --
#     76118 Warmaster's Shack        9.0m   Bell Bearing Hunter   (NIGHT-ONLY spawn)
#     76311 Hermit Merchant's Shack 21.6m   Bell Bearing Hunter   (NIGHT-ONLY spawn)
#     76451 Isolated Merchant's Shack 17.4m Bell Bearing Hunter   (NIGHT-ONLY spawn)
#     76357 Primeval Sorcerer Azur  36.8m   Demi-Human Queen Maggie
#     76910 Behind the Fort of Reprimand 19.2m Black Knight Edredd
# Three are MERCHANT SHACKS whose "arena" is an ordinary safe place with a conditional night
# invader. Withholding them costs the player three shops and two travel nodes -- the 76414/76416
# over-skip again, which the note above already calls out as guessing conservatively.
#
# DISTANCE ALONE CANNOT DECIDE A CONDITIONAL SPAWN. Until the predicate can (spawn conditions are
# EMEVD, not MSB), boss_class ships in the table so a human adjudicates rather than the radius.
DEFAULT_RADIUS = 40.0

# Floors. BonfireWarpParam carries 421 warp graces and the committed table holds 41 arena hits;
# both are measured, not guessed. Raise, never lower -- a drop is a finding, not a rebaseline.
MIN_GRACES = 400
MIN_HITS = 41


def _boss_meta():
    """{entity: (class, name)} from the generated boss_healthbars module."""
    p = os.path.join(ROOT, "greenfield", "eldenring", "boss_healthbars.py")
    if not os.path.isfile(p):
        return {}
    return {int(e): (c, n) for e, _g, _t, c, n in re.findall(
        r"(\d+):\s*\('([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)'\)",
        open(p, encoding="utf-8").read())}


_BOSS_META = _boss_meta()


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
    """[(flag, mapTile, (x,y,z))] straight from BonfireWarpParam.csv.

    🛑 THIS USED TO READ `elden_ring_artifacts/grace_flags.tsv` AND THAT WAS A TRAP (2026-08-10).
    Two different files carry that name:

      greenfield/grace_flags.tsv   TRACKED. warpUnlockFlag/mapTile/subCategory/placeName -- NO
                                   COORDINATES. Copy it into the artifacts tree, as the obvious
                                   fix suggests, and every row dies on `float(row["posX"])`.
      elden_ring_artifacts/...     a BonfireWarpParam dump that is NOT in the gen_inputs bundle,
                                   so a clean `--extract` tree does not have it at all.

    Either way `except (KeyError, ValueError, TypeError): continue` swallowed it PER ROW, the grace
    list came out empty, and the tool wrote a ZERO-ROW arena_graces.tsv -- disarming the arena-grace
    skip set with one cheerful line of output.

    BonfireWarpParam.csv IS bundled, IS the param grace_flags.tsv is lifted from, and carries the
    positions. Read the source, not a copy of a copy.
    """
    fp = os.path.join(AR, "vanilla_er", "vanilla_er", "BonfireWarpParam.csv")
    if not os.path.isfile(fp):
        raise SystemExit(
            "FATAL: %s missing. Extract the bundle first:\n"
            "    python tools/gen_inputs.py --extract elden_ring_artifacts" % fp)
    out = []
    with open(fp, encoding="utf-8-sig", newline="") as f:
        rdr = csv.DictReader(f)
        need = {"eventflagId", "bonfireEntityId", "areaNo", "gridXNo", "gridZNo",
                "posX", "posY", "posZ"}
        gone = need - set(rdr.fieldnames or ())
        if gone:
            raise SystemExit(
                "FATAL: %s is missing column(s) %s. Refusing to swallow that per row -- an empty "
                "grace list writes a table that turns the arena-grace protection OFF."
                % (fp, sorted(gone)))
        for row in rdr:
            try:
                fl = int(row["eventflagId"])
                p = (float(row["posX"]), float(row["posY"]), float(row["posZ"]))
            except (TypeError, ValueError):
                continue
            if not (71000 <= fl <= 76999):     # the warp-grace flag group; skips the template row
                continue
            a = int(row["areaNo"] or 0)
            if a in (60, 61):
                tile = "m%d_%02d_%02d" % (a, int(row["gridXNo"]), int(row["gridZNo"]))
            else:                               # interior: the entity id encodes mAA_BB
                ent = str(row["bonfireEntityId"] or "")
                tile = "m%s_%s" % (ent[0:2], ent[2:4]) if len(ent) == 8 else "?"
            out.append((fl, tile, p))
    return out


def dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--radius", type=float, default=DEFAULT_RADIUS)
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    _graces = graces()
    bosses = boss_ids_by_map()
    poscache = {}
    hits, unresolved, _seen = [], set(), {}
    adjudicated_tiles = set()      # map_id whose MSB WAS unpacked (the old, per-MAP notion)
    unresolved_bosses = {}         # map_id -> sorted[boss entity with NO MSB Part position]

    for flag, tile, gp in _graces:
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
                # dedupe: the _00 and _10 MSB variants of a tile are the SAME arena, and listing a
                # grace twice (76120 did, 2026-08-10) inflates the count the FLOOR is measured on.
                k = (flag, b)
                if k not in _seen or d < _seen[k][4]:
                    _seen[k] = (flag, tile, map_id, b, round(d, 1))

    # 🛑 ABSENCE IS NEVER AN ANSWER -- and this tool emitted a ZERO-ROW table on 2026-08-10 without
    # a word. graces() reads elden_ring_artifacts/grace_flags.tsv and swallows a column mismatch per
    # row (`except KeyError: continue`), so the wrong copy of that file yields an empty grace list,
    # zero hits, and a written table that turns the whole arena-grace protection OFF. Two floors:
    if len(_graces) < MIN_GRACES:
        raise SystemExit(
            "FATAL: graces() returned %d grace(s) (floor %d). %s is missing, truncated, or has "
            "different columns -- every row is being swallowed by the per-row except. Refusing to "
            "write a table that would silently disable the arena-grace skip set."
            % (len(_graces), MIN_GRACES, os.path.join(AR, "grace_flags.tsv")))
    # 🛑 MATERIALISE BEFORE MEASURING. This read len(hits) while the loop above filled _seen, so the
    # floor measured an empty list and FATAL'd on a run that had found 47 (2026-08-10). The floor was
    # right to fire -- it just fired at its own author. Keep the assignment ABOVE the check.
    hits = sorted(_seen.values())
    if len(hits) < MIN_HITS:
        raise SystemExit(
            "FATAL: only %d grace(s) came out inside an arena (floor %d, and the committed table "
            "has 41). The MSBs or the boss set collapsed. A SHRUNK arena_graces.tsv silently "
            "re-grants graces that stand in live boss arenas -- fail instead of emitting."
            % (len(hits), MIN_HITS))
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
        f.write("# boss_class is carried so a human can adjudicate: a `field` boss may be a\n")
        f.write("#   CONDITIONAL spawn (Bell Bearing Hunter is night-only) whose 'arena' is an\n")
        f.write("#   ordinary, safe, permanently-useful grace. Distance alone cannot tell those\n")
        f.write("#   from a real arena grace -- see the 2026-08-10 note in the tool docstring.\n")
        f.write("grace_flag\tmap_tile\tboss_entity\tboss_class\tboss_name\tdistance_m\n")
        for flag, tile, map_id, b, d in hits:
            _c, _n = _BOSS_META.get(b, ("?", "?"))
            f.write("%d\t%s\t%d\t%s\t%s\t%s\n" % (flag, tile, b, _c, _n, d))

    print(f"arena_graces: {len(hits)} grace(s) inside a boss arena (<{args.radius}m) -> {args.out}")
    for flag, tile, map_id, b, d in hits:
        _c, _n = _BOSS_META.get(b, ("?", "?"))
        print(f"  grace {flag:<7} {tile:<12} boss {b:<12} {d:>6.1f}m  {_c:<9} {_n}")
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
