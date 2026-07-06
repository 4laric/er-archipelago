"""Greenfield num_regions spine (matt-free) -- SPEC-PARITY Phase 1.

Progression order over the 22 greenfield regions + the always-kept goal region. `num_regions`
seals the world down to N regions; `compute_kept` decides which N. Pure (no AP import) so it runs
in the data-invariant gate. Keyed by REGION name only (greenfield's own names), never an imported
set -- this is the re-keyed port of the eldenring region spine (SPEC-PARITY.md P1).
"""
from .data import REGIONS

# Lock always required (capital ending). Always kept so the seed stays winnable at any num_regions.
GOAL_REGION = "Leyndell"

# Fixed progression path (Limgrave-first). num_regions_order='spine' keeps the first N of this;
# 'rolled' keeps N random regions. Must be a permutation of REGIONS (guarded by test_gf_data).
SPINE = [
    "Limgrave", "Weeping Peninsula", "Stormveil Castle", "Liurnia of the Lakes",
    "Raya Lucaria Academy", "Caelid", "Dragonbarrow", "Altus Plateau", "Mt. Gelmir",
    "Leyndell", "Mountaintops of the Giants", "Consecrated Snowfield", "Miquella's Haligtree",
    "Farum Azula", "Mohgwyn Palace", "Eternal Cities",
    # DLC (rides as plain lock gates -- SPEC-PARITY.md P7)
    "Land of Shadow", "Belurat", "Scadu Altus", "Shadow Keep", "Jagged Peak", "Abyssal Woods",
]


def compute_kept(n, order, rng):
    """Kept-region list. n<=0 or n>=len(REGIONS) -> all regions (full Shattering).
    order 'spine' -> first N of SPINE; anything else -> N random regions (rng.sample).
    The goal region is always included (added if the selection missed it)."""
    regions = list(REGIONS)
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
