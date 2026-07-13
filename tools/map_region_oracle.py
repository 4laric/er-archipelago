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
# The fold layer is region_groups.py -- THE spine, the same table gen_data derives from. This
# oracle used to restate it by hand "independently"; that made it a second copy of a curated
# CONVENTION, so every deliberate re-carve broke the oracle spuriously while real bugs hid behind
# the churn. What stays independent here is the JOIN (grace_flags x grace_region_map), which is
# what actually arbitrates data.py's per-row derivation paths. None = non-explorable system ids.
import importlib.util as _ilu
_rg_spec = _ilu.spec_from_file_location(
    "region_groups", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "greenfield", "region_groups.py"))
_rg = _ilu.module_from_spec(_rg_spec); _rg_spec.loader.exec_module(_rg)
PLAY_REGION_TO_GF = {0: None, 10010: None}
PLAY_REGION_TO_GF.update({int(_p): _r for _p, _r in _rg.PLAY2AP.items()})

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
    # The grace tsvs are DERIVED + TRACKED in greenfield/ now (a `git clean -xdf` once deleted the
    # artifacts-only copies); artifacts_dir stays as the legacy fallback for older trees.
    _here = os.path.dirname(os.path.abspath(__file__))
    _gfdir = os.path.abspath(os.path.join(_here, "..", "greenfield"))
    artifacts_dir = artifacts_dir or _find_artifacts(_here)
    gf_path, grm = None, []
    for _base in (_gfdir, artifacts_dir):
        if not _base or not os.path.isdir(_base):
            continue
        _gfp = sorted(glob.glob(os.path.join(_base, "grace_flags*.tsv")))
        _grm = sorted(glob.glob(os.path.join(_base, "grace_region_map*.tsv")))
        if _gfp and _grm:
            gf_path, grm = _gfp[-1], _grm
            break
    if not gf_path or not grm:
        return None, "grace_flags.tsv / grace_region_map*.tsv absent (greenfield/ and artifacts)"
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
