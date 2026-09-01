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

    def test_current_census_is_complete_with_two_proven_radahn_checks(self):
        value = access.summary(LEDGER, DISPOSITIONS)
        self.assertEqual(value["checks_total"], 4923)
        self.assertEqual(value["dispositions_total"], value["checks_total"])
        self.assertEqual(value["by_disposition"]["region_sufficient"], 2)
        self.assertEqual(value["by_disposition"]["unresolved"], value["checks_total"] - 2)
        self.assertEqual(value["by_risk"]["critical"]["region_sufficient"], 2)
        self.assertEqual(value["by_option_set"]["all"]["region_sufficient"], 2)
        self.assertEqual(value["release_blockers"], value["checks_total"] - 2)
        self.assertEqual(value["with_access_claim"], 11)
        self.assertEqual(value["without_access_claim"], 4912)

    def test_checked_in_summary_is_an_exact_drift_gate(self):
        generated = access.summary(LEDGER, DISPOSITIONS)
        committed = json.loads(SUMMARY.read_text())
        self.assertGreater(generated["checks_total"], 0)
        self.assertEqual(committed, generated)

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
