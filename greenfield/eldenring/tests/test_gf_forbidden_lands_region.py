"""#1075 -- the three pickups at Forbidden Lands belong behind the Rold gate together."""

from ..data import LOCATIONS

FLAGS = {1047517000, 1047517010, 1047517300}


def test_forbidden_lands_pickup_trio_is_mountaintops():
    found = {flag: region for region, rows in LOCATIONS.items()
             for (_name, _ap, flag) in rows if flag in FLAGS}
    assert found == {flag: "Mountaintops of the Giants" for flag in FLAGS}
