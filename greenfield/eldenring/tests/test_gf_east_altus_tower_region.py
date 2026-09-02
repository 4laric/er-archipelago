"""#324: East Altus Tower needs both its Altus ground and its Leyndell approach."""

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
from worlds.eldenring.data import LOCATIONS  # noqa: E402
from worlds.eldenring.features import cross_region_access as cross_access  # noqa: E402
from worlds.eldenring.region_graces import REGION_GRACE_POINTS  # noqa: E402


TOWER_AP_IDS = {7770679, 7772342, 7772343, 7772344, 7772345, 7772346, 7772347}
TOWER_FLAGS = {510740, 34147000, 34147010, 34147020, 34147720, 34147800, 34147810}


def test_tower_checks_keep_their_measured_altus_ground():
    rows = {(ap_id, flag, region) for region, checks in LOCATIONS.items()
            for _name, ap_id, flag in checks if ap_id in TOWER_AP_IDS}
    assert {ap_id for ap_id, _flag, _region in rows} == TOWER_AP_IDS
    assert {flag for _ap_id, flag, _region in rows} == TOWER_FLAGS
    assert {region for _ap_id, _flag, region in rows} == {"Altus"}


def test_every_tower_check_requires_leyndell_and_sweep_does_not_bypass_it(monkeypatch):
    class AltusOnly:
        def _kept(self):
            return {"Altus"}

    monkeypatch.setattr(cross_access, "_swept_members", lambda _world: TOWER_AP_IDS)
    assert TOWER_AP_IDS <= set(cross_access.ALTERNATE_ACCESS)
    assert TOWER_AP_IDS.isdisjoint(cross_access.SWEEP_INDEPENDENT)
    assert {cross_access.OWNING_REGION[ap_id] for ap_id in TOWER_AP_IDS} == {"Altus"}
    assert not any(cross_access.location_available(AltusOnly(), ap_id)
                   for ap_id in TOWER_AP_IDS)


def test_tower_graces_are_not_in_any_single_lock_bundle():
    bundled = {grace for graces in REGION_GRACE_POINTS.values() for grace in graces}
    assert {73450, 73451}.isdisjoint(bundled)


class TestEastAltusTowerAccess(WorldTestBase):
    game = "Elden Ring"
    options = {"num_regions": 0, "dungeon_sweep": "bosses", "progression_surface": []}

    def test_altus_locations_still_require_leyndell_with_sweeps_enabled(self):
        state = self.multiworld.get_all_state(False)
        lock = next(item for item in self.multiworld.get_items()
                    if item.player == self.world.player and item.name == "Leyndell Lock")
        state.remove(lock)
        locations = {location.address: location
                     for location in self.multiworld.get_locations(self.player)}
        assert TOWER_AP_IDS <= set(locations)
        assert not any(locations[ap_id].can_reach(state) for ap_id in TOWER_AP_IDS)
