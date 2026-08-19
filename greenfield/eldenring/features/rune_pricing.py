"""shop price overrides for finite AP checks and limited-currency altars.

Finite shop checks receive a seed-seeded price in ``[0, 5000]`` independent of their reward. That
restores the fun one-shot arbitrage where a valuable money rune can land on a cheap shelf, without
making the price itself an item hint. Every row belonging to one AP check receives the same price.

Infinite shelves are deliberately outside this feature. ``shop_stock`` prices their rerolled ware at
its value (and a money rune at its exact payout), so a lucky finite flip cannot become an unlimited
rune farm.

The rune helpers in this module still cover every money-rune family. ``shop_stock`` needs that datum
to recognize unlimited rune shelves and price them at their exact payout; narrowing it to Golden
Runes would leave the same exploit on Hero's, Lord's, Numen's, and DLC runes.

Dragon Communion is the other exceptional economy. Randomising the reward must never randomise the
number of scarce hearts the altar asks for: every altar row costs exactly one unit of its own
currency (Dragon Heart, Bayle's Heart, or another costType the game assigns). The cost type stays
untouched; only ShopLineupParam.value is normalised to 1.

Cosmetic-adjacent but NOT cosmetic: the price is the only thing standing between a check and the
player. It does not touch reachability -- fill sees the same locations either way -- so this feature
never gates progression and needs no logic rules.
"""
import random as _random

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

FINITE_PRICE_MAX = 5000

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


@register
class RunePricing(Feature):
    name = "rune_pricing"

    def slot_data(self, world):
        # RULING (#231, 2026-08-18): every Dragon Communion / other alt-currency altar row costs
        # exactly ONE unit of the currency selected by its unchanged costType.  The generated
        # missable table is the reviewed costType != 0 classification; joining it back through
        # SHOP_ROW_IDS avoids a second, hand-maintained altar list.
        out, alt_location_ids = fixed_alt_currency_prices()

        if not (SHOP_ROW_FLAGS and SHOP_ROW_IDS):
            return {contract.SHOP_RUNE_PRICES: out}

        player = world.player
        active_shop_ids = sorted({
            str(getattr(loc, "address", ""))
            for loc in world.multiworld.get_locations(player)
            if str(getattr(loc, "address", "")) in SHOP_ROW_FLAGS
            and str(getattr(loc, "address", "")) not in alt_location_ids
        }, key=int)
        # fill_slot_data may be called repeatedly for the same already-built world (the fixture
        # contract does exactly that). Consuming world.random here makes the wire move on every
        # call and also perturbs later feature output. Use a namespaced RNG so the prices vary by
        # seed/player while remaining a pure function of that seed.
        rng = _random.Random(f"{world.multiworld.seed}:finite_shop_prices:{player}")
        prices = []
        for aid in active_shop_ids:
            price = rng.randint(0, FINITE_PRICE_MAX)
            prices.append(price)
            for row_id in SHOP_ROW_IDS.get(aid, []):
                out[str(int(row_id))] = price
        if prices:
            import logging
            log = logging.getLogger("Greenfield")
            ordered = sorted(prices)
            log.info(
                "[eldenring:%s] finite shop pricing: %d check(s) into [0, %d] -- min %d median %d "
                "max %d; %d alternate-currency check(s) fixed at one",
                player, len(prices), FINITE_PRICE_MAX, ordered[0], ordered[len(ordered) // 2],
                ordered[-1], len(alt_location_ids))
        return {contract.SHOP_RUNE_PRICES: out}
