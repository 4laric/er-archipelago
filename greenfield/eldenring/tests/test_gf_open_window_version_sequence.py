"""Release patch windows advance one number at a time."""

import importlib.util
import os
import sys
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, HERE)
    from _util import find_repo_root, REPO_ONLY_REASON

ROOT = find_repo_root(HERE)
OPEN_WINDOW = None
if ROOT is not None:
    SPEC = importlib.util.spec_from_file_location(
        "open_window_version_sequence", os.path.join(ROOT, "tools", "open_window.py"))
    OPEN_WINDOW = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(OPEN_WINDOW)


@unittest.skipUnless(OPEN_WINDOW is not None, REPO_ONLY_REASON)
class OpenWindowVersionSequenceTests(unittest.TestCase):
    def test_next_patch_is_accepted(self):
        self.assertIsNone(OPEN_WINDOW.patch_sequence_error("0.5.8", "0.5.9"))

    def test_skipped_patch_is_rejected_with_the_expected_successor(self):
        error = OPEN_WINDOW.patch_sequence_error("0.5.8", "0.5.10")
        self.assertIsNotNone(error)
        self.assertIn("0.5.9", error)

    def test_intentional_minor_window_is_not_treated_as_a_skipped_patch(self):
        self.assertIsNone(OPEN_WINDOW.patch_sequence_error("0.5.8", "0.6.0"))


if __name__ == "__main__":
    unittest.main()
