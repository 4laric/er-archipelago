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
import ast
import enum
import importlib.util
import json
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
PACK_ROOT = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(PACK_ROOT)
DEFAULT_APWORLD = os.path.join(REPO_ROOT, "Archipelago", "worlds", "eldenring")
ROOT_REGION = "Limgrave"   # the "New Game" entrance target (graph root)

sys.path.insert(0, HERE)
import build_map  # map layer (M3a); returns empty targets + committed pins when no coord dump present

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


# ------------------------------------------------------------------------- runtime import mode
def load_runtime(apworld_dir):
    saved = dict(sys.modules)
    try:
        bc = types.ModuleType("BaseClasses")

        class ItemClassification(enum.IntFlag):
            filler = 0
            progression = 1
            useful = 2
            trap = 4
            skip_balancing = 8
            progression_skip_balancing = 9

        class _Stub:
            def __init__(self, *a, **k):
                pass

        bc.Item = _Stub
        bc.Location = _Stub
        bc.Region = _Stub
        bc.ItemClassification = ItemClassification
        sys.modules["BaseClasses"] = bc

        pkg_w = types.ModuleType("worlds")
        pkg_w.__path__ = []
        pkg_e = types.ModuleType("worlds.eldenring")
        pkg_e.__path__ = [apworld_dir]
        sys.modules["worlds"] = pkg_w
        sys.modules["worlds.eldenring"] = pkg_e

        def _load(name):
            spec = importlib.util.spec_from_file_location(
                f"worlds.eldenring.{name}", os.path.join(apworld_dir, f"{name}.py"))
            mod = importlib.util.module_from_spec(spec)
            sys.modules[f"worlds.eldenring.{name}"] = mod
            spec.loader.exec_module(mod)
            return mod

        return _load("items"), _load("locations")
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: runtime import failed ({exc}); ast fallback (no id maps).", file=sys.stderr)
        sys.modules.clear()
        sys.modules.update(saved)
        return None, None


def regions_from_runtime(locs_mod):
    dlc_set = set(locs_mod.region_order_dlc)
    order = list(locs_mod.region_order) + list(locs_mod.region_order_dlc)
    region_locations = {}
    for region, locs in locs_mod.location_tables.items():
        region_locations[region] = [(getattr(l, "name", None), getattr(l, "ap_code", None))
                                    for l in locs if getattr(l, "name", None)]
    ordered = [r for r in order if r in region_locations]
    ordered += [r for r in region_locations if r not in ordered]
    return {"ordered_regions": ordered, "dlc_set": dlc_set, "region_locations": region_locations}


def items_from_runtime(items_mod):
    out = []
    for data in items_mod.item_table.values():
        name = getattr(data, "name", None)
        if not name:
            continue
        is_lock = bool(getattr(data, "lock", False))
        if not (is_lock or _is_key(name)):
            continue
        out.append({
            "name": name, "ap_code": getattr(data, "ap_code", None), "lock": is_lock,
            "is_dlc": bool(getattr(data, "is_dlc", False)),
            "stage": int(getattr(data, "count", 1) or 1),
        })
    out.sort(key=lambda i: (not i["lock"], i["is_dlc"], i["name"]))
    return out


# ----------------------------------------------------------------------------- ast helpers
def _find_assignment(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == name:
                    return node.value
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == name and node.value:
                return node.value
    return None


def _str_list(v):
    return [e.value for e in v.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]


def _call_first_str(call):
    if call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
        return call.args[0].value
    return None


def _call_kwarg(call, key):
    for kw in call.keywords:
        if kw.arg == key:
            v = kw.value
            if isinstance(v, ast.Constant):
                return v.value
            if isinstance(v, ast.Attribute):
                return v.attr
    return None


def regions_from_ast(loc_tree):
    region_order = _str_list(_find_assignment(loc_tree, "region_order"))
    region_order_dlc = _str_list(_find_assignment(loc_tree, "region_order_dlc"))
    dlc_set = set(region_order_dlc)
    lt = _find_assignment(loc_tree, "location_tables")
    region_locations = {}
    for k, v in zip(lt.keys, lt.values):
        if not (isinstance(k, ast.Constant) and isinstance(k.value, str)):
            continue
        names = []
        if isinstance(v, ast.List):
            for elt in v.elts:
                if isinstance(elt, ast.Call):
                    n = _call_first_str(elt)
                    if n:
                        names.append((n, None))
        region_locations[k.value] = names
    ordered = [r for r in (region_order + region_order_dlc) if r in region_locations]
    ordered += [r for r in region_locations if r not in ordered]
    return {"ordered_regions": ordered, "dlc_set": dlc_set, "region_locations": region_locations}


def items_from_ast(items_tree):
    seen, out = set(), []
    for node in ast.walk(items_tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "ERItemData"):
            continue
        name = _call_first_str(node)
        if not name or name in seen:
            continue
        is_lock = _call_kwarg(node, "lock") is True
        if not (is_lock or _is_key(name)):
            continue
        seen.add(name)
        count = _call_kwarg(node, "count")
        out.append({"name": name, "ap_code": None, "lock": is_lock,
                    "is_dlc": _call_kwarg(node, "is_dlc") is True,
                    "stage": int(count) if isinstance(count, int) else 1})
    out.sort(key=lambda i: (not i["lock"], i["is_dlc"], i["name"]))
    return out


def parse_region_graph(init_path, tracked_codes):
    """ast-parse __init__.py: create_connection edges + _add_entrance_rule gates.

    A gate is classified by the METHOD that adds it (semantically correct), not the item name:
      * _region_lock      -> region-gating-only gate (applies only when world_logic < 3)
      * set_rules / other -> always-applied gate (vanilla progression, e.g. Academy Glintstone Key)
    Only gates whose item is a TRACKED pack code are kept."""
    tree = ast.parse(open(init_path, encoding="utf-8").read())
    franges = [(f.name, f.lineno, (f.body[-1].end_lineno if f.body else f.lineno))
               for f in ast.walk(tree) if isinstance(f, ast.FunctionDef)]

    def enclosing(line):
        best = None
        for nm, a, b in franges:
            if a <= line <= b and (best is None or a > best[1]):
                best = (nm, a, b)
        return best[0] if best else ""

    adj = {}     # region name -> [region name]
    locks = {}   # region name -> set(codes)   (added in _region_lock; gated-mode only)
    keys = {}    # region name -> set(codes)   (added elsewhere; always applied)
    skipped = set()
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        if isinstance(n.func, ast.Name) and n.func.id == "create_connection" and len(n.args) == 2 \
                and all(isinstance(a, ast.Constant) and isinstance(a.value, str) for a in n.args):
            adj.setdefault(n.args[0].value, []).append(n.args[1].value)
        elif isinstance(n.func, ast.Attribute) and n.func.attr == "_add_entrance_rule" \
                and len(n.args) >= 2 \
                and all(isinstance(a, ast.Constant) and isinstance(a.value, str) for a in n.args[:2]):
            region, item = n.args[0].value, n.args[1].value
            code = gate_code(item)
            if code not in tracked_codes:
                skipped.add(item)
                continue
            region_only = enclosing(n.lineno) == "_region_lock"
            (locks if region_only else keys).setdefault(region, set()).add(code)

    def conv(d):
        return {_slug(r): sorted(v) for r, v in d.items()}

    adj_slug = {}
    for a, bs in adj.items():
        adj_slug.setdefault(_slug(a), [])
        for b in bs:
            if _slug(b) not in adj_slug[_slug(a)]:
                adj_slug[_slug(a)].append(_slug(b))
    gate_codes = sorted({c for v in locks.values() for c in v} | {c for v in keys.values() for c in v})
    return {
        "adj": adj_slug, "locks": conv(locks), "keys": conv(keys),
        "root": _slug(ROOT_REGION), "gate_codes": gate_codes,
        "stats": {"edges": sum(len(v) for v in adj_slug.values()),
                  "lock_gated": len(locks), "key_gated": len(keys),
                  "skipped_untracked_gates": len(skipped)},
    }


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


def _lua_strlist(codes):
    return "{" + ", ".join(_lua_str(c) for c in codes) + "}"


def emit_region_graph_lua(graph):
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
              f"REGION_GATE_CODES = {_lua_strlist(graph['gate_codes'])}",
              "", "return REGION_ADJ"]
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------------------------- driver
def generate(apworld_dir):
    items_mod, locs_mod = load_runtime(apworld_dir)
    if items_mod and locs_mod:
        regions, items, mode = regions_from_runtime(locs_mod), items_from_runtime(items_mod), "runtime"
    else:
        with open(os.path.join(apworld_dir, "items.py"), encoding="utf-8") as f:
            items = items_from_ast(ast.parse(f.read()))
        with open(os.path.join(apworld_dir, "locations.py"), encoding="utf-8") as f:
            regions = regions_from_ast(ast.parse(f.read()))
        mode = "ast-fallback"

    tracked_codes = {item_code(it["name"], it["lock"]) for it in items}
    graph = parse_region_graph(os.path.join(apworld_dir, "__init__.py"), tracked_codes)
    section_index = build_section_index(regions)

    # map layer (M3a) FIRST: returns pins (fresh from dump, else committed) used for map_locations,
    # plus maps/* targets that are only written/checked when a coord dump is present.
    map_json, map_text, map_stats, map_pins = build_map.build(apworld_dir, PACK_ROOT, REPO_ROOT)

    items_json = emit_items_json(items)
    locations_json = emit_locations_json(regions, section_index, map_pins)
    item_grid_json = emit_item_grid(items_json)
    loc_map_lua, loc_n = emit_loc_map_lua(regions, section_index)
    ap_map_lua = emit_ap_map_lua(items)
    region_graph_lua = emit_region_graph_lua(graph)

    have_ids = mode == "runtime"
    stats = {"mode": mode, "regions": len(regions["ordered_regions"]),
             "dlc_regions": len(regions["dlc_set"]),
             "locations": sum(len(v) for v in regions["region_locations"].values()),
             "tracked_items": len(items_json), "item_ids": sum(1 for i in items if i["ap_code"]),
             "location_ids": loc_n, "map_pins": len(map_pins), **graph["stats"]}

    json_targets = [
        (os.path.join(PACK_ROOT, "items", "items.json"), items_json),
        (os.path.join(PACK_ROOT, "locations", "locations.json"), locations_json),
        (os.path.join(PACK_ROOT, "layouts", "item_grid.json"), item_grid_json),
    ]
    text_targets = [(os.path.join(PACK_ROOT, "scripts", "region_graph.lua"), region_graph_lua)]
    if have_ids:
        text_targets += [(os.path.join(PACK_ROOT, "scripts", "ap_map.lua"), ap_map_lua),
                         (os.path.join(PACK_ROOT, "scripts", "loc_map.lua"), loc_map_lua)]
    json_targets += map_json
    text_targets += map_text
    stats.update(map_stats)
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
