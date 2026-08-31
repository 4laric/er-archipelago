"""#1091: direct rune reward scaling is an explicit, safely negotiated opt-in."""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")


class RuneRewardScalingOff(WorldTestBase):
    game = "Elden Ring"
    options = {"num_regions": 0, "scale_rune_rewards": False}

    def test_default_path_emits_off_and_requires_no_new_client(self):
        sd = self.world.fill_slot_data()
        assert sd["options"]["scale_rune_rewards"] == 0
        assert "rune_reward_scaling" not in sd.get("requiresClientFeatures", [])


class RuneRewardScalingOn(WorldTestBase):
    game = "Elden Ring"
    options = {"num_regions": 0, "scale_rune_rewards": True}

    def test_opt_in_emits_value_and_feature_handshake(self):
        sd = self.world.fill_slot_data()
        assert sd["options"]["scale_rune_rewards"] == 1
        assert "rune_reward_scaling" in sd["requiresClientFeatures"]
