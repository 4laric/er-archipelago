#!/usr/bin/env python3
"""Validate the immutable Eldenpedia Deathroot acquisition corpus."""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield" / "evidence" / "wiki-audit"
MANIFEST = AUDIT / "eldenpedia-deathroot-pages.tsv"
LEADS = AUDIT / "eldenpedia-deathroot-check-leads.tsv"


def main() -> int:
    with MANIFEST.open(encoding="utf-8", newline="") as handle:
        pages = list(csv.DictReader(handle, delimiter="\t"))
    with LEADS.open(encoding="utf-8", newline="") as handle:
        leads = list(csv.DictReader(handle, delimiter="\t"))
    assert len(pages) == 1 and len(leads) == 9
    page = pages[0]
    assert page["source_id"] == "wiki:eldenpedia:page-10213:revision-38369"
    assert page["revision_url"].endswith("oldid=38369")
    assert page["revision_sha1"] == "fbb08b39a5771a04b4be611d843434541801dfcf"
    assert page["acquisition_rows"] == "9" and page["disposition"] == "lead_only"

    spec = importlib.util.spec_from_file_location(
        "_eldenpedia_deathroot_check_data", ROOT / "greenfield" / "eldenring" / "data.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    current = {str(ap_id): (region, name) for region, checks in module.LOCATIONS.items()
               for name, ap_id, _flag in checks}
    subjects = [row["subject_id"] for row in leads]
    assert len(subjects) == len(set(subjects)) == 9
    assert [row["lead_id"] for row in leads] == sorted(row["lead_id"] for row in leads)
    for row in leads:
        assert row["subject_id"] in current and ":: Deathroot -" in current[row["subject_id"]][1]
        assert row["subject_kind"] == "check" and row["claim_kind"] == "acquisition_identity"
        assert row["source_ids"] == page["source_id"]
        assert row["independence_families"] == "gameplay-wiki:eldenpedia"
        assert row["disposition"] == "lead_only" and row["game_version"] == "unknown"
        value = json.loads(row["normalized_value"])
        assert value["item_name"] == "Deathroot"
        assert value["project_region"] == current[row["subject_id"]][0]
        assert re.fullmatch(r"eldenpedia:pageid-10213:revision-38369:#Acquisition:[1-9]",
                            row["exact_citations"])
        assert "does not prove v1.17" in row["limitations"]
    assert len({row["exact_citations"] for row in leads}) == 9
    print("Eldenpedia Deathroot leads: OK -- 1 immutable revision, 9 exact check bindings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
