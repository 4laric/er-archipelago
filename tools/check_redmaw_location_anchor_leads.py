#!/usr/bin/env python3
"""Validate same-step Redmaw location-anchor bindings."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield/evidence/wiki-audit"


def main() -> int:
    with (AUDIT / "redmaw-location-anchor-check-leads.tsv").open(
            encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    report = json.loads((AUDIT / "redmaw-location-anchor-coverage.json").read_text())
    assert report == {"matched_checks": 27, "refused_location_match": 6,
                      "repeated_item_links": 33, "steps_with_named_location": 428}
    assert len(rows) == 27
    assert len({row["lead_id"] for row in rows}) == len(rows)
    assert len({row["subject_id"] for row in rows}) == len(rows)
    for row in rows:
        assert row["claim_kind"] == "identity_region"
        assert row["source_ids"] == "wiki:redmaw:walkthroughs:7281cb6f"
        assert row["independence_families"] == "gameplay-guide:redmaw"
        assert row["disposition"] == "lead_only" and row["game_version"] == "unknown"
        value = json.loads(row["normalized_value"])
        assert set(value) == {"flag", "item_name", "location_anchor", "region", "wiki_url"}
        assert isinstance(value["flag"], int) and value["location_anchor"]
        assert "project:check:" in row["exact_citations"]
        assert "/detection;flag-" in row["exact_citations"]
        assert "This does not prove access" in row["limitations"]
    print("Redmaw location-anchor leads: OK -- 27 repeated map-lot bindings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
