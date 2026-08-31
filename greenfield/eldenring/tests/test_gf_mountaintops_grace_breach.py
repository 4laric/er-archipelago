"""#323: Leyndell must not light graces beyond its eastern exits.

The original report named Forbidden Lands and the graces at the Divine Tower of East Altus. The
generator now assigns all three from their measured grace ownership; pin that resolved state so a
future grace-table regen cannot quietly put a Mountaintops entrance back in Leyndell's bundle.
"""

import importlib.util
from pathlib import Path


REGION_GRACES = Path(__file__).parents[1] / "region_graces.py"


def _load_region_graces():
    spec = importlib.util.spec_from_file_location("_region_graces_323", REGION_GRACES)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_leyndell_cannot_grant_eastern_exit_graces() -> None:
    region_graces = _load_region_graces()
    reported = {73450, 73451, 76500}

    assert reported.isdisjoint(region_graces.REGION_GRACE_POINTS["Leyndell"])
    assert reported.isdisjoint(region_graces.REGION_GRACE_LANDMARKS["Leyndell"])


def test_reported_graces_stay_with_their_measured_regions() -> None:
    region_graces = _load_region_graces()

    # Both Divine Tower of East Altus graces carry Altus play-region 63003.
    assert {73450, 73451} <= set(region_graces.REGION_GRACE_POINTS["Altus"])
    assert 73450 in region_graces.REGION_GRACE_LANDMARKS["Altus"]

    # Forbidden Lands is beyond the Rold gate and is the Mountaintops entry landmark.
    assert 76500 in region_graces.REGION_GRACE_POINTS["Mountaintops of the Giants"]
    assert 76500 in region_graces.REGION_GRACE_LANDMARKS["Mountaintops of the Giants"]
