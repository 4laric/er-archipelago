"""AP-free contract tests for the v0.6 evidence ledger (world#1210)."""
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:  # package-relative under pytest; plain path when run directly
    from ._util import REPO_ONLY_REASON, find_repo_root
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _util import REPO_ONLY_REASON, find_repo_root

_FOUND = find_repo_root(str(Path(__file__).resolve()))
RUNNING_FROM_REPO = _FOUND is not None
ROOT = Path(_FOUND) if _FOUND else None
TOOL = ROOT / "tools" / "evidence_ledger.py" if ROOT else None
FIXTURE = (
    ROOT / "greenfield" / "evidence" / "fixtures" / "status_engine"
    if ROOT
    else None
)
ledger = None
if RUNNING_FROM_REPO:
    spec = importlib.util.spec_from_file_location("evidence_ledger", TOOL)
    ledger = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = ledger
    spec.loader.exec_module(ledger)

@unittest.skipUnless(RUNNING_FROM_REPO, REPO_ONLY_REASON)
class EvidenceLedgerTests(unittest.TestCase):
    def test_real_failure_shapes_derive_honest_statuses(self):
        result = ledger.validate(FIXTURE)
        self.assertEqual(result.statuses["check:100/region"], "single_source", "two outputs sharing one family are one witness")
        self.assertEqual(result.statuses["check:101/region"], "corroborated")
        self.assertEqual(result.statuses["check:102/region"], "conflicted")
        self.assertEqual(result.statuses["check:103/access"], "unverified")
        self.assertEqual(result.statuses["check:104/description"], "inferred")
        self.assertEqual(result.statuses["check:105/identity"], "proven")

    def test_summary_contract_is_deterministic_and_risk_rankable(self):
        first = ledger.summary(FIXTURE); second = ledger.summary(FIXTURE)
        self.assertEqual(first, second)
        self.assertEqual(set(first), {"schema_version", "claims_total", "by_status", "by_kind", "by_risk", "active_conflicts", "content_hash"})
        self.assertEqual(first["claims_total"], 6)
        self.assertEqual(first["active_conflicts"], ["check:102/region"])
        self.assertEqual(
            {k:v for k,v in first["by_kind"]["region"].items() if v},
            {"conflicted": 1, "corroborated": 1, "single_source": 1},
        )
        self.assertRegex(first["content_hash"], r"^[0-9a-f]{64}$")

    def test_checked_in_schema_matches_the_validator_contract(self):
        schema=json.loads((ROOT/"greenfield"/"evidence"/"SCHEMA.json").read_text())
        self.assertEqual(schema["schema_version"],1)
        self.assertEqual(schema["claim_kinds"],sorted(ledger.CLAIM_KINDS))
        self.assertEqual(schema["identity_namespaces"], sorted(ledger.IDENTITY_NAMESPACES))
        self.assertEqual(schema["statuses"],sorted(ledger.STATUSES))
        self.assertEqual({k:tuple(v) for k,v in schema["tables"].items()},ledger.HEADERS)

    def test_flag_is_a_first_class_identity_namespace(self):
        with tempfile.TemporaryDirectory() as td:
            dst = Path(td)
            shutil.copytree(FIXTURE, dst, dirs_exist_ok=True)
            old = '{"ap_id":105,"flag":400105,"id":50105,"namespace":"lot"}'
            new = '{"ap_id":105,"flag":400105,"id":400105,"namespace":"flag"}'
            for name in ("claims.tsv", "evidence.tsv"):
                path = dst / name
                path.write_text(path.read_text().replace(old, new))

            ledger.validate(dst)
            claim = next(
                row for row in ledger._rows(dst / "claims.tsv")
                if row["claim_id"] == "check:105/identity"
            )
            value = json.loads(claim["value"])
            self.assertEqual(value["namespace"], "flag")
            self.assertEqual(value["id"], value["flag"])

    def test_duplicate_active_claim_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            dst=Path(td); shutil.copytree(FIXTURE,dst,dirs_exist_ok=True)
            claims=dst/"claims.tsv"; lines=claims.read_text().splitlines(); row=lines[1].replace("check:100/region", "check:999/region", 1)
            claims.write_text("\n".join(sorted(lines[1:]+[row], key=lambda x:x.split("\t",1)[0],)) + "\n")
            # Restore the header after sorting data rows.
            claims.write_text(lines[0]+"\n"+claims.read_text())
            with self.assertRaisesRegex(ledger.LedgerError, "duplicate active claim"):
                ledger.validate(dst)

    def test_cli_reports_the_same_public_summary(self):
        out=subprocess.run([sys.executable, str(ROOT/"tools"/"validate_evidence_ledger.py"), str(FIXTURE)], text=True, capture_output=True)
        self.assertEqual(out.returncode,0,out.stdout+out.stderr)
        payload=json.loads(out.stdout.split("evidence ledger OK: ",1)[1])
        self.assertEqual(payload,ledger.summary(FIXTURE))

if __name__ == "__main__": unittest.main()
