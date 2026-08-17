"""The boss worksheet compares human place rulings in the folded AP-region vocabulary."""
import csv
import importlib.util
import os
import sys
import unittest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = find_repo_root(HERE)


@unittest.skipUnless(ROOT, REPO_ONLY_REASON)
class TestBossRegionWorksheet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.path.join(ROOT, "tools", "build_boss_region_worksheet.py")
        spec = importlib.util.spec_from_file_location("_boss_region_worksheet", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.compare = staticmethod(module._arena_vs_members)

    def test_folded_places_do_not_report_false_mismatches(self):
        self.assertEqual("ok", self.compare("Hinterland", "Shadow Keep"))
        self.assertEqual("ok", self.compare("Scaduview", "Shadow Keep"))
        self.assertEqual("ok", self.compare("Ancient Ruins of Rauh", "Ancient Ruins"))
        self.assertEqual("ok", self.compare("Lirunia", "Liurnia"))

    def test_real_mismatch_and_absence_keep_their_meaning(self):
        self.assertEqual("MISMATCH", self.compare("Liurnia", "Limgrave"))
        self.assertEqual("", self.compare("ABSENT", "Limgrave"))

    def test_committed_column_uses_the_same_comparison(self):
        path = os.path.join(ROOT, "greenfield", "boss_region_worksheet.tsv")
        with open(path, encoding="utf-8") as stream:
            rows = csv.DictReader((line for line in stream if not line.startswith("#")),
                                  delimiter="\t")
            for row in rows:
                expected = self.compare(row["arena_region"], row["derived_region"])
                self.assertEqual(expected, row["arena_vs_members"], row["boss_entity"])


if __name__ == "__main__":
    unittest.main()
