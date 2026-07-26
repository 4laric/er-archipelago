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
from ..contract import IMPORTANT_LOCATION_TYPES as _VALID  # shared vocab (the progression surface uses the same)


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
        # MISSABLE WINS over important. A missable check can be lost permanently, so forcing a
        # juice item onto one guarantees the player loses that item -- and the two rules are
        # outright contradictory: important says "reject filler", missable says "reject
        # progression", which leaves a location that accepts NOTHING and fails
        # test_gf_missable::test_reject_progression_accept_filler.
        #
        # It surfaced 2026-07-26 when the widened cross-region screen made f400191 (Golden Seed,
        # Stormhill Shack) missable: it is Seedtree-tagged, and Seedtree is in this option's DEFAULT
        # set, so ONE location out of 118 missable ones became unfillable. The clash was always
        # latent -- any missable check carrying a default tag would have done it -- so this is the
        # rule, not a patch for that flag.
        try:
            from ..missable_locations import MISSABLE_LOCATIONS as _MISS
        except ImportError:                                     # pragma: no cover - partial tree
            _MISS = {}
        tagged = [loc for loc in world.multiworld.get_locations(world.player)
                  if LOCATION_TAGS.get(getattr(loc, "address", None))
                  and selected.intersection(LOCATION_TAGS[loc.address])
                  and loc.address not in _MISS]
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
