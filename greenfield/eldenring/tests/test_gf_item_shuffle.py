"""Real-item-pool tests -- WorldTestBase. ItemShuffle places vanilla items; off = all Rune."""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring.item_ids import ITEM_CATALOG  # noqa: E402

GAME = "Elden Ring"


class ItemShuffleOn(WorldTestBase):
    game = GAME
    options = {"item_shuffle": True}

    def test_real_items_in_pool(self):
        # Feature-registered items are NOT vanilla catalog items and legitimately ride the shuffled
        # pool: progressive_flasks substitutes every Golden Seed / Sacred Tear check for a single
        # "Progressive Flask Upgrade" (features/progressive.py), which is how the ladder stays
        # count-exact. Excluded by NAME from the feature module, so this list cannot silently rot.
        from worlds.eldenring.features.progressive import PROG_FLASK

        self.assertTrue(ITEM_CATALOG, "item_ids.py must be generated")
        _not_vanilla = {"Rune", PROG_FLASK}
        names = [i.name for i in self.multiworld.itempool
                 if not i.name.endswith(" Lock") and i.name not in _not_vanilla]
        self.assertTrue(names, "item shuffle should place real vanilla items")
        for n in names:
            self.assertIn(n, ITEM_CATALOG, "shuffled pool items are catalog items")


# ---- A (2026-07-07): smithing stones un-guarded into FILLER_POOL -------------------------------
def test_filler_pool_includes_smithing_stones():
    """A: regular Smithing Stone [1..8] and Somber Smithing Stone [1..9] are rarity<=1 reinforcement
    goods, so they now land in FILLER_POOL and varied_filler distributes them as upgrade materials.
    pool_builder only juices equippables (goods omitted from tiers), so without this they'd be in
    no pool at all."""
    from worlds.eldenring.item_ids import FILLER_POOL
    fp = set(FILLER_POOL)
    for i in range(1, 9):
        assert f"Smithing Stone [{i}]" in fp, f"Smithing Stone [{i}] must be in FILLER_POOL"
    for i in range(1, 10):
        assert f"Somber Smithing Stone [{i}]" in fp, f"Somber Smithing Stone [{i}] must be in FILLER_POOL"


def test_filler_pool_excludes_capped_and_endtier():
    """The rarity<=1 gate keeps capped resources (Golden Seed, Sacred Tear, Scadutree Fragment,
    Revered Spirit Ash -- all rarity 2) and the end-tier Ancient Dragon (Somber) stones (rarity 3)
    OUT of the varied filler, so A doesn't mint uncapped flask/blessing mats or trivialize max upgrade."""
    from worlds.eldenring.item_ids import FILLER_POOL
    fp = set(FILLER_POOL)
    for n in ("Golden Seed", "Sacred Tear", "Scadutree Fragment", "Revered Spirit Ash",
              "Ancient Dragon Smithing Stone", "Somber Ancient Dragon Smithing Stone"):
        assert n not in fp, f"{n} must NOT be in FILLER_POOL (capped/end-tier)"


