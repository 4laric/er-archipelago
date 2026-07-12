"""important_locations tests -- matt-free location-type tagging + non-filler enforcement.

Pure-data: the tags derive from item_name/method (Remembrance excludes shop duplicates -> ~25, not 50).
World: with item_shuffle ON, every tagged+selected in-play location must reject a filler item; with a
degenerate pool (no real items) the fill-safety gate skips enforcement instead of FillError-ing.
"""
import unittest
import pytest

from BaseClasses import ItemClassification
from worlds.eldenring.location_tags import LOCATION_TAGS, TAG_COUNTS
from worlds.eldenring.features.important_locations import _DEFAULT, _VALID, _is_important
from worlds.eldenring.contract import SURFACE_EXCLUDE_TAGS as BIG_TICKET_EXCLUDE_TAGS

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
GAME = "Elden Ring"


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
        """'Boss' == every boss-healthbar DROP (tools/datamine_boss_drops.py -> _BOSS_DROP_FLAGS in
        gen_data._loc_tags), a superset of the ~25 boss_arena majors. Drift guard on the committed count.

        REBASELINED 76 -> 93 (2026-07-11). NOT a regression -- the DATAMINE got complete. Both EMEVD-derived
        inputs were mined when only 380 of the 589 EMEVD were decompiled, so ~35% of the game's award sites
        were invisible to them. Re-mined against all 589:

            boss_drops.py       54 -> 88 flags      (+34)
            boss_healthbars.py  197 -> 249 entities (+52)  -> boss_sweeps 196 -> 232 triggers

        The new drops are REAL, and the tell is that they include the ones we had HAND-ADDED because the
        scan missed them: Commander's Standard (Commander O'Neil) and Gargoyle's Blackblade (Black Blade
        Kindred) both live in gen_data._BOSS_DROP_EXTRAS. The derivation has caught up with the hand list,
        which is the direction we want (CONTRIBUTING: derive the datum, don't pin the symptom) -- and it
        means _BOSS_DROP_EXTRAS is now partly redundant and should be audited against the derived set.

        REBASELINED 93 -> 94 (2026-07-12). Ground truth got better again, and the predicate did NOT move.
        The 94th is flag 520660, "Caelid :: Dragon Heart" -- a mini-dungeon boss reward that HAD NO
        LOCATION AT ALL until tools/datamine_boss_reward_lots.py recovered the common.emevd $Event(1200)
        family (+37 checks). It picks up 'Boss' from the pre-existing dragon-heart rule in gen_data
        (`'dragon heart' in nm and not shop`), not from anything this change loosened: a Dragon Heart is
        by definition a dragon-boss drop. So this is a check that always existed in the GAME and finally
        exists in the WORLD -- exactly the direction the warning below blesses.

        ⚠️ If this number moves again, FIRST check whether an EMEVD-derived input is stale rather than
        rebaselining: `python tools/datamine_boss_drops.py` and `datamine_boss_healthbars.py` are cheap.
        A number that grows because the ground truth got better is fine; one that grows because a
        predicate got looser is a bug.
        """
        self.assertEqual(TAG_COUNTS["Boss"], 94)

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


