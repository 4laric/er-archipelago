"""pool_builder_intensity -- the juice rarity floor, and proof that it is WIRED.

Rewritten 2026-07-28. The previous file tested the retired private juice budget (juice_pct, the
per-feature cap, `_juice_list`) and was deleted with it. What survives here is the part that is
still true -- the catalog is a monotone ladder -- plus the test that was missing and that this
whole change exists to justify: that turning the knob actually changes what the generator composes.

🛑 THE KNOB WAS INERT FOR WEEKS AND EVERY TEST PASSED. It was frozen in FROZEN_OPTIONS and read
through the constant JUICE_FLOOR, so `plan()` could not see it. Nothing failed, because nothing
asserted the option reached the composer -- the old tests read `juice_order_for_floor(...)` directly,
which works identically whether or not the world's option is connected to anything. A test that
calls the helper the option feeds is not a test that the option feeds the helper.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring.features.pool_builder import (  # noqa: E402
    juice_order_for_floor, INTENSITY_FLOOR, PoolBuilderIntensity,
)

GAME = "Elden Ring"


# ---- pure-data guards (no world) -------------------------------------------------------------
def test_intensity_floor_ladder_is_monotonic():
    assert INTENSITY_FLOOR["normal"] > INTENSITY_FLOOR["high"] > INTENSITY_FLOOR["max"]


def test_a_higher_floor_is_a_strictly_smaller_catalog():
    """The trade the option's name implies backwards: a HIGHER floor yields LESS gear, not better."""
    normal = set(juice_order_for_floor(INTENSITY_FLOOR["normal"]))
    high = set(juice_order_for_floor(INTENSITY_FLOOR["high"]))
    mx = set(juice_order_for_floor(INTENSITY_FLOOR["max"]))
    assert normal < high < mx, "each level must be a STRICT superset of the one above it"
    assert len(normal) > 0, "the strictest floor must still leave a usable catalog"


def test_juice_order_is_best_first():
    """Order is load-bearing: a truncated budget takes a PREFIX, so prefix == the best items."""
    from worlds.eldenring.item_tiers import ITEM_TIERS
    order = juice_order_for_floor(INTENSITY_FLOOR["max"])
    ranks = [ITEM_TIERS[n] for n in order if n in ITEM_TIERS]
    # Tiers are S=3 A=2 B=1 (HIGHER is better), so best-first is DESCENDING. Asserting ascending
    # here failed loudly, which is the only reason this comment exists rather than a silent pass.
    assert ranks == sorted(ranks, reverse=True), "juice_order_for_floor must be best-first"


def test_the_default_is_max_which_is_what_the_frozen_option_shipped():
    """🛑 REGRESSION PIN. While frozen, defaults.FROZEN_OPTIONS pinned this at "max" and the class
    default underneath (`high`) was unreachable. Unfreezing it without moving the class default
    would silently revert every default seed to the smaller catalog -- a behaviour change inside a
    release that claims not to have one. The yaml, the guide and the CHANGELOG all say max."""
    assert PoolBuilderIntensity.default == PoolBuilderIntensity.option_max


# ---- the wiring test: the option must reach the composer ---------------------------------------
def _juice_names(world):
    from worlds.eldenring.features.filler_budget import plan, budget_slots
    from worlds.eldenring.item_tiers import ITEM_TIER_CATEGORY
    return [n for n in plan(world, budget_slots(world)) if n and n in ITEM_TIER_CATEGORY]


class IntensityNormalIsWired(WorldTestBase):
    game = GAME
    options = {"item_shuffle": True, "pool_builder_intensity": "normal"}

    def test_the_strictest_floor_reaches_the_composer(self):
        names = set(_juice_names(self.world))
        allowed = set(juice_order_for_floor(INTENSITY_FLOOR["normal"]))
        self.assertTrue(names, "normal must still compose SOME gear")
        self.assertTrue(
            names <= allowed,
            "plan() composed gear that is not in the normal catalog -- the option is not reaching "
            "filler_budget.juice_floor. This is the exact inert-knob failure the file documents: "
            "off-catalog names here mean the composer is still using a constant.")

    def test_it_reports_its_own_floor(self):
        self.assertEqual(self.world.fill_slot_data()["pool_builder_intensity_floor"],
                         INTENSITY_FLOOR["normal"])


class IntensityMaxIsWider(WorldTestBase):
    game = GAME
    options = {"item_shuffle": True, "pool_builder_intensity": "max"}

    def test_max_composes_from_the_wide_catalog(self):
        """Verified by DIFFERENCE, not by an absolute count: same seed, same everything but the
        floor. If both intensities composed the same set the knob would be decorative."""
        names = set(_juice_names(self.world))
        narrow = set(juice_order_for_floor(INTENSITY_FLOOR["normal"]))
        self.assertTrue(names, "max must compose gear")
        self.assertTrue(
            names - narrow,
            "max composed nothing outside the `normal` catalog. Either the option is not wired or "
            "the budget is too small to reach past the top items -- both make the knob a no-op.")
