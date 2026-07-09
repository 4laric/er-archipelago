"""Region grace lighting -- non-optional. Receiving a region's Lock lights that region's grace warp
flags so the player can warp in (BUNDLE: a lock lights ALL of the region's graces).

Region-keyed, matt-free. REGION_GRACE_POINTS (all warp graces per major region, sorted) is generated
from grace_flags.tsv (gen_data.py) with _BOSS_GATED_GRACE_FLAGS / _ARENA_GRACE_FLAGS already excluded,
so a lit grace is always a real, physically-present warp point (never a sealed boss arena -> no
soft-lock). Region Locks stay the sole progression, so any seed is winnable by construction.

Client contract (region.rs: regionGraces): {"<Region> Lock": [grace_flag, ...]}; receiving the lock
sets those flags.
"""
from ..registry import Feature, register
from .. import contract

try:
    from ..region_graces import REGION_GRACE_POINTS
except Exception:  # not yet generated
    REGION_GRACE_POINTS = {}


@register
class RegionGracesFeature(Feature):
    name = "region_graces"

    def slot_data(self, world):
        kept = set(world._kept())
        region_graces = {}
        for r, fs in REGION_GRACE_POINTS.items():
            if r not in kept or not fs:
                continue
            # bundle: the lock lights the region's whole grace set.
            region_graces[f"{r} Lock"] = list(fs)
        return {contract.REGION_GRACES: region_graces}
