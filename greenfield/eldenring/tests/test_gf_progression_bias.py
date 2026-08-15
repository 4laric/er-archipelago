"""`progression_bias` -- the knob that lets Region Locks be ordinary multiworld items.

WHY IT EXISTS (er-archipelago#491). The Progression Surface removes this world's own advancement
items from the multiworld itempool in `pre_fill` and places them on THIS PLAYER'S OWN locations.
Only items the surface could not host go back to the pool -- the "spill" valve -- and that valve is
the only route by which a Region Lock could ever reach another player's world.

Measured before this option existed, on `08913bf`: **0 spill across 146 world-instances** (num_regions
0/4/12, a GreatRune-only surface, natural_progression, 2xER multiworlds) and **0 of 105 placed Locks
foreign** across 8 two-player seeds, while the same spoiler parser saw 49.2% of all other rows crossing
worlds. The surface hosts ~170 checks against a ceiling of 36 restricted items -- ~4.7x headroom -- so
the ladder never widened once and the valve never opened. Region Locks were effectively 100% local.

Alaric's call, 2026-08-09: "default 100% [released] i think it should be opt out. possibility of getting BK'ed
is part of the spirit of archipelago." So the default releases every Lock, and lowering the number
buys curation back.

WHAT THESE TESTS GUARD. `released_locks` is pure, which is the point: the endpoints must be EXACT
(not a rounding artifact), the draw must come from the world's own rng, and it must never touch an
item that is not a Lock -- required Great Runes and legacy keys keep the surface whatever the
percentage says.
"""
import unittest

import pytest

pytest.importorskip("worlds.eldenring")

from worlds.eldenring.features.progression_surface import (  # noqa: E402
    ProgressionBias, released_locks, lock_region_name, place_released_locks,
    CrossGameProgression, cross_game_share, _foreign_open_locations,
)


class _Item:
    """The minimum `released_locks` reads. Deliberately not a real AP Item: the function is pure over
    `.name`, and a test that needed a world would not be testing that."""

    def __init__(self, name, player=1):
        self.name = name
        self.player = player
        self.advancement = True

    def __repr__(self):
        return f"_Item({self.name!r})"


def _pool():
    """A realistic restricted set: four Locks plus the two kinds of non-Lock progression that share
    the surface with them."""
    return [
        _Item("Limgrave Lock"),
        _Item("Liurnia Lock"),
        _Item("Caelid Lock"),
        _Item("Altus Lock"),
        _Item("Godrick's Great Rune"),
        _Item("Academy Glintstone Key"),
    ]


class _Rng:
    """A `.sample` that is deterministic and RECORDS that it was called -- the draw must come from
    `world.random`, because a seed has to reproduce. Takes the first k, which is enough to assert
    over while staying independent of any real rng's algorithm."""

    def __init__(self):
        self.calls = 0

    def sample(self, population, k):
        self.calls += 1
        return list(population)[:k]


class TestReleasedLocks(unittest.TestCase):
    def test_the_default_is_one_hundred_and_that_is_the_whole_feature(self):
        """THE MOTIVATING CASE. Alaric asked for opt-OUT: a yaml that never mentions this option
        must put every Lock in the multiworld pool."""
        self.assertEqual(ProgressionBias.default, 0)      # 0 bias = no pull home = release all
        self.assertEqual(ProgressionBias.range_start, 0)
        self.assertEqual(ProgressionBias.range_end, 100)

    def test_one_hundred_releases_every_lock_and_nothing_else(self):
        pool = _pool()
        rng = _Rng()
        out = released_locks(pool, 100, rng)
        self.assertEqual(sorted(i.name for i in out),
                         ["Altus Lock", "Caelid Lock", "Limgrave Lock", "Liurnia Lock"])
        # The endpoint is exact by construction, so it must not have needed a draw at all.
        self.assertEqual(rng.calls, 0)

    def test_zero_releases_nothing_which_is_the_pre_option_behaviour(self):
        pool = _pool()
        # WITNESS: the pool really does hold Locks, so "released nothing" is a decision and not the
        # filter having quietly stopped matching.
        self.assertTrue([i for i in pool if lock_region_name(i.name)])
        rng = _Rng()
        self.assertEqual(released_locks(pool, 0, rng), [])
        self.assertEqual(rng.calls, 0)

    def test_runes_and_keys_are_never_released_at_any_percentage(self):
        """Only Locks were asked for. Widening this to the rest of the restricted set would be a
        different feature, and a silent one."""
        saw = 0
        for pct in (0, 1, 50, 99, 100):
            out = released_locks(_pool(), pct, _Rng())
            saw += len(out)
            for it in out:
                self.assertIsNotNone(
                    lock_region_name(it.name),
                    f"{it.name} is not a Region Lock but was released at {pct}%")
        # WITNESS: something was released across that sweep, or the loop above proved nothing.
        self.assertTrue(saw)

    def test_a_partial_release_draws_from_the_worlds_rng(self):
        """Determinism: the subset must come from `world.random`, never module `random`, or the same
        seed would roll differently on a re-gen."""
        rng = _Rng()
        out = released_locks(_pool(), 50, rng)
        self.assertEqual(rng.calls, 1)
        self.assertEqual(len(out), 2)  # 4 locks * 50%

    def test_rounding_is_half_up_so_a_small_seed_is_not_silently_zero(self):
        """Python's `round()` is BANKER'S rounding -- `round(0.5) == 0` -- so a 50% setting on a
        one-Lock seed would release nothing and read as the feature being broken, on exactly the
        seeds small enough for a player to check by hand."""
        self.assertEqual(len(released_locks([_Item("Limgrave Lock")], 50, _Rng())), 1)
        # And it still rounds DOWN below the halfway point rather than always releasing something.
        self.assertEqual(len(released_locks([_Item("Limgrave Lock")], 49, _Rng())), 0)

    def test_a_seed_with_no_locks_is_not_an_error(self):
        """natural_progression and vanilla_placement mint no Lock items at all; the option must be
        inert there rather than raising or drawing."""
        pool = [_Item("Godrick's Great Rune")]
        # WITNESS: the input is non-empty, so the empty RESULT is about there being no Locks in it
        # rather than about there being nothing at all.
        self.assertTrue(pool)
        rng = _Rng()
        self.assertEqual(released_locks(pool, 100, rng), [])
        self.assertEqual(rng.calls, 0)

    def test_the_ashen_capital_lock_travels_with_the_others(self):
        """It is a Lock by name and by role -- the finale gate. Leaving it behind would mean the one
        Lock the goal actually requires is the one that never enters the multiworld."""
        out = released_locks([_Item("Ashen Capital Lock")], 100, _Rng())
        self.assertEqual([i.name for i in out], ["Ashen Capital Lock"])

    def test_released_items_are_the_same_objects_not_copies(self):
        """`apply()` filters the placement list by object identity, so a copy here would leave the
        item in BOTH lists: placed on the surface AND left in the pool."""
        pool = _pool()
        out = released_locks(pool, 100, _Rng())
        for it in out:
            self.assertTrue(any(it is p for p in pool))


class TestThePlacerContract(unittest.TestCase):
    """`place_released_locks` -- the stage_pre_fill pass, and the two things about it that are not
    obvious from reading it.

    It REPLACED an item_rule bar (`released_lock_barred`) that worked and had no spill: `apply()` is
    documented "Never FillErrors" because confined Locks get the ladder AND the return-to-pool valve,
    and a bare rule had neither. Three configurations found that -- a narrowed surface,
    `num_regions: 1`, and a shifted filler pool -- each missed by a different count-based threshold,
    because capacity is not the constraint. Reachable capacity in sphere order is, and a real fill is
    the only thing that can measure it.
    """

    def test_nothing_released_is_a_no_op_with_no_archipelago_needed(self):
        """The hook runs on EVERY multiworld containing this game, including seeds that released
        nothing (bias 100) and modes that mint no Locks at all. It must return before it touches a
        pool, a state or a location -- which is exactly what makes this callable with a stub."""
        class _W:
            gf_released_lock_items = []

        class _MW:
            def __init__(self):
                self.itempool = ["untouched"]

        mw = _MW()
        # WITNESS: the pool is non-empty going in, so "unchanged" is a fact about the hook rather
        # than about there having been nothing to change.
        self.assertTrue(mw.itempool)
        place_released_locks(mw, [_W(), _W()])
        self.assertEqual(mw.itempool, ["untouched"])

    def test_a_world_that_never_ran_apply_is_skipped_not_crashed(self):
        """`gf_released_lock_items` is set in `apply()`, which returns early in several modes
        (vanilla placement, surface off, nothing restricted). A world that never reached it has no
        such attribute at all, and a stage hook that assumed one would take the whole multiworld
        down with an AttributeError."""
        class _Bare:
            pass

        class _MW:
            def __init__(self):
                self.itempool = ["someone else's item"]

        mw = _MW()
        # WITNESS: a NON-empty pool, so "unchanged" is an observation about the hook and not about
        # an empty container being trivially equal to another one.
        self.assertTrue(mw.itempool)
        place_released_locks(mw, [_Bare()])
        self.assertEqual(mw.itempool, ["someone else's item"])


class _Loc:
    """The four fields `_foreign_open_locations` reads. `progress_type` defaults to the sentinel the
    helper treats as "fine", so a test only sets it when EXCLUDED is the point."""

    def __init__(self, name, player, item=None, locked=False, progress_type=None):
        self.name = name
        self.player = player
        self.item = item
        self.locked = locked
        self.progress_type = progress_type

    def __repr__(self):
        return f"_Loc({self.name!r}, p{self.player})"


class TestCrossGameShare(unittest.TestCase):
    """`cross_game_share` -- Alaric's ruling, 2026-08-15: "yaml knob but 1/N is good. 2 games, 50% of
    locks in hk". The function is pure over the option value and the GAME count, which is the whole
    reason it is testable without Archipelago."""

    class _W:
        def __init__(self, value):
            self.options = type("_O", (), {
                "cross_game_progression": type("_V", (), {"value": value})()})()

    def test_auto_is_one_over_n_games(self):
        """THE RULING, literally. Two games is half."""
        self.assertEqual(cross_game_share(self._W(-1), 2), 50)
        self.assertEqual(cross_game_share(self._W(-1), 3), 33)
        self.assertEqual(cross_game_share(self._W(-1), 4), 25)
        self.assertEqual(cross_game_share(self._W(-1), 8), 13)

    def test_auto_rounds_half_up_not_to_even(self):
        """🛑 `round(100/8)` is 12, not 13, because Python rounds halves TO EVEN. The export-volume
        half of #703 caps at 1/N by integer arithmetic, so `round` here would put the two halves one
        point apart on any seed where 100/N lands on a half -- silently, and only sometimes."""
        self.assertEqual(cross_game_share(self._W(-1), 8), 13)
        self.assertNotEqual(cross_game_share(self._W(-1), 8), round(100.0 / 8))
        for n in (2, 3, 4, 5, 6, 8, 10):
            self.assertEqual(cross_game_share(self._W(-1), n), (100 + n // 2) // n)

    def test_never_and_zero_are_the_escape_hatch(self):
        """🛑 The one that matters operationally: a partner apworld that objects to being filled
        during pre_fill has to be switchable off, and off must mean OFF."""
        # WITNESS: the identical stub at `auto` returns 50, so a 0 here is the VALUE being read
        # and honoured -- not the option plumbing failing and everything returning 0.
        self.assertEqual(cross_game_share(self._W(-1), 2), 50)
        self.assertEqual(cross_game_share(self._W(0), 2), 0)
        self.assertEqual(CrossGameProgression.special_range_names["never"], 0)

    def test_an_explicit_percentage_is_taken_literally(self):
        self.assertEqual(cross_game_share(self._W(30), 2), 30)
        self.assertEqual(cross_game_share(self._W(100), 4), 100)

    def test_a_solo_or_single_game_seed_gets_zero_because_there_is_nowhere_to_send(self):
        """Not a policy, an arithmetic fact: 1/1 would say 100% and there is no partner to receive
        it. An all-Elden-Ring multiworld is ONE game however many slots it has."""
        # WITNESS: both stubs return something at TWO games, so the zeros below are the game count
        # being consulted rather than the function having stopped working.
        self.assertEqual(cross_game_share(self._W(-1), 2), 50)
        self.assertEqual(cross_game_share(self._W(100), 2), 100)
        self.assertEqual(cross_game_share(self._W(-1), 1), 0)
        self.assertEqual(cross_game_share(self._W(100), 1), 0)

    def test_an_older_yaml_without_the_option_behaves_as_it_did_before_the_option(self):
        """`getattr` default, and it is load-bearing: every test suite in this repo that builds a
        world stub without options would otherwise start crashing in a stage hook."""
        class _Bare:
            pass
        # WITNESS: same call, same game count, a world that HAS the option -- non-zero. So the 0 is
        # the missing attribute being defaulted, not the whole helper being inert.
        self.assertEqual(cross_game_share(self._W(-1), 2), 50)
        self.assertEqual(cross_game_share(_Bare(), 2), 0)


class TestForeignOpenLocations(unittest.TestCase):
    """`_foreign_open_locations` -- which of a PARTNER's locations we may honestly offer a Lock."""

    class _MW:
        def __init__(self, locs):
            self._locs = locs

        def get_locations(self):
            return self._locs

    def _all(self):
        return [
            _Loc("ours", 1),
            _Loc("theirs open", 2),
            _Loc("theirs filled", 2, item=object()),
            _Loc("theirs locked", 2, locked=True),
        ]

    def test_only_a_partners_empty_unlocked_locations_are_offered(self):
        locs = self._all()
        out = _foreign_open_locations(self._MW(locs), {1})
        self.assertEqual([loc.name for loc in out], ["theirs open"])

    def test_our_own_locations_are_the_other_passs_business(self):
        """The Elden Ring surface pass runs after this one over exactly these. Offering them twice
        would let the cross-game share eat the curated surface it is supposed to leave alone."""
        locs = self._all()
        out = _foreign_open_locations(self._MW(locs), {1})
        self.assertFalse([loc for loc in out if loc.player == 1])
        # WITNESS: player 1 really had a location in the scan, so "none of ours" is a filter doing
        # work and not an empty input.
        self.assertTrue([loc for loc in locs if loc.player == 1])

    def test_a_location_another_world_already_filled_is_never_overwritten(self):
        """A partner's own `pre_fill` runs BEFORE this stage hook. Its placements are decisions."""
        locs = self._all()
        out = _foreign_open_locations(self._MW(locs), {1})
        self.assertFalse([loc for loc in out if loc.item is not None])
        self.assertTrue([loc for loc in locs if loc.item is not None])

    def test_excluded_locations_never_receive_a_lock(self):
        """🛑 THE ONE NOBODY ELSE CHECKS. `exclude_locations` is a player's promise that nothing
        REQUIRED sits there, and a released Lock is progression. `fill_restrictive` does not consult
        `progress_type` -- `distribute_items_restrictive` filters before calling it -- so if this
        helper does not filter, the promise is broken silently."""
        from BaseClasses import LocationProgressType
        excluded = _Loc("theirs excluded", 2, progress_type=LocationProgressType.EXCLUDED)
        allowed = _Loc("theirs default", 2, progress_type=LocationProgressType.DEFAULT)
        out = _foreign_open_locations(self._MW([excluded, allowed]), {1})
        self.assertEqual([loc.name for loc in out], ["theirs default"])

    def test_no_partner_means_no_offer_rather_than_an_error(self):
        # WITNESS: the same scan over the same location plus one partner location DOES return it,
        # so the empty result below is "there is no partner here" and not a broken walk.
        self.assertEqual(
            [loc.name for loc in
             _foreign_open_locations(self._MW([_Loc("ours", 1), _Loc("theirs", 2)]), {1})],
            ["theirs"])
        out = _foreign_open_locations(self._MW([_Loc("ours", 1)]), {1})
        self.assertEqual(out, [])


if __name__ == "__main__":
    unittest.main()
