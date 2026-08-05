"""Region SELECTION invariants, stated as properties over a seed sweep -- AP-free, gen-side.

WHY THIS FILE EXISTS (2026-08-05). Removing the `spine` order deleted the only DETERMINISTIC kept
set, and half a dozen suites had been leaning on it as a determinism handle: assert the kept set IS
Limgrave/Weeping/Stormveil and you have tested the draw by identity. Identity assertions cannot
survive a random draw, and the fix is not to re-pin them to a seed -- it is to say what must be TRUE
of every draw. Alaric's call, explicitly over keeping a player-unreachable `order` parameter alive
for the tests to use, because a code path no player can reach rots.

compute_kept is pure and imports no Archipelago, so this runs in the AP-free generators job rather
than the world suite -- the selection logic is gen-side and deserves gen-side coverage.

THE ANTI-SPINE PROPERTY is test_every_eligible_region_is_reachable_across_seeds: under the old order
NINE base regions could never be kept at num_regions=6, no matter the seed. That is the defect this
whole change exists to fix, and it is the property a re-introduced fixed order fails immediately --
VERIFIED by restoring the spine draw and watching this file go red (2026-08-05).
"""
import os
import random
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:                                        # direct/script fallback
    sys.path.insert(0, HERE)
    from _util import find_repo_root, REPO_ONLY_REASON

_ROOT = find_repo_root(HERE)


def _load_spine():
    """region_spine + data via a package shim: relative imports, no Archipelago."""
    import importlib.util
    import types
    pkg_dir = os.path.join(_ROOT, "greenfield", "eldenring")
    pkg = types.ModuleType("_gfsel")
    pkg.__path__ = [pkg_dir]
    sys.modules["_gfsel"] = pkg

    def sub(name):
        spec = importlib.util.spec_from_file_location("_gfsel." + name,
                                                      os.path.join(pkg_dir, name + ".py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["_gfsel." + name] = mod
        spec.loader.exec_module(mod)
        return mod

    sub("data")
    return sub("region_spine")


@unittest.skipIf(_ROOT is None, REPO_ONLY_REASON)
class RegionSelection(unittest.TestCase):
    SEEDS = 400

    @classmethod
    def setUpClass(cls):
        cls.rs = _load_spine()
        cls.all = list(cls.rs.REGIONS)
        cls.base = cls.rs.base_regions()
        assert cls.base, "base region pool is empty -- every property below would be vacuous"

    def _kept(self, n, seed, pool=None, forced=()):
        return self.rs.compute_kept(n, random.Random(seed), pool or self.all, forced=forced)

    def test_draw_is_n_plus_the_closure_and_nothing_else(self):
        """Every kept region comes from the pool, appears once, and the set is n + goal + parents."""
        for n in (1, 3, 6, 12):
            for seed in range(60):
                kept = self._kept(n, seed)
                self.assertEqual(len(kept), len(set(kept)), "duplicate region in kept set")
                self.assertTrue(set(kept) <= set(self.all), "kept a region outside the pool")
                self.assertGreaterEqual(len(kept), min(n, len(self.all)),
                                        "kept fewer than num_regions asked for")

    def test_parent_closure_holds(self):
        """A gated child is never kept without its ancestors -- fill would strand progression."""
        for n in (1, 3, 6):
            for seed in range(80):
                kept = set(self._kept(n, seed))
                for r in kept:
                    for anc in self.rs.parent_chain(r):
                        self.assertIn(anc, kept, "%s kept without its ancestor %s" % (r, anc))

    def test_full_pool_when_n_is_zero_or_oversized(self):
        for n in (0, -1, len(self.all), len(self.all) + 5):
            self.assertEqual(sorted(self._kept(n, 1)), sorted(self.all),
                             "n=%s must keep the whole eligible pool" % n)

    def test_auto_keeps_the_goal_region(self):
        """No named goal -> GOAL_REGION is force-kept, so `auto` can always derive a terminus."""
        for seed in range(120):
            self.assertIn(self.rs.GOAL_REGION, self._kept(6, seed),
                          "auto seed lost the goal region")

    def test_a_named_goal_is_kept_and_does_not_drag_the_capital(self):
        """The 2026-08-05 fix: forcing Enir Ilim must not also force Leyndell. Stated as BOTH halves
        -- the forced region always kept, AND the capital no longer universal -- because the first
        alone would pass on the old unconditional-append code."""
        if "Enir Ilim" not in set(self.all):
            self.skipTest("DLC regions absent from this data build")
        caps = 0
        for seed in range(self.SEEDS):
            kept = set(self._kept(6, seed, forced=("Enir Ilim",)))
            self.assertIn("Enir Ilim", kept, "a NAMED goal region was not kept")
            caps += self.rs.GOAL_REGION in kept
        self.assertLess(caps, self.SEEDS,
                        "the capital is still kept in EVERY named-goal seed -- the unconditional "
                        "GOAL_REGION append is back")

    def test_every_eligible_region_is_reachable_across_seeds(self):
        """THE property the spine order failed: at num_regions=6 it could never keep nine of the
        base regions. Any fixed-order re-introduction fails here on the first run."""
        seen = set()
        for seed in range(self.SEEDS):
            seen |= set(self._kept(6, seed, pool=self.base))
        missing = sorted(set(self.base) - seen)
        self.assertFalse(missing, "these base regions were NEVER kept in %d seeds: %r"
                         % (self.SEEDS, missing))

    def test_the_draw_actually_varies(self):
        """A constant kept set would satisfy every property above."""
        sets = {tuple(sorted(self._kept(6, s, pool=self.base))) for s in range(self.SEEDS)}
        self.assertGreater(len(sets), self.SEEDS // 10,
                           "only %d distinct kept sets in %d seeds -- the draw is not random"
                           % (len(sets), self.SEEDS))

    def test_same_seed_same_result(self):
        for seed in (0, 7, 99):
            self.assertEqual(self._kept(6, seed), self._kept(6, seed),
                             "compute_kept is not deterministic for a fixed rng seed")

    def test_a_restricted_pool_is_never_escaped(self):
        """DLC-only / base-only draws may not smuggle in a region outside the eligible set."""
        for pool, label in ((self.base, "base-only"), (self.rs.dlc_regions(), "dlc-only")):
            if not pool:
                continue
            for seed in range(60):
                self.assertTrue(set(self._kept(6, seed, pool=pool)) <= set(pool),
                                "%s draw escaped its pool" % label)


if __name__ == "__main__":
    unittest.main(verbosity=2)
