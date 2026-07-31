"""Pool Builder per-category juice percents -- WorldTestBase.

Verifies the per-category percent knobs (pool_builder_pct_weapons / _armor / _spells / _talismans /
_ashes_of_war): while every per-category percent is 0 the feature is unchanged (global Juice Percent,
best-first across all categories); setting a single category to 100 fills the tail with ONLY that
category's gear; and mixing two categories injects both (and nothing else). Uses the generated
ITEM_TIER_CATEGORY map to classify what actually got injected.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring.item_tiers import ITEM_TIER_CATEGORY  # noqa: E402

GAME = "Elden Ring"

# `pool_builder` and `pool_builder_juice_cap` retired 2026-07-28 (Options.Removed): naming
# either one here would raise. max floor = S/A/B = the widest per-category room.
_BASE = {"item_shuffle": True, "pool_builder_intensity": "max"}


def _injected_categories(world):
    """category -> count, for the gear this world's filler recipe actually places.

    Re-pointed 2026-07-28 from `PoolBuilderFeature._juice_list` to `filler_budget.plan`. The private
    juice list was deleted with the rest of the retired budget machine; the per-category percents are
    still live and are now read inside `plan()` (via CATEGORY_OPTION), so this asks the code that
    really decides. Reading the composed itempool instead would NOT work: with item_shuffle on the
    pool already holds every vanilla weapon and robe, so "gear in the pool" is not "gear injected".
    """
    from worlds.eldenring.features.filler_budget import plan, budget_slots
    names = [n for n in plan(world, budget_slots(world)) if n and n in ITEM_TIER_CATEGORY]
    out = {}
    for n in names:
        out[ITEM_TIER_CATEGORY[n]] = out.get(ITEM_TIER_CATEGORY[n], 0) + 1
    return out, len(names)


class WeaponsOnly(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, **_BASE, "pool_builder_pct_weapons": 100}

    def test_only_weapons_injected(self):
        cats, total = _injected_categories(self.world)
        self.assertGreater(total, 0, "weapons-only should still inject a non-empty juice set")
        self.assertEqual(set(cats), {"WEAPON"},
                         f"pct_weapons=100 (others 0) must inject ONLY weapons, got {cats}")


class SpellsAndTalismans(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, **_BASE, "pool_builder_pct_spells": 50, "pool_builder_pct_talismans": 50}

    def test_only_the_two_set_categories(self):
        cats, total = _injected_categories(self.world)
        self.assertGreater(total, 0)
        self.assertTrue(set(cats).issubset({"SPELL", "TALISMAN"}),
                        f"only spells+talismans were weighted, got {cats}")
        self.assertIn("SPELL", cats, "spells were weighted -> expected some spell juice")
        self.assertIn("TALISMAN", cats, "talismans were weighted -> expected some talisman juice")


class DefaultIsGlobal(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, **_BASE}  # no per-category percents -> global mode (multiple categories)

    def test_global_mode_spans_categories(self):
        cats, total = _injected_categories(self.world)
        self.assertGreater(total, 0)
        self.assertGreater(len(cats), 1,
                           f"global mode (no per-category %) should span multiple categories, got {cats}")
