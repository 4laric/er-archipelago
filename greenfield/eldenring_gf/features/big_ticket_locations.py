"""big_ticket_locations -- CONFIGURABLE big-ticket set (SPEC-gf-configurable-big-ticket-20260708).

Big-ticket drives BOTH region-Lock placement (features/curated_fill) and the client F6 tracker. This
feature owns the OptionList and emits the per-seed result to slot_data so the client stays in lockstep
with where the locks actually go (no drift): it ships `bigTicketLocations` = the AP location ids for
which contract.is_big_ticket(tags, <selection>) holds. Same class vocabulary as important_locations;
Enia's remembrance store (EniaShop tag) is a permanent hard-exclude and is never selectable.
"""
from Options import OptionList
from ..registry import Feature, register
from .. import contract

try:
    from ..location_tags import LOCATION_TAGS
except Exception:  # not yet generated -> emit nothing (client falls back to the static default)
    LOCATION_TAGS = {}


class BigTicketLocations(OptionList):
    """Location classes that count as big-ticket -- region Locks land on them (with curated_fill) and
    the F6 tracker stars/filters them. Drawn from the same vocabulary as Important Locations. Default =
    Boss, Remembrance, Legendary, GreatRune, KeyItem. Enia's remembrance store is ALWAYS excluded, even
    if you select Shop or Legendary; selecting Shop turns on the OTHER shops."""
    display_name = "Big-Ticket Locations"
    default = list(contract.BIG_TICKET_DEFAULT_LIST)
    valid_keys = frozenset(contract.IMPORTANT_LOCATION_TYPES)


def _selected(world):
    opt = getattr(world.options, "big_ticket_locations", None)
    sel = set(opt.value) if opt is not None else set(contract.BIG_TICKET_TYPES)
    return sel & set(contract.IMPORTANT_LOCATION_TYPES)


@register
class BigTicketLocationsFeature(Feature):
    name = "big_ticket_locations"
    OPTIONS = {"big_ticket_locations": BigTicketLocations}

    def slot_data(self, world):
        sel = _selected(world)
        ids = sorted(
            loc.address
            for loc in world.multiworld.get_locations(world.player)
            if getattr(loc, "address", None) is not None
            and contract.is_big_ticket(LOCATION_TAGS.get(loc.address), sel)
        )
        return {contract.BIG_TICKET_LOCATIONS: ids}
