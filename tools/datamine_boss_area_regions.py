#!/usr/bin/env python3
r"""datamine_boss_area_regions.py -- PlayRegionParam BOSS-AREA rows -> the region you are STANDING in
when you kill a boss (and therefore where its reward is REACHABLE).

WHY THIS EXISTS (Alaric, playtest 2026-07-21)
---------------------------------------------
The Golden Hippopotamus (defeat flag 21000850) is fought just inside the Shadow Keep Main Gate. Its
reward (flag 510440: Aspects of the Crucible: Thorns + a Scadutree Fragment) is attributed by
`datamine_msb_item_regions.py` to the boss's emevd map `m21_00`, and `m21_00 -> Shadow Keep`. But the
LIVE fight is not on Shadow Keep ground: while the Hippo is alive the player's runtime `play_region_id`
is PlayRegionParam row 6900010 -- a BOSS-ALIVE overlay in bucket 69000 = **Scadu Altus**. Holding ONLY
the Shadow Keep lock, Alaric was KICKED before he could reach the fight; a Shadow Keep drop is
UNREACHABLE. You must own Scadu Altus to kill the Hippo, so its drop belongs to Scadu Altus.

This is not a Hippo special-case: it is a GENERAL fact of the boss-area geometry. `PlayRegionParam`
encodes, for every gated boss, the play_region the player occupies during the fight:

    pcPositionSaveLimitEventFlagId  = the boss DEFEAT flag that gates this row (e.g. 21000850)
    ID                              = the runtime play_region_id the client reports for that row
    bucket = ID // 100              = the value the kick-watch compares play_region_id/100 against
    bossAreaId                      = the BASE play-region the boss-alive overlay belongs to
                                      (6900010.bossAreaId == 6900000, the always-on Scadu Altus base;
                                       for interior boss rooms bossAreaId is the boss flag itself and
                                       is NOT a play_region id -- so bucket is taken from ID, never
                                       from bossAreaId).

So the derivation is: for every PlayRegionParam row whose pcPositionSaveLimitEventFlagId is a boss
defeat flag, bucket = ID//100, and region = the apworld region that OWNS that bucket in
region_groups.PLAY_REGION_GROUPS (the same MEASURED play_region->region spine the kick uses). A boss
whose bucket is owned by its own map's region (nearly all of them -- an interior boss room's bucket IS
its dungeon map) produces region == map default and moves nothing; only a boss whose arena bucket is a
FOREIGN play_region (the Hippo's 69000 vs m21_00's 21000) is corrected downstream.

This tool DERIVES and REPORTS; gen_data consumes the tsv. It does not know about item rewards -- the
reward-flag -> defeat-flag link is boss_reward_lots.py's job (BOSS_REWARD_DEFEAT). Keeping this a pure
PlayRegionParam read makes it an independent, auditable ground-truth source.

`--emit` writes greenfield/boss_area_regions.tsv (TRACKED, tier-2: run by hand, commit the tsv, THEN
gen_data picks it up -- see AGENTS.md §5a):
    defeat_flag \t bucket \t region

Usage:
    python tools/datamine_boss_area_regions.py            # report + write nothing
    python tools/datamine_boss_area_regions.py --emit     # also write greenfield/boss_area_regions.tsv
    python tools/datamine_boss_area_regions.py --param P   # read PlayRegionParam.csv from P
"""
from __future__ import annotations

import argparse
import collections
import csv
import importlib.util
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AR = os.path.join(REPO, "elden_ring_artifacts")
PARAM = os.path.join(AR, "vanilla_er", "vanilla_er", "PlayRegionParam.csv")
ARTIFACT = os.path.join(REPO, "greenfield", "boss_area_regions.tsv")

# Read by NAME, never index (the upstream play_region bug was a value read from the wrong column).
C_ID, C_FLAG, C_BOSSAREA = "ID", "pcPositionSaveLimitEventFlagId", "bossAreaId"

# Ambient/non-boss values seen in pcPositionSaveLimitEventFlagId on the always-on overworld rows.
# Real boss/dungeon defeat flags are all >= 8 digits (e.g. 10000800, 21000850); the ambient markers
# are the tiny ones (0, 6000, 6001). A >= 7-digit floor separates them with room to spare and is
# robust to an unknown ambient marker showing up after a patch.
_MIN_DEFEAT_FLAG = 1_000_000

# The game has ~130 boss-area rows. Far fewer means a truncated/filtered CSV; reporting off one would
# call real boss areas phantom -- refuse instead (mirrors datamine_play_regions.MIN_BUCKETS).
MIN_BOSS_ROWS = 100


def fail(msg):
    sys.exit("datamine_boss_area_regions: FATAL: %s" % msg)


def load_module(path, name):
    if not os.path.isfile(path):
        fail("%s not found" % path)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def bucket_region_map():
    """{bucket:int -> region} inverted from region_groups.PLAY_REGION_GROUPS (imported by path; it
    imports nothing). This is the MEASURED play_region->region spine, the same one the kick uses."""
    rg = load_module(os.path.join(REPO, "greenfield", "region_groups.py"), "_gf_region_groups")
    out = {}
    for region, buckets in rg.PLAY_REGION_GROUPS.items():
        for b in buckets:
            if b in out and out[b] != region:
                fail("PLAY_REGION_GROUPS assigns bucket %d to both %r and %r." % (b, out[b], region))
            out[int(b)] = region
    if not out:
        fail("PLAY_REGION_GROUPS is empty.")
    return rg, out


def load_boss_rows(param):
    """{defeat_flag -> {bucket, ...}} from PlayRegionParam boss-area rows. Hard-fails on a missing
    column or a degenerate row count."""
    if not os.path.isfile(param):
        fail("PlayRegionParam not found: %s\nThis tool needs the game-data artifacts; it cannot run "
             "in CI." % param)
    flag_buckets = collections.defaultdict(set)
    seen = 0
    with open(param, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        missing = [c for c in (C_ID, C_FLAG, C_BOSSAREA) if c not in (rd.fieldnames or [])]
        if missing:
            fail("PlayRegionParam.csv lacks column(s) %s -- header is %r. A renamed column must fail "
                 "HERE, not read as empty data downstream." % (missing, rd.fieldnames))
        for row in rd:
            try:
                rid = int(row[C_ID])
                flag = int(row[C_FLAG])
            except (TypeError, ValueError):
                continue
            if flag < _MIN_DEFEAT_FLAG:
                continue
            seen += 1
            flag_buckets[flag].add(rid // 100)
    if len(flag_buckets) == 0:
        fail("no boss-area rows parsed (pcPositionSaveLimitEventFlagId always < %d)." % _MIN_DEFEAT_FLAG)
    if seen < MIN_BOSS_ROWS:
        fail("only %d boss-area rows parsed; the game has ~130. Truncated or filtered CSV -- a report "
             "off this would call real boss areas phantom." % seen)
    print("PlayRegionParam: %d boss-area rows -> %d distinct boss defeat flags" % (seen, len(flag_buckets)))
    return flag_buckets


def derive(param):
    """[(defeat_flag, bucket_str, region)], plus contested/unowned reports. A flag whose rows span
    buckets owned by >1 region is CONTESTED and not emitted (nobody guesses which arena is 'the'
    arena); a flag whose bucket(s) no region owns is UNOWNED (falls through to map-truth downstream,
    exactly as today)."""
    rg, b2r = bucket_region_map()
    flag_buckets = load_boss_rows(param)
    rows, contested, unowned = [], [], []
    for flag in sorted(flag_buckets):
        buckets = sorted(flag_buckets[flag])
        regions = {b2r.get(b) for b in buckets}
        owned = {r for r in regions if r is not None}
        if not owned:
            unowned.append((flag, buckets))
            continue
        if len(owned) > 1:
            contested.append((flag, buckets, sorted(owned)))
            continue
        region = next(iter(owned))
        # bucket column: the owned bucket(s) that carry the region (drop any unowned strays).
        bstr = ";".join(str(b) for b in buckets if b2r.get(b) == region)
        rows.append((flag, bstr, region))
    return rg, rows, contested, unowned


def emit_artifact(path, rows):
    lines = [
        "# AUTO-GENERATED by tools/datamine_boss_area_regions.py --emit -- DO NOT EDIT.",
        "# The region the player STANDS IN while killing a boss (= where its reward is REACHABLE),",
        "#   from PlayRegionParam boss-area rows: for a row whose pcPositionSaveLimitEventFlagId is a",
        "#   boss DEFEAT flag, bucket = ID // 100, region = the PLAY_REGION_GROUPS owner of that bucket.",
        "# gen_data consults this ABOVE the msb map-truth branch: a boss-reward flag (via",
        "#   boss_reward_lots.BOSS_REWARD_DEFEAT: reward_flag -> defeat_flag) whose arena region differs",
        "#   from its emevd map's region is re-homed to the arena region (the Golden Hippopotamus:",
        "#   510440 -> 21000850 -> bucket 69000 = Scadu Altus, not m21_00 = Shadow Keep).",
        "# TRACKED (tier-2, AGENTS.md §5a): regenerate after a game patch, commit WITH the region_groups",
        "#   changes it depends on. Most rows equal the boss's own map region and move nothing.",
        "defeat_flag\tbucket\tregion",
    ]
    for flag, bstr, region in rows:
        lines.append("%d\t%s\t%s" % (flag, bstr, region))
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\nemitted %s (%d boss-area flags)." % (path, len(rows)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--param", default=PARAM, help="path to PlayRegionParam.csv")
    ap.add_argument("--emit", nargs="?", const=ARTIFACT, default=None, metavar="PATH",
                    help="write the boss-area region table (default %s)" % ARTIFACT)
    args = ap.parse_args()

    rg, rows, contested, unowned = derive(args.param)
    b2r = {int(b): reg for reg, bs in rg.PLAY_REGION_GROUPS.items() for b in bs}

    print("resolved: %d boss-area flags -> region" % len(rows))
    if contested:
        print("\n== CONTESTED (rows span >1 region; NOT emitted) ==")
        for flag, buckets, regs in contested:
            print("   flag %-12d buckets %s -> %s" % (flag, buckets, regs))
    if unowned:
        print("\n== UNOWNED (no region owns the bucket; falls through to map-truth, as today) ==")
        for flag, buckets in unowned:
            print("   flag %-12d buckets %s" % (flag, buckets))

    # Advisory only (gen_data does the authoritative reward-vs-map comparison): a boss whose defeat
    # flag SELF-ENCODES an interior map (AABBnnnn, AA in 10..59) but whose arena bucket is owned by a
    # DIFFERENT region. Overworld defeat flags (10-/20- prefixed) stand on the tile they encode, so
    # their arena is never foreign -- they are not candidates and are skipped here.
    print("\n== FLAGS WHOSE ARENA REGION IS FOREIGN TO THE FLAG'S OWN INTERIOR MAP (advisory) ==")
    moved = 0
    for flag, bstr, region in rows:
        s = str(flag)
        if not (len(s) == 8 and 10 <= int(s[0:2]) < 60):   # interior-encoded flags only
            continue
        map_region = b2r.get(int(s[0:4] + "0"))            # mAA_BB -> bucket AABB0 -> owner
        if map_region and map_region != region:
            moved += 1
            print("   flag %-12d arena=%-16r  map m%s_%s = %r"
                  % (flag, region, s[0:2], s[2:4], map_region))
    if not moved:
        print("   (none)")

    if args.emit:
        emit_artifact(args.emit, rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
