"""Real-item-pool tests -- WorldTestBase. ItemShuffle places vanilla items; off = all Rune."""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")
from worlds.eldenring_gf.item_ids import ITEM_CATALOG  # noqa: E402

GAME = "Elden Ring (Greenfield)"


class ItemShuffleOn(WorldTestBase):
    game = GAME
    options = {"item_shuffle": True, "grace_rando": False}

    def test_real_items_in_pool(self):
        self.assertTrue(ITEM_CATALOG, "item_ids.py must be generated")
        names = [i.name for i in self.multiworld.itempool
                 if not i.name.endswith(" Lock") and i.name != "Rune"]
        self.assertTrue(names, "item shuffle should place real vanilla items")
        for n in names:
            self.assertIn(n, ITEM_CATALOG, "shuffled pool items are catalog items")


class ItemShuffleOff(WorldTestBase):
    game = GAME
    options = {"item_shuffle": False, "grace_rando": False, "varied_filler": False}

    def test_default_all_rune(self):
        fill = [i.name for i in self.multiworld.itempool if not i.name.endswith(" Lock")]
        self.assertTrue(fill and all(n == "Rune" for n in fill),
                        "shuffle off + grace off fills every non-lock slot with Rune")


class VariedFillerOn(WorldTestBase):
    game = GAME
    options = {"item_shuffle": False, "grace_rando": False, "varied_filler": True}

    def test_filler_is_varied_junk(self):
        from worlds.eldenring_gf.item_ids import FILLER_POOL
        fill = [i.name for i in self.multiworld.itempool if not i.name.endswith(" Lock")]
        # every non-lock item is a FILLER_POOL junk item or the Rune fallback (still filler-classified)
        self.assertTrue(fill and all(n in FILLER_POOL or n == "Rune" for n in fill))
        # real variety, not the monotone-Rune wall
        self.assertGreater(len(set(fill)), 5, "varied_filler places many distinct junk items")
