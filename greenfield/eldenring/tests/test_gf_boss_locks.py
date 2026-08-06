"""Phase 3 region-boss tests -- WorldTestBase. bossLocations must be scoped to kept regions and
reference real locations; sealed-region bosses drop out."""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring.boss_data import REGION_BOSSES  # noqa: E402

GAME = "Elden Ring"


class BossLocationsAll(WorldTestBase):
    game = GAME

    def test_boss_data_nonempty_and_valid(self):
        self.assertTrue(REGION_BOSSES, "boss_data.py must be generated")
        self.assertNotIn("Roundtable Hold", REGION_BOSSES, "bosses must map to real regions")

    def test_boss_locations_scoped_and_real(self):
        sd = self.world.fill_slot_data()
        bl = sd["bossLocations"]
        kept = set(self.world._kept())
        catalog = set(self.world.location_name_to_id.values())
        for region, ids in bl.items():
            self.assertIn(region, kept, f"boss region {region!r} not kept")
            for aid in ids:
                self.assertIn(aid, catalog, "boss ap-id must be a real location")


class BossLocationsSealed(WorldTestBase):
    game = GAME
    options = {"num_regions": 1}

    def test_sealed_boss_regions_excluded(self):
        # AUDIT 2026-08-04 (finding P2): this used to be `all(r in kept for r in bl)` -- a
        # quantifier over the OUTPUT of the function under test, vacuously true when the feature
        # is deleted (`boss_locs = {}` left all 35 referencing tests green). Assert keyset
        # EQUALITY against the INPUT table instead: the expectation is derived from REGION_BOSSES
        # + the region cut, never from slot_data, so an emptied or over-emitted bossLocations
        # cannot satisfy it. bossLocations carries the "Felled:" trophy map and, under boss_keys
        # mode-B, the per-boss `gate` deferral hint -- it emptying out is player-visible.
        bl = self.world.fill_slot_data()["bossLocations"]
        kept = set(self.world._kept())
        expected = {r for r in REGION_BOSSES if r in kept}
        sealed = set(REGION_BOSSES) - kept
        self.assertTrue(sealed,
                        "num_regions=1 kept every boss region -- the exclusion under test is not "
                        "being exercised at all (fixture rot)")
        self.assertTrue(expected,
                        "num_regions=1 should still keep a region with bosses; an empty "
                        "expectation would let an empty emission pass vacuously")
        self.assertEqual(set(bl), expected,
                         "bossLocations must be EXACTLY the kept rows of REGION_BOSSES -- "
                         "sealed regions out, every kept boss region in")


class DungeonSweepFlags(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "dungeon_sweep": "all"}

    def test_sweep_flags_present_and_scoped(self):
        from worlds.eldenring.boss_sweeps import DUNGEON_SWEEPS
        self.assertTrue(DUNGEON_SWEEPS, "boss_sweeps.py must be generated")
        sd = self.world.fill_slot_data()
        sw = sd["dungeonSweepFlags"]
        self.assertTrue(sw, "dungeon sweeps should be non-empty with dungeon_sweep=all")
        catalog = set(self.world.location_name_to_id.values())
        for fl_str, members in sw.items():
            self.assertEqual(fl_str, str(int(fl_str)), "sweep keys are stringified boss-defeat flags")
            for aid in members:
                self.assertIn(aid, catalog, "sweep member must be a real location")


class DungeonSweepOffSeed(WorldTestBase):
    """dungeon_sweep = "none" -- off must mean OFF: the sweep keys ABSENT, not present-and-empty.

    AUDIT 2026-08-04 (finding P1): the previous version of this test lived in DungeonSweepFlags
    (a dungeon_sweep="all" class) with a body of literally `pass`; replacing the emission gate in
    features/boss_locks.py::slot_data with `if True:` left all 57 tests across the four
    option-referencing files green, because nothing anywhere generated an OFF world and asked.
    Absent-not-empty is the contract (test_gf_slot_data_fixture.ALWAYS_KEYS excludes the sweep
    keys for exactly this reason): the client treats a missing key as feature-off, so a key that
    appears under dungeon_sweep=none re-arms whole-dungeon auto-grants for a player who explicitly
    disabled them -- silently, since the keys are required=False and validate_slot_data does not
    police unexpected OPTIONAL keys. Paired in test_gf_off_means_off.OFF_LEDGER.
    """
    game = GAME
    options = {"num_regions": 0, "dungeon_sweep": "none"}

    def test_sweeps_off_when_disabled(self):
        sd = self.world.fill_slot_data()
        # membership list, not assertNotIn: on failure assertNotIn dumps the ENTIRE slot_data
        # (hundreds of KB); the leaked-key list says everything that matters.
        leaked = [k for k in ("dungeonSweepFlags", "dungeonSweeps", "sweepLockGates") if k in sd]
        self.assertEqual(leaked, [],
                         "sweep keys emitted with dungeon_sweep=none -- the gate in "
                         "features/boss_locks.py::slot_data is not honoring the option; a player "
                         "who disabled sweeps would still get whole-dungeon auto-grants on boss "
                         "kills")
