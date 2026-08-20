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
import collections
import csv
import glob
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AR = os.path.join(ROOT, "elden_ring_artifacts")


def _param_dir(root):
    """The vanilla-param CSV dir under an artifacts root. TWO layouts exist in the wild --
    `vanilla_params/` (this tool's original expectation) and `vanilla_er/vanilla_er/` (the
    gen_inputs bundle and datamine_msb_item_regions). The old comment here claimed they were the
    same dir; they never were, and on 2026-08-19 that lie cost a run: every param read printed
    `missing ...` and the tool still wrote a 1,436-row tsv over a 5,295-row one. Prefer whichever
    actually holds ItemLotParam_map.csv; fall back to the first so the error message names a path.
    """
    cands = [os.path.join(root, "vanilla_params"),
             os.path.join(root, "vanilla_er", "vanilla_er")]
    for c in cands:
        if os.path.isfile(os.path.join(c, "ItemLotParam_map.csv")):
            return c
    return cands[0]


def _msb_dirs(root):
    # map/ + mapstudio/ + the root itself (datamine_msb_item_regions scans the root too, and a
    # witchy export dropped there should mean the same thing to both tools).
    return [os.path.join(root, "map"), os.path.join(root, "mapstudio"), root]


MSB_DIRS = _msb_dirs(AR)
VV = _param_dir(AR)
OUT = os.path.join(ROOT, "greenfield", "item_grace_coords.tsv")


def _set_artifacts_root(path):
    """`--artifacts`: point every input at a different artifacts tree (same flag, same semantics
    as datamine_msb_item_regions). Output stays repo-relative; `--out` moves it."""
    global AR, MSB_DIRS, VV
    AR = os.path.abspath(path)
    MSB_DIRS = _msb_dirs(AR)
    VV = _param_dir(AR)

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


def _treasure_item_rows(map_id, lot2flags):
    """Event/Treasure -> ItemLotID (-> flags) + TreasurePartName -> that Asset/DummyAsset part's
    Position. Reads ONLY the referenced part files (not the whole Part/Asset directory), so it stays
    fast -- the earlier full-index version re-parsed every asset in every map and was CPU-bound.
    VALIDATED against real MSBs (a Belurat treasure resolves to a Belurat grace at ~50m)."""
    d = _msb_sub(map_id, "Event", "Treasure")
    rows = []
    if d is None:
        return rows
    partdirs = [pd for pd in (_msb_sub(map_id, "Part", s) for s in ("Asset", "DummyAsset")) if pd]
    poscache = {}

    def _partpos(name):
        if name in poscache:
            return poscache[name]
        p = None
        for pd in partdirs:
            fp = os.path.join(pd, name + ".xml")
            if os.path.isfile(fp):
                m = _POS_RE.search(open(fp, encoding="utf-8-sig", errors="replace").read())
                if m:
                    p = (m.group(1), m.group(2), m.group(3))
                break
        poscache[name] = p
        return p

    for fp in glob.glob(os.path.join(d, "*.xml")):
        try:
            t = open(fp, encoding="utf-8-sig", errors="replace").read()
        except OSError:
            continue
        lid = re.search(r"<ItemLotID>(-?\d+)</ItemLotID>", t)
        if not lid or lid.group(1) in ("-1", "0"):
            continue
        lot = int(lid.group(1))
        if lot not in lot2flags:
            continue
        pn = re.search(r"<TreasurePartName>([^<]*)</TreasurePartName>", t)
        xyz = _partpos(pn.group(1).strip()) if pn else None
        if xyz is None:
            continue
        for flag in lot2flags[lot]:
            rows.append((flag, map_id, xyz))
    return rows


# ---- grace positions + names --------------------------------------------------------------------
def _grace_names():
    """warpUnlockFlag -> grace name, from committed greenfield/grace_names.tsv
    (tools/datamine_grace_names.py: BonfireWarpParam.textId1 -> PlaceName FMG)."""
    names = {}
    gn = os.path.join(ROOT, "greenfield", "grace_names.tsv")
    if os.path.isfile(gn):
        for ln in open(gn, encoding="utf-8-sig"):
            if ln.startswith("#") or not ln.strip():
                continue
            p = ln.rstrip("\n").split("\t")
            if len(p) >= 2 and p[0].strip().isdigit():
                names[int(p[0])] = p[1].strip()
    return names


def _grace_rows():
    """(flag, mapTile, (x,y,z)): position from BonfireWarpParam.posX/Y/Z, tile from committed
    greenfield/grace_flags.tsv. VALIDATED: these positions are in the SAME map-local frame as the MSB
    Part positions (a Belurat treasure resolves to the correct Belurat grace at a sane distance)."""
    tile = {}
    gf = os.path.join(ROOT, "greenfield", "grace_flags.tsv")
    if os.path.isfile(gf):
        for row in csv.DictReader(open(gf, encoding="utf-8-sig"), delimiter="\t"):
            try:
                tile[int(row["warpUnlockFlag"])] = row["mapTile"].strip()
            except (KeyError, ValueError, TypeError):
                pass
    out = []
    bwp = os.path.join(VV, "BonfireWarpParam.csv")
    if not os.path.isfile(bwp):
        sys.stderr.write(f"missing {bwp}\n")
        return out
    for row in csv.DictReader(open(bwp, encoding="utf-8", errors="replace")):
        fl = row.get("eventflagId", "")
        if not fl.lstrip("-").isdigit() or int(fl) <= 200 or int(fl) not in tile:
            continue
        out.append((int(fl), tile[int(fl)], (row["posX"], row["posY"], row["posZ"])))
    return out


def _full_map(tile):
    return tile + ("_00" if tile[:3] in ("m60", "m61") else "_00_00")


def _merchant_item_rows():
    """Shop checks get the MERCHANT's position -- one row per (check flag, merchant instance).

    The merchant has a location (Alaric): a shop check is not non-spatial, it is MULTI-spatial. This
    reads two committed tsvs and needs NO artifacts, so it costs nothing on any run:
      merchant_shops.tsv  row_id -> (map_id, pos_x/y/z)   [positions added 2026-07-26]
      shop_rows.tsv       row_id -> stock_flag            [the check's flag]

    ⭐ It lives HERE, in the tool that OWNS item_grace_coords.tsv, on purpose. A separate tool
    appending to this file would be wiped by the next run of this one -- the same "an earlier tool
    silently deletes a later tool's work" bug that --refresh-names had.
    """
    gf = os.path.join(ROOT, "greenfield")

    def _tsv(name):
        path = os.path.join(gf, name)
        if not os.path.isfile(path):
            return None
        hdr, out = None, []
        with open(path, encoding="utf-8-sig") as fh:
            for ln in fh:
                if ln.startswith("#"):
                    continue
                cols = ln.rstrip("\n").split("\t")
                if hdr is None:
                    hdr = cols
                    continue
                out.append(dict(zip(hdr, cols)))
        return out

    ms, sr = _tsv("merchant_shops.tsv"), _tsv("shop_rows.tsv")
    if ms is None or sr is None:
        print("[coords] merchant rows SKIPPED: merchant_shops.tsv or shop_rows.tsv missing")
        return [], collections.Counter()
    flag_of = {}
    for r in sr:
        f = (r.get("stock_flag") or "").strip()
        if f.isdigit():
            flag_of.setdefault((r.get("row_id") or "").strip(), f)
    out, tally = [], collections.Counter()
    for r in ms:
        x = (r.get("pos_x") or "").strip()
        if not x:
            tally["merchant instance with no position (map came from the binder, no Part/Enemy)"] += 1
            continue
        f = flag_of.get((r.get("row_id") or "").strip())
        if not f:
            tally["merchant row whose row_id has no stock_flag in shop_rows"] += 1
            continue
        out.append((f, (r.get("map_id") or "").strip(),
                    (x, (r.get("pos_y") or "").strip(), (r.get("pos_z") or "").strip())))
    return out, tally


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--maps", nargs="*", help="restrict to these map ids (e.g. m20_00 m20_01)")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--artifacts", metavar="DIR",
                    help="use this artifacts tree instead of <repo>/elden_ring_artifacts (accepts "
                         "both param layouts: vanilla_params/ and vanilla_er/vanilla_er/; MSB dirs "
                         "under map/, mapstudio/, or the root)")
    ap.add_argument("--merge", action="store_true",
                    help="UNION with the committed tsv: item rows for maps scanned THIS run are "
                         "refreshed, item rows for absent maps are carried forward, and grace rows "
                         "are kept when this run produced none. Batch witchy exports compose "
                         "instead of clobbering (see the degenerate-scan guard's incident).")
    ap.add_argument("--force", action="store_true",
                    help="write the tsv even when the scan is DEGENERATE (params missing, zero "
                         "maps, or far fewer rows than the committed file). Without this the tool "
                         "refuses instead of silently shrinking ground truth.")
    ap.add_argument("--enemy", action="store_true",
                    help="also scan Part/Enemy for enemy-drop checks (slower -- reads every enemy in "
                         "every map; treasure alone covers most checks)")
    args = ap.parse_args(argv)
    if args.artifacts:
        if not os.path.isdir(args.artifacts):
            sys.exit(f"FATAL: --artifacts {args.artifacts} is not a directory")
        _set_artifacts_root(args.artifacts)

    print("[coords] reading params...", flush=True)
    lot2flags = _lot2flags()
    npc2lots = _npc2lots() if args.enemy else {}
    gnames = _grace_names()

    # enumerate maps present as witchy dirs (basename set de-dups map/ vs mapstudio/)
    maps = set()
    for m in MSB_DIRS:
        for p in glob.glob(os.path.join(m, "m*-msb-dcx")):
            maps.add(os.path.basename(p)[:-len("-msb-dcx")])
    if args.maps:
        want = set(args.maps)
        maps = {mid for mid in maps if mid in want or mid[: mid.rfind("_", 0, mid.rfind("_"))] in want or any(mid.startswith(w) for w in want)}
    maps = sorted(maps)
    total = len(maps)
    print(f"[coords] {total} maps (enemy scan: {'on' if args.enemy else 'off'})", flush=True)

    item_rows = []
    _merch_rows, _merch_tally = _merchant_item_rows()
    print("[coords] merchant instances with a position: %d%s"
          % (len(_merch_rows), ("  " + repr(dict(_merch_tally))) if _merch_tally else ""))
    for i, mid in enumerate(maps, 1):
        if args.enemy:
            item_rows += _enemy_item_rows(mid, lot2flags, npc2lots)
        item_rows += _treasure_item_rows(mid, lot2flags)
        if i % 25 == 0 or i == total:
            print(f"[coords] {i}/{total} maps  ({len(item_rows)} item rows so far)", flush=True)

    # de-dup (flag,map) keeping first position
    # Merchant rows come LAST in the de-dup order on purpose: a shop check that also has a real
    # world placement (a map_lot row) keeps the placement, and the merchant is the fallback.
    item_rows = item_rows + _merch_rows

    # ---- DEGENERATE-SCAN GUARD (2026-08-19). `open(..., "w")` below TRUNCATES the committed
    # ground truth before a single row lands, and this tool once did exactly that: params missing
    # (three `missing ...` lines scrolled past), ZERO maps found, and it still replaced a
    # 5,295-row tsv with 1,436 merchant rows while printing "wrote ...". A partial census read as
    # complete is worse than no census (the msb_item_regions coverage lesson) -- so a scan that is
    # obviously blind REFUSES to publish unless --force says the shrink is intended.
    carried_graces = []
    if args.merge and os.path.isfile(args.out):
        scanned = set(maps)
        new_keys = {(str(f), m) for f, m, _ in item_rows}
        carried = kept_scanned = 0
        with open(args.out, encoding="utf-8") as fh:
            for ln in fh:
                p = ln.rstrip("\n").split("\t")
                if len(p) < 6 or p[0] not in ("item", "grace"):
                    continue
                if p[0] == "grace":
                    carried_graces.append(p)
                    continue
                # an old item row survives when this run neither rescanned its map nor reproduced
                # its (flag, map). NEW rows win a collision (freshest position).
                mid_map = p[2][: p[2].rfind("_", 0, p[2].rfind("_"))] if p[2].count("_") >= 3 else p[2]
                if (p[1], p[2]) in new_keys or mid_map in scanned or p[2] in scanned:
                    kept_scanned += 1
                    continue
                item_rows.append((p[1], p[2], (p[3], p[4], p[5])))
                carried += 1
        print(f"[coords] merge: carried {carried} item row(s) forward; "
              f"{kept_scanned} superseded by this scan; {len(carried_graces)} grace row(s) held in reserve")

    prior_items = 0
    if os.path.isfile(args.out) and not args.maps:
        with open(args.out, encoding="utf-8") as fh:
            prior_items = sum(1 for ln in fh if ln.startswith("item\t"))
    fatal = []
    if not lot2flags:
        fatal.append(f"no ItemLotParam CSVs under {VV} (both layouts tried)")
    if total == 0:
        fatal.append("zero witchy MSB dirs found under " + ", ".join(MSB_DIRS))
    new_items = len({(f, m) for f, m, _ in item_rows})
    if not args.maps and prior_items and new_items < prior_items // 2:
        fatal.append(f"scan yields {new_items} item rows vs {prior_items} already committed -- "
                     "more than half the ground truth would vanish")
    if fatal and not args.force:
        sys.exit("FATAL: refusing to overwrite %s -- %s. Fix the inputs (or pass --force if the "
                 "shrink is deliberate)." % (args.out, "; ".join(fatal)))

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
        if gwritten == 0 and carried_graces:
            # BonfireWarpParam was unreadable this run; a merge must not amputate the grace half
            # (build_nearest_grace emits nothing without it).
            for p in carried_graces:
                nm = p[6] if len(p) > 6 else ""
                named += 1 if nm else 0
                gwritten += 1
                fh.write("\t".join(p[:6] + [nm]) + "\n")
    print(f"wrote {args.out}: {len(seen)} item rows, {gwritten} grace rows ({named} named). "
          f"Now run tools/build_nearest_grace.py.")
    if named == 0:
        sys.stderr.write("WARNING: 0 graces got a name -- fix (B): supply grace_names.tsv or the "
                         "REGION_ID_MAP.md parse. Without names build_nearest_grace emits nothing.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
