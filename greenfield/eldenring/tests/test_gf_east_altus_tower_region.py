"""#324: the East Altus Tower IS Leyndell -- checks, sweep, kick bucket and route."""

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
from worlds.eldenring.tables.data import LOCATIONS  # noqa: E402
from worlds.eldenring.features import cross_region_access as cross_access  # noqa: E402
from worlds.eldenring.tables.region_graces import REGION_GRACE_POINTS  # noqa: E402
from worlds.eldenring.tables.region_play_ids import REGION_PLAY_IDS  # noqa: E402
from worlds.eldenring.tables.boss_sweeps import SWEEP_ARENA_REGION, SWEEP_REGION  # noqa: E402


TOWER_AP_IDS = {7770679, 7772342, 7772343, 7772344, 7772345, 7772346, 7772347}
TOWER_FLAGS = {510740, 34147000, 34147010, 34147020, 34147720, 34147800, 34147810}


def test_tower_checks_are_leyndells():
    rows = {(ap_id, flag, region) for region, checks in LOCATIONS.items()
            for _name, ap_id, flag in checks if ap_id in TOWER_AP_IDS}
    assert {ap_id for ap_id, _flag, _region in rows} == TOWER_AP_IDS
    assert {flag for _ap_id, flag, _region in rows} == TOWER_FLAGS
    assert {region for _ap_id, _flag, region in rows} == {"Leyndell"}


def test_the_tower_no_longer_needs_a_cross_region_rule():
    """Owning the region IS the route now. A leftover ALTERNATE_ACCESS row would double-count:
    the census subtracts a cross-region check whose owner is kept but whose route is not, and for
    these checks owner and route became the same region on 2026-09-07."""
    assert TOWER_AP_IDS.isdisjoint(cross_access.ALTERNATE_ACCESS)
    assert TOWER_AP_IDS.isdisjoint(cross_access.OWNING_REGION)
    assert TOWER_AP_IDS.isdisjoint(cross_access.SWEEP_INDEPENDENT)


def test_the_tower_bucket_and_its_sweep_moved_with_the_checks():
    """The kick/scaling geometry must follow the checks, or a Leyndell-lock holder is ejected at
    the tower he can legitimately reach and an Altus-only holder is admitted to one he cannot."""
    assert 34140 in REGION_PLAY_IDS["Leyndell"]
    assert 34140 not in REGION_PLAY_IDS.get("Altus", ())
    assert SWEEP_REGION[34140850] == "Leyndell"
    assert SWEEP_ARENA_REGION[34140850] == "Leyndell"


def test_tower_graces_are_not_in_any_single_lock_bundle():
    bundled = {grace for graces in REGION_GRACE_POINTS.values() for grace in graces}
    assert {73450, 73451}.isdisjoint(bundled)


class TestEastAltusTowerAccess(WorldTestBase):
    game = "Elden Ring"
    options = {"num_regions": 0, "dungeon_sweep": "bosses", "progression_surface": []}

    def test_tower_locations_still_require_leyndell_with_sweeps_enabled(self):
        state = self.multiworld.get_all_state(False)
        lock = next(item for item in self.multiworld.get_items()
                    if item.player == self.world.player and item.name == "Leyndell Lock")
        state.remove(lock)
        locations = {location.address: location
                     for location in self.multiworld.get_locations(self.player)}
        assert TOWER_AP_IDS <= set(locations)
        assert not any(locations[ap_id].can_reach(state) for ap_id in TOWER_AP_IDS)
