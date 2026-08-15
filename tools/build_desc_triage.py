#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_desc_triage.py -- rank the checks that most need a HAND description, on a map.

Writes er-archipelago-desc-triage.html: an offline annotation surface for filling in
greenfield/location_descriptions.tsv (layer 1 of the desc_sources waterfall). It answers the
only question that matters when authoring those rows -- "which check is which?" -- by putting
a check and its INDISTINGUISHABLE SIBLINGS on the Lands Between / Land of Shadow map together.

WHY THIS EXISTS. desc_sources.py builds every check a description from a 6-layer waterfall, and
when the waterfall still can't separate two checks, collision_ordinals() appends "(1)"/"(2)" as a
last-resort uniqueness backstop. That ordinal is the defect made visible: MEASURED on this data,
986 checks carry one -- 36 "Golden Rune [1] -- around Palace Approach Ledge-Road" in Mohgwyn
alone, and 4 "Dragon Heart" in Liurnia. A player reading the tracker sees identical rows and a
number. A hand row in location_descriptions.tsv is the ONLY fix, and writing one requires knowing
how the siblings differ SPATIALLY -- which is why this tool is a map and not a list.

NEED SCORE (transparent, rendered per row as the chips you see in the UI):
    +100  item name is literally "check"   -- no item name at all, the worst row a tracker can show
    + 50  carries a collision ordinal      -- provably indistinguishable from >=1 sibling
    + 25  layer 6 BARE                     -- no descriptor whatsoever
    + 20  layer 5 LOCALE                   -- machine noise ("treasure . m60_33_41"), not a place
    + 10  layer 4b tile-grace ("around")   -- ~256 m coarse, not the exact position
    + 15  important tag (Boss/KeyItem/Legendary/Seedtree/Fragment/Revered/GreatRune/...)
    - 30  bulk filler item (Golden Rune, Rada Fruit, Smithing Stone, ...)  -- deprioritised, NOT hidden
    ---   a check that already HAS a hand override scores 0 and is filtered out by default

The score is a triage heuristic, not a truth claim. It is shown decomposed so you can disagree
with it row by row rather than having to trust it.

COORDINATES. Overworld rows are placed with the LOD-aware fold:
    lod   = int(suffix[1]) if the map id has a 4th field else (2 if tileX < 30 else 0)
    pitch = 256 << lod
    world = tile*pitch + local + (pitch-256)/2
then through map_calibration.json's exact transform. The 4th map-id field is [version][lod]
(LOD documented at greenfield/eldenring/tests/test_gf_lod_tile_regions.py and gen_data.py:177);
the (pitch-256)/2 centring term and the "no 4th field + low tile = truncated LOD2" rule are
INFERRED -- see the DESC-TRIAGE section of AGENTS.md for the evidence and how to falsify them.
Interior checks have no position on these two maps and are marked notplottable, not guessed at.

Run:  python tools/build_desc_triage.py [--out PATH] [--repo ROOT]
"""
import argparse
import ast
import json
import os
import re
from collections import defaultdict

# world_xz lives in build_check_browser so BOTH pages fold coordinates identically --
# two copies of an inferred transform would drift and only one would be pinned by tests.
from build_check_browser import load_module_consts, read_tsv, data_stamp, world_xz

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = "er-archipelago-desc-triage.html"

NAME_RE = re.compile(r"^(?P<region>.*?) :: (?P<rest>.*?) \[f(?P<flag>\d+)\]$")
ORD_RE = re.compile(r"\s\((\d+)\)$")
# The sweep clause a member carries (er-archipelago#670): ", also granted by <boss> (<tile>)".
# 🛑 STRIPPED BEFORE ANYTHING ELSE READS THE NAME, and it must be. It is an ANNOTATION, not a
# descriptor -- this tool exists to judge whether a descriptor distinguishes a check from its
# siblings, and two checks can be equally indistinguishable while being swept by different bosses.
# Leaving it in did two things at once: it sat AFTER the ordinal so `ORD_RE` (anchored at `$`) no
# longer matched, and it split the (region, item, desc) family key -- so a sibling pair became one
# check with a lone ordinal and one with none, which is exactly what
# `test_collision_ordinals_come_in_families` calls "a parse bug". It was right.
SWEEP_CLAUSE_RE = re.compile(r",\s*also granted by .*$")
LOCALE_RE = re.compile(r"^(?:world drop|treasure|enemy drop|shop|event|gesture)\s·\s|^m\d\d")

IMPORTANT = {"Boss", "MajorBoss", "GreatRune", "Remembrance", "KeyItem", "Legendary",
             "Seedtree", "Fragment", "Revered", "Church", "Basin"}
FILLER_RE = re.compile(
    r"^(Golden Rune|Rada Fruit|Starlight Shards?|Smithing Stone|Somber Smithing Stone|"
    r"Grave Glovewort|Ghost Glovewort|Arteria Leaf|Rune Arc|Lost Ashes|Beast Blood|"
    r"Golden Centipede|Fire Blossom|Trina's Lily|Herba|Mushroom|Crystal Cave Moss)")


def split_name(name):
    """'Region :: Item - desc (2) [f123]' -> (region, item, desc, ordinal, flag).

    The #670 sweep clause is stripped first -- see SWEEP_CLAUSE_RE for why it cannot be part of
    `desc`."""
    m = NAME_RE.match(name)
    if not m:
        return None
    rest = SWEEP_CLAUSE_RE.sub("", m.group("rest"))
    o = ORD_RE.search(rest)
    ordinal = int(o.group(1)) if o else None
    if o:
        rest = rest[:o.start()]
    item, desc = rest.split(" - ", 1) if " - " in rest else (rest, "")
    return m.group("region"), item, desc, ordinal, int(m.group("flag"))


def desc_layer(flag, desc, overrides):
    """Which waterfall layer produced this description. Derived from the SHIPPED name, so it
    cannot drift from what the tracker actually renders."""
    if flag in overrides:
        return "1-override"
    if not desc:
        return "6-bare"
    if desc.startswith("from "):
        return "3b-merchant"
    if desc.startswith("near "):
        return "4-grace"
    if desc.startswith("around "):
        return "4b-tile"
    if LOCALE_RE.match(desc):
        return "5-locale"
    return "2/3-boss-or-spot"



def score(rec):
    """Need score + the human reasons for it. Returns (score, [reason, ...])."""
    s, why = 0, []
    if rec["item"].strip() == "check":
        s += 100; why.append("no item name")
    if rec.get("ord"):
        s += 50; why.append("indistinguishable sibling")
    layer = rec["layer"]
    if layer == "6-bare":
        s += 25; why.append("no descriptor")
    elif layer == "5-locale":
        s += 20; why.append("machine locale")
    elif layer == "4b-tile":
        s += 10; why.append("coarse (tile-grace)")
    if IMPORTANT & set(rec["t"]):
        s += 15; why.append("important item")
    if FILLER_RE.match(rec["item"]):
        s -= 30; why.append("bulk filler")
    return s, why


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    root, gf = args.repo, os.path.join(args.repo, "greenfield")
    er = os.path.join(gf, "eldenring")
    out_path = args.out or os.path.join(root, DEFAULT_OUT)

    LOCATIONS = load_module_consts(os.path.join(er, "data.py"), {"LOCATIONS"})["LOCATIONS"]
    TAGS = load_module_consts(os.path.join(er, "location_tags.py"), {"LOCATION_TAGS"})["LOCATION_TAGS"]
    overrides = {int(r["flag"]): r["description"]
                 for r in read_tsv(os.path.join(gf, "location_descriptions.tsv"))}

    grace_by_flag = {int(r["flag"]): r["grace_name"]
                     for r in read_tsv(os.path.join(gf, "nearest_grace.tsv"))}
    maps_by_flag = defaultdict(set)
    for r in read_tsv(os.path.join(gf, "check_maps.tsv")):
        maps_by_flag[int(r["flag"])].add(r["map_id"])
    lots_by_flag = defaultdict(list)
    for r in read_tsv(os.path.join(gf, "flag_lots.tsv")):
        lots_by_flag[int(r["flag"])].append(r.get("name", ""))

    # --- coordinates -----------------------------------------------------------------
    pos_by_flag = defaultdict(list)
    graces = []
    for r in read_tsv(os.path.join(gf, "item_grace_coords.tsv")):
        try:
            x, z = float(r["x"]), float(r["z"])
        except (KeyError, ValueError):
            continue
        w = world_xz(r["map_id"], x, z)
        if not w:
            continue
        base, gx, gz = w
        if r["kind"] == "grace":
            graces.append({"b": base, "gx": round(gx, 1), "gz": round(gz, 1), "n": r.get("name", "")})
        else:
            try:
                f = int(r["key"])
            except ValueError:
                continue
            pos_by_flag[f].append({"b": base, "gx": round(gx, 1), "gz": round(gz, 1),
                                   "m": r["map_id"]})

    cal = {}
    for key, fn in (("m60", "map_calibration.json"), ("m61", "map_calibration_dlc.json")):
        p = os.path.join(root, "poptracker", "maps", fn)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                cal[key] = json.load(fh)

    # --- assemble ---------------------------------------------------------------------
    recs = []
    for region, entries in LOCATIONS.items():
        for name, ap_id, flag in entries:
            parts = split_name(name)
            if not parts:
                continue
            _reg, item, desc, ordinal, _f = parts
            rec = {"id": ap_id, "f": flag, "r": region, "item": item, "desc": desc,
                   "ord": ordinal, "t": TAGS.get(ap_id, []),
                   "layer": desc_layer(flag, desc, overrides),
                   "g": grace_by_flag.get(flag, ""),
                   "maps": sorted(maps_by_flag.get(flag, ())),
                   "lots": sorted({n for n in lots_by_flag.get(flag, []) if n}),
                   "pos": [dict(p) for p in pos_by_flag.get(flag, [])]}
            if flag in overrides:
                rec["have"] = overrides[flag]
            rec["s"], rec["why"] = score(rec)
            # de-dup map-version twins: the same flag on _00 and _10 is ONE physical spot
            seen, uniq = set(), []
            for p in rec["pos"]:
                k = (p["b"], round(p["gx"]), round(p["gz"]))
                if k not in seen:
                    seen.add(k); uniq.append(p)
            rec["pos"] = uniq
            recs.append(rec)

    # sibling families: checks a player literally cannot tell apart (same region+item+desc)
    fam = defaultdict(list)
    for r in recs:
        if r["ord"]:
            fam[(r["r"], r["item"], r["desc"])].append(r["f"])
    for r in recs:
        sibs = fam.get((r["r"], r["item"], r["desc"]))
        if sibs and len(sibs) > 1:
            r["sib"] = [f for f in sibs if f != r["f"]]

    recs.sort(key=lambda r: (-r["s"], r["r"], r["item"], r["f"]))

    meta = {
        "total": len(recs),
        "stamp": data_stamp(os.path.join(er, "data.py")),
        "have_override": sum(1 for r in recs if "have" in r),
        "ambiguous": sum(1 for r in recs if r["ord"]),
        "families": sum(1 for v in fam.values() if len(v) > 1),
        "noitem": sum(1 for r in recs if r["item"].strip() == "check"),
        "bare": sum(1 for r in recs if r["layer"] == "6-bare"),
        "locale": sum(1 for r in recs if r["layer"] == "5-locale"),
        "plottable": sum(1 for r in recs if r["pos"]),
        "layers": {k: sum(1 for r in recs if r["layer"] == k)
                   for k in sorted({r["layer"] for r in recs})},
        "cal": cal,
    }

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "desc_triage_template.html"), encoding="utf-8") as fh:
        tpl = fh.read()
    for key, fn in (("__SVG_BASE__", "lands_between_map.svg"),
                    ("__SVG_DLC__", "land_of_shadow_map.svg")):
        p = os.path.join(root, "poptracker", "maps", fn)
        svg = ""
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                svg = fh.read()
        tpl = tpl.replace(key, json.dumps(svg))
    payload = json.dumps({"meta": meta, "checks": recs, "graces": graces},
                         separators=(",", ":"), sort_keys=True, ensure_ascii=False)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(tpl.replace("/*__DATA__*/null", payload))

    print(json.dumps({k: v for k, v in meta.items() if k != "cal"}, indent=2))
    print(f"wrote {out_path} ({os.path.getsize(out_path)/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
