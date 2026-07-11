"""Smoke test for the feature registry: every registered phase contributes its option surface and
its slot_data keys (skeleton stubs count -- empty dicts are a valid contract). Full per-feature
behavior tests live in test_gf_<phase>.py."""
import dataclasses
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")

GAME = "Elden Ring (Greenfield)"
_OPTS = ("completion_scaling_floor", "global_scadutree_blessing", "dungeon_sweep",
         "boss_lock_placement", "merchant_bell_logic")
_KEYS = ("completion_scaling", "dungeonSweeps", "sweepLockGates", "shopRowFlags",
         "shopPreviewGoods", "regionGraces", "startGraces")


class FeaturesSmoke(WorldTestBase):
    game = GAME
    options = {"dungeon_sweep": "all"}

    def test_feature_options_present(self):
        """Every declared feature option must be ACCOUNTED FOR: either yaml-exposed in GFOptions, or
        frozen as behaviour in defaults.FROZEN_OPTIONS. Neither silently dropped nor double-counted."""
        from worlds.eldenring_gf.defaults import FROZEN_OPTIONS
        names = {f.name for f in dataclasses.fields(self.world.options_dataclass)}
        for o in _OPTS:
            self.assertTrue(o in names or o in FROZEN_OPTIONS,
                            f"feature option {o!r} is neither in GFOptions nor FROZEN_OPTIONS")
            self.assertFalse(o in names and o in FROZEN_OPTIONS,
                             f"feature option {o!r} is BOTH yaml-exposed and frozen")

    def test_feature_slot_data_keys_present(self):
        sd = self.world.fill_slot_data()   # merge_slot_data raises on any key collision
        for k in _KEYS:
            self.assertIn(k, sd, f"feature slot_data key {k!r} missing")

    def test_fingerslayer_chest_gate_flag_force_set(self):
        # The Nokron Fingerslayer Blade chest (check 12027080) is vanilla-gated behind Ranni's-Rise
        # flag 1034509410; start_grace force-sets it on the startGraces spawn-flag list so the chest
        # opens ("not destined" otherwise) and the check stays reachable in a warp-shuffle seed.
        sd = self.world.fill_slot_data()
        self.assertIn(1034509410, sd["startGraces"],
                      "Ranni chest-gate flag 1034509410 must ride startGraces so check 12027080 opens")
