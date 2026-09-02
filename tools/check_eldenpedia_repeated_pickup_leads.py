#!/usr/bin/env python3
"""Validate exact repeated-pickup bindings against current AP and pinned wiki revisions."""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield" / "evidence" / "wiki-audit"
LEADS = AUDIT / "eldenpedia-repeated-pickup-check-leads.tsv"
MANIFEST = AUDIT / "eldenpedia-location-pages.tsv"
CLAIMS = ROOT / "greenfield" / "evidence" / "v060-current" / "claims.tsv"
MAP_LOT = "ItemLotParam_map.getItemFlagId"


def main() -> int:
    with LEADS.open(encoding="utf-8", newline="") as handle:
        leads = list(csv.DictReader(handle, delimiter="\t"))
    with MANIFEST.open(encoding="utf-8", newline="") as handle:
        sources = {row["source_id"]: row for row in csv.DictReader(handle, delimiter="\t")}
    detections = {}
    with CLAIMS.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row["claim_kind"] == "detection" and row["active"] == "true":
                value = json.loads(row["value"])
                if isinstance(value, dict) and "flag" in value and "mechanism" in value:
                    detections[row["subject_id"]] = value
    spec = importlib.util.spec_from_file_location(
        "_repeated_pickup_data", ROOT / "greenfield" / "eldenring" / "data.py")
    mod = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)
    current = {str(ap_id): (region, flag) for region, checks in mod.LOCATIONS.items()
               for _location, ap_id, flag in checks}
    assert len(leads) >= 110, "repeated-pickup coverage unexpectedly collapsed"
    ids = [row["lead_id"] for row in leads]
    subjects = [row["subject_id"] for row in leads]
    assert ids == sorted(ids) and len(ids) == len(set(ids))
    assert len(subjects) == len(set(subjects))
    for row in leads:
        assert row["subject_kind"] == "check" and row["claim_kind"] == "identity_region"
        assert row["source_ids"] in sources
        assert row["independence_families"] == "gameplay-wiki:eldenpedia"
        assert row["disposition"] == "lead_only" and row["game_version"] == "unknown"
        value = json.loads(row["normalized_value"])
        assert row["subject_id"] in current
        assert (value["region"], value["flag"]) == current[row["subject_id"]]
        detection = detections[row["subject_id"]]
        assert (detection["flag"], detection["mechanism"]) == (value["flag"], MAP_LOT)
        assert value["location_page"] == sources[row["source_ids"]]["title"]
        assert "does not prove access" in row["limitations"]
        assert "#Notable_Loot:" in row["exact_citations"]
    print(f"Eldenpedia repeated pickups: OK -- {len(leads)} exact map-lot bindings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
