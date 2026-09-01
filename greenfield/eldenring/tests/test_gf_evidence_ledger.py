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
LIVE_FIXTURE = (
    ROOT / "greenfield" / "evidence" / "fixtures" / "live_testimony"
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
    @staticmethod
    def _copy_status_fixture(directory):
        dst = Path(directory)
        shutil.copytree(FIXTURE, dst, dirs_exist_ok=True)
        return dst

    @staticmethod
    def _add_history_claim(
        directory, *, claim_id="history:100/region", subject_id="100",
        claim_kind="region", active="false", evidence_id="",
    ):
        value = '"""Limgrave"""' if claim_kind == "region" else '{"type":"unknown"}'
        row = "\t".join([
            claim_id, "check", subject_id, claim_kind, "1.16", value, "unverified",
            "high", "automatic", evidence_id, "2026-08-31", "#1238", active,
        ])
        path = Path(directory) / "claims.tsv"
        lines = path.read_text().splitlines()
        path.write_text(lines[0] + "\n" + "\n".join(sorted(lines[1:] + [row])) + "\n")

    @staticmethod
    def _link_successor(directory, predecessor):
        path = Path(directory) / "claims.tsv"
        lines = path.read_text().splitlines()
        lines = [
            line + "\t" + predecessor
            if line.startswith("check:100/region\t") else line
            for line in lines
        ]
        path.write_text("\n".join(lines) + "\n")

    @staticmethod
    def _copy_live_fixture(directory):
        dst = Path(directory)
        shutil.copytree(LIVE_FIXTURE, dst, dirs_exist_ok=True)
        return dst

    def test_reproducible_testimony_is_one_family_not_proof(self):
        result = ledger.validate(LIVE_FIXTURE)
        self.assertEqual(result.statuses["check:200/region"], "single_source")

    def test_testimony_source_version_must_match_its_environment(self):
        with tempfile.TemporaryDirectory() as td:
            dst = self._copy_live_fixture(td)
            sources = dst / "sources.tsv"
            sources.write_text(sources.read_text().replace("\t1.17\t2026-", "\t1.16\t2026-"))
            with self.assertRaisesRegex(ledger.LedgerError, "game_version must match"):
                ledger.validate(dst)

    def test_testimony_citation_names_the_exact_observation_revision(self):
        with tempfile.TemporaryDirectory() as td:
            dst = self._copy_live_fixture(td)
            evidence = dst / "evidence.tsv"
            evidence.write_text(evidence.read_text().replace("message msg-123", "message msg-1234"))
            with self.assertRaisesRegex(ledger.LedgerError, "citation must name source revision"):
                ledger.validate(dst)

    def test_unknown_client_build_keeps_testimony_as_a_lead(self):
        with tempfile.TemporaryDirectory() as td:
            dst = self._copy_live_fixture(td)
            environments = dst / "environments.tsv"
            environments.write_text(
                environments.read_text().replace("\tclient-sha-abc\t", "\tunknown\t")
            )
            claims = dst / "claims.tsv"
            claims.write_text(claims.read_text().replace("\tsingle_source\t", "\tunverified\t"))
            result = ledger.validate(dst)
            self.assertEqual(result.statuses["check:200/region"], "unverified")

    def test_source_kind_cannot_spoof_a_runtime_family(self):
        with tempfile.TemporaryDirectory() as td:
            dst = self._copy_live_fixture(td)
            sources = dst / "sources.tsv"
            sources.write_text(
                sources.read_text().replace(
                    "testimony:player:run-1", "game:runtime:env:run-1"
                )
            )
            with self.assertRaisesRegex(ledger.LedgerError, "does not match family_id"):
                ledger.validate(dst)

    def test_runtime_family_requires_a_referenced_environment(self):
        with tempfile.TemporaryDirectory() as td:
            dst = self._copy_live_fixture(td)
            sources = dst / "sources.tsv"
            text = sources.read_text()
            text = text.replace("live_testimony", "game_data")
            text = text.replace("testimony:player:run-1", "game:runtime:env:run-1")
            text = text.replace("\tprivate-evidence\tenv:run-1", "\tprivate-evidence")
            sources.write_text(text)
            with self.assertRaisesRegex(ledger.LedgerError, "needs a referenced environment"):
                ledger.validate(dst)

    def test_incomplete_runtime_probe_cannot_make_high_risk_claim_proven(self):
        claim = {
            "claim_id": "check:1/region", "value": '"Limgrave"',
            "game_version": "1.17", "adjudication": "automatic", "risk": "high",
        }
        evidence = [
            {"evidence_id": "runtime", "source_id": "runtime", "stance": "supports", "value": '"Limgrave"', "valid_from": "1.17", "valid_to": ""},
            {"evidence_id": "reference", "source_id": "reference", "stance": "supports", "value": '"Limgrave"', "valid_from": "1.17", "valid_to": ""},
        ]
        sources = {
            "runtime": {
                "source_kind": "game_data", "family_id": "game:runtime:env:run-1",
                "environment_id": "env:run-1", "game_version": "1.17",
                "source_id": "runtime",
            },
            "reference": {
                "source_kind": "external_reference", "family_id": "reference:wiki:revision",
                "environment_id": "", "game_version": "1.17", "source_id": "reference",
            },
        }
        environment = {key: "" for key in ledger.HEADERS["environments.tsv"]}
        environment["environment_id"] = "env:run-1"
        self.assertEqual(
            ledger.derive_status(
                claim, evidence, sources, {"env:run-1": environment}
            ),
            "single_source",
        )

    def test_reproducible_runtime_probe_and_independent_family_can_prove(self):
        claim = {
            "claim_id": "check:1/region", "value": '"Limgrave"',
            "game_version": "1.17", "adjudication": "automatic", "risk": "high",
        }
        evidence = [
            {"evidence_id": "runtime", "source_id": "runtime", "stance": "supports", "value": '"Limgrave"', "valid_from": "1.17", "valid_to": ""},
            {"evidence_id": "reference", "source_id": "reference", "stance": "supports", "value": '"Limgrave"', "valid_from": "1.17", "valid_to": ""},
        ]
        sources = {
            "runtime": {
                "source_kind": "game_data", "family_id": "game:runtime:env:run-1",
                "environment_id": "env:run-1", "game_version": "1.17",
                "source_id": "runtime",
            },
            "reference": {
                "source_kind": "external_reference", "family_id": "reference:wiki:revision",
                "environment_id": "", "game_version": "1.17", "source_id": "reference",
            },
        }
        environment = ledger._rows(LIVE_FIXTURE / "environments.tsv")[0]
        self.assertEqual(
            ledger.derive_status(
                claim, evidence, sources, {"env:run-1": environment}
            ),
            "proven",
        )

    def test_real_failure_shapes_derive_honest_statuses(self):
        result = ledger.validate(FIXTURE)
        self.assertEqual(result.statuses["check:100/region"], "single_source", "two outputs sharing one family are one witness")
        self.assertEqual(result.statuses["check:101/region"], "corroborated")
        self.assertEqual(result.statuses["check:102/region"], "conflicted")
        self.assertEqual(result.statuses["check:103/access"], "unverified")
        self.assertEqual(result.statuses["check:104/description"], "inferred")
        self.assertEqual(result.statuses["check:105/identity"], "proven")

    def test_same_family_opposite_assertions_do_not_create_conflict(self):
        with tempfile.TemporaryDirectory() as td:
            dst = self._copy_status_fixture(td)
            evidence = dst / "evidence.tsv"
            lines = evidence.read_text().splitlines()
            lines = [
                line.replace(
                    "\tsupports\t\"\"\"Limgrave\"\"\"\t",
                    "\tcontradicts\t\"\"\"Liurnia\"\"\"\t",
                    1,
                ) if line.startswith("evidence:b\t") else line
                for line in lines
            ]
            evidence.write_text("\n".join(lines) + "\n")
            claims = dst / "claims.tsv"
            lines = claims.read_text().splitlines()
            lines = [
                line.replace("\tsingle_source\thigh\t", "\tunverified\thigh\t")
                if line.startswith("check:100/region\t") else line
                for line in lines
            ]
            claims.write_text("\n".join(lines) + "\n")
            result = ledger.validate(dst)
            self.assertEqual(result.statuses["check:100/region"], "unverified")

    def test_incomplete_environment_contradiction_remains_a_lead(self):
        with tempfile.TemporaryDirectory() as td:
            dst = self._copy_live_fixture(td)
            environments = dst / "environments.tsv"
            environments.write_text(
                environments.read_text().replace("\tclient-sha-abc\t", "\tunknown\t")
            )
            evidence = dst / "evidence.tsv"
            text = evidence.read_text()
            text = text.replace("\tsupports\t\"\"\"Limgrave\"\"\"\t", "\tcontradicts\t\"\"\"Liurnia\"\"\"\t")
            evidence.write_text(text)
            claims = dst / "claims.tsv"
            claims.write_text(claims.read_text().replace("\tsingle_source\t", "\tunverified\t"))
            result = ledger.validate(dst)
            self.assertEqual(result.statuses["check:200/region"], "unverified")

    def test_out_of_version_direct_source_remains_a_lead(self):
        with tempfile.TemporaryDirectory() as td:
            dst = self._copy_status_fixture(td)
            sources = dst / "sources.tsv"
            lines = sources.read_text().splitlines()
            lines = [
                line.replace("\t1.17\t", "\t1.16\t", 1)
                if line.startswith("source:e\t") else line
                for line in lines
            ]
            sources.write_text("\n".join(lines) + "\n")
            claims = dst / "claims.tsv"
            lines = claims.read_text().splitlines()
            lines = [
                line.replace("\tproven\tmedium\t", "\tunverified\tmedium\t")
                if line.startswith("check:105/identity\t") else line
                for line in lines
            ]
            claims.write_text("\n".join(lines) + "\n")
            result = ledger.validate(dst)
            self.assertEqual(result.statuses["check:105/identity"], "unverified")

    def test_out_of_version_contradiction_does_not_create_conflict(self):
        with tempfile.TemporaryDirectory() as td:
            dst = self._copy_status_fixture(td)
            sources = dst / "sources.tsv"
            lines = sources.read_text().splitlines()
            lines = [
                line.replace("\t1.17\t", "\t1.16\t", 1)
                if line.startswith("source:d\t") else line
                for line in lines
            ]
            sources.write_text("\n".join(lines) + "\n")
            claims = dst / "claims.tsv"
            lines = claims.read_text().splitlines()
            lines = [
                line.replace("\tconflicted\thigh\t", "\tsingle_source\thigh\t")
                if line.startswith("check:102/region\t") else line
                for line in lines
            ]
            lines = [
                line.replace("\tcorroborated\thigh\t", "\tsingle_source\thigh\t")
                if line.startswith("check:101/region\t") else line
                for line in lines
            ]
            claims.write_text("\n".join(lines) + "\n")
            result = ledger.validate(dst)
            self.assertEqual(result.statuses["check:102/region"], "single_source")

    def test_reversed_evidence_version_interval_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            dst = self._copy_status_fixture(td)
            evidence = dst / "evidence.tsv"
            lines = evidence.read_text().splitlines()
            lines = [
                line.replace("\t1.17", "\t1.18\t1.17", 1)
                if line.startswith("evidence:a\t") else line
                for line in lines
            ]
            evidence.write_text("\n".join(lines) + "\n")
            with self.assertRaisesRegex(ledger.LedgerError, "valid_from is after valid_to"):
                ledger.validate(dst)

    def test_supersession_cannot_cross_subject_or_claim_kind(self):
        cases = (("999", "region"), ("100", "access"))
        for subject_id, claim_kind in cases:
            with self.subTest(subject_id=subject_id, claim_kind=claim_kind):
                with tempfile.TemporaryDirectory() as td:
                    dst = self._copy_status_fixture(td)
                    predecessor = f"history:{subject_id}/{claim_kind}"
                    self._add_history_claim(
                        dst, claim_id=predecessor, subject_id=subject_id,
                        claim_kind=claim_kind,
                    )
                    self._link_successor(dst, predecessor)
                    with self.assertRaisesRegex(
                        ledger.LedgerError, "supersedes a different claim identity"
                    ):
                        ledger.validate(dst)

    def test_superseded_predecessor_must_be_inactive(self):
        with tempfile.TemporaryDirectory() as td:
            dst = self._copy_status_fixture(td)
            predecessor = "history:100/region"
            self._add_history_claim(dst, claim_id=predecessor, active="true")
            self._link_successor(dst, predecessor)
            with self.assertRaisesRegex(
                ledger.LedgerError, "superseded predecessor must be inactive"
            ):
                ledger.validate(dst)

    def test_valid_cross_version_replacement_preserves_claim_identity(self):
        with tempfile.TemporaryDirectory() as td:
            dst = self._copy_status_fixture(td)
            predecessor = "history:100/region"
            self._add_history_claim(dst, claim_id=predecessor)
            self._link_successor(dst, predecessor)
            result = ledger.validate(dst)
            self.assertEqual(result.statuses["check:100/region"], "single_source")

    def test_inactive_history_and_evidence_do_not_change_active_summary(self):
        before = ledger.summary(FIXTURE)
        with tempfile.TemporaryDirectory() as td:
            dst = self._copy_status_fixture(td)
            self._add_history_claim(
                dst, claim_id="history:999/region", subject_id="999",
                evidence_id="evidence:history",
            )
            evidence = dst / "evidence.tsv"
            lines = evidence.read_text().splitlines()
            row = "\t".join([
                "evidence:history", "history:999/region", "source:a", "contradicts",
                '"""Liurnia"""', "data.py historical row 999", "historical adapter",
                "inactive history", "1.16",
            ])
            evidence.write_text(lines[0] + "\n" + "\n".join(sorted(lines[1:] + [row])) + "\n")
            after = ledger.summary(dst)
            self.assertEqual(after["by_status"], before["by_status"])
            self.assertEqual(after["content_hash"], before["content_hash"])

    def test_source_locators_reject_escape_and_unstable_url_shapes(self):
        invalid = (
            "../secret.tsv",
            "/etc/passwd",
            "C:\\Users\\player\\evidence.txt",
            "greenfield//data.py",
            "http://example.invalid/source",
            "https://user:password@example.invalid/source",
            "private:../secret",
        )
        for locator in invalid:
            with self.subTest(locator=locator):
                with self.assertRaises(ledger.LedgerError):
                    ledger._source_locator(locator, "fixture")

    def test_source_locators_accept_repo_https_and_private_evidence(self):
        valid = (
            "greenfield/evidence/source.tsv",
            "https://example.invalid/page?oldid=123#section",
            "private:discord-attachment-sha256",
        )
        for locator in valid:
            with self.subTest(locator=locator):
                ledger._source_locator(locator, "fixture")
                self.assertLessEqual(len(locator), ledger.LOCATOR_MAX)

    def test_traversing_source_path_cannot_validate(self):
        with tempfile.TemporaryDirectory() as td:
            dst = self._copy_status_fixture(td)
            sources = dst / "sources.tsv"
            sources.write_text(
                sources.read_text().replace(
                    "greenfield/eldenring/data.py", "../../outside/data.py", 1
                )
            )
            with self.assertRaisesRegex(ledger.LedgerError, "canonical relative POSIX"):
                ledger.validate(dst)

    def test_revision_and_citation_are_bounded_single_line_values(self):
        with self.assertRaisesRegex(ledger.LedgerError, "single-line"):
            ledger._bounded_single_line("x" * (ledger.REVISION_MAX + 1), "revision", ledger.REVISION_MAX)
        with self.assertRaisesRegex(ledger.LedgerError, "single-line"):
            ledger._bounded_single_line("row 1\nrow 2", "citation", ledger.CITATION_MAX)

    def test_malformed_live_artifact_manifests_are_rejected(self):
        digest = "sha256:" + "a" * 64
        valid = '{"screenshot":"' + digest + '"}'
        invalid = (
            "none",
            "{}",
            '{"screenshot":"sha256:abc"}',
            '{"../screenshot":"' + digest + '"}',
            '{"screenshot":"SHA256:' + "A" * 64 + '"}',
        )
        for manifest in invalid:
            with self.subTest(manifest=manifest):
                with tempfile.TemporaryDirectory() as td:
                    dst = self._copy_live_fixture(td)
                    environments = dst / "environments.tsv"
                    environments.write_text(
                        environments.read_text().replace(valid, manifest)
                    )
                    with self.assertRaises(ledger.LedgerError):
                        ledger.validate(dst)

    def test_missing_artifact_manifest_keeps_live_evidence_as_a_lead(self):
        digest = "sha256:" + "a" * 64
        manifest = '{"screenshot":"' + digest + '"}'
        with tempfile.TemporaryDirectory() as td:
            dst = self._copy_live_fixture(td)
            environments = dst / "environments.tsv"
            environments.write_text(environments.read_text().replace(manifest, ""))
            claims = dst / "claims.tsv"
            claims.write_text(claims.read_text().replace("\tsingle_source\t", "\tunverified\t"))
            result = ledger.validate(dst)
            self.assertEqual(result.statuses["check:200/region"], "unverified")

    def test_sha256_source_revision_must_be_exact(self):
        with tempfile.TemporaryDirectory() as td:
            dst = self._copy_status_fixture(td)
            sources = dst / "sources.tsv"
            sources.write_text(sources.read_text().replace("\tsha\t", "\tsha256:abc\t"))
            with self.assertRaisesRegex(ledger.LedgerError, "malformed SHA-256"):
                ledger.validate(dst)

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
        self.assertEqual(
            schema["family_source_kinds"],
            {key: sorted(value) for key, value in ledger.FAMILY_SOURCE_KINDS.items()},
        )
        self.assertEqual(schema["identity_namespaces"], sorted(ledger.IDENTITY_NAMESPACES))
        self.assertEqual(
            schema["live_testimony"]["exact_build_fields"],
            list(ledger.LIVE_EXACT_BUILD_FIELDS),
        )
        self.assertEqual(schema["statuses"],sorted(ledger.STATUSES))
        self.assertEqual(schema["version_policy"]["out_of_version_strength"], "lead")
        self.assertEqual(schema["family_disagreement_strength"], "lead")
        self.assertEqual(
            schema["claim_supersession"]["preserved_fields"],
            ["subject_kind", "subject_id", "claim_kind"],
        )
        self.assertEqual(
            schema["citation_contract"]["citation_max_chars"], ledger.CITATION_MAX
        )
        self.assertEqual(
            schema["citation_contract"]["revision_max_chars"], ledger.REVISION_MAX
        )
        self.assertEqual(
            schema["environment_artifacts"]["digest"], "lowercase sha256:<64 hex>"
        )
        self.assertEqual(
            schema["row_ids"]["grammar"],
            "[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}",
        )
        self.assertEqual(
            schema["typed_values"]["integers"],
            "exact JSON integers; booleans are forbidden",
        )
        self.assertEqual(schema["tsv_rows"]["surplus_cells"], "rejected")
        self.assertEqual({k:tuple(v) for k,v in schema["tables"].items()},ledger.HEADERS)

    def test_surplus_tsv_cells_are_rejected_by_the_shared_parser(self):
        for table, header in ledger.HEADERS.items():
            with self.subTest(table=table), tempfile.TemporaryDirectory() as td:
                path = Path(td) / table
                row = ["canonical:id"] + [""] * (len(header) - 1) + ["surplus"]
                self.assertEqual(len(row), len(header) + 1)
                path.write_text("\t".join(header) + "\n" + "\t".join(row) + "\n")
                with self.assertRaisesRegex(
                    ledger.LedgerError, "more columns than the header"
                ):
                    ledger._rows(path)

    def test_primary_row_ids_are_canonical_ascii_tokens(self):
        malformed = ("trailing-space ", "embedded space", "unicode-\u03b1", "control\x01")
        for table, header in ledger.HEADERS.items():
            for row_id in malformed:
                with self.subTest(table=table, row_id=repr(row_id)), tempfile.TemporaryDirectory() as td:
                    path = Path(td) / table
                    row = [row_id] + [""] * (len(header) - 1)
                    path.write_text("\t".join(header) + "\n" + "\t".join(row) + "\n")
                    self.assertTrue(row_id)
                    with self.assertRaisesRegex(ledger.LedgerError, "canonical ASCII token"):
                        ledger._rows(path)

    def test_noncanonical_json_value_is_rejected_before_hashing(self):
        with tempfile.TemporaryDirectory() as td:
            dst = self._copy_status_fixture(td)
            claims = dst / "claims.tsv"
            canonical = '{"ap_id":105,"flag":400105,"id":50105,"namespace":"lot"}'
            reordered = '{"namespace":"lot","id":50105,"flag":400105,"ap_id":105}'
            self.assertNotEqual(canonical, reordered)
            self.assertEqual(json.loads(canonical), json.loads(reordered))
            claims.write_text(claims.read_text().replace(canonical, reordered))

            with self.assertRaisesRegex(ledger.LedgerError, "canonical JSON"):
                ledger.validate(dst)

    def test_boolean_is_not_an_integer_identifier(self):
        with tempfile.TemporaryDirectory() as td:
            dst = self._copy_status_fixture(td)
            old = '{"ap_id":105,"flag":400105,"id":50105,"namespace":"lot"}'
            new = '{"ap_id":true,"flag":400105,"id":50105,"namespace":"lot"}'
            self.assertIs(type(json.loads(new)["ap_id"]), bool)
            for name in ("claims.tsv", "evidence.tsv"):
                path = dst / name
                path.write_text(path.read_text().replace(old, new))

            with self.assertRaisesRegex(ledger.LedgerError, "invalid identity value"):
                ledger.validate(dst)

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
