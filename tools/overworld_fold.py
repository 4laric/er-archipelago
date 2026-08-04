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
import re

# A 3-field id (m60_34_50) is the SAME TILE as its 4-field form (m60_34_50_00) when the tile is on
# the fine grid; below tile 33 it is a truncated LOD2 id. Both shapes occur in
# item_grace_coords.tsv -- 725 item rows are 3-field and every one of the 225 overworld grace rows
# is 4-field, which is the whole of issue #338.
OW_RE = re.compile(r"^(m6[01])_(\d\d)_(\d\d)(?:_(\d)(\d))?$")


def world_xz(map_id, x, z):
    """Overworld map-local coords -> (base, gx, gz) in the single folded frame that
    poptracker/maps/map_calibration*.json is authored in. None for interiors."""
    m = OW_RE.match(map_id)
    if not m:
        return None
    base, tx, tz, _ver, lod = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4), m.group(5)
    lod = int(lod) if lod is not None else (2 if tx < 30 else 0)
    pitch = 256 << lod
    off = (pitch - 256) / 2.0
    return base, tx * pitch + x + off, tz * pitch + z + off
