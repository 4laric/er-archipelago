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

    def test_auto_keeps_exactly_the_draw_and_its_closure(self):
        """WAS test_auto_keeps_the_goal_region: "no named goal -> GOAL_REGION is force-kept, so
        `auto` can always derive a terminus".

        SPEC-ashen-capital-lock (2026-08-06) deleted that force-keep. `auto` resolves to the Elden
        Beast on every base-game seed and the Ashen Capital is reached from the HUB behind an item,
        so the derivation always has a terminus WITHOUT any region being kept for it -- and
        `num_regions` finally means what it says (bobler: "num_regions: 1 gave me four regions").

        What replaces it is strictly stronger than what it said: `auto` keeps EXACTLY its draw plus
        the parent closure of that draw, and nothing else. The old assertion would pass under any
        force-keep at all, including a new one; this one fails on the first extra region."""
        for seed in range(120):
            parts = {}
            kept = self.rs.compute_kept(6, random.Random(seed), self.all, parts=parts)
            self.assertEqual(parts["forced"], [],
                             "seed %d: `auto` passes no forced set and compute_kept must add none "
                             "of its own" % seed)
            closure = {a for r in parts["drawn"] for a in self.rs.parent_chain(r)}
            self.assertEqual(set(kept), set(parts["drawn"]) | closure,
                             "seed %d: auto kept something that is neither drawn nor an ancestor "
                             "of a drawn region: %s"
                             % (seed, sorted(set(kept) - set(parts["drawn"]) - closure)))
        # WITNESS (test_gf_vacuous_pass): the equality above would also hold if the goal region
        # simply always fell out of the draw, so state the fact the deleted force-keep guaranteed
        # and which must now be FALSE -- some auto seed does not keep the capital at all.
        without = sum(1 for seed in range(120)
                      if self.rs.GOAL_REGION not in self._kept(6, seed))
        self.assertGreater(without, 0,
                           "every one of 120 auto seeds kept the goal region -- the `auto` "
                           "force-keep is back")

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
        # WITNESS (test_gf_vacuous_pass): the assertion below says a set is EMPTY, which is also
        # what it would say if the sweep had kept nothing at all. Prove the sweep saw something.
        self.assertTrue(seen, "the sweep kept NO regions across %d seeds -- `missing` would be the "
                              "whole pool and the assertion below could not fail" % self.SEEDS)
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

    # ---- #409: the draw is EXPLAINED, not just correct -------------------------------------
    #
    # 🛑 THE MOTIVATING CASE (CONTRIBUTING rule 11) IS A SUPPORT COST, NOT A CRASH. bobler set
    # `num_regions: 1` on 0.3.5 and got FOUR regions; he asked twice, an hour apart, and was still
    # unsure. Every step was right -- the draw took Liurnia, `goal: elden_beast` force-kept Farum
    # Azula and Leyndell (GOAL_CHOICES), and the parent closure pulled Altus in behind Leyndell --
    # and NOTHING SAID SO. The acceptance test for "N is a draw size, not a region count" is
    # therefore that the three contributions are recoverable and that the line names all three.

    def test_the_three_contributions_partition_the_kept_set(self):
        """`parts` must ACCOUNT FOR EVERY KEPT REGION, exactly once. A breakdown that does not add
        up to the kept set is worse than none: it would state a wrong number with authority."""
        for n in (1, 3, 6, 12):
            for seed in range(60):
                parts = {}
                kept = self.rs.compute_kept(n, random.Random(seed), self.all,
                                            forced=("Farum Azula", "Leyndell"), parts=parts)
                got = parts["drawn"] + parts["forced"] + parts["closure"]
                self.assertEqual(len(got), len(set(got)),
                                 "a region is counted in two contributions: %r" % (parts,))
                self.assertEqual(sorted(got), sorted(kept),
                                 "the breakdown does not add up to the kept set (n=%d seed=%d): %r"
                                 % (n, seed, parts))
                self.assertEqual(len(parts["drawn"]), min(n, len(self.all)),
                                 "`drawn` must be exactly the draw size, not the total")

    def test_parts_is_observational_only(self):
        """Telemetry may not move the draw. Passing `parts` must not change the rng stream or the
        result -- a logging feature that perturbed every rolled seed would be a far worse bug than
        the one it documents (the economy floor is one seed thick)."""
        for seed in (0, 7, 99):
            plain = self.rs.compute_kept(6, random.Random(seed), self.all)
            observed = self.rs.compute_kept(6, random.Random(seed), self.all, parts={})
            self.assertEqual(plain, observed, "passing parts= changed the kept set")

    def test_the_line_names_all_three_contributions(self):
        """bobler's line, rendered from his own breakdown. This is the sentence that would have
        answered him in the spoiler instead of four hours later."""
        line = self.rs.describe_kept(
            1,
            {"drawn": ["Liurnia"], "forced": ["Farum Azula", "Leyndell"], "closure": ["Altus"]},
            ["Liurnia", "Farum Azula", "Leyndell", "Altus"],
            goal="elden_beast")
        self.assertEqual(
            line,
            "num_regions: 1 drawn (Liurnia) + 2 forced by goal=elden_beast (Farum Azula, Leyndell)"
            " + 1 parent closure (Altus) = 4 kept")

    def test_start_pool_and_goal_force_keeps_are_named_separately(self):
        """#841: the old line called every forced region `goal=auto`, including candidates the
        player added through start_region_pool. The categories must partition the same combined
        `forced` list without moving or double-counting a region."""
        line = self.rs.describe_kept(
            1,
            {"drawn": ["Liurnia"],
             "forced": ["Farum Azula", "Leyndell", "Caelid", "Limgrave"],
             "closure": ["Altus"]},
            ["Liurnia", "Farum Azula", "Leyndell", "Caelid", "Limgrave", "Altus"],
            goal="elden_beast",
            start_region_pool={"Caelid", "Limgrave"})
        self.assertEqual(
            line,
            "num_regions: 1 drawn (Liurnia) + 2 forced by start_region_pool (Caelid, Limgrave)"
            " + 2 forced by goal=elden_beast (Farum Azula, Leyndell)"
            " + 1 parent closure (Altus) = 6 kept")
        self.assertEqual(line.count("Caelid"), 1, "a starting candidate was counted twice")
        self.assertNotIn("goal=auto", line, "start_region_pool was mislabeled as an automatic goal")

    def test_the_line_omits_contributions_that_did_not_happen(self):
        """A draw that needed nothing must not print "+ 0 forced + 0 parent closure" -- noise in
        every log line is how a line stops being read."""
        line = self.rs.describe_kept(2, {"drawn": ["Limgrave", "Caelid"], "forced": [],
                                         "closure": []},
                                     ["Limgrave", "Caelid"])
        self.assertEqual(line, "num_regions: 2 drawn (Limgrave, Caelid) = 2 kept")
        self.assertNotIn("+", line)
        full = self.rs.describe_kept(0, {"drawn": list(self.all), "forced": [], "closure": [],
                                         "full_pool": True}, list(self.all))
        self.assertEqual(full, "num_regions: 0 = the whole eligible map = %d kept" % len(self.all))

    def test_a_real_draw_reproduces_the_report_shape(self):
        """END TO END on a REAL draw, not a hand-built dict: somewhere in a seed sweep, `n=1` with
        the elden_beast forced set must produce MORE than one kept region and a line whose total
        matches. Stated as a SEED SEARCH rather than a magic seed -- the draw is random, so the
        property is "this shape occurs and is described correctly", and the search FAILS LOUD if it
        never occurs rather than passing vacuously."""
        forced = ("Farum Azula", "Leyndell")
        hits = 0
        for seed in range(200):
            parts = {}
            kept = self.rs.compute_kept(1, random.Random(seed), self.all, forced=forced,
                                        parts=parts)
            if len(kept) <= 1:
                continue
            hits += 1
            line = self.rs.describe_kept(1, parts, kept, goal="elden_beast")
            self.assertTrue(line.endswith("= %d kept" % len(kept)),
                            "the line's total disagrees with the kept set: %r vs %d" % (line,
                                                                                        len(kept)))
            self.assertIn("drawn", line)
            self.assertIn("forced by goal=elden_beast", line)
            for r in parts["closure"]:
                self.assertIn(r, line, "a closure region is missing from the line")
        self.assertGreater(hits, 0, "no seed in 200 produced a kept set larger than num_regions=1 "
                                    "with a forced goal set -- this test proved nothing")

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
