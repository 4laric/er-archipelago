"""#323: Leyndell must not light graces beyond its eastern exits.

The original report named Forbidden Lands and the graces at the Divine Tower of East Altus. The
generator now assigns all three from their measured grace ownership; pin that resolved state so a
future grace-table regen cannot quietly put a Mountaintops entrance back in Leyndell's bundle.
"""

import pytest

pytest.importorskip("worlds.eldenring")

from worlds.eldenring.region_graces import (  # noqa: E402
    REGION_GRACE_LANDMARKS,
    REGION_GRACE_POINTS,
)


def test_leyndell_cannot_grant_eastern_exit_graces() -> None:
    reported = {73450, 73451, 76500}

    assert reported.isdisjoint(REGION_GRACE_POINTS["Leyndell"])
    assert reported.isdisjoint(REGION_GRACE_LANDMARKS["Leyndell"])


def test_reported_graces_stay_with_their_measured_regions() -> None:
    # Both Divine Tower of East Altus graces carry Altus play-region 63003.
    assert {73450, 73451} <= set(REGION_GRACE_POINTS["Altus"])
    assert 73450 in REGION_GRACE_LANDMARKS["Altus"]

    # Forbidden Lands is beyond the Rold gate and is the Mountaintops entry landmark.
    assert 76500 in REGION_GRACE_POINTS["Mountaintops of the Giants"]
    assert 76500 in REGION_GRACE_LANDMARKS["Mountaintops of the Giants"]
