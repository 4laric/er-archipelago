#!/usr/bin/env python3
"""Repo-only integrity tests for the #1273 gameplay-wiki intake pilot."""
from __future__ import annotations

import csv
import importlib.util
import unittest
from pathlib import Path

REPO_ONLY_REASON = "wiki source registry and validator are repository evidence, not world files"


def find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "tools" / "check_wiki_audit.py").is_file():
            return candidate
    raise RuntimeError("repository root not found")


REPO = find_repo_root(Path(__file__).resolve())
SPEC = importlib.util.spec_from_file_location(
    "check_wiki_audit", REPO / "tools" / "check_wiki_audit.py")
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class WikiAuditTest(unittest.TestCase):
    def test_registry_and_normalized_leads_validate(self):
        self.assertEqual(AUDIT.validate(REPO), (2, 3))

    def test_lamenter_pilot_preserves_lead_only_scope(self):
        path = REPO / "greenfield" / "evidence" / "wiki-audit" / "leads.tsv"
        with path.open(encoding="utf-8", newline="") as handle:
            leads = {row["lead_id"]: row for row in csv.DictReader(handle, delimiter="\t")}
        self.assertEqual(leads["lamenters-gaol-upper-key-access"]["normalized_value"],
                         '{"type":"region_only"}')
        self.assertIn("Gaol Upper Level Key",
                      leads["lamenters-gaol-lower-key-access"]["normalized_value"])
        self.assertIn("Gaol Lower Level Key",
                      leads["lamenter-boss-access"]["normalized_value"])
        self.assertTrue(all(row["disposition"] == "lead_only" for row in leads.values()))
        self.assertTrue(all(row["game_version"] == "unknown" for row in leads.values()))


if __name__ == "__main__":
    unittest.main()
