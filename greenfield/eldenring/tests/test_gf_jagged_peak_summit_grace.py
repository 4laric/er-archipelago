"""#370: Jagged Peak Summit is an approach grace, not Bayle's post-fight arena grace."""

import csv
import math
import os

import pytest

pytest.importorskip("worlds.eldenring")

from worlds.eldenring.region_graces import REGION_GRACE_POINTS  # noqa: E402

try:
    from ._util import find_repo_root
except ImportError:
    from _util import find_repo_root


SUMMIT_GRACE = 76852
BAYLE_GRACE = 76853
BAYLE_DEFEAT_FLAG = 2054390800
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = find_repo_root(HERE)


def _rows(name):
    assert REPO is not None, "repo root is required for committed position evidence"
    with open(os.path.join(REPO, "greenfield", name), encoding="utf-8", newline="") as source:
        return list(csv.DictReader(
            (line for line in source if not line.startswith("#")), delimiter="\t"
        ))


def test_summit_is_geometrically_outside_bayles_arena_anchor() -> None:
    grace = next(row for row in _rows("item_grace_coords.tsv")
                 if row["kind"] == "grace" and int(row["key"]) == SUMMIT_GRACE)
    bayle = next(row for row in _rows("game_areas.tsv")
                 if int(row["defeat_flag"]) == BAYLE_DEFEAT_FLAG)

    assert grace["map_id"] == bayle["boss_map"] == "m61_54_39_00"
    delta = tuple(float(grace[axis]) - float(bayle["local_" + axis]) for axis in ("x", "y", "z"))
    assert abs(delta[2]) > 70.0, "summit grace lost its measured vertical separation from Bayle"
    assert math.dist((0.0, 0.0, 0.0), delta) > 100.0


def test_only_the_safe_summit_grace_is_granted() -> None:
    jagged = set(REGION_GRACE_POINTS["Jagged Peak"])
    assert SUMMIT_GRACE in jagged
    assert BAYLE_GRACE not in jagged


def test_bayles_actual_grace_remains_event_gated() -> None:
    rows = _rows("boss_gated_graces.tsv")
    bayle = next(row for row in rows if int(row["grace_flag"]) == BAYLE_GRACE)
    assert int(bayle["gate_flag"]) == BAYLE_DEFEAT_FLAG
    assert all(int(row["grace_flag"]) != SUMMIT_GRACE for row in rows)
