"""keep_out_of_shops -- categories of YOUR OWN item that no merchant of yours may stock.

WHY THIS EXISTS (boblerrr, Discord, 2026-08-10)
-----------------------------------------------
    "can you add a setting for us auto equip user for merchants and bell bearings not to hold
     weapons and armor / so its more split around the world"

The screenshot attached to it is a merchant shelf of weapons, gauntlets and helms priced 800-25,000
against 11,144 runes in pocket. Read as DISTRIBUTION, not auto-equip: auto_equip equips a bought
weapon perfectly well, and the complaint is that gear concentrated behind purchase menus is gear
behind a RUNE WALL rather than out in the world where you find it by going somewhere. 213 of the 562
purchase-menu checks pay a weapon or an armour piece in vanilla, and 184 of the hub's 224 locations
are shop rows -- on a small seed a merchant IS the world.

Sibling of features/no_runes_in_shops, and most of the mechanism is lifted from it verbatim (the
SHOP_ROW_FLAGS scope, the item_rule chaining, the pure fill-safety gate, the hub-pin rejection).
What differs is the predicate -- a category selection rather than "is it a money rune" -- and, as a
direct consequence, the capacity story: see THE GATE below, because the rune feature's comfortable
margin does NOT transfer and this option skips for real.

AN OptionSet OVER item_categories, NOT A TOGGLE (Alaric, 2026-08-10)
---------------------------------------------------------------------
`no_gear_in_shops: true` would answer bobler and nobody else. The partition already exists
(eldenring/item_categories.py, derived from the FullID nibble + EquipParamGoods.goodsType), every
other item-selection option in this world is already keyed on it (`keep_local`,
`exclude_local_item_only`), and reusing it means `spells`, `spirit_ashes`, `crafting` and the
`goods` / `everything` umbrellas come free rather than as four more toggles later. It is also the
compat-safe shape: adding a category name is additive, and only REMOVING one is a break.

    keep_out_of_shops: [weapons, armor]      <- bobler's ask, exactly

WHAT IS FORBIDDEN, AND FROM WHAT
--------------------------------
  * SCOPE is `shop_data.SHOP_ROW_FLAGS` membership -- 562 rows, the same table shop_sell rewrites
    and rune_pricing prices. Tags are the wrong instrument: `Shop` covers 527 of those rows and the
    mechanism covers 562 (see the umbrella ruling in features/no_runes_in_shops and
    test_gf_shop_umbrella). Bell-bearing shops are in it, which is what "merchants AND bell
    bearings" asked for -- a bell bearing's wares are ShopLineupParam rows like any other.
  * THE ITEM SET is `item_categories.names_in(selected, PROGRESSIVE_NAMES)` -- the SAME helper
    features/local_items uses -- not `category_of(item.name)` over the pool. The difference is not
    cosmetic: `category_of` answers `progressive` for every name outside ITEM_CATALOG, which is the
    region Lock items and the `Rune` filler sentinel as well as the four real Progressive X items.
    Selecting `progressive` would then quietly forbid REGION LOCKS from every shop check -- a
    progression constraint nobody asked for, on the one item class this world's logic is built out
    of. Going through `names_in` makes that unrepresentable.
    It is also what keeps the widest selection satisfiable: `keep_out_of_shops: [everything]`
    forbids every OWN CATALOG item from all 562 rows, and those rows are still fillable because the
    region Locks and the `Rune` sentinel are outside the partition and therefore outside the ban.
    Sweeping them in would turn the umbrella into a guaranteed FillError on a solo seed.
  * FOREIGN items are untouched, deliberately, and for the same reason no_runes_in_shops leaves them
    alone: another slot's item is never sold natively (its row shows an AP-placeholder spare good),
    bobler's complaint is about HIS gear not being in HIS world, and forbidding foreign rewards
    would shrink multiworld fill freedom to no purpose. It also means the gate below is
    CONSERVATIVE -- in a multiworld a shop row can be filled by a foreign item, so real capacity is
    larger than the number it checks.

BOTH HALVES, because bobler said "merchants and bell bearings"
---------------------------------------------------------------
  1. the PLACED checks -- an item_rule on every SHOP_ROW_FLAGS location (set_rules, below);
  2. the REROLLED INFINITE SHELVES -- features/shop_stock draws from a filtered list
     (`forbidden_goods_rows` is called from its slot_data, and filters the DRAW LIST, never
     `filler_curation.CATEGORIES`, which is shared with the received-filler roster).

     🛑 THE SHELVES ARE GOODS-ONLY, so a `[weapons, armor]` selection cannot bite there and the roll
     is bit-identical to an unset option. That is not a defect and it is said out loud here because
     the alternative is a reader concluding half the feature is broken: the 14 browsable unlimited
     rows are `equipType 3` and a weapon cannot be stocked on one (see features/shop_stock). The
     half bites for `consumables`, `crafting`, `key_items` and `runes`, which are what that pool
     holds.

⭐ THE GATE: this option runs out of room, and the rune feature's margin does not transfer
-------------------------------------------------------------------------------------------
no_runes_in_shops documents 744 rune items against ~4300 non-shop slots and "clears by hundreds".
Runes are a thin slice. Weapons and armour are two of the five top-level buckets, and measured on
shipped data (`LOCATION_ITEM` x `item_categories`, item_shuffle frozen ON):

    full world      4931 locations, 562 of them shop -> 4369 non-shop slots
                    462 weapons + 227 armor = 689.  Fits, by a factor of six.
    hub + finale      236 locations, 184 of them shop ->   52 non-shop slots
                    60 weapons, 68 armor.  EITHER ONE alone overflows.

So the skip path is not a theoretical guard here -- a small seed hits it. Two requirements follow.

PER CATEGORY, NOT ALL-OR-NOTHING (the design call, taken deliberately). If `weapons` does not fit
but `spells` does, enforcing `spells` is strictly better than enforcing nothing, and a player who
listed four categories would rather be told which one was dropped than have the whole option go
quiet. `plan()` below is therefore a small budgeted selection, and it takes the categories
SMALLEST-FIRST, which is optimal for the thing being maximised -- the NUMBER of selected categories
honoured. It is deliberately not maximising the item COUNT held out of shops; between "three of your
four categories" and "one big one", the first is the more legible answer to a player who wrote a
list. The order is a total one (count, then name), so the outcome is deterministic across seeds.

AND IT MUST SAY SO, SPECIFICALLY. A player who selected [weapons, armor] and silently got neither is
owed the sentence. Every dropped category is logged BY NAME with its item count and the capacity it
did not fit into, and the armed case logs what it armed -- an option that can no-op without a line
is the failure mode this project keeps rediscovering.

🛑 COUNT, THEN DECIDE -- never hand fill an unsatisfiable constraint (progression_surface's
feasibility ladder is the precedent). `plan()` is a PURE function of (counts, capacity) so a test can
call it directly both ways: no realistic corpus seed exercises every branch, and a guard the corpus
never triggers is untested.

REJECTED COMBINATIONS (both name the option, the value and the fix, per CONTRIBUTING)
--------------------------------------------------------------------------------------
  * `vanilla_placement` -- it pins EVERY location with `place_locked_item`, which does not consult
    item_rule, and leaves zero unfilled locations. This option would not be weakened by it, it would
    be a total silent no-op, on the one setting whose entire purpose is that items sit where the
    base game keeps them. That is a contradiction in the request, not a fill problem, so it is an
    OptionError, following the natural_progression precedent in features/vanilla_placement.
  * `infinite_hub_wares` pinning a ware in a forbidden category -- the pin either overrides this
    option (a knob quietly losing to another knob) or is silently dropped (a player asks and nothing
    says no).

Matt-free: SHOP_ROW_FLAGS and ITEM_CATALOG are param-derived (gen_data.py); the categories are
derived from the FullID nibble and EquipParamGoods.goodsType. slot_data: none of its own -- the
placed half is fill-side and the shelf half rides the existing SHOP_INFINITE_STOCK key, so
CONTRACT_HASH does not move and no client change is implied.
"""
import logging
import warnings
from typing import Dict, List, Set, Tuple

from Options import OptionError, OptionSet

from ..registry import Feature, register
from ..item_categories import SELECTABLE, expand, names_in

try:
    from ..shop_data import SHOP_ROW_FLAGS
except Exception:  # not yet generated -> no shop scope -> the feature can only warn
    SHOP_ROW_FLAGS = {}

try:
    from ..item_ids import ITEM_CATALOG
except Exception:
    ITEM_CATALOG = {}

# The Progressive X names, by NAME, exactly as features/local_items imports them: they carry no
# FullID and are not in ITEM_CATALOG, so `names_in` cannot find them on its own.
try:
    from .progressive import (PROG_FLASK, PROG_STONESWORD_KEY,
                              PROG_SMITHING_BELL, PROG_SOMBER_BELL)
    _PROGRESSIVE_NAMES: List[str] = [PROG_FLASK, PROG_STONESWORD_KEY,
                                     PROG_SMITHING_BELL, PROG_SOMBER_BELL]
except Exception:
    _PROGRESSIVE_NAMES = []

_GOODS_NIBBLE = 0x40000000
_ROW_ID_MASK = 0x0FFFFFFF

_LOG = logging.getLogger("Greenfield")


class KeepOutOfShops(OptionSet):
    """Categories of YOUR OWN item that your merchants may never stock, listed one per line. The
    items still exist and are still shuffled -- they just land out in the world instead of behind a
    purchase menu, so finding them is a matter of going somewhere rather than of having enough
    runes.

    Covers both halves of a merchant: the shop checks themselves (bell-bearing shops included) and
    the rerolled unlimited shelves. Other players' items at your shops are unaffected.

    Example, and the one this was written for:
        keep_out_of_shops: [weapons, armor]

    Same categories as Keep Local: weapons, armor, talismans, ashes (ashes of WAR), spells,
    spirit_ashes, consumables, crafting, cookbooks, upgrade_materials, upgrade_bells,
    merchant_bells, runes, crystal_tears, key_items, other, progressive -- plus the umbrellas
    `goods`, `key_items` (the whole inventory tab: cookbooks and bell bearings included),
    `bell_bearings` (both kinds) and `everything`.

    Empty (default) = merchants stock exactly what they would have. On a SMALL seed there may not be
    room: the hub is 184 shop rows out of 224 locations, and if a category holds more items than
    there are non-shop slots to move them to, that category is skipped and the generation log says
    which one and by how much. Larger seeds have room to spare."""
    display_name = "Keep Out Of Shops"
    valid_keys = frozenset(SELECTABLE)


# ---- the pure half ------------------------------------------------------------------------------
def plan(counts: Dict[str, int], capacity: int) -> Tuple[List[str], List[str]]:
    """Which selected categories can actually be enforced, given `capacity` non-shop slots to move
    their items into. PURE, so a test can call it directly both ways.

    `counts` is {category: how many of this world's pool items it holds}. Returns
    (enforced, dropped), both sorted by name.

    Budgeted, smallest-first: forbidding a category means every item in it has to fit somewhere that
    is not a shop, and the categories share one pool of non-shop slots, so the budget is cumulative.
    Taking the cheapest first maximises HOW MANY of the player's categories survive -- see the
    module docstring for why that is the objective rather than total items displaced. Ties break on
    the name so the outcome cannot depend on dict order.
    """
    enforced: List[str] = []
    dropped: List[str] = []
    used = 0
    for cat, n in sorted(counts.items(), key=lambda kv: (kv[1], kv[0])):
        if used + n <= capacity:
            used += n
            enforced.append(cat)
        else:
            dropped.append(cat)
    return sorted(enforced), sorted(dropped)


def safe_forbid_capacity(non_shop_slots: int, selected_items: int,
                         shop_slots: int, compatible_outside_items: int) -> int:
    """Maximum selected items that may be forbidden without starving shop-only slots.

    ``B <= non_shop_slots`` is necessary but not sufficient: some shop rows already reject the
    Region Locks / Rune sentinels outside the catalog partition. Preserve enough selected items as
    legal shop stock to cover the shortfall. This is deliberately conservative (one outside item
    is counted once even if many shops accept it), which may drop a category but can never invent
    capacity that fill does not have.
    """
    shop_shortfall = max(0, shop_slots - compatible_outside_items)
    return max(0, min(non_shop_slots, selected_items - shop_shortfall))


def _max_shop_matches(items, shops) -> int:
    """Maximum one-item/one-shop matching under the rows' existing item rules.

    Counting an outside item merely because *some* shop accepts it overstates capacity when several
    items all fit the same permissive row but not the restrictive rows. The small augmenting-path
    matcher makes the reserve a proof rather than a heuristic.
    """
    matched_item = [-1] * len(shops)

    def place(item_index: int, seen: Set[int]) -> bool:
        item = items[item_index]
        for shop_index, shop in enumerate(shops):
            if shop_index in seen or not shop.item_rule(item):
                continue
            seen.add(shop_index)
            prior = matched_item[shop_index]
            if prior == -1 or place(prior, seen):
                matched_item[shop_index] = item_index
                return True
        return False

    return sum(1 for item_index in range(len(items)) if place(item_index, set()))


def skip_line(cat: str, count: int, remaining: int, capacity: int, enforced: List[str]) -> str:
    """The sentence a dropped category is owed, as a PURE function so a test can pin the numbers.

    🛑 IT MUST QUOTE THE REMAINING BUDGET, NOT THE TOTAL. The first draft of this logged `capacity`
    for every drop and produced "the pool holds 71 armor item(s) but only 94 non-shop location(s)
    could hold them" -- 71 fits in 94, so the line said the opposite of the truth and read as a bug
    in the gate. The budget is CUMULATIVE (see plan()): armor was dropped because weapons had
    already claimed 66 of those 94. A telemetry line that cannot be checked against its own numbers
    is worse than none, because it sends the reader after the wrong defect.
    """
    if enforced:
        return ("keep_out_of_shops: SKIPPING %r -- it holds %d pool item(s) and only %d of this "
                "seed's %d non-shop location(s) are still free once %s is enforced, so enforcing "
                "it too would make fill unsatisfiable. The seed still generates; %s may appear at "
                "merchants this seed."
                % (cat, count, remaining, capacity, " and ".join(enforced), cat))
    return ("keep_out_of_shops: SKIPPING %r -- it holds %d pool item(s) against only %d non-shop "
            "location(s), so enforcing it would make fill unsatisfiable. The seed still generates; "
            "%s may appear at merchants this seed." % (cat, count, capacity, cat))


def _selected(world) -> List[str]:
    """The player's selection, umbrellas resolved. Empty = the option is off."""
    opt = getattr(getattr(world, "options", None), "keep_out_of_shops", None)
    return expand(getattr(opt, "value", ()) or ()) if opt is not None else []


def _names_by_category(categories) -> Dict[str, Set[str]]:
    return {c: set(names_in([c], _PROGRESSIVE_NAMES)) for c in categories}


def forbidden_names(world) -> Set[str]:
    """Every item NAME this option forbids from a shop, ignoring capacity. Used by the shelf half
    (which has no fill to be unsatisfiable) and by the option-conflict check."""
    cats = _selected(world)
    if not cats:
        return set()
    return set(names_in(cats, _PROGRESSIVE_NAMES))


def forbidden_goods_rows(world) -> Set[int]:
    """The forbidden names that are GOODS, as ShopLineupParam-style row ids -- what
    features/shop_stock needs to filter its draw list. Empty when the option is off, so the shelf
    roll is bit-identical to a world without this option."""
    out = set()
    for nm in forbidden_names(world):
        full = ITEM_CATALOG.get(nm)
        if full is not None and (full & ~_ROW_ID_MASK) == _GOODS_NIBBLE:
            out.add(full & _ROW_ID_MASK)
    return out


@register
class KeepOutOfShopsFeature(Feature):
    name = "keep_out_of_shops"
    OPTIONS = {"keep_out_of_shops": KeepOutOfShops}

    def generate_early(self, world):
        cats = _selected(world)
        if not cats:
            return

        # vanilla_placement pins every location with place_locked_item, which never consults
        # item_rule, and leaves no unfilled location behind -- so this option would not merely be
        # weakened, it would do NOTHING while reading as armed.
        vp = getattr(world.options, "vanilla_placement", None)
        if vp is not None and int(getattr(vp, "value", 0) or 0):
            raise OptionError(
                "keep_out_of_shops lists %s, but vanilla_placement is on. Vanilla placement puts "
                "every item back on its base-game location, merchants included, so nothing can be "
                "kept out of a shop -- the option would silently do nothing. Turn "
                "vanilla_placement off, or clear keep_out_of_shops."
                % ", ".join(repr(c) for c in cats))

        # A hub pin naming a forbidden ware is the same class of conflict no_runes_in_shops rejects.
        pins = getattr(getattr(world.options, "infinite_hub_wares", None), "value", ()) or ()
        banned = forbidden_names(world)
        bad = sorted(str(w) for w in pins if str(w) in banned)
        if bad:
            raise OptionError(
                "keep_out_of_shops lists %s, but infinite_hub_wares pins %s onto a hub shelf. "
                "Remove the pin(s), or drop the category from keep_out_of_shops."
                % (", ".join(repr(c) for c in cats), ", ".join(repr(b) for b in bad)))

    def set_rules(self, world):
        cats = _selected(world)
        if not cats:
            return
        player = world.player
        if not SHOP_ROW_FLAGS:
            # TOLERANCE REQUIRES TELEMETRY (rune_pricing's rule): an option that is ON and can scope
            # nothing must say so, or "it did nothing" is indistinguishable from "it worked".
            warnings.warn(
                "keep_out_of_shops is set (%s) but shop_data.SHOP_ROW_FLAGS is empty -- this tree "
                "needs a -Greenfield regen. The option scoped no shop checks and did nothing."
                % ", ".join(cats), RuntimeWarning)
            return

        shop_locs = []
        capacity = 0
        for loc in world.multiworld.get_locations(player):
            aid = getattr(loc, "address", None)
            if aid is None:
                continue                      # events are not checks
            if str(aid) in SHOP_ROW_FLAGS:
                shop_locs.append(loc)
            elif loc.item is None:
                capacity += 1                 # a non-shop slot a displaced item could land on

        by_cat = _names_by_category(cats)
        own = [i for i in world.multiworld.itempool if i.player == player]
        selected_names = set().union(*by_cat.values()) if by_cat else set()
        open_shops = [loc for loc in shop_locs if loc.item is None]
        outside = [item for item in own if item.name not in selected_names]
        compatible_outside = _max_shop_matches(outside, open_shops)
        selected_count = sum(1 for item in own if item.name in selected_names)
        capacity = safe_forbid_capacity(
            capacity, selected_count, len(open_shops), compatible_outside)
        counts = {c: sum(1 for i in own if i.name in ns) for c, ns in by_cat.items()}
        enforced, dropped = plan(counts, capacity)

        used = sum(counts[c] for c in enforced)
        for c in dropped:
            _LOG.warning("[eldenring:%s] %s", player,
                         skip_line(c, counts[c], capacity - used, capacity, enforced))
        if not enforced:
            _LOG.warning(
                "[eldenring:%s] keep_out_of_shops: INERT this seed -- none of %s fits in %d "
                "non-shop location(s). A larger seed (more kept regions) has room.",
                player, ", ".join(cats), capacity)
            return

        forbidden: Set[str] = set()
        for c in enforced:
            forbidden |= by_cat[c]
        _LOG.info(
            "[eldenring:%s] keep_out_of_shops: armed on %d shop check(s) for %s -- %d item name(s) "
            "forbidden, %d pool item(s) displaced into %d non-shop location(s).",
            player, len(shop_locs), ", ".join(enforced), len(forbidden), used, capacity)

        for loc in shop_locs:
            prev = loc.item_rule
            loc.item_rule = (lambda item, pv=prev:
                             pv(item) and not (item.player == player and item.name in forbidden))
