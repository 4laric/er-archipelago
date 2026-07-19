"""Greenfield num_regions spine (matt-free) -- SPEC-PARITY Phase 1.

Progression order over the 31 greenfield regions + the always-kept goal region (region-spine v2). `num_regions`
seals the world down to N regions; `compute_kept` decides which N. Pure (no AP import) so it runs
in the data-invariant gate. Keyed by REGION name only (greenfield's own names), never an imported
set -- this is the re-keyed port of the eldenring region spine (SPEC-PARITY.md P1).
"""
from .data import REGIONS

# Lock always required (capital ending). Always kept so the seed stays winnable at any num_regions.
# Region-spine v2: Leyndell is a first-class region again (buckets 11000 Royal + 11050 Ashen fold +
# 19000 Fractured Marika), so the capital-ending checks live in Leyndell -> it is the goal region.
GOAL_REGION = "Leyndell"

# VANILLA HARD WALLS -- gated child -> the parent region it is physically entered from.
#
# These three regions sit behind a wall the GAME already enforces: Raya Lucaria's seal wants the
# Academy Glintstone Key, the capital's main gate wants Great Runes (leyndell_runes_required), and
# the m35 Shunning-Grounds are entered down a well INSIDE the capital (no independent entrance), so
# the Sewer inherits Leyndell's wall transitively. The 2026-07-14 playtest bug was the apworld
# GRANTING a child's grace bundle on region-open -- a warp target on the far side of the wall
# (East Capital Rampart 71102, BonfireWarpParam 110002, straight past the 2-rune gate). The fix is
# to let the game keep enforcing its own walls and encode the containment ONCE, here:
#   * features/graces.py withholds a child's grace bundle (walk in, touch the graces yourself);
#   * core.create_regions parents the child's AP region under this entry, so reachability logic
#     requires the whole ancestor Lock chain (fill can never strand progression in a sealed child);
#   * compute_kept (below) closes the kept set over this map -- a child is never kept parentless;
#   * features/start_grace.pick_anchor_region refuses a child as the run's opening region (the
#     anchor grant is exactly the bundle being withheld).
# tests/test_gf_gated_children.py asserts every region-entry gate feature (legacy_key_gates map
# ranges, leyndell_gate's GOAL_REGION) has an entry here, so a future gate cannot land without one.
REGION_PARENT = {
    "Raya Lucaria Academy": "Liurnia",   # Academy Glintstone Key seal (features/legacy_key_gates)
    "Leyndell": "Altus",                 # capital main gate, N Great Runes (features/leyndell_gate)
    "Sewer": "Leyndell",                 # m35 well is inside the capital walls (SPEC-region-spine-v2)
    # Scaduview's containment entry was REMOVED 2026-07-19: the Hinterland was FOLDED into Shadow Keep
    # (region_groups) rather than kept a contained child, so it is no longer a separate region to gate
    # -- its checks ARE Shadow Keep checks now, under the Keep's own Lock. (Its door ground was always
    # the Keep's bucket 21000, which is exactly why the fold is clean; the Keep's front door stays its
    # own m21_00 entrance 72102 via gen_data._FRONT_DOOR_PIN.)
}


def parent_chain(region):
    """Ancestor list for `region`, nearest first (empty for an ungated region). Raises on a cycle
    rather than looping -- a cyclic REGION_PARENT is corrupt data, not a soft case."""
    chain, seen = [], {region}
    r = REGION_PARENT.get(region)
    while r is not None:
        if r in seen:
            raise ValueError(f"REGION_PARENT cycle at {r!r} (from {region!r})")
        chain.append(r)
        seen.add(r)
        r = REGION_PARENT.get(r)
    return chain

# Fixed progression path (Limgrave-first). num_regions_order='spine' keeps the first N of this;
# 'rolled' keeps N random regions. Must be a permutation of REGIONS (guarded by test_gf_data).
SPINE = [
    # base game, rough vanilla progression order
    "Limgrave", "Weeping", "Stormveil", "Liurnia", "Raya Lucaria Academy",
    "Caelid", "Siofra River", "Altus", "Mt. Gelmir",
    "Leyndell", "Sewer", "Ainsel River", "Deeproot Depths", "Mohgwyn",
    "Mountaintops of the Giants", "Haligtree", "Farum Azula",
    # DLC (rides as plain lock gates -- SPEC-PARITY.md P7), entry-first
    "Gravesite", "Ensis", "Cerulean", "Charo's", "Belurat",
    "Scadu Altus", "Shadow Keep", "Stone Coffin",
    "Ancient Ruins", "Rauh Base", "Jagged Peak", "Abyssal", "Enir Ilim",
]

# The Shadow of the Erdtree DLC regions. These are the last 13 entries of SPINE and are the pool the
# EnableDLC / DLCOnly toggles filter on (core.py). Kept as a frozenset for O(1) membership; the
# base-game pool is REGIONS minus these. Pure data (no AP import) so region-scope filtering can run
# in the data-invariant gate.
DLC_REGIONS = frozenset({
    "Gravesite", "Ensis", "Cerulean", "Charo's", "Belurat",
    "Scadu Altus", "Shadow Keep", "Stone Coffin",
    "Ancient Ruins", "Rauh Base", "Jagged Peak", "Abyssal", "Enir Ilim",
})


def base_regions():
    """Base-game (non-DLC) region names, in REGIONS order."""
    return [r for r in REGIONS if r not in DLC_REGIONS]


def dlc_regions():
    """DLC region names, in REGIONS order."""
    return [r for r in REGIONS if r in DLC_REGIONS]


def compute_kept(n, order, rng, eligible=None):
    """Kept-region list, drawn from `eligible` (defaults to all of REGIONS).

    `eligible` is the already-filtered pool of regions in play this seed (e.g. base-only when
    EnableDLC is off, or DLC-only when DLCOnly is on -- computed in core.generate_early). Passing it
    in keeps num_regions selection honest: N is always drawn from the eligible set, never from a
    sealed region.

    n<=0 or n>=len(eligible) -> the whole eligible pool (full Shattering of what's in play).
    order 'spine' -> the first N eligible regions in SPINE order; anything else -> N random eligible
    regions (rng.sample). The goal region is appended only when it is itself eligible -- under
    DLCOnly the base-game goal (Leyndell) is not eligible, and the goal collapses to "hold every kept
    lock" over the eligible set (still winnable; see core.set_rules)."""
    regions = list(REGIONS) if eligible is None else [r for r in REGIONS if r in set(eligible)]
    if not regions:
        return regions
    if n <= 0 or n >= len(regions):
        return _close_over_parents(regions, regions)
    if order == "spine":
        base = [r for r in SPINE if r in regions][:n]
    else:  # rolled
        base = rng.sample(regions, n)
    kept = list(dict.fromkeys(base))
    if GOAL_REGION in regions and GOAL_REGION not in kept:
        kept.append(GOAL_REGION)
    return _close_over_parents(kept, regions)


def _close_over_parents(kept, pool):
    """Close `kept` over REGION_PARENT: a kept gated child PULLS ITS ANCESTORS IN (never the other
    way -- dropping the child instead is impossible for the always-kept goal region, whose parent
    chain is exactly why Altus rides along on every base seed: the capital has no other way in).
    The closure keeps the seed winnable by construction; a kept-but-unreachable child is a
    dead-drop generator. An ancestor missing from the eligible pool is a hard error, not a shrug:
    it means a gated child was declared eligible while its only entrance was not (a scope-filter
    bug) -- and it applies on EVERY path, including the n<=0 / n>=len full-pool returns."""
    kept = list(kept)
    in_pool = set(pool)
    for r in list(kept):
        for anc in parent_chain(r):
            if anc in kept:
                continue
            if anc not in in_pool:
                raise ValueError(
                    f"compute_kept: kept region {r!r} needs ancestor {anc!r}, which is not in the "
                    f"eligible pool -- a gated child must never be eligible without its parent")
            kept.append(anc)
    return kept
