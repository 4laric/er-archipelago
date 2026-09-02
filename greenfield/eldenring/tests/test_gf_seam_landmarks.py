#!/usr/bin/env python3
"""Cross-representation witnesses for adjudicated region-boundary landmarks (#1319)."""
from __future__ import annotations

import csv
import os
import unittest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON


REPO = find_repo_root(__file__, marker="greenfield/seam_landmarks.tsv")


@unittest.skipUnless(REPO is not None, REPO_ONLY_REASON)
class SeamLandmarkLedgerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from worlds.eldenring import boss_sweeps, data, region_graces, region_play_ids

        cls.boss_sweeps = boss_sweeps
        cls.data = data
        cls.region_graces = region_graces
        cls.region_play_ids = region_play_ids
        with open(os.path.join(REPO, "greenfield", "seam_landmarks.tsv"),
                  encoding="utf-8", newline="") as handle:
            cls.rows = list(csv.DictReader(handle, delimiter="\t"))

    def test_ledger_is_nonempty_and_provenanced(self):
        self.assertGreaterEqual(len(self.rows), 1)
        for row in self.rows:
            self.assertTrue(row["landmark"] and row["ruling_source"] and row["ruling_date"])
            self.assertTrue(row["operator"])
            self.assertEqual(row["not_applicable"], "none")

    def test_every_row_agrees_across_all_shipped_representations(self):
        by_check = {ap_id: region for region, entries in self.data.LOCATIONS.items()
                    for _name, ap_id, _flag in entries}
        self.assertGreater(len(by_check), 4_000, "location corpus disappeared; witness is vacuous")
        for row in self.rows:
            region = row["expected_region"]
            check_id = int(row["check_id"])
            trigger = int(row["sweep_trigger"])
            bucket = int(row["kick_bucket"])
            grace = int(row["grace_flag"])
            self.assertIn(check_id, by_check, f"{row['landmark']}: named check vanished")
            self.assertIn(trigger, self.boss_sweeps.DUNGEON_SWEEPS,
                          f"{row['landmark']}: named sweep vanished")
            self.assertIn(check_id, self.boss_sweeps.DUNGEON_SWEEPS[trigger])
            self.assertEqual(by_check[check_id], region, "check/tracker ownership disagrees")
            self.assertEqual(self.boss_sweeps.SWEEP_REGION[trigger], region)
            self.assertEqual(self.boss_sweeps.SWEEP_ARENA_REGION[trigger], region)
            self.assertIn(bucket, self.region_play_ids.REGION_PLAY_IDS[region])
            self.assertIn(grace, self.region_graces.REGION_GRACE_POINTS[region])
            for member in self.boss_sweeps.DUNGEON_SWEEPS[trigger]:
                self.assertEqual(by_check[member], region,
                                 f"sweep {trigger} member {member} crosses the seam")

    def test_intentional_splits_are_explicit_and_still_owned(self):
        for row in self.rows:
            bucket_text, region = row["intentional_split"].split(":", 1)
            bucket = int(bucket_text)
            self.assertIn(bucket, self.region_play_ids.REGION_PLAY_IDS[region])
            self.assertNotEqual(region, row["expected_region"])
            self.assertNotIn(bucket,
                             self.region_play_ids.REGION_PLAY_IDS[row["expected_region"]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
