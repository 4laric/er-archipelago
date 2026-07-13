#!/usr/bin/env python3
"""datamine_dungeon_regions.py -- derive interior map -> greenfield region FROM DATA.

`gen_data.DUNGEON_REGION_OVERRIDE` is a hand-maintained map->region table (~78 rows). Almost all of
it is derivable, from two independent game sources:

  1. GRACE JOIN (covers ~80% of minor dungeons). A dungeon's warp grace carries a
     BonfireWarpParam.bonfireSubCategoryId = play_region_id, which names its region:
     grace_flags.tsv (warpUnlockFlag -> mapTile) JOIN grace_region_map_*.tsv (grace_flag ->
     play_region_id) -> REGION_ID_MAP.md. Independent of region_map.csv.

  2. MSB ConnectCollision (covers the graceless ones). Every dungeon MSB records the map it connects
     to, in Part/ConnectCollision/*.xml as <MapID> -- 4 base64'd bytes (area, X, Y, block). A minor
     dungeon connects to its PARENT OVERWORLD TILE, e.g. m32_02 -> "PCUv/w==" -> 3C 25 2F -> m60_37_47
     -> Liurnia. That tile's region comes from the same grace anchors gen_data already uses.

Emits greenfield/dungeon_regions.tsv:  map_id \t region \t source \t evidence
`source` = grace | connect. Maps resolvable by NEITHER are omitted (they stay hand-curated).

Run on Windows (the MSB pass reads mapstudio; slow over the sandbox FUSE mount):
  python tools/datamine_dungeon_regions.py
"""
import base64
import csv
import glob
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
ART = os.path.join(REPO, "elden_ring_artifacts")
OUT = os.path.join(REPO, "greenfield", "dungeon_regions.tsv")

# play_region_id -> greenfield region: imported from THE spine (greenfield/region_groups.py) --
# this tool used to carry its own overworld copy, which is exactly the drift class the single
# source exists to kill.
import importlib.util as _ilu
_rg_spec = _ilu.spec_from_file_location("region_groups", os.path.join(REPO, "greenfield", "region_groups.py"))
_rg = _ilu.module_from_spec(_rg_spec); _rg_spec.loader.exec_module(_rg)
PLAY2GF = dict(_rg.PLAY2AP)


def _grace_source(prefix):
    """Latest grace table: TRACKED greenfield/ copy first (the derived tsvs moved there so a
    `git clean` can't orphan gen_data), artifacts as the legacy fallback -- same rule as
    gen_data._grace_table."""
    for base in (os.path.join(REPO, "greenfield"), ART):
        if not os.path.isdir(base):
            continue
        cand = sorted(x for x in os.listdir(base) if x.startswith(prefix) and x.endswith(".tsv"))
        if cand:
            return os.path.join(base, cand[-1])
    raise SystemExit(f"FATAL: {prefix}*.tsv found in neither greenfield/ nor elden_ring_artifacts/")


def _grace_tables():
    gf = {}
    with open(_grace_source("grace_flags"), newline="") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            try:
                f = int(r["warpUnlockFlag"])
            except (KeyError, ValueError):
                continue
            if 71000 <= f <= 76999:
                gf[str(f)] = r["mapTile"]
    pid = {}
    with open(_grace_source("grace_region_map"), newline="") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            pid[r["grace_flag"]] = r["play_region_id"]
    return gf, pid


def _overworld_anchors(gf, pid):
    acc = defaultdict(Counter)
    for flag, tile in gf.items():
        p = pid.get(flag)
        m = re.match(r"m60_(\d\d)_(\d\d)", tile or "")
        if p and p != "0" and m:
            acc[(int(m.group(1)), int(m.group(2)))][p] += 1
    return {k: v.most_common(1)[0][0] for k, v in acc.items()}


def _tile_region(tile, anchors):
    m = re.match(r"m6[01]_(\d\d)_(\d\d)", tile)
    if not m:
        return None
    x, y = int(m.group(1)), int(m.group(2))
    if (x, y) in anchors:
        return PLAY2GF.get(anchors[(x, y)])
    best, bd = None, 1e18                      # nearest grace-anchored tile
    for (ax, ay), p in anchors.items():
        d = (ax - x) ** 2 + (ay - y) ** 2
        if d < bd:
            bd, best = d, p
    return PLAY2GF.get(best)


def _map_from_graces(gf, pid, anchors):
    """map_id -> (region, evidence) via the dungeon's own warp grace."""
    out = {}
    votes = defaultdict(Counter)
    for flag, tile in gf.items():
        p = pid.get(flag)
        if not p or p == "0" or not tile:
            continue
        mid = "_".join(tile.split("_")[:2])
        votes[mid][p] += 1
    for mid, c in votes.items():
        p = c.most_common(1)[0][0]
        reg = PLAY2GF.get(p)
        if reg:
            out[mid] = (reg, f"grace play_region={p}")
    return out


def _connect_tiles(map_id):
    """Parent overworld tile(s) from the dungeon MSB's ConnectCollision <MapID> (base64 4 bytes)."""
    tiles = Counter()
    for d in glob.glob(os.path.join(ART, "mapstudio", map_id + "_*_*-msb-dcx")):
        for f in glob.glob(os.path.join(d, "Part", "ConnectCollision", "*.xml")):
            try:
                r = ET.parse(f).getroot()
            except ET.ParseError:
                continue
            b = r.findtext("MapID")
            if not b:
                continue
            try:
                raw = base64.b64decode(b)
            except Exception:
                continue
            if len(raw) < 3:
                continue
            a, x, y = raw[0], raw[1], raw[2]
            if a in (60, 61) and x != 255 and y != 255:
                tiles[f"m{a}_{x:02d}_{y:02d}"] += 1
    return tiles


# ConnectCollision says which map a dungeon CONNECTS to. For a MINOR dungeon (catacomb/cave/tunnel/
# DLC gaol/forge) that parent overworld tile IS its region. But a LEGACY or UNDERGROUND map is its OWN
# region -- Stormveil (m10) connects to a Limgrave tile and Deeproot (m12_03) surfaces under
# Mountaintops, yet neither is Limgrave/Mountaintops. So the connect fallback is restricted to the
# minor-dungeon areas; everything else must come from the grace join (or stay hand-curated).
MINOR_AREAS = ("m30", "m31", "m32", "m34", "m39", "m40", "m41", "m42", "m43")


def build():
    gf, pid = _grace_tables()
    anchors = _overworld_anchors(gf, pid)
    # grace truth from tools/map_region_oracle.py -- the SAME fold table the provenance oracle uses
    # (REGION_ID_MAP.md, incl. interior pids: Raya->Liurnia, Leyndell->Altus, ...). Do not re-derive.
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("_mro", os.path.join(HERE, "map_region_oracle.py"))
    _mro = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_mro)
    _truth, _meta = _mro.load_map_truth()
    grace_map = {}
    for mid, regs in (_truth or {}).items():
        if len(regs) == 1:                      # a boundary map with a region SET stays hand-curated
            grace_map[mid] = (next(iter(regs)), "grace join (map_region_oracle)")

    # Candidates = every interior map region_map.csv places a check in, UNION every interior map the
    # grace join knows. The union matters: a dungeon whose checks are all unplaced (map=PENDING, the
    # global/flag_prefix rows) contributes NO map to region_map.csv, so a region_map-only candidate set
    # silently skips it -- which is how 14 perfectly derivable catacombs (m30_01/02/04/06/08/12/14/15/16,
    # m40_01, m42_00, m43_00, ...) were left to be hand-curated despite the grace join knowing them.
    cands = set()
    with open(os.path.join(REPO, "greenfield", "region_map.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            m = (r.get("map") or "")
            if m and m != "PENDING" and not m.startswith(("m60", "m61")):
                cands.add("_".join(m.split("_")[:2]))
    cands |= {m for m in grace_map if not m.startswith(("m60", "m61"))}

    rows = []
    for mid in sorted(cands):
        if mid in grace_map:
            reg, ev = grace_map[mid]
            rows.append((mid, reg, "grace", ev))
            continue
        if not mid.startswith(MINOR_AREAS):
            continue                            # legacy/underground: its own region, never its parent's
        t = _connect_tiles(mid)
        if t:
            tile, n = t.most_common(1)[0]
            reg = _tile_region(tile, anchors)
            if reg:
                rows.append((mid, reg, "connect", f"ConnectCollision -> {tile} (x{n})"))
    return rows


def main():
    rows = build()
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("map_id\tregion\tsource\tevidence\n")
        for r in rows:
            fh.write("\t".join(r) + "\n")
    src = Counter(r[2] for r in rows)
    sys.stderr.write(f"dungeon_regions: {len(rows)} maps derived {dict(src)} -> {OUT}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
