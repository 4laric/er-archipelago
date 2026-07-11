"""filler_curation tests -- configurable category recipe + stack grants (itemCounts)."""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring.item_ids import ITEM_CATALOG  # noqa: E402
from worlds.eldenring.features import filler_curation as fc  # noqa: E402

GAME = "Elden Ring"


# ---- pure-data guards -------------------------------------------------------------------------
def test_finished_pots_in_catalog():
    for p in ("Fire Pot", "Lightning Pot", "Volcano Pot", "Sleep Pot", "Rancor Pot"):
        assert p in ITEM_CATALOG, f"{p} must be added to the catalog (grantable)"


def test_all_categories_resolve():
    for cat, members in fc.CATEGORIES.items():
        for n in members:
            assert n in ITEM_CATALOG, f"{cat} member {n} must resolve in the catalog"


def test_stack_quantities():
    q = fc.stack_qty_by_name()
    assert q["Kukri"] == 5 and q["Throwing Dagger"] == 5, "throwables grant x5"
    assert q["Fire Pot"] == 2 and q["Rancor Pot"] == 2, "pots grant x2"
    assert q["Fire Grease"] == 2 and q["Rot Grease"] == 2, "greases grant x2"
    # foods/economy are NOT stacked here
    assert "Golden Rune [1]" not in q and "Exalted Flesh" not in q


def test_junk_predicate_protects_economy_and_funny():
    assert fc._is_junk_consumable("Smoldering Butterfly")
    assert fc._is_junk_consumable("Rune")
    assert not fc._is_junk_consumable("Golden Rune [1]")
    assert not fc._is_junk_consumable("Smithing Stone [3]")
    assert not fc._is_junk_consumable("Raw Meat Dumpling")


# ---- WorldTestBase: recipe distribution + stacks + fill-safety ---------------------------------
class CuratedFillerRecipe(WorldTestBase):
    game = GAME
    # inherited test_fill proves beatable with the recipe on.
    options = {"item_shuffle": True, "enable_dlc": True, "num_regions": 8,
               "curated_filler": {"throwables": 60, "pots": 30, "greases": 10}}

    def test_recipe_distribution_and_stacks(self):
        from collections import Counter
        n = Counter(i.name for i in self.multiworld.itempool if i.player == self.world.player)
        thr = sum(n[x] for x in fc.CATEGORIES["throwables"])
        pot = sum(n[x] for x in fc.CATEGORIES["pots"])
        gre = sum(n[x] for x in fc.CATEGORIES["greases"])
        self.assertGreater(thr, pot, "throwables (weight 60) > pots (30)")
        self.assertGreater(pot, gre, "pots (30) > greases (10)")
        # stacks emitted in slot_data
        ic = self.world.fill_slot_data().get("itemCounts", {})
        self.assertEqual(ic.get(str(self.world.item_name_to_id["Kukri"])), 5)
        self.assertEqual(ic.get(str(self.world.item_name_to_id["Fire Pot"])), 2)
        # funny junk survives
        self.assertGreater(n["Raw Meat Dumpling"] + n["Gold-Tinged Excrement"], 0)


class CuratedFillerOff(WorldTestBase):
    game = GAME
    options = {"item_shuffle": True, "num_regions": 6, "curated_filler": {}}

    def test_empty_recipe_no_change(self):
        n = sum(1 for i in self.multiworld.itempool
                if i.player == self.world.player and i.name in ("Fire Pot", "Kukri"))
        self.assertLess(n, 10, "empty recipe must not inject the roster")
        # itemCounts (stacks) are ALWAYS emitted (item property, not recipe-gated).
        ic = self.world.fill_slot_data().get("itemCounts", {})
        self.assertEqual(ic.get(str(self.world.item_name_to_id["Kukri"])), 5)
