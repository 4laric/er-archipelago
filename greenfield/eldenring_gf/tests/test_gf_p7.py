"""Phase 7 tests -- deathlink + start_items feature surfaces (WorldTestBase).

Defaults: slot_data carries a bool death_link and startItems == [24000000, 1073741954]
(the Torch FullID + the Spectral Steed Whistle FullID; both start_with_torch and start_with_steed
default ON). start_with_torch=false drops the Torch; start_with_steed=false drops the whistle;
both off -> empty startItems. death_link=true -> death_link True.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")

GAME = "Elden Ring (Greenfield)"
TORCH_FULL_ID = 24000000
STEED_WHISTLE_FULL_ID = 0x40000000 | 130  # Spectral Steed Whistle = 1073741954


class Phase7Defaults(WorldTestBase):
    game = GAME

    def test_death_link_default_bool(self):
        sd = self.world.fill_slot_data()
        self.assertIn("death_link", sd)
        self.assertIsInstance(sd["death_link"], bool)

    def test_start_items_default_has_torch_and_steed(self):
        sd = self.world.fill_slot_data()
        self.assertEqual(sd["startItems"], [TORCH_FULL_ID, STEED_WHISTLE_FULL_ID])


class Phase7TorchOff(WorldTestBase):
    game = GAME
    options = {"start_with_torch": False}

    def test_no_torch_when_disabled(self):
        # torch off, steed still on (default) -> only the whistle remains.
        sd = self.world.fill_slot_data()
        self.assertEqual(sd["startItems"], [STEED_WHISTLE_FULL_ID])


class Phase7SteedOff(WorldTestBase):
    game = GAME
    options = {"start_with_steed": False}

    def test_no_steed_when_disabled(self):
        # steed off, torch still on (default) -> only the Torch remains.
        sd = self.world.fill_slot_data()
        self.assertEqual(sd["startItems"], [TORCH_FULL_ID])


class Phase7BothOff(WorldTestBase):
    game = GAME
    options = {"start_with_torch": False, "start_with_steed": False}

    def test_empty_start_items_when_both_disabled(self):
        sd = self.world.fill_slot_data()
        self.assertEqual(sd["startItems"], [])


class Phase7DeathLinkOn(WorldTestBase):
    game = GAME
    options = {"death_link": True}

    def test_death_link_flag_true(self):
        sd = self.world.fill_slot_data()
        self.assertIs(sd["death_link"], True)
