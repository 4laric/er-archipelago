"""Regression: pool_builder must reserve ALL non-juice pool contributors, not just region Locks.

pool_builder sizes its juice to the "true remaining Rune tail" = Rune-fallback checks minus the slots
the OTHER pool contributors already consume. That reserve used to be just len(kept) (one Lock per kept
region), so Boss Keys (boss_keys mode) and progressive copies went uncounted -> juice over-provisioned
and the over-provision trim dropped REAL vanilla gear past the Rune tail (count stayed exact via
range(slots), so it was a silent precision bug, not a crash). core.create_items now runs pool_builder
LAST and records the exact consumed-slot count on the world, so the reserve includes boss keys etc.

This drives the collision (boss_keys ON + juice_pct 100) and asserts the reserve covers the boss keys
and that total contributions (reserve + juice) never exceed the Rune-fallback count.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")

from worlds.eldenring_gf.data import LOCATIONS, HUB  # noqa: E402
from ._util import world_items, world_pool_items  # noqa: E402
from worlds.eldenring_gf.features.pool_builder import PoolBuilderFeature  # noqa: E402

GAME = "Elden Ring (Greenfield)"


class ReserveCountsBossKeys(WorldTestBase):
    game = GAME
    options = {
        "item_shuffle": True,
        "pool_builder": True,
        "pool_builder_intensity": "max",
        "pool_builder_juice_cap": 0,     # auto -> only the reserve bounds the budget
        "pool_builder_juice_pct": 100,   # take the whole tail -> maximal over-provision pressure
        "boss_keys": True,               # adds ~two dozen Boss Key contributors the old reserve missed
    }

    def _counts(self):
        own = [it for it in world_pool_items(self) if it.player == self.world.player]
        locks = sum(1 for it in own if it.name.endswith(" Lock"))
        boss_keys = sum(1 for it in own if it.name.startswith("Boss Key:"))
        return own, locks, boss_keys

    def test_reserve_includes_boss_keys(self):
        _own, locks, boss_keys = self._counts()
        self.assertGreater(boss_keys, 0, "test is vacuous -- boss_keys produced no keys")
        reserved = PoolBuilderFeature()._reserved_slots(self.world)
        self.assertGreaterEqual(
            reserved, locks + boss_keys,
            f"reserve {reserved} must cover locks ({locks}) + boss keys ({boss_keys}); the old "
            f"len(kept)-only reserve undercounted and over-provisioned juice.")

    def test_juice_never_over_provisions_past_rune_tail(self):
        pb = PoolBuilderFeature()
        R = pb._rune_fallback_locations(self.world)
        reserved = pb._reserved_slots(self.world)
        juice = len(pb._juice_list(self.world))
        self.assertLessEqual(
            reserved + juice, R,
            f"reserve ({reserved}) + juice ({juice}) exceeds the Rune-fallback count ({R}) -- juice is "
            f"displacing real vanilla items past the Rune tail.")

    def test_count_neutral(self):
        own, _l, _b = self._counts()
        total = len(LOCATIONS.get(HUB, [])) + sum(len(LOCATIONS.get(r, [])) for r in self.world._kept())
        self.assertEqual(len(own), total, "pool must stay one item per location (count-neutral)")
