"""missable_locations tests -- generated missable tagging + progression/useful guard.

Pure-data: MISSABLE_LOCATIONS is the 10 Gurranq deathroot rewards + the 19 Dragon-Communion (Dragon-
Heart) purchases, every value a known source label, every ap_id a real location.
World: the default rejects progression and useful items but accepts filler. The legacy progression
mode rejects only progression, and off accepts both. A degenerate pool fails as an actionable
OptionError instead of silently disabling the selected protection.
"""
import unittest
from types import SimpleNamespace
from ._util import world_items  # noqa: E402
import pytest

from worlds.eldenring.tables.missable_locations import MISSABLE_LOCATIONS
from worlds.eldenring.features.missable_locations import (
    MissableLocationsFeature, ProtectMissableLocations)

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
GAME = "Elden Ring"


class MissableDataTests(unittest.TestCase):
    def test_quest_dispatch_is_not_a_first_talk_gift(self):
        """An award's collection latch says nothing about the caller's quest-state gate.

        Sellen dispatches the Kris handover only at state 3468; Millicent dispatches the
        Heirloom handover only at 4186. Both gift-table rows contain only a negative latch,
        which previously let these quest rewards host required progression.
        """
        from worlds.eldenring.tables.data import LOCATIONS

        for flag in (400101, 400320, 400600, 400722):
            ids = [aid for rows in LOCATIONS.values() for _, aid, fl in rows if fl == flag]
            self.assertTrue(ids, f"quest reward f{flag} disappeared instead of being protected")
            for aid in ids:
                self.assertEqual(MISSABLE_LOCATIONS.get(aid), "questline",
                                 f"f{flag}: caller's quest gate lost behind an award latch")

    def test_count_and_split(self):
        vals = list(MISSABLE_LOCATIONS.values())
        self.assertEqual(vals.count("deathroot"), 10)
        alt = [v for v in vals if v.startswith("alt_currency")]
        # 2026-07-24: this was pinned at 19 "dragon_heart". The predicate was costType == 1 and it
        # MISSED the DLC Grand Altar of Dragon Communion, whose Bayle incantations are costType 5 --
        # so they were eligible to carry REQUIRED progression. Widened to "not runes" (costType != 0).
        # The count grew because the INPUT PREDICATE got more correct, not looser: every added row is
        # a shop row bought with something other than runes. A floor, not a pin, so the next currency
        # FromSoft adds shows up as a pass rather than a rebaseline -- but a DROP is a lost currency
        # family and must fail.
        self.assertGreaterEqual(len(alt), 19,
                                "alt-currency missables SHRANK -- a currency family stopped matching")
        # 2026-07-26: 'gesture_award' joined the label set. EVERY gesture check now bars
        # progression (Alaric: "they're no progression surface. but belt and suspenders let's tag
        # em all missable"). The NPC/dialogue awards are questline-labelled; the WORLD pickups are
        # not questline-gated at all, so they carry their own label rather than a reason that is
        # false of them. The identity below is the real assertion: every entry has a known source.
        # 2026-08-04: 'questline_item' joined the label set -- a key item whose CHECK is an
        # ordinary world pickup (so none of the other sources is true of it) but whose ITEM feeds a
        # questline. Same reason gesture_award exists: the label is a claim about WHY, and calling
        # the Fingerslayer Blade's Nokron CHEST "questline" would be false about the mechanism.
        # This identity is the assertion that matters -- it fails the moment a label is minted
        # without being registered here, which is exactly how it caught this one.
        # 2026-09-08: 'multisite' and 'cross_region_prereq' joined the label set. Both used to be
        # emitted as "questline" because they are members of the same QUEST_GATED_FLAGS union -- but
        # a multi-site flag (e.g. 60510, set from m10_00 AND m11_00) is missable because the pickup
        # exists at several sites and the visit order decides which one still has it, and the
        # enabler class is missable because another REGION's flag gates the treasure. No questline
        # touches either. Same doctrine as gesture_award/questline_item: the label says WHY.
        self.assertEqual(len(MISSABLE_LOCATIONS),
                         10 + len(alt) + vals.count("questline") + vals.count("gesture_award")
                         + vals.count("questline_item") + vals.count("multisite")
                         + vals.count("cross_region_prereq"))

    def test_both_dragon_communion_currencies_are_tagged(self):
        """The bug this guards: ONE altar can mix cost types. Caelid's shelf is costType 1, the DLC
        Grand Altar mixes 1 and 5 (believed Bayle's Heart -- a distinct, scarcer currency). Tagging
        one family and not the other is how a limited-consumable purchase became an ordinary check."""
        kinds = {v for v in MISSABLE_LOCATIONS.values() if v.startswith("alt_currency")}
        self.assertGreaterEqual(len(kinds), 2,
                                "only one alt-currency cost type is tagged: %r -- the DLC altar's "
                                "second currency is missing again" % sorted(kinds))

    def test_only_known_sources(self):
        for v in set(MISSABLE_LOCATIONS.values()):
            self.assertTrue(v in ("deathroot", "questline", "gesture_award", "questline_item",
                                  "multisite", "cross_region_prereq")
                            or v.startswith("alt_currency:"),
                            "unknown missable source label %r" % v)

    def test_multisite_label_is_not_questline(self):
        """The defect this guards: the five missable derivations were unioned into one set and the
        whole union was emitted as "questline", so a flag set from several maps claimed a quest
        gated it. The label is a claim about the mechanism -- if the multi-site class exists at all
        it must say so. (Those checks stay MISSABLE on purpose: tagging costs a filler slot, being
        wrong costs an unwinnable seed.)"""
        self.assertIn("multisite", set(MISSABLE_LOCATIONS.values()),
                      "no check carries the multisite reason -- either the screen stopped "
                      "contributing or its members collapsed back into 'questline'")

    def test_ap_ids_are_ints(self):
        for aid in MISSABLE_LOCATIONS:
            self.assertIsInstance(aid, int)


def _missable_in_play(world, mw):
    return [l for l in mw.get_locations(world.player)
            if getattr(l, "address", None) in MISSABLE_LOCATIONS]


class MissableGuardOn(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "item_shuffle": True}  # real-item pool so there is progression to reject

    def _an_advancement_item(self):
        for i in world_items(self):
            if i.player == self.world.player and i.advancement:
                return i
        return None

    def _a_useful_item(self):
        from BaseClasses import ItemClassification
        for i in world_items(self):
            if i.player == self.world.player and i.classification & ItemClassification.useful:
                return i
        return None

    def test_reject_progression_and_useful_accept_filler(self):
        missable = _missable_in_play(self.world, self.multiworld)
        self.assertGreater(len(missable), 0, "expected in-play missable locations")
        prog = self._an_advancement_item()
        self.assertIsNotNone(prog, "expected an advancement item in the pool")
        useful = self._a_useful_item()
        self.assertIsNotNone(useful, "expected a useful item in the pool")
        filler = self.world.create_item(self.world.get_filler_item_name())
        self.assertFalse(filler.advancement)
        bad = [l for l in missable if l.item_rule(prog)]
        self.assertFalse(bad, f"{len(bad)} missable locations accept a progression item")
        bad = [l for l in missable if l.item_rule(useful)]
        self.assertFalse(bad, f"{len(bad)} missable locations accept a useful item")
        # Filler must still be allowed: missable does not mean excluded.
        self.assertTrue(all(l.item_rule(filler) for l in missable),
                        "missable locations should still accept filler")

    def test_no_progression_placed(self):
        for l in _missable_in_play(self.world, self.multiworld):
            if l.item is not None and l.item.player == self.world.player:
                from BaseClasses import ItemClassification
                barred = ItemClassification.progression | ItemClassification.useful
                self.assertFalse(l.item.classification & barred,
                                 f"progression/useful item landed on missable location {l.name}")


class MissableReservationLeavesTheEarlyGuarantee(WorldTestBase):
    """THE MOTIVATING CASE (CONTRIBUTING rule 11). `reserve_filler` runs in pre_fill, BEFORE AP's
    early-items pass, and drew from every filler copy in the pool. On a 1-region seed (seed 1044,
    2026-09-06) it locked both Somber Smithing Stone [2] onto two Ashen Capital sweep checks --
    sphere 1 -- so `filler_budget`'s "2 reachable from the start" guarantee, which had counted those
    very copies, delivered 0 with no warning. The declared copies must survive pre_fill in the pool
    so AP's local_early_items pass has something to place."""
    game = GAME
    options = {"num_regions": 1, "num_regions_order": "vanilla_order", "item_shuffle": True,
               "enable_dlc": True, "ending_condition": "great_runes"}

    def test_declared_early_copies_are_still_in_the_pool_after_pre_fill(self):
        from collections import Counter
        early = dict(self.multiworld.local_early_items[self.world.player])
        self.assertTrue(early, "no early guarantee was declared -- the premise of this test is gone")
        held = Counter(i.name for i in self.multiworld.itempool if i.player == self.world.player)
        short = {nm: (n, held[nm]) for nm, n in early.items() if held[nm] < n}
        self.assertFalse(short, "pre_fill spent early-guaranteed copies before AP's early pass "
                                "could place them (name: (declared, left in pool)): %r" % (short,))


class MissableProgressionOnly(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "item_shuffle": True,
               "protect_missable_locations": "progression"}

    def test_legacy_mode_rejects_progression_but_accepts_useful(self):
        from BaseClasses import ItemClassification
        missable = _missable_in_play(self.world, self.multiworld)
        progression = next(i for i in world_items(self) if i.advancement)
        useful = next(i for i in world_items(self)
                      if i.classification & ItemClassification.useful and not i.advancement)
        self.assertTrue(all(not l.item_rule(progression) for l in missable))
        self.assertTrue(all(l.item_rule(useful) for l in missable))


class MissableOff(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "item_shuffle": True,
               "protect_missable_locations": "off"}

    def test_off_installs_no_additional_rule(self):
        # Some missable checks have independent bars, so probing them all with one progression item
        # would test the rest of the bar stack rather than this option. Off's contract is that this
        # feature leaves the existing rules untouched.
        self.assertTrue(_missable_in_play(self.world, self.multiworld))
        option = SimpleNamespace(value=ProtectMissableLocations.option_off, current_key="off")
        before = {id(l): l.item_rule for l in _missable_in_play(self.world, self.multiworld)}
        self.world.options.protect_missable_locations = option
        MissableLocationsFeature().set_rules(self.world)
        after = {id(l): l.item_rule for l in _missable_in_play(self.world, self.multiworld)}
        self.assertEqual(before, after)


class MissableOptionMigrationTests(unittest.TestCase):
    def test_default_is_progression_and_useful(self):
        self.assertEqual(2, ProtectMissableLocations.default)

    def test_legacy_booleans_remain_meaningful(self):
        self.assertEqual(2, ProtectMissableLocations.from_any(True).value)
        self.assertEqual(0, ProtectMissableLocations.from_any(False).value)

    def test_documented_plus_spelling_resolves(self):
        self.assertEqual(2, ProtectMissableLocations.from_any("progression+useful").value)

    def test_all_levels_resolve(self):
        for value in (0, 1, 2):
            self.assertEqual(value, ProtectMissableLocations.from_any(value).value)

    def test_insufficient_filler_fails_loudly(self):
        from Options import OptionError

        ap_id = next(iter(MISSABLE_LOCATIONS))
        location = SimpleNamespace(address=ap_id, item_rule=lambda _item: True)
        multiworld = SimpleNamespace(
            itempool=[], get_locations=lambda _player: [location])
        option = SimpleNamespace(
            value=ProtectMissableLocations.option_progression_and_useful,
            current_key="progression_and_useful")
        world = SimpleNamespace(
            player=1, multiworld=multiworld,
            options=SimpleNamespace(protect_missable_locations=option))

        with self.assertRaisesRegex(OptionError, "supplies only 0"):
            MissableLocationsFeature().set_rules(world)
