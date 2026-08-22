"""#241 -- the Tarnished Pack (2026-08-28) pool-exclusion hook.

Two things must hold before patch day, and this locks both so the hook is not a dead constant:

  1. THE DECISION IS WIRED AND UNCONDITIONAL. Any name in `TARNISHED_PACK_ITEM_NAMES` is excluded
     whether or not DLC is on -- unlike the DLC names, which are excluded only when DLC is off. The
     mutation test plants a name and proves it is dropped under BOTH dlc states, so on patch day
     "paste the new armour names in" is all it takes.
  2. IT IS A NO-OP TODAY. The set is empty until 2026-08-28; a non-empty set here would silently
     drop real items from every pre-patch seed, which is exactly the failure the pin guards.

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
    def test_empty_until_patch_day(self):
        self.assertEqual(
            tp.TARNISHED_PACK_ITEM_NAMES, frozenset(),
            "TARNISHED_PACK_ITEM_NAMES must stay empty until 2026-08-28 -- a name here silently "
            "drops a real item from every pre-patch seed. Populate it ONLY on patch day (#241).")

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
        # restored, so the empty-set pin above is not perturbed for other tests
        self.assertEqual(tp.TARNISHED_PACK_ITEM_NAMES, frozenset())



if __name__ == "__main__":
    unittest.main()
