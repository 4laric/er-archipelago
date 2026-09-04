#!/usr/bin/env python3
"""Coverage and determinism gates for the repeated/generic pickup family inventory."""
from __future__ import annotations

import csv
import importlib.util
import json
import os
from pathlib import Path
import unittest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

_ROOT = find_repo_root(__file__, marker="tools/build_generic_pickup_review.py")
ROOT = Path(_ROOT) if _ROOT else None


@unittest.skipUnless(ROOT is not None, REPO_ONLY_REASON)
class GenericPickupReviewTest(unittest.TestCase):
    def test_complete_inventory_and_report_agree(self):
        spec = importlib.util.spec_from_file_location(
            "_generic_pickup_review", ROOT / "tools/build_generic_pickup_review.py")
        tool = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(tool)
        expected, report = tool.build()
        with tool.OUT.open(encoding="utf-8", newline="") as handle:
            actual = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(actual, expected)
        self.assertEqual(json.loads(tool.REPORT.read_text(encoding="utf-8")), report)
        self.assertGreater(len(actual), 2500)
        self.assertEqual(sum(row["confidence"] == "hold" for row in actual),
                         report["remaining_held"])
        self.assertEqual(sum(row["partition"] == "ambiguous_map_lot" for row in actual),
                         report["ambiguous_or_conflicted"])
        self.assertTrue(all(row["detection_mechanism"] == tool.MAP_LOT
                            for row in actual if row["partition"] != "non_map_lot"))


if __name__ == "__main__":
    unittest.main()
