#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""datamine_map_names.py -- INTERIOR map tile -> dungeon display name, from vanilla game files.

Emits greenfield/map_names.tsv (tile<TAB>name), consumed by gen_data._MAP_NAMES and passed to
desc_sources.describe() as `map_names` -- the layer-5 locale fallback, so a check with no boss / spot /
grace descriptor renders "treasure - Sellia Crystal Tunnel" instead of the bare "treasure - m32_08".

WHY A NEW DATAMINE (vs build_tile_grace.py, which already does tile -> grace name):
build_tile_grace keys off grace_flags.tsv, whose `mapTile` is the grace's *flag-decoded* tile. For a
minor dungeon whose warp grace's flag decodes to the OVERWORLD ENTRANCE tile (m60_XX_YY) rather than
the interior, that join leaves the interior tile (m32_04) UNNAMED -- and the interior tile is exactly
where the dungeon's checks physically sit (Alaric 2026-07-22: "most of these maps have a single grace
with the same name as the catacomb"). So we go to ground truth: BonfireWarpParam.bonfireEntityId
encodes the grace's PHYSICAL map (first 4 digits = area+block, e.g. 32040800 -> m32_04), which is the
same tile the check's map id folds to (desc_sources.map_short: m32_04_00_00 -> m32_04). That physical
tile, joined to the grace's PlaceName, is the dungeon's name.

Derivation (matt-free): BonfireWarpParam row -> `bonfireEntityId`[0:4] = physical interior tile (for
graces whose `areaNo` is NOT 60/61, i.e. not overworld); `textId1` indexes the PlaceName FMG (base +
item_dlc0*), whose entry is the shown name -- same PlaceName join as datamine_grace_names.py. Overworld
graces (areaNo 60/61) are SKIPPED: their checks already carry the region-name prefix, and naming an
m60 grid tile after one dungeon would be wrong. Per tile the representative name is the lowest-flag
NON-arena grace on it (arena_graces.tsv excluded, so a catacomb shows its own name, not the boss-arena
grace's -- mirrors build_tile_grace.py); if every grace on the tile is an arena grace, the lowest-flag
one is used.

Reads elden_ring_artifacts (unpacked witchy FMG xml + vanilla_params CSV) + committed arena_graces.tsv.
Pure Python, no Oodle, so it runs anywhere the artifacts are readable (Windows, or a Linux box with the
folder mounted):
    python tools/datamine_map_names.py
"""
import csv
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AR = os.path.join(ROOT, "elden_ring_artifacts")
OUT = os.path.join(ROOT, "greenfield", "map_names.tsv")

_TEXT_RE = re.compile(r'<text id="(\d+)"[^>]*>(.*?)</text>', re.S)
_NULLS = ("%null%", "&lt;?null?&gt;", "x", "")


def _fmg(path):
    d = {}
    if not os.path.isfile(path):
        return d
    for m in _TEXT_RE.finditer(open(path, encoding="utf-8", errors="replace").read()):
        v = m.group(2).strip()
        if v not in _NULLS:
            d[int(m.group(1))] = v
    return d


def _arena_flags():
    """Grace flags that sit inside a boss arena (greenfield/arena_graces.tsv, col 0). Excluded from the
    per-tile representative so the DUNGEON name wins over the boss-arena grace's name."""
    flags, path = set(), os.path.join(ROOT, "greenfield", "arena_graces.tsv")
    if os.path.isfile(path):
        for ln in open(path, encoding="utf-8"):
            if ln[:1].isdigit():
                try:
                    flags.add(int(ln.split("\t")[0]))
                except ValueError:
                    pass
    return flags


def _bwp_path():
    for cand in (os.path.join(AR, "vanilla_er", "vanilla_er", "BonfireWarpParam.csv"),
                 os.path.join(AR, "vanilla_params", "BonfireWarpParam.csv")):
        if os.path.isfile(cand):
            return cand
    return None


def main():
    base = _fmg(os.path.join(AR, "msg", "item-msgbnd-dcx", "PlaceName.fmg.xml"))
    dlc = {}
    for fp in glob.glob(os.path.join(AR, "msg", "item_dlc0*-msgbnd-dcx", "PlaceName*.fmg.xml")):
        dlc.update(_fmg(fp))
    if not base and not dlc:
        print(f"no PlaceName FMGs under {AR}/msg -- nothing written.", file=sys.stderr)
        return 1
    bwp = _bwp_path()
    if not bwp:
        print(f"missing BonfireWarpParam.csv under {AR} -- nothing written.", file=sys.stderr)
        return 1
    arena = _arena_flags()

    # tile -> {grace_flag: name}. Only INTERIOR graces (areaNo not 60/61); the physical tile is the
    # bonfireEntityId's map prefix (AABBxxxx -> mAA_BB), which is the tile the check's map id folds to.
    by_tile = {}
    for r in csv.DictReader(open(bwp, encoding="utf-8", errors="replace")):
        fl = r.get("eventflagId", "")
        if not fl.lstrip("-").isdigit() or not (71000 <= int(fl) <= 76999):
            continue
        try:
            area = int(r.get("areaNo", 0) or 0)
        except ValueError:
            continue
        if area in (60, 61):
            continue                                   # overworld -> region-named, not a dungeon
        ent = str(r.get("bonfireEntityId", "") or "").strip()
        if len(ent) != 8 or not ent.isdigit():
            continue                                   # no interior entity id -> can't place it
        tile = f"m{ent[0:2]}_{ent[2:4]}"
        try:
            tid = int(r["textId1"])
        except (KeyError, ValueError):
            continue
        if tid < 0:
            continue
        nm = dlc.get(tid) or base.get(tid)
        if nm:
            by_tile.setdefault(tile, {})[int(fl)] = nm

    if not by_tile:
        print("no interior grace names resolved -- nothing written.", file=sys.stderr)
        return 1

    tile_name = {}
    for tile, fn in by_tile.items():
        non = [f for f in fn if f not in arena]        # non-arena graces win (dungeon name, not arena)
        tile_name[tile] = fn[min(non)] if non else fn[min(fn)]

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("# AUTO-GENERATED by tools/datamine_map_names.py -- INTERIOR map tile -> dungeon name.\n")
        f.write("# BonfireWarpParam.bonfireEntityId[0:4] (physical tile) -> textId1 -> PlaceName FMG\n")
        f.write("# (base + DLC); representative = lowest-flag non-arena grace on the tile. desc_sources\n")
        f.write("# layer-5 locale renders 'verb - <name>'.\n")
        f.write("tile\tname\n")
        for t in sorted(tile_name):
            f.write(f"{t}\t{tile_name[t]}\n")
    print(f"wrote {OUT}: {len(tile_name)} interior tiles named")
    return 0


if __name__ == "__main__":
    sys.exit(main())
