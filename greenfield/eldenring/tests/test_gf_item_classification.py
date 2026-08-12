"""useful/filler comes from the item_categories partition, and this file is the pin on that.

WHAT CHANGED. `core._classify_full` answered "useful or filler?" from the ER FullID high nibble --
goods -> filler, everything else -> useful. That was a SECOND partition of the same 2084 items,
coarser than `item_categories` and living in a different file, so the two could disagree with
nothing to say so. They did: 203 spells, 79 spirit ashes and 37 crystal tears carry the GOODS
nibble, and AP's fill -- plus every partner's client and tracker -- reads them as junk. The nibble
test is gone; `item_categories.CATEGORY_CLASS` is the one table.

THIS REFACTOR CHANGES NO SEED, and `test_the_table_still_agrees_with_the_retired_nibble_rule` is the
whole reason that sentence can be said out loud. It re-derives the retired rule and demands the new
table agree on every catalog name. Flipping a category is therefore a deliberate edit that turns
this red -- which is the point: the policy question ("should a spell be useful?") gets argued on its
own PR, with `tools/gf_export_profile.py` numbers, and not smuggled in under a refactor.

`test_the_disagreement_this_exists_to_expose` is that argument's exhibit, asserted rather than
described, so the cost of today's answer is a number in the suite instead of a claim in a comment.
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


class TheRefactorMovedNothing(WorldTestBase):
    game = GAME
    options = {"num_regions": 1}

    def test_the_table_still_agrees_with_the_retired_nibble_rule(self):
        """THE PIN. No seed may move because of this refactor."""
        disagreed = sorted(n for n in ITEM_CATALOG
                           if ic.class_of(n) != _retired_nibble_rule(n))
        seen = {n: ic.class_of(n) for n in ITEM_CATALOG}
        # Witnesses: the scan ran over the whole catalog and BOTH answers actually occur, so a
        # constant-returning class_of could not pass this.
        self.assertEqual(len(seen), len(ITEM_CATALOG))
        self.assertEqual(set(seen.values()), {ic.USEFUL, ic.FILLER})
        self.assertFalse(disagreed,
                         f"{len(disagreed)} items reclassified by a refactor that must move "
                         f"nothing, e.g. {disagreed[:8]}")

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


class TheDisagreementThisExistsToExpose(WorldTestBase):
    """The motivating case (CONTRIBUTING rule 11), asserted so it is a number and not a claim.

    These three categories are gear a player equips and casts, and today the world hands them to
    AP's fill -- and to a partner's tracker -- labelled junk. Nothing here says that is wrong; it
    says it is TRUE, and it is the exhibit the flip PR argues from. When that PR lands, this class
    is the one that changes, deliberately, with export-profile numbers attached.
    """
    game = GAME
    options = {"num_regions": 1}

    def test_gear_that_carries_the_goods_nibble_is_still_filler(self):
        counts = {c: 0 for c in ("spells", "spirit_ashes", "crystal_tears")}
        for name in ITEM_CATALOG:
            cat = ic.category_of(name)
            if cat in counts:
                counts[cat] += 1
                self.assertEqual(ic.class_of(name), ic.FILLER, name)
        for cat, n in counts.items():
            self.assertGreater(n, 30, f"witness: {cat} holds {n} items, expected a real roster")
