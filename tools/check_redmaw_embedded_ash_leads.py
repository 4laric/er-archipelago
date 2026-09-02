#!/usr/bin/env python3
"""Validate Redmaw base-weapon aliases against current AP names and map-lot flags."""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield/evidence/wiki-audit"
LEADS = AUDIT / "redmaw-embedded-ash-check-leads.tsv"
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
    builder = load("_redmaw_ash_check", ROOT / "tools/build_redmaw_embedded_ash_leads.py")
    base = load("_redmaw_ash_base_check", ROOT / "tools/build_walkthrough_check_leads.py")
    current = {str(ap_id): (region, flag, base.ap_item_name(location))
               for region, locations in base.load_locations().items()
               for location, ap_id, flag in locations}
    detections = {}
    with CLAIMS.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row["claim_kind"] == "detection" and row["active"] == "true":
                detections[row["subject_id"]] = json.loads(row["value"])
    assert len(rows) == 6
    assert [row["lead_id"] for row in rows] == sorted(row["lead_id"] for row in rows)
    assert len({row["subject_id"] for row in rows}) == len(rows)
    for row in rows:
        value = json.loads(row["normalized_value"])
        region, flag, item = current[row["subject_id"]]
        normalized = base.norm(item)
        assert builder.MARKER in normalized
        assert normalized.split(builder.MARKER, 1)[0] == base.norm(value["source_item_name"])
        assert (value["region"], value["flag"], value["ap_item_name"]) == (region, flag, item)
        assert detections[row["subject_id"]] == {"flag": flag, "mechanism": MAP_LOT}
        assert row["source_ids"] == builder.SOURCE_ID
        assert row["disposition"] == "lead_only" and row["claim_kind"] == "identity_region"
        assert "does not prove access" in row["limitations"]
    print("Redmaw embedded-Ash aliases: OK -- 6 exact weapon/map-lot bindings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
