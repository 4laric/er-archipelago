#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""overworld_fold.py -- THE overworld tile fold, in one place.

m60 (Lands Between) and m61 (Shadow Realm) are stored as a grid of per-tile MSB frames whose
coordinates are MAP-LOCAL. Anything that compares two overworld positions -- nearest-grace, the
check browser's map, the desc-triage map -- must first fold them into one global frame, and must
do it IDENTICALLY, or the same check lands in two places depending on who asked.

It did. Until 2026-08-04 there were TWO folds: this one (formerly build_check_browser.world_xz,
pinned by tests/test_gf_desc_triage.py) and build_nearest_grace._normalize, which folded at *256
regardless of LOD and whose regex required a trailing '_'. `world_xz`'s own docstring named the
other one as wrong and the divergence still cost 421 checks their nearest grace (issue #338). One
implementation, one test -- so the drift cannot come back.

The 4th map-id field is [version][lod]. LOD is DOCUMENTED (see
greenfield/eldenring/tests/test_gf_lod_tile_regions.py and gen_data.py:177): _00 is the fine grid,
_01 2x coarser, _02 4x coarser, so pitch = 256 << lod.

Two parts are INFERRED and documented nowhere -- both pinned by tests/test_gf_desc_triage.py so
they fail loudly rather than drift:
  * the (pitch-256)/2 centring term. Without it all 18 LOD2 rows sit 244-463 m outside the tile
    their own flag encodes; with it, five coarse merchant tiles land 50-122 m from a real named
    grace. See the DESC-TRIAGE section of AGENTS.md to falsify.
  * "3-field id + low tile = truncated LOD2" -- tools/datamine_merchant_shops.py::_map_id builds
    `area_x_y` and drops both digits, and the fine grid starts at tile 33.
"""
import math
import re

# A 3-field id (m60_34_50) is the SAME TILE as its 4-field form (m60_34_50_00) when the tile is on
# the fine grid; below tile 33 it is a truncated LOD2 id. Both shapes occur in
# item_grace_coords.tsv -- 725 item rows are 3-field and every one of the 225 overworld grace rows
# is 4-field, which is the whole of issue #338.
OW_RE = re.compile(r"^(m6[01])_(\d\d)_(\d\d)(?:_(\d)(\d))?$")


def world_xz(map_id, x, z):
    """Overworld map-local coords -> (base, gx, gz) in the single folded frame that
    greenfield/maps/map_calibration*.json is authored in. None for interiors."""
    m = OW_RE.match(map_id)
    if not m:
        return None
    base, tx, tz, _ver, lod = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4), m.group(5)
    lod = int(lod) if lod is not None else (2 if tx < 30 else 0)
    pitch = 256 << lod
    off = (pitch - 256) / 2.0
    return base, tx * pitch + x + off, tz * pitch + z + off


def fine_tile(gx, gz):
    """The FINE-GRID tile index a FOLDED overworld position belongs to -- i.e. the tile whose
    PlayRegionParam (gridXNo, gridZNo) row governs that point.

    THE TILE FRAME IS CENTRE-ORIGIN, so this ROUNDS; it does not floor. Tile index t owns
    [t*256 - 128, t*256 + 128), not [t*256, t*256 + 256). `floor(g / 256)` -- what
    datamine_item_play_regions did until 2026-08-26 -- attributes every point to the tile a HALF
    STEP down-and-left of the one it is standing on, and it looks entirely plausible because it is
    only ever wrong by one tile index.

    THE MEASUREMENT, on the shipped params (pure counts, all re-runnable):
      * BonfireWarpParam's 225 overworld graces carry 450 local axis values. 438 (97.3%) fall in
        [-128, 128); only 227 (50.4%) fall in [0, 256), and 222 of them are NEGATIVE. A local frame
        whose origin were the tile CORNER cannot produce 222 negative locals.
      * greenfield/item_grace_coords.tsv, overworld placements: 4732 of 5010 axis values (94.5%)
        in [-128, 128).
      * Round-trip each grace -- fold with `world_xz`, re-derive the tile with THIS function -- and
        214 of 225 land back on the grace's OWN authored tile. Under `floor` only 53 of 225 do.
        The 11 that still move are genuine spillers: their local coordinate is past +-128, so they
        physically stand on the neighbouring tile.
      * Against the graces whose ground a PlayArea VOLUME rules on (independent truth), the tile
        default agrees 11/14 rounded and 8/10 floored.

    Rounds half AWAY FROM ZERO deliberately: Python's `round` is banker's, so a coordinate exactly
    on a tile seam would flip with the PARITY of the tile index."""
    return (int(math.floor(gx / 256.0 + 0.5)), int(math.floor(gz / 256.0 + 0.5)))
