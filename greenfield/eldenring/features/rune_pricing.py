"""shop price overrides for money runes and limited-currency altars.

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

Dragon Communion is the other exceptional economy. Randomising the reward must never randomise the
number of scarce hearts the altar asks for: every altar row costs exactly one unit of its own
currency (Dragon Heart, Bayle's Heart, or another costType the game assigns). The cost type stays
untouched; only ShopLineupParam.value is normalised to 1.

Cosmetic-adjacent but NOT cosmetic: the price is the only thing standing between a check and the
player. It does not touch reachability -- fill sees the same locations either way -- so this feature
never gates progression and needs no logic rules.
"""
from Options import Toggle

from ..registry import Feature, register
from .. import contract

try:
    from ..shop_data import SHOP_ROW_FLAGS, SHOP_ROW_IDS
except Exception:  # not yet generated
    SHOP_ROW_FLAGS, SHOP_ROW_IDS = {}, {}
try:
    from ..shop_stock_data import GOODS_PRICE, RUNE_PAYOUT
except Exception:  # not yet generated
    GOODS_PRICE, RUNE_PAYOUT = {}, {}
try:
    from ..item_ids import ITEM_CATALOG
except Exception:  # not yet generated
    ITEM_CATALOG = {}
try:
    from ..missable_locations import MISSABLE_LOCATIONS
except Exception:  # not yet generated
    MISSABLE_LOCATIONS = {}

_GOODS_NIBBLE = 0x40000000
_ROW_MASK = 0x0FFFFFFF

if GOODS_PRICE and not RUNE_PAYOUT:
    # TOLERANCE REQUIRES TELEMETRY. Without RUNE_PAYOUT every rune keeps GOODS_PRICE = 10x its
    # payout, which is indistinguishable from "the feature is off" until a player says so -- three
    # times. warnings.warn, not print: pytest captures stdout into a void.
    import warnings
    warnings.warn("rune_pricing: RUNE_PAYOUT is EMPTY while GOODS_PRICE is populated -- the world "
                  "needs a -Greenfield regen. Until then every rune shop slot keeps its inherited "
                  "10x price.", RuntimeWarning)

# `Golden Rune [7]`, `Hero's Rune [3]`, `Lord's Rune`, `Numen's Rune`. Anchored so a hypothetical
# "Rune Arc" or "Great Rune" never matches -- those are not money and must keep their price.
# RETIRED 2026-07-30 -- kept only as this note. Rune-ness used to be
#     _RUNE_RE = ^(?:Golden|Hero's|Lord's|Numen's) Rune(?: \[\d+\])?$
# an anchored name whitelist. It matched all 21 base-game money runes and MISSED all eleven DLC ones
# (Shadow Realm Rune [1..7], Rune of an Unsung Hero, Marika's, Leda's, Broken Rune). A miss is not a
# skip: the caller falls through to GOODS_PRICE, which for a rune is sellValue*10, so the whitelist
# was re-pricing every DLC rune at EXACTLY the 10x bug this module exists to remove -- through two
# separate "10x fixed" commits and three player reports. The predicate now comes from
# RUNE_PAYOUT (gen_data: refId_default -> SpEffectParam.soul, sortGroupId 100), so the next DLC
# needs no edit here. The old regex survives as a CROSS-CHECK in test_gf_rune_pricing: everything it
# matched must still be priced.

# The roll is [0, PRICE_MULT x worth].
#
# 2 = "up to double" (Alaric 2026-07-25) -- a rune could be a bargain or a rip-off, which is what
# "randomized" should mean. Changed to 1 on 2026-07-29 at Alaric's call, as a DIAGNOSTIC as much as a
# tuning: at 1x every rune is priced at or below its payout, so buying one is never a loss. If a rune
# still shows above its payout in game after this, the displayed price is provably not the one we
# wrote, and the fault is downstream of the generator.
#
# Context: the world was cleared of the reported bug by reading his own seed -- 117 rune slots,
# 38% below worth, min 0.003x, and four BELOW-value runes at the very merchant in the screenshot
# (Golden Rune [4] paying 1200 for 378). The two prices he photographed, 419 and 1011, matched rows
# 101863 and 101867 exactly, which also proves the client applies what we send. At 1x there is no
# above-value case left to mistake for one.
PRICE_MULT = 1

# ⭐ WORTH IS THE PAYOUT, NOT THE SHOP PRICE. GOODS_PRICE is what a MERCHANT charges, and for runes
# that is a 10x markup over what the rune actually gives you. Priced off it, a Golden Rune [10] --
# 5000 runes in your pocket -- cost up to 125000, which is not a gamble, it is the same
# never-press-it slot in a new hat. (Alaric, playtest 2026-07-25: "rune prices are too high" --
# 34191, 78140, 192430 on screen.)
#
# The 10x is DERIVED, not assumed. GOODS_PRICE // 10 reproduces the entire published Golden Rune
# payout ladder exactly -- 200, 400, 800, 1200, 1600, 2000, 2500, 3000, 3800, 5000, 6250, 7500,
# 10000 for [1]..[13] -- which is 13 independent confirmations, not a coincidence. It follows from
# gen_data's own chain: a rune has no vanilla shop row, so its GOODS_PRICE falls through to
# sellValue*10, and for a rune sellValue IS the payout.
#
# NO LONGER THE SOURCE OF WORTH, as of 2026-07-30 -- `rune_worth` reads RUNE_PAYOUT
# (SpEffectParam.soul), the payout the game itself ships. This constant is retained as the
# CROSS-CHECK: test_gf_rune_pricing asserts soul == GOODS_PRICE // 10 for every money rune, so the
# two independent derivations must keep agreeing or the test says which one moved. Measured
# 2026-07-30: they agree on all 32, and the only two soul-granting goods where they DISAGREE (91,
# 98) are excluded by sortGroupId because both have a real vanilla shop row -- i.e. the divisor was
# always an inference about how GOODS_PRICE was derived, and soul is not.
GOODS_PRICE_MARKUP = 10


def rune_worth(full_id):
    """What the rune is WORTH to the player (its rune payout), or None if it cannot be derived."""
    return RUNE_PAYOUT.get(full_id & _ROW_MASK) or None


def is_rune(full_id):
    """Is this FullID a money rune? Answered from the game's own datum -- see RUNE_PAYOUT."""
    if not full_id or (full_id & 0xF0000000) != _GOODS_NIBBLE:
        return False
    return (full_id & _ROW_MASK) in RUNE_PAYOUT


def is_rune_item(name):
    """Name-keyed shim over `is_rune`, for callers that only hold a display name.

    It resolves through ITEM_CATALOG rather than matching the name itself. A name that is not in the
    catalog is not a rune we can price, which is the same answer the old regex gave for junk input.
    """
    full = ITEM_CATALOG.get(name or "")
    return bool(full) and is_rune(full)


def fixed_alt_currency_prices():
    """ShopLineupParam row -> 1 for every generated limited-currency altar check."""
    alt_location_ids = {
        str(int(aid)) for aid, source in MISSABLE_LOCATIONS.items()
        if str(source).startswith("alt_currency:")
    }
    return {
        str(int(row_id)): 1
        for aid in alt_location_ids
        for row_id in SHOP_ROW_IDS.get(aid, [])
    }, alt_location_ids


class RuneShopPricing(Toggle):
    """Randomise the rune price of shop slots whose reward is a Golden/Hero's/Lord's/Numen's Rune,
    to somewhere in [0, 2x that rune's own worth]. Off = the slot keeps the price of the ware it
    used to sell, which for a rune reward is usually far more than the rune is worth."""
    display_name = "Randomise Rune Shop Prices"
    # 🛑 EXPLICIT, not inherited, because this option was FROZEN AT 1 until 2026-08-12 and a frozen
    # option's class default is unreachable -- so it sits there unread and rots
    # ([[er-unfreezing-an-option-needs-the-class-default]]: PoolBuilderIntensity was frozen at `max`
    # over a `default = high` nobody could see, and unfreezing it silently reverted every seed).
    # Writing the 0 down makes "off unless you ask" a decision on the page instead of an inherited
    # accident, and `test_gf_rune_pricing` pins it.
    default = 0


@register
class RunePricing(Feature):
    name = "rune_pricing"
    OPTIONS = {"rune_shop_pricing": RuneShopPricing}

    def slot_data(self, world):
        # RULING (#231, 2026-08-18): every Dragon Communion / other alt-currency altar row costs
        # exactly ONE unit of the currency selected by its unchanged costType.  The generated
        # missable table is the reviewed costType != 0 classification; joining it back through
        # SHOP_ROW_IDS avoids a second, hand-maintained altar list.
        out, alt_location_ids = fixed_alt_currency_prices()

        opt = getattr(world.options, "rune_shop_pricing", None)
        if opt is None or not int(getattr(opt, "value", 0)):
            return {contract.SHOP_RUNE_PRICES: out}
        if not (SHOP_ROW_FLAGS and SHOP_ROW_IDS and GOODS_PRICE and ITEM_CATALOG):
            return {contract.SHOP_RUNE_PRICES: out}

        player = world.player
        priced = unpriced = 0
        _ratios = []          # price/worth per slot, for the distribution line below
        for loc in world.multiworld.get_locations(player):
            aid = getattr(loc, "address", None)
            if aid is None or str(aid) not in SHOP_ROW_FLAGS:
                continue
            if str(aid) in alt_location_ids:
                continue          # fixed one-heart ruling outranks the optional money-rune roll
            it = getattr(loc, "item", None)
            if it is None or getattr(it, "player", None) != player:
                continue          # a foreign reward is not sold natively; its slot shows a placeholder
            if not is_rune_item(it.name):
                continue
            full = ITEM_CATALOG.get(it.name)
            if full is None or (full & 0xF0000000) != _GOODS_NIBBLE:
                continue
            worth = rune_worth(full)
            if not worth:
                # REFUSE rather than invent a price: an unpriced rune left at the slot's own cost is
                # the status quo, while a made-up one could be anything. Counted, not swallowed.
                unpriced += 1
                continue
            price = world.random.randint(0, PRICE_MULT * int(worth))
            _ratios.append(price / float(worth))
            for row_id in SHOP_ROW_IDS.get(str(aid), []):
                out[str(int(row_id))] = price
            priced += 1
        if priced or unpriced:
            import logging
            log = logging.getLogger("Greenfield")
            # 🛑 REPORT THE DISTRIBUTION, NOT JUST THE COUNT. "repriced N slots" is true whether the
            # roll lands where it should or piles every rune above its value -- which is exactly what
            # was reported in game 2026-07-29 ("i have never seen a single rune priced below its
            # value") while this code was, measurably, correct. A count with no shape cannot tell the
            # two apart, so the generate log now carries the shape and any future report is one
            # grep from an answer instead of a session of guessing.
            if _ratios:
                _r = sorted(_ratios)
                _below = sum(1 for x in _r if x < 1.0)
                log.info(
                    "[eldenring:%s] rune pricing: %d slot(s) into [0, %dx worth] -- price/worth "
                    "min %.2f median %.2f max %.2f, %d of %d BELOW worth (%.0f%%); %d left at the "
                    "slot's own price (no derived worth)",
                    player, priced, PRICE_MULT, _r[0], _r[len(_r) // 2], _r[-1],
                    _below, len(_r), 100.0 * _below / len(_r), unpriced)
                if _below == 0:
                    log.warning(
                        "[eldenring:%s] rune pricing: NOT ONE of %d rune slots is priced below its "
                        "worth. A uniform [0, %dx] roll should put about half of them there -- "
                        "suspect the worth derivation before the roll.", player, len(_r), PRICE_MULT)
            else:
                log.info(
                    "[eldenring:%s] rune pricing: %d rune shop slot(s) repriced into [0, %dx worth], "
                    "%d left at the slot's own price (no derived worth)",
                    player, priced, PRICE_MULT, unpriced)
        return {contract.SHOP_RUNE_PRICES: out}
