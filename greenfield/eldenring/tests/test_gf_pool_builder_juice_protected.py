"""Regression: juice gear reaches the pool as `useful`, and per-category juice still works.

HISTORY -- read this before "simplifying" the file away. It used to guard a collision that no longer
exists: pool_builder injected gear as `useful`, but some catalog gear (notably spells & incantations)
carries the GOODS FullID nibble, so core._classify_full defaulted it to `filler` -- and BOTH seizers
of the day (core's stone_injection, then filler_curation.curate()) protected only progression|useful.
A filler-classified S-tier sorcery the player had "paid" a juice slot for would be silently
overwritten with a throwable or a smithing stone.

There are no seizers any more. features/filler_budget is the single owner of the filler tail: it
decides the whole thing in ONE pass, so nothing runs afterwards that could take a juice slot back.
The collision is structurally impossible, which is a better guarantee than the classification fix was.

What survives is worth keeping, and it is what this file now asserts:

  1. juice still lands in the pool as `useful` (AP's fill treats useful and filler differently, and
     juice is meant to be the former);
  2. `pool_builder_pct_spells` and friends STILL WORK -- they split the JUICE allocation rather than
     carving a second private slice out of the tail. Same knob, same meaning ("what share of my gear
     injection is spells?"), but it can no longer grow the juice budget at the economy's expense.
     That last clause is the whole reason the tail got a single owner, so it deserves a test.
"""
import collections

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from BaseClasses import ItemClassification  # noqa: E402
from worlds.eldenring.item_tiers import ITEM_TIER_CATEGORY  # noqa: E402
from worlds.eldenring.features import filler_budget as fb  # noqa: E402

GAME = "Elden Ring"


class SpellJuiceIsUsefulAndCategorised(WorldTestBase):
    game = GAME
    options = {
        "num_regions": 6,
        "pool_builder_pct_spells": 100,   # spell-only gear injection
        # A heavy economy recipe alongside it: under the OLD design this is precisely the combination
        # that starved -- juice took the whole tail first and the recipe got the crumbs. Now they are
        # allocated from one budget, so both must actually arrive.
        "curated_filler": {"juice": 40, "stones": 25, "runes": 15, "throwables": 20},
    }

    def _pool(self):
        return [i for i in self.multiworld.itempool if i.player == self.world.player]

    def test_juice_is_spells_only_and_useful(self):
        pool = self._pool()
        spells = [i for i in pool if ITEM_TIER_CATEGORY.get(i.name) == "SPELL"]
        self.assertTrue(spells, "pct_spells=100 should inject SPELL-category juice")
        not_useful = [i.name for i in spells
                      if not (i.classification & ItemClassification.useful)]
        self.assertFalse(
            not_useful,
            f"spell juice must be classified useful, not filler (GOODS nibble trap): {not_useful[:5]}")

    def test_juice_did_not_eat_the_economy(self):
        """THE point of the single owner. Under the old two-budget design juice ran first and took the
        entire tail; the recipe's stones/runes then had nothing to seize and delivered ~nothing. Both
        must now arrive, in roughly the proportions the recipe asked for."""
        names = collections.Counter(i.name for i in self._pool())
        stones = sum(c for n, c in names.items() if n.startswith("Smithing Stone ["))
        spells = sum(c for n, c in names.items() if ITEM_TIER_CATEGORY.get(n) == "SPELL")
        self.assertGreater(stones, 0, "the recipe weighted stones at 25 and got none -- juice ate them")
        self.assertGreater(spells, 0, "the recipe weighted juice at 40 and got none")

        # stones:25 vs juice:40 -- the ratio need not be exact (juice is capped by how many SPELLs
        # exist at the rarity floor, and vanilla stones ride along on top of the reservation), but
        # neither side may be starved to a rounding error by the other.
        alloc = getattr(self.world, "gf_filler_alloc", {})
        self.assertGreater(alloc.get("stones", 0), 0, f"allocator gave stones nothing: {alloc}")
        self.assertGreater(alloc.get("juice", 0), 0, f"allocator gave juice nothing: {alloc}")


class GlobalJuiceIsBestFirst(WorldTestBase):
    game = GAME
    options = {"num_regions": 6, "curated_filler": {"juice": 100}}

    def test_juice_only_recipe_fills_the_tail_with_gear(self):
        """juice:100 = the whole tail is gear injection. This is the old frozen behaviour (pool_builder
        scope=all_filler, cap=auto), now expressed as a recipe weight instead of a private budget --
        and it is exactly the setting that starved the economy, so it must remain EXPRESSIBLE (you may
        ask for it) while no longer being the DEFAULT (you no longer get it by accident)."""
        alloc = getattr(self.world, "gf_filler_alloc", {})
        self.assertGreater(alloc.get("juice", 0), 0)
        self.assertEqual(alloc.get("stones", 0), 0, "juice-only recipe reserves no stones, by request")
        from worlds.eldenring.features.filler_curation import CuratedFiller
        self.assertGreater(CuratedFiller.default.get("stones", 0), 0,
                           "...but the SHIPPED DEFAULT must reserve stones -- that is the fix")
