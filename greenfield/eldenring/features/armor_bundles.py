"""Synthetic complete-armor-set items, generated from protector row families (world#849)."""
from BaseClasses import ItemClassification

from ..registry import Feature, register
from ..item_ids import ARMOR_BUNDLES


@register
class ArmorBundlesFeature(Feature):
    name = "armor_bundles"
    ITEMS = {name: ItemClassification.useful for name in ARMOR_BUNDLES}

    def slot_data(self, world):
        # Vanilla/off seeds never mint wrappers and therefore require no newer client.
        from . import vanilla_placement
        if not world._shuffle_on() or vanilla_placement.is_on(world):
            return {}
        return {
            "armorBundles": {
                str(world.item_name_to_id[name]): members
                for name, members in sorted(ARMOR_BUNDLES.items())
            },
            "requiresClientFeatures": ["armor_bundles"],
        }
