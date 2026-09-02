"""Reachability for checks whose physical pickup and sweep routes differ."""

from __future__ import annotations

from typing import Dict, Set

from ..registry import Feature, register


# AP location id -> region required to reach the physical pickup.
ALTERNATE_ACCESS: Dict[int, str] = {
    # Listed under Belurat, but physically accessible only from Enir-Ilim. Divine Beast
    # Dancing Lion's sweep is the independent Belurat-side route.
    7771810: "Enir Ilim",
    # Divine Tower of East Altus physically belongs to Altus's runtime bucket, but its only
    # ordinary entrance is the greatbridge from Leyndell's eastern ward (#324). Keep these checks
    # in Altus so the kick-watch agrees with their ground, then require Leyndell as the second half
    # of the route. The Fell Twins sweep is not an independent route: killing the twins already
    # required crossing that bridge.
    7770679: "Leyndell",
    7772342: "Leyndell",
    7772343: "Leyndell",
    7772344: "Leyndell",
    7772345: "Leyndell",
    7772346: "Leyndell",
    7772347: "Leyndell",
}

# Only these checks have a boss-sweep route that genuinely avoids their physical route.
SWEEP_INDEPENDENT = frozenset({7771810})

# Static census ownership is separate from physical access. Keep it explicit so tests and future
# generated summaries only subtract a conditionally omitted check when its owning region was part
# of the seed's static count in the first place.
OWNING_REGION: Dict[int, str] = {
    7771810: "Belurat",
    7770679: "Altus",
    7772342: "Altus",
    7772343: "Altus",
    7772344: "Altus",
    7772345: "Altus",
    7772346: "Altus",
    7772347: "Altus",
}


def _swept_members(world) -> Set[int]:
    from .boss_locks import enabled_sweeps

    cached = getattr(world, "_gf_cross_region_swept_members", None)
    if cached is not None:
        return cached
    members = {
        int(location_id)
        for members in enabled_sweeps(world).values()
        for location_id in members
    }
    world._gf_cross_region_swept_members = members
    return members


def location_available(world, location_id: int) -> bool:
    """Whether *location_id* has at least one route in this generated seed."""

    required_region = ALTERNATE_ACCESS.get(location_id)
    if required_region is None:
        return True
    sweep_route = location_id in SWEEP_INDEPENDENT and location_id in _swept_members(world)
    return sweep_route or required_region in world._kept()


@register
class CrossRegionAccess(Feature):
    name = "cross_region_access"

    def set_rules(self, world) -> None:
        swept = _swept_members(world)
        player = world.player
        for location_id, required_region in ALTERNATE_ACCESS.items():
            if location_id in SWEEP_INDEPENDENT and location_id in swept:
                continue
            location = next(
                (candidate for candidate in world.multiworld.get_locations(world.player)
                 if candidate.address == location_id),
                None,
            )
            if location is None:
                continue
            previous_rule = location.access_rule
            location.access_rule = (
                lambda state, previous_rule=previous_rule, required_region=required_region:
                previous_rule(state) and state.can_reach(required_region, "Region", player)
            )
