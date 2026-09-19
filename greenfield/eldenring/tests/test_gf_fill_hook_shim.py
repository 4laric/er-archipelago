"""`features/fill_hook_shim.pool_view` -- the one adapter between core's `stage_fill_hook`
signature and our seven passes, tested against fakes because the contract is pure list mechanics.

The shim is the entire difference between the hook core gives us and the `multiworld.itempool`
dialect the passes speak, so every clause of it gets a test: core's order survives, a placement is
reconciled out of BOTH lists, a pop-and-return is not mistaken for a placement, the dead pool is
left dead, and none of that depends on the body returning normally.
See docs/specs/SPEC-fill-hook-migration-20260907.md section 2.
"""
import unittest

import pytest

pytest.importorskip("worlds.eldenring")

from worlds.eldenring.features.fill_hook_shim import pool_view  # noqa: E402


class _Loc:
    def __init__(self, name):
        self.name = name
        self.item = None

    def place(self, item):
        self.item = item
        item.location = self


class _Item:
    def __init__(self, name):
        self.name = name
        self.location = None


class _MW:
    def __init__(self):
        self.itempool = []


def _fixture():
    mw = _MW()
    prog = [_Item("prog %d" % i) for i in range(3)]
    useful = [_Item("useful %d" % i) for i in range(2)]
    filler = [_Item("filler %d" % i) for i in range(2)]
    locs = [_Loc("loc %d" % i) for i in range(4)]
    return mw, prog, useful, filler, locs


class PoolViewContract(unittest.TestCase):
    def test_round_trip_leaves_cores_order_intact(self):
        """Nothing placed, nothing changed: the pools come back as the same objects in the same
        order, because the shim FILTERS the originals rather than rebuilding them from the view."""
        mw, prog, useful, filler, locs = _fixture()
        before = (list(prog), list(useful), list(filler), list(locs))
        with pool_view(mw, prog, useful, filler, locs):
            self.assertEqual(mw.itempool, before[0] + before[1] + before[2])
        self.assertEqual(prog, before[0])
        self.assertEqual(useful, before[1])
        self.assertEqual(filler, before[2])
        self.assertEqual(locs, before[3])

    def test_a_placement_leaves_both_lists(self):
        """What core reads after the hook is the three pools and `fill_locations`. An item we
        placed that is still in a pool gets placed TWICE; a location we filled that is still in
        `fill_locations` is handed to fill as an empty slot."""
        mw, prog, useful, filler, locs = _fixture()
        placed, target = prog[1], locs[2]
        with pool_view(mw, prog, useful, filler, locs):
            mw.itempool.remove(placed)      # what every one of our passes does with its batch
            target.place(placed)
        self.assertNotIn(placed, prog)
        self.assertEqual([i.name for i in prog], ["prog 0", "prog 2"])
        self.assertNotIn(target, locs)
        self.assertEqual([l.name for l in locs], ["loc 0", "loc 1", "loc 3"])

    def test_an_item_popped_and_returned_survives(self):
        """The refusal path. Every pass pops its batch up front and returns whatever fill refused;
        a returned item is unplaced, so it must still be in its own pool, in its original slot."""
        mw, prog, useful, filler, locs = _fixture()
        refused = useful[0]
        with pool_view(mw, prog, useful, filler, locs):
            mw.itempool.remove(refused)
            mw.itempool.append(refused)     # ... and hands it back
        self.assertEqual([i.name for i in useful], ["useful 0", "useful 1"])
        self.assertIs(useful[0], refused)

    def test_the_dead_pool_is_left_empty(self):
        """`multiworld.itempool` is dead after `Fill.py:500`. We revive it for the body only; a
        later reader should get nothing rather than a plausible stale list."""
        mw, prog, useful, filler, locs = _fixture()
        with pool_view(mw, prog, useful, filler, locs):
            # WITNESS: the view really held the whole pool, so "empty afterwards" is the shim
            # clearing it and not a fixture that was empty all along.
            self.assertEqual(len(mw.itempool), 7)
        self.assertEqual(mw.itempool, [])

    def test_exit_runs_on_exception(self):
        """A pass that raises must not leave core holding a pool with placed items in it -- the
        seed would either die confusingly or place the same item twice."""
        mw, prog, useful, filler, locs = _fixture()
        placed, target = prog[0], locs[0]

        class _Boom(Exception):
            pass

        with self.assertRaises(_Boom):
            with pool_view(mw, prog, useful, filler, locs):
                mw.itempool.remove(placed)
                target.place(placed)
                raise _Boom()
        # WITNESS: the reconciliation ran and kept everything else, rather than emptying the lists.
        self.assertEqual([i.name for i in prog], ["prog 1", "prog 2"])
        self.assertEqual([l.name for l in locs], ["loc 1", "loc 2", "loc 3"])
        self.assertNotIn(placed, prog)
        self.assertNotIn(target, locs)
        self.assertEqual(mw.itempool, [])


class _PItem(_Item):
    def __init__(self, name, player):
        super().__init__(name)
        self.player = player


class _NamedMW(_MW):
    def __init__(self):
        super().__init__()
        self.worlds = {2: type("W", (), {"game": "Some Other Game"})()}

    def get_player_name(self, player):
        return {2: "Partner"}.get(player, "P%d" % player)


class NamesTheCulprit(unittest.TestCase):
    """2026-09-18: alttpr's pot hook (2026-08-28 build) placed 128 items and removed an unplaced
    same-named twin from the pool instead (`list.remove` compares by name + player). The placed
    items were still in the pools when our hook started, and the failure read "a pass created or
    dropped an item" -- pointing at us. It has to point at the owner."""

    def test_an_already_placed_item_in_a_pool_is_named_at_entry(self):
        mw = _NamedMW()
        stale = _PItem("Small Heart", 2)
        Loc = _Loc("pot")
        Loc.place(stale)
        prog, useful, filler, locs = [], [], [stale, _PItem("Small Heart", 2)], []
        with self.assertRaises(AssertionError) as ctx:
            with pool_view(mw, prog, useful, filler, locs):
                self.fail("the body must not run over a corrupted pool")   # pragma: no cover
        msg = str(ctx.exception)
        self.assertIn("already PLACED", msg)
        self.assertIn("1x Small Heart [Partner (Some Other Game)]", msg)
        self.assertIn("not an Elden Ring pass", msg)
        # Nothing was mutated on the way out: the dead pool was never revived.
        self.assertEqual(mw.itempool, [])

    def test_a_pass_that_drops_an_item_names_it_at_exit(self):
        mw = _NamedMW()
        a, b = _PItem("Rune", 1), _PItem("Small Magic", 2)
        with self.assertRaises(AssertionError) as ctx:
            with pool_view(mw, [a], [], [b], []):
                mw.itempool.remove(b)           # dropped on the floor: neither placed nor returned
        msg = str(ctx.exception)
        self.assertIn("created or dropped an item", msg)
        self.assertIn("1x Small Magic [Partner (Some Other Game)]", msg)
        self.assertIn("In multiworld.itempool only: none", msg)

    def test_a_clean_run_raises_nothing(self):
        mw = _NamedMW()
        with pool_view(mw, [_PItem("Rune", 1)], [], [_PItem("Small Magic", 2)], []):
            pass


if __name__ == "__main__":       # pragma: no cover
    unittest.main()
