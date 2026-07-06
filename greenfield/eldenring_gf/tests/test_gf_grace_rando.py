"""Phase 6 grace-rando tests -- WorldTestBase. Freebie (one grace + scatter items), bundle (all)."""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")
from worlds.eldenring_gf.region_graces import REGION_GRACE_POINTS  # noqa: E402

GAME = "Elden Ring (Greenfield)"


class GraceFreebieScatter(WorldTestBase):
    game = GAME
    options = {"grace_rando": True}

    def test_freebie_one_grace_and_scatter_items(self):
        sd = self.world.fill_slot_data()
        rg, gi = sd["regionGraces"], sd["graceItems"]
        kept = set(self.world._kept())
        for lock, flags in rg.items():
            self.assertTrue(lock.endswith(" Lock"))
            self.assertIn(lock[:-len(" Lock")], kept)
            self.assertEqual(len(flags), 1, "freebie lights exactly one grace")
            self.assertEqual(flags[0], REGION_GRACE_POINTS[lock[:-len(" Lock")]][0])
        # graceItems = {name: flag}, all positive, names present in the item pool
        pool = {i.name for i in self.multiworld.itempool}
        for name, flag in gi.items():
            self.assertTrue(name.startswith("Grace: "))
            self.assertIsInstance(flag, int)
            self.assertGreater(flag, 0)
            self.assertIn(name, pool, "each scattered grace must be an item in the pool")


class GraceBundle(WorldTestBase):
    game = GAME
    options = {"grace_rando": False}

    def test_bundle_all_graces_no_scatter(self):
        sd = self.world.fill_slot_data()
        self.assertEqual(sd["graceItems"], {}, "bundle mode has no scatter items")
        kept = set(self.world._kept())
        saw_multi = False
        for lock, flags in sd["regionGraces"].items():
            region = lock[:-len(" Lock")]
            self.assertEqual(list(flags), list(REGION_GRACE_POINTS[region]))
            if len(flags) > 1:
                saw_multi = True
        self.assertTrue(saw_multi)
