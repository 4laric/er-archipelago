#!/usr/bin/env python3
"""Build the complete repeated field-pickup review queue.

The family is deliberately mechanical: an item name must occur at least twice after checks with
special acquisition tags are removed. Rows are partitioned by the strongest committed join that
can distinguish them; repeated names alone are never evidence.
"""
from __future__ import annotations

import csv
from collections import Counter
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "greenfield/evidence/wiki-audit/generic-pickup-review.tsv"
REPORT = ROOT / "greenfield/evidence/wiki-audit/generic-pickup-review-coverage.json"
EXCLUDED_TAGS = frozenset({
    "Basin", "Boss", "Church", "Fragment", "GreatRune", "KeyItem", "Legendary",
    "MajorBoss", "Remembrance", "Revered", "Seedtree", "Shop",
})
MAP_LOT = "ItemLotParam_map.getItemFlagId"
FIELDS = (
    "check_id", "region", "item_name", "flag", "detection_mechanism", "map_tile",
    "route_anchor", "partition", "confidence", "external_family_count",
    "external_families", "review_reason",
)


def load(name: str, path: Path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def item_name(location: str) -> str:
    return location.split(" :: ", 1)[1].split(" - ", 1)[0]


def route_anchor(location: str) -> str:
    if " - " not in location:
        return ""
    tail = location.split(" - ", 1)[1]
    tail = tail.split(", may be sweep-granted", 1)[0]
    tail = re.sub(r"\s*\[f\d+\]\s*$", "", tail).strip()
    tail = re.sub(r"\s*\(\d+\)\s*$", "", tail).strip()
    tail = tail.replace("(region unconfirmed)", "").strip()
    if re.fullmatch(r"m\d\d(?:_\d\d){1,3}", tail):
        return ""
    return tail


def build() -> tuple[list[dict[str, str]], dict]:
    data = load("_generic_review_data", ROOT / "greenfield/eldenring/data.py")
    tags = load("_generic_review_tags", ROOT / "greenfield/eldenring/location_tags.py")
    candidates = []
    for region, locations in data.LOCATIONS.items():
        for location, ap_id, flag in locations:
            if EXCLUDED_TAGS.intersection(tags.LOCATION_TAGS.get(ap_id, ())):
                continue
            candidates.append((region, location, ap_id, flag, item_name(location)))
    frequencies = Counter(row[4] for row in candidates)
    family = [row for row in candidates if frequencies[row[4]] >= 2]

    claims = {}
    with (ROOT / "greenfield/evidence/v060-current/claims.tsv").open(
            encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row["active"] == "true" and row["claim_kind"] == "detection":
                value = json.loads(row["value"])
                claims[int(row["subject_id"])] = value.get("mechanism", "")
    confidence = {}
    with (ROOT / "greenfield/evidence/v060-current/progression_host_confidence.tsv").open(
            encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            confidence[int(row["check_id"])] = row

    anchors = Counter()
    tiles = Counter()
    prepared = []
    for region, location, ap_id, flag, item in family:
        anchor = route_anchor(location)
        match = re.search(r"\((m\d\d(?:_\d\d){1,3})\)", location.split(", may be sweep-granted", 1)[0])
        tile = match.group(1) if match else ""
        anchors[(region, item, anchor)] += 1
        tiles[(region, item, tile)] += 1
        prepared.append((region, ap_id, flag, item, anchor, tile))

    rows = []
    for region, ap_id, flag, item, anchor, tile in prepared:
        mechanism = claims.get(ap_id, "")
        if mechanism != MAP_LOT:
            partition = "non_map_lot"
            reason = "requires a mechanism-specific evidence join"
        elif anchor and anchors[(region, item, anchor)] == 1:
            partition = "exact_route_anchor"
            reason = "seek an independent source naming this exact route anchor and item"
        elif tile and tiles[(region, item, tile)] == 1:
            partition = "exact_map_tile"
            reason = "seek an independent source with map-level evidence for this item"
        else:
            partition = "ambiguous_map_lot"
            reason = "same-name candidates survive the committed anchor/tile joins; player ruling needed"
        conf = confidence[ap_id]
        rows.append({
            "check_id": str(ap_id), "region": region, "item_name": item, "flag": str(flag),
            "detection_mechanism": mechanism, "map_tile": tile, "route_anchor": anchor,
            "partition": partition, "confidence": conf["confidence"],
            "external_family_count": conf["external_family_count"],
            "external_families": conf["external_families"], "review_reason": reason,
        })
    rows.sort(key=lambda row: (row["confidence"] != "hold", row["partition"], row["region"],
                               row["item_name"], int(row["check_id"])))
    report = {
        "category": "repeated_generic_field_pickups_and_consumables",
        "definition": "item name occurs at least twice after special acquisition tags are excluded",
        "excluded_tags": sorted(EXCLUDED_TAGS),
        "checks_total": len(rows),
        "item_names": len({row["item_name"] for row in rows}),
        "by_confidence": dict(sorted(Counter(row["confidence"] for row in rows).items())),
        "by_external_family_count": dict(sorted(
            Counter(row["external_family_count"] for row in rows).items(), key=lambda pair: int(pair[0]))),
        "by_partition": dict(sorted(Counter(row["partition"] for row in rows).items())),
        "ambiguous_or_conflicted": sum(row["partition"] == "ambiguous_map_lot" for row in rows),
        "remaining_held": sum(row["confidence"] == "hold" for row in rows),
        "schema_version": 1,
    }
    return rows, report


def main() -> int:
    rows, report = build()
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
