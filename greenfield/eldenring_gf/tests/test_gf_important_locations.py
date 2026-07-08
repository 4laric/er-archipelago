"""important_locations tests -- matt-free location-type tagging + non-filler enforcement.

Pure-data: the tags derive from item_name/method (Remembrance excludes shop duplicates -> ~25, not 50).
World: with item_shuffle ON, every tagged+selected in-play location must reject a filler item; with a
degenerate pool (no real items) the fill-safety gate skips enforcement instead of FillError-ing.
"""
import unittest
import pytest

from BaseClasses import ItemClassification
from worlds.eldenring_gf.location_tags import LOCATION_TAGS, TAG_COUNTS
from worlds.eldenring_gf.features.important_locations import _DEFAULT, _VALID, _is_important
from worlds.eldenring_gf.contract import BIG_TICKET_EXCLUDE_TAGS

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")
GAME = "Elden Ring (Greenfield)"


class TagDataTests(unittest.TestCase):
    def test_default_is_the_six(self):
        self.assertEqual(_DEFAULT, ["Remembrance", "Seedtree", "Church", "Boss", "Fragment", "Revered"])

    def test_all_default_tags_present(self):
        for t in _DEFAULT:
            self.assertIn(t, TAG_COUNTS, f"{t} not derived from the data")
            self.assertGreater(TAG_COUNTS[t], 0)

    def test_remembrance_excludes_shop_dupes(self):
        # buying a duplicate remembrance at the Twin Maiden Husks is NOT the meaningful check;
        # the raw item_name match was ~50, the boss-drop/emevd set is ~25.
        self.assertLessEqual(TAG_COUNTS["Remembrance"], 30)
        self.assertGreaterEqual(TAG_COUNTS["Remembrance"], 20)

    def test_boss_tag_is_boss_drop_set(self):
        # Boss was REDEFINED (boss-drop datamine, tools/datamine_boss_drops.py -> _BOSS_DROP_FLAGS in
        # gen_data._loc_tags): the 'Boss' tag is now every boss-healthbar DROP (~54), a superset of the
        # old ~23-25 boss_arena majors. Guards the current committed count against drift.
        self.assertEqual(TAG_COUNTS["Boss"], 54)

    def test_tags_are_valid_keys(self):
        # LOCATION_TAGS may carry INTERNAL tags (EniaShop) that are deliberately NOT user-selectable
        # important_location TYPES; those live in contract.BIG_TICKET_EXCLUDE_TAGS. Valid == either.
        valid = set(_VALID) | BIG_TICKET_EXCLUDE_TAGS
        for tags in LOCATION_TAGS.values():
            for t in tags:
                self.assertIn(t, valid)


def _tagged_in_play(world, mw):
    sel = set(world.options.important_locations.value) & set(_VALID)
    return [l for l in mw.get_locations(world.player)
            if LOCATION_TAGS.get(getattr(l, "address", None)) and sel.intersection(LOCATION_TAGS[l.address])]


class ImportantLocEnforced(WorldTestBase):
    game = GAME
    options = {"item_shuffle": True}  # real-item pool -> enough non-filler to enforce

    def test_tagged_reject_filler(self):
        tagged = _tagged_in_play(self.world, self.multiworld)
        self.assertGreater(len(tagged), 0, "expected tagged in-play locations with the real-item pool")
        filler = self.world.create_item(self.world.get_filler_item_name())
        self.assertFalse(_is_important(filler))
        bad = [l for l in tagged if l.item_rule(filler)]
        self.assertFalse(bad, f"{len(bad)} tagged locations accept a filler item")

    def test_placed_items_non_filler(self):
        # post-fill: nothing filler landed on a tagged location.
        for l in _tagged_in_play(self.world, self.multiworld):
            if l.item is not None and l.item.player == self.world.player:
                self.assertTrue(_is_important(l.item),
                                f"filler landed on tagged location {l.name}")


class ImportantLocDegenerateSafe(WorldTestBase):
    game = GAME
    options = {"item_shuffle": False}  # degenerate pool -> gate must SKIP, gen must not FillError

    def test_generates_without_overconstraint(self):
        # reaching setUp without a FillError is the assertion; confirm the world built.
        self.assertTrue(self.multiworld.get_locations(self.world.player))


class ImportantLocDegenerateFragmentSafe(WorldTestBase):
    # Regression for GF-fuzz-1569033476-0012/0024: item_shuffle off + a SINGLE small type
    # ("Fragment", ~21 tagged) meant the old avail>=tagged gate PASSED on region-Locks alone
    # (advancement, but logic-pinned -- 0 freely-placeable juice), enforced, then FillError.
    # The juice-keyed gate must SKIP here and gen clean.
    game = GAME
    options = {"item_shuffle": False, "important_locations": ["Fragment"]}

    def test_fragment_only_off_skips_and_gens(self):
        # reaching setUp (which runs fill) without FillError is the core assertion.
        self.assertTrue(self.multiworld.get_locations(self.world.player))
        # gate must have SKIPPED: with no juice, tagged Fragment locations still accept filler.
        tagged = _tagged_in_play(self.world, self.multiworld)
        self.assertGreater(len(tagged), 0, "expected Fragment locations in play")
        juice = sum(1 for i in self.multiworld.itempool
                    if i.player == self.world.player
                    and bool(i.classification & ItemClassification.useful)
                    and not i.advancement)
        self.assertEqual(juice, 0, "item_shuffle off should have no freely-placeable juice")
        filler = self.world.create_item(self.world.get_filler_item_name())
        self.assertTrue(all(l.item_rule(filler) for l in tagged),
                        "gate should have SKIPPED (juice < tagged): tagged locs must still accept filler")
