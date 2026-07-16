"""region_groups.py -- THE region spine: play_region bucket -> apworld region (single source).

Every fact of the form "play_region X belongs to region R" lives HERE and only here. Consumers:
  * greenfield/gen_data.py           -- check regioning (PLAY2AP), grace bundles, open flags, and
                                        the generated eldenring/region_play_ids.py (the inverse,
                                        which features/area_locks.py and the client's baked
                                        region_locks.rs are built from);
  * tools/datamine_dungeon_regions.py -- interior map -> region (grace join);
  * tools/map_region_oracle.py        -- the provenance-oracle fold table.
The repo was repeatedly bitten by hand copies of this map drifting apart (area_locks.REGION_PLAY_IDS
vs gen_data.PLAY2AP vs the oracle's PLAY_REGION_TO_GF); they now all import this table or a module
generated from it.

WHAT A BUCKET IS. `BonfireWarpParam.bonfireSubCategoryId` -- the game's own warp-menu grouping --
equals the runtime play_region_id the client's kick-watch sees (verified against every empirically
captured id; see elden_ring_artifacts/REGION_ID_MAP.md, the authoritative 55-bucket doc). The game
has 54 explorable buckets (+ id 0 system warps and 10010, an empty placeholder). A region is a SET
of buckets; the kick-watch can gate exactly at bucket granularity, no finer.

NAMES (bedrock interop, 2026-07-12). The client enforces a foreign apworld's region locks by
matching its lock ITEM NAMES against "<Region> Lock" over these region names (er-logic
region_locks.rs baked table). Bedrock's apworld is the one shipping such locks, and Alaric agreed
to adopt his region names where he has one; ours are kept where he has none. That is why several
names are terse ("Weeping", "Ensis", "Ancient Ruins") and why "Enir Ilim" drops the game's own
hyphen -- his lock item is literally "Enir Ilim Lock". NOT adopted (documented in
SPEC-region-spine-v2.md): "Redmane" (Redmane Castle has no bucket of its own -- it is m60 tiles
inside 64000), "Volcano" (bucket 16000 exists but the Manor sits ON Mt. Gelmir; one region),
"Ashen" (post-burn Leyndell, 11050: never rollable, but since 2026-07-14 its checks are the
CONDITIONAL finale region -- data.FINALE_REGION, created per-seed by features/finale.py -- whose
kick geometry stays measured under Leyndell here), and his three "* Underground Lock"s (their grouping does
not map onto the game's seven underground buckets; we keep bucket-true regions instead).

UN-GATEABLE FOLDS (measured 2026-07-12; the kick-watch works on play_region, so a place that
shares a bucket with its parent CANNOT be separately gated -- do not invent a mechanism):
  * Ellac River     (graces 76812 @ m61_47_43, 76830 @ m61_47_41) -> bucket 6800 = Gravesite Plain;
  * Recluses' River (graces 76917 @ m61_50_45, 76918 @ m61_50_44) -> bucket 6900 = Scadu Altus
    (6900 also holds Fog Rift Fort, per REGION_ID_MAP.md "Shared buckets").
Bedrock's "Ellac Lock" / "Recluses' Lock" therefore have no enforceable geometry here.

DELIBERATE SPANS (one region, several buckets -- each earns its line):
  * Limgrave = 61000 + 61001 (Stormhill IS Limgrave) + 18000 (Stranded Graveyard / Chapel of
    Anticipation, the tutorial; its graces ride Limgrave's bundle so the Chapel stays warpable);
  * Liurnia = 62000/62001/62002 (core / Bellum Highway / Moonlight Altar) + 39200 (Ruin-Strewn
    Precipice -- entered from the Liurnia ravine; its grace join already filed m39_20 under
    Liurnia before this table existed);
  * Altus = 63000/63002/63003 (core / W. Altus-Outskirts / E. Altus-Forbidden Lands);
  * Mt. Gelmir = 63001 + 16000 (Volcano Manor interior -- the Manor sits on Gelmir);
  * Leyndell = 11000 + 11050 (Ashen Capital: kick bucket of the conditional finale region, see
    above) + 19000 (Fractured Marika, the capital-ending arena) -- the GOAL region;
  * Caelid = 64000 + 64001 (Dragonbarrow) + 64002 (Swamp of Aeonia);
  * Mountaintops of the Giants = 65000 + 65001 + 65002 (Consecrated Snowfield fold: keeps Fire
    Giant as the region's major; a split Snowfield would have no MajorBoss check);
  * Haligtree = 15000 (Elphael) + 15001 (Miquella's Haligtree proper);
  * Ainsel River = 12010 + 12011 (Lake of Rot) + 12012 (Ainsel Depths / Astel) -- one descent;
  * Siofra River = 12020 (Siofra / Nokron) + 12070 (Siofra Bank / Worshippers' Woods);
  * Jagged Peak = 6850 + 6851 (Foot of the Jagged Peak / Dragon Communion Altar);
  * Abyssal = 6860 + 28000 (Midra's Manse, the woods' interior);
  * Shadow Keep = 21000 + 21001 (Church District) + 21010 (Storehouse).
Scaduview (6920, the Hinterland) is deliberately its OWN region now (the Cathedral of Manus Metyr is
NOT part of it -- m25's grace 72500 -> 6900 = Scadu Altus; corrected 2026-07-13 matt-diff):
the old "fold into Shadow Keep, only reachable through the Keep" reasoning predates region locks
lighting a region's whole grace bundle -- with its own lock its graces make it warp-reachable, and
folding it in would have made a back-exit grace the Keep's numerically-first overworld front door.
"""

# region -> play_region buckets. Region names are the datapackage-visible region names; the HUB
# entry is the always-open Roundtable Hold (never a spoke, never gated).
HUB = "Roundtable Hold"

REGION_GROUPS = {
    # --- base game overworld ---
    "Limgrave": (61000, 61001, 18000),
    "Weeping": (61002,),
    "Liurnia": (62000, 62001, 62002, 39200),
    "Altus": (63000, 63002, 63003),
    "Mt. Gelmir": (63001, 16000),
    "Caelid": (64000, 64001, 64002),
    "Mountaintops of the Giants": (65000, 65001, 65002),
    # --- base game legacy / interiors ---
    "Stormveil": (10000,),
    "Raya Lucaria Academy": (14000,),
    "Leyndell": (11000, 11050, 19000),
    "Sewer": (35000,),
    "Haligtree": (15000, 15001),
    "Farum Azula": (13000,),
    # --- base game underground ---
    "Ainsel River": (12010, 12011, 12012),
    "Siofra River": (12020, 12070),
    "Deeproot Depths": (12030,),
    "Mohgwyn": (12050,),
    # --- DLC (Shadow of the Erdtree) ---
    "Gravesite": (6800,),          # + Ellac River (shares 6800; un-gateable fold, see docstring)
    "Ensis": (6820,),
    "Cerulean": (6830,),
    "Charo's": (6840,),
    "Jagged Peak": (6850, 6851),
    "Abyssal": (6860, 28000),
    "Scadu Altus": (6900,),        # + Fog Rift Fort + Recluses' River (share 6900; un-gateable)
    "Scaduview": (6920,),
    "Shadow Keep": (21000, 21001, 21010),
    "Ancient Ruins": (6940,),
    "Rauh Base": (6950,),
    "Belurat": (20000,),
    "Enir Ilim": (20010,),
    "Stone Coffin": (22000,),
    # --- the hub ---
    HUB: (11100,),
}

# str(play_region_id) -> region name. Keys are STRINGS because the grace tables (grace_region_map
# .tsv) carry ids as text and gen_data joins on them verbatim.
PLAY2AP = {str(pid): region for region, pids in REGION_GROUPS.items() for pid in pids}

# Buckets that must NEVER receive kick-watch geometry, even though they belong to a region above:
#   11100 -- the Roundtable HUB (always open; the client treats it as home);
#   18000 -- the tutorial spawn (Stranded Graveyard). It rides Limgrave for CHECK regioning and
#            grace bundles, but a fresh character SPAWNS there -- geometry here would let a rolled
#            start that seals Limgrave eject the player out of the tutorial.
KICK_EXCLUDED_PLAY_IDS = frozenset({11100, 18000})


def region_play_ids():
    """region -> [play_region ids] for kick geometry: spoke regions only (no HUB), minus the
    kick-excluded buckets. This is what gen_data bakes into eldenring/region_play_ids.py."""
    out = {}
    for region, pids in PLAY_REGION_GROUPS.items():   # MEASURED play_region buckets, not warp ids
        if region == HUB:
            continue
        kept = [p for p in pids if p not in KICK_EXCLUDED_PLAY_IDS]
        if kept:
            out[region] = kept
    return out


def assert_covers(play_region_ids):
    """Hard-fail unless this table covers EXACTLY the given bucket universe (the 54 explorable
    buckets from grace_region_map.tsv, plus 11100). A bucket the game knows that this table does
    not is a check/grace that silently falls to fallback paths; a bucket here that the game does
    not know is an invented id."""
    want = {str(p) for p in play_region_ids}
    have = set(PLAY2AP)
    missing, extra = want - have, have - want
    if missing or extra:
        raise AssertionError(
            "region_groups.PLAY2AP does not match the game's bucket universe: "
            f"missing={sorted(missing)} extra={sorted(extra)}")


# =====================================================================================================
# TWO ID SPACES. They name the same places with different numbers, and conflating them is the bug this
# section exists to prevent.
#
#   REGION_GROUPS      keys = BonfireWarpParam.bonfireSubCategoryId -- the game's WARP-MENU grouping.
#                      This is what grace_region_map.tsv is keyed by, so it drives grace bundles and
#                      check regioning (PLAY2AP). It was always CORRECT for that job.
#
#   PLAY_REGION_GROUPS keys = PlayRegionParam.ID // 100 -- the runtime `play_region_id` the client's
#                      kick-watch actually reads. This drives KICK GEOMETRY (region_play_ids ->
#                      areaLockFlags -> the client's baked table).
#
# This file used to claim, in writing, that "bonfireSubCategoryId equals the runtime play_region_id
# (verified against every empirically captured id)". It does not: the two coincide for the base
# OVERWORLD and differ everywhere else -- Gravesite is subcategory 6800 and play_region bucket 68000.
# The caveat was true and vacuous, because no DLC id had ever been captured: nobody had played it.
#
# So ONE table was serving both jobs, and the kick got the wrong numbers. The kick is PERMISSIVE on a
# bucket it has no entry for, so it did not error -- it simply never fired:
#   * the whole DLC overworld -> DLC region locks NEVER enforced; sealed DLC regions were lootable;
#   * Weeping -> its lock had never enforced anything, in any seed;
#   * every mini-dungeon and region sub-bucket -> sealed regions leaked in their sub-areas;
#   * same space feeds the Scadutree blessing FLOOR and DLC enemy scaling -> both inert.
# A missing bucket is not a crash. It is a shrug.
#
# PLAY_REGION_GROUPS below is MEASURED from PlayRegionParam (tools/datamine_play_regions.py --emit),
# checked against the tracked greenfield/play_region_buckets.tsv by
# greenfield/eldenring/tests/test_gf_play_region_buckets.py.
# =====================================================================================================

PLAY_REGION_GROUPS = {
    # === MEASURED from PlayRegionParam (tools/datamine_play_regions.py --emit, 2026-07-13). ===
    # The previous table was sourced from BonfireWarpParam.bonfireSubCategoryId, on the claim that it
    # "equals the runtime play_region_id". It does not: it coincides for the base OVERWORLD and is a
    # different number everywhere else. 27 of its 53 buckets did not exist and 89 real ones were absent,
    # so the KICK -- which is PERMISSIVE on an unknown bucket -- simply never fired on most of the map.
    # Weeping's only bucket (61002) was fictional: that lock had never enforced anything. The whole DLC
    # overworld was fictional. Vote counts below are checks-per-bucket from the derivation.

    # --- base overworld ---
    "Limgrave": (61000, 61010, 18000, 30020, 30040, 30110, 31000, 31030, 31150, 31170, 32010, 34100),
    "Weeping": (61020, 30000, 30010, 31010, 31020, 32000),
    "Liurnia": (62000, 62010, 62020, 39200, 30030, 30050, 30060, 31040, 31050, 31060, 32020, 34110),
    "Altus": (63000, 63010, 30070, 30080, 30100, 30120, 30130, 31180, 31190, 32040, 32050, 34120, 34140),
    "Mt. Gelmir": (63020, 16000, 30090, 31070, 31090),
    "Caelid": (64000, 64010, 64020, 30140, 30150, 30160, 31100, 31110, 31200, 31210, 32070, 32080, 34130),
    # 65000: the derivation votes 'Altus' 2/2 -- OVERRIDDEN. It is the Mountaintops PRIMARY bucket and
    # its three siblings (65010/65020/65030) carry 45 votes of Mountaintops between them. Two border
    # checks (the Grand Lift of Rold sits on the seam) do not outweigh that. Same artefact class as the
    # Altus/Gelmir grace-join fold we already declined to "correct".
    "Mountaintops of the Giants": (65000, 65010, 65020, 65030, 30170, 30180, 30190, 30200, 31120, 31220, 32110),

    # --- base interiors / legacy ---
    "Stormveil": (10000, 10010),
    "Leyndell": (11000, 11050, 19000),
    "Raya Lucaria Academy": (14000,),
    "Haligtree": (15000,),
    "Farum Azula": (13000,),
    "Sewer": (35000,),
    "Ainsel River": (12010,),
    "Siofra River": (12020, 12070),
    "Deeproot Depths": (12030,),
    "Mohgwyn": (12050,),

    # --- DLC overworld (every bucket here is NEW; the old ones were fiction) ---
    # 68200 moved to Ensis (2026-07-13): PlayRegionParam has a row in bucket 68200 on m61_48_44, which
    # is Ensis's OWN grace tile. 68100 and 68200 both have rows on the seam tile m61_47_44, which is
    # why the check-vote split 25/21 between Gravesite and Ensis -- that was not noise, it was the seam.
    "Gravesite": (68000, 68100, 40000, 41000, 42000, 43000, 43010),
    "Ensis": (68200,),                      # m61_48_44 -> row 6820010 (its exclusive grace tile)
    # 68410 assigned 2026-07-15: its MSB PlayArea volumes are named "dragon-mountain FOOT" (the
    # game's name for the Foot of the Jagged Peak, whose warp group 6851 is already Jagged Peak's)
    # and sit at the Foot grace's own elevation; a Jagged Peak check (2049387010, Dragon Communion
    # Harpoon) stands inside one. Named geometry, no longer the refused "adjacency only" guess.
    "Jagged Peak": (68410, 68500,),         # m61_54_39 -> row 6850001 (its grace tile)
    "Scaduview": (69300,),                  # see below -- band evidence, not a tile hit
    # 68400 moved to Charo's (2026-07-15, in-game kick + MSB geometry): warping to Charo's own
    # front-door grace 76841 measured play_region 6840000 (client kick-watch log), and the MSB
    # PlayArea volumes carrying 6840000 (dev name "dragon-mountain west") contain that grace and
    # the grave's own checks. The old "Cerulean 8/8" check-vote was CIRCULAR: the votes were the
    # tile-join's own guesses on the two-region tiles 47/39+48/39 the grave shares with the coast.
    # Ground truth lives in grace_ground.tsv (tools/datamine_grace_ground.py); gen_data gates on it.
    "Cerulean": (68300,),
    "Abyssal": (68600,),          # 28000 (Midra's Manse) is NOT a bucket -- it lives inside 68600
    "Scadu Altus": (69000, 69020, 69030, 40020, 41010, 42020),
    "Ancient Ruins": (69400, 69410),
    # 69010 moved to Rauh Base (2026-07-15, MSB geometry): Rauh Base's bundle grace 76914 stands
    # INSIDE a 6901000 PlayArea volume, and every 6901000 volume is Rauh Base terrain by the
    # game's own names (runebear forest, "directly under Mohenjo-daro" = the Rauh ruins plateau,
    # the trap cellar, around ruined forge 1-4). The old Gravesite 12/12 vote was the same
    # circular tile-join artifact as 68400's. Cookbook check 68680 (Rauh Base) stands on it too.
    "Rauh Base": (69010, 40010, 42030),
    "Charo's": (68400, 41020),

    # --- DLC interiors ---
    "Belurat": (20000,),
    "Enir Ilim": (20010,),
    "Shadow Keep": (21000, 21010, 21020),
    "Stone Coffin": (22000,),

    # --- the hub ---
    HUB: (11100,),
}

# No region is bucketless any more. All three were resolved from the game's data, not from adjacency:
#
#   Ensis       68200 -- PlayRegionParam has a row in that bucket on m61_48_44, Ensis's OWN grace tile.
#                        (68100/68200 both have rows on the SEAM tile m61_47_44, which is exactly why the
#                        check vote split 25/21 with Gravesite. The seam was the signal, not noise.)
#   Jagged Peak 68500 -- row 6850001 sits on m61_54_39, a Jagged Peak grace tile.
#   Scaduview   69300 -- CONFIRMED as Scaduview's bucket, with a twist (the predicted Hinterland kick
#                        happened, 2026-07-15): warping to its front-door grace 76935 measured
#                        play_region 2100010 -- NOT 693xxxxx -- because the grace stands on m21_00's
#                        DEFAULT ground (bucket 21000 = Shadow Keep; the m21_00 MSB carves override
#                        volumes for subs 2100001/11/12/13/15 and none for 2100010). 69300 itself is
#                        still Scaduview's: its 6930000 MSB boundary volumes (m61_49_48/m61_50_48) and
#                        the PlayRegionParam row anchored at m61_52_48 (mapMenuUnlockEventId = 76935!)
#                        are real Scaduview geometry. Bucket 21000 is shared with the whole Keep
#                        interior, so the fix is NOT a rebucket: region_spine.REGION_PARENT gates
#                        Scaduview behind Shadow Keep (containment, the Sewer pattern), and
#                        grace_ground.tsv carries the measured 76935 -> 21000 row.
#
# Kept as a set so the machinery survives (a future region added before its bucket is measured).
REGIONS_PENDING_BUCKET = frozenset()

UNASSIGNED_BUCKETS = {
    0: "system / no-region sentinel (the client sees it pre-spawn and between loads)",
    9810: "unreachable dev/system map (m09_81) -- no checks, no graces",
    9820: "unreachable dev/system map (m09_82) -- no checks, no graces",
    9999: "unreachable dev/system map (m09_99) -- no checks, no graces",
    12040: "underground bucket with no checks and no graces -- nothing to gate",
    12080: "underground bucket with no checks and no graces -- nothing to gate",
    12090: "underground bucket with no checks and no graces -- nothing to gate",
    25000: "Cathedral of Manus Metyr (m25_00): no checks of its own; its grace resolves to Scadu Altus",
    34150: "divine-tower-class interior with no checks -- nothing to gate",
    42010: "DLC dungeon (m42_01) with no checks -- nothing to gate",
    45000: "DLC gaol-class interior with no checks -- nothing to gate",
    45010: "DLC gaol-class interior with no checks -- nothing to gate",
    45020: "DLC gaol-class interior with no checks -- nothing to gate",
    60000: "base overworld with NO coordinate rows and no checks; the real Limgrave..Mountaintops "
           "geometry is 61000-65030. Kept permissive rather than guessed onto a region",
    # THESE FOUR ARE THE PENDING REGIONS' LIKELY BUCKETS -- parked here ONLY because they are not yet
    # measured. They are NOT 'deliberately permissive': they are the open question. See
    # REGIONS_PENDING_BUCKET above; a grace warp + kick-watch line settles each.
    69200: "no coordinate rows AND no MSB PlayArea volume anywhere carries a 692xxxxx id, so there "
           "is literally no geometry to stand on. (68410, which used to sit here on the same "
           "grounds, got real geometry evidence 2026-07-15 -- named 'dragon-mountain foot' volumes "
           "-- and moved to Jagged Peak.) Still permissive, not guessed",
}

