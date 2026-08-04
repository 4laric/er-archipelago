# -*- coding: utf-8 -*-
"""Pure tests for tools/build_nearest_grace.py -- the nearest-grace math (layer 4 producer).
Synthetic coordinates, no artifacts. Run: python3 eldenring/tests/test_gf_nearest_grace.py"""
import importlib.util
import os
import re

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
    assert bng.build_map(coords) == {500: "Far Grace"}          # 1000 m is inside the default cap
    assert bng.build_map(coords, max_dist=200.0) == {}          # explicit cap -> dropped
    assert bng.build_map(coords, max_dist=None) == {500: "Far Grace"}   # opt out entirely


def test_the_default_is_capped_not_open():
    """The default used to be `no cap`, and a nearest-neighbour with no cap NEVER fails: 18 overworld
    checks anchored to a grace 8.7-10.4 km away, twelve of them to Altar South, which is what made
    that grace look like it spanned four regions. Pin the default so it cannot quietly reopen."""
    assert bng.DEFAULT_MAX_DIST == 2000.0
    coords = [
        "grace\t1\tmA\t0\t0\t0\tDistant Grace",
        "item\t500\tmA\t9000\t0\t0\t",
    ]
    assert bng.build_map(coords) == {}, "a 9 km 'nearest' grace must be refused, not answered"


def test_drops_are_tallied_not_silent():
    """A filter with no tally is a lie (CONTRIBUTING rule 4)."""
    coords = [
        "grace\t1\tmA\t0\t0\t0\tDistant Grace",
        "item\t500\tmA\t9000\t0\t0\t",
        "item\t501\tmA\t10\t0\t0\t",
    ]
    mapping, dropped = bng.build_keyed_map_reporting(coords)
    assert mapping == {501: ("Distant Grace", "1")}
    assert dropped == [(500, "Distant Grace", 9000.0)], dropped


def test_a_map_with_no_named_grace_is_not_reported_as_a_drop():
    """"No grace within the cap" and "no named grace in this map at all" are different facts, and
    only the first is this cap's doing. Conflating them would make the tally noise."""
    coords = [
        "grace\t1\tmA\t0\t0\t0\t",          # unnamed -> unusable
        "item\t500\tmA\t10\t0\t0\t",
    ]
    mapping, dropped = bng.build_keyed_map_reporting(coords)
    assert mapping == {}
    assert dropped == [], "an unnamed-grace map is not a distance drop"


def test_unnamed_grace_ignored():
    coords = [
        "grace\t1\tmA\t0\t0\t0\t",              # no name -> useless
        "grace\t2\tmA\t50\t0\t0\tNamed Grace",
        "item\t500\tmA\t1\t0\t0\t",             # closest is unnamed; must fall to the named one
    ]
    assert bng.build_map(coords) == {500: "Named Grace"}


def test_overworld_tiles_merge_across_border():
    # Overworld (m60/m61) tiles are per-tile map-local frames folded into one global grid
    # (world = tile*256 + local). A graceless tile's check must still anchor to a neighbouring
    # tile's grace metres across the border -- the whole point of the merge.
    coords = [
        "grace\t1\tm60_11_08_00\t5\t0\t0\tNeighbour Grace",   # global x = 11*256 + 5 = 2821
        "item\t500\tm60_10_08_00\t250\t0\t0\t",               # global x = 10*256 + 250 = 2810 (~11m away)
    ]
    # old same-map-only logic would leave 500 blind (its tile has no grace)
    assert bng.build_map(coords) == {500: "Neighbour Grace"}


def test_overworld_merge_preserves_true_distance():
    # Same local coords in DIFFERENT tiles are NOT the same point: the nearer tile wins by true
    # world distance, so the merge can't collapse distinct tiles onto each other.
    coords = [
        "grace\t1\tm60_00_00_00\t0\t0\t0\tFar Grace",         # global (0,0,0)
        "grace\t2\tm60_05_00_00\t10\t0\t0\tNear Grace",       # global (1290,0,0)
        "item\t500\tm60_05_00_00\t0\t0\t0\t",                 # global (1280,0,0): Near=10m, Far=1280m
    ]
    assert bng.build_map(coords)[500] == "Near Grace"


def test_interior_maps_still_isolated():
    # Non-overworld map ids pass through _normalize untouched: still strictly same-map.
    coords = [
        "grace\t1\tm20_00_00_00\t0\t0\t0\tGrace A",
        "grace\t2\tm20_01_00_00\t1\t0\t0\tGrace B",           # closer in raw coords, different map
        "item\t500\tm20_00_00_00\t5\t0\t0\t",
    ]
    assert bng.build_map(coords)[500] == "Grace A"


if __name__ == "__main__":
    import sys
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn(); print("ok", fn.__name__)
    print(f"\n{len(fns)} tests passed")
    sys.exit(0)

# ---------------------------------------------------------------------------------------------
# ISSUE #338 -- ONE OVERWORLD FOLD, AND ONE KEY SPACE
#
# For months there were TWO folds. `build_check_browser.world_xz` honoured LOD and accepted a
# 3-field map id; `build_nearest_grace._normalize` folded at *256 regardless of LOD and its regex
# required a trailing '_'. So every one of the 725 three-field ITEM rows in item_grace_coords.tsv
# kept its raw map id as the join key while all 225 overworld GRACE rows folded to 'm60' -- the two
# sides could never share a key, `graces_by_map.get()` returned empty before any distance was
# computed, and 421 checks lost their nearest grace with nothing in the run output to say so.
#
# world_xz's own docstring NAMED the other fold as wrong. A comment is not a gate (CONTRIBUTING
# rule 10), so these are.
# ---------------------------------------------------------------------------------------------

def _tools_dir():
    return os.path.dirname(TOOL)


def _load_sibling(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_tools_dir(), name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_there_is_exactly_one_overworld_fold():
    """Not "the two agree" -- the two are the SAME OBJECT. Agreement is a property that can lapse
    between commits; identity cannot. Re-introducing a private fold in either module fails here."""
    fold = _load_sibling("overworld_fold")
    browser = _load_sibling("build_check_browser")
    assert bng.world_xz.__module__ == fold.world_xz.__module__ == browser.world_xz.__module__
    assert bng.world_xz.__qualname__ == "world_xz"
    src = open(TOOL, encoding="utf-8").read()
    assert "_OVERWORLD_RE" not in src and "_TILE_M" not in src, \
        "build_nearest_grace has grown its own overworld fold again -- that is issue #338"


def test_the_three_field_and_four_field_id_are_the_same_tile():
    """The premise the whole fix rests on, stated as an assertion instead of an assumption.
    item_grace_coords.tsv carries BOTH shapes for the overworld; if they did not denote the same
    tile, folding them into one key space would be an id-space error (CONTRIBUTING rule 3), not a
    repair. Above the fine-grid floor (tile 33) the 3-field form is just the 4-field form with a
    _00 that got dropped; below it, it is a truncated LOD2 id and is NOT the same tile."""
    fold = _load_sibling("overworld_fold")
    assert fold.world_xz("m60_34_50", 1.0, 2.0) == fold.world_xz("m60_34_50_00", 1.0, 2.0)
    assert fold.world_xz("m60_44_36", 0.0, 0.0) == fold.world_xz("m60_44_36_00", 0.0, 0.0)
    # ...and the low-tile form is deliberately NOT equal to its _00 reading.
    assert fold.world_xz("m60_08_11", 0.0, 0.0) != fold.world_xz("m60_08_11_00", 0.0, 0.0)
    assert fold.world_xz("m60_08_11", 0.0, 0.0) == fold.world_xz("m60_08_11_02", 0.0, 0.0)


def test_no_overworld_row_survives_the_fold_unnormalised():
    """THE REGRESSION GATE, over the REAL committed coords rather than a fixture.

    The defect was invisible per-row: every id was well-formed and every coordinate was real. It
    only shows when you ask whether the two SIDES of the join can ever meet. So: after parsing, no
    key in graces_by_map and no item key may still look like a raw overworld tile id."""
    coords = _find_up(os.path.join("greenfield", "item_grace_coords.tsv"))
    if coords is None:
        pytest.skip("item_grace_coords.tsv not beside the package")
    with open(coords, encoding="utf-8-sig") as fh:
        items, graces_by_map = bng.parse_coords(fh.readlines())
    raw = re.compile(r"^m6[01]_\d\d")
    bad_g = sorted(k for k in graces_by_map if raw.match(k))
    bad_i = sorted({m for _f, m, _x in items if raw.match(m)})
    assert bad_g == [], f"grace keys left unfolded: {bad_g[:5]}"
    assert bad_i == [], f"item keys left unfolded: {bad_i[:5]}"
    # And both sides really do land in the shared frame, or the assertion above is vacuous.
    assert "m60" in graces_by_map, "no overworld graces folded at all -- this gate has gone vacuous"
    assert any(m == "m60" for _f, m, _x in items), "no overworld items folded at all"


def test_the_committed_table_has_not_shrunk_and_keeps_its_derived_rows():
    """A shrinking oracle must fail loudly (AGENTS.md, the _ARENA_FLOOR rule).

    The floor is a tripwire, not a target. The `via=boss_arena` half is here because re-emitting
    WITHOUT `--extra-coords greenfield/boss_reward_coords.tsv` silently drops 24 rows and the run
    still says "wrote ... 3856 checks" -- which is exactly what happened while fixing #338, and
    nothing but a diff caught it. The correct invocation is in the module docstring."""
    tsv = _find_up(os.path.join("greenfield", "nearest_grace.tsv"))
    if tsv is None:
        pytest.skip("nearest_grace.tsv not beside the package")
    rows = [ln.rstrip("\n").split("\t") for ln in open(tsv, encoding="utf-8")
            if ln.strip() and not ln.startswith("#") and not ln.startswith("flag\t")]
    assert len(rows) >= 3880, (
        f"nearest_grace.tsv has {len(rows)} rows, below the 3880 measured on 2026-08-04. A re-emit "
        f"that STRANDS checks must be explained, not rebaselined -- did the coords regress, or was "
        f"--extra-coords omitted?")
    derived = [r for r in rows if len(r) > 3 and r[3] == "boss_arena"]
    assert len(derived) >= 24, (
        f"only {len(derived)} via=boss_arena row(s): re-emit with "
        f"`--extra-coords greenfield/boss_reward_coords.tsv`")


def test_the_graceless_map_case_is_counted():
    """The blind spot that hid #338. The drop tally only fires when a same-map grace exists and is
    too far; with ZERO same-map graces nothing was recorded -- and zero same-map graces is precisely
    what a broken join key produces. Counted now, on an opt-in third return value so no existing
    caller changed shape."""
    coords = [
        "grace\t1\tmA\t0\t0\t0\tNamed Grace",
        "item\t500\tmA\t10\t0\t0\t",      # resolves
        "item\t501\tmB\t0\t0\t0\t",       # map with no grace at all -> unmatched, not a drop
    ]
    mapping, dropped, unmatched = bng.build_keyed_map_reporting(coords, with_unmatched=True)
    assert mapping == {500: ("Named Grace", "1")}
    assert dropped == []
    assert unmatched == [(501, "mB")], unmatched
    # the 2-tuple contract is untouched for every existing caller
    assert len(bng.build_keyed_map_reporting(coords)) == 2
