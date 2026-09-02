#!/usr/bin/env python3
"""Validate immutable Redmaw checklist leads against the current AP check corpus."""

from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield" / "evidence" / "wiki-audit"
LEADS = AUDIT / "redmaw-checklist-check-leads.tsv"
REPORT = AUDIT / "redmaw-checklist-coverage.json"
HEADERS = (
    "lead_id", "subject_kind", "subject_id", "claim_kind", "normalized_value",
    "source_ids", "independence_families", "disposition", "game_version",
    "exact_citations", "summary", "limitations",
)


def main() -> int:
    with (AUDIT / "sources.tsv").open(encoding="utf-8", newline="") as handle:
        source_ids = {row["source_id"] for row in csv.DictReader(handle, delimiter="\t")}
    with LEADS.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        assert tuple(reader.fieldnames or ()) == HEADERS
        rows = list(reader)

    spec = importlib.util.spec_from_file_location(
        "_redmaw_checklist_data", ROOT / "greenfield" / "eldenring" / "data.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    current = {str(ap_id): name for locations in module.LOCATIONS.values()
               for name, ap_id, _flag in locations}

    lead_ids = [row["lead_id"] for row in rows]
    subjects = [row["subject_id"] for row in rows]
    assert lead_ids == sorted(lead_ids) and len(lead_ids) == len(set(lead_ids))
    assert len(subjects) == len(set(subjects)), "checklist emits at most one lead per AP check"
    assert len(rows) >= 1350, "Redmaw checklist coverage collapsed below the 1367-check pilot"
    for row in rows:
        assert row["subject_kind"] == "check" and row["claim_kind"] == "identity"
        assert row["subject_id"] in current
        assert row["source_ids"] in source_ids
        assert row["independence_families"] == "gameplay-guide:redmaw"
        assert row["disposition"] == "lead_only" and row["game_version"] == "unknown"
        value = json.loads(row["normalized_value"])
        assert set(value) == {"item_name", "wiki_url"} and value["item_name"]
        assert value["wiki_url"].startswith("https://eldenring.wiki.gg/wiki/")
        assert row["exact_citations"].startswith("redmaw-checklists:")
        assert ";wiki.gg:https://eldenring.wiki.gg/wiki/" in row["exact_citations"]
        assert "does not prove region" in row["limitations"]
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["labels"] == 3249
    assert report["exact_labels"] == 1857
    assert report["matched_checks"] == len(rows) == 1499
    assert report["duplicate_exact_labels"] == 358
    assert report["ambiguous_labels"] == 432
    assert report["unmatched_labels"] == 960
    assert sum(sheet["labels"] for sheet in report["by_sheet"].values()) == report["labels"]
    print(f"Redmaw checklist leads: OK -- {len(rows)} exact global check bindings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
