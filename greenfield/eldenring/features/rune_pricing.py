"""rune_pricing -- a shop slot selling a RUNE should not cost what the slot used to cost.

A shop check keeps the price of the ware it used to sell; `shop_sell` rewrites `equipId` to the AP
reward and deliberately leaves `value` alone (the slot costs what the slot cost). That is right for
gear -- you are buying a randomised item at this merchant's price -- and wrong for runes, because a
rune IS money. A 3500-rune slot that now sells a Golden Rune [1] worth ~200 is not a gamble, it is
a slot no player will ever press, and the check behind it goes uncollected.

So: roll the price. `[0, 2x the rune's own derived worth]`, per seed, per row. Sometimes free,
sometimes a bad trade, occasionally worth it -- which is what "randomised" should mean for an item
whose only property is a number.

The worth comes from `GOODS_PRICE` (gen_data: vanilla shop price -> basicPrice -> sellValue*10), the
same chain `shop_stock` prices its infinite-row rerolls with. Deriving a SECOND price notion here
would be a fork, and the two would drift.

Scope: every rune-family consumable, not just Golden Rune. Hero's / Lord's / Numen's Runes hit the
identical wall for the identical reason, and narrowing this to the one Alaric happened to see would
be pinning the symptom (CONTRIBUTING: "derive the datum, don't pin the symptom"). A rune is anything
GOODS_PRICE prices whose name is `<X> Rune` or `<X> Rune [N]`.

Cosmetic-adjacent but NOT cosmetic: the price is the only thing standing between a check and the
player. It does not touch reachability -- fill sees the same locations either way -- so this feature
never gates progression and needs no logic rules.
"""
import re

from Options import Toggle

from ..registry import Feature, register
from .. import contract

try:
    from ..shop_data import SHOP_ROW_FLAGS, SHOP_ROW_IDS
except Exception:  # not yet generated
    SHOP_ROW_FLAGS, SHOP_ROW_IDS = {}, {}
try:
    from ..shop_stock_data import GOODS_PRICE
except Exception:  # not yet generated
    GOODS_PRICE = {}
try:
    from ..item_ids import ITEM_CATALOG
except Exception:  # not yet generated
    ITEM_CATALOG = {}

_GOODS_NIBBLE = 0x40000000
_ROW_MASK = 0x0FFFFFFF

# `Golden Rune [7]`, `Hero's Rune [3]`, `Lord's Rune`, `Numen's Rune`. Anchored so a hypothetical
# "Rune Arc" or "Great Rune" never matches -- those are not money and must keep their price.
_RUNE_RE = re.compile(r"^(?:Golden|Hero's|Lord's|Numen's) Rune(?: \[\d+\])?$")

# The roll is [0, PRICE_MULT x worth]. 2 = "up to double", Alaric 2026-07-25.
PRICE_MULT = 2


def is_rune_item(name):
    return bool(_RUNE_RE.match(name or ""))


class RuneShopPricing(Toggle):
    """Randomise the rune price of shop slots whose reward is a Golden/Hero's/Lord's/Numen's Rune,
    to somewhere in [0, 2x that rune's own worth]. Off = the slot keeps the price of the ware it
    used to sell, which for a rune reward is usually far more than the rune is worth."""
    display_name = "Randomise Rune Shop Prices"


@register
class RunePricing(Feature):
    name = "rune_pricing"
    OPTIONS = {"rune_shop_pricing": RuneShopPricing}

    def slot_data(self, world):
        opt = getattr(world.options, "rune_shop_pricing", None)
        if opt is None or not int(getattr(opt, "value", 0)):
            return {contract.SHOP_RUNE_PRICES: {}}
        if not (SHOP_ROW_FLAGS and SHOP_ROW_IDS and GOODS_PRICE and ITEM_CATALOG):
            return {contract.SHOP_RUNE_PRICES: {}}

        player = world.player
        out = {}
        priced = unpriced = 0
        for loc in world.multiworld.get_locations(player):
            aid = getattr(loc, "address", None)
            if aid is None or str(aid) not in SHOP_ROW_FLAGS:
                continue
            it = getattr(loc, "item", None)
            if it is None or getattr(it, "player", None) != player:
                continue          # a foreign reward is not sold natively; its slot shows a placeholder
            if not is_rune_item(it.name):
                continue
            full = ITEM_CATALOG.get(it.name)
            if full is None or (full & 0xF0000000) != _GOODS_NIBBLE:
                continue
            worth = GOODS_PRICE.get(full & _ROW_MASK)
            if not worth:
                # REFUSE rather than invent a price: an unpriced rune left at the slot's own cost is
                # the status quo, while a made-up one could be anything. Counted, not swallowed.
                unpriced += 1
                continue
            price = world.random.randint(0, PRICE_MULT * int(worth))
            for row_id in SHOP_ROW_IDS.get(str(aid), []):
                out[str(int(row_id))] = price
            priced += 1
        if priced or unpriced:
            import logging
            logging.getLogger("Greenfield").info(
                "[eldenring:%s] rune pricing: %d rune shop slot(s) repriced into [0, %dx worth], "
                "%d left at the slot's own price (no derived worth)",
                player, priced, PRICE_MULT, unpriced)
        return {contract.SHOP_RUNE_PRICES: out}
