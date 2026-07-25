"""`nearest_grace.tsv` must keep its `grace_key` column -- gen_data now REGIONS checks with it.

The GRACE-STRADDLE SCREEN groups checks by the grace's own key, and `gen_data._load_grace_play_region()`
reads the same column to report how many checks that oracle can actually see.

⚠️ It is NOT used to region checks. That was tried (e14dfa7) and reverted: regioning a check by its
own nearest grace makes the straddle screen circular -- the check can no longer disagree with the
grace it was regioned by, so the oracle stops being able to find anything. The column is the
ORACLE's input, not the derivation's.

That still makes it load-bearing. If a regen with an older `build_nearest_grace.py` drops it, nothing
errors: the straddle screen falls back on... nothing, because `_straddles()` asserts the column is
there -- and this test is the earlier, more legible failure. Seven grace display NAMES are shared by
two physically distant graces, so a name-keyed join would group checks under the wrong grace and
manufacture straddles that do not exist (2 of them, 4 phantom minority checks, measured).

It is also why the column holds the KEY and not the display name: seven grace names are shared by two
physically distant graces, so a name-keyed join would region checks by the wrong grace entirely (see
tools/build_nearest_grace.py).
"""
import os

import pytest


def _tsv():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nearest_grace.tsv")
    if not os.path.isfile(path):
        pytest.skip("nearest_grace.tsv not installed beside the package -- oracle would run BLIND")
    rows = []
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            p = line.rstrip("\n").split("\t")
            if p[0] == "flag":
                continue
            rows.append(p)
    assert rows, "nearest_grace.tsv parsed to ZERO rows -- an empty oracle is a failure, not a pass"
    return rows


def test_every_row_carries_a_grace_key():
    rows = _tsv()
    missing = [p[0] for p in rows if len(p) < 3 or not p[2].strip()]
    assert not missing, (
        f"{len(missing)} of {len(rows)} nearest_grace.tsv rows have no grace_key. gen_data regions "
        "overworld checks with it and falls back to the TILE GUESS without it -- silently. Re-emit: "
        "python tools/build_nearest_grace.py. First few: " + ", ".join(missing[:8]))


def test_grace_keys_resolve_to_a_play_region():
    """A key that no grace table knows is the same failure wearing a different hat: the join returns
    nothing and every affected check falls back to the tile without a word."""
    import csv
    pkg = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    grm = os.path.join(pkg, "grace_region_map.tsv")
    if not os.path.isfile(grm):
        pytest.skip("grace_region_map.tsv not installed beside the package")
    with open(grm, encoding="utf-8-sig", newline="") as fh:
        known = {r["grace_flag"]: r["play_region_id"] for r in csv.DictReader(fh, delimiter="\t")}
    rows = _tsv()
    unknown = sorted({p[2] for p in rows if len(p) > 2 and p[2].strip() and p[2] not in known})
    assert not unknown, (
        f"nearest_grace.tsv references {len(unknown)} grace key(s) that grace_region_map.tsv does "
        f"not define: {unknown[:8]}. The two tables are out of step -- re-emit both.")
    resolved = sum(1 for p in rows if len(p) > 2 and known.get(p[2], "0") not in ("", "0"))
    assert resolved > 2000, (
        f"only {resolved} of {len(rows)} checks resolve to a real play_region through their grace. "
        "That is the number gen_data regions WITHOUT a tile guess, so a collapse here silently "
        "hands the map back to tile_pr.")
