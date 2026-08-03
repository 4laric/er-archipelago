"""gen_data must REFUSE to generate from an incomplete declared input set.

MOTIVATING CASE (CONTRIBUTING rules 4 and 11, 2026-08-02). `item_tiers.tsv` is a declared input at
the repo ROOT. It was absent from a sparse checkout, and gen_data read it as

    if os.path.isfile(_tier_tsv):        # ...and no else

so the tier-list catalog augmentation (+334 gear items) silently did not run. gen_data exited 0 and
emitted `item_catalog` 1724 instead of 2058, which moved Legendary/EniaShop tags in
location_tags.py. Nothing failed. The drift was misattributed to the gen_inputs bundle and cost a
wrong hand-off before a log diff against CI found the real cause -- one ABSENT log line.

`compute_manifest()` already returned `missing`; `compute_inputs_hash()` threw it away, and that is
the one gen_data called. So this asserts the three things that incident needed:

  1. the real checkout IS complete (a live gate, not a unit test of a mock);
  2. an incomplete input set RAISES, naming what is missing -- verified by actually calling the
     real function on a tree that has nothing (rule 7: seen to fail, not assumed to);
  3. the check happens EARLY in gen_data, before any module is written. A completeness check that
     runs at stamp time is decoration: by then the wrong data is already on disk.
"""
import os
import sys
import unittest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:  # run as a script
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
_FOUND = find_repo_root(HERE)
REPO = _FOUND or os.path.dirname(os.path.dirname(HERE))


def _gen_manifest():
    sys.path.insert(0, os.path.join(REPO, "tools"))
    import gen_manifest
    return gen_manifest


@unittest.skipUnless(_FOUND is not None, REPO_ONLY_REASON)
class InputCompleteness(unittest.TestCase):
    def test_this_checkout_declares_nothing_missing(self):
        """The live gate. If this fails, a regen from this tree would emit a smaller dataset."""
        gm = _gen_manifest()
        man = gm.compute_manifest(REPO)
        self.assertEqual(man["missing"], [],
                         "declared input(s) missing from this checkout -- a regen here would "
                         "silently under-generate: %s" % man["missing"])

    def test_item_tiers_tsv_is_declared_and_present(self):
        """The specific file the incident turned on. Declared inputs live in FILE_INPUTS; this one
        sits at the repo ROOT, which is why a greenfield/-only sparse cone dropped it."""
        gm = _gen_manifest()
        self.assertIn("item_tiers.tsv", gm.FILE_INPUTS)
        self.assertNotIn("item_tiers.tsv", gm.OPTIONAL)
        self.assertTrue(os.path.isfile(os.path.join(REPO, "item_tiers.tsv")))

    def test_an_incomplete_tree_is_REFUSED_not_quietly_accepted(self):
        """Rule 7 -- break it and watch it fail. Calls the REAL function on a tree with nothing in
        it, so this cannot pass by testing a mock of itself."""
        import tempfile
        gm = _gen_manifest()
        with tempfile.TemporaryDirectory() as empty:
            with self.assertRaises(SystemExit) as caught:
                gm.require_complete_inputs(empty, who="test")
            msg = str(caught.exception)
            self.assertIn("REFUSING TO GENERATE", msg)
            self.assertIn("item_tiers.tsv", msg, "the message must NAME what is missing")

    def test_gen_data_checks_BEFORE_it_writes(self):
        """A completeness check at stamp time is decoration -- the modules are already on disk.

        Guarding placement, not just presence (rule 8): what would make this pass while the bug is
        back? Calling the function only at the bottom of the file. So assert it appears early, near
        the REPO/AR definitions, and long before the first generated module is opened for writing."""
        src = open(os.path.join(REPO, "greenfield", "gen_data.py"), encoding="utf-8").read()
        self.assertIn("require_complete_inputs", src,
                      "gen_data no longer verifies input completeness -- if it went back to "
                      "compute_inputs_hash(), the `missing` list is being discarded again")
        call_at = src.index("require_complete_inputs")
        first_write = min(src.index('OUT=os.path.join'), src.index("_STAMP_MODULES"))
        self.assertLess(call_at, first_write,
                        "the completeness check must run BEFORE any output is produced")
        self.assertLess(src[:call_at].count("\n"), 80,
                        "the check drifted late in gen_data.py; it belongs beside the REPO/AR "
                        "definitions, before anything is read or written")


if __name__ == "__main__":
    unittest.main()
