#!/usr/bin/env python3
"""Validate PowerPyx regional walkthrough leads against current checks and source registry."""

from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield" / "evidence" / "wiki-audit"
LEADS = AUDIT / "powerpyx-check-leads.tsv"
HEADERS = (
    "lead_id", "subject_kind", "subject_id", "claim_kind", "normalized_value",
    "source_ids", "independence_families", "disposition", "game_version",
    "exact_citations", "summary", "limitations",
)


def main() -> int:
    with (AUDIT / "sources.tsv").open(encoding="utf-8", newline="") as fh:
        sources = {row["source_id"]: row for row in csv.DictReader(fh, delimiter="\t")}
    with LEADS.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        assert tuple(reader.fieldnames or ()) == HEADERS
        rows = list(reader)

    spec = importlib.util.spec_from_file_location(
        "_powerpyx_check_data", ROOT / "greenfield" / "eldenring" / "data.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    current = {str(ap_id): region for region, checks in mod.LOCATIONS.items()
               for _name, ap_id, _flag in checks}

    assert len(rows) >= 90, "PowerPyx coverage unexpectedly collapsed below the 93-check corpus"
    ids = [row["lead_id"] for row in rows]
    subjects = [row["subject_id"] for row in rows]
    assert ids == sorted(ids) and len(ids) == len(set(ids))
    assert len(subjects) == len(set(subjects))
    for row in rows:
        assert row["subject_kind"] == "check" and row["claim_kind"] == "identity_region"
        assert row["subject_id"] in current
        assert row["source_ids"] in sources
        assert sources[row["source_ids"]]["body_sha256"].startswith("sha256:")
        assert row["independence_families"] == "gameplay-guide:powerpyx"
        assert row["disposition"] == "lead_only" and row["game_version"] == "unknown"
        assert json.loads(row["normalized_value"])["region"] == current[row["subject_id"]]
        assert row["exact_citations"].startswith("powerpyx:#")
        assert ":block-" in row["exact_citations"] and ":sha256-" in row["exact_citations"]
        assert row["summary"] and row["limitations"]
    print(f"PowerPyx check leads: OK -- {len(rows)} exact check bindings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
