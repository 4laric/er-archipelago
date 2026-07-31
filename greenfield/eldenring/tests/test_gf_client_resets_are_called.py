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
#
# The bar for landing here is NOT "the gate is inconvenient" -- it is "a map load cannot break this
# module". The class this file screens for is specifically: WE WRITE A PARAM, a load streams the
# param file back in and reverts the write, and a DONE latch stops us re-applying. A module that
# writes no params, or that re-derives from observed state every tick, is not in that class.
_EDGE_EXEMPT = {
    # connect-scoped: re-armed when a new seed arrives, not per load.
    # (shop_preview / fmg_inject were exempted here until 2026-07-31. Both modules still exist and
    # are still called from core.rs, but NEITHER defines `pub fn reset(` any more, so their entries
    # named nothing and test_the_exemptions_still_exist had been warning about them. Removed rather
    # than kept as decoration: if either regains a reset(), the gate should demand an edge call and
    # make someone re-justify it, which a stale exemption would silently prevent.)
    # Not a param writer at all -- grep lock_hints.rs for SoloParamRepository/set_ and it is empty.
    # It is the server-side hint LEDGER (an AP data-storage key), re-read from the server on the
    # next pump, so there is nothing for a map load to revert. Its reset IS called -- as the method
    # `self.lock_hints.reset()` in core.rs's seed-change block, which is the correct scope: the
    # ledger is keyed per SLOT, so it must be dropped when the seed changes, not when a map loads.
    "lock_hints": "server-side hint ledger, no param writes; reset is seed-scoped in core.rs",
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
        if not missing:
            return

        # SAY WHICH KIND OF MISSING. This gate matches exactly one call shape --
        # `crate::<mod>::reset()`, the free function -- and its failure text used to read
        # "core.rs never calls it" for every miss. For `lock_hints` (2026-07-31) that sentence was
        # simply FALSE: core.rs calls `self.lock_hints.reset()`, because LockHints is a struct held
        # as a field, not a free function. The gate was right to fail (a seed-scoped reset is not an
        # edge reset) and wrong about why, which sent the reader looking for a missing call that was
        # sitting there. A guard is a derivation too, and it will lie to you just as happily.
        #
        # We deliberately do NOT accept `self.<field>.reset()` as satisfying the gate. Accepting it
        # would let a struct-field PARAM WRITER whose reset only runs at connect pass green -- which
        # is the shop_stock bug exactly. Fail closed, and name the shape so the fix is obvious:
        # either move/duplicate the call onto the in_world edge, or exempt with a reason.
        method_shaped = sorted(m for m in missing if re.search(r"\.%s\.reset\(\)" % re.escape(m), self.core))
        uncalled = sorted(m for m in missing if m not in method_shaped)
        detail = []
        if uncalled:
            detail.append("  NO CALL ANYWHERE in core.rs: %s" % uncalled)
        if method_shaped:
            detail.append(
                "  called as a METHOD (`self.<field>.reset()`), which this gate does not accept as "
                "an edge reset: %s\n"
                "    -> that call may be seed-scoped or connect-scoped. If a map load cannot break "
                "the module, add it to _EDGE_EXEMPT with the reason; if it writes params, call it "
                "on the in_world edge too." % method_shaped)
        self.assertFalse(
            missing,
            "%d client module(s) define reset() with no `crate::<mod>::reset()` call in core.rs: "
            "%s.\n%s\n"
            "A map load reverts param writes and each module latches DONE after one pass, so a "
            "reset() that never runs on the in_world edge means the write applies once on connect "
            "and silently never again -- the shop_sell (07-24), shop_icon and shop_stock (07-29) "
            "bug, three times over."
            % (len(missing), sorted(missing), "\n".join(detail)))

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

    def test_the_method_shape_is_still_detected(self):
        """CONTRIBUTING rule 11: the case that motivated the change is the acceptance test.

        `lock_hints` is the module that exposed the lying diagnostic -- reset() defined as a METHOD
        on a struct field, called as `self.lock_hints.reset()`, reported as "never calls it". If the
        method-shape probe ever stops matching, the failure text silently reverts to asserting a
        falsehood about the next module in this shape, so pin the probe itself.
        """
        if "lock_hints" not in self.modules:
            self.skipTest("lock_hints no longer defines reset(); the exemplar is gone")
        self.assertNotIn("crate::lock_hints::reset()", self.core,
                         "lock_hints gained a free-function reset; re-point this exemplar or drop "
                         "its _EDGE_EXEMPT entry")
        # assertRegex, NOT used here on purpose: its failure message embeds the whole haystack, and
        # core.rs is ~400 KB -- the diagnostic would be unreadable. Found by running the mutation.
        self.assertTrue(re.search(r"\.lock_hints\.reset\(\)", self.core),
                        "the method-call shape this test exists to describe is gone from core.rs; "
                        "re-point this exemplar at whatever module now has a method-shaped reset()")


if __name__ == "__main__":
    unittest.main()
