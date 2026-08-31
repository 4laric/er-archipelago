"""Pin the evidence-backed part of #527's Rauh Base / Ancient Ruins boundary.

Only f2046467010 is settled by the committed point-in-volume corpus. The other
rows in #527 are nearest-grace leads, not verdicts, and deliberately do not
appear here.
"""
import csv
import os
import sys
import unittest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = find_repo_root(HERE)
IN_REPO = REPO is not None

FLAG = 2046467010
REGION = "Ancient Ruins"
PLAY_BUCKET = "69400"


class RauhBoundaryProvenRow(unittest.TestCase):
    def test_generated_location_uses_the_measured_region(self):
        from .. import data

        rows = [(region, name, ap) for region, locations in data.LOCATIONS.items()
                for name, ap, flag in locations if flag == FLAG]
        self.assertTrue(rows, "f%d is no longer a generated location" % FLAG)
        for region, name, _ap in rows:
            self.assertEqual(region, REGION)
            self.assertTrue(name.startswith(REGION + " ::"), name)

    @unittest.skipUnless(IN_REPO, REPO_ONLY_REASON)
    def test_point_in_volume_evidence_still_says_ancient_ruins(self):
        path = os.path.join(REPO, "greenfield", "item_play_regions.tsv")
        with open(path, encoding="utf-8", newline="") as fh:
            lines = (line for line in fh if not line.startswith("#"))
            rows = [row for row in csv.DictReader(lines, delimiter="\t")
                    if int(row["flag"]) == FLAG]
        self.assertTrue(rows, "item_play_regions.tsv lost f%d" % FLAG)
        self.assertEqual({row["buckets"] for row in rows}, {PLAY_BUCKET})
        self.assertTrue(all(row["source"].startswith("volume:") for row in rows), rows)


if __name__ == "__main__":
    unittest.main()
