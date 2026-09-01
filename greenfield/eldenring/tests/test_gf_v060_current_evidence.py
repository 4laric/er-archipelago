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
        self.assertTrue(all({"identity", "region"}.issubset(kinds)
                            for kinds in claims_by_subject.values()))

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

    def test_map_lot_detection_has_exact_citations_and_one_family(self):
        detections = [row for row in self.bundle["claims"]
                      if row["claim_kind"] == "detection"]
        self.assertTrue(detections)
        self.assertEqual(len(detections), 4285)
        self.assertTrue(all(row["status"] == "single_source" for row in detections))
        evidence_by_id = {row["evidence_id"]: row for row in self.bundle["evidence"]}
        source_by_id = {row["source_id"]: row for row in self.bundle["sources"]}
        for claim in detections:
            rows = [evidence_by_id[eid] for eid in claim["evidence_ids"].split(",")]
            self.assertEqual(
                {source_by_id[row["source_id"]]["family_id"] for row in rows},
                {"game:param:ItemLotParam_map"},
            )
            self.assertTrue(all("table=map lot=" in row["citation"]
                                and " getItemFlagId=" in row["citation"]
                                for row in rows))

    def test_stormhill_access_preserves_one_emevd_or_group(self):
        claim = next(row for row in self.bundle["claims"]
                     if row["claim_id"] == "check:7770583/access")
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

    def test_perfect_order_access_is_one_exact_emevd_witness(self):
        claim = next(row for row in self.bundle["claims"]
                     if row["claim_id"] == "check:7770008/access")
        self.assertEqual(json.loads(claim["value"]), {"type": "flag", "flag": 11059206})
        evidence_by_id = {row["evidence_id"]: row for row in self.bundle["evidence"]}
        source_by_id = {row["source_id"]: row for row in self.bundle["sources"]}
        row = evidence_by_id[claim["evidence_ids"]]
        self.assertEqual(source_by_id[row["source_id"]]["family_id"],
                         "game:emevd:m11_05_00_00:90005750")
        self.assertEqual((claim["status"], claim["risk"], claim["review_issue"]),
                         ("single_source", "critical", "#1232"))
        self.assertIn("not independent detection evidence", row["independence_notes"])
        self.assertIn("greenfield/lot_gates.tsv:18", row["citation"])
        self.assertIn("event=90005750 commonarg/WaitFor", row["citation"])

    def test_death_prince_access_is_immediate_not_the_unknown_cone(self):
        claim = next(row for row in self.bundle["claims"]
                     if row["claim_id"] == "check:7770009/access")
        self.assertEqual(json.loads(claim["value"]), {"type": "flag", "flag": 4131})
        evidence_by_id = {row["evidence_id"]: row for row in self.bundle["evidence"]}
        source_by_id = {row["source_id"]: row for row in self.bundle["sources"]}
        row = evidence_by_id[claim["evidence_ids"]]
        self.assertEqual(source_by_id[row["source_id"]]["family_id"],
                         "game:emevd:m12_03_00_00:90005750")
        self.assertEqual((claim["status"], claim["risk"], claim["review_issue"]),
                         ("single_source", "critical", "#1237"))
        self.assertIn("not independent detection evidence", row["independence_notes"])
        self.assertIn("unknown group semantics", row["independence_notes"])
        self.assertIn("not the complete Fia quest chain", row["notes"])
        self.assertIn("greenfield/lot_gates.tsv:19", row["citation"])
        self.assertIn("event=90005750 commonarg/WaitFor", row["citation"])

    def test_varres_bouquet_access_is_only_the_immediate_vanilla_award_gate(self):
        claim = next(row for row in self.bundle["claims"]
                     if row["claim_id"] == "check:7770560/access")
        self.assertEqual(json.loads(claim["value"]), {"type": "flag", "flag": 12059166})
        evidence_by_id = {row["evidence_id"]: row for row in self.bundle["evidence"]}
        source_by_id = {row["source_id"]: row for row in self.bundle["sources"]}
        row = evidence_by_id[claim["evidence_ids"]]
        self.assertEqual(source_by_id[row["source_id"]]["family_id"],
                         "game:emevd:m12_05_00_00:90005750")
        self.assertEqual((claim["status"], claim["risk"], claim["review_issue"]),
                         ("single_source", "critical", "#1244"))
        self.assertIn("not independent detection evidence", row["independence_notes"])
        self.assertIn("correlated projections", row["independence_notes"])
        self.assertIn("not the complete Varre quest", row["notes"])
        self.assertIn("does not describe the Archipelago Mohg boss-sweep alternate", row["notes"])
        self.assertIn("greenfield/lot_gates.tsv:30", row["citation"])
        self.assertIn("event=90005750 commonarg/WaitFor", row["citation"])

    def test_taunters_tongue_access_does_not_guess_the_unlabeled_gate_meaning(self):
        claim = next(row for row in self.bundle["claims"]
                     if row["claim_id"] == "check:7770017/access")
        self.assertEqual(json.loads(claim["value"]), {"type": "flag", "flag": 11102180})
        evidence_by_id = {row["evidence_id"]: row for row in self.bundle["evidence"]}
        source_by_id = {row["source_id"]: row for row in self.bundle["sources"]}
        row = evidence_by_id[claim["evidence_ids"]]
        self.assertEqual(source_by_id[row["source_id"]]["family_id"],
                         "game:emevd:m11_10_00_00:90005792")
        self.assertEqual((claim["status"], claim["risk"], claim["review_issue"]),
                         ("single_source", "critical", "#1248"))
        self.assertIn("not independent detection evidence", row["independence_notes"])
        self.assertIn("correlated projection", row["independence_notes"])
        self.assertIn("assigns it no Alberich or Roundtable meaning", row["notes"])
        self.assertIn("greenfield/lot_gates.tsv:21", row["citation"])
        self.assertIn("event=90005792 commonarg/WaitFor", row["citation"])

    def test_purifying_tear_access_excludes_quest_and_sweep_inferences(self):
        claim = next(row for row in self.bundle["claims"]
                     if row["claim_id"] == "check:7770039/access")
        self.assertEqual(json.loads(claim["value"]), {"type": "flag", "flag": 1039522181})
        evidence_by_id = {row["evidence_id"]: row for row in self.bundle["evidence"]}
        source_by_id = {row["source_id"]: row for row in self.bundle["sources"]}
        row = evidence_by_id[claim["evidence_ids"]]
        self.assertEqual(source_by_id[row["source_id"]]["family_id"],
                         "game:emevd:m60_39_52_00:90005792")
        self.assertEqual((claim["status"], claim["risk"], claim["review_issue"]),
                         ("single_source", "critical", "#1253"))
        self.assertIn("not independent detection evidence", row["independence_notes"])
        self.assertIn("assigns it no Eleonora or broader quest meaning", row["notes"])
        self.assertIn("does not describe the Archipelago Sanguine Noble boss-sweep alternate",
                      row["notes"])
        self.assertIn("greenfield/lot_gates.tsv:22", row["citation"])
        self.assertIn("event=90005792 commonarg/WaitFor", row["citation"])

    def test_ijis_bell_bearing_access_excludes_quest_and_sweep_inferences(self):
        claim = next(row for row in self.bundle["claims"]
                     if row["claim_id"] == "check:7770585/access")
        self.assertEqual(json.loads(claim["value"]), {"type": "flag", "flag": 3768})
        evidence_by_id = {row["evidence_id"]: row for row in self.bundle["evidence"]}
        source_by_id = {row["source_id"]: row for row in self.bundle["sources"]}
        row = evidence_by_id[claim["evidence_ids"]]
        self.assertEqual(source_by_id[row["source_id"]]["family_id"],
                         "game:emevd:m60_34_49_00:90005750")
        self.assertEqual((claim["status"], claim["risk"], claim["review_issue"]),
                         ("single_source", "critical", "#1259"))
        self.assertIn("not independent detection evidence", row["independence_notes"])
        self.assertIn("correlated projections", row["independence_notes"])
        self.assertIn("does not prove Iji's death or the complete Ranni/Iji quest", row["notes"])
        self.assertIn("does not describe the Archipelago Royal Revenant boss-sweep alternate",
                      row["notes"])
        self.assertIn("greenfield/lot_gates.tsv:76", row["citation"])
        self.assertIn("event=90005750 commonarg/WaitFor", row["citation"])

    def test_frenzied_flame_seal_access_excludes_quest_and_sweep_inferences(self):
        claim = next(row for row in self.bundle["claims"]
                     if row["claim_id"] == "check:7770572/access")
        self.assertEqual(json.loads(claim["value"]), {"type": "flag", "flag": 35009211})
        evidence_by_id = {row["evidence_id"]: row for row in self.bundle["evidence"]}
        source_by_id = {row["source_id"]: row for row in self.bundle["sources"]}
        row = evidence_by_id[claim["evidence_ids"]]
        self.assertEqual(source_by_id[row["source_id"]]["family_id"],
                         "game:emevd:m35_00_00_00:90005750")
        self.assertEqual((claim["status"], claim["risk"], claim["review_issue"]),
                         ("single_source", "critical", "#1264"))
        self.assertIn("not independent detection evidence", row["independence_notes"])
        self.assertIn("correlated projections", row["independence_notes"])
        self.assertIn("does not prove the complete Hyetta or Frenzied Flame quest", row["notes"])
        self.assertIn("does not describe the Archipelago Mohg, the Omen boss-sweep alternate",
                      row["notes"])
        self.assertIn("greenfield/lot_gates.tsv:42", row["citation"])
        self.assertIn("event=90005750 commonarg/WaitFor", row["citation"])

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
            self.assertEqual(len(claims), len(self.bundle["claims"]))
            self.assertGreaterEqual(len(evidence), len(claims))


if __name__ == "__main__":
    unittest.main()
