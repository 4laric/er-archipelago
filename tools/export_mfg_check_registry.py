#!/usr/bin/env python3
"""Offline check/source registry. Original flags only; no independent corroboration."""
import argparse
import ast
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ("greenfield/eldenring/data.py", "greenfield/flag_lots.tsv",
          "greenfield/shop_rows.tsv", "greenfield/item_grace_coords.tsv")


def read_rows(path):
    with path.open(encoding="utf-8") as stream:
        yield from csv.DictReader(
            (line for line in stream if not line.startswith("#")), delimiter="\t")


def locations(path):
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "LOCATIONS" for t in node.targets
        ):
            return ast.literal_eval(node.value)
    raise ValueError("LOCATIONS missing from " + str(path))


def build(root=ROOT):
    root = Path(root)
    sources = {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
               for name in INPUTS}
    checks = []
    by_flag = defaultdict(list)
    for region, rows in locations(root / INPUTS[0]).items():
        for name, ap_id, flag in rows:
            if not isinstance(ap_id, int) or not isinstance(flag, int) or flag <= 0:
                raise ValueError("Invalid check identity: " + repr((ap_id, flag)))
            checks.append(dict(ap_id=ap_id, name=name, region=region,
                               original_acquisition_flag=flag))
            by_flag[flag].append(ap_id)
    if not checks or len({r["ap_id"] for r in checks}) != len(checks):
        raise ValueError("Empty catalog or duplicate AP IDs")
    lots, shops, positions = defaultdict(set), defaultdict(set), defaultdict(set)
    for row in read_rows(root / INPUTS[1]):
        if row["table"] not in ("map", "enemy"):
            raise ValueError("Unknown ItemLotParam table: " + row["table"])
        lots[int(row["flag"])].add((row["table"], int(row["lot"])))
    for row in read_rows(root / INPUTS[2]):
        shops[int(row["stock_flag"])].add(int(row["row_id"]))
    excluded = Counter()
    for row in read_rows(root / INPUTS[3]):
        if row["kind"] == "grace":
            excluded["grace_rows"] += 1
            continue
        if row["kind"] != "item":
            raise ValueError("Unknown coordinate kind: " + row["kind"])
        point = tuple(float(row[axis]) for axis in ("x", "y", "z"))
        if not all(math.isfinite(v) for v in point) or not re.fullmatch(r"m[0-9]{2}(?:_[0-9]{2}){1,3}", row["map_id"]):
            raise ValueError("Invalid physical position: " + repr(row))
        positions[int(row["key"])].add((row["map_id"], *point))
    coverage = Counter()
    for check in checks:
        flag = check["original_acquisition_flag"]
        siblings = sorted(by_flag[flag])
        check["co_triggered_ap_ids"] = siblings
        check["source_identity"] = {
            "item_lots": [dict(table=t, row_id=r) for t, r in sorted(lots[flag])],
            "shop_rows": sorted(shops[flag]),
            "scope": "acquisition_flag_group",
        }
        # The source tables do not prove a lot -> coordinate join.
        check["physical_sites"] = [
            dict(map_id=m, map_id_scope="full" if m.count("_") == 3 else "partial",
                 map_local_xyz=[x, y, z],
                 precision="datamined_part_position",
                 source=INPUTS[3], display_position=None)
            for m, x, y, z in sorted(positions[flag])
        ]
        count = len(check["physical_sites"])
        check["site_status"] = (
            "unresolved" if count == 0 else
            "ambiguous_shared_flag" if len(siblings) > 1 else
            "multiple_candidate_sites" if count > 1 else "single_candidate_site")
        coverage[check["site_status"]] += 1
    return {
        "schema_version": 1,
        "evidence_kind": "game_data_derived_not_independent_corroboration",
        "sources_sha256": sources,
        "coverage": dict(sorted(coverage.items())),
        "total_checks": len(checks),
        "excluded_rows": dict(excluded),
        "residual_source_flags": {
            label: sorted(set(table) - set(by_flag))
            for label, table in (("item_lots", lots), ("shop_rows", shops),
                                 ("physical_positions", positions))
        },
        "checks": sorted(checks, key=lambda r: r["ap_id"]),
    }


def encode(manifest):
    return json.dumps(manifest, ensure_ascii=False, sort_keys=True,
                      indent=2, allow_nan=False) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = build(args.repo)
    text = encode(result)
    if args.check:
        if not args.out.exists() or args.out.read_text(encoding="utf-8") != text:
            raise SystemExit("Registry missing or stale: " + str(args.out))
    else:
        args.out.write_text(text, encoding="utf-8")
    print(json.dumps({"total_checks": result["total_checks"],
                      "coverage": result["coverage"]}, sort_keys=True))


if __name__ == "__main__":
    main()
