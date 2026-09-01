#!/usr/bin/env python3
"""Validate immutable Eldenpedia location-page metadata and conservative check bindings."""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield" / "evidence" / "wiki-audit"
MANIFEST = AUDIT / "eldenpedia-location-pages.tsv"
LEADS = AUDIT / "eldenpedia-location-check-leads.tsv"


def main() -> int:
    with MANIFEST.open(encoding="utf-8", newline="") as handle:
        pages = list(csv.DictReader(handle, delimiter="\t"))
    with LEADS.open(encoding="utf-8", newline="") as handle:
        leads = list(csv.DictReader(handle, delimiter="\t"))
    assert len(pages) >= 340, "Eldenpedia location corpus unexpectedly collapsed"
    assert len(leads) >= 315, "exact Eldenpedia check coverage unexpectedly collapsed"
    sources = {}
    for row in pages:
        source = row["source_id"]
        assert source not in sources, f"duplicate page source {source}"
        sources[source] = row
        assert source == (f"wiki:eldenpedia:page-{row['page_id']}:"
                          f"revision-{row['revision_id']}")
        assert row["revision_url"] == ("https://eldenring.wiki.gg/w/index.php?oldid=" +
                                       row["revision_id"])
        assert re.fullmatch(r"[0-9a-z]{40}", row["revision_sha1"])
        assert row["revision_timestamp"].endswith("Z")
        assert row["disposition"] == "lead_only"

    spec = importlib.util.spec_from_file_location(
        "_eldenpedia_check_data", ROOT / "greenfield" / "eldenring" / "data.py")
    mod = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)
    current = {str(ap_id): (region, name) for region, checks in mod.LOCATIONS.items()
               for name, ap_id, _flag in checks}
    subjects = [row["subject_id"] for row in leads]
    lead_ids = [row["lead_id"] for row in leads]
    assert lead_ids == sorted(lead_ids) and len(lead_ids) == len(set(lead_ids))
    assert len(subjects) == len(set(subjects)), "one check may not bind to multiple location pages"
    for row in leads:
        assert row["subject_kind"] == "check" and row["claim_kind"] == "identity_region"
        assert row["subject_id"] in current
        assert row["source_ids"] in sources
        assert row["independence_families"] == "gameplay-wiki:eldenpedia"
        assert row["disposition"] == "lead_only" and row["game_version"] == "unknown"
        value = json.loads(row["normalized_value"])
        assert value["region"] == current[row["subject_id"]][0]
        source = sources[row["source_ids"]]
        citation = (f"eldenpedia:pageid-{source['page_id']}:"
                    f"revision-{source['revision_id']}:#Notable_Loot:{value['item_name']}")
        assert row["exact_citations"] == citation
        assert "does not prove access" in row["limitations"]
    print(f"Eldenpedia location leads: OK -- {len(pages)} immutable page revisions, "
          f"{len(leads)} exact check bindings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
