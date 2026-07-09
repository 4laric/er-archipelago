"""Tier-A COVERAGE GATE test (WorldTestBase-free -- uses AP's setup_multiworld, needs AP + Py3.11).

Runs `coverage.build_coverage` + all three checks over an OPTION MATRIX (dlc on/off/only, missable
on/off, num_regions PINNED to explicit values -- never the default, per house rule) and asserts the
gate RUNS and produces the STABLE, EXPECTED baseline of violations. The coverage invariant is
seed-invariant (every input is a generated table + the kept-region scope), so:

  * the LIVE matrix builds a real world through AP's gen steps (stopping at pre_fill -- no flaky
    multiworld fill), then joins its emitted slot_data;
  * the STATIC-SCOPED matrix pins the exact kept set each num_regions/DLC combo produces and joins
    the generated source files directly (no AP world needed).

Baseline THIS tree (encode it so a regression that ADDS an uncovered location fails here):
  * detection / suppression / quarantine violations: **0** in every scope.
  * region violations: exactly the ONE known Stormveil open-flag gap (bogus flag 200, memory
    gf-legacy-dungeon-open-flag-gap) -- present iff Stormveil Castle is in the kept scope, else 0.
  * static full pool: 3915 emitted locations, 1 region violation.

If gen_data ever allocates a real Stormveil open flag, BASELINE_STATIC_REGION_VIOLATIONS drops to 0
and this test's Stormveil assertions must be updated (the gate then guards a clean tree). A NEW hole
(a detection/suppression/cross-file/region regression) makes one of the ==[] assertions fail.

importorskips AP + the installed world, so it is a no-op in the bare source-tree sandbox and runs
once the world is installed under Archipelago/worlds/ (ci-linux.sh / the provisioned env).

Run (from the Archipelago dir, world installed):
    python -m pytest worlds/eldenring_gf/tests/test_coverage_gate.py
"""
import random
import unittest

import pytest

_general = pytest.importorskip("test.general")
pytest.importorskip("worlds.eldenring_gf")
from worlds.AutoWorld import AutoWorldRegister  # noqa: E402
from worlds.eldenring_gf import coverage, coverage_quarantine, region_spine  # noqa: E402

setup_multiworld = _general.setup_multiworld
gen_steps = _general.gen_steps
GAME = "Elden Ring (Greenfield)"
WT = AutoWorldRegister.world_types[GAME]
STORMVEIL = "Stormveil Castle"

# --- the encoded baseline (this tree) ---------------------------------------------------------
BASELINE_TOTAL_LOCATIONS = 3915
BASELINE_STATIC_REGION_VIOLATIONS = 1          # only Stormveil open flag 200


def _live_world(options, seed=1234):
    """Build a real greenfield world through the gen steps (pre_fill inclusive; NO main fill, so this
    can't hit the ~1-in-N fill flakiness) and return it."""
    mw = setup_multiworld(WT, gen_steps, seed=seed, options=options)
    return mw.worlds[1]


class CoverageGate(unittest.TestCase):
    # ------------------------------------------------------------------ shared assertion
    def _assert_baseline(self, records, ctx, byname, label):
        self.assertGreater(len(records), 0, f"{label}: no emitted locations")
        self.assertEqual([v.detail for v in byname["detection"]], [],
                         f"{label}: detection must be clean (a new uncovered location leaked in)")
        self.assertEqual([v.detail for v in byname["suppression"]], [],
                         f"{label}: suppression must be clean (a ware lost its suppressor)")
        self.assertEqual([v.detail for v in byname["quarantine"]], [],
                         f"{label}: degradation ledger must be clean/self-consistent")
        kept = set(ctx["kept"])
        reg = byname["region"]
        for v in reg:
            self.assertIn("Stormveil", v.detail,
                          f"{label}: unexpected region violation (not the known Stormveil gap): {v.detail}")
        self.assertEqual(len(reg), 1 if STORMVEIL in kept else 0,
                         f"{label}: region violations must be exactly the Stormveil gap when kept, "
                         f"else 0 (kept has Stormveil={STORMVEIL in kept}); got {[v.detail for v in reg]}")

    # ------------------------------------------------------------------ static full pool
    def test_static_full_pool_baseline_snapshot(self):
        records, ctx, byname = coverage.report_coverage(world=None, printer=None)
        self.assertEqual(len(records), BASELINE_TOTAL_LOCATIONS,
                         "full-pool emitted-location count drifted -- update BASELINE_TOTAL_LOCATIONS "
                         "(and confirm the new locations are covered)")
        self.assertEqual(len(byname["region"]), BASELINE_STATIC_REGION_VIOLATIONS,
                         "static region-violation count drifted from the encoded baseline")
        self._assert_baseline(records, ctx, byname, "static-full")

    # ------------------------------------------------------------------ LIVE option matrix
    def test_live_option_matrix(self):
        matrix = [
            ({}, "default(all,dlc-on)"),
            ({"num_regions": 3, "num_regions_order": "spine"}, "nr3-spine"),
            ({"num_regions": 5, "num_regions_order": "spine"}, "nr5-spine"),
            ({"enable_dlc": False}, "dlc-off"),
            ({"dlc_only": True}, "dlc-only"),
            ({"protect_missable_locations": False}, "missable-off"),
            ({"protect_missable_locations": True}, "missable-on"),
            ({"num_regions": 3, "num_regions_order": "spine", "enable_dlc": False}, "nr3-baseonly"),
        ]
        for opts, label in matrix:
            with self.subTest(config=label):
                world = _live_world(opts)
                records, ctx, byname = coverage.report_coverage(world=world, printer=None)
                self._assert_baseline(records, ctx, byname, "live:" + label)

    # ------------------------------------------------------------------ STATIC-SCOPED matrix
    def test_static_scoped_option_matrix(self):
        rng = random.Random(0xC0FFEE)
        pools = {
            "all": list(region_spine.REGIONS),
            "base": region_spine.base_regions(),
            "dlc": region_spine.dlc_regions(),
        }
        for pool_name, pool in pools.items():
            for n in (0, 3, 5):
                kept = region_spine.compute_kept(n, "spine", rng, eligible=pool)
                label = f"{pool_name}-nr{n}"
                with self.subTest(config=label):
                    records, ctx, byname = coverage.report_coverage(world=None, kept=kept, printer=None)
                    self._assert_baseline(records, ctx, byname, "scoped:" + label)

    # ------------------------------------------------------------------ stability across an axis
    def test_missable_axis_is_scope_invariant(self):
        a = _live_world({"protect_missable_locations": True})
        b = _live_world({"protect_missable_locations": False})
        # missable toggles progression-forbidding, NOT which locations/flags are emitted, so the
        # coverage join (emitted set + detect_flag + region) must be identical across the axis.
        reca, _ = coverage.build_coverage(a)
        recb, _ = coverage.build_coverage(b)
        self.assertEqual(sorted(reca), sorted(recb), "missable changed the emitted location set")
        for ap in reca:
            self.assertEqual(reca[ap].detect_flag, recb[ap].detect_flag,
                             f"missable changed detect_flag for {ap}")
            self.assertEqual(reca[ap].region, recb[ap].region,
                             f"missable changed region for {ap}")

    # ------------------------------------------------------------------ degradation ledger
    def test_quarantine_ledger_is_wellformed(self):
        self.assertEqual(coverage_quarantine.validate_ledger(), [],
                         "coverage_quarantine ledger is malformed")

    def test_accepted_leak_self_cleans_when_suppressable(self):
        """An ACCEPTED_LEAK for a location that is actually suppressable must make the gate say
        'remove it' (the ledger cannot rot into a permanent excuse)."""
        records, ctx = coverage.build_coverage(world=None)
        # pick a real emitted filler location that IS suppressable (client_intercept) and filler.
        target = next(r for r in records.values()
                      if r.suppress_kind == "client_intercept" and r.is_filler is True)
        saved = dict(coverage_quarantine.ACCEPTED_LEAKS)
        try:
            coverage_quarantine.ACCEPTED_LEAKS.clear()
            coverage_quarantine.ACCEPTED_LEAKS[target.ap_id] = {
                "reason": "test injected", "issue": "TEST", "date": "2026-07-08"}
            byname = coverage.all_checks(records, ctx)
            hits = [v for v in byname["quarantine"] if v.ap_id == target.ap_id]
            self.assertTrue(hits, "a suppressable ACCEPTED_LEAK must be reported for removal")
            self.assertIn("remove", hits[0].detail.lower())
        finally:
            coverage_quarantine.ACCEPTED_LEAKS.clear()
            coverage_quarantine.ACCEPTED_LEAKS.update(saved)

    def test_quarantine_self_cleans_when_emitted_and_passing(self):
        """A QUARANTINE entry (promised excluded) that is STILL emitted and passes every check must be
        reported for removal."""
        records, ctx = coverage.build_coverage(world=None)
        # any emitted location that passes all checks (not the Stormveil region-level violation).
        clean = coverage.all_checks(records, ctx)
        flagged = {v.ap_id for lst in clean.values() for v in lst}
        target = next(r for r in records.values() if r.ap_id not in flagged)
        saved = dict(coverage_quarantine.QUARANTINE)
        try:
            coverage_quarantine.QUARANTINE.clear()
            coverage_quarantine.QUARANTINE[target.ap_id] = {
                "reason": "test injected", "issue": "TEST", "date": "2026-07-08"}
            byname = coverage.all_checks(records, ctx)
            hits = [v for v in byname["quarantine"] if v.ap_id == target.ap_id]
            self.assertTrue(hits, "an emitted+passing QUARANTINE entry must be reported for removal")
            self.assertIn("remove", hits[0].detail.lower())
        finally:
            coverage_quarantine.QUARANTINE.clear()
            coverage_quarantine.QUARANTINE.update(saved)


if __name__ == "__main__":
    unittest.main(verbosity=2)
