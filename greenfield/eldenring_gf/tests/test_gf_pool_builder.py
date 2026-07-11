"""Phase 5 pool-builder tests -- WorldTestBase.

Pool Builder curates the shuffled vanilla pool: it replaces the Rune fallback tail with high-tier
juice (rare + legendary equippables), count-neutral, and no-ops when item_shuffle is off. Tiers are
param-derived (item_tiers.py, matt-free). The base WorldTestBase suite (test_fill) already proves the
seed is beatable in every subclass below, so winnability is covered for free.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")
from worlds.eldenring_gf.data import REGIONS, LOCATIONS  # noqa: E402
from ._util import world_items, world_pool_items  # noqa: E402
from worlds.eldenring_gf.item_ids import ITEM_CATALOG  # noqa: E402
from BaseClasses import ItemClassification  # noqa: E402
from worlds.eldenring_gf.features.pool_builder import (  # noqa: E402
    PoolBuilderFeature, ITEM_TIERS, JUICE_ORDER, JUICE_MIN_RARITY,
)

GAME = "Elden Ring (Greenfield)"
_JUICE = set(JUICE_ORDER)
_TOTAL = sum(len(v) for v in LOCATIONS.values())   # full seed (num_regions default 0 = all regions)


class PoolBuilderData:
    """Pure-data guards (no world needed) -- run as a plain unittest via WorldTestBase subclass."""

    def _check_tiers(self):
        assert ITEM_TIERS, "item_tiers.py must be generated (gen_data.py Phase 5 block)"
        assert JUICE_ORDER, "there must be high-tier juice available"
        for n in JUICE_ORDER:
            assert n in ITEM_CATALOG, "every juice item is a real-item-pool catalog item"
            assert ITEM_TIERS[n] >= JUICE_MIN_RARITY
        # best-first ordering: legendary before rare
        rarities = [ITEM_TIERS[n] for n in JUICE_ORDER]
        assert rarities == sorted(rarities, reverse=True), "juice ordered best-first"


class PoolBuilderOn(WorldTestBase, PoolBuilderData):
    game = GAME
    options = {"item_shuffle": True, "pool_builder": True}

    def test_tier_data(self):
        self._check_tiers()

    def test_count_neutral(self):
        # curation never changes the pool size -- it swaps items, one-for-one.
        own = world_pool_items(self)   # itempool + pre-placed location-payers (progression_surface)
        self.assertEqual(len(own), _TOTAL,
                         "pool builder is count-neutral (pool == number of locations)")

    def test_adds_high_tier_juice(self):
        feat = PoolBuilderFeature()
        budget = feat._juice_budget(self.world)
        self.assertGreater(budget, 0, "pool builder should have juice to add for a full seed")
        juice_in_pool = sum(1 for i in self.multiworld.itempool if i.name in _JUICE)
        # the pool holds at least the added juice (plus any that landed naturally at its location).
        self.assertGreaterEqual(juice_in_pool, budget,
                                "pool builder must add its juice budget to the pool")

    def test_juice_is_never_progression(self):
        for i in self.multiworld.itempool:
            if i.name in _JUICE:
                self.assertFalse(i.classification & ItemClassification.progression,
                                 "juice is useful/filler, never progression (locks stay the goal)")

    def test_slot_data_reports_enabled(self):
        sd = self.world.fill_slot_data()
        self.assertTrue(sd["pool_builder"])
        self.assertGreater(sd["pool_builder_juice_added"], 0)


class PoolBuilderOff(WorldTestBase):
    """Same shuffle knobs, builder OFF -- the ON world above must carry strictly more juice."""
    game = GAME
    options = {"item_shuffle": True, "pool_builder": False}

    def test_off_has_less_juice_than_on(self):
        off_juice = sum(1 for i in self.multiworld.itempool if i.name in _JUICE)

        class _On(WorldTestBase):
            game = GAME
            options = {"item_shuffle": True, "pool_builder": True}

        on = _On()
        on.setUp()
        on_juice = sum(1 for i in on.multiworld.itempool if i.name in _JUICE)
        self.assertGreater(on_juice, off_juice, "pool builder ON adds juice vs OFF")


class PoolBuilderNoOpWhenShuffleOff(WorldTestBase):
    game = GAME
    options = {"item_shuffle": False, "pool_builder": True, "varied_filler": False}

    def test_no_op_all_rune(self):
        fill = [i.name for i in self.multiworld.itempool if not i.name.endswith(" Lock")]
        self.assertTrue(fill and all(n == "Rune" for n in fill),
                        "pool builder is a no-op when item_shuffle is off (every slot stays Rune)")
        self.assertFalse([n for n in fill if n in _JUICE], "no juice added when shuffle off")

    def test_slot_data_reports_disabled(self):
        sd = self.world.fill_slot_data()
        self.assertFalse(sd["pool_builder"])
        self.assertEqual(sd["pool_builder_juice_added"], 0)
