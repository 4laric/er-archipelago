"""region_sweep (SPEC-region-completion-release.md): the region's own gating boss additionally
releases the rest of that region's checks, on top of whatever design-1 sweep already exists on the
same trigger flag. See features/boss_locks.region_sweep_groups.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

GAME = "Elden Ring"
SEED = 4242


class _FakeToggle:
    def __init__(self, value):
        self.value = int(bool(value))


class _FakeChoice:
    def __init__(self, current_key):
        self.current_key = current_key


class _FakeOptionSet:
    def __init__(self, value=()):
        self.value = set(value)


class _FakeTables:
    def __init__(self, locations, hub="HUB"):
        self.locations = locations
        self.hub = hub


class _FakeWorld:
    """Minimal duck for region_sweep_groups: options + tables.locations + _kept()."""
    def __init__(self, kept, locations, region_sweep=True, dungeon_sweep_key="bosses",
                 surface=(), full_area=False, hub="HUB"):
        self._kept_regions = set(kept)
        self.options = type("_O", (), {
            "region_sweep": _FakeToggle(region_sweep),
            "dungeon_sweep": _FakeChoice(dungeon_sweep_key),
            "progression_surface": _FakeOptionSet(surface),
            "full_area_sweeps": _FakeToggle(full_area),
        })()
        self.tables = _FakeTables(locations, hub=hub)

    def _kept(self):
        return set(self._kept_regions)


def test_region_sweep_off_yields_nothing():
    from worlds.eldenring.features.boss_locks import region_sweep_groups
    locations = {"Stormveil": [("a", 1, 100), ("b", 2, 101)]}
    world = _FakeWorld(kept={"Stormveil"}, locations=locations, region_sweep=False)
    assert region_sweep_groups(world, region_gating_boss={"Stormveil": 10000800}) == {}


def test_region_sweep_grants_every_region_member_not_never_tagged():
    from worlds.eldenring.features.boss_locks import region_sweep_groups
    locations = {
        "Stormveil": [
            ("filler check", 7770100, 100),
            ("Godrick's Great Rune", 7770001, 10000800),   # GreatRune -- never taken
            ("a shop slot", 7770200, 200),                 # Shop -- never taken
        ],
    }
    tags = {7770001: ["GreatRune", "MajorBoss", "Boss"], 7770200: ["Shop"]}
    world = _FakeWorld(kept={"Stormveil"}, locations=locations)
    groups = region_sweep_groups(world, location_tags=tags,
                                  region_gating_boss={"Stormveil": 10000800})
    assert groups == {10000800: [7770100]}, (
        "region_sweep must grant the region's plain filler and hold back its own gating boss's "
        "Great Rune -- got %r" % groups)


def test_region_sweep_never_grants_a_region_not_kept():
    from worlds.eldenring.features.boss_locks import region_sweep_groups
    locations = {"Stormveil": [("a", 7770100, 100)], "Liurnia": [("b", 7770101, 101)]}
    world = _FakeWorld(kept={"Stormveil"}, locations=locations)
    groups = region_sweep_groups(
        world, location_tags={}, region_gating_boss={"Stormveil": 10000800, "Liurnia": 1035500800})
    assert groups == {10000800: [7770100]}, (
        "a region this seed did not keep must never contribute a group: %r" % groups)


def test_region_sweep_respects_the_progression_surface_cut():
    """Same per-seed cut every other sweep obeys -- full_area_sweeps controls it identically."""
    from worlds.eldenring.features.boss_locks import region_sweep_groups
    locations = {"Stormveil": [("a golden seed", 7770100, 100), ("filler", 7770101, 101)]}
    tags = {7770100: ["Seedtree"]}
    cut_world = _FakeWorld(kept={"Stormveil"}, locations=locations, surface=("Seedtree",))
    assert region_sweep_groups(
        cut_world, location_tags=tags, region_gating_boss={"Stormveil": 10000800}
    ) == {10000800: [7770101]}
    uncut_world = _FakeWorld(kept={"Stormveil"}, locations=locations, surface=("Seedtree",),
                              full_area=True)
    got = set(region_sweep_groups(
        uncut_world, location_tags=tags, region_gating_boss={"Stormveil": 10000800})[10000800])
    assert got == {7770100, 7770101}, (
        "full_area_sweeps must turn the surface cut off for region_sweep exactly as it does for "
        "design-1 sweeps -- got %r" % got)


def test_region_sweep_never_gates_on_a_dead_boss():
    """§2's build-time check: no REGION_GATING_BOSS value may be a runtime-skipped (unspawned) boss,
    or that region could never complete."""
    from worlds.eldenring import contract
    from worlds.eldenring.tables.region_gating_boss import REGION_GATING_BOSS
    assert REGION_GATING_BOSS, "REGION_GATING_BOSS is empty -- the scan below would vacuously pass"
    skips = contract.runtime_sweep_skips()
    bad = {region: fl for region, fl in REGION_GATING_BOSS.items() if fl in skips}
    assert not bad, "region(s) gated on a dead/unspawned boss, can never complete: %r" % bad


def test_region_sweep_covers_every_named_region():
    """Every region SWEEP_REGION knows about must have a REGION_GATING_BOSS entry, or region_sweep
    silently does nothing there."""
    from worlds.eldenring.tables.boss_sweeps import SWEEP_REGION
    from worlds.eldenring.tables.region_gating_boss import REGION_GATING_BOSS
    assert SWEEP_REGION, "SWEEP_REGION is empty -- the scan below would vacuously pass"
    missing = sorted(set(SWEEP_REGION.values()) - set(REGION_GATING_BOSS))
    assert not missing, "region(s) with sweep triggers but no REGION_GATING_BOSS entry: %s" % missing


def test_region_sweep_gating_bosses_are_real_flags():
    """Every REGION_GATING_BOSS flag must be a real, named boss (boss_healthbars), not a typo'd id."""
    from worlds.eldenring.tables.boss_healthbars import BOSS_HEALTHBARS
    from worlds.eldenring.tables.region_gating_boss import REGION_GATING_BOSS
    assert REGION_GATING_BOSS, "REGION_GATING_BOSS is empty -- the scan below would vacuously pass"
    unknown = {region: fl for region, fl in REGION_GATING_BOSS.items() if fl not in BOSS_HEALTHBARS}
    assert not unknown, "REGION_GATING_BOSS flag(s) with no boss_healthbars entry: %r" % unknown


def test_region_sweep_off_by_default_matches_head():
    """The option must default OFF so an existing seed's slot data is untouched by this feature."""
    from worlds.eldenring.features.boss_locks import RegionSweep
    assert RegionSweep.default == 0, "region_sweep must default off -- this feature is opt-in"


def test_region_sweep_composes_with_dungeon_sweep_none():
    """region_sweep is a modifier on top of Dungeon Sweep, not a trigger of its own: with
    dungeon_sweep: none the whole sweep block never runs, so region_sweep must not either."""

    class _T(WorldTestBase):
        game = GAME

    t = _T("runTest")
    t.options = {"dungeon_sweep": "none", "region_sweep": True}
    t.world_setup(SEED)
    flags = t.world.fill_slot_data().get("dungeonSweepFlags") or {}
    assert flags == {}, (
        "dungeon_sweep: none must still grant nothing even with region_sweep on -- got %d group(s)"
        % len(flags))
