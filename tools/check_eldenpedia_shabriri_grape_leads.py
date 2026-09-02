#!/usr/bin/env python3
"""Validate the immutable Eldenpedia Shabriri Grape acquisition corpus."""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield" / "evidence" / "wiki-audit"
MANIFEST = AUDIT / "eldenpedia-shabriri-grape-pages.tsv"
LEADS = AUDIT / "eldenpedia-shabriri-grape-check-leads.tsv"
EXPECTED = {"7770896": 10007850, "7772713": 1039417200, "7770562": 400061}
SOURCE_AREAS = {"7770896": "Limgrave", "7772713": "Liurnia of the Lakes",
                "7770562": "Liunia of the Lakes"}


def main() -> int:
    with MANIFEST.open(encoding="utf-8", newline="") as handle:
        pages = list(csv.DictReader(handle, delimiter="\t"))
    with LEADS.open(encoding="utf-8", newline="") as handle:
        leads = list(csv.DictReader(handle, delimiter="\t"))
    assert len(pages) == 1 and len(leads) == 3
    page = pages[0]
    assert page["source_id"] == "wiki:eldenpedia:page-13775:revision-51506"
    assert page["revision_url"].endswith("oldid=51506")
    assert page["revision_sha1"] == "3cbde246b8fc0f5071784f614dbf948d9ab7f23c"
    assert page["acquisition_rows"] == "3" and page["disposition"] == "lead_only"

    spec = importlib.util.spec_from_file_location(
        "_eldenpedia_shabriri_check_data", ROOT / "greenfield" / "eldenring" / "data.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    current = {str(ap_id): (region, name, flag) for region, checks in module.LOCATIONS.items()
               for name, ap_id, flag in checks}
    assert {row["subject_id"] for row in leads} == set(EXPECTED)
    assert [row["lead_id"] for row in leads] == sorted(row["lead_id"] for row in leads)
    for row in leads:
        subject = row["subject_id"]
        assert subject in current and ":: Shabriri Grape -" in current[subject][1]
        assert current[subject][2] == EXPECTED[subject]
        assert row["subject_kind"] == "check" and row["claim_kind"] == "acquisition_identity"
        assert row["source_ids"] == page["source_id"]
        assert row["independence_families"] == "gameplay-wiki:eldenpedia"
        assert row["disposition"] == "lead_only" and row["game_version"] == "unknown"
        value = json.loads(row["normalized_value"])
        assert value["flag"] == EXPECTED[subject] and value["item_name"] == "Shabriri Grape"
        assert value["project_region"] == current[subject][0]
        assert value["source_area"] == SOURCE_AREAS[subject]
        assert bool(value["quest_context"]) == (subject == "7770562")
        assert re.fullmatch(r"eldenpedia:pageid-13775:revision-51506:#Acquisition:[1-3]",
                            row["exact_citations"])
        assert "does not prove v1.17" in row["limitations"]
    assert len({row["exact_citations"] for row in leads}) == 3
    assert json.loads(next(row["normalized_value"] for row in leads
                           if row["subject_id"] == "7770896"))["project_region"] == "Stormveil"
    print("Eldenpedia Shabriri Grape leads: OK -- 1 immutable revision, 3 exact check bindings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
