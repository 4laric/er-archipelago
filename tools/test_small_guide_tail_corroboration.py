import csv
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield" / "evidence" / "wiki-audit"
PROMOTED = {7771149, 7771799, 7771812, 7772023, 7773207,
            7773236, 7773401, 7773603, 7774563}


class SmallGuideTailTests(unittest.TestCase):
    def test_promotions_are_exact_registered_identity_region_evidence(self):
        with (AUDIT / "small-guide-tail-corroboration-check-leads.tsv").open(
                encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        with (AUDIT / "sources.tsv").open(encoding="utf-8", newline="") as handle:
            sources = {row["source_id"] for row in csv.DictReader(handle, delimiter="\t")}
        for manifest in AUDIT.glob("*-pages.tsv"):
            with manifest.open(encoding="utf-8", newline="") as extra_handle:
                sources.update(row["source_id"] for row in csv.DictReader(extra_handle, delimiter="	"))
        self.assertEqual(PROMOTED, {int(row["subject_id"]) for row in rows})
        self.assertEqual(len(PROMOTED), len(rows))
        for row in rows:
            self.assertEqual("check", row["subject_kind"])
            self.assertEqual("identity_region", row["claim_kind"])
            self.assertEqual("lead_only", row["disposition"])
            self.assertEqual("unknown", row["game_version"])
            self.assertIn(row["source_ids"], sources)
            self.assertTrue(row["exact_citations"])
            value = json.loads(row["normalized_value"])
            self.assertEqual({"item_name", "location", "region"}, set(value))

    def test_promoted_and_blocked_partition_the_original_thirty_check_tail(self):
        report = json.loads((AUDIT / "small-guide-tail-coverage.json").read_text())
        blocked = {ap for ids in report["blocked"].values() for ap in ids}
        self.assertEqual(30, report["tail_total"])
        self.assertEqual(PROMOTED, set(report["promoted"]))
        self.assertEqual(21, len(blocked))
        self.assertFalse(PROMOTED & blocked)
        self.assertEqual(30, len(PROMOTED | blocked))

    def test_promotions_reach_two_external_families_but_access_stays_unknown(self):
        path = AUDIT.parent / "v060-current" / "progression_host_confidence.tsv"
        with path.open(encoding="utf-8", newline="") as handle:
            rows = {int(row["check_id"]): row for row in csv.DictReader(handle, delimiter="\t")}
        for ap_id in PROMOTED:
            self.assertEqual("trusted_identity_region", rows[ap_id]["confidence"])
            self.assertGreaterEqual(int(rows[ap_id]["external_family_count"]), 2)
            self.assertEqual("unknown", rows[ap_id]["access_status"])


if __name__ == "__main__":
    unittest.main()
