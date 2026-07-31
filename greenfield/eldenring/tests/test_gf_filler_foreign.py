"""filler_foreign_pct -- how much of this slot's filler is forced to stay home.

RESCUED 2026-07-28. These tests lived in `test_gf_pool_builder_intensity.py`, which was deleted
along with the retired pool-builder budget machine. They have nothing to do with that machine:
`filler_foreign_pct` is a live option, `features/filler_foreign.py` is live, and
`filler_foreign_localized` is a contract key -- deleting the file would have left all of it with
zero behavioural coverage, silently.

🛑 The lesson is about the unit of deletion. Retiring a mechanism justifies deleting the tests OF
that mechanism, not every test that happened to share a file with them. A test file is a filing
decision; coverage is not. Before deleting a test file, read every case in it and say which feature
each one actually guards.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring.features.filler_foreign import (  # noqa: E402
    FillerForeignFeature, FillerForeignPct, filler_names, FILLER_NAME, NO_CHANGE_PCT,
)

GAME = "Elden Ring"


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


class FillerForeignDefault(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "item_shuffle": True}

    def test_default_localizes_nothing(self):
        feat = FillerForeignFeature()
        self.assertEqual(feat.names_to_localize(self.world), [],
                         "default filler_foreign_pct (100) localizes nothing (no change)")


class FillerForeignAllLocal(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "item_shuffle": True, "filler_foreign_pct": 0}

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
    options = {"num_regions": 0, "item_shuffle": True, "filler_foreign_pct": 50}

    def test_half_localizes_partial(self):
        feat = FillerForeignFeature()
        names = filler_names(self.world)
        localized = feat.names_to_localize(self.world)
        expected_k = (len(names) * 50) // 100
        # (100 - pct)% = 50% of the distinct filler names, floor-rounded, kept home.
        self.assertEqual(len(localized), expected_k)
        self.assertTrue(set(localized).issubset(set(names)))
        self.assertGreater(expected_k, 0, "half of the filler names is a non-empty partial set")
