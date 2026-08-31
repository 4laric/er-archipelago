"""Reroll repeatable mine-stone asset rewards to consumables, per seed.

The 1.17 source census joins placed MSB assets to AssetEnvironmentGeometryParam and then to
ItemLotParam_map.  It proves that 133 placed deposits share 11 unflagged, repeatable, break-on-pickup
lot templates.  These are not AP checks and must stay that way.

This feature rewrites only slot 1's GOODS row id for those 11 lots.  It does not alter quantities,
weights, flags, asset presence, respawn behavior, inventory, or location count.  Ancient Dragon
capstones are absent from the eligible table.  Because the game keys the reward by shared asset model,
all deposits of one original tier receive the same seed-selected replacement.
"""
import random as _random

from Options import DefaultOnToggle

from .. import contract
from ..registry import Feature, register

try:
    from ..item_ids import ITEM_CATALOG
except ImportError:
    ITEM_CATALOG = {}

try:
    from ..mine_material_data import MINE_MATERIAL_LOTS
except ImportError:
    MINE_MATERIAL_LOTS = ()

try:
    from ..repeatable_goods import REPEATABLE_GOODS
except ImportError:
    REPEATABLE_GOODS = frozenset()


_GOODS_CATEGORY = 0x40000000
_ROW_ID_MASK = 0x0FFFFFFF

# A mine node grants one item, so exclude categories whose useful bundle size depends on itemCounts
# (ammunition/pots/perfumes), progression-like keys, upgrade materials, and runes.  Member names remain
# owned by filler_curation.CATEGORIES; this is only the policy-level category subset.
_CATEGORIES = ("throwables", "greases", "foods", "boluses", "utility", "funny")


class RerollMineMaterials(DefaultOnToggle):
    """Reroll repeatable mine-stone deposits to useful consumables, per seed.

    Deposits remain ordinary respawning world pickups, not Archipelago checks.  All deposits that
    originally shared one stone tier also share one replacement for the seed.  Ancient Dragon and
    Somber Ancient Dragon capstones are never included.  Disable this option to keep vanilla mine
    rewards unchanged."""
    display_name = "Reroll Mine Materials"


def pool(world=None):
    """Sorted safe GOODS rows drawn from the existing curated consumable roster."""
    from .filler_curation import CATEGORIES
    excluded = set(getattr(world, "gf_dlc_excluded", ()) or ()) if world is not None else set()
    out = set()
    for category in _CATEGORIES:
        for name in CATEGORIES.get(category, ()):
            if name in excluded:
                continue
            full_id = ITEM_CATALOG.get(name)
            if full_id is None or (full_id & ~_ROW_ID_MASK) != _GOODS_CATEGORY:
                continue
            goods_id = full_id & _ROW_ID_MASK
            # A check-only ware would be swallowed by vanilla suppression when mined.
            if REPEATABLE_GOODS and goods_id not in REPEATABLE_GOODS:
                continue
            out.add(goods_id)
    return sorted(out)


@register
class MineMaterialsFeature(Feature):
    name = "mine_materials"
    OPTIONS = {"reroll_mine_materials": RerollMineMaterials}

    def slot_data(self, world):
        option = getattr(world.options, "reroll_mine_materials", None)
        if option is None or not int(option.value) or not MINE_MATERIAL_LOTS:
            return {}
        goods = pool(world)
        if not goods:
            return {}
        rng = _random.Random(f"{world.multiworld.seed}:mine_materials:{world.player}")
        return {contract.MINE_MATERIAL_ROLL: {
            str(lot): rng.choice(goods) for lot in sorted(MINE_MATERIAL_LOTS)
        }}
