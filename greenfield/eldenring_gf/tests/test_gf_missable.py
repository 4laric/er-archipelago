"""missable_locations tests -- matt-free missable tagging (deathroot + dragon-heart) + progression guard.

Pure-data: MISSABLE_LOCATIONS is the 10 Gurranq deathroot rewards + the 19 Dragon-Communion (Dragon-
Heart) purchases, every value a known source label, every ap_id a real location.
World: with the guard ON (default) every in-play missable location rejects an *advancement* item but
still accepts filler; post-fill no own-player progression lands on one. With the guard OFF, progression
is allowed again. A degenerate pool must still generate (fill-safety gate skips instead of FillError).
"""
import unittest
import pytest

from worlds.eldenring_gf.missable_locations import MISSABLE_LOCATIONS

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")
GAME = "Elden Ring (Greenfield)"


class MissableDataTests(unittest.TestCase):
    def test_count_and_split(self):
        self.assertEqual(len(MISSABLE_LOCATIONS), 29)
        vals = list(MISSABLE_LOCATIONS.values())
        self.assertEqual(vals.count("deathroot"), 10)
        self.assertEqual(vals.count("dragon_heart"), 19)

    def test_only_known_sources(self):
        self.assertTrue(set(MISSABLE_LOCATIONS.values()) <= {"deathroot", "dragon_heart"})

    def test_ap_ids_are_ints(self):
        for aid in MISSABLE_LOCATIONS:
            self.assertIsInstance(aid, int)


def _missable_in_play(world, mw):
    return [l for l in mw.get_locations(world.player)
            if getattr(l, "address", None) in MISSABLE_LOCATIONS]


class MissableGuardOn(WorldTestBase):
    game = GAME
    options = {"item_shuffle": True}  # real-item pool so there is progression to reject

    def _an_advancement_item(self):
        for i in self.multiworld.itempool:
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


class MissableGuardOff(WorldTestBase):
    game = GAME
    options = {"item_shuffle": True, "protect_missable_locations": False}

    def test_progression_allowed_when_off(self):
        missable = _missable_in_play(self.world, self.multiworld)
        self.assertGreater(len(missable), 0)
        prog = next((i for i in self.multiworld.itempool
                     if i.player == self.world.player and i.advancement), None)
        self.assertIsNotNone(prog)
        # a deathroot reward location is never tagged important, so with the guard off nothing
        # forbids progression there.
        deathroot = [l for l in missable if MISSABLE_LOCATIONS[l.address] == "deathroot"]
        self.assertTrue(any(l.item_rule(prog) for l in deathroot),
                        "with the guard off, a deathroot location should accept progression")


class MissableDegenerateSafe(WorldTestBase):
    game = GAME
    options = {"item_shuffle": False}  # degenerate pool -> gate skips, gen must not FillError

    def test_generates(self):
        self.assertTrue(self.multiworld.get_locations(self.world.player))
