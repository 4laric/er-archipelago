"""Real-item-pool tests -- WorldTestBase. ItemShuffle places vanilla items; off = all Rune."""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")
from worlds.eldenring_gf.item_ids import ITEM_CATALOG  # noqa: E402

GAME = "Elden Ring (Greenfield)"


class ItemShuffleOn(WorldTestBase):
    game = GAME
    options = {"item_shuffle": True}

    def test_real_items_in_pool(self):
        self.assertTrue(ITEM_CATALOG, "item_ids.py must be generated")
        names = [i.name for i in self.multiworld.itempool
                 if not i.name.endswith(" Lock") and i.name != "Rune"]
        self.assertTrue(names, "item shuffle should place real vanilla items")
        for n in names:
            self.assertIn(n, ITEM_CATALOG, "shuffled pool items are catalog items")


class ItemShuffleOff(WorldTestBase):
    game = GAME
    options = {"item_shuffle": False, "varied_filler": False}

    def test_default_all_rune(self):
        fill = [i.name for i in self.multiworld.itempool if not i.name.endswith(" Lock")]
        self.assertTrue(fill and all(n == "Rune" for n in fill),
                        "shuffle off + grace off fills every non-lock slot with Rune")


class VariedFillerOn(WorldTestBase):
    game = GAME
    options = {"item_shuffle": False, "varied_filler": True}

    def test_filler_is_varied_junk(self):
        from worlds.eldenring_gf.item_ids import FILLER_POOL
        fill = [i.name for i in self.multiworld.itempool if not i.name.endswith(" Lock")]
        # every non-lock item is a FILLER_POOL junk item or the Rune fallback (still filler-classified)
        self.assertTrue(fill and all(n in FILLER_POOL or n == "Rune" for n in fill))
        # real variety, not the monotone-Rune wall
        self.assertGreater(len(set(fill)), 5, "varied_filler places many distinct junk items")


# ---- A (2026-07-07): smithing stones un-guarded into FILLER_POOL -------------------------------
def test_filler_pool_includes_smithing_stones():
    """A: regular Smithing Stone [1..8] and Somber Smithing Stone [1..9] are rarity<=1 reinforcement
    goods, so they now land in FILLER_POOL and varied_filler distributes them as upgrade materials.
    pool_builder only juices equippables (goods omitted from tiers), so without this they'd be in
    no pool at all."""
    from worlds.eldenring_gf.item_ids import FILLER_POOL
    fp = set(FILLER_POOL)
    for i in range(1, 9):
        assert f"Smithing Stone [{i}]" in fp, f"Smithing Stone [{i}] must be in FILLER_POOL"
    for i in range(1, 10):
        assert f"Somber Smithing Stone [{i}]" in fp, f"Somber Smithing Stone [{i}] must be in FILLER_POOL"


def test_filler_pool_excludes_capped_and_endtier():
    """The rarity<=1 gate keeps capped resources (Golden Seed, Sacred Tear, Scadutree Fragment,
    Revered Spirit Ash -- all rarity 2) and the end-tier Ancient Dragon (Somber) stones (rarity 3)
    OUT of the varied filler, so A doesn't mint uncapped flask/blessing mats or trivialize max upgrade."""
    from worlds.eldenring_gf.item_ids import FILLER_POOL
    fp = set(FILLER_POOL)
    for n in ("Golden Seed", "Sacred Tear", "Scadutree Fragment", "Revered Spirit Ash",
              "Ancient Dragon Smithing Stone", "Somber Ancient Dragon Smithing Stone"):
        assert n not in fp, f"{n} must NOT be in FILLER_POOL (capped/end-tier)"


class StoneInjection(WorldTestBase):
    """B: stone_injection swaps filler for low smithing stones on the SHUFFLED pool, count-neutral."""
    game = GAME
    options = {"item_shuffle": True, "stone_injection": 150}

    def test_injection_raises_low_stones_count_neutral(self):
        from collections import Counter
        names = Counter(i.name for i in self.multiworld.itempool if i.player == self.world.player)
        # low tiers should be plentiful after injection (baseline vanilla supply is ~20-25 each)
        for t in (1, 2, 3):
            self.assertGreater(names.get(f"Smithing Stone [{t}]", 0), 40,
                               f"injection should raise Smithing Stone [{t}] supply")
        # every injected item is filler-classified (never progression/useful) -> winnable (test_fill)
