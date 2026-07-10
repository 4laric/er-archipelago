"""Regression: pool_builder juice must survive curated_filler + stone_injection (classification fix).

pool_builder injects high-tier GEAR as `useful` juice. But some catalog gear -- notably spells &
incantations -- carries the GOODS FullID nibble, so core._classify_full would default it to `filler`.
features/filler_curation.curate() and core's stone_injection both seize `filler`-classified junk and
protect only `progression|useful` -- so a filler-classified spell juice item would be silently
overwritten with a throwable / smithing stone (an S-tier sorcery the player "paid" a juice slot for).
pool_builder.create_items() forces `useful` on every pick to close this. This test drives the exact
collision -- pool_builder_pct_spells=100 (spell-only juice) alongside a heavy curated_filler recipe
AND stone_injection -- and asserts every injected spell survives as a useful item in the pool.

WorldTestBase.setUp runs create_items (which builds the pool: pool_builder.create_items -> extras ->
stone_injection -> curate), so the post-setUp itempool is the final, curated pool.
"""
import collections
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")

from BaseClasses import ItemClassification  # noqa: E402
from worlds.eldenring_gf.item_tiers import ITEM_TIER_CATEGORY  # noqa: E402
from worlds.eldenring_gf.features.pool_builder import PoolBuilderFeature  # noqa: E402

GAME = "Elden Ring (Greenfield)"


class SpellJuiceSurvivesSeizers(WorldTestBase):
    game = GAME
    options = {
        "item_shuffle": True,
        "pool_builder": True,
        "pool_builder_intensity": "max",     # S/A/B -> widest spell pool
        "pool_builder_pct_spells": 100,      # inject ONLY spells (the GOODS-nibble juice)
        "curated_filler": {"throwables": 10},  # a seizer: would overwrite filler spells with throwables
        "stone_injection": 200,              # a second seizer: filler -> low smithing stones
    }

    def test_injected_spells_all_survive_as_useful(self):
        # What pool_builder injects this world (deterministic; all SPELL under pct_spells=100).
        injected = PoolBuilderFeature()._juice_list(self.world)
        self.assertTrue(injected, "test is vacuous -- no spell juice was injected")
        self.assertTrue(all(ITEM_TIER_CATEGORY.get(n) == "SPELL" for n in injected),
                        "pct_spells=100 should inject only SPELL-category juice")

        # Every injected spell must appear in the FINAL curated pool as a `useful` item. This catches
        # BOTH failure modes at once: a seized spell vanishes entirely (replaced by a throwable/stone),
        # and an un-protected (filler) spell would be present but not useful -- either way it is missing
        # from the useful multiset. (A couple of base-pool spells resolve to non-GOODS FullIDs and are
        # useful too, so we assert per-injected-name coverage, not an exact total.)
        useful_spell_counts = collections.Counter(
            it.name for it in self.multiworld.itempool
            if it.player == self.world.player
            and ITEM_TIER_CATEGORY.get(it.name) == "SPELL"
            and bool(it.classification & ItemClassification.useful))
        injected_counts = collections.Counter(injected)
        seized = {n: (injected_counts[n], useful_spell_counts[n])
                  for n in injected_counts if useful_spell_counts[n] < injected_counts[n]}
        self.assertEqual(
            seized, {},
            "spell juice was seized by curated_filler / stone_injection -- these injected spells did "
            f"not survive as useful {{name: (injected, survived)}}: {seized}")
