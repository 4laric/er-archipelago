"""useful/filler comes from the item_categories partition, and this file is the pin on that.

WHAT CHANGED. `core._classify_full` answered "useful or filler?" from the ER FullID high nibble --
goods -> filler, everything else -> useful. That was a SECOND partition of the same 2084 items,
coarser than `item_categories` and living in a different file, so the two could disagree with
nothing to say so. They did: 203 spells, 79 spirit ashes and 37 crystal tears carry the GOODS
nibble, and AP's fill -- plus every partner's client and tracker -- reads them as junk. The nibble
test is gone; `item_categories.CATEGORY_CLASS` is the one table.

THE FLIP HAPPENED (2026-08-12, Alaric's call). `spells`, `spirit_ashes` and `crystal_tears` are
`useful` now. The refactor that split this question out of core shipped as a no-op precisely so this
PR could be the one that moves seeds, on its own, with numbers attached.

So the pin CHANGED SHAPE rather than being deleted. It used to demand agreement with the retired
nibble rule on every catalog name; it now demands the difference be EXACTLY those three categories,
in exactly one direction. That is strictly the stronger assertion -- it still catches any drift the
old one caught, and it additionally catches the flip growing a fourth category by accident, which a
loosened "some things are useful now" test would wave through.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from BaseClasses import ItemClassification                     # noqa: E402
from worlds.eldenring import core                              # noqa: E402
from worlds.eldenring import item_categories as ic             # noqa: E402
from worlds.eldenring.item_ids import ITEM_CATALOG, GOODS_TYPE  # noqa: E402
from worlds.eldenring.features.progressive import PROG_FLASK   # noqa: E402
from worlds.eldenring.features.traps import TRAPS              # noqa: E402

GAME = "Elden Ring"

# The rule core.py used to carry, re-derived here and NOWHERE ELSE. It is retired production code
# kept as an oracle: the pin below is only worth anything if this is the original predicate, so it
# is written from the nibble directly rather than by calling anything under test.
def _retired_nibble_rule(name):
    return ic.FILLER if (ITEM_CATALOG[name] & 0xF0000000) == ic.GOODS_NIBBLE else ic.USEFUL


class TheTableIsTotalAndMintsTwoClasses(WorldTestBase):
    game = GAME
    options = {"num_regions": 1}

    def test_generated_inputs_are_present(self):
        # Every scan below is vacuous on a pre-regen tree. Say so loudly rather than pass.
        self.assertTrue(ITEM_CATALOG, "item_ids.py must be generated")
        self.assertTrue(GOODS_TYPE, "item_ids.py must carry GOODS_TYPE (gen_data.py regen)")

    def test_every_category_has_a_class_except_the_no_fullid_bucket(self):
        # Totality is the property that makes the table safe to read with `.get(..., FILLER)`: add a
        # goods type tomorrow and this reds instead of the new category silently defaulting to junk.
        self.assertEqual(set(ic.CATEGORY_CLASS),
                         set(ic.CATEGORIES) - {ic.PROGRESSIVE_CATEGORY})
        self.assertNotIn(ic.PROGRESSIVE_CATEGORY, ic.CATEGORY_CLASS)

    def test_no_category_mints_progression(self):
        # `progressive` and `progression` are one letter apart and unrelated. A category may never
        # grant the AP class -- that is per-name and per-seed, and core._class_for owns it.
        self.assertTrue(ic.CATEGORY_CLASS)
        self.assertEqual(set(ic.CATEGORY_CLASS.values()), {ic.USEFUL, ic.FILLER})

    def test_no_category_spans_both_sides_of_the_nibble(self):
        # THE HAZARD IN THE PIN BELOW. `other` is reachable from goodsType 3/9/12/15 AND -- via
        # `NIBBLE_CATEGORY.get(..., "other")` -- from any nibble the table does not know. No catalog
        # item takes that second path today, so `other` has ONE honest class. If a regen ever adds a
        # nibble, this reds here rather than silently reclassifying whatever arrived.
        sides = {}
        for name, full in ITEM_CATALOG.items():
            sides.setdefault(ic.category_of(name), set()).add(
                (full & 0xF0000000) == ic.GOODS_NIBBLE)
        self.assertEqual(len(sides), len(ic.census()), "witness: every category was visited")
        mixed = sorted(c for c, s in sides.items() if len(s) > 1)
        self.assertFalse(mixed, f"categories holding both goods and non-goods items: {mixed}")


# The categories the flip deliberately moved, and the ONLY ones. Adding to this list is how a future
# flip is declared; a category that starts disagreeing with the retired rule without being named
# here is drift, and the pin below calls it that.
FLIPPED_TO_USEFUL = frozenset({"spells", "spirit_ashes", "crystal_tears"})


class TheFlipIsExactlyThreeCategories(WorldTestBase):
    game = GAME
    options = {"num_regions": 1}

    def test_the_difference_from_the_retired_rule_is_exactly_the_declared_flip(self):
        """THE PIN, in its post-flip shape. Every departure from the nibble must be declared."""
        moved = {n for n in ITEM_CATALOG if ic.class_of(n) != _retired_nibble_rule(n)}
        declared = {n for n in ITEM_CATALOG if ic.category_of(n) in FLIPPED_TO_USEFUL}
        seen = {n: ic.class_of(n) for n in ITEM_CATALOG}
        # Witnesses: the scan covered the catalog, both answers occur, and the flip is not empty --
        # so neither a constant class_of nor a table that silently reverted could pass.
        self.assertEqual(len(seen), len(ITEM_CATALOG))
        self.assertEqual(set(seen.values()), {ic.USEFUL, ic.FILLER})
        self.assertGreater(len(declared), 300, "witness: the declared flip is a real roster")
        undeclared = sorted(moved - declared)
        self.assertFalse(undeclared,
                         f"{len(undeclared)} items disagree with the nibble rule without being "
                         f"declared in FLIPPED_TO_USEFUL: {undeclared[:8]}")
        reverted = sorted(declared - moved)
        self.assertFalse(reverted,
                         f"{len(reverted)} declared-flipped items are back on the nibble answer: "
                         f"{reverted[:8]}")

    def test_the_flip_only_ever_went_filler_to_useful(self):
        # A category flipped the other way would be a demotion, and nothing here has ever wanted
        # one. Asserted separately so the direction cannot ride in on the set comparison above.
        demoted = sorted(n for n in ITEM_CATALOG
                         if _retired_nibble_rule(n) == ic.USEFUL and ic.class_of(n) == ic.FILLER)
        self.assertFalse(demoted, f"items demoted to filler: {demoted[:8]}")

    def test_the_categories_that_did_not_flip_did_not_move(self):
        # The closest call on the table is `upgrade_materials` -- deliberately still filler, because
        # promoting it would move features/filler_budget's whole allocated tail into the useful tier.
        for cat in ("upgrade_materials", "consumables", "crafting", "runes", "key_items", "other"):
            self.assertEqual(ic.CATEGORY_CLASS[cat], ic.FILLER, cat)

    def test_the_world_asks_the_table_and_not_the_nibble(self):
        # The pin above is about the table; this is about the WIRING. A correct table core never
        # consults would pass the one and fail the player.
        checked = 0
        for name in ("Uchigatana", "Lordsworn's Greatsword", "Golden Rune [1]",
                     "Smithing Stone [1]", "Radagon's Soreseal"):
            if name not in ITEM_CATALOG:
                continue
            want = (ItemClassification.useful if ic.class_of(name) == ic.USEFUL
                    else ItemClassification.filler)
            self.assertEqual(self.world.create_item(name).classification, want, name)
            checked += 1
        self.assertGreaterEqual(checked, 4, "witness: the sample names must exist in the catalog")


class DeclaredClassesWinOverTheTable(WorldTestBase):
    game = GAME
    options = {"num_regions": 1}

    def test_the_table_has_no_opinion_outside_the_catalog(self):
        # `category_of` folds every feature-minted name into `progressive`, which holds FOUR AP
        # classes at once. class_of must abstain there or it overrules the features' declarations.
        minted = [core.FILLER, PROG_FLASK] + sorted(TRAPS.values())
        self.assertGreaterEqual(len(minted), 5)
        for name in minted:
            self.assertIsNone(ic.class_of(name),
                              f"{name} is feature-minted; the taxonomy must not classify it")

    def test_each_minted_class_survives(self):
        # One live item per class the `progressive` bucket actually holds, so "abstain" is shown to
        # preserve all of them rather than merely the one that would have been guessed.
        region_lock = f"{core.REGIONS[0]} Lock"
        cases = [(region_lock, ItemClassification.progression),
                 (PROG_FLASK, ItemClassification.useful),
                 (TRAPS["rune_thief"], ItemClassification.filler),
                 (core.FILLER, ItemClassification.filler)]
        for name, want in cases:
            self.assertEqual(self.world.create_item(name).classification, want, name)
        self.assertEqual(len(cases), 4, "witness: all four classes were exercised")


class GearThatCarriesTheGoodsNibbleIsUsefulNow(WorldTestBase):
    """The motivating case (CONTRIBUTING rule 11), and the class that changed when the flip landed.

    It used to assert the opposite -- that these three were filler -- as the exhibit the flip would
    argue from. Same three rosters, same witnesses, inverted expectation, so the file records that
    the thing it measured is the thing that got fixed.
    """
    game = GAME
    options = {"num_regions": 1}

    def test_spells_spirit_ashes_and_crystal_tears_are_useful(self):
        counts = {c: 0 for c in FLIPPED_TO_USEFUL}
        for name in ITEM_CATALOG:
            cat = ic.category_of(name)
            if cat in counts:
                counts[cat] += 1
                self.assertEqual(ic.class_of(name), ic.USEFUL, name)
        for cat, n in counts.items():
            self.assertGreater(n, 30, f"witness: {cat} holds {n} items, expected a real roster")

    def test_the_world_hands_a_sorcery_to_the_fill_as_useful(self):
        # End to end, through create_item, because the table is not what AP reads -- the Item is.
        sample = [n for n in ITEM_CATALOG if ic.category_of(n) == "spells"]
        self.assertGreater(len(sample), 100, "witness: the spell roster is real")
        for name in sorted(sample)[:25]:
            self.assertEqual(self.world.create_item(name).classification,
                             ItemClassification.useful, name)
