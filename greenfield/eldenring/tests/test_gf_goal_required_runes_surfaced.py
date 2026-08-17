"""#813 -- the Great Rune ending is a count over all seven eligible runes."""
import itertools

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring.core import GREAT_RUNES  # noqa: E402
from worlds.eldenring import contract as _contract  # noqa: E402
from ._util import world_items  # noqa: E402

GAME = "Elden Ring"


class AnyFourGreatRunesAreSurfaced(WorldTestBase):
    game = GAME
    options = {
        "num_regions": 0,
        "item_shuffle": True,
        "ending_condition": "great_runes",
        "goal_great_runes": 4,
        "leyndell_runes_required": 0,
    }

    def _world(self):
        return self.multiworld.worlds[self.player]

    def test_slot_data_carries_all_seven_names_and_the_count(self):
        sd = self._world().fill_slot_data()
        self.assertEqual(sd["great_runes_required"], 4)
        self.assertEqual(set(sd["great_rune_items"]), set(GREAT_RUNES))
        self.assertEqual(len(sd["great_rune_items"]), 7)

    def test_contract_still_declares_the_client_reader(self):
        key = [k for k in _contract.CONTRACT if k.name == "great_rune_items"]
        self.assertEqual(len(key), 1)
        self.assertIn("goal.rs", key[0].consumer)

    def test_every_four_rune_combination_satisfies_the_count(self):
        cond = self.multiworld.completion_condition[self.player]
        items = world_items(self)
        by_name = {}
        for item in items:
            if item.name in set(GREAT_RUNES):
                by_name.setdefault(item.name, item)
        self.assertEqual(set(by_name), set(GREAT_RUNES))

        for names in itertools.combinations(sorted(GREAT_RUNES), 4):
            state = self.multiworld.get_all_state(False)
            for victim in [i for i in items if i.name in set(GREAT_RUNES)]:
                state.remove(victim)
            for name in names:
                state.collect(by_name[name], prevent_sweep=True)
            self.assertTrue(cond(state), "four-rune combination failed: %r" % (names,))

    def test_three_runes_are_not_enough(self):
        cond = self.multiworld.completion_condition[self.player]
        items = world_items(self)
        state = self.multiworld.get_all_state(False)
        for victim in [i for i in items if i.name in set(GREAT_RUNES)]:
            state.remove(victim)
        by_name = {}
        for item in items:
            if item.name in set(GREAT_RUNES):
                by_name.setdefault(item.name, item)
        for name in sorted(by_name)[:3]:
            state.collect(by_name[name], prevent_sweep=True)
        self.assertFalse(cond(state))
