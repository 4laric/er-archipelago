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

WHAT A BUCKET IS. bucket = PlayRegionParam.ID // 100. `PlayRegionParam` row ids ARE the runtime
play_region_id the client's kick-watch reads (WorldChrMan.main_player.play_region_id); nothing
else is authoritative. This table was ORIGINALLY sourced from
`BonfireWarpParam.bonfireSubCategoryId` on the claim that it equals the runtime id -- that claim
is FALSE. It coincides for the base-game overworld primaries and nowhere else: the DLC warp ids
are a different number entirely (Gravesite's warps say 6800; the runtime bucket is 68000-band),
and the game defines far more buckets than the 54 the warp menu shows (every mini-dungeon and
region sub-bucket has its own). REGION_ID_MAP.md documents the WARP grouping, not the runtime id
space -- it is superseded for kick geometry. Entries below are therefore KNOWN-STALE until
re-derived: some are phantoms the game never produces (their locks can never fire) and many real
buckets have no entry (the kick silently has no opinion there). Re-derive with
tools/datamine_play_regions.py (needs the game artifacts); its --emit writes
greenfield/play_region_buckets.tsv, the TRACKED bucket universe that
greenfield/eldenring/tests/test_gf_play_region_buckets.py asserts this table against. Bucket
numbers quoted in the paragraphs below predate this correction. A region is a SET of buckets; the
kick-watch can gate exactly at bucket granularity, no finer.

NAMES (bedrock interop, 2026-07-12). The client enforces a foreign apworld's region locks by
matching its lock ITEM NAMES against "<Region> Lock" over these region names (er-logic
region_locks.rs baked table). Bedrock's apworld is the one shipping such locks, and Alaric agreed
to adopt his region names where he has one; ours are kept where he has none. That is why several
names are terse ("Weeping", "Ensis", "Ancient Ruins") and why "Enir Ilim" drops the game's own
hyphen -- his lock item is literally "Enir Ilim Lock". NOT adopted (documented in
SPEC-region-spine-v2.md): "Redmane" (Redmane Castle has no bucket of its own -- it is m60 tiles
inside 64000), "Volcano" (bucket 16000 exists but the Manor sits ON Mt. Gelmir; one region),
"Ashen" (post-burn Leyndell, 11050: its checks are excluded as dead content -- the 2026-07-08
decision -- so it folds into Leyndell), and his three "* Underground Lock"s (their grouping does
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
  * Leyndell = 11000 + 11050 (Ashen Capital: dead-content fold, see above) + 19000 (Fractured
    Marika, the capital-ending arena) -- the GOAL region;
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
    "Gravesite": (68000, 68100, 68200, 69010, 40000, 41000, 42000, 43000, 43010),
    "Cerulean": (68300, 68400),
    "Abyssal": (68600,),          # 28000 (Midra's Manse) is NOT a bucket -- it lives inside 68600
    "Scadu Altus": (69000, 69020, 69030, 40020, 41010, 42020),
    "Ancient Ruins": (69400, 69410),
    "Rauh Base": (40010, 42030),
    "Charo's": (41020,),

    # --- DLC interiors ---
    "Belurat": (20000,),
    "Enir Ilim": (20010,),
    "Shadow Keep": (21000, 21010, 21020),
    "Stone Coffin": (22000,),

    # --- the hub ---
    HUB: (11100,),
}

# REGIONS WHOSE BUCKET IS NOT YET KNOWN. Their locks DO NOT ENFORCE: the kick is permissive on ground it
# has no entry for, so these three can be walked into while sealed. This is a NAMED hole, not a silent
# one -- which is the whole difference from the table this replaces.
#
# Why they are not guessed: a bucket's PlayRegionParam coordinate is ONE sample row, not its extent, so
# adjacency proves nothing. The obvious pattern (bonfire subcategory x10) was tried and was WRONG -- the
# real set has 68410/69010/69030 and no 68510/69500. Resolve by warping to a grace in each and reading
# the client's kick-watch line, which prints the live bucket:
#     kick-watch: play_region <old> -> <new> (sub <bucket>)
#
#   Ensis       tiles m61_47_44, m61_48_44. Its checks vote inside 68100/68200, both of which are
#               majority-Gravesite (68200 = Gravesite 25 / Ensis 21). Castle Ensis may simply SHARE
#               Gravesite's bucket, in which case it is un-gateable at bucket granularity -- the same
#               class as Fog Rift Fort / Recluses' River sharing 69000 with Scadu Altus.
#   Jagged Peak tiles m61_49_38/39, m61_50_40, m61_52_40/41, m61_53_39/40 + interior m12_05. Candidate
#               unassigned buckets: 68410 (sample coord m61_49_40), 68500 (m61_54_39).
#   Scaduview   tiles m61_49_48, m61_49_49, m61_53_48. Candidates: 69200 (no coord rows), 69300
#               (m61_52_48).
REGIONS_PENDING_BUCKET = frozenset({"Ensis", "Jagged Peak", "Scaduview"})

# str(play_region_id) -> region name. Keys are STRINGS because the grace tables (grace_region_map
# .tsv) carry ids as text and gen_data joins on them verbatim.
PLAY2AP = {str(pid): region for region, pids in REGION_GROUPS.items() for pid in pids}

# Buckets that must NEVER receive kick-watch geometry, even though they belong to a region above:
#   11100 -- the Roundtable HUB (always open; the client treats it as home);
#   18000 -- the tutorial spawn (Stranded Graveyard). It rides Limgrave for CHECK regioning and
#            grace bundles, but a fresh character SPAWNS there -- geometry here would let a rolled
#            start that seals Limgrave eject the player out of the tutorial.
KICK_EXCLUDED_PLAY_IDS = frozenset({11100, 18000})

# Real buckets (rows of greenfield/play_region_buckets.tsv) that DELIBERATELY map to no region:
# ground where the kick is permissive ON PURPOSE, each with its reason. Anything in that tsv that
# is neither in REGION_GROUPS nor here is an UNREVIEWED permissive hole, and
# greenfield/eldenring/tests/test_gf_play_region_buckets.py fails on it. Never park a bucket here
# to silence the test -- a reasonless entry is the same hole with a lid on it.
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
    68410: "PENDING: candidate for Jagged Peak (sample coord m61_49_40) -- measure, do not guess",
    68500: "PENDING: candidate for Jagged Peak (sample coord m61_54_39) -- measure, do not guess",
    69200: "PENDING: candidate for Scaduview (no coordinate rows) -- measure, do not guess",
    69300: "PENDING: candidate for Scaduview (sample coord m61_52_48) -- measure, do not guess",
}


def region_play_ids():
    """region -> [play_region ids] for kick geometry: spoke regions only (no HUB), minus the
    kick-excluded buckets. This is what gen_data bakes into eldenring/region_play_ids.py."""
    out = {}
    for region, pids in REGION_GROUPS.items():
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
