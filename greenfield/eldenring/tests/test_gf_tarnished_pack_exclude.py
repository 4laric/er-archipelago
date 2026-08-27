"""#241 -- the Tarnished Pack (2026-08-28) pool-exclusion hook.

Two things must hold before patch day, and this locks both so the hook is not a dead constant:

  1. THE DECISION IS WIRED AND UNCONDITIONAL. Any name in `TARNISHED_PACK_ITEM_NAMES` is excluded
     whether or not DLC is on -- unlike the DLC names, which are excluded only when DLC is off. The
     mutation test plants a name and proves it is dropped under BOTH dlc states, so on patch day
     "paste the new armour names in" is all it takes.
  2. EVERY NAME IS A REAL NAME. Until the pack shipped this was pinned as "the set must be
     EMPTY", which was the right guard for a pre-patch tree and the wrong one from patch day on:
     it turned runbook step 5 ("paste the new armour names in", docs/TARNISHED-PATCH-DAY.md) into
     a red suite. The pin is replaced by the guard it was standing in for -- a name here must be a
     name the regenerated catalog actually has, asserted in test_gf_tarnished_pack_wiring.py where
     ITEM_CATALOG is importable. That catches the failure the empty-pin was really aimed at (a
     guessed or mistyped name, which excludes nothing and silently ships), and it keeps catching
     it after patch day instead of expiring on it.

This file is AP-free (imports only `tarnished_pack`), so it runs on any host. The WIRING -- that
`core` publishes the helper's output as `gf_dlc_excluded`, the set every pool-augmentation feature
reads -- is asserted separately in test_gf_tarnished_pack_wiring.py (needs the AP world).
"""
import importlib.util
import os
import unittest

# Load the AP-free helper directly from source so the decision tests run without the AP env.
_HERE = os.path.dirname(os.path.abspath(__file__))
try:  # installed apworld (CI)
    from worlds.eldenring import tarnished_pack as tp  # type: ignore
except Exception:  # bare source tree (sandbox)
    _spec = importlib.util.spec_from_file_location(
        "tarnished_pack", os.path.join(_HERE, "..", "tarnished_pack.py"))
    tp = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(tp)


class TarnishedPackDecision(unittest.TestCase):
    def test_the_hook_is_a_frozenset_of_non_blank_names(self):
        # Shape only. WHETHER a name is real is decided against ITEM_CATALOG in the wiring test;
        # this file is AP-free and cannot see the catalog. A blank or whitespace entry matches
        # nothing and would be an exclusion that silently excludes zero items.
        self.assertIsInstance(tp.TARNISHED_PACK_ITEM_NAMES, frozenset)
        for name in tp.TARNISHED_PACK_ITEM_NAMES:
            self.assertIsInstance(name, str, f"not a name: {name!r}")
            self.assertEqual(name, name.strip(), f"padded name will never match ITEM_CATALOG: {name!r}")
            self.assertTrue(name, "empty string in TARNISHED_PACK_ITEM_NAMES")

    def test_dlc_semantics_unchanged(self):
        # DLC excluded only when DLC is OFF -- the pre-existing behaviour, preserved exactly.
        self.assertEqual(tp.pool_excluded_names(True, {"A DLC Set"}), frozenset())
        self.assertEqual(tp.pool_excluded_names(False, {"A DLC Set"}), frozenset({"A DLC Set"}))

    def test_tarnished_names_are_excluded_unconditionally(self):
        # The patch-day mutation: a planted pack name is dropped with DLC on AND off, and it does
        # not disturb the DLC decision either way.
        orig = tp.TARNISHED_PACK_ITEM_NAMES
        tp.TARNISHED_PACK_ITEM_NAMES = frozenset({"Heavy Knight Helm"})
        try:
            self.assertIn("Heavy Knight Helm", tp.pool_excluded_names(True, set()))
            self.assertIn("Heavy Knight Helm", tp.pool_excluded_names(False, {"D"}))
            self.assertIn("D", tp.pool_excluded_names(False, {"D"}))
            self.assertNotIn("D", tp.pool_excluded_names(True, {"D"}))
        finally:
            tp.TARNISHED_PACK_ITEM_NAMES = orig
        # restored, so a later patch-day paste is neither hidden nor invented by this test
        self.assertEqual(tp.TARNISHED_PACK_ITEM_NAMES, orig)



if __name__ == "__main__":
    unittest.main()
