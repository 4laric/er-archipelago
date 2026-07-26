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

This file does not fix that. The fix is to make the uncovered case DEFAULT LOUDLY instead of
answering -- give `tile_pr` a failure branch and bar a defaulted check from carrying progression.

⚠️ CORRECTION 2026-07-25. An earlier version of this note said the fix also needed re-emitting
`play_region_buckets.tsv` with RAW ids because "the `// 100` bucket collapses the game's own
subdivision: Weeping 61002 and Limgrave 61000 are one bucket". **That was an ID-SPACE confusion and
it is wrong.** 61002 is a BonfireWarpParam WARP id (18 graces carry it in grace_region_map.tsv), not
a PlayRegionParam bucket. PlayRegionParam does subdivide -- 61000 / 61010 / 61020 are three distinct
buckets, Weeping is 61020 -- and `region_groups.PLAY_REGION_GROUPS` has had all three, correctly
assigned, since 2026-07-13. Nothing is collapsed and no re-emit is owed.

The two tables in region_groups.py are deliberate and must not be conflated: `PLAY_REGION_GROUPS` is
PlayRegionParam buckets (the client KICK), `REGION_GROUPS` is warp ids (PLAY2AP, which regions
CHECKS). `tile_pr` and PLAY2AP both live in the WARP-id space, which is self-consistent -- the defect
below is coverage, not id space.

What this file does is make the exposure a NUMBER that cannot grow quietly. It needs no artifacts:
both inputs are committed tsvs, and it recomputes ANCHOR exactly as gen_data does.

DO NOT raise the pins. They come down when tiles get anchored or when the derivation learns to
refuse.

## WHAT IT WOULD TAKE TO ANCHOR THE REST -- two routes MEASURED 2026-07-26, both dead

Asked directly, and answered with numbers rather than a plan. On the slice measured here (check-
bearing m60 tiles from region_map.csv: 204 tiles, 117 anchored, 87 graceless carrying 308 checks --
a narrower universe than the pins above, which is why the numbers differ; the pins were NOT
re-derived):

  1. MORE GRACES REACHING THE JOIN -- nothing to win. Every one of the 166 m60 graces in
     grace_flags.tsv already resolves to a play_region through grace_region_map.tsv. ZERO are lost in
     the join. The tiles are graceless because THE GAME PUT NO GRACE THERE, not because we drop rows.

  2. PlayRegionParam.gridXNo / gridZNo -- looks exactly like a tile -> region table and is not.
     * coverage: 86 non-origin grid cells, covering 12 of the 87 graceless check-bearing tiles
       (54 of 308 checks). Not enough to matter even if it were right.
     * and it is not right: on tiles where BOTH exist, the ids do not correspond. Tile (37,47) is
       grace play_region 62000; PlayRegionParam says 3202001. (38,53) -> 63000 vs 3204001.
       (46,39) -> 64000 vs 3207001. A THIRD id space, unrelated to the warp-id space tile_pr and
       PLAY2AP live in -- exactly the confusion §2 of this docstring already corrects once.
     Those grid columns are most likely sign/invasion placement, not a region extent.

So the remaining routes are the expensive one and the honest one:
  * SPATIAL, from the MSBs -- each m60 tile has one; derive the tile's region from what physically
    stands in it. A 2.2 GB mount walk and a real datamine (the same one precise XYZ needs).
  * REFUSE -- give tile_pr a failure branch and let the 87/308 default LOUDLY, barred from carrying
    progression, which is what the top of this docstring already prescribes. Cheap and correct, but
    it shrinks the progression surface by 308 checks, so it is a FILL change: it needs gen_sweep +
    run_fill_regression, and it is Alaric's call, not a tidy-up.
"""
import collections
import csv
import os
import re

import pytest

# Measured on main 2026-07-25. RATCHETS: they may only go DOWN.
# RE-PINNED 2026-07-26, and the question CONTRIBUTING demands is answered before touching them:
# "a count that grows because the ground truth improved is fine; a count that grows because a
# predicate got looser is a bug. Rebaselining without answering which one it is, is how you launder
# a regression into a test."
#
# THIS ONE GREW BECAUSE THE INPUT GOT BETTER. `datamine_item_grace_coords.py --enemy` located 136
# more overworld checks (1809 -> 1945; --enemy is opt-in and the previous emit had not used it, so
# all 61 enemy-source checks were simply absent). Measured against the OLD table at 8e52c6a:
#
#     before   144 graceless tiles | 640 of 1809 exposed (35%)
#     now      145 graceless tiles | 670 of 1945 exposed (34%)
#
# One new graceless tile, m60_33_45, which previously held no LOCATED check at all. No predicate
# moved. ⭐ And the SHARE went DOWN -- we can see more of the map than we could, and a slightly
# smaller fraction of it is guessed.
#
# ⚠️ THE ABSOLUTE COUNTS ARE FRAGILE BY CONSTRUCTION: they can only rise as the coordinate table
# improves, so they will keep going red for the RIGHT reason and keep inviting a blind bump. That is
# why MAX_EXPOSED_SHARE below exists -- it is the quantity that actually means something, and it may
# only fall.
MAX_GRACELESS_TILES = 145
MAX_CHECKS_ON_GRACELESS_TILES = 670
# The honest invariant: the FRACTION of located overworld checks whose region is a tile guess. Unlike
# the raw counts this cannot be inflated by locating more checks, so it is the one to defend.
MAX_EXPOSED_SHARE = 0.35

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
    share = exposed / total
    assert share <= MAX_EXPOSED_SHARE, (
        f"{100.0 * share:.1f}% of located overworld checks ({exposed} of {total}) get their region "
        f"from a tile GUESS -- over the {100.0 * MAX_EXPOSED_SHARE:.0f}% ceiling. THIS is the "
        "assertion that means something: it cannot be moved by locating more checks, only by the "
        "derivation getting worse.")
    assert exposed <= MAX_CHECKS_ON_GRACELESS_TILES, (
        f"{exposed} of {total} overworld checks ({100.0 * share:.0f}%) sit on a tile with no grace, "
        f"so their region is a nearest-neighbour GUESS (pin {MAX_CHECKS_ON_GRACELESS_TILES}). "
        "Before raising this, answer the question CONTRIBUTING asks: did the SHARE above also rise? "
        "If it did not, the coordinate table simply located more checks and this count is expected "
        "to follow -- re-pin it WITH the before/after measurement, as the 2026-07-26 entry does. If "
        "the share DID rise, something got worse and the pin is not the problem.")


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
