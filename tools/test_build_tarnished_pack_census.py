import importlib.util
import os
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "tools", "build_tarnished_pack_census.py")
SPEC = importlib.util.spec_from_file_location("build_tarnished_pack_census", PATH)
CENSUS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CENSUS)


class TarnishedPackCensusDocument(unittest.TestCase):
    def test_committed_document_is_current(self):
        with open(CENSUS.OUTPUT, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), CENSUS.render())

    def test_report_has_all_dispositions(self):
        report = CENSUS.render()
        self.assertIn("**14 admitted; 5 blocked", report)
        self.assertIn("blocked_activation", report)
        self.assertIn("blocked_grant", report)
        self.assertIn("blocked_missability", report)


if __name__ == "__main__":
    unittest.main()
