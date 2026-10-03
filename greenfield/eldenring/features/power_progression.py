"""Ordered talisman families; weapon/Rune Level caps are not exposed until enforced natively."""
from collections import Counter

from Options import Toggle, OptionError
from ..registry import Feature, register

# Append-only identities, independent of feature import order and catalogue sorting.
FAMILY_NAMES = (
    "Arsenal Charm", "Boltdrake Talisman", "Cerulean Amber Medallion",
    "Cerulean Seed Talisman", "Clarifying Horn Charm", "Crimson Amber Medallion",
    "Crimson Seed Talisman", "Dragoncrest Shield Talisman", "Erdtree's Favor",
    "Flamedrake Talisman", "Haligdrake Talisman", "Immunizing Horn Charm",
    "Mottled Necklace", "Pearldrake Talisman", "Spelldrake Talisman",
    "Stalwart Horn Charm", "Viridian Amber Medallion",
)
ITEM_IDS = {"Progressive " + name: 7920000 + index
            for index, name in enumerate(FAMILY_NAMES)}
FEATURE_TAG = "progressive_talismans_v1"


def enabled(world):
    return bool(getattr(getattr(world.options, "progressive_talismans", None), "value", 0))


def families(catalogue, excluded=()):
    """Derive numbered siblings from real accessory IDs; no unrelated replacements."""
    excluded = set(excluded)
    result = {}
    for base in FAMILY_NAMES:
        names = [base] + [base + " +" + str(rank) for rank in range(1, 4)]
        members = [name for name in names if name in catalogue and name not in excluded
                   and catalogue[name] >> 28 == 2]
        if len(members) > 1:
            result["Progressive " + base] = members
    return result


def remap_rewards(world, pool, filler_name):
    """One receipt per physical family member, after every reward contributor has run.

    Small seeds keep their existing family copy counts. One kept +3 becomes the base;
    two kept variants become base/+1. Surplus copies become ordinary filler rather
    than a second progressive reward after the last rung. No filler economy is spent
    topping up families whose higher ranks did not fit this seed.
    """
    if not enabled(world):
        return pool
    ladders = families(world.tables.item_catalog, getattr(world, "gf_dlc_excluded", ()))
    substitution = {member: name for name, members in ladders.items() for member in members}
    counts = Counter()
    result = []
    for item in pool:
        name = substitution.get(item.name, item.name)
        if name in ladders:
            counts[name] += 1
            name = name if counts[name] <= len(ladders[name]) else filler_name
        result.append(item if name == item.name else world.create_item(name))
    world.gf_talisman_ladders = ladders
    return result


class ProgressiveTalismans(Toggle):
    """Receive numbered talisman families in order: base, +1, +2, then +3.

    Replaces existing family rewards one-for-one; short seeds may stop early.
    Respects DLC gear exclusions. Unrelated and already owned talismans stay.
    Requires item shuffle; incompatible with vanilla placement and family
    start inventory. Off by default.
    """
    display_name = "Progressive Talisman Families"
    default = 0


@register
class PowerProgression(Feature):
    name = "power_progression"
    OPTIONS = {"progressive_talismans": ProgressiveTalismans}

    def generate_early(self, world):
        if not enabled(world):
            return
        from .vanilla_placement import is_on
        if not world._shuffle_on() or is_on(world):
            raise OptionError("progressive_talismans requires item_shuffle on and vanilla_placement off.")
        members = {member for ladder in families(world.tables.item_catalog).values() for member in ladder}
        for key in ("start_inventory", "start_inventory_from_pool"):
            inventory = getattr(getattr(world.options, key, None), "value", {})
            if any(name in members or name in ITEM_IDS for name, count in inventory.items() if count):
                raise OptionError("progressive_talismans cannot be combined with talisman family "
                                  "start inventory; remove those starting talismans or disable the option.")

    def slot_data(self, world):
        return {"requiresClientFeatures": [FEATURE_TAG]} if enabled(world) else {}


def grant_ladders(world):
    if not enabled(world):
        return {}
    catalogue = world.tables.item_catalog
    return {name: [{"goods": catalogue[member], "flags": [], "consumed": True}
                   for member in members]
            for name, members in getattr(world, "gf_talisman_ladders", {}).items()}
