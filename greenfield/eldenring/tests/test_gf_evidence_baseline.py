"""The v0.6 evidence baseline must reject malformed and silently changed censuses."""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest


REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
TOOL = os.path.join(REPO, "tools", "check_evidence_baseline.py")
SPEC = importlib.util.spec_from_file_location("_check_evidence_baseline", TOOL)
baseline = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(baseline)


def _summary(**changes):
    statuses = {
        "proven": 1,
        "corroborated": 0,
        "single_source": 1,
        "conflicted": 1,
        "inferred": 0,
        "unverified": 1,
    }
    value = {
        "schema_version": 1,
        "claims_total": 4,
        "by_status": statuses,
        "by_kind": {
            "identity": {
                "proven": 1,
                "corroborated": 0,
                "single_source": 1,
                "conflicted": 0,
                "inferred": 0,
                "unverified": 0,
            },
            "region": {
                "proven": 0,
                "corroborated": 0,
                "single_source": 0,
                "conflicted": 1,
                "inferred": 0,
                "unverified": 1,
            },
        },
        "by_risk": {
            "critical": {status: 0 for status in baseline.STATUSES},
            "high": {
                "proven": 0,
                "corroborated": 0,
                "single_source": 0,
                "conflicted": 1,
                "inferred": 0,
                "unverified": 1,
            },
            "medium": {
                "proven": 1,
                "corroborated": 0,
                "single_source": 1,
                "conflicted": 0,
                "inferred": 0,
                "unverified": 0,
            },
            "low": {status: 0 for status in baseline.STATUSES},
        },
        "active_conflicts": ["check:region/3"],
        "content_hash": "a" * 64,
    }
    value.update(changes)
    return value


class EvidenceBaselineValidation(unittest.TestCase):
    def test_accepts_complete_consistent_summary(self):
        self.assertEqual(4, baseline.validate_summary(_summary())["claims_total"])

    def test_rejects_status_total_that_launders_a_missing_claim(self):
        value = _summary(claims_total=5)
        with self.assertRaisesRegex(baseline.BaselineError, "by_status sums to 4"):
            baseline.validate_summary(value)

    def test_rejects_kind_status_totals_that_disagree_with_the_global_view(self):
        value = _summary()
        value["by_kind"]["region"]["conflicted"] = 0
        value["by_kind"]["region"]["unverified"] = 2
        with self.assertRaisesRegex(baseline.BaselineError, "by_kind status totals"):
            baseline.validate_summary(value)

    def test_rejects_unknown_status_and_risk_vocabularies(self):
        value = _summary()
        value["by_status"]["probably"] = 0
        with self.assertRaisesRegex(baseline.BaselineError, "unknown=\\['probably'\\]"):
            baseline.validate_summary(value)

        value = _summary()
        value["by_risk"]["urgent"] = value["by_risk"].pop("critical")
        with self.assertRaisesRegex(baseline.BaselineError, "by_risk keys differ"):
            baseline.validate_summary(value)

    def test_conflict_counter_is_not_an_independent_claim(self):
        with self.assertRaisesRegex(baseline.BaselineError, "active_conflicts"):
            baseline.validate_summary(_summary(active_conflicts=[]))

    def test_compare_reports_every_changed_aggregate_and_hash(self):
        old = baseline.validate_summary(_summary())
        new_raw = _summary(content_hash="b" * 64)
        new_raw["by_status"]["conflicted"] = 0
        new_raw["by_status"]["proven"] = 2
        new_raw["by_kind"]["region"]["conflicted"] = 0
        new_raw["by_kind"]["region"]["proven"] = 1
        new_raw["by_risk"]["high"]["conflicted"] = 0
        new_raw["by_risk"]["high"]["proven"] = 1
        new_raw["active_conflicts"] = []
        new = baseline.validate_summary(new_raw)
        fields = [line.split(":", 1)[0] for line in baseline.compare(new, old)]
        self.assertEqual(
            ["by_status", "by_kind", "by_risk", "active_conflicts", "content_hash"], fields
        )

    def test_update_then_check_round_trip_is_byte_stable(self):
        with tempfile.TemporaryDirectory() as directory:
            current = os.path.join(directory, "current.json")
            reviewed = os.path.join(directory, "baseline.json")
            with open(current, "w", encoding="utf-8") as handle:
                json.dump(_summary(), handle)
            self.assertEqual(
                0,
                baseline.main(["--current", current, "--baseline", reviewed, "--update"]),
            )
            with open(reviewed, "rb") as handle:
                first = handle.read()
            self.assertEqual(0, baseline.main(["--current", current, "--baseline", reviewed]))
            self.assertEqual(
                0,
                baseline.main(["--current", current, "--baseline", reviewed, "--update"]),
            )
            with open(reviewed, "rb") as handle:
                self.assertEqual(first, handle.read())

    def test_canonical_claim_payload_hash_ignores_mapping_insertion_order(self):
        left = {"claims": [{"id": "a", "status": "proven"}], "schema_version": 1}
        right = {"schema_version": 1, "claims": [{"status": "proven", "id": "a"}]}
        self.assertEqual(baseline.summary_hash(left), baseline.summary_hash(right))


if __name__ == "__main__":
    unittest.main()
