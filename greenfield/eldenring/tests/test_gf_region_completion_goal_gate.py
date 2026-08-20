"""The optional region-completion goal gate reaches the client and is compatibility-guarded."""

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring import contract  # noqa: E402
from worlds.eldenring.core import GREAT_RUNES  # noqa: E402
from ._util import world_items  # noqa: E402

GAME = "Elden Ring"
TAG = "region_completion_goal_gate"


class ItemsHeldCompatibility(WorldTestBase):
    game = GAME
    options = {"num_regions": 3, "goal_region_unlock_policy": "items_held"}

    def test_default_keeps_the_existing_policy_without_demanding_a_new_client(self):
        sd = self.world.fill_slot_data()
        assert sd["options"]["goal_region_unlock_policy"] == 0
        assert TAG not in sd.get(contract.REQUIRES_CLIENT_FEATURES, [])
        assert sd[contract.GOAL_REQUIRED_ITEMS]


class RegionsCompleted(WorldTestBase):
    game = GAME
    options = {"num_regions": 3, "goal_region_unlock_policy": "regions_completed"}

    def test_selected_policy_is_sent_and_requires_the_supporting_client(self):
        sd = self.world.fill_slot_data()
        assert sd["options"]["goal_region_unlock_policy"] == 1
        assert TAG in sd.get(contract.REQUIRES_CLIENT_FEATURES, [])
        assert sd[contract.PROGRESSION_SURFACE_LOCATIONS], (
            "region completion needs the exact per-seed surface the client reconciles")
        assert sd[contract.LOCATION_REGIONS], (
            "region completion needs the per-seed location-to-region assignment")
        assert contract.GOAL_REQUIRED_ITEMS not in sd, (
            "completed regions replace rather than supplement the held-lock gate")
        contract.validate_slot_data(sd, strict=True)


class NoRegionRequirement(WorldTestBase):
    game = GAME
    options = {"num_regions": 3, "goal_region_unlock_policy": "none"}

    def test_none_is_a_distinct_wire_value_with_no_region_gate(self):
        sd = self.world.fill_slot_data()
        assert sd["options"]["goal_region_unlock_policy"] == 2
        assert TAG not in sd.get(contract.REQUIRES_CLIENT_FEATURES, [])
        assert contract.GOAL_REQUIRED_ITEMS not in sd
        assert self.multiworld.completion_condition[self.player](
            self.multiworld.get_all_state(False))
        contract.validate_slot_data(sd, strict=True)


class GreatRunesOnly(WorldTestBase):
    game = GAME
    options = {
        "num_regions": 3,
        "item_shuffle": True,
        "ending_condition": "great_runes",
        "goal_great_runes": 4,
        "goal_region_unlock_policy": "none",
    }

    def test_four_runes_satisfy_the_goal_without_region_locks(self):
        world = self.world
        sd = world.fill_slot_data()
        assert contract.GOAL_REQUIRED_ITEMS not in sd
        assert sd["great_runes_required"] == 4

        state = self.multiworld.get_all_state(False)
        all_items = world_items(self)
        for item in [i for i in all_items if i.name in set(GREAT_RUNES) or i.name.endswith(" Lock")]:
            state.remove(item)
        runes = {}
        for item in all_items:
            if item.name in set(GREAT_RUNES):
                runes.setdefault(item.name, item)
        chosen = [runes[name] for name in sorted(runes)[:4]]
        for item in chosen[:3]:
            state.collect(item, prevent_sweep=True)
        condition = self.multiworld.completion_condition[self.player]
        assert not condition(state)
        state.collect(chosen[3], prevent_sweep=True)
        assert condition(state), "the fourth rune alone must complete the independent rune axis"


class GreatRunesAndCompletedRegions(WorldTestBase):
    game = GAME
    options = {
        "num_regions": 3,
        "item_shuffle": True,
        "ending_condition": "great_runes",
        "goal_great_runes": 4,
        "goal_region_unlock_policy": "regions_completed",
    }

    def test_both_runtime_axes_are_emitted_without_a_held_lock_gate(self):
        sd = self.world.fill_slot_data()
        assert sd["great_runes_required"] == 4
        assert TAG in sd[contract.REQUIRES_CLIENT_FEATURES]
        assert contract.GOAL_REQUIRED_ITEMS not in sd
