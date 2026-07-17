"""Tier-A COVERAGE GATE test -- the join over an option matrix, asserting a stable baseline.

Two halves:
  * STATIC half (AP-free, runs anywhere in milliseconds, like test_gf_data.py): loads
    coverage.py by file path, runs the full-pool join + a pinned scoped matrix
    (all/base/dlc pools x num_regions 0/3/5 via region_spine.compute_kept), and asserts the
    encoded baseline. Also proves the gate can CATCH a hole (corruption tripwires) and that the
    degradation ledger self-cleans -- a gate that trivially passes is worse than none.
  * LIVE half (WorldTestBase, needs AP + installed worlds.eldenring -- tools/gf_test.py): builds
    real worlds over an option matrix (num_regions PINNED in every config -- the unpinned default
    breaks tests, memory er-test-defaults-numregions) and joins the ACTUALLY EMITTED slot_data.

Baseline THIS tree (post the 2026-07-14 synthetic-award-guard regen -- encode it so a regression
that ADDS an uncovered location fails here). NOTE 2026-07-14: these constants encode the tree AFTER
`build.ps1 -Greenfield` re-runs gen_data with the synthetic award guard (drops the 3 phantom
synthetic rows: flags 177, 320820, 1038457500 -- 4836 -> 4833). Until that regen lands, this file
and the award check are RED on exactly those locations. That red is the gate telling the truth: two
of the three are checks a player can hunt and NEVER obtain. Do not paper over it -- regen.
  * detection / award / region / quarantine violations: **0** in every scope.
  * suppression violations: NONE. BASELINE_SUPPRESSION_APS is empty and must stay empty --
    its 6 debut holes were FIXED on 2026-07-14 (lotItemCategory 0/6 are GOODS; the lot blank was the
    only mechanism that could suppress a farmable ware, and an abstention had closed it).
    check_lots_table.json (EMEVD-award or unjudged lotItemCategory-0/6 rows), whose wares are
    farmable REPEATABLE_GOODS, so features/check_item_flags.py correctly declines id-keyed
    suppression: the vanilla ware double-dips at these checks. They are deliberately NOT in
    coverage_quarantine.ACCEPTED_LEAKS -- they stay visible here until someone decides to either
    fix them (blank via an EMEVD/lot enrichment) or formally accept them.
  * static full pool: 4833 emitted locations (561 shop checks).

Run (static half): python -m pytest greenfield/eldenring/tests/test_coverage_gate.py
Run (both halves): python tools/gf_test.py -- -k coverage_gate
"""
import importlib.util
import os
import sys
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GF_PKG = os.path.dirname(HERE)
_PKG = "cov_gate_test_pkg"  # synthetic package so path-loaded modules can relative-import siblings

# --- the encoded baseline (this tree) ---------------------------------------------------------
BASELINE_TOTAL_LOCATIONS = 4848   # 4833 (post synthetic-award-guard regen) + 10 finale (the
                                  # conditional Ashen Capital, 2026-07-14) + 7 gesture pickups --
                                  # every new location covered; the gate stayed at ZERO violations
BASELINE_SHOP_CHECKS = 561   # 562 -> 561 (2026-07-18): the shop-region/ShopSlot pass reclassified one
                             # merchant check off the shop_stock_flag channel; total pool unchanged (4848)
# EMPTY, and it must stay that way. ap_id -> region (so scoped runs can subset).
#
# This held the 6 suppression holes the gate found on debut -- Glintstone Scrap, Gravel Stone, and four
# Golden Runes. They are FIXED (2026-07-14), not accepted:
#
#   Their wares are FARMABLE goods, so check_item_flags correctly refuses to suppress them by id (it
#   would eat every legitimate copy the player ever picks up). The LOT BLANK was the only mechanism that
#   could ever work for them -- and it was locked behind `_cat == 1` in gen_data plus a "lotItemCategory
#   0 and 6 are ambiguous, NEVER judged" comment. They were never ambiguous; they were never DERIVED.
#   Both categories are GOODS (voted out of ItemLotParam x ITEM_CATALOG). Three suppression mechanisms,
#   and the abstention closed the only door that applied.
#
# So this is now the assertion that the fix STAYS fixed. A new entry here is not bookkeeping -- it is a
# check that hands the player its vanilla ware alongside the Archipelago item, in every seed, silently.
# Fix the mechanism. Do not pin the symptom.
BASELINE_SUPPRESSION_APS = {}


def _path_load(modname):
    """Load a package module by file path under a synthetic package (so `from .data import ...`
    works without an AP install), memoized in sys.modules."""
    if _PKG not in sys.modules:
        pkg = types.ModuleType(_PKG)
        pkg.__path__ = [GF_PKG]
        sys.modules[_PKG] = pkg
    fq = _PKG + "." + modname
    if fq in sys.modules:
        return sys.modules[fq]
    spec = importlib.util.spec_from_file_location(fq, os.path.join(GF_PKG, modname + ".py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[fq] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        del sys.modules[fq]
        raise
    return mod


class _BaselineAssertions:
    """Shared baseline assertion, used by BOTH halves. `cov` is the coverage module in use."""

    def assert_baseline(self, cov, records, ctx, byname, label):
        self.assertGreater(len(records), 0, f"{label}: no emitted locations")
        self.assertEqual([v.detail for v in byname["detection"]], [],
                         f"{label}: detection must be clean (a new undetectable location leaked in)")
        self.assertEqual([(v.ap_id, v.detail) for v in byname["award"]], [],
                         f"{label}: award must be clean -- a location is keyed on a flag NO "
                         f"ItemLotParam row awards (the phantom 177/320820 class): the game can "
                         f"never set it, the check can never fire, a progression item placed on it "
                         f"is a multiworld soft-lock. If this fires right after a gen_data change, "
                         f"regenerate (build.ps1 -Greenfield) -- the synthetic award guard drops "
                         f"these rows at the source.")
        self.assertEqual([v.detail for v in byname["region"]], [],
                         f"{label}: region consistency must be clean")
        self.assertEqual([v.detail for v in byname["quarantine"]], [],
                         f"{label}: degradation ledger must be clean/self-consistent")
        in_scope = {ap for ap, region in BASELINE_SUPPRESSION_APS.items()
                    if region in set(ctx["scope"])}
        got = {v.ap_id for v in byname["suppression"]}
        self.assertEqual(got, in_scope,
                         f"{label}: suppression violations must be exactly the encoded baseline "
                         f"(a NEW unsuppressed ware leaked in, or a baseline hole was fixed -- "
                         f"update BASELINE_SUPPRESSION_APS); got {sorted(got)}, "
                         f"expected {sorted(in_scope)}")


# ===================================================================================================
# STATIC half -- AP-free
# ===================================================================================================
class CoverageGateStatic(unittest.TestCase, _BaselineAssertions):
    @classmethod
    def setUpClass(cls):
        cls.cov = _path_load("coverage")
        cls.spine = _path_load("region_spine")

    # ------------------------------------------------------------------ full pool snapshot
    def test_static_full_pool_baseline_snapshot(self):
        records, ctx, byname = self.cov.report_coverage(printer=None)
        self.assertEqual(len(records), BASELINE_TOTAL_LOCATIONS,
                         "full-pool emitted-location count drifted -- update "
                         "BASELINE_TOTAL_LOCATIONS (and confirm the new locations are covered)")
        self.assertEqual(sum(1 for r in records.values()
                             if r.detect_kind == "shop_stock_flag"), BASELINE_SHOP_CHECKS,
                         "shop-check count drifted -- update BASELINE_SHOP_CHECKS")
        self.assert_baseline(self.cov, records, ctx, byname, "static-full")

    # ------------------------------------------------------------------ scoped option matrix
    def test_static_scoped_option_matrix(self):
        import random
        rng = random.Random(0xC0FFEE)
        pools = {
            "all": list(self.spine.REGIONS),
            "base": self.spine.base_regions(),
            "dlc": self.spine.dlc_regions(),
        }
        for pool_name, pool in pools.items():
            for n in (0, 3, 5):  # num_regions PINNED -- never the default
                kept = self.spine.compute_kept(n, "spine", rng, eligible=pool)
                label = f"scoped:{pool_name}-nr{n}"
                with self.subTest(config=label):
                    records, ctx, byname = self.cov.report_coverage(kept=kept, printer=None)
                    self.assert_baseline(self.cov, records, ctx, byname, label)

    # ------------------------------------------------------------------ the gate can CATCH a hole
    def test_tripwire_lot_blank_removal_is_caught(self):
        """Corrupt the static suppression table (drop one covered flag) -> the join must report a
        NEW suppression violation. Proves the suppression check is a real join, not a tautology."""
        sm, se, si = self.cov._load_static_table()
        self.assertTrue(sm, "static table empty -- check_lots_table.json missing?")
        _, _, clean = self.cov.report_coverage(printer=None)
        victim = next(iter(sm))
        broken = dict(sm); del broken[victim]
        _, _, tripped = self.cov.report_coverage(printer=None, _static_table=(broken, se, si))
        self.assertGreater(len(tripped["suppression"]), len(clean["suppression"]),
                           "gate did NOT trip on a corrupted suppression table")

    def test_tripwire_flag_with_no_awarding_lot_is_caught(self):
        """A check keyed on a flag NO ItemLotParam row awards (the phantom synthetic class: flag
        177's only lot awards nothing; flag 320820 has no lot at all) must be an award violation.
        Proves check_award_source is a real join against check_lots_table.json, not a tautology."""
        records, ctx = self.cov.build_coverage()
        victim = next(r for r in records.values() if r.detect_kind == "event_flag"
                      and r.ap_id not in ctx["shop_flag_by_ap"])
        bogus = 979797  # provably outside the award join THIS run:
        self.assertNotIn(bogus, ctx["static_map"])
        self.assertNotIn(bogus, ctx["static_enemy"])
        self.assertNotIn(bogus, ctx["static_items"])
        clean = self.cov.check_award_source(records, ctx)
        victim.detect_flag = bogus
        tripped = self.cov.check_award_source(records, ctx)
        self.assertEqual(len(tripped), len(clean) + 1,
                         "gate did NOT trip on a flag with no awarding lot")
        hit = next(v for v in tripped if v.ap_id == victim.ap_id)
        self.assertIn("NO awarding ItemLotParam row", hit.detail)

    def test_tripwire_system_flag_collision_is_caught(self):
        """A check keyed on the deathlink-kill flag (the old 76996 collision class) must be a
        detection violation."""
        records, ctx = self.cov.build_coverage()
        victim = next(iter(records.values()))
        victim.detect_flag = self.cov.DEATHLINK_KILL_FLAG
        det = self.cov.check_detection(records, ctx)
        self.assertEqual(len(det), 1)
        self.assertIn("system-flag collision", det[0].detail)

    def test_tripwire_aliased_flag_is_caught(self):
        records, ctx = self.cov.build_coverage()
        vals = list(records.values())
        vals[10].detect_flag = vals[20].detect_flag
        det = self.cov.check_detection(records, ctx)
        self.assertGreaterEqual(len(det), 2, "aliased flags must be reported for BOTH locations")

    def test_tripwire_sweep_mismatch_is_caught(self):
        """A sweep member whose canonical region disagrees (Full Moon Queen class) must be a
        region violation."""
        records, ctx = self.cov.build_coverage()
        trig, members = next((t, m) for t, m in ctx["DUNGEON_SWEEPS"].items() if m)
        sr = ctx["SWEEP_REGION"][trig]
        member = next(a for a in members if a in records)
        records[member].region = "Limgrave" if sr != "Limgrave" else "Caelid"
        reg = self.cov.check_region_consistency(records, ctx)
        self.assertTrue(any("Full Moon Queen" in v.detail for v in reg),
                        "sweep-membership mismatch not caught")

    # ------------------------------------------------------------------ degradation ledger
    def test_quarantine_ledger_is_wellformed(self):
        q = self.cov._load("coverage_quarantine")
        self.assertIsNotNone(q, "coverage_quarantine.py failed to load")
        self.assertEqual(q.validate_ledger(), [], "coverage_quarantine ledger is malformed")

    def test_accepted_leak_self_cleans_when_suppressable(self):
        """An ACCEPTED_LEAK for a location that is actually suppressable must make the gate say
        'remove it' (the ledger cannot rot into a permanent excuse)."""
        q = self.cov._load("coverage_quarantine")
        records, ctx = self.cov.build_coverage()
        target = next(r for r in records.values()
                      if r.suppress_kind in self.cov.SUPPRESS_KINDS and r.is_filler is True)
        saved = dict(q.ACCEPTED_LEAKS)
        try:
            q.ACCEPTED_LEAKS.clear()
            q.ACCEPTED_LEAKS[target.ap_id] = {
                "reason": "test injected", "issue": "TEST", "date": "2026-07-14"}
            byname = self.cov.all_checks(records, ctx)
            hits = [v for v in byname["quarantine"] if v.ap_id == target.ap_id]
            self.assertTrue(hits, "a suppressable ACCEPTED_LEAK must be reported for removal")
            self.assertIn("remove", hits[0].detail.lower())
        finally:
            q.ACCEPTED_LEAKS.clear()
            q.ACCEPTED_LEAKS.update(saved)

    def test_quarantine_self_cleans_when_emitted_and_passing(self):
        """A QUARANTINE entry (promised excluded) that is STILL emitted and passes every check must
        be reported for removal."""
        q = self.cov._load("coverage_quarantine")
        records, ctx = self.cov.build_coverage()
        flagged = {v.ap_id for lst in self.cov.all_checks(records, ctx).values() for v in lst}
        target = next(r for r in records.values() if r.ap_id not in flagged)
        saved = dict(q.QUARANTINE)
        try:
            q.QUARANTINE.clear()
            q.QUARANTINE[target.ap_id] = {
                "reason": "test injected", "issue": "TEST", "date": "2026-07-14"}
            byname = self.cov.all_checks(records, ctx)
            hits = [v for v in byname["quarantine"] if v.ap_id == target.ap_id]
            self.assertTrue(hits, "an emitted+passing QUARANTINE entry must be reported for removal")
            self.assertIn("remove", hits[0].detail.lower())
        finally:
            q.QUARANTINE.clear()
            q.QUARANTINE.update(saved)

    # ------------------------------------------------------------------ report mode is fail-open
    def test_assert_coverage_is_wired_into_the_gen_path(self):
        """assert_coverage must be WIRED and RAISING (2026-07-14).

        It debuted in report mode -- fail-open, per the release rule -- and the baseline soaked to
        ZERO violations. It now raises from core.post_fill.

        This assertion is the inverse of the one it replaces, and the inversion is the point: a gate
        that exists but is not called is a gate that catches nothing. Every significant bug of
        2026-07-13/14 was inside its scope (region geometry in the wrong id space, suppression keyed
        by the wrong id space, whole lotItemCategories silently never judged) and NOT ONE of them
        errored, logged, or failed a test. If someone un-wires this to make a seed generate, they are
        re-creating that world, and this test is what stops them.
        """
        self.assertTrue(callable(getattr(self.cov, "assert_coverage", None)))
        src = open(os.path.join(GF_PKG, "core.py"), encoding="utf-8").read()
        self.assertIn("assert_coverage", src,
                      "core.py no longer calls assert_coverage -- the coverage gate is DEAD. It is "
                      "not a report; it is the thing that makes a silent wrong answer loud.")


# ===================================================================================================
# LIVE half -- needs AP + installed worlds.eldenring (tools/gf_test.py)
# ===================================================================================================
try:
    import pytest
    _bases = pytest.importorskip("test.bases")
    pytest.importorskip("worlds.eldenring")
    WorldTestBase = _bases.WorldTestBase
    _HAVE_AP = True
except Exception:  # bare source tree: static half already ran; skip the live half quietly
    _HAVE_AP = False

if _HAVE_AP:
    from worlds.eldenring import coverage as live_cov  # noqa: E402

    class _LiveCoverageBase(WorldTestBase, _BaselineAssertions):
        """One subclass per option config (repo house style). num_regions PINNED in every config."""
        game = "Elden Ring"
        run_default_tests = False
        __test__ = False

        def test_live_coverage_baseline(self):
            records, ctx, byname = live_cov.report_coverage(world=self.world, printer=None)
            self.assert_baseline(live_cov, records, ctx, byname,
                                 f"live:{type(self).__name__}")
            # the live join must agree with the static join on the same kept scope
            s_records, s_ctx, s_byname = live_cov.report_coverage(kept=ctx["kept"], printer=None)
            self.assertEqual(sorted(records), sorted(s_records),
                             "live and static joins disagree on the emitted location set")

    class LiveCovAllRegions(_LiveCoverageBase):
        __test__ = True
        options = {"num_regions": 0}

    class LiveCovNR3Spine(_LiveCoverageBase):
        __test__ = True
        options = {"num_regions": 3, "num_regions_order": "spine"}

    class LiveCovNR5Spine(_LiveCoverageBase):
        __test__ = True
        options = {"num_regions": 5, "num_regions_order": "spine"}

    class LiveCovDlcOff(_LiveCoverageBase):
        __test__ = True
        options = {"num_regions": 0, "enable_dlc": False}

    class LiveCovDlcOnly(_LiveCoverageBase):
        __test__ = True
        options = {"num_regions": 0, "dlc_only": True}

    class LiveCovNR3BaseOnly(_LiveCoverageBase):
        __test__ = True
        options = {"num_regions": 3, "num_regions_order": "spine", "enable_dlc": False}


if __name__ == "__main__":
    unittest.main(verbosity=2)
