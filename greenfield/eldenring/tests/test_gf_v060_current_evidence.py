"""Repo-only deterministic adapter gate for the v0.6 current evidence census."""
import csv
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON


FOUND = find_repo_root(__file__)
RUNNING_FROM_REPO = FOUND is not None
REPO = Path(FOUND) if FOUND else None


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _load_adapter():
    assert REPO is not None
    tools = REPO / "tools"
    sys.path.insert(0, str(tools))
    path = tools / "build_v060_current_evidence.py"
    spec = importlib.util.spec_from_file_location("build_v060_current_evidence", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(RUNNING_FROM_REPO, REPO_ONLY_REASON)
class CurrentEvidenceAdapterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert REPO is not None
        cls.adapter = _load_adapter()
        cls.bundle = cls.adapter.build_records(REPO)

    def test_every_current_check_has_identity_and_region_claims(self):
        claims_by_subject: dict[str, set[str]] = {}
        for claim in self.bundle["claims"]:
            claims_by_subject.setdefault(claim["subject_id"], set()).add(claim["claim_kind"])
        self.assertEqual(len(claims_by_subject), self.bundle["diagnostics"]["locations"])
        self.assertEqual(
            [kinds for kinds in claims_by_subject.values() if kinds != {"identity", "region"}],
            [{"identity", "region", "access"}],
        )

    def test_stormhill_access_preserves_one_emevd_or_group(self):
        claim = next(row for row in self.bundle["claims"]
                     if row["claim_kind"] == "access")
        value = json.loads(claim["value"])
        self.assertEqual(value["type"], "any")
        self.assertEqual(
            {row["flag"] for row in value["conditions"]},
            {3708, 3709, 1041389414},
        )
        evidence_by_id = {row["evidence_id"]: row for row in self.bundle["evidence"]}
        source_by_id = {row["source_id"]: row for row in self.bundle["sources"]}
        rows = [evidence_by_id[eid] for eid in claim["evidence_ids"].split(",")]
        self.assertEqual(len(rows), 3)
        self.assertEqual(
            {source_by_id[row["source_id"]]["family_id"] for row in rows},
            {"game:emevd:m60_41_38_00:90005750"},
        )
        self.assertEqual((claim["status"], claim["risk"], claim["review_issue"]),
                         ("single_source", "critical", "#1226"))
        self.assertTrue(all("not independent detection evidence" in row["independence_notes"]
                            for row in rows))
        self.assertTrue(all("event=90005750" in row["citation"] and
                            "commonarg/WaitFor" in row["citation"] for row in rows))

    def test_two_transforms_of_one_family_do_not_corroborate(self):
        claim = next(
            claim for claim in self.bundle["claims"]
            if claim["claim_kind"] == "region" and "," in claim["evidence_ids"]
        )
        evidence_by_id = {row["evidence_id"]: row for row in self.bundle["evidence"]}
        source_by_id = {row["source_id"]: row for row in self.bundle["sources"]}
        rows = [evidence_by_id[eid] for eid in claim["evidence_ids"].split(",")]
        families = {source_by_id[row["source_id"]]["family_id"] for row in rows}
        self.assertEqual(families, {next(iter(families))})
        self.assertEqual(claim["status"], "single_source")
        self.assertTrue(any("Not independent" in row["independence_notes"] for row in rows))

    def test_identity_uses_the_first_class_flag_namespace(self):
        identities = [row for row in self.bundle["claims"]
                      if row["claim_kind"] == "identity"]
        self.assertTrue(identities)
        self.assertTrue(all(json.loads(row["value"])["namespace"] == "flag"
                            for row in identities))

    def test_checked_in_bundle_validates_and_is_byte_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first"
            second = Path(tmp) / "second"
            first_bundle = self.adapter.write_bundle(REPO, first)
            second_bundle = self.adapter.write_bundle(REPO, second)
            checked_in = REPO / "greenfield" / "evidence" / "v060-current"
            for name in (*self.adapter.evidence_ledger.HEADERS, "summary.json"):
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())
                self.assertEqual((first / name).read_bytes(), (checked_in / name).read_bytes())
            self.assertEqual(first_bundle["summary"], second_bundle["summary"])
            self.assertEqual(first_bundle["summary"],
                             self.adapter.evidence_ledger.summary(first))
            claims = _read_tsv(first / "claims.tsv")
            evidence = _read_tsv(first / "evidence.tsv")
            self.assertEqual(len(claims),
                             2 * self.bundle["diagnostics"]["locations"] + 1)
            self.assertGreaterEqual(len(evidence), len(claims))


if __name__ == "__main__":
    unittest.main()
