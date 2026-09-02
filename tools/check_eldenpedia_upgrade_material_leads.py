#!/usr/bin/env python3
"""Validate upgrade-material acquisition anchors against current AP map-lot evidence."""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield/evidence/wiki-audit"
LEADS = AUDIT / "eldenpedia-upgrade-material-check-leads.tsv"
MANIFEST = AUDIT / "eldenpedia-upgrade-material-pages.tsv"
CLAIMS = ROOT / "greenfield/evidence/v060-current/claims.tsv"
MAP_LOT = "ItemLotParam_map.getItemFlagId"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    with LEADS.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    with MANIFEST.open(encoding="utf-8", newline="") as handle:
        sources = {row["source_id"]: row for row in csv.DictReader(handle, delimiter="\t")}
    data = load("_upgrade_check_data", ROOT / "greenfield/eldenring/data.py")
    builder = load("_upgrade_check_builder", ROOT / "tools/build_eldenpedia_upgrade_material_leads.py")
    current = {str(ap_id): (region, flag, builder.norm(builder.item_name(location)))
               for region, entries in data.LOCATIONS.items()
               for location, ap_id, flag in entries}
    detections = {}
    with CLAIMS.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row["claim_kind"] == "detection" and row["active"] == "true":
                detections[row["subject_id"]] = json.loads(row["value"])
    assert len(rows) >= 12, "upgrade-material coverage unexpectedly collapsed"
    assert [row["lead_id"] for row in rows] == sorted(row["lead_id"] for row in rows)
    assert len({row["subject_id"] for row in rows}) == len(rows)
    for row in rows:
        value = json.loads(row["normalized_value"])
        source = sources[row["source_ids"]]
        region, flag, item = current[row["subject_id"]]
        assert row["subject_kind"] == "check" and row["claim_kind"] == "identity_region"
        assert row["disposition"] == "lead_only" and row["game_version"] == "unknown"
        assert (value["region"], value["flag"], builder.norm(value["item_name"])) == (region, flag, item)
        assert builder.is_upgrade_material(value["item_name"])
        assert detections[row["subject_id"]] == {"flag": flag, "mechanism": MAP_LOT}
        assert source["title"] == value["item_name"]
        assert len(value["acquisition_anchor"].split()) >= 2
        assert "does not prove access" in row["limitations"] and "#Acquisition:" in row["exact_citations"]
    print(f"Eldenpedia upgrade materials: OK -- {len(rows)} exact anchor/map-lot bindings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
