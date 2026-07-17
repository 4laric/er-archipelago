"""Phase 7 tests -- deathlink + start_items + start-region-lock surfaces (WorldTestBase).

Defaults: startItems == [Torch, Flask of Crimson Tears, Flask of Cerulean Tears] + pot vessels --
the REPEATED (duplicate-harmless) path. The UNIQUE key items (Spectral Steed Whistle, Spirit
Calling Bell, Flask of Wondrous Physick) ride uniqueStartGrants as [FullID, obtainedFlag] pairs
instead: the client grants them only if the obtained-flag (60100/60110/60020) is unset, then sets
the flag with the grant -- so a reload/reconnect/pool-pickup can never double-grant. A unique
FullID appearing in BOTH lists would double-grant by construction; asserted disjoint here.
death_link=true -> death_link True.
start_with_region_lock (default OFF; the flagship yaml turns it on) precollects ONE random region
lock so a region is open from the start -- count-neutral (the pool then holds N-1 locks + 1 precollected).
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

GAME = "Elden Ring"
LANTERN = 0x40000000 | 2070    # goods 2070; replaces the old start Torch (hands-free pouch light)
STEED = 0x40000000 | 130       # goods 130,  obtained-flag 60100 (Torrent enable)
BELL = 0x40000000 | 8158       # goods 8158, obtained-flag 60110 (spirit summoning enable)
PHYSICK = 0x40000000 | 250     # goods 250,  acquisition flag 60020
WHETSTONE = 0x40000000 | 8590  # goods 8590, obtained-flag 60130 (Ashes of War enable)
CRIMSON = 0x40000000 | 1001
CERULEAN = 0x40000000 | 1051
UNIQUES = {STEED: 60100, BELL: 60110, PHYSICK: 60020, WHETSTONE: 60130}
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
        # The whistle + whetstone knife are uniqueStartGrants (below), not here; lantern + flasks
        # stay on the plain repeated path.
        self.assertEqual(si[:3], [LANTERN, CRIMSON, CERULEAN])
        # item_shuffle is FROZEN ON (defaults.py), so start_items also grants pot VESSELS -- held
        # throwing-pot capacity == vessels held, else received pots overflow to storage unusable.
        self.assertTrue(all(x in VESSELS for x in si[3:]),
                        f"trailing startItems must be pot vessels, got {si[3:]}")

    def test_unique_start_grants_default(self):
        # start_with_steed / bell / physick / whetstone (all frozen ON) emit the
        # [FullID, obtainedFlag] pairs the client's flag-idempotent unique-grant path consumes.
        sd = self.world.fill_slot_data()
        self.assertEqual(sd["uniqueStartGrants"],
                         [[STEED, 60100], [BELL, 60110], [PHYSICK, 60020], [WHETSTONE, 60130]])

    def test_unique_fullids_never_ride_the_repeated_path(self):
        # A unique FullID in plain startItems would be granted UNCONDITIONALLY next to the
        # flag-gated unique grant -- a guaranteed double. The two lists must stay disjoint.
        sd = self.world.fill_slot_data()
        si = set(sd["startItems"])
        for full_id in UNIQUES:
            self.assertNotIn(full_id, si,
                             f"unique FullID {full_id} must not also be in plain startItems")

    def test_unique_obtained_flags_not_in_start_graces(self):
        # The obtained-flags are the idempotency LATCH: set as part of the grant, never
        # unconditionally. 60100 riding startGraces (the 7165bf8 shape) would pre-set the latch
        # and make the whistle grant skip itself on a fresh save.
        graces = set(self.world.fill_slot_data().get("startGraces", []))
        for flag in UNIQUES.values():
            self.assertNotIn(flag, graces,
                             f"obtained-flag {flag} must not be set unconditionally in startGraces")


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
