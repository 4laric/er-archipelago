"""AP-free coverage and drift gates for the v0.6 per-check access census (#1271)."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

try:
    from ._util import REPO_ONLY_REASON, find_repo_root
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _util import REPO_ONLY_REASON, find_repo_root

_FOUND = find_repo_root(str(Path(__file__).resolve()))
RUNNING_FROM_REPO = _FOUND is not None
ROOT = Path(_FOUND) if _FOUND else None
LEDGER = ROOT / "greenfield/evidence/v060-current" if ROOT else None
DISPOSITIONS = LEDGER / "access_dispositions.tsv" if LEDGER else None
SUMMARY = LEDGER / "access_dispositions_summary.json" if LEDGER else None
BASELINE = LEDGER / "access_dispositions_baseline.json" if LEDGER else None
access = None
if RUNNING_FROM_REPO:
    tools = ROOT / "tools"
    sys.path.insert(0, str(tools))
    spec = importlib.util.spec_from_file_location("access_dispositions", tools / "access_dispositions.py")
    access = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(access)


@unittest.skipUnless(RUNNING_FROM_REPO, REPO_ONLY_REASON)
class AccessDispositionTests(unittest.TestCase):
    def test_checked_in_schema_matches_the_validator_contract(self):
        schema = json.loads((ROOT / "greenfield/evidence/SCHEMA.json").read_text())
        self.assertEqual(schema["access_dispositions"]["fields"], list(access.HEADERS))
        self.assertEqual(
            schema["access_dispositions"]["values"], sorted(access.DISPOSITIONS)
        )

    def test_current_census_is_complete_with_encoded_key_gate_option_rows(self):
        value = access.summary(LEDGER, DISPOSITIONS)
        self.assertEqual(value["checks_total"], 4923)
        self.assertEqual(value["dispositions_total"], value["checks_total"] + 12)
        self.assertEqual(value["by_disposition"]["region_sufficient"], 3)
        self.assertEqual(value["by_disposition"]["encoded"], 12)
        self.assertEqual(value["by_disposition"]["unresolved"], value["checks_total"] - 3)
        self.assertEqual(value["by_risk"]["critical"]["region_sufficient"], 3)
        self.assertEqual(value["by_risk"]["critical"]["encoded"], 12)
        self.assertEqual(value["by_option_set"]["all"]["region_sufficient"], 3)
        self.assertEqual(
            value["by_option_set"][
                "item_shuffle=true,legacy_dungeon_keys=true,vanilla_placement=false"
            ]["encoded"],
            12,
        )
        self.assertEqual(
            value["by_option_set"][
                "not(item_shuffle=true,legacy_dungeon_keys=true,vanilla_placement=false)"
            ]["unresolved"],
            12,
        )
        self.assertEqual(value["release_blockers"], value["checks_total"] - 3)
        self.assertEqual(value["with_access_claim"], 36)
        self.assertEqual(value["without_access_claim"], 4899)

    def test_every_resolved_disposition_has_a_machine_checked_witness(self):
        rows = access.validate(LEDGER, DISPOSITIONS)
        resolved = [row for row in rows if row["disposition"] != "unresolved"]
        self.assertEqual(len(resolved), 15)
        self.assertTrue(all(row["implementation_path"] for row in resolved))
        self.assertTrue(all(row["implementation_symbol"].startswith("test_") for row in resolved))

    def test_resolved_disposition_rejects_missing_or_spoofed_witnesses(self):
        original = DISPOSITIONS.read_text()
        path_token = "greenfield/eldenring/tests/test_gf_features_smoke.py"
        symbol_token = "test_radahn_festival_flag_force_set"
        self.assertIn(path_token, original)
        self.assertIn(symbol_token, original)
        mutations = (
            (path_token, "../outside.py", "invalid implementation_path"),
            (
                f"\t{symbol_token}\n",
                "\ttest_symbol_that_does_not_exist\n",
                "implementation_symbol is absent",
            ),
        )
        for old, new, message in mutations:
            with self.subTest(new=new), tempfile.TemporaryDirectory() as td:
                path = Path(td) / "access_dispositions.tsv"
                path.write_text(original.replace(old, new, 1))
                with self.assertRaisesRegex(access.AccessDispositionError, message):
                    access.validate(LEDGER, path)

    def test_resolved_disposition_rejects_omitted_witness_fields(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "access_dispositions.tsv"
            lines = DISPOSITIONS.read_text().splitlines()
            index = next(i for i, line in enumerate(lines) if "region_sufficient" in line)
            fields = lines[index].split("\t")
            self.assertTrue(fields[9])
            lines[index] = "\t".join(fields[:7])
            path.write_text("\n".join(lines) + "\n")
            with self.assertRaisesRegex(access.AccessDispositionError, "implementation_path"):
                access.validate(LEDGER, path)

    def test_checked_in_summary_is_an_exact_drift_gate(self):
        generated = access.summary(LEDGER, DISPOSITIONS)
        committed = json.loads(SUMMARY.read_text())
        self.assertGreater(generated["checks_total"], 0)
        self.assertEqual(committed, generated)

    def test_current_census_does_not_regress_from_reviewed_baseline(self):
        current = access.ratchet_snapshot(LEDGER, DISPOSITIONS)
        baseline = json.loads(BASELINE.read_text())
        self.assertGreater(current["checks_total"], 0)
        self.assertEqual(access.compare_ratchet(current, baseline), [])

    def test_ratchet_rejects_more_blockers_or_lost_evidence(self):
        baseline = access.ratchet_snapshot(LEDGER, DISPOSITIONS)
        more_blockers = dict(baseline, release_blockers=baseline["release_blockers"] + 1)
        self.assertIn("release_blockers increased", access.compare_ratchet(more_blockers, baseline))
        lost = dict(baseline, linked_access_claim_ids=baseline["linked_access_claim_ids"][1:])
        errors = access.compare_ratchet(lost, baseline)
        self.assertTrue(any("evidence disappeared" in error for error in errors))

    def test_ratchet_protects_resolved_rows_but_allows_encoding_them(self):
        baseline = access.ratchet_snapshot(LEDGER, DISPOSITIONS)
        baseline["resolved_dispositions"] = {"7770008|all": "region_sufficient"}
        lost = dict(baseline, resolved_dispositions={})
        errors = access.compare_ratchet(lost, baseline)
        self.assertTrue(any("resolved disposition regressed" in error for error in errors))
        encoded = dict(
            baseline,
            resolved_dispositions={"7770008|all": "encoded"},
        )
        self.assertEqual(access.compare_ratchet(encoded, baseline), [])

    def test_one_unresolved_row_can_split_into_two_resolved_option_rows(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "access_dispositions.tsv"
            lines = DISPOSITIONS.read_text().splitlines()
            index = next(i for i, line in enumerate(lines) if "check:7770008/access" in line)
            fields = lines[index].split("\t")
            self.assertEqual(fields[2:5], ["unresolved", "critical", "all"])
            fields.extend([""] * (len(access.HEADERS) - len(fields)))
            fields[9] = "greenfield/eldenring/tests/test_gf_features_smoke.py"
            fields[10] = "test_radahn_festival_flag_force_set"
            first = fields[:]
            first[2:5] = ["region_sufficient", "critical", "festival_route"]
            second = fields[:]
            second[2:5] = ["region_sufficient", "critical", "quest_route"]
            lines[index:index + 1] = ["\t".join(first), "\t".join(second)]
            path.write_text("\n".join(lines) + "\n")
            baseline = access.ratchet_snapshot(LEDGER, DISPOSITIONS)
            current = access.ratchet_snapshot(LEDGER, path)
            self.assertEqual(current["release_blockers"], baseline["release_blockers"] - 1)
            self.assertEqual(access.compare_ratchet(current, baseline), [])

    def test_all_option_cannot_overlap_specific_option_rows(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "access_dispositions.tsv"
            lines = DISPOSITIONS.read_text().splitlines()
            index = next(i for i, line in enumerate(lines) if "check:7770008/access" in line)
            duplicate = lines[index].replace("\tall", "\tspecific_route", 1)
            lines.insert(index + 1, duplicate)
            path.write_text("\n".join(lines) + "\n")
            with self.assertRaisesRegex(access.AccessDispositionError, "cannot coexist"):
                access.validate(LEDGER, path)

    def test_missing_check_cannot_disappear_from_the_census(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "access_dispositions.tsv"
            lines = DISPOSITIONS.read_text().splitlines()
            self.assertGreater(len(lines), 2)
            path.write_text("\n".join(lines[:-1]) + "\n")
            with self.assertRaisesRegex(access.AccessDispositionError, "population differs"):
                access.validate(LEDGER, path)

    def test_existing_access_claim_must_be_linked_exactly(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "access_dispositions.tsv"
            text = DISPOSITIONS.read_text()
            self.assertIn("check:7770008/access", text)
            path.write_text(text.replace("check:7770008/access", ""))
            with self.assertRaisesRegex(access.AccessDispositionError, "access_claim_id"):
                access.validate(LEDGER, path)

    def test_waiver_requires_review_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "access_dispositions.tsv"
            lines = DISPOSITIONS.read_text().splitlines()
            fields = lines[1].split("\t")
            fields[2] = "waived"
            lines[1] = "\t".join(fields)
            path.write_text("\n".join(lines) + "\n")
            with self.assertRaisesRegex(access.AccessDispositionError, "review metadata"):
                access.validate(LEDGER, path)

    def test_bootstrap_defaults_every_check_to_unresolved(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "access_dispositions.tsv"
            access.bootstrap(LEDGER, path)
            rows = access.validate(LEDGER, path)
            self.assertEqual(len(rows), 4923)
            self.assertEqual({row["disposition"] for row in rows}, {"unresolved"})


if __name__ == "__main__":
    unittest.main()
