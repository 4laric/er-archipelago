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
    # #768 withheld the Ashen Lock, so a 1-region `region_locks` seed has no findable goal item
    # and is refused at gen. The rune goal restores one WITHOUT changing the seed size this
    # class is about -- the sealing claim below is measured on one region, as before.
    options = {"num_regions": 1, "ending_condition": "great_runes"}
    # SEEDS: `num_regions: 1` really keeps ONE region since SPEC-ashen-capital-lock removed the
    # `auto` goal force-keep, and not every region has bosses -- so the fixture's own premise
    # ("a kept region with bosses") is now a property of the draw. Verified per run by walking a
    # fixed sequence, rather than pinned to a seed that happens to work: a data change that shifts
    # the pool moves the search, not the test. This class went red on CI and green in the sandbox
    # on the same commit, which is exactly what an unverified premise looks like.
    SEEDS = tuple(range(16))

    def _setup_seed_with_a_kept_boss_region(self):
        for seed in self.SEEDS:
            self.world_setup(seed=seed)
            if {r for r in REGION_BOSSES if r in set(self.world._kept())}:
                return seed
        self.fail("no seed in %r kept a region with bosses at num_regions=1, so the exclusion "
                  "under test went UNEXERCISED -- widen SEEDS, or REGION_BOSSES has shrunk"
                  % (self.SEEDS,))

    def test_sealed_boss_regions_excluded(self):
        self._setup_seed_with_a_kept_boss_region()
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


class FullAreaSweepsOneRegionSeed(WorldTestBase):
    """siffrin's case, generated (#1033). One region, `full_area_sweeps` on: every check the sweep
    tables hold for that region is in the payload, with nothing taken back out by the Progression
    Surface.

    A GENERATED world rather than a synthetic duck, because the unit tests in
    test_gf_dungeon_sweep_rungs already pin what the option DOES -- what they cannot see is whether
    the yaml key exists at all. An option that never reached `GFOptions` would leave them all green.
    """
    game = GAME
    options = {"num_regions": 1, "ending_condition": "great_runes",
               "dungeon_sweep": "bosses", "full_area_sweeps": True}

    def test_every_baked_member_is_paid_out(self):
        from worlds.eldenring.boss_sweeps import DUNGEON_SWEEPS
        sd = self.world.fill_slot_data()
        sw = sd.get("dungeonSweepFlags", {})
        self.assertTrue(sw, "a one-region seed at the widest rung must still emit sweeps")
        for fl_str, members in sw.items():
            baked = DUNGEON_SWEEPS[int(fl_str)]
            self.assertEqual(sorted(members), sorted(baked),
                             "trigger %s paid out %d of its %d baked members with "
                             "full_area_sweeps on -- something is still cutting"
                             % (fl_str, len(members), len(baked)))


class FullAreaSweepsOffSeed(WorldTestBase):
    """The control: the SAME seed shape with the option left at its default. The surface cut must
    still run, so at least one trigger pays out fewer members than the bake holds -- otherwise the
    class above passes for free on a corpus where nothing was ever being cut."""
    game = GAME
    options = {"num_regions": 1, "ending_condition": "great_runes",
               "dungeon_sweep": "bosses"}

    def test_the_surface_cut_still_runs(self):
        from worlds.eldenring.boss_sweeps import DUNGEON_SWEEPS
        from worlds.eldenring.features.boss_locks import sweep_surface_cut
        sd = self.world.fill_slot_data()
        sw = sd.get("dungeonSweepFlags", {})
        self.assertTrue(sw, "a one-region seed at the widest rung must still emit sweeps")
        cut = sweep_surface_cut(self.world)
        self.assertTrue(cut, "the DEFAULT Progression Surface claims four classes -- an empty cut "
                             "here means the default moved and this control is vacuous")
        for fl_str, members in sw.items():
            baked = set(DUNGEON_SWEEPS[int(fl_str)])
            self.assertEqual(set(members), baked - cut,
                             "trigger %s: the emitted members are not the bake minus this seed's "
                             "surface cut" % fl_str)
