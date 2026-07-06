"""varied_filler -- received filler is real ER junk consumables, not a monotone Rune (matt-free).

greenfield's non-juice filler is otherwise all one item (Golden Rune [1]); in a multiworld that hands
co-op partners a wall of identical Runes. This draws each filler grant from FILLER_POOL (goods-tier
consumables/materials the catalog resolved -- greases, boluses, butterflies, smithing stones, ...),
so filler feels like real loot. Count-neutral, fill-safe (all filler-classified), deterministic
(world.random). Composes UNDER pool_builder: pool_builder still juices the top of the tail with
rare/legendary equippables; this varies whatever filler remains. On by default.
"""
from Options import DefaultOnToggle
from ..registry import Feature, register


class VariedFiller(DefaultOnToggle):
    """Received filler items are a varied mix of real ER consumables/materials instead of all being
    the same Golden Rune. On by default; off = the monotone Rune filler."""
    display_name = "Varied Filler"


@register
class VariedFillerFeature(Feature):
    name = "varied_filler"
    OPTIONS = {"varied_filler": VariedFiller}
    # No slot_data key + no items: filler items are already ITEM_CATALOG entries core registers, and
    # the choice happens in core.create_items / get_filler_item_name. This feature only adds the option.
