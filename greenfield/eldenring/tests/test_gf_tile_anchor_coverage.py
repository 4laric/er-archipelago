"""How many checks get their region from a TILE GUESS -- pinned, so the exposure cannot grow.

`gen_data.tile_pr(x, y)` names an overworld tile's play_region. It is built from ANCHOR, which is
assembled from the tiles that CONTAIN A GRACE (grace_flags.tsv mapTile x grace_region_map.tsv
play_region_id). A tile with no grace is not in ANCHOR -- and `tile_pr` then returns the nearest
anchored tile's play_region:

    def tile_pr(x,y):
        if (x,y) in ANCHOR: return ANCHOR[(x,y)]
        best,bd=None,1e18
        for (ax,ay),pr in ANCHOR.items(): ...      # nearest-neighbour
        return best

**It has no failure branch.** There is always a nearest tile, so an uncovered tile always gets a
confident answer, and a wrong one is indistinguishable from a right one. That is the mechanism behind
the reported Church of Pilgrimage bug (a Weeping Sacred Tear reading as Limgrave) and behind
`Summonwater Village Outskirts`, whose SEVEN minority checks are on graceless tiles -- all seven.
Measured 2026-07-25: 34 of the grace-straddle screen's 98 minority checks sit on graceless tiles.

This file does not fix that. The fix is #192 -- re-emit `play_region_buckets.tsv` with RAW
PlayRegionParam ids (the `// 100` bucket also collapses the game's own subdivision: Weeping 61002 and
Limgrave 61000 are one bucket) and make the uncovered case DEFAULT LOUDLY instead of answering. That
needs PlayRegionParam.csv, which is Windows-only.

What this file does is make the exposure a NUMBER that cannot grow quietly. It needs no artifacts:
both inputs are committed tsvs, and it recomputes ANCHOR exactly as gen_data does.

DO NOT raise the pins. They come down when tiles get anchored or when the derivation learns to
refuse.
"""
import collections
import csv
import os
import re

import pytest

# Measured on main 2026-07-25. RATCHETS: they may only go DOWN.
MAX_GRACELESS_TILES = 144
MAX_CHECKS_ON_GRACELESS_TILES = 640

_TILE_RE = re.compile(r"(m6[01])_(\d\d)_(\d\d)")


def _pkg(name):
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), name)
    if not os.path.isfile(path):
        pytest.skip(f"{name} not installed beside the package -- oracle would run BLIND")
    return path


def _anchor_tiles():
    """The overworld tiles gen_data can answer for: those holding a grace with a play_region.

    Mirrors gen_data's ANCHOR construction. If the two ever diverge this file is measuring a fiction,
    so the shape assertions below are load-bearing, not decoration.
    """
    gf = {}
    with open(_pkg("grace_flags.tsv"), encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            if 71000 <= int(row["warpUnlockFlag"]) <= 76999:
                gf[row["warpUnlockFlag"]] = row["mapTile"]
    greg = {}
    with open(_pkg("grace_region_map.tsv"), encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            greg[row["grace_flag"]] = row["play_region_id"]
    assert gf and greg, "grace tables parsed to zero rows -- an empty oracle is a failure, not a pass"
    anchor = set()
    for flag, tile in gf.items():
        pr = greg.get(flag)
        m = _TILE_RE.match(tile)
        if pr and pr != "0" and m:
            anchor.add((m.group(1), int(m.group(2)), int(m.group(3))))
    assert len(anchor) > 100, f"only {len(anchor)} anchored tiles -- the join has drifted"
    return anchor


def _check_tiles():
    """{tile -> number of checks on it} for every overworld check with coordinates."""
    tiles = collections.Counter()
    with open(_pkg("item_grace_coords.tsv"), encoding="utf-8-sig") as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) < 6 or p[0] != "item":
                continue
            m = _TILE_RE.match(p[2])
            if m:
                tiles[(m.group(1), int(m.group(2)), int(m.group(3)))] += 1
    assert sum(tiles.values()) > 1000, "too few overworld checks located -- the join has drifted"
    return tiles


def test_graceless_tile_count_does_not_grow():
    anchor = _anchor_tiles()
    tiles = _check_tiles()
    graceless = sorted(t for t in tiles if t not in anchor)
    assert len(graceless) <= MAX_GRACELESS_TILES, (
        f"{len(graceless)} overworld tiles hold checks but no grace (pin {MAX_GRACELESS_TILES}). "
        "Every check on one of these gets its region from tile_pr's nearest-neighbour, which cannot "
        "fail and therefore cannot warn. Do NOT raise the pin: "
        + ", ".join(f"{a}_{b:02d}_{c:02d}" for a, b, c in graceless[:10]))


def test_checks_resolved_by_a_tile_guess_do_not_grow():
    anchor = _anchor_tiles()
    tiles = _check_tiles()
    exposed = sum(n for t, n in tiles.items() if t not in anchor)
    total = sum(tiles.values())
    assert exposed <= MAX_CHECKS_ON_GRACELESS_TILES, (
        f"{exposed} of {total} overworld checks ({100.0 * exposed / total:.0f}%) sit on a tile with "
        f"no grace, so their region is a nearest-neighbour GUESS (pin "
        f"{MAX_CHECKS_ON_GRACELESS_TILES}). This is the upper bound on tile-guessed regions and it "
        "may only shrink.")


def test_the_summonwater_case_is_still_visible():
    """The clearest instance, named so the screen cannot silently stop seeing it: all seven of
    `Summonwater Village Outskirts`' minority checks (reading Caelid, in a Limgrave location) are on
    graceless tiles. Delete this when the derivation learns to refuse -- and lower the pins with it."""
    anchor = _anchor_tiles()
    tiles = _check_tiles()
    graceless = {t for t in tiles if t not in anchor}
    assert graceless, "no graceless tiles at all -- either fixed (lower the pins) or the join broke"
    # m60_39_35 / m60_40_35 are the Summonwater neighbourhood; at least one must still be uncovered.
    summonwater = {t for t in graceless if t[0] == "m60" and 38 <= t[1] <= 41 and 34 <= t[2] <= 36}
    assert summonwater, (
        "the Summonwater-area tiles are all anchored now -- if that is a real fix, drop this test "
        "AND lower MAX_GRACELESS_TILES / MAX_CHECKS_ON_GRACELESS_TILES in the same commit")
