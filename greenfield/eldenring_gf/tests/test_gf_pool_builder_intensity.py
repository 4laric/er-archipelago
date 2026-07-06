"""pool_builder_intensity + filler_foreign_pct tests.

Two knobs added on top of Pool Builder:

  * pool_builder_intensity (Choice normal/high/max) sets the juice rarity FLOOR
    (normal=3 legendary-only, high=2 rare+legendary [DEFAULT = historical], max=1
    also common). A higher intensity WIDENS the juice candidate set (max >= high >=
    normal by count) but stays count-neutral in the pool. Default 'high' == the old
    fixed floor, so existing seeds are unchanged.
  * filler_foreign_pct (Range 0-100, default 100) forces (100 - pct)% of this slot's
    distinct filler item names into local_items. Default 100 -> 0% localized -> NO
    CHANGE (greenfield stays fully open). Lower keeps more filler home; 0 = all local.

Pure-data guards (juice-floor monotonicity, no-change default) plus WorldTestBase
integration (the base test_fill proves every subclass is still beatable).
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")
from worlds.eldenring_gf.features.pool_builder import (  # noqa: E402
    juice_order_for_floor, INTENSITY_FLOOR, DEFAULT_INTENSITY, JUICE_ORDER, JUICE_MIN_RARITY,
)
from worlds.eldenring_gf.features.filler_foreign import (  # noqa: E402
    FillerForeignFeature, FillerForeignPct, filler_names, FILLER_NAME, NO_CHANGE_PCT,
)

GAME = "Elden Ring (Greenfield)"


# ---- pure-data guards (no world) -------------------------------------------------------------
def test_intensity_floor_monotonic():
    """max floor (1) is the widest, normal (3) the narrowest -> max >= high >= normal by count."""
    n_normal = len(juice_order_for_floor(INTENSITY_FLOOR["normal"]))
    n_high = len(juice_order_for_floor(INTENSITY_FLOOR["high"]))
    n_max = len(juice_order_for_floor(INTENSITY_FLOOR["max"]))
    assert n_max >= n_high >= n_normal, (n_normal, n_high, n_max)
    # strictly wider in a real catalog (there ARE common + legendary items).
    assert n_max > n_normal, "max intensity must widen the juice set over normal"


def test_intensity_default_is_historical():
    """Default intensity 'high' == the old fixed floor, so JUICE_ORDER == the high-floor list."""
    assert DEFAULT_INTENSITY == "high"
    assert INTENSITY_FLOOR[DEFAULT_INTENSITY] == JUICE_MIN_RARITY == 2
    assert JUICE_ORDER == juice_order_for_floor(INTENSITY_FLOOR[DEFAULT_INTENSITY])


def test_higher_floor_is_subset():
    """A higher floor list is a strict subset of a lower one (rarity is a threshold)."""
    lo = set(juice_order_for_floor(1))
    mid = set(juice_order_for_floor(2))
    hi = set(juice_order_for_floor(3))
    assert hi <= mid <= lo


def test_juice_order_best_first():
    order = juice_order_for_floor(INTENSITY_FLOOR["max"])
    from worlds.eldenring_gf.features.pool_builder import ITEM_TIERS
    rarities = [ITEM_TIERS[n] for n in order]
    assert rarities == sorted(rarities, reverse=True), "juice ordered best-first (legendary first)"


def test_filler_foreign_default_is_no_change():
    """Default pct == NO_CHANGE_PCT (100): fully open, nothing localized -> greenfield unchanged."""
    assert FillerForeignPct.default == NO_CHANGE_PCT == 100
    assert FillerForeignPct.range_start == 0 and FillerForeignPct.range_end == 100


def test_filler_names_always_include_rune():
    class _Stub:
        class options:
            item_shuffle = type("O", (), {"value": False})()
    names = filler_names(_Stub)
    assert names == [FILLER_NAME], "shuffle off -> only the generic Rune filler exists"


# ---- WorldTestBase integration ---------------------------------------------------------------
class _IntensityBase(WorldTestBase):
    game = GAME

    def _juice_candidates(self):
        feat_floor = self.world.options.pool_builder_intensity.current_key
        return len(juice_order_for_floor(INTENSITY_FLOOR[feat_floor]))


class IntensityMax(_IntensityBase):
    options = {"item_shuffle": True, "pool_builder": True, "pool_builder_intensity": "max",
               "grace_rando": False}

    def test_max_widens_candidates_and_reports_floor(self):
        self.assertEqual(self.world.options.pool_builder_intensity.current_key, "max")
        sd = self.world.fill_slot_data()
        self.assertEqual(sd["pool_builder_intensity_floor"], INTENSITY_FLOOR["max"])
        # max candidate set >= high candidate set
        self.assertGreaterEqual(sd["pool_builder_juice_candidates"],
                                len(juice_order_for_floor(INTENSITY_FLOOR["high"])))
        self.assertGreater(sd["pool_builder_juice_added"], 0)


class IntensityNormal(_IntensityBase):
    options = {"item_shuffle": True, "pool_builder": True, "pool_builder_intensity": "normal",
               "grace_rando": False}

    def test_normal_narrows_candidates(self):
        sd = self.world.fill_slot_data()
        self.assertEqual(sd["pool_builder_intensity_floor"], INTENSITY_FLOOR["normal"])
        self.assertLessEqual(sd["pool_builder_juice_candidates"],
                             len(juice_order_for_floor(INTENSITY_FLOOR["high"])))


class FillerForeignDefault(WorldTestBase):
    game = GAME
    options = {"item_shuffle": True, "grace_rando": False}

    def test_default_localizes_nothing(self):
        feat = FillerForeignFeature()
        self.assertEqual(feat.names_to_localize(self.world), [],
                         "default filler_foreign_pct (100) localizes nothing (no change)")


class FillerForeignAllLocal(WorldTestBase):
    game = GAME
    options = {"item_shuffle": True, "grace_rando": False, "filler_foreign_pct": 0}

    def test_zero_pct_localizes_all_filler_names(self):
        feat = FillerForeignFeature()
        localized = set(feat.names_to_localize(self.world))
        self.assertEqual(localized, set(filler_names(self.world)),
                         "pct 0 forces every distinct filler name local")
        self.assertIn(FILLER_NAME, localized)
        # and the feature actually added them to local_items in generate_early.
        self.assertTrue(set(filler_names(self.world)).issubset(self.world.options.local_items.value))


class FillerForeignHalf(WorldTestBase):
    game = GAME
    options = {"item_shuffle": True, "grace_rando": False, "filler_foreign_pct": 50}

    def test_half_localizes_partial(self):
        feat = FillerForeignFeature()
        names = filler_names(self.world)
        localized = feat.names_to_localize(self.world)
        expected_k = (len(names) * 50) // 100
        # (100 - pct)% = 50% of the distinct filler names, floor-rounded, kept home.
        self.assertEqual(len(localized), expected_k)
        # every localized name is a real filler name; the sample is drawn from world.random
        # (seeded) -> deterministic per seed at generate_early time.
        self.assertTrue(set(localized).issubset(set(names)))
        self.assertGreater(expected_k, 0, "half of the filler names is a non-empty partial set")
