#!/usr/bin/env python3
r"""datamine_msb_item_regions.py -- authoritative flag -> map GROUND TRUTH for item checks.

A check's *physical map* is knowable without ever consulting region_map.csv or gen_data's region
assignment. That independence is the whole point: the §1 provenance oracle
(test_gf_region_provenance_oracle.py) cross-checks data.py against THIS, so a mis-pinned location is
caught mechanically instead of in-game. See SPEC-provenance-oracle-20260710.md.

THREE independent provenance chains, one per `source` column value:

  source=treasure   (v1)  the MSB *is* the map: a Treasure event places an ItemLotParam_map row
      physically in a known map block.
          mapstudio/<map>-msb-dcx/Event/Treasure/*.xml  -> <ItemLotID>
          -> ItemLotParam_map.ID -> getItemFlagId*      -> flag

  source=enemy      (v2)  an enemy is *placed* as a Part in a known map, and its NpcParam carries the
      lots it drops. Covers NPC invaders / named enemies whose drops carry acquisition flags.
          mapstudio/<map>-msb-dcx/Part/Enemy/*.xml      -> <NPCParamID>
          -> NpcParam.itemLotId_enemy -> ItemLotParam_enemy.ID -> getItemFlagId*  -> flag
          -> NpcParam.itemLotId_map   -> ItemLotParam_map.ID   -> getItemFlagId*  -> flag

  source=event      (v2)  BOSS drops (remembrances, great runes, boss rewards) are NOT NpcParam drops
      and NOT map Treasures -- they are awarded by EMEVD. The emevd file is per-map, so the map is
      still ground truth. Three award sites, all resolved mechanically (no hand tables):
        a) literal  AwardItemLot(N) / AwardItemsIncludingClients(N)  in m<XX>...emevd.dcx.js
        b) $InitializeCommonEvent(_, E, args...) where common_func's $Event(E, ...) has an
           `itemLotId`-named parameter (the boss handlers 90005860/861/880 et al) -> args[thatIdx]
        c) common.emevd registers flag-gated award events, e.g.
               $Event(1100, Default, function(eventFlagId, itemLotId, itemLotId2, eventFlagId2) {
                   ... WaitFor(EventFlag(eventFlagId)); AwardItemsIncludingClients(itemLotId); ... })
               $InitializeEvent(18, 1100, 9118, 10180, 0, 197);   // flag 9118 -> lot 10180
           so we build triggerFlag -> lots from common.emevd, then attribute those lots to whichever
           MAP emevd SETs the trigger flag ON (m14_00 sets 9118 -> lot 10180 -> flag 197, Rennala's
           Remembrance of the Full Moon Queen). That is the chain that would have caught the 2026-07-08
           "flag 197 pinned to Stormveil" mis-pin, which v1 (Treasure-only) was blind to.
      Lot ids are looked up in ItemLotParam_map first, then ItemLotParam_enemy.

Reads (all under elden_ring_artifacts, licensing-restricted, .gitignore'd):
  * mapstudio/<map>-msb-dcx/{Event/Treasure,Part/Enemy}/*.xml   (witchy MSBE export; dir name = map)
  * event/m*.emevd.dcx.js, event/common.emevd.dcx.js, event/common_func.emevd.dcx.js  (EMEVD decompile)
  * vanilla_er/vanilla_er/{ItemLotParam_map,ItemLotParam_enemy,NpcParam}.csv   (Smithbox param dump)

Emits greenfield/msb_flag_region.tsv:  flag \t map_id \t item_lot_id \t treasure_name \t source
`map_id` is the raw MSB/emevd map (e.g. m10_00, m60_51_57); mapping map_id -> gf region is the oracle's
job (kept OUT of here so the extractor stays a pure, independent ground-truth source). `treasure_name`
is the MSB Treasure part name for source=treasure, the MSB Enemy part name for source=enemy, and the
award site (e.g. `award`, `common90005860`, `trigflag9118`) for source=event.

A flag may legitimately appear in SEVERAL maps (an invader placed in three tiles, a shared/common drop
lot). Disambiguating that is the ORACLE's job (it excludes flags whose maps span >1 region); the
extractor just reports every placement it can prove.

Run on WINDOWS (mount is native there; the full 1000+ MSB scan is slow over the sandbox FUSE mount):
  python tools/datamine_msb_item_regions.py                       # all maps, all sources
  python tools/datamine_msb_item_regions.py --maps m10_00 m14_00  # subset (validation)
  python tools/datamine_msb_item_regions.py --sources event       # one chain only (fast)
"""
import argparse
import csv
import glob
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.abspath(os.path.join(HERE, ".."))
ART = os.path.join(REPO, "elden_ring_artifacts")
VV = os.path.join(ART, "vanilla_er", "vanilla_er")
EVT = os.path.join(ART, "event")
OUT = os.path.join(REPO, "greenfield", "msb_flag_region.tsv")

SOURCES = ("treasure", "enemy", "event")

_DIR_RE = re.compile(r"^(m\d\d)_(\d\d)_(\d\d)_(\d\d)-msb-dcx$")
_EMEVD_RE = re.compile(r"^(m\d\d)_(\d\d)_(\d\d)_\d\d\.emevd\.dcx\.js$")


def _map_id(area, x, y):
    """m10_00_00_00 -> m10_00 ; m60_51_57_00 -> m60_51_57 (the overworld tile IS the unit)."""
    return f"{area}_{x}_{y}" if area in ("m60", "m61") else f"{area}_{x}"


def _map_id_from_dir(dirname):
    m = _DIR_RE.match(dirname)
    return _map_id(m.group(1), m.group(2), m.group(3)) if m else None


def _iter_msb_dirs(roots):
    for root in roots:
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            p = os.path.join(root, name)
            mid = _map_id_from_dir(name)
            if mid and os.path.isdir(p):
                yield mid, p


# ---------------------------------------------------------------- params

def _lot2flags(csv_name):
    """ItemLotParam ID -> sorted distinct nonzero getItemFlagId* (both `getItemFlagId` and 01..08)."""
    path = os.path.join(VV, csv_name)
    if not os.path.isfile(path):
        sys.stderr.write(f"missing {path}\n")
        return {}
    out = {}
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
                out[rid] = fl
    return out


def _npc2lots():
    """NpcParam ID -> [(lot_id, which)] where which is 'enemy' (ItemLotParam_enemy) or 'map'."""
    path = os.path.join(VV, "NpcParam.csv")
    if not os.path.isfile(path):
        sys.stderr.write(f"missing {path}\n")
        return {}
    out = {}
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        for row in csv.DictReader(fh):
            try:
                nid = int(row["ID"])
            except (KeyError, TypeError, ValueError):
                continue
            lots = []
            for col, which in (("itemLotId_enemy", "enemy"), ("itemLotId_map", "map")):
                v = row.get(col)
                if v in (None, "", "0", "-1"):
                    continue
                try:
                    lots.append((int(v), which))
                except ValueError:
                    pass
            if lots:
                out[nid] = lots
    return out


# ---------------------------------------------------------------- source: treasure

def _treasure_rows(msb_dir, map_id, lot_map):
    rows = []
    tdir = os.path.join(msb_dir, "Event", "Treasure")
    if not os.path.isdir(tdir):
        return rows
    for f in glob.glob(os.path.join(tdir, "*.xml")):
        try:
            r = ET.parse(f).getroot()
        except (ET.ParseError, OSError):
            continue
        lid = (r.findtext("ItemLotID") or "").strip()
        nm = (r.findtext("Name") or "").strip()
        if not lid or lid in ("-1", "0"):
            continue
        for flag in lot_map.get(int(lid), ()):
            rows.append((flag, map_id, int(lid), nm, "treasure"))
    return rows


# ---------------------------------------------------------------- source: enemy

# Enemy parts are read with a regex rather than ElementTree: there are ~200k of them across the full
# map set and only two fields matter -- full XML parsing turns a 30s scan into a 10min one.
_NPCID_RE = re.compile(r"<NPCParamID>\s*(-?\d+)\s*</NPCParamID>")
_NAME_RE = re.compile(r"<Name>([^<]*)</Name>")


def _enemy_rows(msb_dir, map_id, lot_map, lot_enemy, npc_lots):
    rows = []
    edir = os.path.join(msb_dir, "Part", "Enemy")
    if not os.path.isdir(edir):
        return rows
    tables = {"map": lot_map, "enemy": lot_enemy}
    with os.scandir(edir) as it:
        for ent in it:
            if not ent.name.endswith(".xml"):
                continue
            try:
                with open(ent.path, encoding="utf-8-sig", errors="replace") as fh:
                    src = fh.read()
            except OSError:
                continue
            m = _NPCID_RE.search(src)
            if not m:
                continue
            lots = npc_lots.get(int(m.group(1)))
            if not lots:
                continue
            nm = _NAME_RE.search(src)
            nm = nm.group(1).strip() if nm else ent.name[:-4]
            for lot_id, which in lots:
                for flag in tables[which].get(lot_id, ()):
                    rows.append((flag, map_id, lot_id, nm, "enemy"))
    return rows


# ---------------------------------------------------------------- source: event (EMEVD)

_EVENT_RE = re.compile(r"\$Event\(\s*(\d+)\s*,\s*\w+\s*,\s*function\(([^)]*)\)\s*\{", re.S)
_AWARD_ARG_RE = re.compile(r"Award(?:ItemLot|ItemsIncludingClients)\(\s*(\w+)\s*\)")
_AWARD_LIT_RE = re.compile(r"Award(?:ItemLot|ItemsIncludingClients)\(\s*(\d+)\s*\)")
_GATE_RE = re.compile(r"WaitFor\(\s*EventFlag\(\s*(\w+)\s*\)\s*\)")
_INIT_RE = re.compile(r"\$InitializeEvent\(\s*\d+\s*,\s*(\d+)\s*,\s*([^)]*)\)")
_ICE_RE = re.compile(r"\$InitializeCommonEvent\(\s*\d+\s*,\s*(\d+)\s*,\s*([^)]*)\)")
_SETFLAG_RE = re.compile(r"SetEventFlagID\(\s*(\d+)\s*,\s*ON\s*\)"
                         r"|SetEventFlag\([^,]+,\s*(\d+)\s*,\s*ON\s*\)")
_LOTPARAM_RE = re.compile(r"itemlot", re.I)


def _read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def _iter_events(src):
    hits = [(int(m.group(1)),
             [p.strip() for p in m.group(2).split(",") if p.strip()],
             m.start()) for m in _EVENT_RE.finditer(src)]
    for i, (eid, params, start) in enumerate(hits):
        end = hits[i + 1][2] if i + 1 < len(hits) else len(src)
        yield eid, params, src[start:end]


def _common_func_lot_args():
    """common_func $Event id -> [param index, ...] whose name is an itemLot (boss handlers etc)."""
    src = _read(os.path.join(EVT, "common_func.emevd.dcx.js"))
    out = {}
    for eid, params, _body in _iter_events(src):
        idxs = [i for i, p in enumerate(params) if _LOTPARAM_RE.search(p)]
        if idxs:
            out[eid] = idxs
    return out


def _trigger_flag_lots():
    """triggerFlag -> {lot} from common.emevd's flag-gated award events (the remembrance path).

    An event that BOTH awards a lot passed as a parameter AND gates on a flag passed as a parameter
    is a "when flag F fires, award lot L" registration; common.emevd's own $InitializeEvent rows bind
    concrete (F, L). Which map that flag belongs to is then decided by which map emevd SETs it ON.
    """
    src = _read(os.path.join(EVT, "common.emevd.dcx.js"))
    award = {}
    for eid, params, body in _iter_events(src):
        lots = sorted({params.index(m.group(1)) for m in _AWARD_ARG_RE.finditer(body)
                       if m.group(1) in params})
        gates = sorted({params.index(m.group(1)) for m in _GATE_RE.finditer(body)
                        if m.group(1) in params})
        if lots and gates:
            award[eid] = (lots, gates[0])
    trig = {}
    for m in _INIT_RE.finditer(src):
        eid = int(m.group(1))
        if eid not in award:
            continue
        args = [a.strip() for a in m.group(2).split(",")]
        lots, gate = award[eid]
        try:
            flag = int(args[gate])
        except (IndexError, ValueError):
            continue
        for li in lots:
            try:
                lot = int(args[li])
            except (IndexError, ValueError):
                continue
            if lot > 0:
                trig.setdefault(flag, set()).add(lot)
    return trig


def _event_rows(only_maps, lot_map, lot_enemy):
    cf_lot = _common_func_lot_args()
    trig = _trigger_flag_lots()
    rows = []
    seen = set()
    for path in sorted(glob.glob(os.path.join(EVT, "m*.emevd.dcx.js"))):
        m = _EMEVD_RE.match(os.path.basename(path))
        if not m:
            continue
        map_id = _map_id(m.group(1), m.group(2), m.group(3))
        if only_maps and map_id not in only_maps:
            continue
        seen.add(map_id)
        src = _read(path)
        sites = {}                                        # lot_id -> award-site tag (first wins)
        for mm in _AWARD_LIT_RE.finditer(src):            # (a) literal award in this map's script
            sites.setdefault(int(mm.group(1)), "award")
        for mm in _ICE_RE.finditer(src):                  # (b) boss handler w/ itemLotId argument
            eid = int(mm.group(1))
            if eid not in cf_lot:
                continue
            args = [a.strip() for a in mm.group(2).split(",")]
            for li in cf_lot[eid]:
                try:
                    lot = int(args[li])
                except (IndexError, ValueError):
                    continue
                if lot > 0:
                    sites.setdefault(lot, f"common{eid}")
        for mm in _SETFLAG_RE.finditer(src):              # (c) map sets a common award trigger flag
            flag = int(mm.group(1) or mm.group(2))
            for lot in trig.get(flag, ()):
                sites.setdefault(lot, f"trigflag{flag}")
        for lot, tag in sites.items():
            flags = lot_map.get(lot) or lot_enemy.get(lot) or ()
            for flag in flags:
                rows.append((flag, map_id, lot, tag, "event"))
    return rows, seen


# ---------------------------------------------------------------- build

def build(only_maps=None, sources=SOURCES):
    lot_map = _lot2flags("ItemLotParam_map.csv")
    lot_enemy = _lot2flags("ItemLotParam_enemy.csv") if ("enemy" in sources or "event" in sources) else {}
    npc_lots = _npc2lots() if "enemy" in sources else {}
    rows = []
    maps = set()
    if "treasure" in sources or "enemy" in sources:
        roots = [os.path.join(ART, "mapstudio"), ART]     # mapstudio + any root-level witchy dirs
        for map_id, msb_dir in _iter_msb_dirs(roots):
            if only_maps and map_id not in only_maps:
                continue
            maps.add(map_id)
            if "treasure" in sources:
                rows += _treasure_rows(msb_dir, map_id, lot_map)
            if "enemy" in sources:
                rows += _enemy_rows(msb_dir, map_id, lot_map, lot_enemy, npc_lots)
    if "event" in sources:
        erows, emaps = _event_rows(only_maps, lot_map, lot_enemy)
        rows += erows
        maps |= emaps
    return sorted(set(rows)), len(maps)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--maps", nargs="*", help="restrict to these map_ids (validation)")
    ap.add_argument("--sources", nargs="*", choices=SOURCES, default=list(SOURCES),
                    help="which provenance chains to emit (default: all)")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--stdout", action="store_true", help="print instead of writing the tsv")
    args = ap.parse_args(argv)
    rows, nmaps = build(set(args.maps) if args.maps else None, set(args.sources))
    scope = ",".join(sorted(args.maps)) if args.maps else "all"
    if args.stdout:
        for r in rows:
            print("\t".join(map(str, r)))
    else:
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            # Self-describing scope: the oracle's multi-map ambiguity rule is only COMPLETE on a full
            # scan (a flag placed in an unscanned map looks single-map here), so it must be able to see
            # that this tsv was restricted -- a partial tsv can raise false mis-pins.
            fh.write(f"# maps={scope} sources={','.join(sorted(args.sources))}\n")
            fh.write("flag\tmap_id\titem_lot_id\ttreasure_name\tsource\n")
            for r in rows:
                fh.write("\t".join(str(x) for x in r) + "\n")
    by_src = {}
    for r in rows:
        by_src[r[4]] = by_src.get(r[4], 0) + 1
    sys.stderr.write(
        "msb_item_regions: %d flag->map rows (%s) across %d maps%s\n"
        % (len(rows), ", ".join(f"{k}={v}" for k, v in sorted(by_src.items())), nmaps,
           "" if args.stdout else " -> " + args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
