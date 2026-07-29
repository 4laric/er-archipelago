"""Every client `reset()` must be CALLED on the in-world edge. Three writers forgot; nothing caught it.

THE CLASS, three instances in six days:
  * shop_sell   -- 2026-07-24, found by a Kalé repro in playtest
  * shop_icon   -- 2026-07-29, found by a review noticing the asymmetry
  * shop_stock  -- 2026-07-29, found only after a player reported the SAME symptom three times

A map load streams ShopLineupParam / ItemLotParam back in and reverts our param writes. Each writer
latches a `DONE` flag after one clean pass, so unless `reset()` is called on the `in_world` false->true
edge, the write applies once on connect and is gone for the rest of the session. `DONE` stays set, so
nothing retries and nothing logs.

🛑 A `reset()` WITH NO CALLER IS THE SAME BUG AS A PREDICATE WITH NO CALLER. CONTRIBUTING already says
"a green predicate with no production caller is not a fix -- it is a spec". This is that rule one
level down: the function existed, read as protection, and was dead code. shop_stock's was dead from
the day it was written.

WHY IT COST SO MUCH. The generator was provably correct -- his seed's slot_data carried a Golden Rune
[5] priced at 4 runes -- so every measurement upstream of the game agreed the feature worked, and I
told him so three times. A correct wire is not a correct feature.
"""
import os
import re
import unittest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

_ROOT = find_repo_root(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_ROOT or "", "from-software-archipelago-clients",
                    "crates", "eldenring-archipelago", "src")

# Modules whose reset() is deliberately NOT on the in-world edge. Each needs a reason.
_EDGE_EXEMPT = {
    # connect-scoped: re-armed when a new seed arrives, not per load.
    "shop_preview": "FMG override, reset at connect (msg repo is not streamed back per load)",
    "fmg_inject": "process-latched by design; the swap survives loads",
}


@unittest.skipUnless(_ROOT is not None, REPO_ONLY_REASON)
class ClientResetsAreCalled(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(_SRC):
            raise unittest.SkipTest("client not checked out beside the repo")
        with open(os.path.join(_SRC, "core.rs"), encoding="utf-8") as fh:
            cls.core = fh.read()
        cls.modules = {}
        for fn in sorted(os.listdir(_SRC)):
            if not fn.endswith(".rs") or fn in ("core.rs", "contract_gen.rs"):
                continue
            with open(os.path.join(_SRC, fn), encoding="utf-8") as fh:
                body = fh.read()
            if re.search(r"pub fn reset\s*\(", body):
                cls.modules[fn[:-3]] = body

    def test_every_reset_has_a_caller_on_the_in_world_edge(self):
        """A reset() nobody calls is dead code wearing the shape of a safeguard."""
        self.assertTrue(self.modules, "found no client module defining reset() -- the scan broke")
        missing = [m for m in self.modules
                   if m not in _EDGE_EXEMPT
                   and ("crate::%s::reset()" % m) not in self.core]
        self.assertFalse(
            missing,
            "%d client module(s) define reset() but core.rs never calls it: %s.\n"
            "A map load reverts param writes and each module latches DONE after one pass, so an "
            "uncalled reset() means the write applies once on connect and silently never again -- "
            "the shop_sell (07-24), shop_icon and shop_stock (07-29) bug, three times over. Either "
            "call it on the in_world edge or add it to _EDGE_EXEMPT with a reason."
            % (len(missing), sorted(missing)))

    def test_the_exemptions_still_exist(self):
        """An exemption for a module that is gone hides the next real omission behind stale prose."""
        stale = [m for m in _EDGE_EXEMPT if m not in self.modules]
        if stale:
            import warnings
            warnings.warn("_EDGE_EXEMPT names %s, which no longer define reset() -- prune them so "
                          "the list keeps meaning something." % sorted(stale))

    def test_the_scan_is_not_vacuous(self):
        """If the regex or the layout changes this must fail loudly, not pass with zero findings."""
        self.assertGreaterEqual(
            len(self.modules), 5,
            "only %d module(s) with reset() found; the client has more than that. The scan is "
            "matching nothing and a green run here would mean nothing." % len(self.modules))
        self.assertIn("crate::shop_stock::reset()", self.core,
                      "shop_stock::reset() is the regression this file was written for")


if __name__ == "__main__":
    unittest.main()
