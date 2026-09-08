#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_check_browser.py -- render the whole check corpus as ONE offline HTML page.

Writes er-archipelago-check-browser.html: a single self-contained file (no server, no CDN,
no game artifacts) that lets you search, facet and inspect every check the world defines.
Meant as a datamine READING tool -- it is a pure join over already-committed generator
output, so it can never disagree with gen_data unless one of its inputs is stale.

AP-FREE and import-free: the generated .py modules are read with ast.literal_eval, never
imported, so this runs with a bare python3 and no Archipelago on sys.path.

INPUTS (all committed; none are game files):
  greenfield/eldenring/tables/data.py              LOCATIONS: region -> [(name, ap_id, flag)]
  greenfield/eldenring/tables/location_tags.py     LOCATION_TAGS + DEFAULTED/BURN ap-id sets
  greenfield/eldenring/tables/missable_locations.py MISSABLE_LOCATIONS: ap_id -> reason
  greenfield/check_maps.tsv                 flag -> physical map tile(s)
  greenfield/nearest_grace.tsv              flag -> nearest Site of Grace
  greenfield/lot_gates.tsv                  flag -> gate flag(s)
  greenfield/flag_lots.tsv                  flag -> ItemLotParam rows
  greenfield/map_names.tsv                  map tile -> dungeon name
  greenfield/location_descriptions.tsv      hand-authored descriptions
  greenfield/shop_rows.tsv                  ShopLineupParam row detail
  greenfield/treasure_enablers.tsv          StartDisabled enabler verdicts
  greenfield/msb_gated_treasures.tsv        StartDisabled=1 MSB records
  greenfield/esd_gifts.tsv                  NPC dialogue gift gate paths
  greenfield/esd_gates.tsv                  merchant shop-range gate paths
  greenfield/synthetic_flag_recovery.tsv    phantom-flag verdicts (negative space)

GATE EVIDENCE IS PLURAL. lot_gates.tsv covers 110 checks and is the SMALLEST of four
corpora that document gating; showing it alone taught the reader "110/4879 are gated",
which is the partial-read this project keeps getting burned by. All four are joined, each
counted separately, and each rendered beside its own tsv header VERBATIM -- because those
headers carry the polarity rules (EndIf has INVERTED sense; self_set_flags is a MEMO, not a
prerequisite; NO_ENTITY_HANDLE is PROOF OF NO GATING, not mystery) and a UI that flattened
them to "gated: yes/no" would invert their meaning.

NEGATIVE SPACE. The page also carries the join RESIDUALS -- rows in those side tables that
are NOT checks -- with the recorded reason where one exists and an honest blank where none
does. That population is where every wrong claim here has come from.

DETERMINISM: the output is a pure function of those inputs -- every set is emitted sorted and
the page is stamped with data.py's _GEN_STAMP.inputs_hash, NOT with the git commit. This is
what lets CI regenerate and fail on a non-empty diff (see .github/workflows/tests.yaml
`generators`); embedding a commit hash would make the committed file stale by construction.

Run:  python tools/build_check_browser.py [--out PATH] [--repo ROOT]
"""
import argparse
import ast
import json
import os
import re
import sys
from collections import Counter, defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = "er-archipelago-check-browser.html"
MIN_CHECKS = 4_900
MIN_PLOTTABLE = 2_000


def require_complete_payload(checks, meta, out_path):
    """Refuse a convincing-looking page built from a silently shrunken corpus."""
    missing = []
    if len(checks) < MIN_CHECKS:
        missing.append(f"checks={len(checks)} (minimum {MIN_CHECKS})")
    if meta["plottable"] < MIN_PLOTTABLE:
        missing.append(
            f"plottable={meta['plottable']} (minimum {MIN_PLOTTABLE})"
        )
    if missing:
        raise SystemExit(
            "FATAL: check-browser corpus is incomplete: "
            + ", ".join(missing)
            + f". Refusing to overwrite {out_path}."
        )


def load_module_consts(path, names):
    """Parse a generated .py without importing it (no AP deps)."""
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    out = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for tgt in node.targets:
            if isinstance(tgt, ast.Name) and tgt.id in names:
                try:
                    out[tgt.id] = ast.literal_eval(node.value)
                except ValueError:
                    # frozenset([...]) / frozenset({...}) etc. The BRACE arm was added for
                    # contract.SURFACE_DEFAULT_CLASSES (#599), which is a set literal -- the
                    # list-only pattern silently returned nothing for it, and a silently absent
                    # constant is the failure mode this helper exists to avoid.
                    src = ast.unparse(node.value)
                    m = re.match(r"frozenset\((\[.*\]|\{.*\})\)$", src, re.S)
                    if m:
                        out[tgt.id] = set(ast.literal_eval(m.group(1)))
    return out


def read_tsv(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        header = None
        for line in fh:
            if line.startswith("#"):
                continue
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t")
            if header is None:
                header = parts
                continue
            rows.append(dict(zip(header, parts)))
    return rows


# `tools/` is not necessarily on sys.path: the test suites load this file BY PATH with
# importlib, which does not add its directory. Without this the sibling import below raises
# ModuleNotFoundError and the whole suite errors at collection.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# THE overworld fold now lives in tools/overworld_fold.py and is re-exported here so every
# existing `from build_check_browser import world_xz` keeps working. It moved on 2026-08-04
# (issue #338) because build_nearest_grace needed the SAME transform and importing it from here
# would have been a cycle -- build_check_browser already imports build_nearest_grace.
from overworld_fold import OW_RE, world_xz  # noqa: F401  (re-exported for build_desc_triage)

# The sweep clause is taken back OUT of the name here (er-archipelago#936). The splitter lives
# next to the writer in greenfield/desc_sources so the two shapes cannot drift; `greenfield/` is
# the repo root's package dir, one level up from tools/.
sys.path.insert(0, os.path.join(REPO, "greenfield"))
from desc_sources import split_sweep_clause  # noqa: E402


def data_stamp(path):
    """data.py's _GEN_STAMP.inputs_hash -- a content id that is stable across commits."""
    with open(path, encoding="utf-8") as fh:
        m = re.search(r"^_GEN_STAMP = (\{.*\})\s*$", fh.read(), re.M)
    if not m:
        return ""
    return ast.literal_eval(m.group(1)).get("inputs_hash", "")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=REPO, help="repo root (default: parent of tools/)")
    ap.add_argument("--out", default=None,
                    help=f"output html (default: <repo>/{DEFAULT_OUT})")
    args = ap.parse_args()
    root = args.repo
    out_path = args.out or os.path.join(root, DEFAULT_OUT)
    gf = os.path.join(root, "greenfield")
    er = os.path.join(gf, "eldenring")

    d = load_module_consts(os.path.join(er, "tables", "data.py"), {"LOCATIONS", "REGIONS", "HUB", "NOT_RANDOMIZED"})
    tagmod = load_module_consts(
        os.path.join(er, "tables", "location_tags.py"),
        {"LOCATION_TAGS", "TAG_COUNTS", "DEFAULTED_REGION_APS", "ERDTREE_BURN_APS",
         "SHOP_RELEASE_GATED_APS", "SURFACE_EXCLUDE_APS"},
    )
    miss = load_module_consts(os.path.join(er, "tables", "missable_locations.py"), {"MISSABLE_LOCATIONS"})

    LOCATIONS = d["LOCATIONS"]
    TAGS = tagmod.get("LOCATION_TAGS", {})
    MISSABLE = miss.get("MISSABLE_LOCATIONS", {})
    DEFAULTED = tagmod.get("DEFAULTED_REGION_APS", set())
    BURN = tagmod.get("ERDTREE_BURN_APS", set())

    # --- side tables keyed by event flag -------------------------------------
    maps_by_flag = defaultdict(list)
    for r in read_tsv(os.path.join(gf, "check_maps.tsv")):
        maps_by_flag[int(r["flag"])].append(
            {"map": r["map_id"], "src": r.get("source", ""), "detail": r.get("detail", "")}
        )

    grace_by_flag = {}
    for r in read_tsv(os.path.join(gf, "nearest_grace.tsv")):
        grace_by_flag[int(r["flag"])] = r["grace_name"]

    gates_by_flag = defaultdict(list)
    for r in read_tsv(os.path.join(gf, "lot_gates.tsv")):
        gates_by_flag[int(r["check_flag"])].append(
            {"gate": r["gate_flag"], "ctx": r.get("context", ""), "ev": r.get("event_id", "")}
        )

    lots_by_flag = defaultdict(list)
    for r in read_tsv(os.path.join(gf, "flag_lots.tsv")):
        lots_by_flag[int(r["flag"])].append(
            {"table": r.get("table", ""), "lot": r.get("lot", ""), "slot": r.get("slot", ""),
             "cat": r.get("category", ""), "item": r.get("item_id", ""),
             "n": r.get("num", ""), "name": r.get("name", "")}
        )

    # --- ORACLE REGION REVIEW QUEUE ------------------------------------------------
    # greenfield/evidence/oracle-region-queue.tsv is a COMMITTED generator input, refreshed by
    # hand with `tools/matt_oracle.py --region-queue` against a local second-source checkout that
    # CI does not have. This build must therefore never need that checkout -- it reads the tsv and
    # nothing else, so the page stays a pure function of committed files (see DETERMINISM above).
    # 🛑 The tsv carries OUR flag/ap_id/region and a reviewer's own words. It records only THAT a
    # second source's partition disagrees, never what that source names the place. A reviewer rules
    # from the evidence panels beside it (tile, nearest grace, wiki second opinion), not from it.
    queue_by_ap = {}
    queue_path = os.path.join(gf, "evidence", "oracle-region-queue.tsv")
    if os.path.exists(queue_path):
        for r in read_tsv(queue_path):
            try:
                queue_by_ap[int(r["ap_id"])] = {
                    "status": r.get("status", "open") or "open",
                    "basis": r.get("basis", ""),
                    "reviewer": r.get("reviewer", ""),
                    "note": r.get("note", ""),
                }
            except (KeyError, ValueError):
                continue

    # --- ORACLE MISSABLE REVIEW QUEUE ----------------------------------------------
    # greenfield/evidence/oracle-missable-queue.tsv, the region queue's sibling and the same kind
    # of committed generator input (`tools/matt_oracle.py --missable-queue`). Same determinism
    # rule: the tsv is the only thing read, so no second-source checkout is ever needed here.
    # 🛑 It records only THAT a second source tags a flag missable while OUR MISSABLE_LOCATIONS
    # does not -- never that source's tags or prose. `our_conditions` is OUR OWN
    # questline_conditions.tsv root classes, and a root is a gate we SAW, never a proof.
    missable_by_ap = {}
    missable_path = os.path.join(gf, "evidence", "oracle-missable-queue.tsv")
    if os.path.exists(missable_path):
        for r in read_tsv(missable_path):
            try:
                missable_by_ap[int(r["ap_id"])] = {
                    "status": r.get("status", "open") or "open",
                    "conds": r.get("our_conditions", ""),
                    "reviewer": r.get("reviewer", ""),
                    "note": r.get("note", ""),
                }
            except (KeyError, ValueError):
                continue

    # Second opinion from our own wiki audit, for the reviewer panel. Region names in this table
    # are from OUR vocabulary (see the tsv's own header); no wiki prose is reproduced.
    second_by_ap = {}
    for r in read_tsv(os.path.join(gf, "check_region_second_opinion.tsv")):
        try:
            second_by_ap.setdefault(int(r["ap_id"]), {
                "verdict": r.get("verdict", ""), "ext": r.get("external_regions", ""),
                "src": r.get("source", ""), "page": r.get("page_title", ""),
                "vote": r.get("msb_vote_region", ""), "note": r.get("vote_note", ""),
            })
        except (KeyError, ValueError):
            continue

    map_names = {r["tile"]: r["name"] for r in read_tsv(os.path.join(gf, "map_names.tsv"))}
    # #599: how check_region_triage describes each region decision (GUESSED / CONFLICT / ...).
    triage_how = {int(r["flag"]): r["how"]
                  for r in read_tsv(os.path.join(gf, "check_region_triage.tsv"))
                  if r.get("flag", "").isdigit() and r.get("how")}
    # The default progression-surface classes, parsed rather than imported: eldenring/__init__
    # pulls Archipelago's BaseClasses, and this tool is AP-free on purpose.
    SURFACE_DEFAULT = frozenset(load_module_consts(
        os.path.join(er, "contract.py"), ("SURFACE_DEFAULT_CLASSES",))["SURFACE_DEFAULT_CLASSES"])
    desc_by_flag = {int(r["flag"]): r["description"]
                    for r in read_tsv(os.path.join(gf, "location_descriptions.tsv"))}

    # --- the OTHER gate corpora ------------------------------------------------------
    # lot_gates.tsv is only one of FOUR tables that document gating, and it is the
    # smallest. A panel that showed only it would teach the reader that 110/4879 checks
    # are gated -- the exact partial-read that has produced wrong claims here before.
    # Every corpus below carries polarity/semantic caveats in its own header; those
    # headers are lifted VERBATIM into the UI (see tsv_caveats) rather than paraphrased,
    # because flattening e.g. NO_ENTITY_HANDLE to "gated: no" inverts its meaning.
    enablers_by_flag = defaultdict(list)
    for r in read_tsv(os.path.join(gf, "treasure_enablers.tsv")):
        try:
            f = int(r["flag"])
        except (KeyError, ValueError):
            continue
        enablers_by_flag[f].append({
            "verdict": r.get("verdict", ""), "kind": r.get("gate_kind", ""),
            "self": r.get("self_set_flags", ""), "ext": r.get("external_gate_flags", ""),
            "extin": r.get("external_flag_set_in", ""), "verbatim": r.get("gate_verbatim", ""),
            "ev": r.get("enabler_event", ""), "map": r.get("map_id", ""),
            "chest": r.get("in_chest", ""),
        })

    startdisabled = set()
    for r in read_tsv(os.path.join(gf, "msb_gated_treasures.tsv")):
        try:
            startdisabled.add(int(r["flag"]))
        except (KeyError, ValueError):
            continue

    # esd_gifts: NPC dialogue hands over an ItemLotParam lot. Join lot -> flag through
    # flag_lots so a gift row lands on the check it actually feeds.
    flag_of_lot = {}
    for r in read_tsv(os.path.join(gf, "flag_lots.tsv")):
        try:
            flag_of_lot.setdefault(r["lot"], int(r["flag"]))
        except (KeyError, ValueError):
            continue
    gifts_by_flag = defaultdict(list)
    gift_unjoined = []
    for r in read_tsv(os.path.join(gf, "esd_gifts.tsv")):
        lot = r.get("item_lot", "")
        row = {"talk": r.get("talk_id", ""), "gate": r.get("gate_flag", ""),
               "sense": r.get("gate_sense", ""), "lot": lot}
        f = flag_of_lot.get(lot)
        if f is None:
            gift_unjoined.append(row)
        else:
            gifts_by_flag[f].append(row)

    # esd_gates: a merchant TALK gates a ShopLineupParam RANGE. Expand the range onto
    # the shop rows inside it, then onto those rows' stock flags.
    shop_flag_of_row = {}
    for r in read_tsv(os.path.join(gf, "shop_rows.tsv")):
        try:
            shop_flag_of_row[int(r["row_id"])] = int(r["stock_flag"])
        except (KeyError, ValueError):
            continue
    esd_shop_by_flag = defaultdict(list)
    for r in read_tsv(os.path.join(gf, "esd_gates.tsv")):
        try:
            lo, hi = int(r["shop_begin"]), int(r["shop_end"])
        except (KeyError, ValueError):
            continue
        for row_id, f in shop_flag_of_row.items():
            if lo <= row_id <= hi:
                esd_shop_by_flag[f].append({"talk": r.get("talk_id", ""),
                                            "gate": r.get("gate_flag", ""),
                                            "sense": r.get("gate_sense", ""),
                                            "range": f"{lo}-{hi}"})

    # --- positions, for the MAP tab ---------------------------------------------------
    # Plotting the CURRENT FILTER makes a whole bug class visual: a misregioned check is a
    # colour outlier, a tile-straddle question is "look at the border". 🛑 The calibration
    # covers BASE OVERWORLD + DLC only -- interiors have no position on these two maps.
    # Those are counted and stated, never silently dropped, or the map would imply spatial
    # coverage the data does not have.
    pos_by_flag = defaultdict(list)
    for r in read_tsv(os.path.join(gf, "item_grace_coords.tsv")):
        if r.get("kind") != "item":
            continue
        try:
            f, x, z = int(r["key"]), float(r["x"]), float(r["z"])
        except (KeyError, ValueError):
            continue
        w = world_xz(r["map_id"], x, z)
        if w:
            pos_by_flag[f].append({"b": w[0], "gx": round(w[1], 1), "gz": round(w[2], 1)})

    cal = {}
    for key, fn in (("m60", "map_calibration.json"), ("m61", "map_calibration_dlc.json")):
        p = os.path.join(root, "greenfield", "maps", fn)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                cal[key] = json.load(fh)

    def tsv_caveats(name):
        """The '#' header of a generated tsv, VERBATIM. These headers carry the polarity
        and 'this is not a risk list' warnings; the UI shows them next to the data."""
        out = []
        with open(os.path.join(gf, name), encoding="utf-8") as fh:
            for line in fh:
                if not line.startswith("#"):
                    break
                out.append(line[1:].rstrip())
        return "\n".join(out).strip()

    shop_by_flag = defaultdict(list)
    for r in read_tsv(os.path.join(gf, "shop_rows.tsv")):
        try:
            f = int(r["stock_flag"])
        except (KeyError, ValueError):
            continue
        shop_by_flag[f].append(
            {"row": r.get("row_id", ""), "item": r.get("item_name", ""),
             "value": r.get("value", ""), "where": r.get("region", "")}
        )

    # --- assemble ------------------------------------------------------------
    checks = []
    for region, entries in LOCATIONS.items():
        for name, ap_id, flag in entries:
            # short name: strip the "Region :: " prefix and the trailing [fNNNN]
            # #936: the baked ", also granted by <boss> (<tile>)" clause is a CORPUS fact --
            # every check a sweep COULD pay -- and this page has no seed, so presenting it inside
            # the name reads as a promise this browser cannot make (colombius, Discord
            # 2026-08-27: a Golden Seed whose name named the Fire Giant, in a seed whose
            # progression-surface cut had taken it back out of that sweep). Split it off and let
            # the template say "sweep-eligible" instead.
            honest, sweep_boss, sweep_tile = split_sweep_clause(name)
            short = honest.split(" :: ", 1)[-1]
            short = re.sub(r"\s*\[f\d+\]\s*$", "", short)
            mrows = maps_by_flag.get(flag, [])
            tiles = sorted({m["map"] for m in mrows})
            rec = {
                "id": ap_id,
                "f": flag,
                "n": short,
                "full": honest,
                # ("<boss>", "<tile>") when a sweep in the CORPUS lists this check; the page
                # renders it as eligibility, never as this-seed truth. [] when none.
                "sw": [sweep_boss, sweep_tile or ""] if sweep_boss else [],
                "r": region,
                "t": TAGS.get(ap_id, []),
                "maps": tiles,
                "mapn": [map_names[t] for t in tiles if t in map_names],
                "msrc": sorted({m["src"] for m in mrows if m["src"]}),
                "g": grace_by_flag.get(flag, ""),
                "gates": gates_by_flag.get(flag, []),
                "lots": lots_by_flag.get(flag, []),
                "shop": shop_by_flag.get(flag, []),
                "desc": desc_by_flag.get(flag, ""),
                # gate evidence from the OTHER three corpora
                "enab": enablers_by_flag.get(flag, []),
                "gift": gifts_by_flag.get(flag, []),
                "eshop": esd_shop_by_flag.get(flag, []),
                "sd": flag in startdisabled,
                "pos": pos_by_flag.get(flag, []),
            }
            # #599 REPORT-A-MISREGION. Three fields, and ONLY when they say something, so the
            # payload grows by the rows that matter rather than by 4879 nulls.
            #   how  -- check_region_triage's own word: this region was a nearest-neighbour hop
            #           (GUESSED) or two sources disagreed (CONFLICT), not first-hand evidence.
            #   surf -- carries a contract.SURFACE_DEFAULT_CLASSES tag, so a default seed can hang
            #           progression here and a wrong region is the expensive kind.
            # 🛑 Neither is a verdict. They are what a reporter would otherwise have to know to
            # write a useful report, which is exactly the knowledge we are trying not to require.
            if flag in triage_how:
                rec["how"] = triage_how[flag]
            if set(TAGS.get(ap_id, [])) & SURFACE_DEFAULT:
                rec["surf"] = 1
            # a flag on both _00 and _10 map versions is ONE physical spot, not two dots
            seen, uniq = set(), []
            for p in rec["pos"]:
                k = (p["b"], round(p["gx"]), round(p["gz"]))
                if k not in seen:
                    seen.add(k)
                    uniq.append(p)
            rec["pos"] = uniq
            if ap_id in MISSABLE:
                rec["miss"] = MISSABLE[ap_id]
            fl = []
            if ap_id in DEFAULTED:
                fl.append("defaulted-region")
            if ap_id in BURN:
                fl.append("erdtree-burn")
            if fl:
                rec["fl"] = fl
            checks.append(rec)

    checks.sort(key=lambda c: (c["r"], c["n"]))

    # --- ORACLE REGION REVIEW: the evidence a reviewer needs, joined onto the queued rows -----
    # nearest_grace.tsv names the closest Site of Grace; it does NOT say which region that grace
    # is in, and there is no committed grace->region table. So derive it from OUR OWN corpus: the
    # region the other checks sharing that grace sit in, by strict plurality. Rows currently IN the
    # queue are excluded from their own vote, so the candidate a reviewer sees is independent of
    # the assignment under review rather than a restatement of it. A grace whose checks split
    # evenly maps to nothing and yields NO candidate -- silence, not a guess.
    # 🛑 A candidate is a QUESTION, not a verdict. The same nearest-neighbour hop that produced
    # many of these regions in the first place is what this vote is made of; it ranks, it does not
    # adjudicate. Fixes go through the derivation ladder in a later PR, never from this page.
    grace_votes = defaultdict(Counter)
    for c in checks:
        if c["g"] and c["id"] not in queue_by_ap:
            grace_votes[c["g"]][c["r"]] += 1
    grace_region = {}
    for g, counter in grace_votes.items():
        top = counter.most_common(2)
        if len(top) == 1 or top[0][1] > top[1][1]:
            grace_region[g] = top[0][0]

    queued_checks = 0
    grace_candidates = 0
    for c in checks:
        q = queue_by_ap.get(c["id"])
        if not q:
            continue
        queued_checks += 1
        c["oq"] = q["status"]
        c["oqb"] = q["basis"]
        if q["reviewer"]:
            c["oqw"] = q["reviewer"]
        if q["note"]:
            c["oqn"] = q["note"]
        gr = grace_region.get(c["g"])
        if gr:
            c["gr"] = gr
            if gr != c["r"]:
                c["grc"] = 1          # the nearest grace's region is a CANDIDATE for this row
                grace_candidates += 1
        so = second_by_ap.get(c["id"])
        if so:
            c["so"] = so

    # --- ORACLE MISSABLE REVIEW: the same treatment for the second queue --------------------
    # No derived ranking signal here, deliberately. The region queue has a nearest-grace vote
    # because geometry offers one; missability has no such neighbour to ask, so the panel carries
    # OUR condition roots and the quest features that mention the flag, and stops there rather
    # than inventing a score out of a row count.
    missable_checks = 0
    for c in checks:
        m = missable_by_ap.get(c["id"])
        if not m:
            continue
        missable_checks += 1
        c["mq"] = m["status"]
        c["mqc"] = m["conds"]
        if m["reviewer"]:
            c["mqw"] = m["reviewer"]
        if m["note"]:
            c["mqn"] = m["note"]

    # --- NEGATIVE SPACE ---------------------------------------------------------------
    # Every wrong claim this project has produced lived in a JOIN RESIDUAL: rows that
    # exist in a side table but are not checks. "~126 invisible lots" was 98 already-
    # checks / 32 flagless / 0 new; "27 phantoms" was the wrong table entirely. Making
    # the residual queryable is the difference between a lost day and one search.
    # An unexplained residual is emitted with reason "" -- honestly unknown, NOT guessed.
    check_flags = {c["f"] for c in checks}
    residuals = []

    for lot_flag, rows in sorted(lots_by_flag.items()):
        if lot_flag in check_flags:
            continue
        residuals.append({
            "k": "itemlot flag, not a check", "f": lot_flag,
            "what": ", ".join(sorted({r["name"] for r in rows if r["name"]})) or "(unnamed item)",
            "detail": ", ".join(sorted({f'{r["table"]} {r["lot"]}' for r in rows})[:4]),
            "reason": "",
        })

    for row_id, f in sorted(shop_flag_of_row.items()):
        if f in check_flags:
            continue
        residuals.append({"k": "shop row, not a check", "f": f,
                          "what": f"ShopLineupParam row {row_id}", "detail": "",
                          "reason": "stock flag is not a live AP check"})

    for row in gift_unjoined:
        residuals.append({
            "k": "ESD gift lot, no flag", "f": 0,
            "what": f'lot {row["lot"]} from talk {row["talk"]}',
            "detail": f'gate f{row["gate"]} sense {row["sense"]}',
            # esd_gifts.tsv's own header states this population and why it is not new work
            "reason": "no acquisition flag -> invisible to the flag poll (esd_gifts header)",
        })

    for r in read_tsv(os.path.join(gf, "synthetic_flag_recovery.tsv")):
        try:
            f = int(r["synthetic_flag"])
        except (KeyError, ValueError):
            continue
        ev = r.get("evidence", "")
        residuals.append({
            "k": "phantom flag: " + r.get("verdict", "?"), "f": f,
            "what": r.get("item", ""), "detail": r.get("annotation", ""),
            "reason": (ev[:400] + "…") if len(ev) > 400 else ev,
        })

    residuals.sort(key=lambda x: (x["k"], x["f"]))

    tile_regions = {}
    for c in checks:
        for t in c["maps"]:
            tile_regions.setdefault(t, set()).add(c["r"])

    meta = {
        "total": len(checks),
        "regions": sorted({c["r"] for c in checks}),
        "tags": sorted({t for c in checks for t in c["t"]}),
        "with_map": sum(1 for c in checks if c["maps"]),
        "with_grace": sum(1 for c in checks if c["g"]),
        "with_gate": sum(1 for c in checks if c["gates"]),
        "missable": sum(1 for c in checks if "miss" in c),
        # gate evidence, counted per corpus so nobody reads one number as "the" answer
        "gate_lot": sum(1 for c in checks if c["gates"]),
        "gate_enabler": sum(1 for c in checks if c["enab"]),
        "gate_gift": sum(1 for c in checks if c["gift"]),
        "gate_eshop": sum(1 for c in checks if c["eshop"]),
        "gate_any": sum(1 for c in checks
                        if c["gates"] or c["enab"] or c["gift"] or c["eshop"]),
        "residuals": len(residuals),
        "plottable": sum(1 for c in checks if c["pos"]),
        # The "Oracle region review" facet. `queued` is what the committed tsv holds; the
        # per-status split and the grace-candidate count are what the facet's header states, so a
        # reviewer can see how much of the queue is still open without counting rows by eye.
        "oracle_queue": {
            "queued": queued_checks,
            "status": dict(sorted(Counter(c["oq"] for c in checks if "oq" in c).items())),
            "grace_candidate": grace_candidates,
            "second_opinion": sum(1 for c in checks if "oq" in c and "so" in c),
        },
        # The "Oracle missable review" facet's header. Same shape as the region one above: what
        # the committed tsv holds, and how much of it is still open.
        "oracle_missable_queue": {
            "queued": missable_checks,
            "status": dict(sorted(Counter(c["mq"] for c in checks if "mq" in c).items())),
            "conditions": dict(sorted(Counter(c["mqc"] for c in checks if "mq" in c).items())),
        },
        "cal": cal,
        "caveats": {n: tsv_caveats(n + ".tsv") for n in
                    ("treasure_enablers", "esd_gates", "esd_gifts",
                     "msb_gated_treasures", "lot_gates")},
        # #599: tiles whose checks do NOT all share a region. Emitted so the report form can
        # show a reporter the OTHER regions on their check's tile without them joining two tsvs.
        # 🛑 NOT a defect list. An interior map id covers an enormous space and may own two
        # regions legitimately (m21_00 holds the Golden Hippopotamus arena, which region_of
        # re-homes to Scadu Altus BY DESIGN -- region_overrides.tsv records it). The form says so.
        "tile_regions": {t: sorted(rs) for t, rs in sorted(tile_regions.items())
                         if len({r for r in rs if r != "Roundtable Hold"}) > 1},
        # NOT the git commit -- see DETERMINISM in the module docstring.
        "stamp": data_stamp(os.path.join(er, "tables", "data.py")),
    }

    tpl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "check_browser_template.html")
    with open(tpl_path, encoding="utf-8") as fh:
        tpl = fh.read()
    for token, fn in (("__SVG_BASE__", "lands_between_map.svg"),
                      ("__SVG_DLC__", "land_of_shadow_map.svg")):
        p = os.path.join(root, "greenfield", "maps", fn)
        svg = ""
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                svg = fh.read()
        tpl = tpl.replace(token, json.dumps(svg))
    payload = json.dumps({"meta": meta, "checks": checks, "residuals": residuals},
                         separators=(",", ":"), sort_keys=True, ensure_ascii=False)
    html = tpl.replace("/*__DATA__*/null", payload)
    require_complete_payload(checks, meta, out_path)
    # newline='\n' so a Windows regen and a Linux regen produce the SAME bytes; the CI
    # staleness gate is a git diff and CRLF here would make it red on every platform swap.
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)

    print(json.dumps({k: v for k, v in meta.items()
                      if k not in ("regions", "tags", "caveats")}, indent=2))
    print(f"wrote {out_path} ({os.path.getsize(out_path)/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
