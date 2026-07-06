"""important_locations tests -- matt-free location-type tagging + non-filler enforcement.

Pure-data: the tags derive from item_name/method (Remembrance excludes shop duplicates -> ~25, not 50).
World: with item_shuffle ON, every tagged+selected in-play location must reject a filler item; with a
degenerate pool (no real items) the fill-safety gate skips enforcement instead of FillError-ing.
"""
import unittest
import pytest

from worlds.eldenring_gf.location_tags import LOCATION_TAGS, TAG_COUNTS
from worlds.eldenring_gf.features.important_locations import _DEFAULT, _VALID, _is_important

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

    def test_boss_matches_boss_arena(self):
        self.assertEqual(TAG_COUNTS["Boss"], 25)

    def test_tags_are_valid_keys(self):
        for tags in LOCATION_TAGS.values():
            for t in tags:
                self.assertIn(t, _VALID)


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
