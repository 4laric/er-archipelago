"""Independent map_id -> greenfield-region arbiter (the GRACE JOIN), for the provenance oracle.

WHY THIS EXISTS (replaces majority-vote)
----------------------------------------
Predicate A ("every check the game places in map M must carry M's region in data.py") needs a
ground-truth region for M. v1 used the MAJORITY data.py region among M's own checks -- which is
unsound twice over:
  1. the majority can BE the bug: m11_10 IS Roundtable Hold, but gen_data's coarse
     'Leyndell / Roundtable / Shunning-Grounds' -> 'Altus Plateau' bucket makes "Altus Plateau" the
     majority there, so majority-vote blamed the two CORRECT rows (Ensha, flags 400490 / 11107900,
     deliberate FLAG_REGION_OVERRIDE entries) and blessed the wrong ones;
  2. it shares provenance with the thing under test (both sides are data.py), so it is not an oracle.

The grace join is independent and definitive for interior maps:
    elden_ring_artifacts/grace_flags.tsv           warpUnlockFlag -> mapTile   (game data: BonfireWarpParam)
  JOIN
    elden_ring_artifacts/grace_region_map_*.tsv    grace_flag -> play_region_id (BonfireWarpParam.bonfireSubCategoryId)
  => map_id -> {play_region_id}  => (PLAY_REGION_TO_GF below) => map_id -> {greenfield region}
It never touches region_map.csv or gen_data's region derivation, so cross-checking data.py against
it never re-runs the transform under test. Verified joins: m11_10 -> 11100 Roundtable Hold;
m12_03 -> 12030 Eternal Cities; m31_01 -> 61002 Weeping; m31_17 -> 61000 Limgrave; m32_00 -> 61002;
m39_20 -> 39200; m14_00 -> 14000 (Raya Lucaria, folds to Liurnia); m10_00 -> {10000, 61001}.

SCOPE: INTERIOR MAPS ONLY. m60_*/m61_* overworld map ids are SPATIAL TILES; a single tile can
legitimately straddle a region boundary (72 false majority-vote violations came from exactly this),
so same-map consistency is invalid there. Overworld provenance is already gated independently by
test_gf_grace_region_correctness.py (per-grace play_region oracle) + the tile decode it checks.

FOLDS: several play_regions fold into one greenfield region (a gf region = a data.py LOCATIONS key).
Every fold below is sourced from elden_ring_artifacts/REGION_ID_MAP.md (the authoritative 55-bucket
doc) for WHAT the play_region is, and from gen_data.py's own conventions (PLAY2AP / REGION_MAP /
DUNGEON_REGION_OVERRIDE) for WHICH gf region that place ships in -- i.e. the table encodes the
repo's declared region model, not this file's opinion. Per-entry citations inline.
"""
import csv
import glob
import os
import re
from collections import defaultdict

# ---- play_region_id -> greenfield region (data.py LOCATIONS key) ------------------------------
# None = non-explorable / not a gf region (system warps). Absent id => join fails loudly in meta.
PLAY_REGION_TO_GF = {
    # -- system / placeholder (REGION_ID_MAP.md "System / non-explorable") --
    0: None,          # 3 system warps (flag 200 @ m10, 71260/71261 @ m12), not real graces
    10010: None,      # defined bucket with no bonfire (placeholder)
    # -- overworld buckets (REGION_ID_MAP.md overworld table; fold = gen_data PLAY2AP verbatim) --
    61000: "Limgrave",
    61001: "Limgrave",                    # Stormhill / N. Limgrave (PLAY2AP: 61001 -> Limgrave)
    61002: "Weeping Peninsula",
    62000: "Liurnia of the Lakes",
    62001: "Liurnia of the Lakes",        # Eastern Liurnia / Bellum Highway
    62002: "Liurnia of the Lakes",        # Moonlight Altar
    63000: "Altus Plateau",
    63001: "Mt. Gelmir",                  # its OWN gf region (er-gelmir-lock-rebucket)
    63002: "Altus Plateau",               # W. Altus / Capital Outskirts
    63003: "Altus Plateau",               # E. Altus / Forbidden Lands / Rold (PLAY2AP)
    64000: "Caelid",
    64001: "Caelid",                      # Dragonbarrow
    64002: "Caelid",                      # Swamp of Aeonia
    65000: "Mountaintops of the Giants",
    65001: "Mountaintops of the Giants",  # Forge of the Giants
    65002: "Mountaintops of the Giants",  # Consecrated Snowfield (REGION_MAP: 'Consecrated Snowfield' -> Mountaintops)
    # -- legacy dungeons / capitals (REGION_ID_MAP.md legacy table) --
    10000: "Stormveil Castle",
    11000: "Altus Plateau",               # FOLD: Leyndell, Royal Capital (REGION_MAP 'Leyndell, Royal Capital' -> Altus)
    11050: "Altus Plateau",               # FOLD: Leyndell, Ashen Capital (REGION_MAP 'Leyndell (Ashen Capital)' -> Altus)
    11100: "Roundtable Hold",
    13000: "Farum Azula",                 # REGION_MAP 'Crumbling Farum Azula' -> Farum Azula
    14000: "Liurnia of the Lakes",        # FOLD: Raya Lucaria Academy (REGION_MAP 'Raya Lucaria Academy' -> Liurnia)
    15000: "Miquella's Haligtree",        # Elphael (REGION_MAP "Miquella's Haligtree & Elphael")
    15001: "Miquella's Haligtree",
    16000: "Mt. Gelmir",                  # FOLD: Volcano Manor interior (REGION_MAP 'Volcano Manor (Rykard)' -> Mt. Gelmir)
    18000: "Limgrave",                    # FOLD: Stranded Graveyard / Chapel (gen_data pins m18 Fringefolk lots -> Limgrave)
    19000: "Altus Plateau",               # FOLD: Fractured Marika arena (REGION_MAP 'Fractured Marika (final)' -> Altus)
    35000: "Altus Plateau",               # FOLD: Subterranean Shunning-Grounds (REGION_MAP -> Altus; sits UNDER Leyndell)
    39200: "Liurnia of the Lakes",        # FOLD: Ruin-Strewn Precipice (house convention: gen_data FLAG_REGION_OVERRIDE
                                          #       row 510260 'Magma Wyrm Makar (Ruin-Strewn Precipice)' -> Liurnia)
    # -- underground (REGION_ID_MAP.md underground table; REGION_MAP folds every Siofra/Ainsel/
    #    Nokstella/Lake-of-Rot/Deeproot alias -> 'Eternal Cities'; Mohgwyn is its own gf region) --
    12010: "Eternal Cities",              # Ainsel River / Nokstella
    12011: "Eternal Cities",              # Lake of Rot
    12012: "Eternal Cities",              # Ainsel River Depths / Astel
    12020: "Eternal Cities",              # Siofra River
    12030: "Eternal Cities",              # Deeproot Depths
    12050: "Mohgwyn Palace",
    12070: "Eternal Cities",              # Siofra River Bank / Worshippers' Woods
    # -- DLC (REGION_ID_MAP.md DLC table; folds per REGION_MAP + gen_data DUNGEON_REGION_OVERRIDE §5b) --
    6800: "Gravesite Plain",
    6820: "Gravesite Plain",              # FOLD: Castle Ensis (REGION_MAP 'Castle Ensis (DLC)' -> Gravesite Plain)
    6830: "Gravesite Plain",              # FOLD: Cerulean Coast (REGION_MAP 'Cerulean Coast (DLC)' -> Gravesite Plain)
    6840: "Gravesite Plain",              # FOLD: Charo's Hidden Grave / Lamenter's Gaol (gen_data m41_02 -> Gravesite Plain)
    6850: "Jagged Peak",
    6851: "Jagged Peak",                  # Foot of the Jagged Peak / Dragon Communion Altar
    6860: "Abyssal Woods",
    6900: "Scadu Altus",                  # shared bucket (also Fog Rift Fort / Recluses' River per REGION_ID_MAP)
    6920: "Shadow Keep",                  # FOLD: Scaduview/Hinterland (gen_data §5a: Scaduview -> Shadow Keep,
                                          #       only reachable through the Keep)
    6940: "Ancient Ruins of Rauh",
    6950: "Ancient Ruins of Rauh",        # FOLD: Rauh Base (gen_data pins m40_01/m42_03 'Rauh Base' dungeons -> Rauh)
    20000: "Belurat",
    20010: "Enir-Ilim",
    21000: "Shadow Keep",
    21001: "Shadow Keep",                 # Church District
    21010: "Shadow Keep",                 # Storehouse
    22000: "Gravesite Plain",             # FOLD: Stone Coffin Fissure (REGION_MAP 'm22' -> Gravesite Plain)
    28000: "Abyssal Woods",               # FOLD: Midra's Manse (REGION_MAP 'm28' -> Abyssal Woods)
}

# ---- per-map truth WIDENING for curated boundary connectors ------------------------------------
# A connector dungeon whose warp-menu bucket sits on one side of a boundary but which the repo
# deliberately curates into the other side. The grace-derived region stays in the set (it is not
# wrong); the curated region is ADDED, so neither assignment false-positives. Each entry cites why.
MAP_TRUTH_EXTRA = {
    # Hidden Path to the Haligtree: grace bucket 63003 (E. Altus / Forbidden Lands / Rold) -> Altus,
    # but gen_data DUNGEON_REGION_OVERRIDE curates m30_20 -> Mountaintops of the Giants ("Snowfield
    # folded into Mountaintops") since it is the Snowfield chain's entrance.
    "m30_20": {"Mountaintops of the Giants"},
}

_OVERWORLD_RE = re.compile(r"^m6[01]_")


def is_overworld(map_id):
    """m60_*/m61_* spatial overworld tiles -- out of this arbiter's scope (they straddle borders)."""
    return bool(_OVERWORLD_RE.match(map_id))


def _find_artifacts(start):
    d = os.path.abspath(start)
    for _ in range(8):
        cand = os.path.join(d, "elden_ring_artifacts")
        if os.path.isdir(cand):
            return cand
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    return None


def load_map_truth(artifacts_dir=None):
    """-> (map_truth, meta) or (None, reason-str) if the grace artifacts are absent.

    map_truth: {interior map_id: frozenset(greenfield regions)} from the grace join. Almost every
    map folds to exactly ONE region; a map whose own graces straddle a boundary (m10_00 holds both
    Stormveil-bucket and Stormhill-bucket graces) carries the full set, and the caller adjudicates
    by MEMBERSHIP -- still sound (any cross-boundary region is a violation), just less sharp there.
    meta: counts + the unmapped-pid list so a REGION_ID_MAP drift fails loudly, never silently.
    """
    artifacts_dir = artifacts_dir or _find_artifacts(os.path.dirname(os.path.abspath(__file__)))
    if not artifacts_dir:
        return None, "elden_ring_artifacts/ not found"
    gf_path = os.path.join(artifacts_dir, "grace_flags.tsv")
    grm = sorted(glob.glob(os.path.join(artifacts_dir, "grace_region_map_*.tsv")))
    if not os.path.isfile(gf_path) or not grm:
        return None, "grace_flags.tsv / grace_region_map_*.tsv absent"
    with open(grm[-1], encoding="utf-8", newline="") as fh:
        flag2pid = {int(r["grace_flag"]): int(r["play_region_id"])
                    for r in csv.DictReader(fh, delimiter="\t")}
    map_truth = defaultdict(set)
    unmapped_pids = set()
    graces = overworld_graces = system_graces = 0
    with open(gf_path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            graces += 1
            pid = flag2pid.get(int(r["warpUnlockFlag"]))
            if pid is None:
                continue
            map_id = "_".join(r["mapTile"].split("_")[:2])      # m10_00_00 tile -> m10_00 map block
            if is_overworld(map_id):
                overworld_graces += 1
                continue
            if pid in PLAY_REGION_TO_GF:
                gf = PLAY_REGION_TO_GF[pid]
                if gf is None:
                    system_graces += 1
                    continue
                map_truth[map_id].add(gf)
            else:
                unmapped_pids.add(pid)                          # REGION_ID_MAP drift -- surface it
    for map_id, extra in MAP_TRUTH_EXTRA.items():
        if map_id in map_truth:
            map_truth[map_id] |= extra
    meta = {
        "grace_region_map": os.path.basename(grm[-1]),
        "graces": graces,
        "overworld_graces_skipped": overworld_graces,
        "system_graces_skipped": system_graces,
        "unmapped_play_regions": sorted(unmapped_pids),
        "interior_maps": len(map_truth),
        "boundary_maps": {m: sorted(s) for m, s in map_truth.items() if len(s) > 1},
    }
    return {m: frozenset(s) for m, s in map_truth.items()}, meta


if __name__ == "__main__":
    truth, meta = load_map_truth()
    if truth is None:
        raise SystemExit(meta)
    for m in sorted(truth):
        print(m, sorted(truth[m]))
    print(meta)
