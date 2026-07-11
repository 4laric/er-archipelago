"""Phase 7 progressive-items tests -- WorldTestBase.

Asserts the client contract (progressiveGrants shape + GOODS-packed positive good ids) and the pool
effect (N copies of each active progressive item, count-neutral) when a toggle is on, and that
progressiveGrants is empty {} when every toggle is off. Progressive copies are `useful`, never
progression, so the seed stays winnable in every case.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")
from worlds.eldenring_gf.features.progressive import (  # noqa: E402
    PROG_GOLDEN_SEED, PROG_SACRED_TEAR, PROG_STONESWORD_KEY,
    PROG_SMITHING_BELL, PROG_SOMBER_BELL,
    _GOODS_LADDERS, _POOL_COUNTS, _GOODS_NIBBLE, _BELL_GRANTS, _BELL_EARLY_COUNT,
)
from ._util import world_items, world_pool_items  # noqa: E402

GAME = "Elden Ring (Greenfield)"


def _assert_grant_shape(testcase, tiers):
    """A grant ladder must be a non-empty list of {"goods": GOODS-packed positive int, "flags": []}."""
    testcase.assertIsInstance(tiers, list)
    testcase.assertGreater(len(tiers), 0)
    for step in tiers:
        testcase.assertIsInstance(step, dict)
        testcase.assertIn("goods", step)
        testcase.assertIn("flags", step)
        goods = step["goods"]
        testcase.assertIsInstance(goods, int)
        testcase.assertNotIsInstance(goods, bool)
        testcase.assertGreater(goods, 0, "GOODS-packed FullID must be a positive int")
        testcase.assertEqual(goods & 0xF0000000, _GOODS_NIBBLE, "good must be GOODS-packed")
        testcase.assertIsInstance(step["flags"], list)


def _pool_names(world):
    return [it.name for it in world_pool_items(world) if it.player == world.player]


class ProgressiveOff(WorldTestBase):
    game = GAME  # both toggles default off

    def test_progressive_grants_empty_when_off(self):
        sd = self.world.fill_slot_data()
        self.assertIn("progressiveGrants", sd)
        self.assertEqual(sd["progressiveGrants"], {})

    def test_no_progressive_items_in_pool_when_off(self):
        names = set(_pool_names(self.world))
        for nm in (PROG_GOLDEN_SEED, PROG_SACRED_TEAR, PROG_STONESWORD_KEY):
            self.assertNotIn(nm, names)


class ProgressiveFlasksOn(WorldTestBase):
    game = GAME
    options = {"progressive_flasks": True}

    def test_flask_grants_shape_and_ladder(self):
        grants = self.world.fill_slot_data()["progressiveGrants"]
        for nm in (PROG_GOLDEN_SEED, PROG_SACRED_TEAR):
            self.assertIn(nm, grants)
            _assert_grant_shape(self, grants[nm])
            # ladder length matches the declared vanilla good ladder
            self.assertEqual(len(grants[nm]), len(_GOODS_LADDERS[nm]))
            expected_full = _GOODS_LADDERS[nm][0] | _GOODS_NIBBLE
            self.assertEqual(grants[nm][0]["goods"], expected_full)
        # stonesword key not active under this toggle
        self.assertNotIn(PROG_STONESWORD_KEY, grants)

    def test_flask_copies_in_pool(self):
        names = _pool_names(self.world)
        self.assertEqual(names.count(PROG_GOLDEN_SEED), _POOL_COUNTS[PROG_GOLDEN_SEED])
        self.assertEqual(names.count(PROG_SACRED_TEAR), _POOL_COUNTS[PROG_SACRED_TEAR])
        self.assertNotIn(PROG_STONESWORD_KEY, names)

    def test_pool_count_neutral(self):
        # count-exact: one pool item per real location (hub + kept regions).
        from worlds.eldenring_gf.data import HUB, LOCATIONS
        total = sum(len(LOCATIONS.get(r, [])) for r in [HUB] + list(self.world._kept()))
        self.assertEqual(len(_pool_names(self.world)), total)


class ProgressiveStoneswordKeysOn(WorldTestBase):
    game = GAME
    options = {"progressive_stonesword_keys": True}

    def test_key_grant_shape(self):
        grants = self.world.fill_slot_data()["progressiveGrants"]
        self.assertIn(PROG_STONESWORD_KEY, grants)
        _assert_grant_shape(self, grants[PROG_STONESWORD_KEY])
        self.assertEqual(len(grants[PROG_STONESWORD_KEY]), len(_GOODS_LADDERS[PROG_STONESWORD_KEY]))
        # flasks not active under this toggle
        self.assertNotIn(PROG_GOLDEN_SEED, grants)
        self.assertNotIn(PROG_SACRED_TEAR, grants)

    def test_key_copies_in_pool(self):
        names = _pool_names(self.world)
        self.assertEqual(names.count(PROG_STONESWORD_KEY), _POOL_COUNTS[PROG_STONESWORD_KEY])


class ProgressiveBothOn(WorldTestBase):
    game = GAME
    options = {"progressive_flasks": True, "progressive_stonesword_keys": True}

    def test_all_three_present(self):
        grants = self.world.fill_slot_data()["progressiveGrants"]
        for nm in (PROG_GOLDEN_SEED, PROG_SACRED_TEAR, PROG_STONESWORD_KEY):
            self.assertIn(nm, grants)
            _assert_grant_shape(self, grants[nm])
        names = _pool_names(self.world)
        for nm in (PROG_GOLDEN_SEED, PROG_SACRED_TEAR, PROG_STONESWORD_KEY):
            self.assertEqual(names.count(nm), _POOL_COUNTS[nm])


class ProgressiveStoneBellsOn(WorldTestBase):
    game = GAME
    options = {"progressive_stone_bells": True}

    def test_bell_grant_shape_and_flags(self):
        grants = self.world.fill_slot_data()["progressiveGrants"]
        for nm in (PROG_SMITHING_BELL, PROG_SOMBER_BELL):
            self.assertIn(nm, grants)
            _assert_grant_shape(self, grants[nm])
            # ladder length matches the declared tier grant table
            self.assertEqual(len(grants[nm]), len(_BELL_GRANTS[nm]))
            # unlike flasks/keys, stone bells MUST carry non-empty shop-unlock flags per rung
            for step in grants[nm]:
                self.assertTrue(step["flags"], f"{nm} rung missing shop-unlock flags")
            # first Smithing rung grants the [1] bell good (8951) GOODS-packed
            self.assertEqual(grants[PROG_SMITHING_BELL][0]["goods"], 8951 | _GOODS_NIBBLE)
        # flasks / keys not active under this toggle
        for nm in (PROG_GOLDEN_SEED, PROG_SACRED_TEAR, PROG_STONESWORD_KEY):
            self.assertNotIn(nm, grants)

    def test_bell_copies_in_pool(self):
        names = _pool_names(self.world)
        self.assertEqual(names.count(PROG_SMITHING_BELL), _POOL_COUNTS[PROG_SMITHING_BELL])
        self.assertEqual(names.count(PROG_SOMBER_BELL), _POOL_COUNTS[PROG_SOMBER_BELL])

    def test_bells_forced_early(self):
        # generate_early must have registered the sphere-0 early_items for each active bell.
        early = self.world.multiworld.early_items[self.world.player]
        for nm, n in _BELL_EARLY_COUNT.items():
            self.assertGreaterEqual(early.get(nm, 0), n, f"{nm} not forced into sphere 0")

    def test_pool_count_neutral(self):
        from worlds.eldenring_gf.data import HUB, LOCATIONS
        total = sum(len(LOCATIONS.get(r, [])) for r in [HUB] + list(self.world._kept()))
        self.assertEqual(len(_pool_names(self.world)), total)
