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

ESD FORMAT (confirmed from a real dump, t351006000.esd, 2026-07-23): raw binary EzState ("fsSL"). A
command argument is an int-literal expression `0x82 <int32 LE> 0xA1`. `OpenRegularShop(begin, end)`
stores its two args as ADJACENT literal expressions: `82 <begin> a1 82 <end> a1`. So a shop range is
that exact 12-byte signature with BOTH ints in the ShopLineupParam band [SHOP_LO, SHOP_HI]. This is
precise, not a guess: in the sample it matched the ONE real command (100350,100399) and rejected the
~85 in-band integers sitting in the ESD's data tables (values stepping by 16/32, never wrapped in a
0x82..a1 literal) that the old consecutive-any-integer heuristic wrongly paired into a dozen phantom
ranges. If a future WitchyBND serializes ESD to XML/text instead, we fall back to a regex for the same
literal pattern. Run with --probe first to eyeball the extraction; anchors (Twin Maidens cover 101800,
the Altus Hermit block 1007 lands on an m60_4x tile) validate it before the tsv is trusted.

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
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

import artifacts_root                          # noqa: E402  -- THE --path argument, not a copy

ART = artifacts_root.default_root(REPO)
VV = os.path.join(ART, "vanilla_er", "vanilla_er")
TALK = os.path.join(ART, "talk")
MAPSTUDIO_ROOTS = [os.path.join(ART, "mapstudio"), os.path.join(ART, "map", "mapstudio")]
OUT = os.path.join(REPO, "greenfield", "merchant_shops.tsv")

# Merchant shop rows are ShopLineupParam ids shopBlock*100+slot in the 1000xx..1029xx band. Ranges an
# ESD opens live here; other shop menus (enhance/sell/recipe) index other id spaces and simply won't
# pass the membership filter. Kept wide + validated by real-id membership rather than tightly guessed.
SHOP_LO, SHOP_HI = 100000, 103000
# A single OpenRegularShop range can span a full merchant block or two (the Twin-Maiden re-sell spans
# several); the precise 0x82..a1 adjacent-literal signature makes over-matching a non-issue, so this cap
# only rejects an absurd whole-shop-space pair that could only be a parse artifact, not a real command.
MAX_RANGE_SPAN = 2000

_DIR_MSB_RE = re.compile(r"^(m\d\d)_(\d\d)_(\d\d)_(\d\d)-msb-dcx$")
_DIR_TALK_RE = re.compile(r"^(m\d\d)_(\d\d)_(\d\d)_(\d\d)-talkesdbnd-dcx$")
_TALKFILE_RE = re.compile(r"^t(\d+)\.esd(?:\.xml)?$", re.I)
_TALKID_RE = re.compile(r"<TalkID>\s*(-?\d+)\s*</TalkID>")
_ENTITYID_RE = re.compile(r"<EntityID>\s*(-?\d+)\s*</EntityID>")
_NPCID_RE = re.compile(r"<NPCParamID>\s*(-?\d+)\s*</NPCParamID>")
# Same shape datamine_item_grace_coords uses for Part/Enemy and datamine_arena_graces for graces --
# MAP-LOCAL coordinates, the frame item_grace_coords.tsv is already in.
_POS_RE = re.compile(r"<Position>\s*<X>(-?[\d.eE+]+)</X>\s*<Y>(-?[\d.eE+]+)</Y>\s*<Z>(-?[\d.eE+]+)</Z>")
_NAME_RE = re.compile(r"<Name>([^<]*)</Name>")


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


# NpcParam.nameId is an FMG TEXT ID, not a name. The column was emitting the id, so
# merchant_name read "130900" where a human needs "Patches" -- and a table nobody can read is a table
# nobody audits. These are the same msgbnd dirs gen_data's _NAME_FMGS uses.
_NPC_NAME_FMGS = [
    os.path.join(ART, "msg", "item-msgbnd-dcx", "NpcName.fmg.xml"),
    os.path.join(ART, "msg", "item_dlc01-msgbnd-dcx", "NpcName_dlc01.fmg.xml"),
    os.path.join(ART, "msg", "item_dlc02-msgbnd-dcx", "NpcName_dlc02.fmg.xml"),
]
_PLACEHOLDER_NAMES = ("%null%", "[ERROR]")


def _set_artifacts_root(path):
    """`--path`: read every artifact input out of a different corpus root.

    🛑 `_NPC_NAME_FMGS` is built AT IMPORT off the old root, so moving the root has to rebuild it
    too -- a seam that leaves one input behind gives a run that reads the new ESDs and the old
    names, and that is a plausible table, not a loud failure."""
    global ART, VV, TALK, MAPSTUDIO_ROOTS, _NPC_NAME_FMGS
    ART = os.path.abspath(path)
    VV = os.path.join(ART, "vanilla_er", "vanilla_er")
    TALK = os.path.join(ART, "talk")
    MAPSTUDIO_ROOTS = [os.path.join(ART, "mapstudio"), os.path.join(ART, "map", "mapstudio")]
    _NPC_NAME_FMGS = [
        os.path.join(ART, "msg", "item-msgbnd-dcx", "NpcName.fmg.xml"),
        os.path.join(ART, "msg", "item_dlc01-msgbnd-dcx", "NpcName_dlc01.fmg.xml"),
        os.path.join(ART, "msg", "item_dlc02-msgbnd-dcx", "NpcName_dlc02.fmg.xml"),
    ]


# ------------------------------------------------------------------ merchant IDENTITY: a warning
# 🛑 NO COLUMN IN THIS TABLE IS A MERCHANT IDENTITY. Do not count "how many merchants relocate" off
# one of them without reading this; the number is wrong in BOTH directions and it has already been
# reported wrong twice.
#
#   * nameId SPLITS one NPC across questline states. Alaric, 2026-07-26, in-game: "scribe corhyn and
#     brother corhyn same guy" -- 135100 and 135101 are one man, and keying on nameId reports him as
#     two merchants on 4 and 2 maps instead of one on 6. Generalising his correction finds a second:
#     Knight Bernahl / Recusant Bernahl.
#   * nameId also MERGES: every row whose nameId is 0 collapses into one phantom "merchant" standing
#     on 6 maps. (name_of() refuses nameId 0 for this reason.)
#   * npc_param_id SPLITS one NPC across instances: Gostoc has SIX (36650014..36650514), Sellen four,
#     Patches three.
#   * talk_id // 100000 looks like the answer and is not. MEASURED over this table: it reproduces
#     Alaric's Corhyn correction and finds Bernahl (good), but it MERGES the anonymous merchant
#     CLASSES -- 8011/8012 lump Nomadic/Isolated/Hermit/Imprisoned/Abandoned Merchant together, and
#     those are many physical people -- and it SPLITS Sellen across 3160/3162/3163.
#
# So: relocation is only safely stated PER SHOP ROW (which is what the coordinate model needs --
# check -> {(map_id, x, y, z, availability)}), or with the identity question explicitly labelled
# unresolved. If you need real identities, they have to come from a datum this table does not carry.


def load_npc_name_texts():
    """nameId -> display name, from the NpcName FMGs. {} if none are present (callers must say so)."""
    import xml.etree.ElementTree as ET
    out = {}
    for path in _NPC_NAME_FMGS:
        if not os.path.isfile(path):
            continue
        for t in ET.parse(path).getroot().iter("text"):
            i, tx = t.get("id"), (t.text or "").strip()
            if i and tx and tx not in _PLACEHOLDER_NAMES:
                out.setdefault(int(i), tx)
    return out


def name_of(name_id, texts):
    """The display name for a nameId, or "" -- and "" is a REFUSAL, never a guess.
    nameId 0 is 'unset' at the datum level; it resolves to the literal string "DLC dummy" in the
    FMG, which is a placeholder wearing a name's clothes. Rejected on the ID, not by blacklisting
    the string, so it cannot rot when FromSoft changes the placeholder text."""
    try:
        nid = int(name_id)
    except (TypeError, ValueError):
        return ""
    if nid <= 0:
        return ""
    return texts.get(nid, "")


def load_npc_names():
    """NpcParam ID -> nameId (an FMG text id), best-effort; empty if NpcParam absent. Resolved to a
    display name by name_of(); never load-bearing either way."""
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
    """talk_id -> {map_id}, talk_id -> npc_param_id (first seen), and (talk_id, map_id) -> POSITION.

    Reuses the regex-scan approach of datamine_msb_item_regions._enemy_rows (a full XML parse is 10x
    slower over ~200k Enemy parts).

    ⭐ The position costs NOTHING extra: this walk already opens and reads every Part/Enemy xml to
    find TalkID -- the position is one more regex over text that is already in memory. That is why
    the merchant coordinates are folded into THIS scan instead of a second pass over the same 2.2 GB.

    Positions are MAP-LOCAL, the same frame item_grace_coords.tsv uses. A merchant can stand more
    than once in one map (patrol copies, questline duplicates); the FIRST is kept and the rest are
    TALLIED, never silently dropped -- `dupe_pos` in the return.
    """
    talk_maps = defaultdict(set)
    talk_npc = {}
    talk_pos = {}                 # (talk_id, map_id) -> (x, y, z)
    dupe_pos = Counter()          # (talk_id, map_id) -> how many EXTRA placements were seen
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
                    pm = _POS_RE.search(src)
                    if pm:
                        key = (tid, mid)
                        if key in talk_pos:
                            dupe_pos[key] += 1
                        else:
                            talk_pos[key] = (pm.group(1), pm.group(2), pm.group(3))
    return talk_maps, talk_npc, seen_dirs, talk_pos, dupe_pos


# ---------------------------------------------------------------- ESD: talk id -> shop ranges

# Precise EzState signature for OpenRegularShop's two adjacent int-literal args, both in the shop band:
#   0x82 <begin int32 LE> 0xA1  0x82 <end int32 LE> 0xA1
_TEXT_SHOP_RE = re.compile(rb"OpenRegularShop\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)")


def esd_ranges(path, shop_ids):
    """(begin, end) OpenRegularShop ranges from one ESD. Binary EzState: the adjacent-literal signature
    above (both ints in-band). Text/XML fallback: an OpenRegularShop(a,b) call. Deduped, sorted. `end`
    is treated inclusive and intersected with real ShopLineupParam ids downstream, so an off-by-one at
    the range edge cannot invent a row."""
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError:
        return []
    out = set()
    if b"OpenRegularShop" in raw:                       # decompiled text/xml form
        for m in _TEXT_SHOP_RE.finditer(raw):
            a, b = int(m.group(1)), int(m.group(2))
            if SHOP_LO <= a <= b <= SHOP_HI:
                out.add((a, b))
        return sorted(out)
    # raw binary EzState: scan the 12-byte adjacent-literal signature.
    i, n = 0, len(raw)
    while i <= n - 12:
        if raw[i] == 0x82 and raw[i + 5] == 0xA1 and raw[i + 6] == 0x82 and raw[i + 11] == 0xA1:
            a = struct.unpack_from("<i", raw, i + 1)[0]
            b = struct.unpack_from("<i", raw, i + 7)[0]
            if SHOP_LO <= a <= b <= SHOP_HI and (b - a) <= MAX_RANGE_SPAN:
                out.add((a, b))
                i += 12
                continue
        i += 1
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


def _tracked_row_count():
    """Rows in the committed table, so the refusal message quotes a REAL number instead of a
    hardcoded one that rots the next time the table grows."""
    try:
        with open(OUT, encoding="utf-8-sig") as fh:
            return sum(1 for ln in fh if not ln.startswith("#") and not ln.startswith("row_id"))
    except OSError:
        return "?"


def refresh_names(path):
    """Rewrite ONLY the merchant_name column, from npc_name_id + the NpcName FMGs.

    Why this exists: the full --emit needs the unpacked MSBs and the talk ESD, so a name-table fix
    would otherwise be gated behind a scan that has nothing to do with names. This reads the table's
    OWN committed nameIds, so it is a re-derivation by the owning tool -- not a hand edit of a
    generated file, which is the thing CONTRIBUTING forbids.

    IDEMPOTENT and back-compatible: `npc_name_id` is read from the new last column when present, and
    otherwise from the legacy `merchant_name` column, which used to hold the id itself.
    """
    texts = load_npc_name_texts()
    if not texts:
        sys.exit("FATAL: no NpcName FMG under elden_ring_artifacts/msg -- refusing to blank every "
                 "name in %s. An empty result is a failure, not a clean run." % path)
    with open(path, encoding="utf-8-sig", newline="") as fh:
        lines = fh.read().splitlines()
    out, tally = [], Counter()
    for ln in lines:
        if ln.startswith("#"):
            out.append(ln); continue
        p6 = ln.split("\t")
        if p6 and p6[0] == "row_id":
            out.append("\t".join(["row_id", "talk_id", "npc_param_id", "merchant_name",
                                   "map_id", "map_source", "npc_name_id"] + p6[7:]))
            continue
        if len(p6) < 6 or not p6[0].strip().isdigit():
            out.append(ln); tally["passed through (not a data row)"] += 1; continue
        nid = p6[6].strip() if len(p6) >= 7 else p6[3].strip()
        nm = name_of(nid, texts)
        tally["named" if nm else ("nameId 0 / unset" if nid in ("", "0") else "nameId NOT in any FMG")] += 1
        # keep ANY columns past npc_name_id (pos_x/y/z ...) -- a refresh must NOT truncate the table
        # it refreshes. Rebuilding a fixed-width row is how a later column gets silently dropped by
        # an earlier tool.
        out.append("\t".join(p6[:3] + [nm, p6[4], p6[5], nid] + p6[7:]))
    named = tally["named"]
    total = sum(v for k, v in tally.items() if k != "passed through (not a data row)")
    # An "empty result reads as success" guard: this table is ~97% nameable, so a collapse means the
    # FMG or the id column moved, not that the game changed.
    if total and named * 100 // max(total, 1) < 50:
        sys.exit("FATAL: only %d of %d rows resolved to a name -- the nameId column or the FMG id "
                 "space has drifted. Refusing to write a mostly-blank table." % (named, total))
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out) + "\n")
    print("merchant_shops --refresh-names: %d row(s); %s" % (total, dict(tally)))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    artifacts_root.add_path_argument(ap, artifacts_alias=False)
    ap.add_argument("--refresh-names", action="store_true",
                    help="rewrite ONLY the merchant_name column of an existing table, from the "
                         "committed npc_name_id + the NpcName FMGs. Needs no MSB/ESD scan, so it "
                         "runs anywhere the msgbnd is unpacked. Idempotent.")
    ap.add_argument("--maps", nargs="*", help="restrict to these map ids (e.g. m60_40_54)")
    ap.add_argument("--probe", action="store_true",
                    help="dump extracted ranges for anchor/ filtered ESDs and exit (no tsv written)")
    ap.add_argument("--audit", type=int, metavar="ROWID",
                    help="diagnostic: list every unpacked talk binder (coverage) and every ESD whose "
                         "RAW bytes contain this ShopLineupParam id as an int32 -- even if not a clean "
                         "0x82 literal pair. Distinguishes 'binder not unpacked' from 'range is "
                         "parameterized, not a literal'. Writes nothing.")
    args = ap.parse_args()
    root = artifacts_root.resolve(args.path)
    if root:
        _set_artifacts_root(root)

    if args.refresh_names:
        return refresh_names(args.out)
    map_filter = set(args.maps) if args.maps else None
    # 🛑 --maps RESTRICTS THE SCAN BUT THE EMIT IS WHOLE-TABLE. A subset run therefore rewrites the
    # tracked tsv with only the rows its two maps could see -- a "sanity pass" silently truncating
    # the very table it is sanity-checking. That happened for real on 2026-07-26: --maps m10_00
    # m11_10 cut 1954 rows to 775, and the built-in Hermit probe then fired a FALSE alarm because the
    # Altus tile had not been scanned, so the guard could not tell "subset run" from "broken join".
    # Refuse the combination instead of documenting it: a subset run must say where to put its output.
    if map_filter and os.path.abspath(args.out) == os.path.abspath(OUT):
        sys.exit(
            "FATAL: --maps is a VALIDATION SUBSET, but this tool always emits the WHOLE table -- "
            "writing it to the tracked %s would replace its %s row(s) with only the ones these maps "
            "can see, and the self-checks below would fire false alarms on the missing maps.\n"
            "  full run (what you commit):   python tools/datamine_merchant_shops.py\n"
            "  subset run (validation):      python tools/datamine_merchant_shops.py --maps %s "
            "--out /tmp/ms-subset.tsv"
            % (os.path.relpath(OUT, REPO), _tracked_row_count(), " ".join(sorted(map_filter))))

    if not os.path.isdir(TALK):
        sys.exit(f"FATAL: {TALK} not found. Produce the ESD unpack first (see module docstring): copy "
                 f"script/talk/*.talkesdbnd.dcx into elden_ring_artifacts/talk/ and run WitchyBND on "
                 f"them. Nothing written.")

    if args.audit is not None:
        want = struct.pack("<i", args.audit)
        binders = sorted(d for d in os.listdir(TALK) if os.path.isdir(os.path.join(TALK, d)))
        print(f"# AUDIT for ShopLineupParam id {args.audit} (block {args.audit // 100})")
        print(f"# {len(binders)} talk binder(s) unpacked: {binders}")
        hits = []
        for name in binders:
            bdir = os.path.join(TALK, name)
            for fn in sorted(os.listdir(bdir)):
                if not _TALKFILE_RE.match(fn):
                    continue
                try:
                    raw = open(os.path.join(bdir, fn), "rb").read()
                except OSError:
                    continue
                if want in raw:
                    off = raw.find(want)
                    wrapped = off >= 1 and raw[off - 1] == 0x82   # is it a 0x82 int literal?
                    hits.append((name, fn, off, wrapped))
        if hits:
            print(f"# {len(hits)} ESD(s) contain {args.audit} as a raw int32:")
            for (name, fn, off, wrapped) in hits:
                tag = "(0x82 literal)" if wrapped else "(NOT a 0x82 literal -- data table / computed)"
                print(f"    {name}/{fn}  off={off}  {tag}")
        else:
            print(f"# {args.audit} appears in NO unpacked ESD as an int32. Either its merchant's talk "
                  f"binder was not unpacked, or the shop range is computed (parameterized) rather than a "
                  f"literal -- in which case the range must come from NpcParam / a talk-group param.")
        return 0

    shop_ids = load_shop_ids()
    npc_names = load_npc_names()
    talk_data, esd_files = scan_talk(shop_ids, map_filter)
    talk_maps, talk_npc, msb_dirs, talk_pos, dupe_pos = scan_msb(map_filter)

    if not talk_data:
        sys.exit(f"FATAL: no shop ranges extracted from any ESD under {TALK} ({esd_files} candidate "
                 f"files). The extraction heuristic found no in-band ShopLineupParam id pairs -- the ESD "
                 f"serialization is likely a format _extract_ints doesn't handle. Run with --probe and "
                 f"send the printed sample (and one raw t*.esd) so the parser can be fixed.")

    if args.probe:
        print(f"# PROBE: {esd_files} ESD file(s) yielded shop ranges; {len(talk_data)} talk id(s).")
        for tid in sorted(talk_data):
            d = talk_data[tid]
            print(f"talk {tid}: ranges={sorted(d['ranges'])} binder={sorted(d['binder_maps'])} "
                  f"msb={sorted(talk_maps.get(tid, []))} npc={talk_npc.get(tid)}")
        return 0

    rows = build(shop_ids, talk_data, talk_maps, talk_npc, npc_names)
    _name_texts = load_npc_name_texts()
    if not _name_texts:
        print("WARNING: no NpcName FMG found under elden_ring_artifacts/msg -- merchant_name will be "
              "BLANK for every row. That is a refusal, not a name; unpack the msgbnd and re-emit.")

    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("# AUTO-GENERATED by tools/datamine_merchant_shops.py -- which physical merchant opens\n")
        f.write("# each ShopLineupParam row, and on which map. Replaces datamine_shop_rows.py's false\n")
        f.write("# 'block = one merchant' region inheritance. One line per (row, merchant instance);\n")
        f.write("# a row with >1 distinct map region -> gen_data collapses to HUB + DEFAULTED. map_id ->\n")
        f.write("# region is gen_data's job (_gt_region). map_source: msb|binder|msb+binder|none.\n")
        f.write("row_id\ttalk_id\tnpc_param_id\tmerchant_name\tmap_id\tmap_source\tnpc_name_id"
                "\tpos_x\tpos_y\tpos_z\n")
        _pos_hit = _pos_miss = 0
        for rid in sorted(rows):
            for (tid, npc, mname, mid, src) in rows[rid]:
                _p = talk_pos.get((tid, mid))
                if _p:
                    _pos_hit += 1
                else:
                    _pos_miss += 1
                    _p = ("", "", "")
                f.write(f"{rid}\t{tid}\t{npc if npc is not None else ''}\t"
                        f"{name_of(mname, _name_texts)}\t{mid}\t{src}\t{mname}\t"
                        f"{_p[0]}\t{_p[1]}\t{_p[2]}\n")
        print("merchant_shops: POSITION on %d of %d (row,merchant) line(s); %d had no Part/Enemy "
              "position for that (talk,map). Extra placements of one merchant in one map (kept the "
              "first, tallied the rest): %d over %d (talk,map) pair(s)."
              % (_pos_hit, _pos_hit + _pos_miss, _pos_miss, sum(dupe_pos.values()), len(dupe_pos)))

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
    # ...and the probe only means anything when the Altus tile was actually in scope. On a subset run
    # its absence is the FILTER, not a defect -- a guard that cannot tell those apart is a guard that
    # cries wolf, and people stop reading those.
    if map_filter and not any(m.startswith("m60_4") for m in map_filter):
        print("  (Hermit probe SKIPPED: --maps excluded the Altus m60_4x tiles, so a miss here would "
              "be the filter, not a finding.)")
    elif altus_maps and not any(re.match(r"m60_4", m) for m in altus_maps):
        print("  !! WARNING: Hermit rows 100725/100741 did NOT resolve to an Altus (m60_4x) tile "
              f"-> {sorted(altus_maps)}. The MSB TalkID field or the ESD extraction may be wrong; "
              "verify with --probe before trusting this tsv.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
