"""#324: East Altus Tower's m34_14 map presents as Leyndell, not raw pid bucket Altus."""
from ..data import LOCATIONS
from ..region_graces import REGION_GRACE_LANDMARKS, REGION_GRACE_POINTS


TOWER_FLAGS = {510740, 34147000, 34147010, 34147020, 34147720, 34147800, 34147810}


def _regions_by_flag():
    return {flag: region for region, checks in LOCATIONS.items()
            for _name, _ap_id, flag in checks}


def test_all_east_altus_tower_checks_are_leyndell():
    regions = _regions_by_flag()
    assert {flag: regions.get(flag) for flag in TOWER_FLAGS} == {
        flag: "Leyndell" for flag in TOWER_FLAGS
    }


def test_east_altus_tower_graces_ride_the_leyndell_lock():
    assert {73450, 73451} <= set(REGION_GRACE_POINTS["Leyndell"])
    assert 73450 in REGION_GRACE_LANDMARKS["Leyndell"]
    assert {73450, 73451}.isdisjoint(REGION_GRACE_POINTS.get("Altus", ()))
