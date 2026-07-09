"""Region grace lighting -- non-optional. Receiving a region's Lock lights that region's grace warp
flags so the player can warp in (BUNDLE: a lock lights ALL of the region's graces).

Region-keyed, matt-free. REGION_GRACE_POINTS (all warp graces per major region, sorted) is generated
from grace_flags.tsv (gen_data.py) with _BOSS_GATED_GRACE_FLAGS / _ARENA_GRACE_FLAGS already excluded,
so a lit grace is always a real, physically-present warp point (never a sealed boss arena -> no
soft-lock). Region Locks stay the sole progression, so any seed is winnable by construction.

Attunement interaction (features/attunement.py, opt-in): when the attunement gate is ON, the lock
lights ONLY the K seeded random-start graces (world.gf_attunement[region]["region_lit"]); the region's
remaining graces bloom on attunement (regionAttunement.bloom_flags, emitted by the attunement feature).
When the gate is OFF (default) the lock lights the region's whole grace bundle.

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
        att = getattr(world, "gf_attunement", None)   # attunement plan, or None when the gate is off
        region_graces = {}
        for r, fs in REGION_GRACE_POINTS.items():
            if r not in kept or not fs:
                continue
            if att is not None:
                # attunement gate: the lock lights ONLY the K seeded random-start graces; the region's
                # remaining graces bloom on attunement (regionAttunement.bloom_flags).
                region_graces[f"{r} Lock"] = list(att.get(r, {}).get("region_lit", [fs[0]]))
            else:
                # bundle: the lock lights the region's whole grace set.
                region_graces[f"{r} Lock"] = list(fs)
        return {contract.REGION_GRACES: region_graces}
