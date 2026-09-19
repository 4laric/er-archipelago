"""Option docstrings stay tooltip-sized. AP-free, so it can gate anywhere.

An option's docstring is the text on every built-in Archipelago surface -- the Launcher's Options
Creator (a non-scrolling tooltip that turns each newline into a line break), the generated template
yaml (each line becomes a "# " comment) and the WebHost hover tooltip. A player reported that the
Dungeon Sweep, Keep Local and Keep Local: Rune Cap tooltips "go off the screen": they were 3,625,
3,334 and 3,729 characters. The whole corpus was 72,079 characters and nothing stopped it growing
back.

The rules and the exemption table live in tools/option_doc_budget.py (ONE definition, also read by
tools/dump_options_metadata.py, which refuses to regenerate over the hard cap). This test runs them
against the COMMITTED wizard/options-metadata.json.

WHAT IT DOES NOT COVER. It reads the committed artifact, so it proves the artifact is within budget,
not that the artifact is current: a docstring edit that was never regenerated passes here and fails
`dump_options_metadata.py --check` (the gate that imports the live world). Same split as
test_gf_option_groups and test_gf_wizard_blob_sync.

WHAT IT CANNOT PROVE. That a 13-line tooltip really fits a real Options Creator window. The 14-line
hard cap is inferred; the manual check is to open the Launcher's Options Creator, open Dungeon Sweep
and Keep Local, and screenshot them. If one clips, lower HARD_LINES in tools/option_doc_budget.py.
"""

import json
import os
import sys
import unittest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:  # run as a script (the `generators` CI job does exactly this)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = find_repo_root(HERE)


@unittest.skipUnless(REPO, REPO_ONLY_REASON)
class TestOptionDocBudget(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.join(REPO, "tools"))
        import option_doc_budget
        cls.budget = option_doc_budget
        with open(os.path.join(REPO, "wizard", "options-metadata.json"),
                  "r", encoding="utf-8", newline="") as f:
            cls.options = json.load(f)["options"]

    def test_every_option_docstring_is_within_the_tooltip_budget(self):
        problems = self.budget.violations(self.options)
        self.assertEqual([], problems,
                         "option docstrings over budget (fix the docstring, then regenerate with "
                         "python tools/dump_options_metadata.py):\n  " + "\n  ".join(problems))

    def test_the_gate_can_actually_fail(self):
        """A budget test that cannot fail is worse than none. Feed it a doc that is over every rule
        and require it to complain about each one."""
        bad = [{"key": "probe", "display_name": "P" * 60,
                "description": "no period here and an em dash — too\nnot blank\n" + "x" * 950}]
        bad += self.options[: self.budget.MIN_OPTIONS_WITNESS]
        text = "\n".join(self.budget.violations(bad))
        for needle in ("soft budget", "HARD cap", "line 1", "line 2", "non-ASCII", "display name"):
            self.assertIn(needle, text, "the budget no longer detects: " + needle)

    def test_the_three_reported_tooltips_are_short_enough_to_read(self):
        """The reason this test exists. Pin the three named options to their measured sizes."""
        by = {o["key"]: o["description"] for o in self.options}
        for key in ("dungeon_sweep", "keep_local", "keep_local_rune_cap"):
            doc = by[key]
            self.assertLessEqual(len(doc), 900, key)
            self.assertLessEqual(len(doc.split("\n")), 14, key)


if __name__ == "__main__":
    unittest.main()
