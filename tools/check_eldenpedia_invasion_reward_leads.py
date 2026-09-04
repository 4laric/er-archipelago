#!/usr/bin/env python3
"""Validate the complete Eldenpedia invasion-page inventory and safe direct-drop bindings."""
from __future__ import annotations

import csv
import importlib.util
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield/evidence/wiki-audit"
HEADERS = (
    "lead_id", "subject_kind", "subject_id", "claim_kind", "normalized_value",
    "source_ids", "independence_families", "disposition", "game_version",
    "exact_citations", "summary", "limitations",
)
EXPECTED_FLAGS = {
    "7770017": 60300,
    "7770039": 65270,
    "7771719": 16007940,
    "7772824": 1042377700,
    "7772844": 1042397700,
    "7773759": 400672,
    "7774254": 1039527700,
}


def main() -> int:
    with (AUDIT / "eldenpedia-invasion-reward-category.tsv").open(
            encoding="utf-8", newline="") as handle:
        inventory = list(csv.DictReader(handle, delimiter="\t"))
    assert len(inventory) == 24
    assert len({row["page_id"] for row in inventory}) == len(inventory)
    assert Counter(row["disposition"] for row in inventory) == {
        "bound": 6,
        "quest_or_multi_encounter": 9,
        "multi_encounter_region_ambiguous": 3,
        "not_a_direct_invasion_reward": 2,
        "set_alias_unresolved": 2,
        "blocked_tarnished_runtime": 2,
    }

    with (AUDIT / "eldenpedia-invasion-reward-check-leads.tsv").open(
            encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        assert tuple(reader.fieldnames or ()) == HEADERS
        leads = list(reader)
    assert len(leads) == 7
    assert len({row["lead_id"] for row in leads}) == len(leads)
    assert {row["subject_id"] for row in leads} == {
        "7770017", "7770039", "7771719", "7772824", "7772844", "7773759", "7774254",
    }

    spec = importlib.util.spec_from_file_location(
        "_invasion_reward_data", ROOT / "greenfield/eldenring/data.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    current = {str(ap_id): (region, name, flag) for region, checks in module.LOCATIONS.items()
               for name, ap_id, flag in checks}
    with (ROOT / "greenfield/flag_lots.tsv").open(encoding="utf-8", newline="") as handle:
        lot_flags = {int(row["flag"]) for row in csv.DictReader(handle, delimiter="\t")}
    with (AUDIT / "sources.tsv").open(encoding="utf-8", newline="") as handle:
        source_ids = {row["source_id"] for row in csv.DictReader(handle, delimiter="\t")}
    for row in leads:
        value = json.loads(row["normalized_value"])
        region, name, flag = current[row["subject_id"]]
        assert value["region"] == region
        assert value["item_name"] in name
        assert flag == EXPECTED_FLAGS[row["subject_id"]]
        assert flag in lot_flags
        assert row["source_ids"] in source_ids
        assert row["claim_kind"] == "identity_region"
        assert row["independence_families"] == "gameplay-wiki:eldenpedia"
        assert row["disposition"] == "lead_only" and row["game_version"] == "unknown"

    coverage = json.loads((AUDIT / "eldenpedia-invasion-reward-coverage.json").read_text())
    counts = dict(sorted(Counter(row["disposition"] for row in inventory).items()))
    assert coverage["category_pages"] == len(inventory)
    assert coverage["directly_bound_checks"] == len(leads)
    assert coverage["remaining_pages"] == len(inventory) - 6
    assert coverage["page_dispositions"] == counts
    assert coverage["trusted_checks_after_batch"] == 5
    assert coverage["held_checks_after_batch"] == 2
    assert coverage["conflicted_checks"] == 0
    print("Eldenpedia invasion rewards: OK -- 24 pages, 7 safe bindings, 18 review pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
