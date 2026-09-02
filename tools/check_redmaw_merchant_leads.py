#!/usr/bin/env python3
"""Validate contextual Redmaw merchant bindings."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield/evidence/wiki-audit"


def main() -> int:
    with (AUDIT / "redmaw-merchant-check-leads.tsv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    report = json.loads((AUDIT / "redmaw-merchant-coverage.json").read_text(encoding="utf-8"))
    with (AUDIT / "redmaw-merchant-wikigg-revisions.tsv").open(encoding="utf-8", newline="") as handle:
        revisions = {row["redmaw_url"]: row for row in csv.DictReader(handle, delimiter="\t")}
    assert len(revisions) == 96
    for url, revision in revisions.items():
        assert url.startswith("https://eldenring.wiki.gg/wiki/")
        assert revision["revision_url"].endswith("?oldid=" + revision["revision_id"])
        assert revision["page_id"].isdigit() and revision["revision_id"].isdigit()
        assert revision["revision_timestamp"].endswith("Z")
    assert len(rows) == report["resolved_checks"] == 141
    assert report["ambiguous_merchant_labels"] == 292
    assert report["refused_labels"] == 151
    assert len({row["lead_id"] for row in rows}) == len(rows)
    assert len({row["subject_id"] for row in rows}) == len(rows)
    for row in rows:
        assert row["claim_kind"] == "identity"
        assert row["source_ids"] == "wiki:redmaw:checklists:7281cb6f"
        assert row["independence_families"] == "gameplay-guide:redmaw"
        assert row["disposition"] == "lead_only" and row["game_version"] == "unknown"
        value = json.loads(row["normalized_value"])
        assert set(value) == {"ap_flag", "item_name", "merchant_anchor", "wiki_url"}
        assert isinstance(value["ap_flag"], int) and value["ap_flag"] > 0
        assert value["merchant_anchor"] and value["wiki_url"].startswith("https://eldenring.wiki.gg/wiki/")
        assert row["exact_citations"].endswith(
            ";wiki.gg:" + revisions[value["wiki_url"]]["revision_url"]
        )
        assert "does not independently prove AP's region" in row["limitations"]
    print(f"Redmaw merchant leads: OK -- {len(rows)} contextual bindings; 151 refused")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
