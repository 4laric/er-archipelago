"""`region_locks_anywhere` -- the knob that lets Region Locks be ordinary multiworld items.

WHY IT EXISTS (er-archipelago#491). The Progression Surface removes this world's own advancement
items from the multiworld itempool in `pre_fill` and places them on THIS PLAYER'S OWN locations.
Only items the surface could not host go back to the pool -- the "spill" valve -- and that valve is
the only route by which a Region Lock could ever reach another player's world.

Measured before this option existed, on `08913bf`: **0 spill across 146 world-instances** (num_regions
0/4/12, a GreatRune-only surface, natural_progression, 2xER multiworlds) and **0 of 105 placed Locks
foreign** across 8 two-player seeds, while the same spoiler parser saw 49.2% of all other rows crossing
worlds. The surface hosts ~170 checks against a ceiling of 36 restricted items -- ~4.7x headroom -- so
the ladder never widened once and the valve never opened. Region Locks were effectively 100% local.

Alaric's call, 2026-08-09: "default 100% i think it should be opt out. possibility of getting BK'ed
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
    RegionLocksAnywhere, released_locks, lock_region_name,
)


class _Item:
    """The minimum `released_locks` reads. Deliberately not a real AP Item: the function is pure over
    `.name`, and a test that needed a world would not be testing that."""

    def __init__(self, name):
        self.name = name

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
        self.assertEqual(RegionLocksAnywhere.default, 100)
        self.assertEqual(RegionLocksAnywhere.range_start, 0)
        self.assertEqual(RegionLocksAnywhere.range_end, 100)

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


if __name__ == "__main__":
    unittest.main()
