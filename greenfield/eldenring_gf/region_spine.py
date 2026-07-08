"""Greenfield num_regions spine (matt-free) -- SPEC-PARITY Phase 1.

Progression order over the 22 greenfield regions + the always-kept goal region. `num_regions`
seals the world down to N regions; `compute_kept` decides which N. Pure (no AP import) so it runs
in the data-invariant gate. Keyed by REGION name only (greenfield's own names), never an imported
set -- this is the re-keyed port of the eldenring region spine (SPEC-PARITY.md P1).
"""
from .data import REGIONS

# Lock always required (capital ending). Always kept so the seed stays winnable at any num_regions.
# Capstone re-carve: Leyndell folded into Altus Plateau, so the capital-ending checks (Morgott,
# Ashen Capital, Fractured Marika) now live in Altus's region -> Altus Plateau is the goal region.
GOAL_REGION = "Altus Plateau"

# Fixed progression path (Limgrave-first). num_regions_order='spine' keeps the first N of this;
# 'rolled' keeps N random regions. Must be a permutation of REGIONS (guarded by test_gf_data).
SPINE = [
    "Limgrave", "Weeping Peninsula", "Stormveil Castle", "Liurnia of the Lakes",
    "Caelid", "Altus Plateau", "Mt. Gelmir",
    "Mountaintops of the Giants", "Consecrated Snowfield", "Miquella's Haligtree",
    "Farum Azula", "Mohgwyn Palace", "Eternal Cities",
    # DLC (rides as plain lock gates -- SPEC-PARITY.md P7). Capstone re-carve split the old
    # 'Land of Shadow' catch-all into Gravesite Plain + Ancient Ruins of Rauh (Romina) + Enir-Ilim.
    "Gravesite Plain", "Belurat", "Scadu Altus", "Shadow Keep",
    "Ancient Ruins of Rauh", "Enir-Ilim", "Jagged Peak", "Abyssal Woods",
]

# The Shadow of the Erdtree DLC regions. These are the last 8 entries of SPINE and are the pool the
# EnableDLC / DLCOnly toggles filter on (core.py). Kept as a frozenset for O(1) membership; the
# base-game pool is REGIONS minus these. Pure data (no AP import) so region-scope filtering can run
# in the data-invariant gate.
DLC_REGIONS = frozenset({
    "Gravesite Plain", "Belurat", "Scadu Altus", "Shadow Keep",
    "Ancient Ruins of Rauh", "Enir-Ilim", "Jagged Peak", "Abyssal Woods",
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
        return regions
    if order == "spine":
        base = [r for r in SPINE if r in regions][:n]
    else:  # rolled
        base = rng.sample(regions, n)
    kept = list(dict.fromkeys(base))
    if GOAL_REGION in regions and GOAL_REGION not in kept:
        kept.append(GOAL_REGION)
    return kept
