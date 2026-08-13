"""filler_curation tests -- configurable category recipe + stack grants (itemCounts)."""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring.item_ids import AMMO_ITEM_NAMES, ITEM_CATALOG  # noqa: E402
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


def test_firepots_is_opt_in_fire_lean():
    """firepots leans the mix toward fire/volcano for DLC Furnace Golems. Base members are always
    present; the DLC Hefty Fire Pot joins post-regen (catalog-filtered). It is OPT-IN: a valid recipe
    category that is NOT in the default recipe, so existing seeds are unchanged unless weighted."""
    fp = fc.CATEGORIES["firepots"]
    assert "Fire Pot" in fp and "Volcano Pot" in fp, "firepots must carry the base fire throwables"
    assert all(("Fire" in n or "Volcano" in n) for n in fp), f"firepots must be fire/volcano only: {fp}"
    assert all(n in ITEM_CATALOG for n in fp), "firepots members must resolve in the catalog"
    assert "firepots" in fc._VALID_CATS, "firepots must be an accepted recipe category"
    assert "firepots" not in fc.CuratedFiller.default, "firepots must be opt-in (absent from default)"
    # Same bar for junk_gear (#191/#624 follow-up), and for the same reason: it is OFFERED, not
    # imposed. The weights are relative, so adding a key to the shipped recipe re-proportions every
    # other category and moves EVERY default seed -- which is exactly the silent behaviour change
    # this file exists to stop. junk_gear is the ~368 equippables the game rates trivial; a player
    # who wants the low end of the armoury asks for it. Alaric's ruling, 2026-08-13: default 0.
    assert "junk_gear" not in fc.CuratedFiller.default, (
        "junk_gear must stay opt-in (absent from the default recipe) -- it is a category we PROVIDE, "
        "not one we impose; weighting it by default re-proportions every other category")
    assert "junk_gear" in fc.CATEGORIES, "junk_gear must still be an offerable category"
    assert "junk_gear" in fc.RECIPE_KEYS, "junk_gear must be an accepted recipe key or a yaml naming it raises"
    assert fc.stack_qty_by_name().get("Fire Pot") == 2, "firepots members stack x2 like pots"


# ---- the recipe key surface: one list, three consumers (#571) ----------------------------------
def test_valid_keys_accepts_the_shipped_default():
    """CuratedFiller.valid_keys must accept CuratedFiller.default. Sounds tautological; is not.

    MOTIVATING CASE (rule 11). `valid_keys` was first written as `sorted(_VALID_CATS)`, which is
    `frozenset(CATEGORIES) | {"junk"}` -- and `juice` is NOT a member of CATEGORIES (it is drawn
    from the curated tier ladder, not a name list). The shipped default weights `juice` at 42, so
    AP's verify_keys would have rejected the world's own default recipe and every seed that did not
    override it would have failed to generate. Nothing else in the suite compares these two.
    """
    vk = set(fc.CuratedFiller.valid_keys)
    missing = set(fc.CuratedFiller.default) - vk
    assert not missing, f"the default recipe weights {sorted(missing)}, which valid_keys rejects"
    assert "juice" in vk, "juice is a recipe key with no CATEGORIES entry -- it must be added on top"


def test_valid_keys_is_the_list_filler_budget_enforces():
    """One source. AP's verify_keys, the wizard metadata and filler_budget's unknown-category
    OptionError must all read the SAME set, or a key is accepted by one and refused by another."""
    from worlds.eldenring.features import filler_budget as fb
    assert set(fc.CuratedFiller.valid_keys) == set(fb.VALID) == set(fc.RECIPE_KEYS)


def test_valid_keys_is_sorted():
    """It lands in a committed artifact (wizard/options-metadata.json). A frozenset has no stable
    iteration order, so an unsorted list makes `dump_options_metadata.py --check` flap."""
    assert fc.CuratedFiller.valid_keys == sorted(fc.CuratedFiller.valid_keys)


def test_stack_quantities():
    q = fc.stack_qty_by_name()
    assert q["Kukri"] == 5 and q["Throwing Dagger"] == 5, "throwables grant x5"
    assert q["Fire Pot"] == 2 and q["Rancor Pot"] == 2, "pots grant x2"
    assert q["Fire Grease"] == 2 and q["Rot Grease"] == 2, "greases grant x2"
    assert q["Arrow"] == 20 and q["Bolt"] == 20 and q["Ballista Bolt"] == 20, "ammunition grants x20"
    # foods/economy are NOT stacked here
    assert "Golden Rune [1]" not in q and "Exalted Flesh" not in q


def test_ammunition_is_param_derived_not_name_derived():
    """The ammo set comes from EquipParamWeapon.wepType (81/83/85/86), NOT a name predicate. A
    name-suffix derivation would sweep in the "...Bolt"/"...Strike" INCANTATIONS and hand a caster
    x20 of a spell; the wepType join structurally cannot. Witnesses pin both directions: real ammo
    (base + DLC, all four wepTypes) must be present, known bolt-named incantations and the adjacent
    wepType bands (87 torches, 88 hand-to-hand arts) must be absent. Floor 20: gen_data hard-errors
    below it, this asserts the shipped module actually cleared it (23 measured 2026-07-14)."""
    ammo = set(AMMO_ITEM_NAMES)
    assert len(ammo) >= 20, f"ammo set collapsed: {len(ammo)}"
    for w in ("Arrow", "Great Arrow", "Bolt", "Ballista Bolt", "St. Trina's Arrow",
              "Shattershard Arrow (Fletched)", "Black-Key Bolt"):
        assert w in ammo, f"real ammo missing: {w}"
    for spell in ("Honed Bolt", "Lightning Strike", "Ancient Dragons' Lightning Strike",
                  "Vyke's Dragonbolt", "Lansseax's Glaive", "Fortissax's Lightning Spear"):
        assert spell not in ammo, f"incantation leaked into the ammo set: {spell}"
    for not_ammo in ("Torch", "Beast-Repellent Torch", "Dryleaf Arts"):   # wepType 87 / 88
        assert not_ammo not in ammo, f"non-ammo weapon leaked into the ammo set: {not_ammo}"
    assert set(fc.CATEGORIES["ammunition"]) == ammo, "category must mirror the generated list"
    assert all(n in ITEM_CATALOG for n in ammo), "ammo names must resolve in the catalog"


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

    # PINNED DRAW -- see the funny-junk assertion at the end of the method for why.
    SEED = 22

    def test_recipe_distribution_and_stacks(self):
        from collections import Counter
        self.world_setup(seed=self.SEED)
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
        # FUNNY JUNK SURVIVES THE SEIZURE. `_is_junk_consumable` returns False for these two, so
        # curated_filler may not displace them; the unit-level half of that promise is
        # test_junk_predicate_protects_economy_and_funny, which needs no world at all.
        #
        # 🛑 WHY THE SEED IS PINNED. This recipe carries no `funny` weight, so nothing here
        # INJECTS these items -- every copy is a vanilla placement from whichever regions the draw
        # kept. Their count is therefore a property of the DRAW, and `num_regions: 8` can miss both
        # items outright. Unpinned, this line asserted `> 0` against a random draw and failed on the
        # rare seed that did, reading on main as a flake in an unrelated suite rather than as this
        # assertion. Zero is not a curation bug; it is a seed with nothing to protect, and a test
        # that cannot tell those apart is measuring the draw. Seed 22 places nine.
        self.assertGreater(n["Raw Meat Dumpling"] + n["Gold-Tinged Excrement"], 0,
                           "no protected funny junk in the pool on the PINNED seed %d -- either "
                           "the junk seizure has stopped honouring _is_junk_consumable, or the "
                           "region data moved these items out of this draw and the pin needs "
                           "re-choosing (it is a witness, not a constant)" % self.SEED)


class CuratedFillerOff(WorldTestBase):
    game = GAME
    options = {"item_shuffle": True, "num_regions": 6, "curated_filler": {}}

    def test_empty_recipe_no_change(self):
        """An explicitly empty recipe leaves the tail exactly as vanilla paid it. Since v0.2 that also
        means NO juice and NO stone economy (the recipe owns the whole tail now, not just the junk
        share) -- features/filler_budget warns loudly rather than rejecting, because "give me vanilla"
        is a real thing to want."""
        n = sum(1 for i in self.multiworld.itempool
                if i.player == self.world.player and i.name in ("Fire Pot", "Kukri"))
        self.assertLess(n, 10, "empty recipe must not inject the roster")
        # itemCounts (stacks) are ALWAYS emitted (item property, not recipe-gated).
        ic = self.world.fill_slot_data().get("itemCounts", {})
        self.assertEqual(ic.get(str(self.world.item_name_to_id["Kukri"])), 5)
