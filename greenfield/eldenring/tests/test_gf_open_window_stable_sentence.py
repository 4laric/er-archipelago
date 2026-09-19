"""The stable row's sentence is drafted from the shipped release, never left as a TODO marker."""

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
        "open_window_stable_sentence", os.path.join(ROOT, "tools", "open_window.py"))
    OPEN_WINDOW = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(OPEN_WINDOW)

CHANGELOG = """# Changelog

## v0.6.1.1 — 2026-09-19

- **A fixpack change:** only in the newer section.

## v0.6.1 — 2026-09-18

### What you need to update

- **Client:** Optional.
- **YAML:** **No new YAML required.**

### What changed

- **New default goal: four Great Runes.** Prose.
- **Leyndell opens on its Lock (apworld):** more prose
  on a second line.
- **Margit region lock (existing and new seeds):** prose. (#202)

## v0.6.0.11 — 2026-09-12

- **Older entry:** must not leak into v0.6.1.
"""


@unittest.skipUnless(OPEN_WINDOW is not None, REPO_ONLY_REASON)
class StableSentenceTests(unittest.TestCase):
    def test_quotes_the_shipped_sections_bullets_and_only_those(self):
        s = OPEN_WINDOW.stable_sentence("v0.6.1", CHANGELOG)
        self.assertIn("New default goal: four Great Runes", s)
        self.assertIn("Leyndell opens on its Lock", s)
        self.assertIn("Margit region lock", s)
        self.assertNotIn("Older entry", s)
        self.assertNotIn("A fixpack change", s)

    def test_version_match_is_exact_not_a_prefix(self):
        # `v0.6.1` must not be read out of the `v0.6.1.1` heading that precedes it.
        self.assertNotIn("only in the newer section",
                         OPEN_WINDOW.stable_sentence("v0.6.1", CHANGELOG))
        self.assertIn("A fixpack change", OPEN_WINDOW.stable_sentence("v0.6.1.1", CHANGELOG))

    def test_update_block_rulings_are_not_changes(self):
        s = OPEN_WINDOW.stable_sentence("v0.6.1", CHANGELOG)
        self.assertNotIn("Client", s)
        self.assertNotIn("YAML", s)

    def test_never_leaves_a_marker_even_with_no_section(self):
        for text in ("", "# Changelog\n", CHANGELOG):
            s = OPEN_WINDOW.stable_sentence("v9.9.9", text)
            self.assertNotIn(OPEN_WINDOW.TODO, s)
            self.assertIn("CHANGELOG", s)

    def test_row_is_one_tab_free_line(self):
        s = OPEN_WINDOW.stable_sentence("v0.6.1", CHANGELOG)
        self.assertNotIn("\t", s)
        self.assertNotIn("\n", s)

    def test_long_release_is_capped(self):
        text = "## v1.0.0 — x\n\n" + "".join("- **Change %d**\n" % i for i in range(20))
        s = OPEN_WINDOW.stable_sentence("v1.0.0", text)
        self.assertIn("and 12 more", s)
        self.assertNotIn("Change 12", s)

    def test_channels_row_carries_no_marker(self):
        _path, rows = OPEN_WINDOW.append_channels("v0.6.1", "2026-09-18", "0.6.1.1", CHANGELOG)
        self.assertNotIn(OPEN_WINDOW.TODO, rows)
        self.assertTrue(rows.startswith("stable\tv0.6.1\t2026-09-18\t"))
        self.assertIn("beta\tmain\t2026-09-18\tthe open v0.6.1.1 window", rows)


if __name__ == "__main__":
    unittest.main()
