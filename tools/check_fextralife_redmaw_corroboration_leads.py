#!/usr/bin/env python3
"""Validate the pinned Fextralife corroboration slice for Redmaw-only checks."""
from __future__ import annotations

import csv
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield/evidence/wiki-audit"
LEADS = AUDIT / "fextralife-redmaw-corroboration-check-leads.tsv"
EXPECTED_IDS = {
    7770016, 7770521, 7770568, 7770569, 7770570, 7770581,
    7770592, 7770616, 7770691, 7772048, 7772113,
}


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _norm(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def _locations() -> dict[int, tuple[str, str, int]]:
    path = ROOT / "greenfield/eldenring/data.py"
    spec = importlib.util.spec_from_file_location("_fextra_redmaw_data", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return {
        ap_id: (region, name, flag)
        for region, entries in module.LOCATIONS.items()
        for name, ap_id, flag in entries
    }


def main() -> int:
    rows = _rows(LEADS)
    assert len(rows) == len(EXPECTED_IDS)
    assert {int(row["subject_id"]) for row in rows} == EXPECTED_IDS
    assert len({row["lead_id"] for row in rows}) == len(rows)

    pages = {row["source_id"]: row for row in _rows(AUDIT / "fextralife-item-pages.tsv")}
    fextra_identity = {
        int(row["subject_id"]): row
        for row in _rows(AUDIT / "fextralife-item-check-leads.tsv")
        if row["claim_kind"] == "identity"
    }
    redmaw = {
        int(row["subject_id"])
        for row in _rows(AUDIT / "walkthrough-check-leads.tsv")
        if row["claim_kind"] == "identity_region"
        and "gameplay-guide:redmaw" in row["independence_families"].split(";")
    }
    locations = _locations()

    for row in rows:
        ap_id = int(row["subject_id"])
        value = json.loads(row["normalized_value"])
        region, name, flag = locations[ap_id]
        source = row["source_ids"]
        page = pages[source]
        prior = fextra_identity[ap_id]
        assert ap_id in redmaw, f"{ap_id}: no Redmaw identity_region witness"
        assert prior["source_ids"] == source
        assert page["revision_id"] in row["lead_id"]
        assert page["page_id"] in row["lead_id"]
        assert page["revision_sha1"] and len(page["revision_sha1"]) == 40
        assert row["claim_kind"] == "identity_region"
        assert row["independence_families"] == "gameplay-wiki:fextralife"
        assert row["disposition"] == "lead_only" and row["game_version"] == "unknown"
        assert value["item_name"] == json.loads(prior["normalized_value"])["item_name"]
        assert (value["region"], value["flag"]) == (region, flag)
        assert _norm(value["acquisition_anchor"]) in _norm(name)
        assert f"revision-{page['revision_id']}" in row["exact_citations"]
        assert f"project:check:{ap_id}/detection;flag-{flag}" in row["exact_citations"]
        assert "does not prove access" in row["limitations"]

    print(f"Fextralife/Redmaw corroboration: OK -- {len(rows)} exact identity/region leads")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
