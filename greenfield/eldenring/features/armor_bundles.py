"""Synthetic complete-armor-set items, generated from protector row families (world#849).

Option-gated since #985: `armor_bundles: false` restores the pre-#849 pool shape -- every
protector piece is its own item and no wrapper is minted. The wrapper ids stay in the catalog
either way (ITEMS is a static class attribute, resolved at import, before any option exists);
the boss_keys precedent applies: an OFF seed's pool is count-identical to an ON seed's, only
the id catalog keeps the unused wrapper names. The OFF seed emits no `armorBundles` slot_data
key and drops the `armor_bundles` client-feature demand, so an older client accepts it.
"""
from Options import Toggle
from BaseClasses import ItemClassification

from ..registry import Feature, register
from ..item_ids import ARMOR_BUNDLES


class ArmorBundles(Toggle):
    """on (default): each complete armor set compacts into one '... Set' item that grants every
    piece on receipt -- one pool slot per set, and no orphaned second helmets. off: every armor
    piece is its own item, the pre-#849 pool."""
    display_name = "Armor Bundles"
    default = 1


def armor_bundles_on(world):
    o = getattr(world.options, "armor_bundles", None)
    return True if o is None else bool(o.value)


@register
class ArmorBundlesFeature(Feature):
    name = "armor_bundles"
    OPTIONS = {"armor_bundles": ArmorBundles}
    ITEMS = {name: ItemClassification.useful for name in ARMOR_BUNDLES}

    def slot_data(self, world):
        # Vanilla/off seeds never mint wrappers and therefore require no newer client.
        from . import vanilla_placement
        if not armor_bundles_on(world) or not world._shuffle_on() or vanilla_placement.is_on(world):
            return {}
        return {
            "armorBundles": {
                str(world.item_name_to_id[name]): members
                for name, members in sorted(ARMOR_BUNDLES.items())
            },
            "requiresClientFeatures": ["armor_bundles"],
        }
