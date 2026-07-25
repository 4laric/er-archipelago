"""`nearest_grace.tsv` must keep its `grace_key` column -- gen_data now REGIONS checks with it.

Since 2026-07-25 `gen_data._load_grace_play_region()` reads column 3 (the grace's own warpUnlockFlag)
and uses it to region every overworld check whose nearest grace is known:

    play_region = grace_region_map[nearest_grace.grace_key]      # metric NN, capped at 2000 m
    ... falling back to the TILE only when that is absent, and to DEFAULTED when the tile is
    unanchored (tile_pr_strict).

That makes the column load-bearing in a way it was not when it only fed a description string. If a
regen with an older `build_nearest_grace.py` drops it, nothing errors: every overworld check silently
falls back to the tile guess -- the exact 15%-wrong derivation this change exists to stop using --
and the only symptom is regions quietly moving. gen_data prints a WARNING in that case; this test is
the part that fails.

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
