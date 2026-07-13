#!/usr/bin/env python3
"""PlayRegionParam -> the play_region BUCKET table. The ground truth for kick-watch geometry.

WHY THIS EXISTS
---------------
`region_groups.py` sourced its buckets from `BonfireWarpParam.bonfireSubCategoryId`, on the written
claim that it "equals the runtime play_region_id (verified against every empirically captured id)".
It does not. It happens to coincide for the base overworld, and it is simply a different number in the
DLC:

    Gravesite:  bonfireSubCategoryId = 6800
                runtime play_region  = 6800000   ->  bucket (pr / 100) = 68000

The client compares `play_region_id / 100` against those buckets, so every DLC bucket missed. Three
things failed at once, none of them loudly: the DLC region KICK never fired (you could walk into a
sealed DLC region and loot it), the Scadutree blessing FLOOR never matched, and DLC enemy scaling sat
at its floor tier. All three are "correct behaviour on absent data".

The caveat in that docstring was true and vacuous: no DLC id had ever been captured, because nobody had
played the DLC.

**`PlayRegionParam` is the authority.** Its row IDs ARE the play_region ids -- that is what the game
puts in `WorldChrMan.main_player.play_region_id`. So:

    bucket = PlayRegionParam.ID // 100
    tile   = (areaNo, gridXNo, gridZNo)  ->  mAA_BB_CC

and a bucket belongs to whichever apworld region owns the checks on its tiles.

This tool re-derives the WHOLE table, base included -- the base half is wrong too, it just got away with
it. `Limgrave [61000, 61001]`: 61000 is real, **61001 does not exist**. Every region's primary bucket
happened to be right, so KICK matched on that and the phantoms were inert. Same rot, different luck.

Usage:
    python tools/datamine_play_regions.py           # report + diff against region_groups.py
    python tools/datamine_play_regions.py --write   # rewrite greenfield/region_groups.py's table
"""
from __future__ import annotations

import argparse
import ast
import collections
import csv
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AR = os.path.join(REPO, "elden_ring_artifacts")
PARAM = os.path.join(AR, "vanilla_er", "vanilla_er", "PlayRegionParam.csv")

# PlayRegionParam column names (read by NAME, never by index -- the whole bug upstream of this tool was
# a value read out of the wrong column).
C_ID, C_AREA, C_GX, C_GZ = "ID", "areaNo", "gridXNo", "gridZNo"


def load_play_regions():
    """{bucket: {tile, ...}} from PlayRegionParam. Rows with no tile (areaNo 0) still define a bucket;
    they are sub-regions of it (interiors, arenas) and carry no coordinates."""
    if not os.path.isfile(PARAM):
        sys.exit(f"PlayRegionParam not found: {PARAM}\n"
                 f"This tool needs the game-data artifacts; it cannot run in CI.")
    buckets = collections.defaultdict(set)
    seen = 0
    with open(PARAM, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                rid = int(row[C_ID])
            except (KeyError, ValueError):
                continue
            seen += 1
            bucket = rid // 100
            try:
                a, x, z = int(row[C_AREA]), int(row[C_GX]), int(row[C_GZ])
            except (KeyError, ValueError):
                a = 0
            if a:
                buckets[bucket].add((a, "m%02d_%02d_%02d" % (a, x, z)))
            else:
                buckets[bucket]  # bucket exists, no tile (interior/arena sub-region)
    print(f"PlayRegionParam: {seen} rows -> {len(buckets)} distinct play_region buckets")
    return buckets


def load_tile_regions():
    """{tile: region} -- the apworld's OWN region for each map tile.

    Joined by ap_id: region_map.csv gives ap_id -> map, and the GENERATED eldenring/data.py gives
    region -> ap_ids. We must use the generated data, not region_map.csv's `region` column: that column
    still reads 'Land of Shadow (DLC)' for every m61 tile -- a placeholder, not a place -- which is
    exactly the mis-regioning already fixed downstream. Majority vote per tile.
    """
    # Load data.py BY PATH, not as `eldenring.data`. Importing the package runs eldenring/__init__.py
    # -> core.py -> `from BaseClasses import ...`, i.e. it needs an Archipelago checkout on sys.path --
    # which a datamine tool has no business requiring. data.py is generated and imports nothing, so a
    # direct file load is both sufficient and honest about the dependency.
    import importlib.util

    dp = os.path.join(REPO, "greenfield", "eldenring", "data.py")
    spec = importlib.util.spec_from_file_location("_gf_data", dp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    LOCATIONS = mod.LOCATIONS

    # JOIN ON THE FLAG, not the ap_id. ap-ids are POSITIONAL and have been renumbered: data.py is in the
    # 777xxxx space while region_map.csv still carries 700xxxx, and the two sets do not intersect at all
    # (a zero-overlap join that reports "0 buckets attributed" and looks like a clean run). The
    # acquisition flag is the durable key -- 4813 of 4844 locations carry one and it survives renumbering.
    flag_region = {}
    for region, locs in LOCATIONS.items():
        for entry in locs:
            flag = entry[2]
            if flag:
                flag_region[int(flag)] = region

    votes = collections.defaultdict(collections.Counter)
    with open(os.path.join(REPO, "greenfield", "region_map.csv"), encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            f = (row.get("flag") or "").strip()
            if not f.isdigit():
                continue
            reg = flag_region.get(int(f))
            m = row.get("map") or ""
            if not reg or not m.startswith("m"):
                continue
            tile = "_".join(m.split("_")[:3])
            votes[tile][reg] += 1

    if not votes:
        sys.exit("tile->region join produced NOTHING -- the key drifted again. Refusing to report an "
                 "empty diff as if it were a clean one.")
    tiles = {t: c.most_common(1)[0][0] for t, c in votes.items()}
    # mAA_BB keying too, for the interior decode (a dungeon's bucket names its map, not a tile).
    mvotes = collections.defaultdict(collections.Counter)
    for t, r in ((t, c.most_common(1)[0][0]) for t, c in votes.items()):
        mvotes["_".join(t.split("_")[:2])][r] += 1
    maps = {m: c.most_common(1)[0][0] for m, c in mvotes.items()}
    print(f"tile->region: {len(tiles)} tiles / {len(maps)} maps attributed "
          f"from {len(flag_region)} flagged locations")
    return tiles, maps


def current_groups():
    src = open(os.path.join(REPO, "greenfield", "region_groups.py"), encoding="utf-8").read()
    m = re.search(r"REGION_GROUPS\s*=\s*(\{.*?\n\})", src, re.S)
    if not m:
        sys.exit("could not find REGION_GROUPS in greenfield/region_groups.py")
    # REGION_GROUPS is {region: (bucket, ...)} -- invert it to {bucket: region}. (Parsed with a regex
    # rather than ast.literal_eval because the literal contains named constants.)
    out = {}
    # NB the quote class must BACK-REFERENCE, not alternate: "Charo's" contains an apostrophe, and a
    # naive ["']([^"']+)["'] truncates it to 's'. (It did. Caught in a dry run.)
    for _q, name, tup in re.findall(r"([\"'])(.+?)\1\s*:\s*\(([^)]*)\)", m.group(1)):
        for b in re.findall(r"\d+", tup):
            out[int(b)] = name
    if not out:
        sys.exit("parsed ZERO buckets out of REGION_GROUPS -- the shape changed. Refusing to report "
                 "every bucket as 'missing' off a broken parse.")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="rewrite region_groups.py's REGION_GROUPS")
    args = ap.parse_args()

    buckets = load_play_regions()
    tiles, maps = load_tile_regions()
    cur = current_groups()

    # ATTRIBUTION. Two different geometries, and conflating them is what made my first pass call the
    # tutorial chapel "Gravesite".
    #
    #   OVERWORLD (a row whose areaNo is 60 or 61): the row's areaNo/gridXNo/gridZNo IS the tile the
    #     player stands on. Majority-vote the bucket's tiles.
    #   INTERIOR (everything else): the coordinates are the dungeon's WARP/ENTRY point ON THE OVERWORLD,
    #     so they name the neighbouring region, not this one -- that is why the naive join said Leyndell
    #     (11000) was "Altus" and Raya Lucaria (14000) was "Liurnia". Our table was RIGHT and the tool
    #     was wrong. The bucket ID itself carries the map (11000 -> m11_00, 30030 -> m30_03), which is
    #     exact, so decode it and join on the map instead.
    derived = {}
    unattributed = []
    for bucket, rows in sorted(buckets.items()):
        overworld = [t for (a, t) in rows if a in (60, 61)]
        if overworld:
            regs = collections.Counter(tiles[t] for t in overworld if t in tiles)
        else:
            mp = "m%02d_%02d" % (bucket // 1000, (bucket % 1000) // 10)
            regs = collections.Counter([maps[mp]] if mp in maps else [])
        if regs:
            derived[bucket] = regs.most_common(1)[0][0]
        else:
            unattributed.append((bucket, sorted(t for (_a, t) in rows)))

    print()
    print("== BUCKETS THE GAME HAS THAT WE DO NOT (kick never fires here) ==")
    missing = [b for b in derived if b not in cur]
    for b in sorted(missing):
        print(f"   {b:>7}  -> {derived[b]}")
    if not missing:
        print("   (none)")

    print()
    print("== BUCKETS WE CLAIM THAT THE GAME DOES NOT HAVE (phantoms, inert) ==")
    phantom = [b for b in cur if b not in buckets]
    for b in sorted(phantom):
        print(f"   {b:>7}  we say {cur[b]!r}")
    if not phantom:
        print("   (none)")

    print()
    print("== BUCKETS WHERE WE DISAGREE ON THE REGION ==")
    disagree = [b for b in derived if b in cur and cur[b] != derived[b]]
    for b in sorted(disagree):
        print(f"   {b:>7}  we say {cur[b]!r}  ->  tiles say {derived[b]!r}")
    if not disagree:
        print("   (none)")

    if unattributed:
        print()
        print("== BUCKETS WITH NO ATTRIBUTABLE TILE (left alone, NOT guessed) ==")
        for b, ts in unattributed:
            print(f"   {b:>7}  tiles={ts or '(none -- interior/arena sub-region)'}")

    print()
    print(f"summary: game has {len(buckets)} buckets; we list {len(cur)}; "
          f"{len(missing)} missing, {len(phantom)} phantom, {len(disagree)} mis-assigned")

    print()
    print("== PROPOSED REGION_GROUPS (measured; review before trusting) ==")
    by_region = collections.defaultdict(list)
    for b, r in derived.items():
        by_region[r].append(b)
    for r in sorted(by_region):
        print("    %-30r %s," % (r, tuple(sorted(by_region[r]))))

    if args.write:
        sys.exit("--write is not implemented yet on purpose: review the diff above first. "
                 "A table this load-bearing does not get rewritten by a tool nobody has read the output of.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
