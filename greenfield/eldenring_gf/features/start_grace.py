"""SPEC-PARITY Track A -- starting grace / start region (matt-free).

At spawn the player must have ONE grace lit so they can warp into the world; without it the opening
is unplayable (the connect log shows startGraces=0, startRegion=""). This feature emits:

  startRegion (str)  : the always-kept starting region -- the first region of the kept spine. For
                       num_regions_order='spine' this is Limgrave (SPINE is Limgrave-first); for
                       'rolled' it is whatever region compute_kept placed first. Either way it is
                       world._kept()[0], which is guaranteed non-empty (compute_kept never returns an
                       empty kept list -- core._eligible_regions is defensively never empty).
  startGraces (list[int]) : the front-door grace flag(s) of that start region, so the player can warp
                       there at spawn. REGION_GRACE_POINTS[start_region][0] is the front-door grace
                       (same first-flag convention grace_rando uses for its per-region freebie). The
                       client (startgrants.rs parse) reads startGraces as Vec<u32> via as_u64(); a
                       plain Python int list serializes to JSON numbers it accepts, and core.rs uses
                       start_graces.first() as the clobber read-back sentinel.

Matt-free: derived only from greenfield's own generated region_graces + region_spine (via
world._kept()); no imported/eldenring data. ASCII only.

Collision note: grace_rando.py used to emit "startGraces": [] (a placeholder). This feature now OWNS
startGraces, so that placeholder was removed from grace_rando (merge_slot_data raises on duplicate
top-level keys). grace_rando keeps regionGraces + graceItems; the front-door freebie it lights on a
region LOCK receipt is unchanged -- this feature additionally lights the START region's front door at
spawn (before any lock is received) so the very first warp is possible.
"""
from Options import DefaultOnToggle
from ..registry import Feature, register
from .. import contract

try:
    from ..region_graces import REGION_GRACE_POINTS
except Exception:  # not yet generated
    REGION_GRACE_POINTS = {}


class RevealAllMaps(DefaultOnToggle):
    """Reveal the whole world map (and the underground view) at the start, so you can navigate the
    shattered world. On by default. The client (startgrants.rs) owns the RE'd flag set -- base map
    reveal flags + underground view-unlock 82001 -- and applies them once, gated on the settled
    world; greenfield just requests it via this bool."""
    display_name = "Reveal All Maps"


@register
class StartGrace(Feature):
    name = "start_grace"
    OPTIONS = {"reveal_all_maps": RevealAllMaps}

    def slot_data(self, world):
        reveal = bool(world.options.reveal_all_maps.value)
        kept = world._kept()
        if not kept:
            return {contract.START_REGION: "", contract.START_GRACES: [], contract.REVEAL_ALL_MAPS: reveal}
        start_region = kept[0]
        graces = REGION_GRACE_POINTS.get(start_region) or []
        # front-door grace only: the first (front-door-first) warp grace of the start region.
        start_graces = [int(graces[0])] if graces else []
        return {contract.START_REGION: str(start_region), contract.START_GRACES: start_graces,
                contract.REVEAL_ALL_MAPS: reveal}
