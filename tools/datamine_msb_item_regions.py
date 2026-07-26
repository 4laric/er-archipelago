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


# ---------------------------------------------------------------- schema probe

def explain(flag):
    """Trace ONE check flag end to end, in seconds. The whole point is to not need a 1250-map run.

    The diagnose loop for this join has been: I change something, Alaric runs a walk over every MSB
    in the game, pastes the summary, I read one number off it, repeat. That is minutes-to-hours per
    bit of information, and most of the questions are about a SINGLE check.

    `--explain 67050` answers them directly: which map, which lot, which Treasure event, which part,
    where that part was looked for, what is actually in those directories, and -- if the part is not
    where expected -- WHERE IN THE MSB THE NAME ACTUALLY APPEARS. That last one is the step that has
    cost the most round trips, because "not found" has never distinguished "wrong directory" from
    "wrong name" from "not in this map at all".
    """
    import csv as _csv
    # 1. flag -> map + lot, from the committed tsv (no artifacts needed for this half)
    path = os.path.join(REPO, "greenfield", "msb_flag_region.tsv")
    hits = []
    if os.path.isfile(path):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            rows = (ln for ln in fh if not ln.lstrip().startswith("#"))
            for r in _csv.DictReader(rows, delimiter="\t"):
                if (r.get("flag") or "").strip() == str(flag):
                    hits.append(r)
    print("== flag %s in msb_flag_region.tsv: %d row(s)" % (flag, len(hits)))
    for r in hits:
        print("   map=%s lot=%s source=%s name=%s"
              % (r.get("map_id"), r.get("item_lot_id"), r.get("source"), r.get("treasure_name")))
    if not hits:
        print("   (not a treasure-sourced check -- this tracer only follows the treasure chain)")
        return 0

    want_lots = {(r.get("item_lot_id") or "").strip() for r in hits}
    map_ids = {(r.get("map_id") or "").strip() for r in hits}
    roots = [os.path.join(ART, "mapstudio"), ART]
    for map_id, msb_dir in _iter_msb_dirs(roots):
        if map_id not in map_ids:
            continue
        print("== MSB %s -> %s" % (map_id, msb_dir))
        found_event = False
        for f in glob.glob(os.path.join(msb_dir, "Event", "Treasure", "*.xml")):
            try:
                r = ET.parse(f).getroot()
            except (ET.ParseError, OSError):
                continue
            if (r.findtext("ItemLotID") or "").strip() not in want_lots:
                continue
            found_event = True
            print("   Treasure event %s:" % os.path.basename(f))
            for ch in list(r):
                print("      <%-18s> %s" % (ch.tag, (ch.text or "").strip()[:50]))
            part = (r.findtext("TreasurePartName") or "").strip()
            if not part:
                print("   -> no TreasurePartName: nothing to resolve.")
                continue
            # 2. where did we LOOK, and what is actually there?
            print("   looking for part %r:" % part)
            for t in _AssetIndex.PART_TYPES:
                d = os.path.join(msb_dir, "Part", t)
                direct = os.path.join(d, part + ".xml")
                n = len(glob.glob(os.path.join(d, "*.xml")))
                print("      Part/%-10s %4d file(s)  %s" % (t, n,
                      "HIT " + direct if os.path.isfile(direct) else "no %s.xml" % part))
            # 3. THE STEP THAT SAVES THE ROUND TRIP: where does the name actually appear?
            # VERDICT, so the reader does not have to infer it from a 0.
            for t in _AssetIndex.PART_TYPES:
                pf = os.path.join(msb_dir, "Part", t, part + ".xml")
                if not os.path.isfile(pf):
                    continue
                try:
                    proot = ET.parse(pf).getroot()
                except (ET.ParseError, OSError):
                    break
                ent = (proot.findtext("EntityID") or "").strip()
                if ent in ("0", "-1", ""):
                    print("   ⭐ VERDICT: the part EXISTS and its EntityID is %s -- it has NO ENTITY."
                          % (ent or "absent"))
                    print("      An asset with no entity id cannot be named by")
                    print("      EnableAssetTreasure(assetEntityId), so this treasure is NOT gated")
                    print("      through that instruction and the asset->lot join can never resolve")
                    print("      it. Whatever withholds this pickup works some other way; look at the")
                    print("      ITEM LOT and the flag itself, not the asset.")
                else:
                    print("   ⭐ VERDICT: resolves to asset entity %s -- the join should produce a row."
                          % ent)
                break
            print("   grepping the whole MSB for %r ..." % part)
            seen = 0
            for g in glob.glob(os.path.join(msb_dir, "**", "*.xml"), recursive=True):
                try:
                    with open(g, encoding="utf-8", errors="replace") as fh:
                        txt = fh.read()
                except OSError:
                    continue
                if part not in txt:
                    continue
                seen += 1
                rel = os.path.relpath(g, msb_dir)
                nm = re.search(r"<Name>([^<]*)</Name>", txt)
                ent = re.search(r"<EntityID>([^<]*)</EntityID>", txt)
                print("      %-46s <Name>=%s <EntityID>=%s"
                      % (rel, nm.group(1) if nm else "?", ent.group(1) if ent else "-"))
                if seen >= 12:
                    print("      ... (more)")
                    break
            if not seen:
                print("      NOT ANYWHERE in this MSB -- the part lives in another map, or the name "
                      "is transformed between the Treasure event and the part record.")
        if not found_event:
            print("   no Treasure event in this map carries lot %s" % ",".join(sorted(want_lots)))
    return 0


def probe(msb_dir):
    """DUMP THE ACTUAL LAYOUT. No guessing, no output file.

    Three of my structural guesses have now been wrong in a row, each costing a round trip:

        Parts/Asset          -> 0 files      (guessed the subdir)
        Parts/               -> (none)       (guessed the parent)
        asset id ~= lot id   -> 0 of 186     (guessed the numbering)
        StartDisabled        -> 0/1 on m60_40_39's only treasure, so it does NOT mark the gated ones

    Every one was a plausible story about a schema I had not looked at, and each produced a confident
    empty result that reads like "the data is not there". So this stops proposing shapes and prints
    what is on disk: the real directory tree under the MSB, and every field of every Treasure event in
    the map. Write the join against THAT.

    Run it on the map with the case in it:
        python tools/datamine_msb_item_regions.py --probe --maps m60_40_39
    """
    import xml.etree.ElementTree as _ET
    print("== MSB dir: %s" % msb_dir)
    print("== real layout (2 levels, file counts):")
    for entry in sorted(os.listdir(msb_dir)):
        full = os.path.join(msb_dir, entry)
        if not os.path.isdir(full):
            print("   %-28s (file)" % entry)
            continue
        subs = sorted(os.listdir(full))
        dirs = [d for d in subs if os.path.isdir(os.path.join(full, d))]
        nfile = len(subs) - len(dirs)
        print("   %-28s %d file(s), %d subdir(s)" % (entry + "/", nfile, len(dirs)))
        for d in dirs:
            n = len(glob.glob(os.path.join(full, d, "*")))
            print("      %-24s %d file(s)" % (d + "/", n))

    tdir = os.path.join(msb_dir, "Event", "Treasure")
    tfiles = sorted(glob.glob(os.path.join(tdir, "*.xml")))
    print("== every Treasure event in this map (%d), all fields:" % len(tfiles))
    for f in tfiles:
        try:
            r = _ET.parse(f).getroot()
        except (_ET.ParseError, OSError):
            continue
        print("   --- %s" % os.path.basename(f))
        for ch in list(r):
            print("       <%-20s> %s" % (ch.tag, (ch.text or "").strip()[:52]))
    print("\nNOTE: msb_flag_region.tsv says f67050 (Stormhill Shack cookbook) is lot 1040390000 in")
    print("this map. If the treasure above is that lot and starts ENABLED, the gating is NOT in the")
    print("MSB treasure record and the EMEVD/asset route is the only one left.")
    return 0


# ------------------------------------------------------- treasure asset entity ids (for lot_gates)

ASSETS_OUT = os.path.join(REPO, "greenfield", "treasure_assets.tsv")


class _AssetIndex:
    """Per-map `part name -> EntityID`, built AT MOST ONCE and only if the direct lookup misses.

    v1 opened `Part/Asset/<part>.xml` directly and, on a miss, scanned the whole directory -- PER
    TREASURE. A map whose parts are not filename-addressable therefore re-scanned its 174 files for
    every treasure in it, which is how 1347 maps turned into an overnight job (Alaric, 2026-07-25).
    The scan is now memoised per map, so the worst case is one pass over each map's assets instead of
    one per question asked of it.
    """

    # EVERY part type, not just Asset. 229 of ~2824 treasures resolved (8%) with Asset alone, and
    # f67050 -- the case this exists for -- was not among them. `TreasurePartName` names a PART, and
    # nothing says a treasure's part must be an Asset: the MSB name for f67050's is 宝死体000,
    # "treasure CORPSE", which is a character. Fable flagged this and I underweighted it.
    # The subdirectory list is measured (Alaric's --probe): Asset, Collision, Enemy, MapPiece.
    # Searched in this order, and which type resolved each row is RECORDED, so the next reader gets
    # the distribution instead of another assumption.
    PART_TYPES = ("Asset", "Enemy", "MapPiece", "Collision")

    def __init__(self, msb_dir, stats):
        self.msb_dir = msb_dir
        self.dirs = [os.path.join(msb_dir, "Part", t) for t in self.PART_TYPES]
        self.stats = stats
        self._index = None

    def _entity_of(self, root):
        ent = (root.findtext("EntityID") or "").strip()
        return int(ent) if ent.lstrip("-").isdigit() and int(ent) > 0 else None

    # Two fields out of a small XML: a regex over the raw text, not a DOM.
    _NAME_RE = re.compile(r"<Name>([^<]*)</Name>")
    _ENT_RE = re.compile(r"<EntityID>([^<]*)</EntityID>")

    def _build(self):
        """Index a whole map's Asset parts WITHOUT XML-parsing every one of them.

        This fallback is what made the run slow. `map-scans` ticked 0 -> 1 -> 2 on exactly the maps
        where Alaric's parallel run stalled (m12_07, m12_05, 2026-07-25) -- big underground maps whose
        part files are not filename-addressable, so the index gets built, and building it meant
        ElementTree-parsing thousands of files to read two fields out of each.

        `ET.parse` builds a DOM per file. Two regexes over the raw text do the same job here for a
        fraction of the cost, and the shape is trivially checkable: these are witchy-emitted files
        with one `<Name>` and at most one `<EntityID>` at the top level.
        """
        self._index = {}
        self.stats["map_scans"] += 1
        files = [(f, t) for d, t in zip(self.dirs, self.PART_TYPES)
                 for f in sorted(glob.glob(os.path.join(d, "*.xml")))]
        checked = False
        for f, ptype in files:
            try:
                with open(f, encoding="utf-8", errors="replace") as fh:
                    txt = fh.read()
            except OSError:
                continue
            nm = self._NAME_RE.search(txt)
            if not nm:
                continue
            ent = self._ENT_RE.search(txt)
            val = (ent.group(1).strip() if ent else "")
            eid = int(val) if val.lstrip("-").isdigit() and int(val) > 0 else None
            # AGREE WITH THE DOM, ON REAL DATA, ONCE PER MAP. The regex takes the FIRST <EntityID>
            # anywhere in the text; findtext() takes a DIRECT CHILD of root. On a file with a nested
            # <EntityID> those differ, and every index-resolved row would be wrong -- and wrong
            # DIFFERENTLY from the direct-resolved ones. The docstring asserted "one at top level";
            # Fable pointed out that was asserted and never checked, so now it is checked.
            if not checked:
                checked = True
                try:
                    root = ET.parse(f).getroot()
                    if (root.findtext("Name") or "").strip() != nm.group(1).strip() \
                            or self._entity_of(root) != eid:
                        sys.exit("FATAL: the regex index disagrees with the XML parse on %s -- the "
                                 "'one <Name>/<EntityID> at top level' assumption does not hold for "
                                 "this corpus. Fix _build before trusting any row it produces." % f)
                except (ET.ParseError, OSError):
                    pass
            nm = nm.group(1).strip()
            # DUPLICATE NAMES: refuse to pick. dict last-writer-wins would make the output depend on
            # filesystem order -- machine-dependent rows, silently.
            prev = self._index.get(nm)
            if prev is not None and prev != "AMBIGUOUS" and prev[0] != eid:
                self.stats["dup_name"] += 1
                self._index[nm] = "AMBIGUOUS"
                continue
            self._index[nm] = (eid, ptype)

    def get(self, part_name):
        for d, ptype in zip(self.dirs, self.PART_TYPES):
            found, ent = self._get_in(d, ptype, part_name)
            if found:
                # FOUND IS NOT THE SAME AS RESOLVED. A part whose EntityID is 0 is ANSWERED -- it has
                # no entity, full stop -- and must not send us hunting through the other part types
                # and then building the whole map index. 3017 of 3573 treasure parts are EntityID 0
                # (Alaric's full run), so conflating the two triggered ~3000 needless index builds:
                # 392 map scans and 45 MINUTES of the 45-minute runtime, for parts already located.
                return ent
        if self._index is None:
            self._build()
        hit = self._index.get(part_name)
        if hit is None:
            self.stats["missing_part"] += 1
            return None
        if hit == "AMBIGUOUS":
            return None
        ent, ptype = hit
        if ent is None:
            # Counted as what it is. Previously this bumped `indexed` AND `type_<t>` regardless, so
            # the summary reported the SAME 3017 parts as both "resolved via a map index" and "no
            # EntityID" -- two lines that looked like independent measurements of different things.
            self.stats["no_entity"] += 1
            return None
        self.stats["indexed"] += 1
        self.stats["type_" + ptype] += 1
        return ent

    def _get_in(self, d, ptype, part_name):
        """(found_here, entity_or_None). `found_here` short-circuits the search; the entity may be
        None because the part legitimately has none."""
        direct = os.path.join(d, part_name + ".xml")
        if os.path.isfile(direct):
            try:
                root = ET.parse(direct).getroot()
                # VERIFY THE NAME. The filename is a CONVENTION, not the identity -- witchy could
                # decorate it (collision suffix, index prefix, truncation) and then this path does not
                # MISS, it returns another part's EntityID and the stats read a healthy "direct 1".
                # Fable caught this with a file named AEG_A.xml containing <Name>AEG_B</Name>.
                if (root.findtext("Name") or "").strip() != part_name:
                    self.stats["name_mismatch"] += 1
                    return False, None
                ent = self._entity_of(root)
                if ent is None:
                    self.stats["no_entity"] += 1
                    return True, None          # answered: this part has no entity
                self.stats["direct"] += 1
                self.stats["type_" + ptype] += 1
                return True, ent
            except (ET.ParseError, OSError):
                pass
        return False, None


def _scan_map_treasures(item):
    """ONE map -> [(item_lot_id, asset_entity, map_id, part_name)] + its lookup stats.

    Module-level and returning only plain tuples, because on Windows a process pool SPAWNS: the
    callable must be importable and the payload picklable. The lot -> flag join is deliberately NOT
    done here -- shipping the whole lot_map to every worker would cost more than the parse it saves.
    """
    map_id, msb_dir = item
    stats = {"direct": 0, "indexed": 0, "map_scans": 0, "no_entity": 0,
             "missing_part": 0, "treasures": 0, "name_mismatch": 0, "dup_name": 0,
             "type_Asset": 0, "type_Enemy": 0, "type_MapPiece": 0, "type_Collision": 0}
    assets = _AssetIndex(msb_dir, stats)
    out = []
    for f in glob.glob(os.path.join(msb_dir, "Event", "Treasure", "*.xml")):
        try:
            r = ET.parse(f).getroot()
        except (ET.ParseError, OSError):
            continue
        lid = (r.findtext("ItemLotID") or "").strip()
        part = (r.findtext("TreasurePartName") or "").strip()
        if not lid.isdigit() or int(lid) <= 0 or not part:
            continue
        stats["treasures"] += 1
        ent = assets.get(part)
        if ent is not None:
            out.append((int(lid), ent, map_id, part))
    return map_id, out, stats


def build_treasure_assets(only_maps=None, jobs=1):
    """flag -> (item_lot_id, asset entity id), the join `EnableAssetTreasure(assetEntityId)` needs.

    THE CHAIN, every link observed rather than assumed:
        Treasure event   <TreasurePartName> AEG099_610_9000   <ItemLotID> 1040390000
        Part/Asset/*     <Name> AEG099_610_9000               <EntityID> ...
        ItemLotParam     lot 1040390000                       -> check flag 67050

    datamine_lot_gates.py reported 186 `EnableAssetTreasure` sites it could not resolve -- the largest
    population it cannot see, and the one holding f67050 (the Stormhill Shack cookbook). Two shortcuts
    were measured dead first: asset ids do not share the lot numbering (0 of 186), and `StartDisabled`
    does not mark the gated pickups (m60_40_39's only treasure IS the cookbook and starts ENABLED).

    Prints per-map progress: this walks every unpacked MSB, and silence for minutes is
    indistinguishable from a hang.
    """
    lot_map = _lot2flags("ItemLotParam_map.csv")
    rows, maps = [], 0
    stats = {"direct": 0, "indexed": 0, "map_scans": 0, "no_entity": 0,
             "missing_part": 0, "treasures": 0, "name_mismatch": 0, "dup_name": 0,
             "type_Asset": 0, "type_Enemy": 0, "type_MapPiece": 0, "type_Collision": 0}
    roots = [os.path.join(ART, "mapstudio"), ART]
    # DEDUPE BY MAP ID. `_iter_msb_dirs` walks mapstudio AND the root-level witchy dirs, so maps come
    # back more than once -- Alaric's run had `m10_00` at [1] and again at [2], the second yielding 0
    # rows. First one wins.
    seen, dirs = set(), []
    for m, d in _iter_msb_dirs(roots):
        if only_maps and m not in only_maps:
            continue
        if m in seen:
            continue
        seen.add(m)
        dirs.append((m, d))
    total = len(dirs)
    print("treasure assets: %d distinct map(s) to scan, %d job(s)" % (total, jobs),
          file=sys.stderr, flush=True)

    import time as _time
    t0 = _time.monotonic()
    eta_state = {"last": t0, "window": [(t0, 0)]}

    def _hms(sec):
        sec = int(max(0, sec))
        h, m, sec = sec // 3600, (sec % 3600) // 60, sec % 60
        return ("%dh %02dm" % (h, m)) if h else ("%dm %02ds" % (m, sec)) if m else ("%ds" % sec)

    def _eta(done):
        """Print an ETA at most once a minute, from the RECENT rate.

        Cumulative rate would be wrong in a predictable direction here: the maps are wildly uneven --
        a legacy dungeon has hundreds of assets, an overworld tile has a handful -- so an average
        taken over an unrepresentative prefix quietly misleads for the whole run. The estimate uses
        the last ~60s of completions and SAYS it is doing that, because an ETA with no stated basis
        is just a number that looks authoritative.
        """
        now = _time.monotonic()
        eta_state["window"].append((now, done))
        eta_state["window"][:] = [(t, d) for t, d in eta_state["window"] if now - t <= 90] \
            or [eta_state["window"][-1]]
        if now - eta_state["last"] < 60 or done <= 0:
            return
        eta_state["last"] = now
        t_old, d_old = eta_state["window"][0]
        dt, dd = now - t_old, done - d_old
        # SAY WHICH BASIS IT USED. The window degenerates when completions arrive in bursts -- every
        # sample lands within a second of the others, dt collapses, and the recent rate is
        # meaningless. It then falls back to the cumulative average, and the first version still
        # printed "(last 0s)", which reads as a measured recent rate and is not one. Alaric's run
        # showed `0.1 map/s (last 0s) | ETA 4h 28m`: the number was cumulative, over a prefix of tiny
        # maps, and the label said otherwise.
        if dt >= 5 and dd > 0:
            rate, basis = dd / dt, "last %ds" % int(dt)
        else:
            rate, basis = done / max(1e-9, now - t0), "cumulative"
        left = total - done
        print("  ... %d/%d done in %s | %.2f map/s (%s) | ETA %s%s"
              % (done, total, _hms(now - t0), rate, basis,
                 _hms(left / rate) if rate > 0 else "?",
                 "  [early estimate -- maps are very uneven]" if done < 0.05 * total else ""),
              file=sys.stderr, flush=True)

    def _absorb(map_id, found_rows, st, i):
        nonlocal maps
        maps += 1
        n = 0
        for lid, ent, mid, part in found_rows:
            for flag in lot_map.get(lid, ()):
                rows.append((flag, lid, ent, mid, part))
                n += 1
        for k, v in st.items():
            stats[k] += v
        print("  [%4d/%4d] %-20s %d row(s)  total %d  (direct %d, indexed %d, map-scans %d)"
              % (i, total, map_id, n, len(rows), stats["direct"], stats["indexed"],
                 stats["map_scans"]), file=sys.stderr, flush=True)
        _eta(i)

    if jobs <= 1 or total < 2:
        # Serial path kept deliberately: a process pool is one more thing that can fail (spawn,
        # pickling, an antivirus that dislikes 8 python children), and when the parse is what is
        # broken you want the simple one. `--jobs 1` is the fallback, not a legacy branch.
        for i, item in enumerate(dirs, start=1):
            _absorb(*_scan_map_treasures(item), i)
    else:
        from concurrent.futures import ProcessPoolExecutor, as_completed
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            futs = {ex.submit(_scan_map_treasures, item): item[0] for item in dirs}
            for i, fut in enumerate(as_completed(futs), start=1):
                _absorb(*fut.result(), i)

    # ORDER-INDEPENDENT OUTPUT. Workers finish out of order, so the row list is not in map order --
    # the emit sorts, and this asserts the parallel and serial paths cannot disagree on CONTENT.
    print("treasure assets: %d map(s), %d treasure(s), %d row(s) in %s; lookups: %d direct, %d via "
          "a map index (%d map scan(s)); %d no EntityID, %d part not found, %d FILENAME/<Name> "
          "MISMATCH, %d duplicate <Name> (dropped)"
          % (maps, stats["treasures"], len(rows), _hms(_time.monotonic() - t0), stats["direct"],
             stats["indexed"], stats["map_scans"], stats["no_entity"], stats["missing_part"],
             stats["name_mismatch"], stats["dup_name"]), file=sys.stderr, flush=True)
    print("treasure assets: resolved BY PART TYPE -- %s  (Asset alone resolved 229 of ~2824 before "
          "MEASURED 2026-07-25: Enemy=MapPiece=Collision=0. EVERY treasure part is an Asset -- the "
          "multi-type search found nothing, and 3017 of 3573 parts simply have EntityID 0, i.e. no "
          "entity for the EMEVD to name. ~230 is the whole addressable population, not a shortfall)"
          % ", ".join("%s=%d" % (t, stats["type_" + t])
                                for t in ("Asset", "Enemy", "MapPiece", "Collision")),
          file=sys.stderr, flush=True)
    if maps and not rows:
        sys.exit("FATAL: %d map(s) scanned and ZERO asset entities resolved. Either Part/Asset has no "
                 "<EntityID>, or TreasurePartName does not match the part. Re-run --probe and write "
                 "the lookup against what it prints -- do NOT ship an empty join." % maps)
    return sorted(set(rows))


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
    ap.add_argument("--jobs", "-j", type=int, default=min(8, (os.cpu_count() or 1)),
                    help="parallel map scans (default: min(8, cpu count)). `-j 1` runs serially, "
                         "which is the one to use if the pool itself misbehaves.")
    ap.add_argument("--emit-assets", action="store_true",
                    help="write greenfield/treasure_assets.tsv (flag -> lot -> asset entity), the "
                         "join datamine_lot_gates.py needs for the 186 treasure gate sites")
    ap.add_argument("--explain", metavar="FLAG",
                    help="trace ONE check flag through the treasure chain in seconds -- map, lot, "
                         "event, part, where it was looked for, and where the name actually appears. "
                         "Use this instead of a full --emit-assets walk to diagnose a single miss.")
    ap.add_argument("--probe", action="store_true",
                    help="LOOK FIRST: print the Treasure-event and Asset-part XML tag names of the "
                         "first MSB found, and write nothing. Needed to build the asset->lot join "
                         "datamine_lot_gates.py wants; see probe.__doc__.")
    args = ap.parse_args(argv)
    if args.emit_assets:
        rows = build_treasure_assets(set(args.maps) if args.maps else None, jobs=args.jobs)
        with open(ASSETS_OUT, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("# AUTO-GENERATED by tools/datamine_msb_item_regions.py --emit-assets.\n")
            fh.write("# Treasure check flag -> its ItemLotParam lot -> the ASSET ENTITY the EMEVD\n")
            fh.write("# names in EnableAssetTreasure/DisableAssetTreasure. Consumed by\n")
            fh.write("# tools/datamine_lot_gates.py to resolve the treasure gate sites.\n")
            fh.write("# maps=%s\n" % (",".join(sorted(args.maps)) if args.maps else "all"))
            fh.write("# SCOPE IS LOAD-BEARING: `--maps X --emit-assets` overwrites this same path\n")
            fh.write("# with a ONE-MAP subset, and the consumer cannot tell that from a full run --\n")
            fh.write("# every other site just reads as 'unresolved'. Same reason msb_flag_region.tsv\n")
            fh.write("# carries its scope.\n")
            fh.write("flag\titem_lot_id\tasset_entity\tmap_id\tpart_name\n")
            for r in rows:
                fh.write("\t".join(str(x) for x in r) + "\n")
        print("wrote %s: %d row(s)" % (ASSETS_OUT, len(rows)))
        return 0
    if args.explain:
        return explain(args.explain)
    if args.probe:
        roots = [os.path.join(ART, "mapstudio"), ART]
        want = set(args.maps) if args.maps else None
        for _map_id, _msb_dir in _iter_msb_dirs(roots):
            if want and _map_id not in want:
                continue
            print("probing %s" % _map_id)
            return probe(_msb_dir)
        sys.exit("FATAL: no unpacked MSB dir%s found under %s -- nothing to probe."
                 % (" matching --maps" if want else "", ART))
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
