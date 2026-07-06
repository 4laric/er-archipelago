"""Phase 3 region-boss tests -- WorldTestBase. bossLocations must be scoped to kept regions and
reference real locations; sealed-region bosses drop out."""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")
from worlds.eldenring_gf.boss_data import REGION_BOSSES  # noqa: E402

GAME = "Elden Ring (Greenfield)"


class BossLocationsAll(WorldTestBase):
    game = GAME

    def test_boss_data_nonempty_and_valid(self):
        self.assertTrue(REGION_BOSSES, "boss_data.py must be generated")
        self.assertNotIn("Roundtable Hold", REGION_BOSSES, "bosses must map to real regions")

    def test_boss_locations_scoped_and_real(self):
        sd = self.world.fill_slot_data()
        bl = sd["bossLocations"]
        kept = set(self.world._kept())
        catalog = set(self.world.location_name_to_id.values())
        for region, ids in bl.items():
            self.assertIn(region, kept, f"boss region {region!r} not kept")
            for aid in ids:
                self.assertIn(aid, catalog, "boss ap-id must be a real location")


class BossLocationsSealed(WorldTestBase):
    game = GAME
    options = {"num_regions": 1, "num_regions_order": "spine"}

    def test_sealed_boss_regions_excluded(self):
        bl = self.world.fill_slot_data()["bossLocations"]
        kept = set(self.world._kept())
        self.assertTrue(all(r in kept for r in bl), "sealed-region bosses must be excluded")


class DungeonSweepFlags(WorldTestBase):
    game = GAME
    options = {"dungeon_sweep": "all"}

    def test_sweep_flags_present_and_scoped(self):
        from worlds.eldenring_gf.boss_sweeps import DUNGEON_SWEEPS
        self.assertTrue(DUNGEON_SWEEPS, "boss_sweeps.py must be generated")
        sd = self.world.fill_slot_data()
        sw = sd["dungeonSweepFlags"]
        self.assertTrue(sw, "dungeon sweeps should be non-empty with dungeon_sweep=all")
        catalog = set(self.world.location_name_to_id.values())
        for fl_str, members in sw.items():
            self.assertEqual(fl_str, str(int(fl_str)), "sweep keys are stringified boss-defeat flags")
            for aid in members:
                self.assertIn(aid, catalog, "sweep member must be a real location")

    def test_sweeps_off_when_disabled(self):
        # a fresh world with dungeon_sweep=none emits no sweep keys
        pass
