#!/usr/bin/env python3
"""Inventory unique non-shop map pickups for category-first v0.6 review.

This is a review queue, not evidence.  It deliberately excludes repeated item names,
shops, and boss-tagged checks: those need different adjudication methods.  Interior
maps (m10..m59) are reported separately from open-world maps (m60/m61).
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = os.path.join(str(ROOT), "greenfield", "evidence", "wiki-audit", "dungeon-field-unique-review.tsv")
SUMMARY_OUTPUT = os.path.join(str(ROOT), "greenfield", "evidence", "wiki-audit", "dungeon-field-unique-review-summary.json")
OUT_PATH = Path(OUT)
SUMMARY_PATH = Path(SUMMARY_OUTPUT)
FIELDS = ("check_id", "category", "region", "item_name", "flag", "map_id",
          "review_status", "external_family_count", "external_families", "next_evidence")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def item_name(location: str) -> str:
    value = location.split(" :: ", 1)[-1]
    value = re.sub(r"\s*\[f\d+\]\s*$", "", value)
    value = value.split(", may be sweep-granted", 1)[0]
    value = value.split(" - ", 1)[0]
    return re.sub(r"^\[(?:Incantation|Sorcery)\]\s*", "", value).strip()


def build() -> tuple[list[dict[str, str]], dict[str, object]]:
    data = load_module(ROOT / "greenfield/eldenring/data.py", "_df_data")
    tags = load_module(ROOT / "greenfield/eldenring/location_tags.py", "_df_tags")
    checks = [(region, name, int(ap), int(flag)) for region, entries in data.LOCATIONS.items()
              for name, ap, flag in entries]
    name_counts = Counter(item_name(name).casefold() for _, name, _, _ in checks)
    with (ROOT / "greenfield/evidence/v060-current/progression_host_confidence.tsv").open(
            encoding="utf-8", newline="") as handle:
        confidence = {int(row["check_id"]): row for row in csv.DictReader(handle, delimiter="\t")}

    rows: list[dict[str, str]] = []
    excluded = Counter()
    for region, name, ap_id, flag in checks:
        match = re.search(r"\((m\d{2}(?:_\d{2}){1,3})\)", name)
        if not match:
            excluded["no_map_anchor"] += 1
            continue
        item = item_name(name)
        if name_counts[item.casefold()] != 1:
            excluded["repeated_item_name"] += 1
            continue
        check_tags = set(tags.LOCATION_TAGS.get(ap_id, ()))
        if "Shop" in check_tags:
            excluded["shop"] += 1
            continue
        if "Boss" in check_tags:
            excluded["boss"] += 1
            continue
        map_id = match.group(1)
        category = "unique_dungeon_pickup" if int(map_id[1:3]) < 60 else "unique_field_pickup"
        evidence = confidence[ap_id]
        families = evidence["external_families"]
        family_count = int(evidence["external_family_count"])
        status = "trusted" if evidence["confidence"] == "trusted_identity_region" else (
            "audited_one_family" if family_count else "remaining_unreviewed")
        rows.append({
            "check_id": str(ap_id), "category": category, "region": region,
            "item_name": item, "flag": str(flag), "map_id": map_id,
            "review_status": status, "external_family_count": str(family_count),
            "external_families": families,
            "next_evidence": ("none_identity_region_trusted" if status == "trusted" else
                              "second_independent_identity_region_source" if family_count else
                              "first_independent_identity_region_source"),
        })
    rows.sort(key=lambda row: (row["category"], row["region"], row["item_name"], int(row["check_id"])))
    by_category: dict[str, dict[str, int]] = {}
    for category in ("unique_dungeon_pickup", "unique_field_pickup"):
        category_rows = [row for row in rows if row["category"] == category]
        counts = Counter(row["review_status"] for row in category_rows)
        by_category[category] = {
            "total": len(category_rows), "trusted": counts["trusted"],
            "audited_one_family": counts["audited_one_family"],
            "held": counts["audited_one_family"] + counts["remaining_unreviewed"],
            "conflicted": 0, "remaining_unreviewed": counts["remaining_unreviewed"],
        }
    summary = {
        "schema_version": 1,
        "scope": "unique non-shop non-boss map-anchored pickups",
        "policy": {
            "unique": "normalized AP item name occurs once in the current corpus",
            "dungeon": "descriptor map family m10 through m59",
            "field": "descriptor map family m60 or m61",
            "excluded": "repeated names, shops, bosses, and rows without a map anchor",
            "trust": "at least two independent external identity_region families",
        },
        "by_category": by_category,
        "excluded": dict(sorted(excluded.items())),
    }
    return rows, summary


def render_tsv(rows: list[dict[str, str]]) -> str:
    import io
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rows, summary = build()
    tsv = render_tsv(rows)
    report = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not OUT_PATH.is_file() or OUT_PATH.read_text(encoding="utf-8") != tsv:
            raise SystemExit(f"STALE: {OUT_PATH.relative_to(ROOT)}")
        if not SUMMARY_PATH.is_file() or SUMMARY_PATH.read_text(encoding="utf-8") != report:
            raise SystemExit(f"STALE: {SUMMARY_PATH.relative_to(ROOT)}")
        print(f"dungeon/field unique review: OK -- {len(rows)} checks")
        return 0
    OUT_PATH.write_text(tsv, encoding="utf-8", newline="\n")
    SUMMARY_PATH.write_text(report, encoding="utf-8", newline="\n")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
