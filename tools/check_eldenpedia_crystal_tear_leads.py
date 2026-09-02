#!/usr/bin/env python3
"""Validate the immutable Eldenpedia Crystal Tear acquisition corpus."""
import csv
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield" / "evidence" / "wiki-audit"


def main() -> int:
    with (AUDIT / "eldenpedia-crystal-tear-pages.tsv").open(encoding="utf-8", newline="") as handle:
        pages = list(csv.DictReader(handle, delimiter="\t"))
    with (AUDIT / "eldenpedia-crystal-tear-check-leads.tsv").open(encoding="utf-8", newline="") as handle:
        leads = list(csv.DictReader(handle, delimiter="\t"))
    assert len(pages) == 15 and len(leads) == 18
    assert all(row["source_id"].startswith("wiki:eldenpedia:page-") for row in pages)
    assert all(row["disposition"] == "lead_only" for row in pages + leads)
    spec = importlib.util.spec_from_file_location("_crystal_tear_check_data", ROOT / "greenfield" / "eldenring" / "data.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    current = {str(ap_id): (name, flag) for checks in module.LOCATIONS.values()
               for name, ap_id, flag in checks}
    assert [row["lead_id"] for row in leads] == sorted(row["lead_id"] for row in leads)
    for row in leads:
        value = json.loads(row["normalized_value"])
        assert row["subject_kind"] == "check" and row["claim_kind"] == "acquisition_identity"
        assert row["game_version"] == "unknown" and row["independence_families"] == "gameplay-wiki:eldenpedia"
        assert value["item_name"] in current[row["subject_id"]][0]
        assert value["flag"] == current[row["subject_id"]][1]
        assert "does not prove v1.17" in row["limitations"]
    assert len({row["subject_id"] for row in leads}) == 18
    print("Eldenpedia Crystal Tear leads: OK -- 15 immutable revisions, 18 exact check bindings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
