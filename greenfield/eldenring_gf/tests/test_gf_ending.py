"""Ending-condition (Great-Rune goal) tests -- WorldTestBase.

Covers the greenfield EndingCondition / GreatRunesRequired goal wired into core.py:
  * region_locks (default): goal unchanged -- completion needs every kept lock, no runes.
  * great_runes + item_shuffle on: seed still fills/beatable AND the goal actually requires the
    Great Runes (dropping a required rune breaks completion; the required runes are progression).
  * heavily-sealed seed (num_regions=1) + great_runes: the requirement auto-drops to what's
    reachable (here 0 -- only Limgrave survives, which has no Great Rune), so the seed collapses to
    the region_locks goal and stays beatable. This is the winnability guard: under-require, never
    over-require.

Each subclass runs AP's base suite for free (test_fill etc.), so "beatable" is asserted by the
harness; the extra methods assert the goal shape. importorskips when AP isn't importable
(source-tree sandbox), so it's a no-op there and only runs once installed under Archipelago/worlds/.

Run (from the Archipelago dir, world installed):
    python -m pytest worlds/eldenring_gf/tests/test_gf_ending.py
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")
from worlds.eldenring_gf.core import GREAT_RUNES  # noqa: E402
from BaseClasses import ItemClassification  # noqa: E402

GAME = "Elden Ring (Greenfield)"


def _held_runes(world, itempool):
    return [i for i in itempool if i.name in set(GREAT_RUNES)]


class RegionLocksGoalDefault(WorldTestBase):
    """Default ending goal is unchanged: all kept locks, zero Great Runes required."""
    game = GAME
    options = {"grace_rando": False}  # ending_condition defaults to region_locks

    def test_no_runes_required_by_default(self):
        world = self.multiworld.worlds[self.player]
        self.assertEqual(world._required_runes(), [],
                         "region_locks (default) goal must require no Great Runes")

    def test_all_state_beats_without_runes(self):
        # get_all_state grants every item; goal must be reachable and must be lock-only.
        state = self.multiworld.get_all_state(False)
        self.assertTrue(self.multiworld.completion_condition[self.player](state))

    def test_slot_data_reports_region_locks(self):
        sd = self.multiworld.worlds[self.player].fill_slot_data()
        self.assertEqual(sd["ending_condition"], "region_locks")
        self.assertEqual(sd["great_runes_required"], 0)


class GreatRunesGoalShuffleOn(WorldTestBase):
    """great_runes goal with item_shuffle on: beatable (base test_fill) AND the runes gate it."""
    game = GAME
    options = {
        "item_shuffle": True,
        "grace_rando": False,
        "ending_condition": "great_runes",
        "great_runes_required": 2,
    }

    def test_required_runes_resolved_and_progression(self):
        world = self.multiworld.worlds[self.player]
        req = world._required_runes()
        # full-region seed with shuffle on: at least the requested 2 runes must be reachable.
        self.assertEqual(len(req), 2, "full seed should honor great_runes_required=2")
        for name in req:
            self.assertIn(name, GREAT_RUNES)
        # the required runes are placed as progression items (so fill guarantees reachability).
        placed = [i for i in self.multiworld.itempool
                  if i.name in set(req)]
        self.assertTrue(placed, "required Great Runes must actually be in the pool")
        for i in placed:
            self.assertEqual(i.classification, ItemClassification.progression,
                             f"required Great Rune {i.name} must be progression")

    def test_goal_actually_needs_the_runes(self):
        world = self.multiworld.worlds[self.player]
        req = world._required_runes()
        cond = self.multiworld.completion_condition[self.player]
        # full state beats it.
        full = self.multiworld.get_all_state(False)
        self.assertTrue(cond(full))
        # removing a required rune from an otherwise-complete state breaks completion.
        # remove ALL copies of a required rune (Land of Shadow duplicates the runes, so state.has
        # stays true until every copy is gone) -> completion must then break.
        one = req[0]
        for victim in [i for i in self.multiworld.itempool if i.name == one]:
            full.remove(victim)
        self.assertFalse(cond(full),
                         "dropping every copy of a required Great Rune must break the great_runes goal")

    def test_slot_data_reports_great_runes(self):
        sd = self.multiworld.worlds[self.player].fill_slot_data()
        self.assertEqual(sd["ending_condition"], "great_runes")
        self.assertEqual(sd["great_runes_required"], 2)
        self.assertEqual(len(sd["great_rune_items"]), 2)


class GreatRunesGoalHeavilySealed(WorldTestBase):
    """num_regions=1 spine keeps only Limgrave (+ always-kept goal region). Limgrave has no Great
    Rune, so the requirement auto-drops and the seed reverts to region_locks -- still beatable."""
    game = GAME
    options = {
        "item_shuffle": True,
        "grace_rando": False,
        "num_regions": 1,
        "num_regions_order": "spine",
        "ending_condition": "great_runes",
        "great_runes_required": 7,
    }

    def test_requirement_auto_drops(self):
        world = self.multiworld.worlds[self.player]
        avail = world._available_runes()
        req = world._required_runes()
        self.assertEqual(len(req), len(avail),
                         "requirement must clamp to reachable Great Runes")
        self.assertLessEqual(len(req), 7)
        # if no Great Rune region survived, the goal must collapse to locks-only (req == []).
        if not avail:
            self.assertEqual(req, [],
                             "no reachable Great Rune -> goal falls back to region_locks")

    def test_still_beatable(self):
        state = self.multiworld.get_all_state(False)
        self.assertTrue(self.multiworld.completion_condition[self.player](state),
                        "heavily-sealed great_runes seed must remain winnable")

    def test_slot_data_matches_effective_requirement(self):
        world = self.multiworld.worlds[self.player]
        sd = world.fill_slot_data()
        self.assertEqual(sd["great_runes_required"], len(world._required_runes()))
        expected = "great_runes" if world._required_runes() else "region_locks"
        self.assertEqual(sd["ending_condition"], expected)


class GreatRunesGoalShuffleOffFallsBack(WorldTestBase):
    """great_runes goal but item_shuffle OFF: no Great Rune items exist, so the goal falls back to
    region_locks (requirement 0). Guards against requiring items that were never created."""
    game = GAME
    options = {
        "item_shuffle": False,
        "grace_rando": False,
        "ending_condition": "great_runes",
        "great_runes_required": 3,
    }

    def test_no_runes_without_shuffle(self):
        world = self.multiworld.worlds[self.player]
        self.assertEqual(world._required_runes(), [],
                         "great_runes goal with shuffle off must require no runes")
        sd = world.fill_slot_data()
        self.assertEqual(sd["ending_condition"], "region_locks")
        self.assertEqual(sd["great_runes_required"], 0)
