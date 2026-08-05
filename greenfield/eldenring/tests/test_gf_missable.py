"""missable_locations tests -- matt-free missable tagging (deathroot + dragon-heart) + progression guard.

Pure-data: MISSABLE_LOCATIONS is the 10 Gurranq deathroot rewards + the 19 Dragon-Communion (Dragon-
Heart) purchases, every value a known source label, every ap_id a real location.
World: with the guard ON (default) every in-play missable location rejects an *advancement* item but
still accepts filler; post-fill no own-player progression lands on one. With the guard OFF, progression
is allowed again. A degenerate pool must still generate (fill-safety gate skips instead of FillError).
"""
import unittest
from ._util import world_items  # noqa: E402
import pytest

from worlds.eldenring.missable_locations import MISSABLE_LOCATIONS

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
GAME = "Elden Ring"


class MissableDataTests(unittest.TestCase):
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
        self.assertEqual(len(MISSABLE_LOCATIONS),
                         10 + len(alt) + vals.count("questline") + vals.count("gesture_award")
                         + vals.count("questline_item"))

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
            self.assertTrue(v in ("deathroot", "questline", "gesture_award", "questline_item")
                            or v.startswith("alt_currency:"),
                            "unknown missable source label %r" % v)

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

    def test_reject_progression_accept_filler(self):
        missable = _missable_in_play(self.world, self.multiworld)
        self.assertGreater(len(missable), 0, "expected in-play missable locations")
        prog = self._an_advancement_item()
        self.assertIsNotNone(prog, "expected an advancement item in the pool")
        filler = self.world.create_item(self.world.get_filler_item_name())
        self.assertFalse(filler.advancement)
        bad = [l for l in missable if l.item_rule(prog)]
        self.assertFalse(bad, f"{len(bad)} missable locations accept a progression item")
        # filler must still be allowed (missable != excluded; useful/filler is fine)
        self.assertTrue(all(l.item_rule(filler) for l in missable),
                        "missable locations should still accept filler")

    def test_no_progression_placed(self):
        for l in _missable_in_play(self.world, self.multiworld):
            if l.item is not None and l.item.player == self.world.player:
                self.assertFalse(l.item.advancement,
                                 f"progression landed on missable location {l.name}")


class MissableDegenerateSafe(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "item_shuffle": False}  # degenerate pool -> gate skips, gen must not FillError

    def test_generates(self):
        self.assertTrue(self.multiworld.get_locations(self.world.player))
