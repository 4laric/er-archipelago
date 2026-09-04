#!/usr/bin/env python3
"""Inventory upgrade, flask, and DLC blessing checks for category-first review."""
from __future__ import annotations

import argparse
import csv
import importlib.util
import io
import json
import os
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = os.path.join(str(ROOT), "greenfield", "evidence", "wiki-audit", "upgrade-blessing-review.tsv")
SUMMARY_OUTPUT = os.path.join(str(ROOT), "greenfield", "evidence", "wiki-audit", "upgrade-blessing-review-summary.json")
OUT_PATH = Path(OUT)
SUMMARY_PATH = Path(SUMMARY_OUTPUT)
FIELDS = ("check_id", "category", "acquisition_class", "region", "item_name", "flag",
          "map_id", "review_status", "external_family_count", "external_families",
          "access_disposition", "next_evidence")

# PowerPyx places these landmarks in a different broad area than the current AP filing.  The
# identity is useful, but neither source taxonomy is allowed to silently decide the runtime region.
REGION_TAXONOMY_CONFLICTS = {
    7773495: "adjudicate Highroad Cross boundary: PowerPyx Scadu Altus vs AP Ensis",
    7773939: "adjudicate Church District boundary: PowerPyx Shadow Keep vs AP Scadu Altus",
}


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("_upgrade_blessing_data", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalized_item(location: str) -> str:
    value = location.split(" :: ", 1)[-1]
    value = re.sub(r"\s*\[f\d+\]\s*$", "", value)
    value = value.split(", may be sweep-granted", 1)[0]
    return value.split(" - ", 1)[0].strip()


def category_for(item: str) -> str | None:
    if item == "Scadutree Fragment":
        return "scadutree_fragment"
    if item == "Revered Spirit Ash":
        return "revered_spirit_ash"
    if item == "Golden Seed":
        return "golden_seed"
    if item == "Sacred Tear":
        return "sacred_tear"
    if "Smithing Stone" in item:
        return "smithing_stone"
    if "Glovewort" in item:
        return "glovewort"
    return None


def build() -> tuple[list[dict[str, str]], dict[str, object]]:
    data = load_module(ROOT / "greenfield/eldenring/data.py")
    checks = [(region, name, int(ap), int(flag)) for region, entries in data.LOCATIONS.items()
              for name, ap, flag in entries]
    item_counts = Counter(normalized_item(name) for _, name, _, _ in checks)
    with (ROOT / "greenfield/evidence/v060-current/progression_host_confidence.tsv").open(
            encoding="utf-8", newline="") as handle:
        confidence = {int(row["check_id"]): row for row in csv.DictReader(handle, delimiter="\t")}
    with (ROOT / "greenfield/evidence/v060-current/access_dispositions.tsv").open(
            encoding="utf-8", newline="") as handle:
        access = {int(row["check_id"]): row["disposition"]
                  for row in csv.DictReader(handle, delimiter="\t")}

    rows = []
    for region, location, ap_id, flag in checks:
        item = normalized_item(location)
        category = category_for(item)
        if category is None:
            continue
        evidence = confidence[ap_id]
        family_count = int(evidence["external_family_count"])
        trusted = evidence["confidence"] == "trusted_identity_region"
        status = ("region_taxonomy_conflict" if ap_id in REGION_TAXONOMY_CONFLICTS else
                  "trusted" if trusted else "audited_one_family" if family_count else
                  "remaining_unreviewed")
        map_match = re.search(r"\((m\d{2}(?:_\d{2}){1,3})\)", location)
        collectible = category in {"scadutree_fragment", "revered_spirit_ash",
                                   "golden_seed", "sacred_tear"}
        rows.append({
            "check_id": str(ap_id), "category": category,
            "acquisition_class": ("uniquely_anchored_collectible" if collectible else
                                  "repeated_material_row" if item_counts[item] > 1 else
                                  "unique_material_row"),
            "region": region, "item_name": item, "flag": str(flag),
            "map_id": map_match.group(1) if map_match else "",
            "review_status": status, "external_family_count": str(family_count),
            "external_families": evidence["external_families"],
            "access_disposition": access.get(ap_id, "unresolved"),
            "next_evidence": (REGION_TAXONOMY_CONFLICTS[ap_id]
                              if ap_id in REGION_TAXONOMY_CONFLICTS else
                              "none_identity_region_trusted" if trusted else
                              "second_independent_exact_landmark_source" if family_count else
                              "first_exact_landmark_source"),
        })
    rows.sort(key=lambda row: (row["category"], row["region"], row["item_name"],
                               int(row["check_id"])))
    by_category = {}
    for category in sorted({row["category"] for row in rows}):
        selected = [row for row in rows if row["category"] == category]
        counts = Counter(row["review_status"] for row in selected)
        by_category[category] = {
            "audited": len(selected), "trusted": counts["trusted"],
            "held": len(selected) - counts["trusted"],
            "conflicted": counts["region_taxonomy_conflict"],
            "audited_one_family": counts["audited_one_family"],
            "remaining_unreviewed": counts["remaining_unreviewed"],
            "uniquely_anchored_collectibles": sum(
                row["acquisition_class"] == "uniquely_anchored_collectible" for row in selected),
            "repeated_material_rows": sum(
                row["acquisition_class"] == "repeated_material_row" for row in selected),
        }
    summary = {
        "schema_version": 1,
        "scope": "upgrade materials, flask upgrades, and DLC blessing collectibles",
        "policy": {
            "identity_region_trust": "two independent external source families",
            "repeated_material_rows": "require an exact flag/map-lot or unique landmark binding",
            "collectibles": "retain exact flag and map anchor; guide order alone does not prove access",
            "access": "reported separately and never inferred from identity or region",
        },
        "by_category": by_category,
        "totals": {
            "audited": len(rows),
            "trusted": sum(row["review_status"] == "trusted" for row in rows),
            "held": sum(row["review_status"] != "trusted" for row in rows),
            "conflicted": sum(row["review_status"] == "region_taxonomy_conflict" for row in rows),
            "remaining_unreviewed": sum(row["review_status"] == "remaining_unreviewed"
                                        for row in rows),
        },
    }
    return rows, summary


def render_tsv(rows: list[dict[str, str]]) -> str:
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
    table = render_tsv(rows)
    report = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not OUT_PATH.is_file() or OUT_PATH.read_text(encoding="utf-8") != table:
            raise SystemExit(f"STALE: {OUT_PATH.relative_to(ROOT)}")
        if not SUMMARY_PATH.is_file() or SUMMARY_PATH.read_text(encoding="utf-8") != report:
            raise SystemExit(f"STALE: {SUMMARY_PATH.relative_to(ROOT)}")
        print(f"upgrade/blessing review: OK -- {len(rows)} checks")
        return 0
    OUT_PATH.write_text(table, encoding="utf-8", newline="\n")
    SUMMARY_PATH.write_text(report, encoding="utf-8", newline="\n")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
