"""keep_out_of_shops -- categories of your own item that no merchant may stock.

THE MOTIVATING CASE IS THE ACCEPTANCE TEST (CONTRIBUTING rule 11). boblerrr, Discord, 2026-08-10:
"can you add a setting for us auto equip user for merchants and bell bearings not to hold weapons
and armor / so its more split around the world", with a screenshot of a shelf of weapons, gauntlets
and helms. So the headline case here is literally `keep_out_of_shops: [weapons, armor]` on a seed
big enough to have room, carried through a REAL fill: no own weapon and no own armour piece behind
any purchase menu afterwards, and none in the reroll pool either.

Properties pinned:
  1. DEFAULT (empty set) changes nothing -- no rule is installed, and the shelf roll is
     bit-identical to a world that has never heard of the option.
  2. ON: every SHOP_ROW_FLAGS check rejects an own item of a selected category, still accepts an
     own item of an UNselected one (the ban is a category ban, not a blanket), and NON-shop
     locations still accept the banned categories (it is scoped, not global).
  3. ON, after a full fill: the motivating case. Nothing banned on a shop check, and the items were
     MOVED rather than deleted.
  4. Region Locks and the Rune sentinel are NOT swept up by `progressive` -- the `names_in` vs
     `category_of` distinction the feature docstring argues for, tested because getting it wrong
     puts a progression constraint on every shop check and nothing else would notice.
  5. The shelf half: a goods category really is filtered out of the draw, and the OFF half is
     proven non-vacuous (the unfiltered draw does produce that category).
  6. Both rejected combinations -- vanilla_placement, and a hub pin in a forbidden category.
  7. `plan()`, the capacity gate, called DIRECTLY: no realistic corpus seed walks every branch, and
     a guard the corpus never triggers is untested.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from Options import OptionError  # noqa: E402
from worlds.eldenring.shop_data import SHOP_ROW_FLAGS  # noqa: E402
from worlds.eldenring.features.keep_out_of_shops import (  # noqa: E402
    forbidden_goods_rows, forbidden_names, plan, skip_line)
from worlds.eldenring.item_categories import category_of, names_in  # noqa: E402

GAME = "Elden Ring"
_GEAR = {"weapons", "armor"}


def _shop_locs(world, mw):
    return [l for l in mw.get_locations(world.player)
            if getattr(l, "address", None) is not None and str(l.address) in SHOP_ROW_FLAGS]


def _own_item_in(world, categories):
    """A pool item of this world whose name is in one of `categories`, or None."""
    want = set(names_in(sorted(categories)))
    return next((i for i in world.multiworld.itempool
                 if i.player == world.player and i.name in want), None)


# ---- 1. the default -----------------------------------------------------------------------------

class DefaultIsEmptyAndInstallsNoRule(WorldTestBase):
    game = GAME

    def test_default_is_the_empty_set(self):
        assert set(self.world.options.keep_out_of_shops.value) == set(), (
            "keep_out_of_shops must default to the empty set -- a fresh yaml has to generate "
            "exactly as it did before the option existed")

    def test_no_shop_check_refuses_gear_by_default(self):
        gear = _own_item_in(self.world, _GEAR)
        assert gear is not None, "no own weapon/armour in a default pool -- the probe is broken"
        shops = _shop_locs(self.world, self.multiworld)
        assert shops, "no shop-row locations in a default seed -- scope table missing?"
        refusing = [l for l in shops if not l.item_rule(gear)]
        assert not refusing, (
            "%d shop checks reject %r with the option unset -- the default is not no-change "
            "(first: %s)" % (len(refusing), gear.name, refusing[0].name))


# ---- 2 & 3. the scoped ban, and bobler's case through a real fill --------------------------------

class GearBannedOnAFullSizedSeed(WorldTestBase):
    game = GAME
    # num_regions 0 = every region: 4931 locations against 562 shop rows, so the capacity gate
    # passes and the RULE is what is under test here (the gate has its own tests below).
    options = {"num_regions": 0, "keep_out_of_shops": {"weapons", "armor"}}

    def test_shop_checks_reject_own_gear_but_not_other_categories(self):
        gear = _own_item_in(self.world, _GEAR)
        assert gear is not None, "no own weapon/armour in the pool to probe with"
        shops = _shop_locs(self.world, self.multiworld)
        assert shops, "no shop-row locations in play"
        accepting = [l for l in shops if l.item_rule(gear)]
        assert not accepting, (
            "%d shop checks still accept own gear %r (first: %s)"
            % (len(accepting), gear.name, accepting[0].name))

        # ...and it banned CATEGORIES, not everything. An unselected category must still pass on
        # the bulk of the rows (individual rows refuse filler for their own unrelated reasons).
        other = _own_item_in(self.world, {"consumables", "crafting", "upgrade_materials"})
        assert other is not None, "no own consumable/crafting item in the pool to probe with"
        blocked = [l for l in shops if not l.item_rule(other)]
        assert len(blocked) < len(shops) // 2, (
            "%d of %d shop checks reject %r, an unselected category -- the ban is over-broad"
            % (len(blocked), len(shops), other.name))

    def test_non_shop_locations_still_accept_gear(self):
        gear = _own_item_in(self.world, _GEAR)
        others = [l for l in self.multiworld.get_locations(self.world.player)
                  if getattr(l, "address", None) is not None
                  and str(l.address) not in SHOP_ROW_FLAGS and l.item is None]
        assert others, "no non-shop locations in play"
        accepting = sum(1 for l in others if l.item_rule(gear))
        assert accepting > len(others) // 2, (
            "only %d of %d non-shop locations accept %r -- the ban leaked out of the shop scope"
            % (accepting, len(others), gear.name))

    def test_region_locks_and_the_rune_sentinel_are_not_forbidden(self):
        """`category_of` answers `progressive` for every name outside ITEM_CATALOG -- the region
        Locks and the `Rune` filler sentinel included -- so building the ban from it instead of
        `names_in` would put a progression constraint on all 562 shop checks. Nothing else in the
        suite would notice, so it is pinned here."""
        banned = forbidden_names(self.world)
        assert len(banned) > 500, (
            "only %d name(s) forbidden for [weapons, armor] -- the scan below has nothing to look "
            "at and would pass for the wrong reason" % len(banned))
        leaked = sorted(n for n in banned if n.endswith(" Lock") or n == "Rune")
        assert not leaked, (
            "keep_out_of_shops forbade %s -- the ban was built from category_of over the pool "
            "instead of item_categories.names_in" % leaked)

    def test_after_a_full_fill_no_own_gear_sits_on_a_shop_check(self):
        """THE MOTIVATING CASE. remaining_fill honours item_rule with swaps; prove the outcome."""
        from Fill import distribute_items_restrictive
        distribute_items_restrictive(self.multiworld)
        player = self.world.player
        offenders = [l for l in _shop_locs(self.world, self.multiworld)
                     if l.item is not None and l.item.player == player
                     and category_of(l.item.name) in _GEAR]
        assert not offenders, (
            "own weapons/armour landed on %d shop checks: %s"
            % (len(offenders), [(l.name, l.item.name) for l in offenders[:5]]))
        # MOVED, not deleted: they are out in the world, which is the whole point of the request.
        elsewhere = sum(1 for l in self.multiworld.get_locations(player)
                        if l.item is not None and l.item.player == player
                        and category_of(l.item.name) in _GEAR)
        assert elsewhere > 0, (
            "no own weapon or armour anywhere post-fill -- the pool lost them, which is not this "
            "option's job")


# ---- 5. the shelf half ---------------------------------------------------------------------------

class _Opt:
    def __init__(self, value):
        self.value = value


def _shelf_roll(seed, keep_out=()):
    """features/shop_stock.slot_data against a stub world -- the test_gf_pinned_hub_shelves idiom
    (a stub keeps the seed pinned and the surface minimal)."""
    from worlds.eldenring.features import shop_stock as ss
    from worlds.eldenring import contract

    class _MW:
        pass

    w = type("W", (), {})()
    w.multiworld = _MW()
    w.multiworld.seed = seed
    w.player = 1
    w.options = type("O", (), {
        "reroll_infinite_shop_stock": _Opt(1),
        "infinite_hub_wares": _Opt(set()),
        "keep_out_of_shops": _Opt(set(keep_out)),
    })()
    return ss.ShopStockFeature().slot_data(w).get(contract.SHOP_INFINITE_STOCK, {})


def _shelf_pool_categories():
    from worlds.eldenring.features import shop_stock as ss
    return {nm: category_of(nm) for nm in ss.pool()}


def test_a_goods_category_is_filtered_out_of_the_shelf_draw():
    """`consumables` is the shelf pool's dominant category, so this is the one with teeth."""
    from worlds.eldenring.features import shop_stock as ss
    pool = ss.pool()
    cats = _shelf_pool_categories()
    if "consumables" not in set(cats.values()):
        pytest.fail("shop_stock.pool() no longer holds a `consumables` ware -- pick another "
                    "category for this test rather than letting it go vacuous")
    banned_rows = {rid for nm, rid in pool.items() if cats[nm] == "consumables"}
    for seed in range(30):
        for row, (gid, _et, _price) in _shelf_roll(seed, {"consumables"}).items():
            assert gid not in banned_rows, (
                "seed %d put consumable good %d on shelf %s despite keep_out_of_shops" % (seed, gid, row))


def test_the_unfiltered_draw_does_produce_that_category_so_the_filter_is_load_bearing():
    """Non-vacuity: if no unfiltered seed ever rolls a consumable, the test above proves nothing."""
    from worlds.eldenring.features import shop_stock as ss
    pool = ss.pool()
    cats = _shelf_pool_categories()
    rows = {rid for nm, rid in pool.items() if cats[nm] == "consumables"}
    hits = sum(1 for seed in range(30)
               for _row, (gid, _et, _p) in _shelf_roll(seed).items() if gid in rows)
    assert hits > 0, "30 unfiltered seeds never rolled a consumable shelf -- the ON test is vacuous"


def test_a_gear_only_selection_leaves_the_shelf_roll_untouched():
    """The shelves are GOODS-only, so `[weapons, armor]` correctly cannot bite there. Pinned so the
    no-op is a DOCUMENTED one rather than something a future reader reports as half a feature."""
    assert _shelf_roll(20260810, {"weapons", "armor"}) == _shelf_roll(20260810), (
        "a weapons/armor selection changed the shelf roll -- these shelves are equipType 3 goods "
        "shelves and cannot stock either")


def test_an_unset_option_is_bit_identical_to_the_pre_option_world():
    """The OFF path must match a world that has no such attribute at all (frozen default rule)."""
    from worlds.eldenring.features import shop_stock as ss
    from worlds.eldenring import contract

    class _MW:
        seed = 424242

    class _W:
        multiworld = _MW()
        player = 1
        options = type("O", (), {
            "reroll_infinite_shop_stock": _Opt(1),
            "infinite_hub_wares": _Opt(set()),
        })()   # note: NO keep_out_of_shops attribute -- the pre-option world

    legacy = ss.ShopStockFeature().slot_data(_W())[contract.SHOP_INFINITE_STOCK]
    assert legacy == _shelf_roll(424242), "an unset option changed the shelf roll"


def test_forbidden_goods_rows_is_empty_when_the_option_is_unset():
    class _W:
        options = type("O", (), {})()
    assert forbidden_goods_rows(_W()) == set()


# ---- 6. the rejected combinations -----------------------------------------------------------------

def test_vanilla_placement_with_a_selection_is_an_OptionError_naming_both():
    class _T(WorldTestBase):
        game = GAME
        options = {"vanilla_placement": "all", "keep_out_of_shops": {"weapons"}}

    t = _T("runTest")
    t.options = dict(_T.options)
    with pytest.raises(OptionError) as e:
        t.world_setup()
    msg = str(e.value)
    assert "keep_out_of_shops" in msg and "vanilla_placement" in msg, (
        "the rejection must name both options: %r" % msg)


def test_a_forbidden_hub_pin_is_an_OptionError_naming_the_ware():
    class _T(WorldTestBase):
        game = GAME
        options = {"num_regions": 0, "keep_out_of_shops": {"consumables"},
                   "infinite_hub_wares": {"Rune Arc"}}

    assert category_of("Rune Arc") == "consumables", (
        "Rune Arc is no longer a consumable -- pick another pin for this test")
    t = _T("runTest")
    t.options = dict(_T.options)
    with pytest.raises(OptionError) as e:
        t.world_setup()
    msg = str(e.value)
    assert "keep_out_of_shops" in msg and "infinite_hub_wares" in msg and "Rune Arc" in msg, (
        "the rejection must name both options and the offending ware: %r" % msg)


# ---- 7. the capacity gate, called directly --------------------------------------------------------

def test_the_gate_enforces_everything_when_there_is_room():
    assert plan({"weapons": 462, "armor": 227}, 4369) == (["armor", "weapons"], [])


def test_the_gate_drops_everything_when_there_is_none():
    """The measured minimal seed: hub + Ashen Capital is 52 non-shop slots against 60 weapons and
    68 armour, so BOTH overflow -- the case the docstring's table names."""
    assert plan({"weapons": 60, "armor": 68}, 52) == ([], ["armor", "weapons"])


def test_the_gate_is_PER_CATEGORY_which_is_the_whole_design_call():
    """The reason this is not all-or-nothing: a category that fits is still worth enforcing."""
    enforced, dropped = plan({"weapons": 60, "spells": 35}, 52)
    assert enforced == ["spells"] and dropped == ["weapons"], (enforced, dropped)


def test_the_budget_is_CUMULATIVE_not_per_category():
    """Two categories that each fit alone but not together share one pool of non-shop slots."""
    enforced, dropped = plan({"a": 30, "b": 30}, 50)
    assert enforced == ["a"] and dropped == ["b"], (enforced, dropped)


def test_exact_fit_enforces_and_ties_break_on_the_name():
    assert plan({"weapons": 10}, 10) == (["weapons"], [])
    assert plan({}, 0) == ([], [])
    # equal counts, room for one: the smaller NAME wins, so the outcome cannot depend on dict order
    assert plan({"zeta": 30, "alpha": 30}, 30) == (["alpha"], ["zeta"])


def test_smallest_first_maximises_how_many_categories_survive():
    """The stated objective. Largest-first would keep one; smallest-first keeps three."""
    enforced, _ = plan({"big": 40, "s1": 5, "s2": 5, "s3": 5}, 40)
    assert enforced == ["s1", "s2", "s3"], enforced


def test_the_skip_line_quotes_the_REMAINING_budget_not_the_total():
    """The first draft logged the total capacity on every drop and produced "holds 71 armor item(s)
    but only 94 non-shop location(s) could hold them" -- 71 fits in 94, so the line contradicted
    itself and read as a bug in the gate rather than a cumulative budget doing its job."""
    line = skip_line("armor", 71, 28, 94, ["weapons"])
    assert "71" in line and "28" in line and "94" in line and "weapons" in line, line
    assert "armor" in line
    # the wrong number must not be the one presented as the thing armor did not fit into
    assert "only 94" not in line, (
        "the drop line still offers the TOTAL capacity as the budget armor failed against: %r" % line)


def test_the_skip_line_drops_the_cumulative_clause_when_nothing_was_enforced():
    line = skip_line("armor", 68, 52, 52, [])
    assert "68" in line and "52" in line, line
    assert "still free once" not in line, (
        "with nothing enforced there is no cumulative claim to explain: %r" % line)
