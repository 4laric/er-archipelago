"""important_locations tests -- matt-free location-type tagging + non-filler enforcement.

Pure-data: the tags derive from item_name/method (Remembrance excludes shop duplicates -> ~25, not 50).
World: with item_shuffle ON, every tagged+selected in-play location must reject a filler item; with a
degenerate pool (no real items) the fill-safety gate skips enforcement instead of FillError-ing.
"""
import unittest
import pytest

from BaseClasses import ItemClassification
from worlds.eldenring.data import LOCATIONS
from worlds.eldenring.location_tags import LOCATION_TAGS, TAG_COUNTS, DEFAULTED_REGION_APS
from worlds.eldenring.features.important_locations import _DEFAULT, _VALID, _is_important
from worlds.eldenring.contract import SURFACE_EXCLUDE_TAGS

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

        REBASELINED 94 -> 95 (2026-07-24, co-check regen -- SPEC-flag-lot-item-model). This is a
        CO-CHECK sibling, NOT a datamine change: the distinct Boss-tagged FLAG set is UNCHANGED at 94
        (verified). The +1 is a second Boss-tagged LOCATION for flag 510440 -- the Hippo's death flag in
        Scadu Altus, one of the four CO_CHECK_FLAGS. That flag drives two lots: the primary ('Aspects of
        the Crucible: Thorns') and the sibling ('Scadutree Fragment', ap 7900001), each now its own
        co-firing check. Both are genuine Hippo boss drops, so both carry 'Boss' -- the count follows
        AP LOCATIONS, and one already-Boss flag simply gained its sibling location. The predicate did NOT
        move; widening CO_CHECK_FLAGS beyond the four is the only thing that can move this number via
        co-checks (each added shared-flag Boss drop adds one).

        ⚠️ If this number moves again, FIRST check whether an EMEVD-derived input is stale, or whether a
        CO_CHECK_FLAGS addition added a sibling, rather than rebaselining: `python
        tools/datamine_boss_drops.py` and `datamine_boss_healthbars.py` are cheap. A number that grows
        because the ground truth got better (or a deliberate co-check sibling landed) is fine; one that
        grows because a predicate got looser is a bug.
        REBASELINED 95 -> 134 (2026-07-26, MajorBoss subset closure). The DEFINITION got right; the
        predicate did not get looser. 'Boss' had been excluding the major bosses because
        tools/datamine_boss_drops.py step (4) drops any reward whose ITEM NAME contains "remembrance"
        or "great rune" -- a filter we own, not one the game imposes (its own
        HandleBossDefeatAndDisplayBanner fires for the majors; the tool finds them and discards them).
        The effect was player-visible: important_locations=["Boss"] is a PLAYER option value, and it
        returned 95 checks with Godrick, Rennala, Radahn, Rykard, Mohg and Malenia all missing.
        gen_data now closes MajorBoss under Boss, so the delta is exactly the 39 majors that were
        outside it (34 already tagged MajorBoss + the 5 the arity fix newly tags). Post-closure, Boss
        is exactly the union of {Boss, MajorBoss, Remembrance, GreatRune} = 134.

        ⚠️ Same warning as above still applies to any FURTHER movement.
        """
        self.assertEqual(TAG_COUNTS["Boss"], 134)

    def test_majorboss_is_a_subset_of_boss(self):
        """A major boss is a boss. Definitional, so this is a gate, not a preference (Alaric,
        2026-07-26).

        It did NOT hold before: 34 of 37 MajorBoss checks carried no Boss tag, and the 3 that did
        (Agheel, Magma Wyrm Makkar, Big Red Bear) held it only because their reward is not NAMED
        after a remembrance -- the leak that proves the old filter was a name match rather than a
        model. gen_data closes the set; this fails if anyone reopens it.
        """
        offenders = sorted(ap for ap, tags in LOCATION_TAGS.items()
                           if "MajorBoss" in tags and "Boss" not in tags)
        self.assertEqual(offenders, [], f"{len(offenders)} MajorBoss checks are not Boss: "
                                        f"{offenders[:8]} -- run build.ps1 -Greenfield if the "
                                        f"generated tables predate the closure")

    def test_remembrance_and_greatrune_are_major_boss(self):
        """Only a major boss drops a remembrance or a great rune, so every such check is MajorBoss.

        This is the ARITY half: one boss drops SEVERAL checks, and MajorBoss used to be keyed on
        method=="boss_arena" -- which records how the ROW was recovered, not what the drop is. For a
        boss with two drops the tag landed on whichever one came in through that path, splitting five
        bosses down the middle: Godrick's and Morgott's great runes missed it, and Mohg's, Malenia's
        and Radahn's remembrances missed it. Same shape as the Messmer's Kindling one-flag-many-lots
        bug.
        """
        offenders = sorted(ap for ap, tags in LOCATION_TAGS.items()
                           if ("Remembrance" in tags or "GreatRune" in tags)
                           and "MajorBoss" not in tags)
        self.assertEqual(offenders, [], f"{len(offenders)} Remembrance/GreatRune checks are not "
                                        f"MajorBoss: {offenders[:8]}")

    def test_guessed_regions_do_not_claim_certainty(self):
        """A check whose region is a GUESS must not present it as a fact.

        DEFAULTED_REGION_APS checks are already barred from carrying progression, but their NAMES
        asserted the region flatly -- Alaric hit this in playtest 2026-07-26 on
        'Caelid :: Deathroot - m60_45_39', which is on the Limgrave side of a genuine BORDER tile
        whose other 13 labelled checks are Caelid, so tile_pr answered with the majority and the
        label showed no doubt. 506 checks were in that state. gen_data now appends
        REGION_UNCONFIRMED; the region PREFIX is left intact so tracker grouping and the client's
        kick geometry are unaffected.

        CONTRIBUTING: make not-knowing louder than knowing. Refusing to answer beats answering
        confidently wrong -- and where we cannot refuse (the region is load-bearing for the kick),
        the next best thing is to answer while SAYING it is a guess.
        """
        name_of = {a: n for _r, locs in LOCATIONS.items() for (n, a, _f) in locs}
        naked = sorted(a for a in DEFAULTED_REGION_APS
                       if a in name_of and "(region unconfirmed)" not in name_of[a])
        self.assertEqual(naked, [], f"{len(naked)} guessed-region check(s) still claim their region "
                                    f"as fact, e.g. {[name_of[a] for a in naked[:3]]} -- run "
                                    f"build.ps1 -Greenfield if the tables predate the change")

    def test_confident_regions_are_not_marked(self):
        """The mirror: a check whose region is DERIVED must not wear the hedge. A marker on
        everything is the same as a marker on nothing."""
        name_of = {a: n for _r, locs in LOCATIONS.items() for (n, a, _f) in locs}
        wrong = sorted(a for a, n in name_of.items()
                       if "(region unconfirmed)" in n and a not in DEFAULTED_REGION_APS)
        self.assertEqual(wrong, [], f"{len(wrong)} check(s) are marked unconfirmed but their region "
                                    f"is derived, not guessed")

    def test_f510280_is_the_fringefolk_seed_not_stormhill(self):
        """Two DISTINCT Golden Seeds, and gen_data's comment used to conflate them.

        Alaric, in play 2026-07-26: "there's one at stormhill sapling, and there's one in the cave
        of knowledge on the ulcerated tree spirit behind the stonesword wall, but they're distinct".
        f400191 is the Stormhill sapling (map m60_41_38). f510280 is the Fringefolk one -- and the
        FLAG_REGION_OVERRIDE comment for it claimed "Stormhill golden sapling", which is a fact
        asserted in a comment with nothing to fail when it stopped being true.

        The Limgrave pin itself is right (play_region 18000 rides Limgrave's bundle); only the
        reason was invented. This pins the reason to the datum instead of to prose.
        """
        import csv as _csv
        import os as _os
        pkg = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
        path = _os.path.join(pkg, "check_maps.tsv")
        if not _os.path.isfile(path):
            self.skipTest("check_maps.tsv not installed beside the package -- oracle would run blind")
        # check_maps is ONE-TO-MANY by design (one check, N physical positions), so collect SETS --
        # a first-wins dict would silently hide a second position appearing later.
        maps = {}
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in _csv.DictReader((ln for ln in fh if not ln.lstrip().startswith("#")),
                                     delimiter="\t"):
                maps.setdefault((r.get("flag") or "").strip(), set()).add(
                    (r.get("map_id") or "").strip())
        self.assertTrue(maps, "check_maps.tsv parsed to ZERO rows -- an empty oracle is a failure")
        self.assertIn("m18_00", maps.get("510280", set()),
                      "f510280 is the Fringefolk Hero's Grave seed; if m18_00 is no longer among "
                      "its positions the Limgrave pin's justification no longer holds -- re-derive, "
                      "do not re-word the comment")
        self.assertIn("m60_41_38", maps.get("400191", set()),
                      "f400191 is the Stormhill sapling seed -- the OTHER one")
        self.assertFalse(maps.get("510280", set()) & maps.get("400191", set()),
                         "the two Golden Seeds now share a position -- the conflation this test "
                         "exists to prevent has come back")

    def test_major_boss_count(self):
        """37 -> 42: the five sibling drops the boss_arena keying had split off. Moves only when a
        major boss's drop set changes, or when a new Remembrance/GreatRune check appears -- the
        closure picks those up automatically, which is why this is a closure and not a hand list."""
        self.assertEqual(TAG_COUNTS["MajorBoss"], 42)

    def test_tags_are_valid_keys(self):
        # LOCATION_TAGS may carry INTERNAL tags (EniaShop) that are deliberately NOT user-selectable
        # important_location TYPES; those live in contract.SURFACE_EXCLUDE_TAGS. Valid == either.
        valid = set(_VALID) | SURFACE_EXCLUDE_TAGS
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


