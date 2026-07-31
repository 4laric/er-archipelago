"""no_runes_in_shops -- the world-side escape hatch for invisible rune shop rows.

The motivating case is the acceptance test (CONTRIBUTING rule 11): a seed with the option ON must
never put one of this world's own money runes behind a purchase menu -- that is the exact class of
check players kept reporting as unbuyable (the row is written correctly and the menu does not render
it; see features/no_runes_in_shops for the full account).

Properties pinned here:
  1. DEFAULT OFF changes nothing: shop checks accept a rune (no rule is installed).
  2. ON: every purchase-menu check (SHOP_ROW_FLAGS scope) rejects an own money rune, still accepts
     ordinary junk (the rule must not smuggle in important_locations), and NON-shop locations still
     accept runes (the rule is scoped, not global).
  3. ON, after a FULL fill: no own rune on any shop check, while runes still landed elsewhere (the
     constraint moved them, it did not delete them).
  4. The shelf half: rerolled infinite stock never draws a rune ware -- and the OFF half is proven
     non-vacuous (across seeds, an unfiltered draw does produce runes).
  5. A rune pin in infinite_hub_wares combined with this option is an OptionError naming both.
  6. The fill-safety gate, called DIRECTLY both ways (a guard the corpus never triggers is
     untested -- no realistic seed overfills, so the corpus never will).
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from Options import OptionError  # noqa: E402
from worlds.eldenring.shop_data import SHOP_ROW_FLAGS  # noqa: E402
from worlds.eldenring.features.no_runes_in_shops import _skip_reason  # noqa: E402
from worlds.eldenring.features.rune_pricing import is_rune_item  # noqa: E402

GAME = "Elden Ring"
_PROBE_RUNE = "Golden Rune [1]"


def _shop_locs(world, mw):
    return [l for l in mw.get_locations(world.player)
            if getattr(l, "address", None) is not None and str(l.address) in SHOP_ROW_FLAGS]


class DefaultOffIsNoChange(WorldTestBase):
    game = GAME

    def test_default_is_off_and_installs_no_rule(self):
        assert int(self.world.options.no_runes_in_shops.value) == 0
        rune = self.world.create_item(_PROBE_RUNE)
        assert is_rune_item(rune.name), "the probe item is not a money rune -- test is broken"
        shops = _shop_locs(self.world, self.multiworld)
        assert shops, "no shop-row locations in a default seed -- scope table missing?"
        refusing = [l for l in shops if not l.item_rule(rune)]
        assert not refusing, (
            "%d shop checks reject a rune with the option OFF -- the default is not no-change "
            "(first: %s)" % (len(refusing), refusing[0].name if refusing else ""))


class OnScopesExactlyTheShops(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "no_runes_in_shops": True}

    def test_shop_checks_reject_own_runes_and_nothing_else(self):
        rune = self.world.create_item(_PROBE_RUNE)
        shops = _shop_locs(self.world, self.multiworld)
        assert shops, "no shop-row locations in play"
        accepting = [l for l in shops if l.item_rule(rune)]
        assert not accepting, (
            "%d shop checks still accept an own rune (first: %s)"
            % (len(accepting), accepting[0].name if accepting else ""))
        # ...and the rule forbade RUNES, not filler in general: some ordinary own junk must pass.
        junk = next((i for i in self.multiworld.itempool
                     if i.player == self.world.player and not i.advancement
                     and not is_rune_item(i.name)), None)
        assert junk is not None, "no non-rune own filler in the pool to probe with"
        blocked = [l for l in shops if not l.item_rule(junk)]
        # missable/important composition may block SOME rows for their own reasons; the rune ban
        # itself must not blanket-block. "Most rows accept junk" is the property with teeth.
        assert len(blocked) < len(shops) // 2, (
            "%d of %d shop checks reject ordinary junk (%r) -- the ban is over-broad"
            % (len(blocked), len(shops), junk.name))

    def test_non_shop_locations_still_accept_runes(self):
        rune = self.world.create_item(_PROBE_RUNE)
        others = [l for l in self.multiworld.get_locations(self.world.player)
                  if getattr(l, "address", None) is not None
                  and str(l.address) not in SHOP_ROW_FLAGS and l.item is None]
        assert others, "no non-shop locations in play"
        accepting = sum(1 for l in others if l.item_rule(rune))
        # important_locations etc. legitimately refuse filler on their own tagged rows; the bulk
        # must still take a rune or the option leaked past its scope.
        assert accepting > len(others) // 2, (
            "only %d of %d non-shop locations accept a rune -- the ban leaked out of the shop scope"
            % (accepting, len(others)))

    def test_after_a_full_fill_no_own_rune_sits_on_a_shop_check(self):
        """The motivating case. remaining_fill honours item_rule with swaps; prove the outcome."""
        from Fill import distribute_items_restrictive
        distribute_items_restrictive(self.multiworld)
        offenders = [l for l in _shop_locs(self.world, self.multiworld)
                     if l.item is not None and l.item.player == self.world.player
                     and is_rune_item(l.item.name)]
        assert not offenders, (
            "own money runes landed on %d shop checks: %s"
            % (len(offenders), [l.name for l in offenders[:5]]))
        # The runes were MOVED, not deleted: with item_shuffle frozen on, hundreds exist.
        placed_elsewhere = sum(
            1 for l in self.multiworld.get_locations(self.world.player)
            if l.item is not None and l.item.player == self.world.player
            and is_rune_item(l.item.name))
        assert placed_elsewhere > 0, (
            "no own rune anywhere post-fill -- the pool lost its runes, which is not this "
            "option's job (count-neutrality violated upstream?)")


# ---- the shelf half -----------------------------------------------------------------------------

class _Opt:
    def __init__(self, value):
        self.value = value


def _shelf_roll(seed, ban):
    """features/shop_stock slot_data against a stub world (the test_gf_pinned_hub_shelves idiom:
    a stub keeps the seed pinned and the surface minimal)."""
    from worlds.eldenring.features import shop_stock as ss
    from worlds.eldenring import contract

    class _MW:
        pass

    class _W:
        pass

    w = _W()
    w.multiworld = _MW()
    w.multiworld.seed = seed
    w.player = 1
    w.options = type("O", (), {
        "reroll_infinite_shop_stock": _Opt(1),
        "infinite_hub_wares": _Opt(set()),
        "no_runes_in_shops": _Opt(1 if ban else 0),
    })()
    return ss.ShopStockFeature().slot_data(w).get(contract.SHOP_INFINITE_STOCK, {})


def _is_rune_gid(gid):
    from worlds.eldenring.shop_stock_data import RUNE_PAYOUT
    return gid in RUNE_PAYOUT


def test_shelves_never_stock_a_rune_when_banned():
    from worlds.eldenring.features import shop_stock as ss
    pool = ss.pool()
    if not any(is_rune_item(nm) for nm in pool):
        pytest.fail("shop_stock.pool() no longer contains any rune ware -- the shelf half of "
                    "no_runes_in_shops is vacuous now; if that is deliberate, retire the filter "
                    "and this test together")
    for seed in range(30):
        for row, (gid, _et, _price) in _shelf_roll(seed, ban=True).items():
            assert not _is_rune_gid(gid), (
                "seed %d put rune good %d on shelf %s despite no_runes_in_shops" % (seed, gid, row))


def test_the_unbanned_draw_does_produce_runes_so_the_filter_is_load_bearing():
    """Non-vacuity: if no seed in this window ever rolls a rune unbanned, the previous test proves
    nothing. 30 seeds x 14 shelves at the current pool share makes a miss astronomically unlikely;
    if the pool's rune share shrinks to zero this fails loudly instead of the coverage rotting."""
    hits = sum(1 for seed in range(30)
               for _row, (gid, _et, _p) in _shelf_roll(seed, ban=False).items()
               if _is_rune_gid(gid))
    assert hits > 0, "30 unbanned seeds never rolled a rune shelf -- the ON test is vacuous"


def test_banned_and_unbanned_rolls_differ_only_when_the_ban_bites():
    """The OFF path must be bit-identical to a world with no such option (frozen default rule):
    stub without the attribute at all == stub with value 0."""
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
        })()   # note: NO no_runes_in_shops attribute -- the pre-option world

    legacy = ss.ShopStockFeature().slot_data(_W())[contract.SHOP_INFINITE_STOCK]
    assert legacy == _shelf_roll(424242, ban=False), (
        "an OFF option changed the shelf roll -- the default is not no-change")


# ---- option conflict ----------------------------------------------------------------------------

def test_a_rune_hub_pin_with_the_ban_is_an_OptionError_naming_both():
    class _T(WorldTestBase):
        game = GAME
        options = {"num_regions": 0, "no_runes_in_shops": True, "infinite_hub_wares": {"Golden Rune [5]"}}

    t = _T("runTest")
    t.options = dict(_T.options)
    with pytest.raises(OptionError) as e:
        t.world_setup()
    msg = str(e.value)
    assert "no_runes_in_shops" in msg and "infinite_hub_wares" in msg, (
        "the rejection must name both options: %r" % msg)
    assert "Golden Rune [5]" in msg, "the rejection must name the offending ware: %r" % msg


# ---- the fill-safety gate, called directly ------------------------------------------------------

def test_the_capacity_gate_both_ways():
    assert _skip_reason(10, 10) is None, "rune count == capacity is satisfiable; must enforce"
    assert _skip_reason(0, 0) is None
    r = _skip_reason(11, 10)
    assert r is not None and "11" in r and "10" in r, (
        "the skip reason must carry both numbers so the log line is actionable: %r" % r)
