"""The optional region-completion goal gate reaches the client and is compatibility-guarded."""

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring import contract  # noqa: E402

GAME = "Elden Ring"
TAG = "region_completion_goal_gate"


class ItemsHeldCompatibility(WorldTestBase):
    game = GAME
    options = {"num_regions": 3, "goal_region_unlock_policy": "items_held"}

    def test_default_keeps_the_existing_policy_without_demanding_a_new_client(self):
        sd = self.world.fill_slot_data()
        assert sd["options"]["goal_region_unlock_policy"] == 0
        assert TAG not in sd.get(contract.REQUIRES_CLIENT_FEATURES, [])


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
        contract.validate_slot_data(sd, strict=True)
