"""Phase-1 evidence browser contract and deterministic offline artifact (#1212)."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import re
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILDER = None
spec = importlib.util.spec_from_file_location(
    "evidence_browser_builder", os.path.join(ROOT, "tools", "build_evidence_browser.py"))
BUILDER = importlib.util.module_from_spec(spec)
spec.loader.exec_module(BUILDER)


def payload(html: str) -> dict:
    match = re.search(
        r'<script id="evidence-payload" type="application/json">(.*?)</script>', html, re.S)
    if not match:
        raise AssertionError("offline page has no embedded evidence payload")
    return json.loads(match.group(1).replace("<\\/", "</"))


class FixtureContractTests(unittest.TestCase):
    def test_fixture_uses_normalized_headers_and_identity_values(self):
        tables = BUILDER.normalized_tables()
        self.assertEqual(set(tables), set(BUILDER.HEADERS))
        for table, rows in tables.items():
            if rows:
                self.assertEqual(tuple(rows[0]), BUILDER.HEADERS[table])

        data = BUILDER.load_fixture()
        for check in data["checks"]:
            identity = next(c for c in check["claims"] if c["claim_kind"] == "identity")
            self.assertEqual(set(identity["value"]), {"ap_id", "flag", "namespace", "id"})
            self.assertEqual(identity["value"]["ap_id"], check["check_id"])
            self.assertIn(identity["value"]["namespace"], {"item", "lot", "shop", "entity"})

    def test_fixture_has_exactly_identity_and_region_claims(self):
        data = BUILDER.load_fixture()
        self.assertGreaterEqual(len(data["checks"]), 2, "fixture must exercise more than one check")
        for check in data["checks"]:
            self.assertEqual({c["claim_kind"] for c in check["claims"]}, {"identity", "region"})

    def test_dependent_outputs_are_one_family_not_two_votes(self):
        data = BUILDER.load_fixture()
        claim = next(c for x in data["checks"] for c in x["claims"]
                     if c["claim_id"] == "check:7770100/identity")
        self.assertEqual(len(claim["evidence"]), 2, "witness: the dependent pair disappeared")
        self.assertEqual({e["family_id"] for e in claim["evidence"]},
                         {"game:param:ItemLotParam_map"})
        self.assertTrue(any("not an independent vote" in e["lineage"]
                            for e in claim["evidence"]))

    def test_transform_rejects_dangling_evidence_and_blank_citations(self):
        tables = copy.deepcopy(BUILDER.normalized_tables())
        tables["claims.tsv"][0]["evidence_ids"] += ",evidence:missing"
        with self.assertRaisesRegex(ValueError, "evidence_ids do not match"):
            BUILDER.transform(tables)

        tables = copy.deepcopy(BUILDER.normalized_tables())
        tables["evidence.tsv"][0]["citation"] = ""
        with self.assertRaisesRegex(ValueError, "exact citation"):
            BUILDER.transform(tables)


class OfflineArtifactTests(unittest.TestCase):
    def test_build_is_byte_deterministic_and_committed_page_is_current(self):
        first = BUILDER.build()
        second = BUILDER.build()
        self.assertEqual(first, second)
        with open(BUILDER.OUT_HTML, "rb") as fh:
            self.assertEqual(first, fh.read(),
                             "evidence browser is stale; run tools/build_evidence_browser.py")

    def test_stamp_is_fixture_content_hash_not_a_git_commit(self):
        contract = BUILDER.load_fixture()
        stamp = contract["inputs_hash"]
        self.assertEqual(stamp, BUILDER.fixture_hash())
        html = BUILDER.build().decode("utf-8")
        self.assertIn(f'<meta name="evidence-inputs-hash" content="{stamp}">', html)
        self.assertEqual(payload(html)["inputs_hash"], stamp)

    def test_page_exposes_facets_conflicts_citations_and_the_four_questions(self):
        html = BUILDER.build().decode("utf-8")
        for facet in ('id="status"', 'id="risk"', 'id="kind"', 'id="family"'):
            self.assertIn(facet, html)
        for question in (
            "1. Why is this check here?",
            "2. What says the player can reach and collect it?",
            "3. What disagrees with that answer?",
            "4. What evidence would graduate it?",
        ):
            self.assertIn(question, html)
        data = payload(html)
        claims = [c for x in data["checks"] for c in x["claims"]]
        conflicted = [c for c in claims if c["status"] == "conflicted"]
        self.assertTrue(conflicted, "witness: fixture no longer exercises an active conflict")
        self.assertTrue(any(e["stance"] == "contradicts" for c in conflicted for e in c["evidence"]))
        self.assertTrue(all(e["citation"].strip() for c in claims for e in c["evidence"]))
        self.assertIn("Conflict is active.", html)
        self.assertIn("Evidence by independent family", html)
        self.assertIn("No access evidence exists in Phase 1", html)
        self.assertIn("ownership is not proof that the player can reach or collect it", html)

    def test_permalink_serialises_every_facet_and_selected_claim(self):
        html = BUILDER.build().decode("utf-8")
        self.assertIn("new URLSearchParams(location.hash.slice(1))", html)
        self.assertIn("history.replaceState(null,'','#'+p.toString())", html)
        for key in ("q", "status", "risk", "kind", "family"):
            self.assertIn(f"'{key}'", html)
        self.assertIn("p.set('claim',selected)", html)
        self.assertIn("This permalink names a claim that is absent from this build.", html)

    def test_check_mode_detects_stale_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "page.html")
            with open(path, "wb") as fh:
                fh.write(b"stale")
            with open(path, "rb") as fh:
                stale = fh.read()
            self.assertNotEqual(stale, BUILDER.build(path))


if __name__ == "__main__":
    unittest.main()
