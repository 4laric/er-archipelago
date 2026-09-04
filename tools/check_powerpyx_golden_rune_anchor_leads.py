#!/usr/bin/env python3
"""Validate the exact PowerPyx Golden Rune anchor batch against current map-lot claims."""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEADS = ROOT / "greenfield/evidence/wiki-audit/powerpyx-golden-rune-anchor-check-leads.tsv"
EXPECTED = {
    7770870: (10007580, "Golden Rune [5]", "Stormveil", "Gateside Chamber"),
    7772815: (1042367030, "Golden Rune [2]", "Limgrave", "Church of Elleh"),
    7772921: (1044357000, "Golden Rune [2]", "Limgrave", "Agheel Lake South"),
    7773177: (1052417000, "Golden Rune [8]", "Caelid", "Lenne's Rise"),
    7773178: (1052417010, "Golden Rune [6]", "Caelid", "Lenne's Rise"),
}


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def main() -> int:
    data = load("_golden_rune_data", ROOT / "greenfield/eldenring/data.py")
    current = {ap_id: (region, name, flag) for region, locations in data.LOCATIONS.items()
               for name, ap_id, flag in locations}
    with LEADS.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert {int(row["subject_id"]) for row in rows} == set(EXPECTED)
    for row in rows:
        ap_id = int(row["subject_id"])
        flag, item, region, anchor = EXPECTED[ap_id]
        actual_region, name, actual_flag = current[ap_id]
        value = json.loads(row["normalized_value"])
        assert (actual_region, actual_flag) == (region, flag)
        assert item in name and anchor.lower() in name.lower()
        assert value == {"acquisition_anchor": anchor, "flag": flag,
                         "item_name": item, "region": region}
        assert row["independence_families"] == "gameplay-guide:powerpyx"
        assert row["disposition"] == "lead_only" and row["game_version"] == "unknown"
    print(f"PowerPyx Golden Rune anchors: OK -- {len(rows)} exact map-lot bindings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
