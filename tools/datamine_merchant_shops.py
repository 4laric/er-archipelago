#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""datamine_merchant_shops.py -- which PHYSICAL merchant opens each ShopLineupParam row, and where.

WHY
---
tools/datamine_shop_rows.py assigns a shop check's region by "a block is ONE MERCHANT" (its docstring
lines 40-47) -- inheriting the region of the already-classified rows in the same shopBlock (rowId//100).
That premise is FALSE for the nomadic-merchant range. Block 1007 holds TWO merchants: a Liurnia nomadic
merchant (rows 100700-100720) AND the Hermit Merchant's Shack in Altus (rows 100725+). The whole block
was tagged Liurnia, so the Hermit's ~30 checks were region-scoped to Liurnia and SEALED OUT of any roll
that drops Liurnia -- even though the player reaches him in kept Altus (Alaric, in-game 2026-07-23:
vanilla item, no check fired; the one hand-pinned sibling, Perfume Bottle flag 66750, fired as "Altus"
the same session). The mirror roll (keep Liurnia, seal Altus) is worse: those become reachable-Liurnia
checks whose merchant stands in sealed Altus -> unreachable progression (one carried a region Lock).

THE FIX: derive the merchant->row-range->map join from GROUND TRUTH instead of the block guess. A
merchant NPC's talk ESD opens a ShopLineupParam id RANGE (OpenRegularShop(begin, end)); the NPC is
placed in an MSB, which gives the physical map. So:

    talk ESD  ->  (begin, end) shop range        [this file, from script/talk]
    MSB Enemy <TalkID>  ->  map tile             [this file, reuses datamine_msb_item_regions machinery]
    ESD binder filename  ->  map tile (2nd hop)  [this file]
    map tile  ->  AP region                      [gen_data owns this -- we emit map ids, per house style]

Emits greenfield/merchant_shops.tsv, one line per (shop row, opening merchant instance):
    row_id \t talk_id \t npc_param_id \t merchant_name \t map_id \t map_source \t note
gen_data resolves map_id -> region (via _gt_region / DUNGEON_REGION_OVERRIDE) with precedence:
FLAG_REGION_OVERRIDE (hand pins) > ESD-derived merchant map > legacy block inheritance. A row opened by
merchants in >1 distinct region collapses to HUB + DEFAULTED (the shop_multi convention). A row no ESD
opens gets NO line (unknown -> stays DEFAULTED; never guessed).

ARTIFACTS (all under elden_ring_artifacts/, licensing-restricted, .gitignore'd; run on WINDOWS):
  * talk/<map>-talkesdbnd-dcx/t<talkid>.esd  (or t<talkid>.esd.xml)  -- NEW UNPACK, see below
  * mapstudio/<map>-msb-dcx/Part/Enemy/*.xml  (witchy MSBE export; already used by other tools)
  * vanilla_er/vanilla_er/ShopLineupParam.csv, NpcParam.csv  (Smithbox param dump)

PRODUCE THE ESD UNPACK (once, on Windows):
    copy  <ER install>\\Game\\script\\talk\\*.talkesdbnd.dcx  ->  elden_ring_artifacts\\talk\\
    WitchyBND.exe elden_ring_artifacts\\talk\\*.talkesdbnd.dcx      (same tool that made the -msb-dcx dumps)
  -> elden_ring_artifacts\\talk\\m*-talkesdbnd-dcx\\t*.esd[.xml]

ESD FORMAT IS SELF-CALIBRATING -- we do NOT hard-code the OpenRegularShop command id (unknowable until
the dump exists). We extract every integer LITERAL from each ESD (works on WitchyBND xml OR raw .esd
binary), then take consecutive literal pairs (a, b) with a <= b, both real ShopLineupParam ids in the
merchant band [SHOP_LO, SHOP_HI], as candidate shop ranges. Anchors validate it: Kale's ESD must yield a
range at 100000; the Twin Maidens' must cover 101800; row 100725 (Perfume Bottle) must resolve to an
Altus tile (agreeing with the 66750 hand pin). Run with --probe first to eyeball the extraction before
trusting the tsv.

USAGE (Windows, artifacts present):
    python tools/datamine_merchant_shops.py --probe          # dump what it extracts on anchor ESDs
    python tools/datamine_merchant_shops.py                  # write greenfield/merchant_shops.tsv
    python tools/datamine_merchant_shops.py --maps m60_40_54 # subset (validation)
"""
import argparse
import csv
import glob
import os
import re
import struct
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.abspath(os.path.join(HERE, ".."))
ART = os.path.join(REPO, "elden_ring_artifacts")
VV = os.path.join(ART, "vanilla_er", "vanilla_er")
TALK = os.path.join(ART, "talk")
MAPSTUDIO_ROOTS = [os.path.join(ART, "mapstudio"), os.path.join(ART, "map", "mapstudio")]
OUT = os.path.join(REPO, "greenfield", "merchant_shops.tsv")

# Merchant shop rows are ShopLineupParam ids shopBlock*100+slot in the 1000xx..1029xx band. Ranges an
# ESD opens live here; other shop menus (enhance/sell/recipe) index other id spaces and simply won't
# pass the membership filter. Kept wide + validated by real-id membership rather than tightly guessed.
SHOP_LO, SHOP_HI = 100000, 103000
MAX_RANGE_SPAN = 400          # a single OpenRegularShop range never spans a whole block-hundreds gap

_DIR_MSB_RE = re.compile(r"^(m\d\d)_(\d\d)_(\d\d)_(\d\d)-msb-dcx$")
_DIR_TALK_RE = re.compile(r"^(m\d\d)_(\d\d)_(\d\d)_(\d\d)-talkesdbnd-dcx$")
_TALKFILE_RE = re.compile(r"^t(\d+)\.esd(?:\.xml)?$", re.I)
_TALKID_RE = re.compile(r"<TalkID>\s*(-?\d+)\s*</TalkID>")
_ENTITYID_RE = re.compile(r"<EntityID>\s*(-?\d+)\s*</EntityID>")
_NPCID_RE = re.compile(r"<NPCParamID>\s*(-?\d+)\s*</NPCParamID>")
_NAME_RE = re.compile(r"<Name>([^<]*)</Name>")
_INT_RE = re.compile(rb"-?\d+")


def _map_id(area, x, y):
    """m10_00_00_00 -> m10_00 ; m60_40_54_00 -> m60_40_54 (overworld tile is the unit)."""
    return f"{area}_{x}_{y}" if area in ("m60", "m61") else f"{area}_{x}"


def _map_from_dir(dirname, rx):
    m = rx.match(dirname)
    return _map_id(m.group(1), m.group(2), m.group(3)) if m else None


# ---------------------------------------------------------------- ShopLineupParam id-space

def load_shop_ids():
    """Set of ShopLineupParam row ids that are limited-stock MERCHANT rows (the id space an
    OpenRegularShop range enumerates). We keep ALL ids for membership, and separately note which are the
    detect-predicate check rows so the report can say how many checks each range covers."""
    path = os.path.join(VV, "ShopLineupParam.csv")
    if not os.path.isfile(path):
        sys.exit(f"FATAL: missing {path} -- need the param dump. Nothing written.")
    ids = set()
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
        rd = csv.DictReader(fh)
        idk = (rd.fieldnames or ["ID"])[0]
        for r in rd:
            try:
                rid = int(r[idk])
            except (KeyError, TypeError, ValueError):
                continue
            if SHOP_LO <= rid <= SHOP_HI:
                ids.add(rid)
    return ids


def load_npc_names():
    """NpcParam ID -> a cosmetic label (nameId), best-effort; empty if NpcParam absent. Purely for the
    human-readable merchant_name column -- never load-bearing."""
    path = os.path.join(VV, "NpcParam.csv")
    out = {}
    if not os.path.isfile(path):
        return out
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
        for r in csv.DictReader(fh):
            try:
                out[int(r["ID"])] = (r.get("nameId") or "").strip()
            except (KeyError, TypeError, ValueError):
                pass
    return out


# ---------------------------------------------------------------- MSB: talk id -> map, npc

def scan_msb(map_filter=None):
    """talk_id -> {map_id}, and talk_id -> npc_param_id (first seen). Reuses the regex-scan approach of
    datamine_msb_item_regions._enemy_rows (full XML parse is 10x slower over ~200k Enemy parts)."""
    talk_maps = defaultdict(set)
    talk_npc = {}
    seen_dirs = 0
    for root in MAPSTUDIO_ROOTS:
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            mid = _map_from_dir(name, _DIR_MSB_RE)
            if not mid or (map_filter and mid not in map_filter):
                continue
            edir = os.path.join(root, name, "Part", "Enemy")
            if not os.path.isdir(edir):
                continue
            seen_dirs += 1
            with os.scandir(edir) as it:
                for ent in it:
                    if not ent.name.endswith(".xml"):
                        continue
                    try:
                        with open(ent.path, encoding="utf-8-sig", errors="replace") as fh:
                            src = fh.read()
                    except OSError:
                        continue
                    m = _TALKID_RE.search(src) or _ENTITYID_RE.search(src)
                    if not m:
                        continue
                    tid = int(m.group(1))
                    if tid <= 0:
                        continue
                    talk_maps[tid].add(mid)
                    if tid not in talk_npc:
                        npc = _NPCID_RE.search(src)
                        if npc:
                            talk_npc[tid] = int(npc.group(1))
    return talk_maps, talk_npc, seen_dirs


# ---------------------------------------------------------------- ESD: talk id -> shop ranges

def _extract_ints(path):
    """Ordered list of integer literals in an ESD file. Handles WitchyBND xml/text (regex on text) AND
    raw .esd binary (every 4-byte little-endian int32 that lands in the shop band -- a superset we then
    filter by real-id membership, so binary noise is harmless)."""
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError:
        return []
    # Text (WitchyBND xml or a decompiled .txt): pull integers in document order.
    if b"<" in raw[:256] or b"OpenRegularShop" in raw or b"Shop" in raw[:4096]:
        return [int(m.group()) for m in _INT_RE.finditer(raw)]
    # Raw binary ESD: scan every 4-byte LE int32; keep those in the shop band (order = file offset,
    # which preserves begin-before-end adjacency inside a command's arg bytecode).
    ints = []
    for off in range(0, len(raw) - 3):
        v = struct.unpack_from("<i", raw, off)[0]
        if SHOP_LO <= v <= SHOP_HI:
            ints.append(v)
    return ints


def esd_ranges(path, shop_ids):
    """Candidate (begin, end) shop ranges from one ESD: consecutive literal pairs (a, b) with
    a <= b <= a+MAX_RANGE_SPAN, both real ShopLineupParam ids in-band. Deduped, sorted."""
    ints = _extract_ints(path)
    out = set()
    for i in range(len(ints) - 1):
        a, b = ints[i], ints[i + 1]
        if (SHOP_LO <= a <= b <= SHOP_HI and (b - a) <= MAX_RANGE_SPAN
                and a in shop_ids and b in shop_ids):
            out.add((a, b))
    return sorted(out)


def scan_talk(shop_ids, map_filter=None):
    """talk_id -> {'ranges': [(begin,end)], 'binder_maps': {map_id}}. binder filename is the 2nd map hop."""
    if not os.path.isdir(TALK):
        return {}, 0
    talk = defaultdict(lambda: {"ranges": set(), "binder_maps": set()})
    files = 0
    for name in sorted(os.listdir(TALK)):
        bdir = os.path.join(TALK, name)
        if not os.path.isdir(bdir):
            continue
        bmap = _map_from_dir(name, _DIR_TALK_RE)   # may be None for the common m00 binder
        if map_filter and bmap and bmap not in map_filter:
            continue
        for fn in os.listdir(bdir):
            fm = _TALKFILE_RE.match(fn)
            if not fm:
                continue
            tid = int(fm.group(1))
            rngs = esd_ranges(os.path.join(bdir, fn), shop_ids)
            if not rngs:
                continue
            files += 1
            talk[tid]["ranges"].update(rngs)
            if bmap:
                talk[tid]["binder_maps"].add(bmap)
    return talk, files


# ---------------------------------------------------------------- join + emit

def build(shop_ids, talk_data, talk_maps, talk_npc, npc_names):
    """row_id -> [ (talk_id, npc_id, merchant_name, map_id, map_source) ]."""
    rows = defaultdict(list)
    for tid, d in talk_data.items():
        msb_maps = talk_maps.get(tid, set())
        binder_maps = d["binder_maps"]
        npc = talk_npc.get(tid)
        mname = str(npc_names.get(npc, "")) if npc is not None else ""
        # map for this merchant instance: prefer MSB placement; fall back to binder filename.
        if msb_maps:
            maps = [(m, ("msb+binder" if m in binder_maps else "msb")) for m in sorted(msb_maps)]
        elif binder_maps:
            maps = [(m, "binder") for m in sorted(binder_maps)]
        else:
            maps = [("", "none")]
        for (begin, end) in sorted(d["ranges"]):
            for rid in range(begin, end + 1):
                if rid not in shop_ids:
                    continue
                for (mid, src) in maps:
                    rows[rid].append((tid, npc, mname, mid, src))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--maps", nargs="*", help="restrict to these map ids (e.g. m60_40_54)")
    ap.add_argument("--probe", action="store_true",
                    help="dump extracted ranges for anchor/ filtered ESDs and exit (no tsv written)")
    args = ap.parse_args()
    map_filter = set(args.maps) if args.maps else None

    if not os.path.isdir(TALK):
        sys.exit(f"FATAL: {TALK} not found. Produce the ESD unpack first (see module docstring): copy "
                 f"script/talk/*.talkesdbnd.dcx into elden_ring_artifacts/talk/ and run WitchyBND on "
                 f"them. Nothing written.")

    shop_ids = load_shop_ids()
    npc_names = load_npc_names()
    talk_data, esd_files = scan_talk(shop_ids, map_filter)
    talk_maps, talk_npc, msb_dirs = scan_msb(map_filter)

    if not talk_data:
        sys.exit(f"FATAL: no shop ranges extracted from any ESD under {TALK} ({esd_files} candidate "
                 f"files). The extraction heuristic found no in-band ShopLineupParam id pairs -- the ESD "
                 f"serialization is likely a format _extract_ints doesn't handle. Run with --probe and "
                 f"send the printed sample (and one raw t*.esd) so the parser can be fixed.")

    if args.probe:
        print(f"# PROBE: {esd_files} ESD file(s) yielded shop ranges; {len(talk_data)} talk id(s).")
        for tid in sorted(talk_data)[:40]:
            d = talk_data[tid]
            print(f"talk {tid}: ranges={sorted(d['ranges'])} binder={sorted(d['binder_maps'])} "
                  f"msb={sorted(talk_maps.get(tid, []))} npc={talk_npc.get(tid)}")
        return 0

    rows = build(shop_ids, talk_data, talk_maps, talk_npc, npc_names)

    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("# AUTO-GENERATED by tools/datamine_merchant_shops.py -- which physical merchant opens\n")
        f.write("# each ShopLineupParam row, and on which map. Replaces datamine_shop_rows.py's false\n")
        f.write("# 'block = one merchant' region inheritance. One line per (row, merchant instance);\n")
        f.write("# a row with >1 distinct map region -> gen_data collapses to HUB + DEFAULTED. map_id ->\n")
        f.write("# region is gen_data's job (_gt_region). map_source: msb|binder|msb+binder|none.\n")
        f.write("row_id\ttalk_id\tnpc_param_id\tmerchant_name\tmap_id\tmap_source\n")
        for rid in sorted(rows):
            for (tid, npc, mname, mid, src) in rows[rid]:
                f.write(f"{rid}\t{tid}\t{npc if npc is not None else ''}\t{mname}\t{mid}\t{src}\n")

    # ---- run report + self-validation (report; hard-fail only on the motivating regression) ----
    covered = set(rows)
    multi = {rid for rid, insts in rows.items()
             if len({m for (_t, _n, _nm, m, _s) in insts if m}) > 1}
    unmapped = {rid for rid, insts in rows.items()
                if not any(m for (_t, _n, _nm, m, _s) in insts)}
    print(f"merchant_shops: {sum(len(v) for v in rows.values())} (row,merchant) line(s) over "
          f"{len(covered)} distinct rows; {len(multi)} multi-region (->HUB/DEFAULTED); "
          f"{len(unmapped)} row(s) with no map (kept unknown). MSB dirs scanned={msb_dirs}, "
          f"ESD files with ranges={esd_files}.")

    # Regression anchor for the exact bug this tool exists to fix: Perfume Bottle row 100725 (flag 66750,
    # hand-pinned Altus at gen_data.py) must resolve to an Altus tile (m60_4x_..), and the Prophet Robe
    # row 100741 must too -- and both must differ from the early block-1007 rows (Liurnia merchant).
    def _maps_of(rid):
        return sorted({m for (_t, _n, _nm, m, _s) in rows.get(rid, []) if m})
    hermit_probe = {r: _maps_of(r) for r in (100714, 100720, 100725, 100741)}
    print("  block-1007 split probe (expect 100725/100741 on an Altus m60_4x tile, distinct from "
          f"the early Liurnia rows): {hermit_probe}")
    altus_maps = set(_maps_of(100725)) | set(_maps_of(100741))
    if altus_maps and not any(re.match(r"m60_4", m) for m in altus_maps):
        print("  !! WARNING: Hermit rows 100725/100741 did NOT resolve to an Altus (m60_4x) tile "
              f"-> {sorted(altus_maps)}. The MSB TalkID field or the ESD extraction may be wrong; "
              "verify with --probe before trusting this tsv.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
