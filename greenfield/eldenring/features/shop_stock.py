"""shop_stock -- reroll the INFINITE-STOCK shop rows to high-impact consumables, per seed.

WHAT
----
455 ShopLineupParam rows have no `eventFlag_forStock`, and every one is `sellQuantity == -1`
(unlimited). No flag means no way to observe a purchase, so they can never be AP checks. That is not a
bug -- nothing touches them today, they simply sell their vanilla ware forever, which is why a merchant
still stocks a vanilla Flail in a randomised seed.

Alaric's idea (2026-07-11): don't make them checks. REROLL them. Each seed, every infinite row is
rewritten to a random high-impact consumable, so merchants stock an infinite supply of *something
useful*. GOODS ONLY, deliberately -- infinite stock is only interesting for what you CONSUME. ("I don't
need 30 flails.")

THE POOL is filler_curation.CATEGORIES, unforked. That is already Alaric's curated Nightreign-inspired
roster: crafted throwables, throwing pots (incl. the DLC Hefty ones), greases, foods (Pickled Turtle
Neck, Well-Pickled Turtle Neck, Starlight Shards, Boiled Crab/Prawn), boluses, DLC perfumes, Rune Arc,
Stonesword Key, Imbued Sword Key. No spells, no key items beyond those, no remembrances, no raw crafting
materials (finished throwables instead). Keeping ONE list means the roster can't drift between the two
features that read it.

PRICE IS LOAD-BEARING
---------------------
The 455 rows carry the price of the item they USED to sell:

    116 Gem (Ash of War) rows cost 1 RUNE.  166 of the 332 armor rows are FREE.

Reroll a consumable into one of those at the inherited price and every seed ships an infinite free Rune
Arc / Stonesword Key dispenser. With 282 near-free slots, the odds that at least one lands something
economy-breaking are ~1: that is not "some seeds you get lucky", it is a guaranteed dominant strategy in
every seed. So we send a PRICE with every roll, derived from the item itself (vanilla shop price ->
basicPrice -> sellValue*10; see gen_data GOODS_PRICE). The reroll then costs what the item is WORTH, the
economy is neutral by construction, and no roster item has to be excluded on economy grounds.

CROSS-TYPE: rerolling an armor/gem/weapon row to a GOODS item is a cross-category rewrite. That was
blocked by SHOP_CTD_GUARD until 2026-07-11; the guard is now removed (the CTD repro is believed
confounded by bag-add nulling, which is dead code). This feature therefore RIDES on that being true --
if the shop-buyout playtest CTDs, this comes out with the guard.

Deterministic: rolled from world.random, so a seed always produces the same stock.
"""
import random as _random

from Options import DefaultOnToggle

from ..registry import Feature, register
from .. import contract

try:
    from ..shop_stock_data import INFINITE_SHOP_ROWS, GOODS_PRICE
except ImportError:                      # pre-regen: feature is simply inert
    INFINITE_SHOP_ROWS, GOODS_PRICE = [], {}

try:
    from ..item_ids import ITEM_CATALOG
except ImportError:
    ITEM_CATALOG = {}

_GOODS_CATEGORY = 0x40000000
_ROW_ID_MASK = 0x0FFFFFFF
_EQUIP_TYPE_GOODS = 3


class RerollInfiniteShopStock(DefaultOnToggle):
    """Reroll every unlimited-stock merchant slot to a random high-impact consumable, priced at what it
    is worth. Those slots can never be AP checks (no stock flag = no way to see a purchase), so without
    this they sell their vanilla ware forever."""
    display_name = "Reroll Infinite Shop Stock"


def pool():
    """The roster, as {name: goods_row_id}. filler_curation.CATEGORIES is the single source of truth --
    do NOT fork a second list here. Only GOODS that are in the catalog AND have a derived price survive:
    a good with no price would inherit the row's (often free) one, which is the whole failure mode."""
    from .filler_curation import CATEGORIES
    out = {}
    for names in CATEGORIES.values():
        for nm in names:
            fid = ITEM_CATALOG.get(nm)
            if fid is None or (fid & ~_ROW_ID_MASK) != _GOODS_CATEGORY:
                continue                      # not in the catalog, or not a GOOD
            rid = fid & _ROW_ID_MASK
            if rid in GOODS_PRICE:            # no derived price -> would inherit a free slot. Drop.
                out[nm] = rid
    return out


@register
class ShopStockFeature(Feature):
    name = "shop_stock"
    OPTIONS = {"reroll_infinite_shop_stock": RerollInfiniteShopStock}

    def slot_data(self, world):
        opt = getattr(world.options, "reroll_infinite_shop_stock", None)
        if opt is None or not int(opt.value) or not INFINITE_SHOP_ROWS:
            return {}
        p = pool()
        if not p:
            return {}
        rids = sorted(p.values())             # sorted list => a stable draw order
        # A DEDICATED RNG, not world.random. fill_slot_data may be called more than once (the AP world
        # tests call it twice and assert the result is identical), and drawing from the shared stream
        # both advances it -- perturbing every later consumer -- and makes the second call return a
        # DIFFERENT roll. Seeding off the multiworld seed + player keeps the roll a pure function of the
        # seed: idempotent across calls, still different across seeds, and it consumes none of the
        # shared entropy.
        rng = _random.Random(f"{world.multiworld.seed}:shop_stock:{world.player}")
        roll = {}
        for row in INFINITE_SHOP_ROWS:        # already sorted by gen_data
            gid = rng.choice(rids)
            roll[str(row)] = [gid, _EQUIP_TYPE_GOODS, GOODS_PRICE[gid]]
        return {contract.SHOP_INFINITE_STOCK: roll}
