#!/usr/bin/env python3
"""Validate the immutable, deliberately partial Seedbed Curse acquisition corpus."""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield" / "evidence" / "wiki-audit"
MANIFEST = AUDIT / "eldenpedia-seedbed-curse-pages.tsv"
LEADS = AUDIT / "eldenpedia-seedbed-curse-check-leads.tsv"
EXPECTED = {"7770596": 400308, "7771716": 16007700}


def main() -> int:
    with MANIFEST.open(encoding="utf-8", newline="") as handle:
        pages = list(csv.DictReader(handle, delimiter="\t"))
    with LEADS.open(encoding="utf-8", newline="") as handle:
        leads = list(csv.DictReader(handle, delimiter="\t"))
    assert len(pages) == 1 and len(leads) == 6
    page = pages[0]
    assert page["source_id"] == "wiki:eldenpedia:page-3879:revision-100628"
    assert page["revision_sha1"] == "2472387a6d4b9b62f475bae74e1ef9b539e7d21a"
    assert page["acquisition_rows"] == "6" and page["disposition"] == "lead_only"
    spec = importlib.util.spec_from_file_location(
        "_eldenpedia_seedbed_check_data", ROOT / "greenfield" / "eldenring" / "data.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    current = {str(ap_id): (name, flag) for checks in module.LOCATIONS.values()
               for name, ap_id, flag in checks if ":: Seedbed Curse -" in name}
    assert len(current) == 6
    with (ROOT / "greenfield" / "flag_lots.tsv").open(encoding="utf-8", newline="") as handle:
        lots = {(row["flag"], row["name"]) for row in csv.DictReader(handle, delimiter="\t")}
    matched = [row for row in leads if row["subject_kind"] == "check"]
    refused = [row for row in leads if row["subject_kind"] == "acquisition_row"]
    assert {row["subject_id"] for row in matched} == set(EXPECTED)
    assert len(refused) == 4 and len({row["subject_id"] for row in refused}) == 4
    assert [row["lead_id"] for row in leads] == sorted(row["lead_id"] for row in leads)
    for row in leads:
        assert row["claim_kind"] == "acquisition_identity"
        assert row["source_ids"] == page["source_id"]
        assert row["independence_families"] == "gameplay-wiki:eldenpedia"
        assert row["disposition"] == "lead_only" and row["game_version"] == "unknown"
        assert re.fullmatch(r"eldenpedia:pageid-3879:revision-100628:#Acquisition:[1-6]",
                            row["exact_citations"])
        value = json.loads(row["normalized_value"])
        assert value["item_name"] == "Seedbed Curse"
        if row in matched:
            assert value["flag"] == EXPECTED[row["subject_id"]]
            assert current[row["subject_id"]][1] == EXPECTED[row["subject_id"]]
            assert (str(value["flag"]), "Seedbed Curse") in lots
            assert "refusal_reason" not in value
        else:
            assert value["refusal_reason"] == (
                "same-region duplicate lacks a stable source-to-flag join")
        assert "does not prove v1.17" in row["limitations"]
    assert len({row["exact_citations"] for row in leads}) == 6
    boggart = json.loads(next(row["normalized_value"] for row in matched
                              if row["subject_id"] == "7770596"))
    assert boggart["game_data_anchor"] == (
        "questline_conditions:400308:lot-113010:BOSS_KILL-4143")
    print("Eldenpedia Seedbed Curse leads: OK -- 2 exact bindings, 4 explicit refusals")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
