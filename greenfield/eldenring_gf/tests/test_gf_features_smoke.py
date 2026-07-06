"""Smoke test for the feature registry: every registered phase contributes its option surface and
its slot_data keys (skeleton stubs count -- empty dicts are a valid contract). Full per-feature
behavior tests live in test_gf_<phase>.py."""
import dataclasses
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")

GAME = "Elden Ring (Greenfield)"
_OPTS = ("completion_scaling_floor", "global_scadutree_blessing", "dungeon_sweep",
         "boss_lock_placement", "merchant_bell_logic", "grace_rando")
_KEYS = ("completion_scaling", "dungeonSweeps", "sweepLockGates", "shopRowFlags",
         "shopPreviewGoods", "regionGraces", "graceItems", "startGraces")


class FeaturesSmoke(WorldTestBase):
    game = GAME
    options = {"dungeon_sweep": "all"}

    def test_feature_options_present(self):
        names = {f.name for f in dataclasses.fields(self.world.options_dataclass)}
        for o in _OPTS:
            self.assertIn(o, names, f"feature option {o!r} missing from GFOptions")

    def test_feature_slot_data_keys_present(self):
        sd = self.world.fill_slot_data()   # merge_slot_data raises on any key collision
        for k in _KEYS:
            self.assertIn(k, sd, f"feature slot_data key {k!r} missing")
