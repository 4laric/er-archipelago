#!/usr/bin/env python3
"""Validate immutable Fextralife item revisions and conservative AP bindings."""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield" / "evidence" / "wiki-audit"
MANIFEST = AUDIT / "fextralife-item-pages.tsv"
LEADS = AUDIT / "fextralife-item-check-leads.tsv"


def ap_item_name(location: str) -> str:
    value = location.split(" :: ", 1)[-1]
    value = re.sub(r"\s*\[f\d+\]\s*$", "", value)
    value = value.split(", may be sweep-granted", 1)[0]
    value = value.split(" - ", 1)[0]
    value = re.sub(r"^\[(?:Incantation|Sorcery)\]\s*", "", value)
    return value.strip()


def main() -> int:
    with MANIFEST.open(encoding="utf-8", newline="") as handle:
        pages = list(csv.DictReader(handle, delimiter="\t"))
    with LEADS.open(encoding="utf-8", newline="") as handle:
        leads = list(csv.DictReader(handle, delimiter="\t"))
    assert len(pages) >= 1300, "Fextralife item corpus unexpectedly collapsed"
    assert len(leads) == len(pages)
    sources = {}
    for row in pages:
        source = row["source_id"]
        assert source not in sources
        sources[source] = row
        assert source == f"wiki:fextralife:page-{row['page_id']}:revision-{row['revision_id']}"
        assert row["revision_url"].endswith("?oldid=" + row["revision_id"])
        assert row["canonical_url"] + "?oldid=" + row["revision_id"] == row["revision_url"]
        assert re.fullmatch(r"[0-9a-z]{40}", row["revision_sha1"])
        assert row["revision_timestamp"].endswith("Z")
        assert row["ap_item_name"]
        assert row["disposition"] == "lead_only"

    spec = importlib.util.spec_from_file_location(
        "_fextralife_check_data", ROOT / "greenfield" / "eldenring" / "data.py")
    mod = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)
    current = {str(ap_id): (region, ap_item_name(location))
               for region, checks in mod.LOCATIONS.items()
               for location, ap_id, _flag in checks}
    ids = [row["lead_id"] for row in leads]
    subjects = [row["subject_id"] for row in leads]
    assert ids == sorted(ids) and len(ids) == len(set(ids))
    assert len(subjects) == len(set(subjects))
    for row in leads:
        assert row["subject_kind"] == "check"
        assert row["claim_kind"] in {"identity", "identity_region"}
        assert row["subject_id"] in current and row["source_ids"] in sources
        assert row["independence_families"] == "gameplay-wiki:fextralife"
        assert row["disposition"] == "lead_only" and row["game_version"] == "unknown"
        value = json.loads(row["normalized_value"])
        region, item_name = current[row["subject_id"]]
        source = sources[row["source_ids"]]
        assert value["item_name"] == item_name == source["ap_item_name"]
        if row["claim_kind"] == "identity_region":
            assert value["region"] == region == source["ap_region"]
            assert source["template_fields"]
            assert "does not prove access" in row["limitations"]
        else:
            assert set(value) == {"item_name"}
            assert not source["ap_region"] and not source["template_fields"]
            assert "does not prove region" in row["limitations"]
        assert row["exact_citations"]
    print(f"Fextralife item leads: OK -- {len(pages)} immutable revisions, "
          f"{len(leads)} exact check bindings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
