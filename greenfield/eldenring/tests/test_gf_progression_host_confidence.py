"""Drift and semantic gates for generated external progression-host confidence."""
from __future__ import annotations

import csv
import importlib.util
import os
import unittest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    from _util import find_repo_root, REPO_ONLY_REASON

REPO = find_repo_root(__file__, marker="tools/build_progression_host_confidence.py")


def load_builder():
    path = os.path.join(REPO, "tools", "build_progression_host_confidence.py")
    spec = importlib.util.spec_from_file_location("host_confidence_builder", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


@unittest.skipIf(REPO is None, REPO_ONLY_REASON)
class ProgressionHostConfidenceTests(unittest.TestCase):
    def test_generated_classifier_is_current_and_conservative(self):
        builder = load_builder()
        status = builder.main(["--check"])
        self.assertIsInstance(status, int)
        self.assertGreaterEqual(status, 0)
        self.assertLess(status, 1)

    def test_every_check_is_classified_and_missing_evidence_is_hold(self):
        builder = load_builder()
        path = os.path.join(REPO, "greenfield", "evidence", "v060-current",
                            "progression_host_confidence.tsv")
        with open(path, encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(4_925, len(rows))
        self.assertEqual({builder.HOLD, builder.TRUSTED},
                         {row["confidence"] for row in rows})
        self.assertTrue(all(row["access_status"] == "unknown" for row in rows))
        self.assertTrue(all("does not prove access" in row["limitations"] for row in rows))
        self.assertTrue(all((int(row["external_family_count"]) >= 2) ==
                            (row["confidence"] == builder.TRUSTED) for row in rows))
        # The evidence passes, including the exact Redmaw/Eldenpedia and Fextralife/Redmaw
        # acquisition bindings, move hosts to trusted; overlapping evidence never double-counts.
        self.assertEqual(1_098, sum(row["confidence"] == builder.TRUSTED for row in rows))
        self.assertEqual(3_827, sum(row["confidence"] == builder.HOLD for row in rows))

    def test_generated_runtime_sets_partition_the_current_check_population(self):
        builder = load_builder()
        path = os.path.join(REPO, "greenfield", "eldenring", "evidence_progression_hosts.py")
        spec = importlib.util.spec_from_file_location("generated_host_confidence", path)
        generated = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(generated)
        held = generated.HOLD_PROGRESSION_HOST_APS
        trusted = generated.TRUSTED_PROGRESSION_HOST_APS
        current = set(builder.load_current_check_ids())
        self.assertTrue(trusted)
        self.assertTrue(held)
        self.assertTrue(trusted.isdisjoint(held))
        self.assertEqual(current, trusted | held)


if __name__ == "__main__":
    unittest.main()
