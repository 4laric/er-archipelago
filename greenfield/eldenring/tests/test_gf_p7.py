"""Phase 7 tests -- deathlink + start_items + start-region-lock surfaces (WorldTestBase).

Defaults: startItems == [Torch, Spectral Steed Whistle, Flask of Crimson Tears, Flask of Cerulean
Tears] -- start_with_torch / start_with_steed / start_with_flasks all default ON. Each toggle drops
its item(s); all three off -> empty startItems. death_link=true -> death_link True.
start_with_region_lock (default OFF; the flagship yaml turns it on) precollects ONE random region
lock so a region is open from the start -- count-neutral (the pool then holds N-1 locks + 1 precollected).
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

GAME = "Elden Ring"
TORCH = 24000000
STEED = 0x40000000 | 130
CRIMSON = 0x40000000 | 1001
CERULEAN = 0x40000000 | 1051
# item_shuffle is FROZEN ON, so start_items also grants the pot VESSELS. Import them rather than
# re-hardcoding, so a new vessel can't silently drift this test.
from worlds.eldenring.features.start_items import (  # noqa: E402
    _CRACKED_POT_FULL_ID, _RITUAL_POT_FULL_ID, _PERFUME_BOTTLE_FULL_ID, _HEFTY_CRACKED_POT_FULL_ID,
)
VESSELS = (_CRACKED_POT_FULL_ID, _RITUAL_POT_FULL_ID, _PERFUME_BOTTLE_FULL_ID,
           _HEFTY_CRACKED_POT_FULL_ID)


class Phase7Defaults(WorldTestBase):
    game = GAME

    def test_death_link_default_bool(self):
        sd = self.world.fill_slot_data()
        self.assertIn("death_link", sd)
        self.assertIsInstance(sd["death_link"], bool)

    def test_start_items_default(self):
        si = self.world.fill_slot_data()["startItems"]
        self.assertEqual(si[:4], [TORCH, STEED, CRIMSON, CERULEAN])
        # item_shuffle is FROZEN ON (defaults.py), so start_items also grants pot VESSELS -- held
        # throwing-pot capacity == vessels held, else received pots overflow to storage unusable.
        self.assertTrue(all(x in VESSELS for x in si[4:]),
                        f"trailing startItems must be pot vessels, got {si[4:]}")


class Phase7DeathLinkOn(WorldTestBase):
    game = GAME
    options = {"death_link": True}

    def test_death_link_flag_true(self):
        self.assertIs(self.world.fill_slot_data()["death_link"], True)


class Phase7RegionLockOn(WorldTestBase):
    game = GAME
    options = {"start_with_region_lock": True}

    def test_exactly_one_region_lock_precollected(self):
        pre = [i.name for i in self.multiworld.precollected_items[self.player] if i.name.endswith(" Lock")]
        self.assertEqual(len(pre), 1, "exactly one region lock precollected when enabled")
        from ._util import world_item_names
        pool_locks = [n for n in world_item_names(self)
                      if n.endswith(" Lock") and n not in pre]
        kept = self.world._kept()
        self.assertEqual(sorted(pool_locks + pre), sorted(f"{r} Lock" for r in kept))
