#!/usr/bin/env python3
"""Generate PopTracker pack data for the Elden Ring apworld.

Emits the location-shaped, churn-prone pack pieces:
    poptracker/items/items.json          tracked items (locks + curated key items)
    poptracker/locations/locations.json  one node per apworld region, checks as sections,
                                          + map_locations pins when a map has been built
    poptracker/layouts/item_grid.json    generated item grid referenced by items_only.json
    poptracker/scripts/ap_map.lua        AP item id  -> pack item code           (for on_item)
    poptracker/scripts/loc_map.lua       AP loc  id  -> "@Region/Section" code    (for on_location)
    poptracker/scripts/region_graph.lua  region adjacency + lock/key gates        (for logic.lua)
    poptracker/maps/*                     overworld map layer (only when a coord dump is present)

MODES:
  * RUNTIME (preferred): import items.py + locations.py standalone (stub `BaseClasses`, fake the
    `worlds.eldenring` package) and read the real item_table / location_dictionary, whose ap_code
    == the AP network id. Authoritative; needs no datapackage. Python 3.10+.
  * AST FALLBACK: if that import fails, parse the source literally. ap_codes can't be produced this
    way, so the id maps (ap_map/loc_map) are skipped with a warning. The region graph is ALWAYS
    built by ast-parsing __init__.py (create_connection / _add_entrance_rule), so it works in both
    modes.

Usage: gen_poptracker.py [--apworld DIR] [--check]
Pairs with TODO #15 / SPEC-poptracker-pack.md / SPEC-poptracker-map.md / BRIEF-poptracker-pipeline.md.
"""
from __future__ import annotations
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PACK_ROOT = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(PACK_ROOT)
DEFAULT_APWORLD = os.path.join(REPO_ROOT, "greenfield", "eldenring")

sys.path.insert(0, HERE)
import gf_read    # greenfield data reader (regions/items/graph from the live world data, under stubs)
import build_map  # base map layer (M3a); returns empty targets + committed pins when no coord dump present
import dlc_map    # DLC map layer (M3c, Land of Shadow); coordinate-driven, gated like build_map

KEY_ITEM_SUBSTRINGS = [
    "Great Rune",
    "Dectus Medallion", "Rold Medallion", "Haligtree Secret Medallion",
    "Academy Glintstone Key", "Rusty Key", "Imbued Sword Key", "Stonesword Key",
    "Spirit Calling Bell",
    "Pureblood Knight's Medal", "Cursemark of Death", "Fingerslayer Blade",
    "Dark Moon Ring", "Drawing-Room Key", "Discarded Palace Key",
    "Shackle", "Carian Inverted Statue",                      # region-gate key items
    "Scadutree Fragment", "Revered Spirit Ash", "Gaol", "Prayer Room Key",
    "Hole-Laden Necklace", "Messmer", "Storeroom Key",
]


def _slug(s):
    out = "".join(c.lower() if c.isalnum() else "_" for c in s)
    while "__" in out:
        out = out.replace("__", "_")
    return out.strip("_")


def _is_key(name):
    return any(sub in name for sub in KEY_ITEM_SUBSTRINGS)


def item_code(name, is_lock):
    return ("lock_" if is_lock else "key_") + _slug(name)


def gate_code(item_name):
    """Pack code a region-gate item would have IF tracked (lock items end in 'Lock')."""
    return item_code(item_name, item_name.endswith("Lock"))




# ------------------------------------------------------------------------------- section index
def build_section_index(regions):
    idx = {}
    for region in regions["ordered_regions"]:
        assert "/" not in region, f"region name contains '/': {region!r}"
        used, rows = set(), []
        for (name, ap) in regions["region_locations"].get(region, []):
            sec = name.replace("/", "-")
            base, k = sec, 2
            while sec in used:
                sec = f"{base} ({k})"
                k += 1
            used.add(sec)
            rows.append({"name": sec, "orig": name, "ap_code": ap})
        idx[region] = rows or [{"name": region, "orig": region, "ap_code": None}]
    return idx


# ----------------------------------------------------------------------------------- emitters
def emit_items_json(items):
    out = []
    for it in items:
        entry = {"name": it["name"], "type": "toggle",
                 "img": "images/items/placeholder.png", "codes": item_code(it["name"], it["lock"])}
        if it["ap_code"] is not None:
            entry["ap_code"] = it["ap_code"]
        if it["stage"] and it["stage"] > 1:
            entry["type"] = "consumable"
            entry["max_quantity"] = it["stage"]
        out.append(entry)
    return out


def emit_locations_json(regions, section_index, pins=None):
    pins = pins or {}
    out = []
    for region in regions["ordered_regions"]:
        sections = [{"name": r["name"]} for r in section_index[region]]
        is_dlc = region in regions["dlc_set"]
        node = {
            "name": region,
            "access_rules": ["$can_reach_" + _slug(region)],
            "tags": ["dlc"] if is_dlc else ["base"],
            "children": [{"name": region,
                          "access_rules": ["$can_reach_" + _slug(region)],
                          "sections": sections}],
        }
        p = pins.get(region)
        if p:
            node["map_locations"] = [{"map": p["map"], "x": p["x"], "y": p["y"]}]
        out.append(node)
    return out


def emit_item_grid(items_json):
    codes = [it["codes"] for it in items_json]
    rows = [codes[i:i + 8] for i in range(0, len(codes), 8)]
    return {"item_grid": {"type": "itemgrid", "item_margin": [2, 2], "rows": rows}}


def _lua_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def emit_ap_map_lua(items):
    lines = ["-- GENERATED by tools/gen_poptracker.py -- do not edit.",
             "-- AP item id -> pack item code (ap_code == AP network id).",
             "AP_ITEM_ID_TO_CODE = {"]
    for it in items:
        if it["ap_code"] is not None:
            lines.append(f"  [{int(it['ap_code'])}] = {_lua_str(item_code(it['name'], it['lock']))},")
    lines += ["}", "return AP_ITEM_ID_TO_CODE"]
    return "\n".join(lines) + "\n"


def emit_loc_map_lua(regions, section_index):
    lines = ["-- GENERATED by tools/gen_poptracker.py -- do not edit.",
             "-- AP location id -> PopTracker section code '@Region/Section' (for on_location).",
             "AP_LOC_ID_TO_SECTION = {"]
    n = 0
    for region in regions["ordered_regions"]:
        for r in section_index[region]:
            if r["ap_code"] is None:
                continue
            lines.append(f"  [{int(r['ap_code'])}] = {_lua_str('@' + region + '/' + r['name'])},")
            n += 1
    lines += ["}", "return AP_LOC_ID_TO_SECTION"]
    return "\n".join(lines) + "\n", n


def emit_loc_dlc_lua(regions, section_index):
    """AP location id -> 1 for every check that lives in a DLC region (Land of Shadow).
    autotracking.lua's dlc_only auto-clear sweep marks every NON-DLC check done on connect."""
    lines = ["-- GENERATED by tools/gen_poptracker.py -- do not edit.",
             "-- AP location id -> 1 when the check is in a DLC region (Land of Shadow).",
             "-- Consumed by autotracking.lua: on a dlc_only seed every non-DLC check is auto-cleared.",
             "AP_LOC_DLC = {"]
    n = 0
    for region in regions["ordered_regions"]:
        if region not in regions["dlc_set"]:
            continue
        for r in section_index[region]:
            if r["ap_code"] is None:
                continue
            lines.append(f"  [{int(r['ap_code'])}] = 1,")
            n += 1
    lines += ["}", "return AP_LOC_DLC"]
    return "\n".join(lines) + "\n", n


def _lua_strlist(codes):
    return "{" + ", ".join(_lua_str(c) for c in codes) + "}"


def emit_region_graph_lua(graph, regions):
    lines = ["-- GENERATED by tools/gen_poptracker.py -- do not edit.",
             "-- Region reachability graph (slug-keyed) for logic.lua.",
             f"REGION_ROOT = {_lua_str(graph['root'])}", "",
             "REGION_ADJ = {"]
    for slug in sorted(graph["adj"]):
        lines.append(f"  [{_lua_str(slug)}] = {_lua_strlist(graph['adj'][slug])},")
    lines += ["}", "",
              "-- Region -> lock-item codes (applied only when region gating is active):",
              "REGION_LOCK_GATES = {"]
    for slug in sorted(graph["locks"]):
        lines.append(f"  [{_lua_str(slug)}] = {_lua_strlist(graph['locks'][slug])},")
    lines += ["}", "",
              "-- Region -> key-item codes (applied in all logic modes):",
              "REGION_KEY_GATES = {"]
    for slug in sorted(graph["keys"]):
        lines.append(f"  [{_lua_str(slug)}] = {_lua_strlist(graph['keys'][slug])},")
    lines += ["}", "",
              "-- Flat list of all gate codes (logic.lua uses it to cheaply detect state changes):",
              f"REGION_GATE_CODES = {_lua_strlist(graph['gate_codes'])}", ""]

    # --- region inventory (consumed by logic.lua: defines can_reach_<slug> for EVERY region, and
    #     reroots reachability when connected to a dlc_only seed) ---
    all_slugs = sorted({_slug(r) for r in regions["ordered_regions"]})
    dlc_slugs = sorted({_slug(r) for r in regions["dlc_set"]})
    lines += ["-- Every region slug in the pack (logic.lua creates one can_reach_<slug> per entry):",
              f"REGION_ALL = {_lua_strlist(all_slugs)}", "",
              "-- DLC (Land of Shadow) region slugs; 1 == DLC:",
              "REGION_IS_DLC = {"]
    for s in dlc_slugs:
        lines.append(f"  [{_lua_str(s)}] = 1,")
    lines += ["}", "",
              "-- Graph root for a dlc_only seed: you START in Gravesite (base regions are",
              "-- locked-vanilla transit with no checks), so reachability bootstraps from here.",
              f"REGION_DLC_ROOT = {_lua_str(graph.get('dlc_root', _slug('Gravesite')))}",
              "", "return REGION_ADJ"]
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------------------------- driver
def generate(apworld_dir):
    # greenfield reader: regions/sections/AP-location-ids from data.LOCATIONS, tracked items + AP
    # item ids from core (under framework stubs), region graph from region_spine. Always id-complete
    # (no ast fallback needed -- the ids are authoritative module data).
    mods = gf_read.load_modules(apworld_dir)
    regions = gf_read.read_regions(mods)
    items = gf_read.read_items(mods, KEY_ITEM_SUBSTRINGS)
    graph = gf_read.read_region_graph(mods, regions, item_code)
    mode = "greenfield"
    section_index = build_section_index(regions)

    # map layer FIRST: each builder returns pins (fresh from dump, else committed) used for
    # map_locations, plus maps/* targets only written/checked when a coord dump is present, plus
    # its PopTracker map_def. Base (M3a, Lands Between) and DLC (M3c, Land of Shadow) regions are
    # disjoint, so the two pin dicts merge cleanly; the two map defs merge into one maps.json.
    map_json, map_text, map_stats, map_pins, base_map_def = build_map.build(
        apworld_dir, PACK_ROOT, REPO_ROOT)
    dlc_json, dlc_text, dlc_stats, dlc_pins, dlc_map_def = dlc_map.build_dlc(
        apworld_dir, PACK_ROOT, REPO_ROOT, regions["dlc_set"])
    all_pins = {**map_pins, **dlc_pins}
    maps_doc = [base_map_def, dlc_map_def]

    items_json = emit_items_json(items)
    locations_json = emit_locations_json(regions, section_index, all_pins)
    item_grid_json = emit_item_grid(items_json)
    loc_map_lua, loc_n = emit_loc_map_lua(regions, section_index)
    loc_dlc_lua, dlc_n = emit_loc_dlc_lua(regions, section_index)
    ap_map_lua = emit_ap_map_lua(items)
    region_graph_lua = emit_region_graph_lua(graph, regions)

    have_ids = True   # greenfield reader always yields authoritative AP ids
    stats = {"mode": mode, "regions": len(regions["ordered_regions"]),
             "dlc_regions": len(regions["dlc_set"]),
             "locations": sum(len(v) for v in regions["region_locations"].values()),
             "tracked_items": len(items_json), "item_ids": sum(1 for i in items if i["ap_code"]),
             "location_ids": loc_n, "dlc_location_ids": dlc_n,
             "map_pins": len(map_pins), "dlc_map_pins": len(dlc_pins), **graph["stats"]}

    json_targets = [
        (os.path.join(PACK_ROOT, "items", "items.json"), items_json),
        (os.path.join(PACK_ROOT, "locations", "locations.json"), locations_json),
        (os.path.join(PACK_ROOT, "layouts", "item_grid.json"), item_grid_json),
        (os.path.join(PACK_ROOT, "maps", "maps.json"), maps_doc),
    ]
    text_targets = [(os.path.join(PACK_ROOT, "scripts", "region_graph.lua"), region_graph_lua)]
    if have_ids:
        text_targets += [(os.path.join(PACK_ROOT, "scripts", "ap_map.lua"), ap_map_lua),
                         (os.path.join(PACK_ROOT, "scripts", "loc_map.lua"), loc_map_lua),
                         (os.path.join(PACK_ROOT, "scripts", "loc_dlc.lua"), loc_dlc_lua)]
    json_targets += map_json + dlc_json
    text_targets += map_text + dlc_text
    stats.update(map_stats)
    stats.update(dlc_stats)
    return json_targets, text_targets, stats


def _json_text(data):
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate Elden Ring PopTracker pack data.")
    ap.add_argument("--apworld", default=DEFAULT_APWORLD)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    json_targets, text_targets, stats = generate(args.apworld)

    if args.check:
        stale = []
        for path, data in json_targets:
            old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
            if old != _json_text(data):
                stale.append(os.path.relpath(path, REPO_ROOT))
        for path, text in text_targets:
            old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
            if old != text:
                stale.append(os.path.relpath(path, REPO_ROOT))
        if stale:
            print("STALE (run gen_poptracker.py): " + ", ".join(stale), file=sys.stderr)
            return 1
        print("up to date | " + json.dumps(stats))
        return 0

    for path, data in json_targets:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(_json_text(data))
    for path, text in text_targets:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    print("generated | " + json.dumps(stats))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
