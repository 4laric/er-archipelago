"""pool_builder_scope = all_filler -- juice may displace junk-consumable vanilla filler, economy-safe.

Default scope (rune_tail) only lets juice replace the Rune fallback tail. all_filler ALSO lets it
replace junk-consumable vanilla filler (throwables/pots/greases/...), vastly raising the juice ceiling,
while NEVER touching: the tuned economy (Golden/Lord's/Hero's/Numen's Runes, Smithing/Somber stones,
Golden Seed, Sacred Tear, Glovewort, Great Rune), FUNNY_JUNK, real gear, or anything the seed marks
progression (e.g. the Academy Glintstone Key gate). The core extras-sort and pool_builder's budget use
the SAME displaceable_filler predicate, so the drop order and the juice count cannot drift.

WorldTestBase.setUp runs create_items + fill-reachability default tests, so a class that constructs at
all proves the widened juice pool still generates a WINNABLE seed.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")

from worlds.eldenring_gf.data import LOCATIONS, HUB  # noqa: E402
from ._util import world_items, world_pool_items  # noqa: E402
from worlds.eldenring_gf.features.pool_builder import PoolBuilderFeature  # noqa: E402
from worlds.eldenring_gf.features.filler_curation import displaceable_filler  # noqa: E402

GAME = "Elden Ring (Greenfield)"


def _total_locations(world):
    return len(LOCATIONS.get(HUB, [])) + sum(len(LOCATIONS.get(r, [])) for r in world._kept())


class AllFillerJuice(WorldTestBase):
    game = GAME
    options = {
        "item_shuffle": True,
        "pool_builder": True,
        "pool_builder_intensity": "max",
        "pool_builder_scope": "all_filler",
        "pool_builder_juice_cap": 0,          # auto-size to the whole widened budget
        "legacy_dungeon_keys": True,          # promotes Academy Glintstone Key to progression
        "curated_filler": {"throwables": 5},  # a competing filler seizer
        "stone_injection": 100,               # another filler seizer
    }

    def test_widened_budget_much_larger_than_rune_tail(self):
        # The Rune tail is a few dozen checks; all_filler should reach well past that (clamped only by
        # the S/A/B juice catalog, ~hundreds).
        n = len(PoolBuilderFeature()._juice_list(self.world))
        self.assertGreater(n, 100, f"all_filler juice budget should dwarf the rune tail, got {n}")

    def test_count_neutral(self):
        own = [it for it in world_pool_items(self) if it.player == self.world.player]
        self.assertEqual(len(own), _total_locations(self.world),
                         "pool must stay exactly one item per location (count-neutral)")

    def test_progression_key_not_displaced(self):
        # Academy Glintstone Key is a promoted gate (progression) sharing the GOODS nibble; it must
        # survive the widened displacement.
        names = {it.name for it in world_pool_items(self) if it.player == self.world.player}
        self.assertIn("Academy Glintstone Key", names,
                      "a progression key was displaced by all_filler juice (winnability risk)")

    def test_predicate_protects_economy_and_progression(self):
        w = self.world
        for protected in ("Golden Rune [1]", "Smithing Stone [1]", "Somber Smithing Stone [1]",
                          "Academy Glintstone Key"):
            self.assertFalse(displaceable_filler(w, protected),
                             f"{protected!r} must be protected from juice displacement")
        # a genuine junk consumable IS displaceable
        self.assertTrue(displaceable_filler(w, "Fire Pot"),
                        "Fire Pot is junk-consumable filler and should be displaceable")


class RuneTailUnchanged(WorldTestBase):
    game = GAME
    options = {  # default scope -- juice bounded to the small Rune tail
        "item_shuffle": True, "pool_builder": True, "pool_builder_intensity": "max",
        "pool_builder_juice_cap": 0,
    }

    def test_rune_tail_budget_is_small(self):
        n = len(PoolBuilderFeature()._juice_list(self.world))
        self.assertLess(n, 100,
                        f"default scope=rune_tail should bound juice to the Rune tail, got {n}")
