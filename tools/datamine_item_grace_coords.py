#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""datamine_item_grace_coords.py -- emit map-local XYZ for every check and every grace, so
tools/build_nearest_grace.py can pick each check's nearest Site of Grace (desc_sources layer 4).

RUN ON WINDOWS (needs elden_ring_artifacts: witchy'd MSBs + the vanilla-param CSVs + the
positioned grace_flags.tsv). The agent sandbox has none of these, so this tool is authored to
mirror two already-verified datamines and is validated on-box:
  * flag derivation + treasure/enemy iteration  <- tools/datamine_msb_item_regions.py
  * Part/Enemy <Position> + BonfireWarp grace positions  <- tools/datamine_arena_graces.py

OUTPUT: greenfield/item_grace_coords.tsv
    kind<TAB>key<TAB>map_id<TAB>x<TAB>y<TAB>z<TAB>name
  kind='item'  key=check event flag         name=''
  kind='grace' key=warpUnlockFlag           name=<human grace name>

Positions are MAP-LOCAL (same frame arena_graces relies on); build_nearest_grace only compares
within a map. Enemy-drop items take their enemy part's position; treasure items take their treasure
part's position.

    python tools/datamine_item_grace_coords.py                 # all maps
    python tools/datamine_item_grace_coords.py --maps m20_00 m20_01   # subset (validation)

### VALIDATE-ON-BOX (two spots I could not exercise in the sandbox) ###
 (A) Treasure part -> position: the witchy Event/Treasure xml references a part by name; that part
     (Part/Asset or Part/DummyAsset) carries <Position>. _treasure_positions() resolves it; confirm
     the tag/ dir names against a real map (see the DEBUG print) before trusting the treasure rows.
 (B) Grace name: pulled from elden_ring_artifacts/REGION_ID_MAP.md (BonfireWarp id -> name). If that
     parse yields few names, drop a grace_names.tsv (warpUnlockFlag<TAB>name) next to grace_flags.tsv
     and it is used instead. A grace with no name is emitted with a blank name and build_nearest_grace
     ignores it.
"""
import argparse
import csv
import glob
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AR = os.path.join(ROOT, "elden_ring_artifacts")
MSB_DIRS = [os.path.join(AR, "map"), os.path.join(AR, "mapstudio")]   # search both; prefer whichever has the map
VV = os.path.join(AR, "vanilla_params")   # ItemLotParam*/NpcParam CSVs (same dir datamine_msb_item_regions uses)
OUT = os.path.join(ROOT, "greenfield", "item_grace_coords.tsv")

_POS_RE = re.compile(r"<Position>\s*<X>(-?[\d.eE+]+)</X>\s*<Y>(-?[\d.eE+]+)</Y>\s*<Z>(-?[\d.eE+]+)</Z>")
_NPCID_RE = re.compile(r"<NPCParamID>\s*(-?\d+)\s*</NPCParamID>")


# ---- params (mirrors datamine_msb_item_regions helpers) -----------------------------------------
def _lot2flags():
    """ItemLotParam_map + _enemy row ID -> [flags] (nonzero getItemFlagId*)."""
    out = {}
    for csv_name in ("ItemLotParam_map.csv", "ItemLotParam_enemy.csv"):
        path = os.path.join(VV, csv_name)
        if not os.path.isfile(path):
            sys.stderr.write(f"missing {path}\n")
            continue
        with open(path, newline="", encoding="utf-8", errors="replace") as fh:
            rd = csv.DictReader(fh)
            fcols = [c for c in (rd.fieldnames or []) if c and c.startswith("getItemFlagId")]
            for row in rd:
                try:
                    rid = int(row["ID"])
                except (KeyError, TypeError, ValueError):
                    continue
                fl = sorted({int(row[c]) for c in fcols if row.get(c) not in (None, "", "0", "-1")})
                if fl:
                    out.setdefault(rid, []).extend(fl)
    return out


def _npc2lots():
    """NpcParam ID -> [lot_id] (enemy + map lots)."""
    path = os.path.join(VV, "NpcParam.csv")
    out = {}
    if not os.path.isfile(path):
        sys.stderr.write(f"missing {path}\n")
        return out
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        for row in csv.DictReader(fh):
            try:
                nid = int(row["ID"])
            except (KeyError, TypeError, ValueError):
                continue
            for col in ("itemLotId_enemy", "itemLotId_map"):
                v = row.get(col)
                if v not in (None, "", "0", "-1"):
                    try:
                        out.setdefault(nid, []).append(int(v))
                    except ValueError:
                        pass
    return out


def _msb_sub(map_id, *sub):
    for m in MSB_DIRS:
        d = os.path.join(m, f"{map_id}-msb-dcx", *sub)
        if os.path.isdir(d):
            return d
    return None


# ---- item positions -----------------------------------------------------------------------------
def _enemy_item_rows(map_id, lot2flags, npc2lots):
    """Enemy parts carry <NPCParamID> + <Position>; join NPC -> lots -> flags."""
    d = _msb_sub(map_id, "Part", "Enemy")
    rows = []
    if d is None:
        return rows
    for fp in glob.glob(os.path.join(d, "*.xml")):
        try:
            t = open(fp, encoding="utf-8-sig", errors="replace").read()
        except OSError:
            continue
        nid = _NPCID_RE.search(t)
        pos = _POS_RE.search(t)
        if not (nid and pos):
            continue
        xyz = (pos.group(1), pos.group(2), pos.group(3))
        for lot in npc2lots.get(int(nid.group(1)), ()):
            for flag in lot2flags.get(lot, ()):
                rows.append((flag, map_id, xyz))
    return rows


def _part_position_index(map_id):
    """part Name -> (x,y,z) for the part dirs a Treasure event can reference. (A) VALIDATE tag names."""
    idx = {}
    for sub in ("Asset", "DummyAsset", "Object", "DummyObject"):
        d = _msb_sub(map_id, "Part", sub)
        if d is None:
            continue
        for fp in glob.glob(os.path.join(d, "*.xml")):
            try:
                t = open(fp, encoding="utf-8-sig", errors="replace").read()
            except OSError:
                continue
            nm = re.search(r"<Name>([^<]*)</Name>", t)
            pos = _POS_RE.search(t)
            if nm and pos:
                idx[nm.group(1).strip()] = (pos.group(1), pos.group(2), pos.group(3))
    return idx


def _treasure_item_rows(map_id, lot2flags, part_idx, debug=False):
    """Event/Treasure -> ItemLotID + referenced part -> that part's position. (A) VALIDATE."""
    import xml.etree.ElementTree as ET
    d = _msb_sub(map_id, "Event", "Treasure")
    rows = []
    if d is None:
        return rows
    for fp in glob.glob(os.path.join(d, "*.xml")):
        try:
            r = ET.parse(fp).getroot()
        except (ET.ParseError, OSError):
            continue
        lid = (r.findtext("ItemLotID") or "").strip()
        if not lid or lid in ("-1", "0"):
            continue
        # a Position directly on the event wins; else resolve the referenced part by name
        xyz = None
        pm = _POS_RE.search(ET.tostring(r, encoding="unicode"))
        if pm:
            xyz = (pm.group(1), pm.group(2), pm.group(3))
        else:
            for tag in ("TreasurePartName", "PartName", "AttachPartName", "PartName1"):
                nm = (r.findtext(tag) or "").strip()
                if nm and nm in part_idx:
                    xyz = part_idx[nm]
                    break
        if debug and not xyz:
            sys.stderr.write(f"[treasure] {map_id} lot {lid}: no position resolved ({os.path.basename(fp)})\n")
        if xyz is None:
            continue
        for flag in lot2flags.get(int(lid), ()):
            rows.append((flag, map_id, xyz))
    return rows


# ---- grace positions + names --------------------------------------------------------------------
def _grace_names():
    """warpUnlockFlag -> human name. Prefer a hand grace_names.tsv; else parse REGION_ID_MAP.md. (B)."""
    names = {}
    gn = os.path.join(AR, "grace_names.tsv")
    if os.path.isfile(gn):
        for row in csv.DictReader(open(gn, encoding="utf-8-sig"), delimiter="\t"):
            try:
                names[int(row["warpUnlockFlag"])] = (row.get("name") or "").strip()
            except (KeyError, ValueError, TypeError):
                pass
        return names
    rid = os.path.join(AR, "REGION_ID_MAP.md")
    if os.path.isfile(rid):
        # tolerant: any line pairing a warp/bonfire id with a name; refine to the real md columns on-box.
        for ln in open(rid, encoding="utf-8", errors="replace"):
            m = re.search(r"\b(7\d{4}|71\d{3})\b.*?\|\s*([^|]+?)\s*\|", ln)
            if m:
                names.setdefault(int(m.group(1)), m.group(2).strip())
    return names


def _grace_rows():
    """(flag, mapTile, (x,y,z)) from the positioned grace_flags.tsv (arena_graces uses the same file)."""
    fp = os.path.join(AR, "grace_flags.tsv")
    out = []
    if not os.path.isfile(fp):
        sys.stderr.write(f"missing {fp} (need the POSITIONED grace_flags.tsv from artifacts)\n")
        return out
    for row in csv.DictReader(open(fp, encoding="utf-8"), delimiter="\t"):
        try:
            fl = int(row["warpUnlockFlag"])
            xyz = (row["posX"], row["posY"], row["posZ"])
        except (KeyError, ValueError, TypeError):
            continue
        if fl <= 200:
            continue
        out.append((fl, row["mapTile"], xyz))
    return out


def _full_map(tile):
    return tile + ("_00" if tile[:3] in ("m60", "m61") else "_00_00")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--maps", nargs="*", help="restrict to these map ids (e.g. m20_00 m20_01)")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args(argv)

    lot2flags = _lot2flags()
    npc2lots = _npc2lots()
    gnames = _grace_names()

    # enumerate maps present as witchy dirs
    maps = set()
    for m in MSB_DIRS:
        for p in glob.glob(os.path.join(m, "m*-msb-dcx")):
            mid = os.path.basename(p)[:-len("-msb-dcx")]
            maps.add(mid)
    if args.maps:
        want = set(args.maps)
        maps = {mid for mid in maps if mid in want or mid[: mid.rfind("_", 0, mid.rfind("_"))] in want or any(mid.startswith(w) for w in want)}

    item_rows = []
    for mid in sorted(maps):
        part_idx = _part_position_index(mid)
        item_rows += _enemy_item_rows(mid, lot2flags, npc2lots)
        item_rows += _treasure_item_rows(mid, lot2flags, part_idx, debug=args.debug)

    # de-dup (flag,map) keeping first position
    seen = set()
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# AUTO-GENERATED by tools/datamine_item_grace_coords.py (run on Windows). Map-local XYZ.\n")
        fh.write("kind\tkey\tmap_id\tx\ty\tz\tname\n")
        for flag, mid, (x, y, z) in item_rows:
            k = (flag, mid)
            if k in seen:
                continue
            seen.add(k)
            fh.write(f"item\t{flag}\t{mid}\t{x}\t{y}\t{z}\t\n")
        gwritten = named = 0
        for fl, tile, (x, y, z) in _grace_rows():
            nm = gnames.get(fl, "")
            named += 1 if nm else 0
            gwritten += 1
            fh.write(f"grace\t{fl}\t{_full_map(tile)}\t{x}\t{y}\t{z}\t{nm}\n")
    print(f"wrote {args.out}: {len(seen)} item rows, {gwritten} grace rows ({named} named). "
          f"Now run tools/build_nearest_grace.py.")
    if named == 0:
        sys.stderr.write("WARNING: 0 graces got a name -- fix (B): supply grace_names.tsv or the "
                         "REGION_ID_MAP.md parse. Without names build_nearest_grace emits nothing.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
