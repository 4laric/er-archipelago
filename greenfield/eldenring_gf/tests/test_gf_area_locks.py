"""area_locks -- sealed regions must get a permanent-kick areaLockFlags range (dead-drop fix).

A sealed (non-kept) region has no Lock and its open flag is never received, so its range stays locked
forever -> the client's kick-watch ejects the player. Without a range the client treats the region as
OPEN, letting you wander into a sealed sub-area (e.g. Ruin-Strewn Precipice under a sealed Mt. Gelmir)
and hit dead drops (vanilla suppressed, no active check to grant)."""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")
from worlds.eldenring_gf.region_open_flags import REGION_OPEN_FLAGS  # noqa: E402
from worlds.eldenring_gf.features.area_locks import REGION_PLAY_IDS  # noqa: E402

GAME = "Elden Ring (Greenfield)"


class AreaLocksSealed(WorldTestBase):
    game = GAME
    options = {"item_shuffle": True, "num_regions": 4, "num_regions_order": "rolled"}

    def test_sealed_and_kept_both_get_ranges(self):
        alf = self.world.fill_slot_data().get("areaLockFlags", [])
        self.assertTrue(alf, "areaLockFlags must be emitted (kick-watch on)")
        kept = set(self.world._kept())
        covered = {r[0] for r in alf}  # lo == hi play_region ids with a range
        # EVERY region with geometry + an open flag gets ranges for all its play_regions (kept OR sealed).
        for region, ids in REGION_PLAY_IDS.items():
            if REGION_OPEN_FLAGS.get(region) is None:
                continue
            for pid in ids:
                self.assertIn(pid, covered,
                              f"{region} play_region {pid} must have a kick range (sealed or kept)")
        # kept ranges reference the region's real open flag (unlocks on Lock receipt).
        for kr in kept:
            f = REGION_OPEN_FLAGS.get(kr)
            if f is not None:
                self.assertTrue(any(r[2] == f for r in alf), f"kept {kr} range keyed to open flag {f}")
        # at least one sealed region present (num_regions 4 seals most) -> permanent-kick ranges exist.
        sealed_flags = {REGION_OPEN_FLAGS[r] for r in REGION_OPEN_FLAGS if r not in kept}
        self.assertTrue(any(r[2] in sealed_flags for r in alf),
                        "sealed regions must get permanent-kick ranges (the dead-drop fix)")
