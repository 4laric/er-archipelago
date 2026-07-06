"""important_locations -- force meaningful check TYPES to hold a non-filler item (matt-free).

Parity with the old apworld's ERImportantLocations, but the type of each location is derived from
greenfield's OWN data (item_name + method -> location_tags.py), never from matt's location_name_groups.
An OptionList of types; every location tagged with a SELECTED type gets an item-rule that forbids
plain filler (it must hold a useful or progression item -- "prevent unimportant items", the same
fill-safe semantics as the old world, not a hard progression force). Default = the six meaningful
types; Basin/Shop are opt-in. Purely fill-side (no slot_data key; the client is unaffected).
"""
from Options import OptionList
from BaseClasses import ItemClassification
from ..registry import Feature, register

try:
    from ..location_tags import LOCATION_TAGS
except Exception:  # not yet generated
    LOCATION_TAGS = {}

_DEFAULT = ["Remembrance", "Seedtree", "Church", "Boss", "Fragment", "Revered"]
_VALID = ["Remembrance", "Seedtree", "Church", "Boss", "Fragment", "Revered", "Basin", "Shop"]


class ImportantLocations(OptionList):
    """Location types that must hold a useful/progression item (never plain filler). Matt-free tags
    derived from vanilla item_name + method. Default = Remembrance, Seedtree, Church, Boss, Fragment,
    Revered. Also valid: Basin (Crystal Tears), Shop (Twin Maiden Husks -- opt-in, large)."""
    display_name = "Important Locations"
    default = _DEFAULT
    valid_keys = frozenset(_VALID)


def _is_important(item) -> bool:
    return bool(item.advancement) or bool(item.classification & ItemClassification.useful)


@register
class ImportantLocationsFeature(Feature):
    name = "important_locations"
    OPTIONS = {"important_locations": ImportantLocations}

    def set_rules(self, world) -> None:
        selected = set(world.options.important_locations.value) & set(_VALID)
        if not selected or not LOCATION_TAGS:
            return
        tagged = [loc for loc in world.multiworld.get_locations(world.player)
                  if LOCATION_TAGS.get(getattr(loc, "address", None))
                  and selected.intersection(LOCATION_TAGS[loc.address])]
        if not tagged:
            return
        # Fill-safety: only force non-filler where the pool can supply it. If this player's pool has
        # fewer useful/progression items than tagged locations (e.g. item_shuffle off -> a degenerate
        # locks+Rune pool: ~44 non-filler vs ~115 tagged), enforcing would over-constrain the fill and
        # FillError/churn. Skip cleanly in that case -- the feature is moot without real items anyway.
        avail = sum(1 for i in world.multiworld.itempool
                    if i.player == world.player and _is_important(i))
        if avail < len(tagged):
            return
        for loc in tagged:
            prev = loc.item_rule
            loc.item_rule = lambda item, p=prev: p(item) and _is_important(item)
