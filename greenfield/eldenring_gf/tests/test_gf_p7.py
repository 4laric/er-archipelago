"""Phase 7 tests -- deathlink + start_items feature surfaces (WorldTestBase).

Defaults: slot_data carries a bool death_link and startItems == [24000000] (the Torch FullID).
start_with_torch=false -> empty startItems; death_link=true -> death_link True.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")

GAME = "Elden Ring (Greenfield)"
TORCH_FULL_ID = 24000000


class Phase7Defaults(WorldTestBase):
    game = GAME

    def test_death_link_default_bool(self):
        sd = self.world.fill_slot_data()
        self.assertIn("death_link", sd)
        self.assertIsInstance(sd["death_link"], bool)

    def test_start_items_default_has_torch(self):
        sd = self.world.fill_slot_data()
        self.assertEqual(sd["startItems"], [TORCH_FULL_ID])


class Phase7TorchOff(WorldTestBase):
    game = GAME
    options = {"start_with_torch": False}

    def test_no_torch_when_disabled(self):
        sd = self.world.fill_slot_data()
        self.assertEqual(sd["startItems"], [])


class Phase7DeathLinkOn(WorldTestBase):
    game = GAME
    options = {"death_link": True}

    def test_death_link_flag_true(self):
        sd = self.world.fill_slot_data()
        self.assertIs(sd["death_link"], True)
