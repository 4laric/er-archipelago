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
  greenfield/eldenring/data.py              LOCATIONS: region -> [(name, ap_id, flag)]
  greenfield/eldenring/location_tags.py     LOCATION_TAGS + DEFAULTED/BURN ap-id sets
  greenfield/eldenring/missable_locations.py MISSABLE_LOCATIONS: ap_id -> reason
  greenfield/check_maps.tsv                 flag -> physical map tile(s)
  greenfield/nearest_grace.tsv              flag -> nearest Site of Grace
  greenfield/lot_gates.tsv                  flag -> gate flag(s)
  greenfield/flag_lots.tsv                  flag -> ItemLotParam rows
  greenfield/map_names.tsv                  map tile -> dungeon name
  greenfield/location_descriptions.tsv      hand-authored descriptions
  greenfield/shop_rows.tsv                  ShopLineupParam row detail

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
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = "er-archipelago-check-browser.html"


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
                    # frozenset([...]) etc.
                    src = ast.unparse(node.value)
                    m = re.match(r"frozenset\((\[.*\])\)$", src, re.S)
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

    d = load_module_consts(os.path.join(er, "data.py"), {"LOCATIONS", "REGIONS", "HUB", "NOT_RANDOMIZED"})
    tagmod = load_module_consts(
        os.path.join(er, "location_tags.py"),
        {"LOCATION_TAGS", "TAG_COUNTS", "DEFAULTED_REGION_APS", "ERDTREE_BURN_APS",
         "SHOP_RELEASE_GATED_APS", "SURFACE_EXCLUDE_APS"},
    )
    miss = load_module_consts(os.path.join(er, "missable_locations.py"), {"MISSABLE_LOCATIONS"})

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

    map_names = {r["tile"]: r["name"] for r in read_tsv(os.path.join(gf, "map_names.tsv"))}
    desc_by_flag = {int(r["flag"]): r["description"]
                    for r in read_tsv(os.path.join(gf, "location_descriptions.tsv"))}

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
            short = name.split(" :: ", 1)[-1]
            short = re.sub(r"\s*\[f\d+\]\s*$", "", short)
            mrows = maps_by_flag.get(flag, [])
            tiles = sorted({m["map"] for m in mrows})
            rec = {
                "id": ap_id,
                "f": flag,
                "n": short,
                "full": name,
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
            }
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

    meta = {
        "total": len(checks),
        "regions": sorted({c["r"] for c in checks}),
        "tags": sorted({t for c in checks for t in c["t"]}),
        "with_map": sum(1 for c in checks if c["maps"]),
        "with_grace": sum(1 for c in checks if c["g"]),
        "with_gate": sum(1 for c in checks if c["gates"]),
        "missable": sum(1 for c in checks if "miss" in c),
        # NOT the git commit -- see DETERMINISM in the module docstring.
        "stamp": data_stamp(os.path.join(er, "data.py")),
    }

    tpl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "check_browser_template.html")
    with open(tpl_path, encoding="utf-8") as fh:
        tpl = fh.read()
    payload = json.dumps({"meta": meta, "checks": checks},
                         separators=(",", ":"), sort_keys=True, ensure_ascii=False)
    html = tpl.replace("/*__DATA__*/null", payload)
    # newline='\n' so a Windows regen and a Linux regen produce the SAME bytes; the CI
    # staleness gate is a git diff and CRLF here would make it red on every platform swap.
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)

    print(json.dumps({k: v for k, v in meta.items() if k not in ("regions", "tags")}, indent=2))
    print(f"wrote {out_path} ({os.path.getsize(out_path)/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
