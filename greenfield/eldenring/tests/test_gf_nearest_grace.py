# -*- coding: utf-8 -*-
"""Pure tests for tools/build_nearest_grace.py -- the nearest-grace math (layer 4 producer).
Synthetic coordinates, no artifacts. Run: python3 eldenring/tests/test_gf_nearest_grace.py"""
import importlib.util
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))


def _find_up(rel):
    """Search UP from the test dir for `rel`. A fixed dirname^3 lands on `_ap` (not the repo root) when
    the world is INSTALLED and CI runs from `_ap/worlds/eldenring/tests`; `_ap` lives inside the repo,
    so a walk-up still reaches the source `tools/build_nearest_grace.py`. None when the source tree
    isn't present (a bare player install)."""
    d = HERE
    for _ in range(10):
        cand = os.path.join(d, rel)
        if os.path.exists(cand):
            return cand
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    return None


TOOL = _find_up(os.path.join("tools", "build_nearest_grace.py"))
if TOOL is None:
    pytest.skip("tools/build_nearest_grace.py not found (source tree absent) -- source-tree tool test",
                allow_module_level=True)


def _load():
    spec = importlib.util.spec_from_file_location("build_nearest_grace", TOOL)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


bng = _load()

COORDS = [
    "kind\tkey\tmap_id\tx\ty\tz\tname",
    "grace\t72001\tm20_00_00_00\t0\t0\t0\tBelurat, Tower Settlement",
    "grace\t72002\tm20_00_00_00\t100\t0\t0\tBelurat, Stagefront",
    "grace\t72003\tm20_01_00_00\t0\t0\t0\tBelurat, Theatre",
    "item\t20007620\tm20_00_00_00\t10\t0\t0\t",     # nearest 72001 (d=10)
    "item\t20007820\tm20_00_00_00\t90\t0\t0\t",     # nearest 72002 (d=10)
    "item\t20017350\tm20_01_00_00\t5\t0\t0\t",      # only grace in this map -> 72003
    "# comment ignored",
    "item\t99999\tm99_99_99_99\t0\t0\t0\t",         # no grace in this map -> dropped
]


def test_same_map_nearest():
    m = bng.build_map(COORDS)
    assert m[20007620] == "Belurat, Tower Settlement", m
    assert m[20007820] == "Belurat, Stagefront", m
    assert m[20017350] == "Belurat, Theatre", m
    assert 99999 not in m   # no grace in its map -> no descriptor (falls through to locale)


def test_map_local_isolation():
    # an item is matched ONLY within its own map, never to a closer grace in a different map
    coords = [
        "grace\t1\tmA\t0\t0\t0\tGrace A",
        "grace\t2\tmB\t1\t0\t0\tGrace B",       # spatially closer but WRONG map
        "item\t500\tmA\t5\t0\t0\t",
    ]
    m = bng.build_map(coords)
    assert m[500] == "Grace A"


def test_max_dist_cap():
    coords = [
        "grace\t1\tmA\t0\t0\t0\tFar Grace",
        "item\t500\tmA\t1000\t0\t0\t",
    ]
    assert bng.build_map(coords) == {500: "Far Grace"}          # no cap -> matched
    assert bng.build_map(coords, max_dist=200.0) == {}          # capped -> dropped


def test_unnamed_grace_ignored():
    coords = [
        "grace\t1\tmA\t0\t0\t0\t",              # no name -> useless
        "grace\t2\tmA\t50\t0\t0\tNamed Grace",
        "item\t500\tmA\t1\t0\t0\t",             # closest is unnamed; must fall to the named one
    ]
    assert bng.build_map(coords) == {500: "Named Grace"}


if __name__ == "__main__":
    import sys
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn(); print("ok", fn.__name__)
    print(f"\n{len(fns)} tests passed")
    sys.exit(0)
