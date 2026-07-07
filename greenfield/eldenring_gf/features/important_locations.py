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
_VALID = ["Remembrance", "Seedtree", "Church", "Boss", "Fragment", "Revered", "Basin", "Shop",
          "Legendary", "GreatRune", "KeyItem"]


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
        # Fill-safety: only force non-filler where the pool can ACTUALLY supply it. The reject-filler
        # rule needs FREELY-PLACEABLE non-filler ("juice" = useful & not advancement) -- items fill can
        # drop on an arbitrary tagged location. This world's advancement pool is structural region Locks
        # (always ~21), which fill pins by reachability logic and CANNOT satisfy an arbitrary tagged loc,
        # so they must not count toward supply. Counting advancement (the old `avail`) let item_shuffle
        # off seeds pass the gate on locks alone (avail>=tagged) then FillError, since the juice pool is
        # empty -- e.g. important_locations=["Fragment"] gave 21 tagged vs 21 Locks / 0 juice (FillError),
        # and 6 tagged vs 15 Locks / 0 juice. Key the gate off juice: skip cleanly when it can't cover
        # every tagged loc -- the feature is moot without real freely-placeable items anyway.
        juice = sum(1 for i in world.multiworld.itempool
                    if i.player == world.player
                    and bool(i.classification & ItemClassification.useful)
                    and not i.advancement)
        if juice < len(tagged):
            return
        for loc in tagged:
            prev = loc.item_rule
            loc.item_rule = lambda item, p=prev: p(item) and _is_important(item)
