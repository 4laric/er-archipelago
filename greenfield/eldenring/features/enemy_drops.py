"""enemy_drops -- reroll the FARMABLE enemy drops to high-impact consumables, per seed.

Same predicate as the infinite shop rows, on the other table:

    A LOT WITH NO FLAG CANNOT BE A CHECK, SO IT IS FREE TO REROLL.

ItemLotParam_enemy splits cleanly:
     244 rows carry `getItemFlagId`  -> the one-time enemy/boss drop CHECKS. Never touched.
    4891 rows carry no flag          -> repeatable, farmable drops. Free.
EMEVD `AwardItemLot` references 15 lot ids and NONE is an unflagged lot, so no reward hides in the free
set. gen_data emits only the unflagged lots (REROLLABLE_ENEMY_SLOTS), so the check rows never even reach
this feature.

⚠ THE FLAG COLUMN IS `getItemFlagId`, SINGULAR. ER leaves the per-slot `getItemFlagId01..08` columns at
zero, so reading those -- the obvious guess -- reports every row as unflagged. Taking that at face value
would have handed the reroll 5047 map checks and 244 enemy-drop checks to overwrite, boss drops among
them. Same shape as the LOD-tile bug: a lookup that quietly returns nothing instead of failing.

WHAT CHANGES, AND WHAT DOESN'T
------------------------------
Only the GOODS slots are rerolled (`lotItemCategory == 1` -> FullID nibble 4, per gen_data._LOT_CAT --
NOT runes). Weapon / armor / talisman drop slots keep their vanilla contents. Every slot's
`lotItemBasePoint` (its drop WEIGHT) is left alone, so drop RATES stay exactly vanilla -- an enemy that
dropped something 5% of the time still does, it's just a different consumable. No new drops appear, none
vanish; only the identity changes.

POOL is filler_curation.CATEGORIES -- unforked, the same curated roster the filler recipe and the shop
reroll both read. One list, no drift.

Deterministic: a dedicated RNG seeded from (multiworld seed, player), NOT world.random -- fill_slot_data
is called more than once, and drawing from the shared stream would both advance it and return a
different roll each call.
"""
import random as _random

from Options import DefaultOnToggle

from ..registry import Feature, register
from .. import contract

try:
    from ..enemy_drops_data import REROLLABLE_ENEMY_SLOTS
except ImportError:                      # pre-regen: inert
    REROLLABLE_ENEMY_SLOTS = {}

try:
    from ..item_ids import ITEM_CATALOG
except ImportError:
    ITEM_CATALOG = {}

_GOODS_CATEGORY = 0x40000000
_ROW_ID_MASK = 0x0FFFFFFF


class RerollEnemyDrops(DefaultOnToggle):
    """Reroll what farmable enemies drop. Their one-time drops (the AP checks) are untouched -- only the
    repeatable, unflagged drops change, and only the consumable slots, at exactly the vanilla rates."""
    display_name = "Reroll Enemy Drops"


def pool():
    """The roster as a sorted list of goods row ids. filler_curation.CATEGORIES is the single source of
    truth -- do NOT fork a second list. Goods only (an enemy goods slot must stay a goods slot)."""
    from .filler_curation import CATEGORIES
    out = set()
    for names in CATEGORIES.values():
        for nm in names:
            fid = ITEM_CATALOG.get(nm)
            if fid is None or (fid & ~_ROW_ID_MASK) != _GOODS_CATEGORY:
                continue
            out.add(fid & _ROW_ID_MASK)
    return sorted(out)


@register
class EnemyDropsFeature(Feature):
    name = "enemy_drops"
    OPTIONS = {"reroll_enemy_drops": RerollEnemyDrops}

    def slot_data(self, world):
        opt = getattr(world.options, "reroll_enemy_drops", None)
        if opt is None or not int(opt.value) or not REROLLABLE_ENEMY_SLOTS:
            return {}
        gids = pool()
        if not gids:
            return {}
        rng = _random.Random(f"{world.multiworld.seed}:enemy_drops:{world.player}")
        roll = {}
        for lot in sorted(REROLLABLE_ENEMY_SLOTS):          # sorted => stable draw order
            # FLAT pairs [slot, goodsId, slot, goodsId, ...]. The contract's LISTVAL_INT_MAP shape is
            # list[int], not list[list[int]] -- nesting trips validate_slot_data (which is exactly what
            # it is for). Pairs keep it flat without inventing a shape.
            flat = []
            for sl in REROLLABLE_ENEMY_SLOTS[lot]:
                flat.append(sl)
                flat.append(rng.choice(gids))
            roll[str(lot)] = flat
        return {contract.ENEMY_DROP_ROLL: roll}
