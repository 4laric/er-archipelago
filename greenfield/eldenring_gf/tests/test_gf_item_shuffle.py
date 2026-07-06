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
    options = {"item_shuffle": False, "grace_rando": False}

    def test_default_all_rune(self):
        fill = [i.name for i in self.multiworld.itempool if not i.name.endswith(" Lock")]
        self.assertTrue(fill and all(n == "Rune" for n in fill),
                        "shuffle off + grace off fills every non-lock slot with Rune")
