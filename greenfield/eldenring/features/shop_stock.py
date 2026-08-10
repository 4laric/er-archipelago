"""shop_stock -- reroll the INFINITE-STOCK shop rows to high-impact consumables, per seed.

WHAT
----
14 ShopLineupParam rows are browsable unlimited GOODS shelves -- `equipType 3`, `mtrlId -1` (consume no
material), `costType 0` (rune-priced), `sellQuantity -1` (unlimited), no release gate, and a stock flag.
Kale's Glass Shards, Iji's Somber Smithing Stones, the throwing-knife and poison-dart shelves. They are
never AP checks because our check derivation requires `flag > 0 AND qty >= 1` and these are qty -1.

Alaric's idea (2026-07-11): don't make them checks. REROLL them.

🛑 RETARGETED 2026-07-29, and the old target set was DESTRUCTIVE, not merely useless. The predicate was
`eventFlag_forStock == 0` -- the exact inverse of a shelf -- and selected 455 rows: 332 Alter-Garments
armour-conversion rows (`mtrlId != -1`), 116 Ash-of-War duplication rows (`costType 4`, priced in **Lost
Ashes of War**), and 7 debug rows. Not one is a shelf, and two of those bands back menus a player CAN
open, so this feature was writing consumables into Boc's alteration list and the Roundtable duplication
list, and writing rune-derived prices onto rows denominated in a different currency. Every below-value
rune price a seed produced also lived there, i.e. nowhere reachable -- which is why a player reported
three times that shop runes were never worth buying and was right for a reason nobody had found
(CONTRIBUTING rule 12: a correct wire is not a correct feature).

Goods -> goods only now, so this feature no longer performs any cross-type shop write.

AMMO SHELVES ARE DELIBERATELY EXCLUDED. 55 further rows pass every clause except `equipType 3` -- the
infinite Arrow/Bolt/Greatbolt shelves. Rerolling them would remove a real supply line for bow builds
(a design decision, not a bug fix) and would flip a weapon row to goods in a browse menu, whose
rendering is untested. Extending to them needs Alaric's explicit sign-off plus an in-game render check. Each seed, every infinite row is
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
A shelf carries the price of the ware it USED to sell. Reroll a consumable onto it at the inherited
price and a cheap shelf becomes an infinite Rune Arc / Stonesword Key dispenser -- not "some seeds you
get lucky", a dominant strategy whenever it lands. So we send a PRICE with every roll, derived from the item itself (vanilla shop price ->
basicPrice -> sellValue*10; see gen_data GOODS_PRICE). The reroll then costs what the item is WORTH, the
economy is neutral by construction, and no roster item has to be excluded on economy grounds.

CROSS-TYPE: rerolling an armor/gem/weapon row to a GOODS item is a cross-category rewrite. That was
blocked by SHOP_CTD_GUARD until 2026-07-11; the guard is now removed (the CTD repro is believed
confounded by bag-add nulling, which is dead code). This feature therefore RIDES on that being true --
if the shop-buyout playtest CTDs, this comes out with the guard.

Deterministic: rolled from world.random, so a seed always produces the same stock.
"""
import random as _random

from Options import DefaultOnToggle, OptionError, OptionSet

from ..registry import Feature, register
from .. import contract

try:
    from ..shop_stock_data import INFINITE_SHOP_ROWS, GOODS_PRICE
except ImportError:                      # pre-regen: feature is simply inert
    INFINITE_SHOP_ROWS, GOODS_PRICE = [], {}

try:
    from .rune_pricing import (is_rune as _is_rune, rune_worth as _rune_worth,
                               PRICE_MULT as _PRICE_MULT)
except ImportError:                      # rune_pricing absent -> vanilla price, i.e. today's behaviour
    _is_rune = _rune_worth = None
    _PRICE_MULT = 1   # keep in step with rune_pricing.PRICE_MULT

try:
    from ..item_ids import ITEM_CATALOG
except ImportError:
    ITEM_CATALOG = {}

try:
    from .keep_out_of_shops import forbidden_goods_rows as _kept_out_rows
except ImportError:                      # feature absent -> no categories are forbidden
    _kept_out_rows = None

# name lookup for the rune check: ITEM_CATALOG is name -> FullID, we need the reverse.
_NAME_OF = {v: k for k, v in (ITEM_CATALOG or {}).items()}

try:
    from ..repeatable_goods import REPEATABLE_GOODS
except ImportError:
    REPEATABLE_GOODS = frozenset()

_GOODS_CATEGORY = 0x40000000
_ROW_ID_MASK = 0x0FFFFFFF
_EQUIP_TYPE_GOODS = 3


# ---- GUARANTEED HUB SHELVES --------------------------------------------------------------------
# Requested on Nexus (CrazzyMatthew21, 2026-07-29): an option for the Twin Maiden Husk merchants to
# sell infinite Rune Arcs and Larval Tears. Both wares are ALREADY in the reroll pool -- a seed can
# hand you an infinite Rune Arc shelf today -- so the ask is determinism, not a new capability.
#
# WHY THESE ROWS. Four of the fourteen browsable shelves bracket to Roundtable Hold, i.e. the hub,
# which is sphere 0 in every seed. They are the cheapest possible target by three measures:
#   * already `sellQuantity -1`, so the existing shopInfiniteStock wire carries them with NO client
#     change and NO new contract key (a new key moves CONTRACT_HASH, forcing a client update on
#     every player -- a steep toll for a QoL shelf);
#   * NOT AP checks (the check derivation needs flag > 0 AND qty >= 1; these are qty -1), so the
#     location pool is untouched;
#   * ORDERED LEAST-VALUABLE FIRST, the same discipline as spending describable spare-goods rows
#     first: 600020 and 600022 sell goods 15390/15210, unnamed crafting materials absent from
#     ITEM_CATALOG, so one ware costs the player nothing at all. Only a fourth request reaches
#     Miranda Powder or String.
#
# 🛑 THEIR SELLER IS INFERRED, NOT CONFIRMED IN GAME. All four bracket to "Roundtable Hold" via the
# named checks on the flags either side, and their wares match the Twin Maiden Husks' vanilla stock.
# But ShopLineupParam has no seller column, the bracket straddles a region boundary ~13% of the time,
# and these are exactly the rows test_gf_infinite_shop_rows_are_browsable_shelves calls "seller
# UNIDENTIFIED". Player-facing text therefore says "the hub", never "the Twin Maiden Husks", until
# someone has looked.
HUB_SHELF_ROWS = (600020, 600022, 600021, 600017)


class InfiniteHubWares(OptionSet):
    """Wares the hub merchant always stocks, unlimited, instead of leaving the shelf to the reroll.

    Give item names exactly as the randomiser knows them, e.g.

        infinite_hub_wares: ["Rune Arc", "Larval Tear"]

    Up to FOUR: that is how many browsable unlimited shelves the hub has, and asking for more is
    rejected at generation with a message rather than silently dropping the extras. Each ware is sold
    at its own derived price, so a shelf never becomes a free dispenser.

    Empty by default -- a fresh yaml generates exactly as it did before this option existed. Worth a
    thought before filling it: unlimited Larval Tears is unlimited respec, and unlimited Rune Arcs is
    a permanent great-rune buff. Both are real changes to how a run plays."""
    display_name = "Infinite Hub Wares"
    default = frozenset()


class RerollInfiniteShopStock(DefaultOnToggle):
    """Reroll the merchants' unlimited consumable shelves to a random high-impact consumable.

    Kale's Glass Shards, Iji's Somber Smithing Stones, the throwing-knife and poison-dart shelves --
    14 of them. Each is rerolled per seed and PRICED at what the new item is worth, so a shelf never
    becomes an infinite cheap source of something economy-breaking.

    Ammo shelves (arrows, bolts) are untouched. These shelves are never AP checks, so nothing here
    moves an item or a location."""
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
            # Same guard as the enemy-drop pool: a ware obtainable ONLY as a check arms vanilla-suppress,
            # so buying one from a rerolled slot would have the client EAT the bag-add -- you'd pay and
            # get nothing. Only stock goods that have a repeatable source.
            if REPEATABLE_GOODS and rid not in REPEATABLE_GOODS:
                continue
            if rid in GOODS_PRICE:            # no derived price -> would inherit a free slot. Drop.
                out[nm] = rid
    return out



# ---- pricing ------------------------------------------------------------------------------------
# 🛑 GOODS_PRICE IS NOT A PRICE FOR A RUNE. For a consumable it is the vanilla shop price and
# "sell it for what it is worth" is exactly right. For a rune it is `sellValue * 10`, and a rune's
# sellValue IS its payout -- so pricing a Golden Rune [5] at GOODS_PRICE charges 16,000 for 1,600
# runes. TEN TIMES its value, on every rune, in every seed.
#
# Reported by Alaric 2026-07-29: "rune pricing is bugged, i have never seen a single rune priced
# below its value ... nothing remotely close to the 0 end." The randomizer in features/rune_pricing
# was innocent -- measured over 3 seeds / 350 slots it is a clean uniform [0, 2x worth]: median
# ratio 1.03, 50% below worth, 5% below 0.10x, minimum 0.002x. It just never touched THIS path, and
# this one rerolls the 14 browsable shelves. (That figure was ~455 until 2026-07-29, and the claim
# that they were "the merchants a player stands in front of most" was false -- they were the
# Alter-Garments and AoW-duplication menus. Retargeted; see the module docstring.)
# Every targeted row is costType 0 by regen-time assertion, so a rune-derived price is well-typed here
# -- the old set included 116 rows priced in Lost Ashes of War, where it was not.
#
# So route runes through the same roll. `rune_worth` already divides out the 10x and its ladder is
# pinned by test_gf_rune_pricing (200/400/800/... for [1]..[13], 13 independent confirmations).
def _resolved_pins(world):
    """{shelf row -> goods row id} for `infinite_hub_wares`. Empty by default.

    Every rejection below names the option and the offending value, because the alternative is a
    player quietly not getting the ware they asked for -- and a shelf that silently stayed random is
    indistinguishable from the option not working.

    🛑 A PIN ON A ROW THAT IS NOT A SHELF IS A SILENT NO-OP -- the dormant class this project keeps
    getting bitten by -- so a hub row missing from INFINITE_SHOP_ROWS raises rather than shrugs.
    """
    opt = getattr(world.options, "infinite_hub_wares", None)
    wares = sorted(str(w) for w in getattr(opt, "value", ()) or ())   # sorted => deterministic rows
    if not wares:
        return {}
    if len(wares) > len(HUB_SHELF_ROWS):
        raise OptionError(
            "infinite_hub_wares lists %d wares (%s) but the hub has only %d unlimited shelves. "
            "Remove %d, or sell the rest somewhere else."
            % (len(wares), ", ".join(wares), len(HUB_SHELF_ROWS), len(wares) - len(HUB_SHELF_ROWS)))
    out = {}
    for row, ware in zip(HUB_SHELF_ROWS, wares):
        full = ITEM_CATALOG.get(ware)
        if full is None:
            raise OptionError(
                "infinite_hub_wares names %r, which is not an item this randomiser knows. Use the "
                "exact in-game name, e.g. \"Rune Arc\"." % ware)
        if (full & ~_ROW_ID_MASK) != _GOODS_CATEGORY:
            raise OptionError(
                "infinite_hub_wares names %r, which is not a GOODS item. These shelves are goods "
                "shelves -- a weapon or an armour piece cannot be stocked on one." % ware)
        gid = full & _ROW_ID_MASK
        if gid not in GOODS_PRICE:
            raise OptionError(
                "infinite_hub_wares names %r, which has no derived price, so the shelf would inherit "
                "the row's own (near-free) one -- the exact failure PRICE IS LOAD-BEARING is about. "
                "Pick a ware the game sells somewhere." % ware)
        if row not in INFINITE_SHOP_ROWS:
            raise OptionError(
                "hub shelf row %d is no longer one of the %d browsable unlimited shelves, so "
                "infinite_hub_wares would silently do nothing. Re-derive HUB_SHELF_ROWS rather than "
                "dropping this guard." % (row, len(INFINITE_SHOP_ROWS)))
        out[row] = gid
    return out


def _price_for(gid, rng):
    """What an infinite-stock slot charges for `gid`: vanilla price, or a rolled price for a rune."""
    full = gid | _GOODS_CATEGORY
    if _is_rune and _rune_worth and _is_rune(full):
        worth = _rune_worth(full)
        if worth:
            return rng.randint(0, _PRICE_MULT * int(worth))
    return GOODS_PRICE[gid]


@register
class ShopStockFeature(Feature):
    name = "shop_stock"
    OPTIONS = {
        "reroll_infinite_shop_stock": RerollInfiniteShopStock,
        "infinite_hub_wares": InfiniteHubWares,
    }

    def generate_early(self, world):
        """Validate the ware list HERE, so an impossible request is a clear rejection at
        options-validation time rather than a FillError, a KeyError, or -- worst -- a silent drop.
        CONTRIBUTING's headline gate: name the option, say the number, say what to do."""
        _resolved_pins(world)

    def slot_data(self, world):
        opt = getattr(world.options, "reroll_infinite_shop_stock", None)
        if opt is None or not int(opt.value) or not INFINITE_SHOP_ROWS:
            return {}
        p = pool()
        if not p:
            return {}
        rids = sorted(p.values())             # sorted list => a stable draw order
        # no_runes_in_shops: the shelf half. A shelf stocking a rune is "runes in shops" as surely
        # as a check reward is -- and a rune shelf is priced by the same [0, worth] roll
        # (_price_for), so it sits squarely in the render trap that option exists to sidestep.
        # Filter the DRAW LIST, not filler_curation.CATEGORIES (shared -- the received-filler roster
        # must keep its runes): with the option OFF the list is untouched and every roll is
        # bit-identical to before the option existed. Pins are handled at options time
        # (features/no_runes_in_shops.generate_early rejects a rune pin), not here.
        if _is_rune is not None and int(getattr(
                getattr(world.options, "no_runes_in_shops", None), "value", 0) or 0):
            rids = [r for r in rids if not _is_rune(r | _GOODS_CATEGORY)]
            if not rids:                      # a pool that was ALL runes: nothing left to stock
                return {}
        # keep_out_of_shops: the shelf half, same shape and for the same reason. A shelf stocking a
        # ware the player asked to keep out of shops is "in shops" as surely as a check reward is,
        # and "merchants and bell bearings" is what the request said. Filter the DRAW LIST here too
        # -- filler_curation.CATEGORIES is shared with the received-filler roster and must keep its
        # items -- so with nothing selected the list is untouched and every roll is bit-identical to
        # before the option existed. These shelves are GOODS-only (equipType 3), so a weapons/armor
        # selection cannot bite here and correctly changes nothing. Pins are handled at options time
        # (features/keep_out_of_shops.generate_early), not here.
        if _kept_out_rows is not None:
            banned = _kept_out_rows(world)
            if banned:
                rids = [r for r in rids if r not in banned]
                if not rids:                  # every ware was in a forbidden category
                    return {}
        # A DEDICATED RNG, not world.random. fill_slot_data may be called more than once (the AP world
        # tests call it twice and assert the result is identical), and drawing from the shared stream
        # both advances it -- perturbing every later consumer -- and makes the second call return a
        # DIFFERENT roll. Seeding off the multiworld seed + player keeps the roll a pure function of the
        # seed: idempotent across calls, still different across seeds, and it consumes none of the
        # shared entropy.
        rng = _random.Random(f"{world.multiworld.seed}:shop_stock:{world.player}")
        pins = _resolved_pins(world)
        roll = {}
        for row in INFINITE_SHOP_ROWS:        # already sorted by gen_data
            # THE DRAW HAPPENS EITHER WAY, then a pin overrides it. Skipping the draw for a pinned
            # row would shift the rng stream and re-roll the OTHER shelves, so adding one ware would
            # quietly change shelves it has nothing to do with. Consuming it keeps each ware's effect
            # to exactly the row it lands on.
            gid = rng.choice(rids)
            price = _price_for(gid, rng)
            if row in pins:
                gid = pins[row]
                price = _price_for(gid, rng)
            roll[str(row)] = [gid, _EQUIP_TYPE_GOODS, price]
        return {contract.SHOP_INFINITE_STOCK: roll}
