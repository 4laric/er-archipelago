import csv
from io import StringIO
import unittest

import build_progression_host_confidence as subject


def evidence(families=(), leads=()):
    return {"families": set(families), "identity_region_lead_ids": set(leads)}


class ClassifierTests(unittest.TestCase):
    def test_missing_evidence_is_hold_not_exclude(self):
        row = subject.classify([1], {})[0]
        self.assertEqual((row["confidence"], row["access_status"]), (subject.HOLD, "unknown"))
        self.assertNotIn("exclude", row["confidence"])

    def test_one_family_is_hold(self):
        row = subject.classify([1], {1: evidence(["gameplay-wiki:a"], ["one"])})[0]
        self.assertEqual(row["confidence"], subject.HOLD)

    def test_two_declared_external_families_are_trusted_for_identity_region_only(self):
        row = subject.classify([1], {1: evidence(
            ["gameplay-wiki:a", "gameplay-guide:b"], ["second", "first"])})[0]
        self.assertEqual(row["confidence"], subject.TRUSTED)
        self.assertEqual(row["access_status"], "unknown")
        self.assertEqual(row["identity_region_lead_ids"], "first;second")
        self.assertIn("does not prove access", row["limitations"])

    def test_duplicate_family_does_not_inflate_confidence(self):
        row = subject.classify([1], {1: evidence(["gameplay-wiki:a"], ["one", "two"])})[0]
        self.assertEqual(row["external_family_count"], "1")
        self.assertEqual(row["confidence"], subject.HOLD)

    def test_render_is_stable_by_check_id(self):
        text = subject.render(subject.classify([3, 1, 2], {}))
        rows = list(csv.DictReader(StringIO(text), delimiter="\t"))
        self.assertEqual([row["check_id"] for row in rows], ["1", "2", "3"])


if __name__ == "__main__":
    unittest.main()
