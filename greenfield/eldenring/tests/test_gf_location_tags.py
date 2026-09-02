"""Location TYPE tag facts -- the derived vocabulary the progression surface is built from.

Pure-data: every tag comes from item_name/method in gen_data._loc_tags (Remembrance excludes shop
duplicates -> ~25, not 50; Boss is closed under MajorBoss). These are DRIFT GUARDS on committed
counts and definitional relationships, not preferences -- gen_data cites
`test_gf_location_tags::test_f510280_is_the_fringefolk_seed_not_stormhill` as the guard on a region
claim it makes in a comment.

RENAMED from test_gf_important_locations.py (2026-08-02), when features/important_locations was
deleted. 🛑 The FEATURE went; these tests did NOT go with it. They were never about the enforcement
-- they are about the TAGS, which now serve features/progression_surface and the tracker. Deleting a
test file along with the feature that happened to live next to it is how a guard on unrelated data
disappears silently ([[deleting-a-test-file-is-not-deleting-a-mechanism]]). What WAS removed here is
only the two WorldTestBase suites that exercised the deleted item_rule.
"""
import unittest

from worlds.eldenring.data import LOCATIONS
from worlds.eldenring.location_tags import LOCATION_TAGS, TAG_COUNTS, DEFAULTED_REGION_APS
from worlds.eldenring.contract import (SURFACE_EXCLUDE_TAGS, SURFACE_CLASSES,
                                       SURFACE_DEFAULT_CLASSES)

# The classes these data guards are about. Was features/important_locations._DEFAULT; kept as a
# local constant so the tag assertions survive the option that used to name them.
_TAGGED = ["Remembrance", "Seedtree", "Church", "Boss", "Fragment", "Revered"]


class TagDataTests(unittest.TestCase):
    def test_all_default_tags_present(self):
        for t in _TAGGED:
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
        The effect was player-visible: `Boss` is a PLAYER-selectable location class, and it
        returned 95 checks with Godrick, Rennala, Radahn, Rykard, Mohg and Malenia all missing.
        gen_data now closes MajorBoss under Boss, so the delta is exactly the 39 majors that were
        outside it (34 already tagged MajorBoss + the 5 the arity fix newly tags). Post-closure, Boss
        is exactly the union of {Boss, MajorBoss, Remembrance, GreatRune} = 134.

        ⚠️ Same warning as above still applies to any FURTHER movement.
        """

        # 2026-08-04 (#249): +3. Placing the unplaced common-event rows gave THREE field
        # bosses a check for the first time -- their unique drop had no tile, so it was never a
        # location and the boss carried nothing: f530515 (Vyke's Dragonbolt), f530530 (Death
        # Ritual Spear), f530845 (Star-Lined Sword). Same shape as the GLOBAL_RECOVER entries
        # above them, reached by derivation instead of by hand. NOT a rebaseline: the three are
        # named, and each is a Boss tag that follows a NEW check, not a re-tag of an old one.
        # 137 -> 138 (2026-08-06): the Great Rune of the Unborn co-check (flag 197 lot 10181, #426): a co-check is the SAME physical acquisition as its primary and inherits its tags.
        # 138 -> 143 (2026-08-07, #249): FIVE Dragon Hearts. The de-dup re-key placed f530420
        # (Caelid), f530550 (Mountaintops), f530840 (Cerulean), f530860 (Gravesite) and f530945
        # (Scadu Altus) -- distinct dragon-boss rewards the ITEM-NAME rule had been collapsing
        # into one. Each is a Boss tag following a NEW check, not a re-tag of an old one.
        # ⭐⭐⭐ REBASELINED 143 -> 214 (2026-08-08): `Boss` WAS READING ONE OF TWO REWARD
        # MECHANISMS. Not a loosened predicate and not new datamining -- an attribution fix. A
        # boss's reward reaches the player three ways; measured over BOSS_HEALTHBARS' 244 rows,
        # 65 go through the common handler that carries both the banner and an `itemLotId`
        # (BOSS_DROP_FLAGS, which drove this tag), 104 through a reward flag the map emevd flips
        # (BOSS_REWARD_DEFEAT), and 75 through neither. The two sets are DISJOINT -- zero overlap --
        # so 104 bosses whose drops we had already datamined were simply never attributed.
        # BOSS_REWARD_TILE from that same table has been feeding _recover_tile and the
        # LegacyBoss/FieldBoss join for weeks; only the tag predicate was not reading it.
        # +71 checks, of which 62 were UNTAGGED FILLER before (5 Legendary, 3 Seedtree, 1 KeyItem
        # keep their tags and add Boss). Alaric called the size: "that sounds more like the correct
        # size, how many bosses there are".
        # 🛑 STILL NOT "every boss": the 75 covered by neither mechanism remain untagged, Dryleaf
        # Dane among them (his gear is an ASSET PICKUP -- common event 90005750, lot 107300, flag
        # 400730 -- which is a live check carrying no tags at all).
        # 214 -> 266 (2026-08-13, #191): the co-check allowlist widened from 5 hand-verified families
        # to the datamine_flag_lots policy, minting 286 sibling checks. 56 of them carry this
        # tag, on the SAME rule the flag-197 entry above states: a co-check is the same
        # physical acquisition as its primary and inherits its tags. Alaric confirmed the
        # reading 2026-08-13. NOT a rebaseline -- the tag definition is unchanged, the
        # population of checks grew.
        # 266 -> 267 (2026-08-16, #737): MARGIT. `Stormveil :: Talisman Pouch` (flag 60510) carried
        # NO tags at all -- not Boss, not anything -- because datamine_boss_reward_lots discarded its
        # row as "reward flag flipped by 2 maps". Margit's defeat event sets reward flag 9100
        # unconditionally; Morgott's ALSO sets it, behind `if (!EventFlag(9100))`, because they are
        # the same character and killing Morgott implies Margit. A guarded back-fill is not an
        # ownership claim, and the tool now says so. One check that always existed in the game gains
        # the tag it always deserved; the predicate did not move. (It also re-homes to Limgrave --
        # Stormhill is where you stand to fight him -- and its name loses a wrong "also granted by
        # Godrick the Grafted" attribution that came from the same missing join.)
        # 267 -> 269 (#1296): Senessax's two shared-flag reward lots are now two co-firing
        # locations. Both inherit the same boss-drop attribution as the one physical kill.
        self.assertEqual(TAG_COUNTS["Boss"], 269)

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

    def test_missable_checks_carrying_a_premium_tag_stay_few(self):
        """A missable check cannot host progression, so every premium-tagged one SHRINKS the surface.

        This began life as an important_locations guard: that feature said "reject filler" while
        missable_locations says "reject progression", and a check under both accepted NOTHING
        (f400191, the Stormhill Shack Golden Seed, 2026-07-26). important_locations is gone and that
        contradiction with it -- but the count still matters, for the opposite reason: a missable
        check carrying a surface class is one the progression surface cannot use.
        greenfield/surface_confidence.tsv prices exactly this in its `missable` column.

        BOUND REBASELINED 5 -> 7 (2026-08-02) WHEN THE MEASURED SET WIDENED. 🛑 Not data movement --
        NOTHING became missable. The old bound counted important_locations' six classes, which today
        catch 2; re-pointing the guard at SURFACE_DEFAULT_CLASSES added KeyItem, MajorBoss, GreatRune
        and ShopSlot, and those bring 5 more. Naming them, because a bare number is what let the old
        one drift past its own meaning -- all seven are `questline`-missable:

            7770656  KeyItem                Rold Medallion (Melina, after Morgott)
            7770665  KeyItem                Drawing-Room Key (Tanith)
            7770683  Seedtree               Golden Seed, Stormhill Shack (f400191, the original case)
            7770758  MajorBoss+Remembrance  Remembrance of the Lichdragon -- Fortissax
            7773838  KeyItem                Pureblood Knight's Medal
            7773839  KeyItem                Haligtree Secret Medallion (Right)
            7900000  KeyItem                Prayer Room Key (Queelign)

        FIVE OF THE SEVEN ARE KeyItem, which is why that class prices out at 47% eligible in
        surface_confidence.tsv -- the worst in the vocabulary, and it is in the shipped default
        surface. Cross-check: the artifact's missable column reads Remembrance 1 + Seedtree 1 +
        KeyItem 5 + MajorBoss 1 = 8, and Fortissax carries two of those classes -> 7 distinct. If
        those two ever disagree, one of them is lying.

        Not asserting the clash is EMPTY -- it legitimately is not, and pretending otherwise would
        re-hide it. Asserting it is KNOWN and small, so a jump gets looked at.
        """
        from worlds.eldenring.missable_locations import MISSABLE_LOCATIONS
        clash = sorted(a for a in MISSABLE_LOCATIONS
                       if set(SURFACE_DEFAULT_CLASSES) & set(LOCATION_TAGS.get(a, ())))
        # Not asserting the clash is EMPTY -- it legitimately is not, and pretending otherwise
        # would just re-hide it. Asserting it is KNOWN and small, so a jump gets looked at.
        self.assertLessEqual(len(clash), 7,
                             f"{len(clash)} missable locations now carry a DEFAULT SURFACE class "
                             f"({clash[:5]}). Each is barred from hosting progression, which is correct, "
                             f"but a jump means the hosting surface just shrank -- "
                             f"explain it before raising this bound.")

    def test_major_boss_count(self):
        """37 -> 42: the five sibling drops the boss_arena keying had split off. Moves only when a
        major boss's drop set changes, or when a new Remembrance/GreatRune check appears -- the
        closure picks those up automatically, which is why this is a closure and not a hand list."""
        # 42 -> 43 (2026-08-06): the Great Rune of the Unborn co-check (flag 197 lot 10181, #426): a co-check is the SAME physical acquisition as its primary and inherits its tags.
        # 43 -> 52 (2026-08-13, #191): the co-check allowlist widened from 5 hand-verified families
        # to the datamine_flag_lots policy, minting 286 sibling checks. 10 of them carry this
        # tag, on the SAME rule the flag-197 entry above states: a co-check is the same
        # physical acquisition as its primary and inherits its tags. Alaric confirmed the
        # reading 2026-08-13. NOT a rebaseline -- the tag definition is unchanged, the
        # population of checks grew.
        # ⭐⭐⭐ 52 -> 43 (2026-08-16, #737): THE ENTRY ABOVE APPLIED THE INHERITANCE RULE TO A TAG
        # THAT IS NOT ABOUT ACQUISITION, and this reverses that half of it. `Boss` and `Legendary`
        # answer HOW THIS CHECK WAS ACQUIRED, so a sibling lot on the same death flag inherits them
        # correctly -- that reading stands and `Boss` does not move here (266, unchanged; gen_data
        # CLOSURE 2b keeps it deliberately). `MajorBoss` answers IS THIS BOSS ON THE ROSTER, which is
        # a claim about an ENTITY, and inheritance turned two DLC field bosses' ARMOUR SETS into
        # major bosses: Dancer of Ranah's Hood/Dress/Bracer/Trousers (f530810) and Blackgaol Knight's
        # Helm/Armor/Gauntlets/Greaves (f530820), plus Magma Wyrm Makar's Dragon Heart (f510260).
        # Nine checks, three bosses. `MajorBoss` is in SURFACE_DEFAULT_CLASSES, so four pairs of
        # trousers were on the DEFAULT progression surface as major-boss checks.
        # NOT a rebaseline in the "ground truth got better" sense and not a looser predicate: it is
        # the same 43 entities the number read before the co-check allowlist widened, which is what
        # every other count derived from this tag was written against (contract.py's containment
        # comment still said 43). The arity is now gated at regen (gen_data: one primary per roster
        # entry, never zero, never two) and asserted host-side by
        # test_gf_progression_surface.test_one_major_boss_check_per_roster_entry, so it cannot come
        # back by accident.
        # ⭐⭐⭐ 43 -> 51 (2026-08-16, #737 direction 2): THE ROSTER IS DERIVED NOW. It was a hand
        # list -- MAJOR_BOSS_EXTRAS, "hand-picked field/evergaol/dragon bosses" -- and it was wrong
        # in both directions against matt's published roster. His UI says "Major bosses, INCLUDING
        # ALL ACHIEVEMENT BOSSES", and that phrase is the derivation: common.emevd's trophy event
        # fires AwardAchievement on a boss's DEFEAT FLAG, so "is this an achievement boss" is a join,
        # not an opinion (greenfield/achievement_bosses.tsv, 29 boss rows of 32 call sites).
        #   +11  the achievement bosses we had no MajorBoss check for: Red Wolf of Radagon, Godskin
        #        Noble, Godskin Duo, Valiant Gargoyles, Mimic Tear, Dragonkin Soldier of Nokstella,
        #        Royal Knight Loretta, Elemer of the Briar, Commander Niall, Ancestor Spirit, and
        #        Godfrey's Talisman Pouch. Nine of these are on matt's missing-ten list.
        #    -3  hand anchors with nothing left to anchor: Dancer of Ranah and Lamenter (Cerulean has
        #        its own Remembrance boss) and Godefroy (Altus has Elemer). Godefroy is one matt
        #        explicitly does not count, so the derivation and his roster agree here.
        # ⭐ MARGIT IS THE TENTH OF MATT'S TEN AND HE IS IN THIS NUMBER, after a correction worth
        # recording. He was first written off as "no boss-drop row exists in our data" and ledgered
        # as unresolvable -- Alaric: "margit's boss drop is stormveil talisman pouch". It is: m10_00's
        # `Defeat Margit` event flips reward flag 9100, which pays lot 10000 = `Talisman Pouch`.
        # datamine_boss_reward_lots had been discarding that row because Morgott's event ALSO sets
        # 9100, behind an `if (!EventFlag(...))` back-fill (same character, so killing Morgott implies
        # Margit). The fix is in the derivation, not here, and it nets to zero on this count: +Margit,
        # and -Agheel, whose Limgrave anchor became redundant the moment Margit's check re-homed
        # there. Agheel is the other entry matt does not count, so both are now gone -- neither for a
        # reason that had anything to do with matt. All 29 achievement bosses resolve; the
        # _ACH_NO_CHECK ledger is EMPTY and the test asserts it stays that way.
        # `Boss` does NOT move (266): Dancer of Ranah and Godefroy reached it only through CLOSURE 2
        # while they were wrongly major, and they are now in _BOSS_DROP_EXTRAS on their own evidence
        # (both have BOSS_HEALTHBARS rows; neither defeat flag is in the reward capture).
        # 51 -> 52 (#868): Great Wyrm Theodorix is Consecrated Snowfield's own progression anchor.
        # It remains FieldBoss-only, so this does not turn Snowfield into a terminal goal region.
        self.assertEqual(TAG_COUNTS["MajorBoss"], 52)

    def test_boss_geography_counts(self):
        """LegacyBoss / FieldBoss split `Boss` by WHERE the boss stands. Drift guard on both."""
        # 30 -> 31 (2026-08-06): the Great Rune of the Unborn co-check (flag 197 lot 10181, #426): a co-check is the SAME physical acquisition as its primary and inherits its tags.
        # 31 -> 42 (2026-08-08): the second reward mechanism (see TAG_COUNTS["Boss"] above). The
        # geography pass already joined via BOSS_REWARD_TILE, so these followed the Boss tag with no
        # further change -- which is the evidence the two halves were always meant to be one.
        # 42 -> 52 (2026-08-13, #191): the co-check allowlist widened from 5 hand-verified families
        # to the datamine_flag_lots policy, minting 286 sibling checks. 13 of them carry this
        # tag, on the SAME rule the flag-197 entry above states: a co-check is the same
        # physical acquisition as its primary and inherits its tags. Alaric confirmed the
        # reading 2026-08-13. NOT a rebaseline -- the tag definition is unchanged, the
        # population of checks grew.
        # 52 -> 53 (2026-08-16, #737): Margit's Talisman Pouch, the one check the catch-up fix
        # recovered (see TAG_COUNTS["Boss"] above). m10_00 is a legacy dungeon, so the geography pass
        # classes it the moment the reward join exists -- it followed the Boss tag with no further
        # change, which is the evidence the two halves are one.
        self.assertEqual(TAG_COUNTS["LegacyBoss"], 53)

        # 2026-08-04 (#249): +3. Placing the unplaced common-event rows gave THREE field
        # bosses a check for the first time -- their unique drop had no tile, so it was never a
        # location and the boss carried nothing: f530515 (Vyke's Dragonbolt), f530530 (Death
        # Ritual Spear), f530845 (Star-Lined Sword). Same shape as the GLOBAL_RECOVER entries
        # above them, reached by derivation instead of by hand. NOT a rebaseline: the three are
        # named, and each is a Boss tag that follows a NEW check, not a re-tag of an old one.
        # 87 -> 92 (2026-08-07, #249): the same five Dragon Hearts as TAG_COUNTS["Boss"] above.
        # 92 -> 95 (2026-08-08): same cause. Note the asymmetry -- +11 legacy, +3 field, and
        # **+57 UNDERGROUND** (3 -> 60), which carries NO tag. BOSS_REWARD_DEFEAT is the
        # MINI-DUNGEON reward family, so the bulk of it lands in catacombs/caves/tunnels. That
        # retires the stated reason for having no `Underground` class ("only THREE of them drop an
        # AP-tracked check"); gen_data's comment is corrected, and whether to OFFER the class is
        # left as a player-facing decision.
        # 95 -> 110 (2026-08-13, #191): the FieldBoss half of the same widening. 266 Boss = 52
        # legacy + 110 field + the rest; the split is unchanged, both halves grew with the check
        # population. Same rule: a co-check inherits its primary's tags.
        # 110 -> 112 (#1296): the regular and somber Senessax stones are distinct checks at the
        # same Jagged Peak field boss.
        self.assertEqual(TAG_COUNTS["FieldBoss"], 112)

    def test_geography_tags_are_subsets_of_boss_and_disjoint(self):
        """Definitional, so these are gates, not preferences: a legacy/field boss IS a boss, and no
        boss stands in two places."""
        leg = {ap for ap, t in LOCATION_TAGS.items() if "LegacyBoss" in t}
        fld = {ap for ap, t in LOCATION_TAGS.items() if "FieldBoss" in t}
        boss = {ap for ap, t in LOCATION_TAGS.items() if "Boss" in t}
        self.assertTrue(leg <= boss, sorted(leg - boss)[:8])
        self.assertTrue(fld <= boss, sorted(fld - boss)[:8])
        self.assertEqual(leg & fld, set(), "a check cannot be both legacy and field")
        self.assertLess(len(leg | fld), len(boss),
                        "some Boss checks are legitimately unclassified (majors + the dragon-heart "
                        "special-case); if this ever equals Boss, the join started guessing")

    def test_no_underground_class(self):
        """81 catacomb/cave/tunnel/minor-dungeon BOSSES exist; only THREE drop an AP-tracked check,
        because minidungeon rewards are arena chests, not the boss's own drop. So there is no
        `Underground` class and "exclude the catacombs" is not expressible. If this ever fails, the
        data changed and the decision is worth revisiting -- it is not a lint."""
        self.assertNotIn("Underground", SURFACE_CLASSES)
        self.assertNotIn("Underground", TAG_COUNTS)

    def test_tags_are_valid_keys(self):
        # LOCATION_TAGS may carry INTERNAL tags (EniaShop) that are deliberately NOT user-selectable
        # surface-selectable TYPES; those live in contract.SURFACE_EXCLUDE_TAGS. Valid == either.
        from ..contract import SURFACE_INTERNAL_TAGS
        valid = set(SURFACE_CLASSES) | SURFACE_EXCLUDE_TAGS | SURFACE_INTERNAL_TAGS
        for tags in LOCATION_TAGS.values():
            for t in tags:
                self.assertIn(t, valid)


class LegacyBossAbsorption(unittest.TestCase):
    """The CLASS is absorbed into MajorBoss; the TAG survives as roster fuel (2026-08-20).

    Retagging was tried first and refused by five tests: goal_locations, anchor eligibility and
    the roster-uniqueness law all read the raw MajorBoss tag as ROSTER identity. The absorption
    therefore lives at contract.has_class (SURFACE_CLASS_EXTRA_TAGS)."""

    def test_the_class_is_gone_but_the_tag_remains(self):
        self.assertNotIn("LegacyBoss", SURFACE_CLASSES)
        self.assertEqual(TAG_COUNTS.get("LegacyBoss"), 53)

    def test_selecting_majorboss_matches_a_legacy_only_row(self):
        from .. import contract
        # WITNESS both halves: a LegacyBoss-only row is ON the MajorBoss surface, and a row with
        # neither tag is not -- so the alias is doing work and the predicate did not go vacuous.
        self.assertTrue(contract.has_class(("LegacyBoss", "Boss"), {"MajorBoss"}))
        self.assertFalse(contract.has_class(("Boss",), {"MajorBoss"}))
        # The absorbed MajorBoss surface population: 52 native + 22 legacy-only = 74.
        absorbed = [ap for ap, ts in LOCATION_TAGS.items()
                    if contract.has_class(ts, {"MajorBoss"})]
        self.assertEqual(len(absorbed), 74)

    def test_every_legacy_row_also_carries_boss(self):
        # THE closure that lets _SWEEP_NEVER_TAGS drop "LegacyBoss": `Boss` is in that set, so
        # dropping the alias tag cuts nothing from the never-sweep guarantee. If a LegacyBoss row
        # ever stops carrying Boss, that reasoning is dead and this must fail.
        rows = [ap for ap, ts in LOCATION_TAGS.items() if "LegacyBoss" in ts]
        self.assertEqual(len(rows), 53)   # witness: the closure is over a real population
        for ap in rows:
            self.assertIn("Boss", LOCATION_TAGS[ap])


if __name__ == "__main__":
    unittest.main()
