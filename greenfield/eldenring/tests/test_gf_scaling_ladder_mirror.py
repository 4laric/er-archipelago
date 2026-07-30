"""Tier-B CROSS-REPO gate, runnable from SOURCE with no Archipelago install: the world's copy of the
enemy-scaling tier ladder must match the client's, and the percent->multiplier conversion built on it
must invert the client's own search exactly.

THE BUG THIS EXISTS FOR (found 2026-07-27, latent since 2026-07-06)

`completion_scaling_floor` is the difficulty FLOOR -- the hard-mode lever. The two sides spoke
DIFFERENT UNITS and neither said so:

    world   a Range documented as "a percent of max"; core._options_echo emitted the raw int
    client  er-logic/scaling.rs `floor_tier_from_multiplier` -- the FIRST tier whose `hp >= value`.
            An HP MULTIPLIER, over a ladder topping out at 3.703.

Every value above 3 selected the TOP tier. 46 of the old Range(0..50)'s 51 settings collapsed to one
outcome, and `completion_scaling_floor: 25` -- the obvious reading of a percent -- would have pinned
EVERY enemy in the game to 3.70x HP from the moment the player left Roundtable. Nothing crashed; the
knob simply meant something else. It never reached a player only because the option was frozen at 0.

And it was already KNOWN: `docs/history/RECON-tracker-scaling-20260706.md` line 171 states it
outright and prescribes the conversion as item 3 of five. The other four shipped. Item 3 did not, and
no gate was watching. That gap is what this file closes.

WHY THIS FILE IS STANDALONE (`python <this file>`), not pytest
It reads the CLIENT submodule source, which only exists in the repo tree -- the installed-world copy
under `<AP>/worlds/eldenring/` has no sibling `from-software-archipelago-clients/`. Same reason and
same shape as `test_gf_client_contract_paths.py`; both run in ci-linux.sh's "GREENFIELD (b) PURE
UNIT" step, from source. It imports only `scaling_ladder.py`, which is AP-free for exactly this.

WHAT IS GATED
  * the ladder mirror matches the Rust `SCALING_TIERS`, rung for rung;
  * the ladder is STRICTLY ASCENDING -- the premise that makes the round-trip exact;
  * every percent round-trips through the client's search to the tier it promises;
  * the pre-fix raw-percent emission still reproduces the top-tier inversion (rule 7: verify the fix
    by breaking it -- if this stops failing, the client changed and the fix needs re-deriving);
  * the Rust predicate is still `position(|t| t.hp >= floor_mult)`, so the local oracle cannot rot
    into agreement with a client that moved.
"""
import importlib.util
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GF_PKG = os.path.dirname(HERE)                    # .../greenfield/eldenring
REPO_ROOT = os.path.dirname(os.path.dirname(GF_PKG))
LADDER_PY = os.path.join(GF_PKG, "scaling_ladder.py")
ER_LOGIC_SCALING_RS = os.path.join(
    REPO_ROOT, "from-software-archipelago-clients", "crates", "er-logic", "src", "scaling.rs")


def _load_ladder():
    """Path-load `scaling_ladder.py` so this runs with no AP install and no package import."""
    spec = importlib.util.spec_from_file_location("gf_scaling_ladder_gate", LADDER_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _rust_ladder_hp(src):
    """The `hp:` rates of `SCALING_TIERS`, in declaration order, parsed from the Rust source."""
    m = re.search(r"pub const SCALING_TIERS:\s*&\[ScalingTier\]\s*=\s*&\[(.*?)\n\];", src, re.S)
    assert m, ("could not find `pub const SCALING_TIERS` in %s -- the ladder was renamed or moved. "
               "This gate is now BLIND; re-point it, do not delete it." % ER_LOGIC_SCALING_RS)
    return [float(x) for x in re.findall(r"\bhp:\s*([0-9.]+)", m.group(1))]


class ScalingLadderMirror(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(LADDER_PY):
            raise unittest.SkipTest("scaling_ladder.py absent (installed-world copy).")
        if not os.path.isfile(ER_LOGIC_SCALING_RS):
            raise unittest.SkipTest(
                "client crate absent (%s) -- this cross-repo gate needs the client submodule "
                "checked out (`git submodule update --init`). CI has it."
                % ER_LOGIC_SCALING_RS)
        cls.mod = _load_ladder()
        with open(ER_LOGIC_SCALING_RS, encoding="utf-8") as fh:
            cls.src = fh.read()
        cls.rust = _rust_ladder_hp(cls.src)

    def test_extractor_is_not_vacuous(self):
        # A regex that matched nothing must FAIL, not pass quietly (CONTRIBUTING rule 2: an empty
        # result is a failure). Without this the whole file goes green against an empty list.
        self.assertGreaterEqual(
            len(self.rust), 5,
            "parsed only %d hp rates out of SCALING_TIERS -- the extractor broke. A gate that "
            "measures nothing is a lie." % len(self.rust))

    def test_python_mirror_matches_the_rust_ladder(self):
        py = list(self.mod.SCALING_HP_LADDER)
        self.assertEqual(
            py, self.rust,
            "greenfield SCALING_HP_LADDER has DRIFTED from er-logic SCALING_TIERS.\n"
            "  python: %s\n  rust:   %s\n"
            "Every completion_scaling_floor a player sets is converted through the python copy, so "
            "a drifted rung silently moves their difficulty floor by a tier. Re-mirror it."
            % (py, self.rust))

    def test_ladder_is_strictly_ascending(self):
        """The round-trip is exact ONLY because of this: a `first hp >= rung` search recovers that
        rung's index only if no earlier rung is also >= it. Pin the premise, not just the result."""
        lad = self.mod.SCALING_HP_LADDER
        self.assertTrue(all(a < b for a, b in zip(lad, lad[1:])),
                        "ladder is not strictly ascending: %s" % (lad,))

    def test_rust_predicate_is_still_a_ge_search_over_hp(self):
        """`_floor_tier` below mirrors `position(|t| t.hp >= floor_mult)`. If the client changes that
        comparison the oracle would still agree with ITSELF while diverging from reality, so pin the
        shape at the source (CONTRIBUTING rule 8: what would make this guard pass while the bug is
        present?)."""
        m = re.search(r"pub fn floor_tier_from_multiplier\b.*?\n}", self.src, re.S)
        self.assertIsNotNone(
            m, "floor_tier_from_multiplier not found in er-logic/scaling.rs -- re-point this gate.")
        self.assertRegex(
            m.group(0), r"\.position\(\|t\|\s*t\.hp\s*>=\s*floor_mult\)",
            "the client's floor search is no longer `position(|t| t.hp >= floor_mult)`. The world's "
            "percent->multiplier conversion is built on that exact predicate -- re-derive "
            "scaling_ladder.floor_multiplier before updating this assertion.")

    # -- the client's search, restated locally as the oracle ------------------------------------
    def _floor_tier(self, floor_mult):
        for i, hp in enumerate(self.rust):        # the RUST ladder, deliberately: cross-check
            if hp >= floor_mult:
                return i
        return len(self.rust) - 1

    def test_every_percent_round_trips_to_the_tier_it_promises(self):
        top = len(self.rust) - 1
        for pct in (0, 1, 5, 10, 25, 33, 50, 66, 75, 90, 99, 100):
            with self.subTest(pct=pct):
                want = round(pct / 100 * top)
                got = self._floor_tier(self.mod.floor_multiplier(pct))
                self.assertEqual(
                    got, want,
                    "completion_scaling_floor: %d resolved to tier %d (%.3fx HP), expected tier %d "
                    "(%.3fx)." % (pct, got, self.rust[got], want, self.rust[want]))

    def test_the_motivating_case_and_the_inversion_it_replaced(self):
        """CONTRIBUTING rule 11: the case that motivated the work is the acceptance test."""
        top = len(self.rust) - 1
        got = self._floor_tier(self.mod.floor_multiplier(25))
        self.assertLess(
            got, top,
            "completion_scaling_floor: 25 reached the TOP tier -- that is the inversion this gate "
            "exists for, not a tuning question.")

        # Break the fix: replay the pre-2026-07-27 emission (the percent, straight through).
        self.assertEqual(
            self._floor_tier(25), top,
            "the OLD raw-percent emission no longer reproduces the top-tier inversion. The client's "
            "floor parse must have changed; re-derive this gate rather than relaxing it.")

    def test_default_stays_int_zero(self):
        """A yaml that never mentions the option must generate byte-identically to before it was
        reachable -- the pre-existing wire value was the int 0."""
        got = self.mod.floor_multiplier(0)
        self.assertEqual(got, 0)
        self.assertIsInstance(got, int,
                              "default floor must emit int 0, not %r" % (got,))

    def test_out_of_range_clamps(self):
        self.assertEqual(self.mod.floor_multiplier(-5), 0)
        self.assertEqual(self.mod.floor_multiplier(9999), self.mod.SCALING_HP_LADDER[-1])

    # ---- the RAMP (completion_scaling_ramp) -----------------------------------------------
    def test_default_ramp_is_the_linear_curve_it_replaced(self):
        """ramp 100 must be byte-identical to the old `round(i * TARGET_MAX / span)`. A yaml that
        never mentions the option generates exactly as before."""
        rt, MAX, span = self.mod.ramped_target, 10000, 16
        for i in range(span + 1):
            self.assertEqual(rt(i, span, MAX, 100), round(i * MAX / span), f"position {i}")

    def test_a_faster_ramp_saturates_early_and_never_lowers_the_max(self):
        """The whole reason this is expressible: the max emitted target STAYS at TARGET_MAX, so the
        client's re-normalization is unchanged and the tail simply sits on the top rung. Lowering
        the ceiling instead would be silently undone (see ramped_target's docstring)."""
        rt, MAX, span = self.mod.ramped_target, 10000, 16
        for pct in (25, 50, 75):
            vals = [rt(i, span, MAX, pct) for i in range(span + 1)]
            self.assertEqual(max(vals), MAX,
                             f"ramp {pct} lowered the max emitted target to {max(vals)} -- the "
                             f"client would renormalize it straight back and the option would be a "
                             f"silent no-op")
            self.assertTrue(all(a <= b for a, b in zip(vals, vals[1:])),
                            f"ramp {pct} is not monotonic: {vals}")
            # top tier reached at ~pct% of the way through, and flat after
            first_max = vals.index(MAX)
            self.assertAlmostEqual(first_max / span, pct / 100.0, delta=1.0 / span,
                                   msg=f"ramp {pct} hits max at position {first_max}/{span}")

    def test_a_faster_ramp_is_never_easier_than_a_slower_one(self):
        rt, MAX, span = self.mod.ramped_target, 10000, 16
        for i in range(span + 1):
            self.assertGreaterEqual(rt(i, span, MAX, 50), rt(i, span, MAX, 100))
            self.assertGreaterEqual(rt(i, span, MAX, 25), rt(i, span, MAX, 50))

    def test_ramp_clamps_and_survives_degenerate_spans(self):
        rt = self.mod.ramped_target
        self.assertEqual(rt(0, 0, 10000, 100), 0, "a one-region seed has no depth to ramp over")
        self.assertEqual(rt(5, 10, 10000, 0), rt(5, 10, 10000, 1), "ramp 0 clamps to 1")
        self.assertEqual(rt(5, 10, 10000, 500), rt(5, 10, 10000, 100), "ramp >100 clamps to 100")


class AutoDifficultyCeiling(unittest.TestCase):
    """`maximum_enemy_difficulty: auto` -- the cap derived from the LENGTH of the run.

    Enemy scaling is RELATIVE (a region's position in the unlock order, normalized so the deepest
    kept region tops out) while player power is ABSOLUTE (Somber +10 needs a Somber [9]). So a short
    seed reaches "the end of the run" against endgame-strength enemies with mid-game gear, and
    FEWER regions makes the ramp steeper. `auto` lowers the top of the curve instead.
    """

    @classmethod
    def setUpClass(cls):
        cls.mod = _load_ladder()

    def test_five_regions_is_the_old_cap_plus_exactly_one_rung(self):
        """THE MOTIVATING CASE, by name (CONTRIBUTING rule 11). Alaric playtested the pre-2026-07-27
        ladder -- which topped out at 3.703x -- and said of num_regions 5: "felt pretty close, if it
        was a bit harder we get there". So `auto` at 5 regions must land ONE rung above 3.703x."""
        m = self.mod
        ladder = m.SCALING_HP_LADDER
        old_top = 3.703
        self.assertIn(old_top, ladder, "the old ladder's top rung is gone from the ladder")
        old_rung = ladder.index(old_top)
        pct = m.auto_ceiling_pct(5, 30)
        got = m.ceiling_multiplier(pct)
        self.assertEqual(ladder.index(got), old_rung + 1,
                         "auto at 5 regions gave %.3fx (rung %d); the old cap was %.3fx (rung %d) "
                         "and 'a bit harder' means exactly one rung above it"
                         % (got, ladder.index(got), old_top, old_rung))

    def test_num_regions_zero_means_ALL_regions_not_none(self):
        """THE TRAP. core.NumRegions: "0 = all regions (full Shattering)". Read as zero, the cube root
        returns pct 0 -- the BOTTOM rung -- which would cap every enemy in a default seed at 1.141x
        and make the whole game trivial while looking like a tuning change."""
        m = self.mod
        self.assertEqual(m.auto_ceiling_pct(0, 30), 100,
                         "num_regions 0 must mean ALL regions, i.e. an uncapped run")
        self.assertEqual(m.ceiling_multiplier(m.auto_ceiling_pct(0, 30)), m.SCALING_HP_LADDER[-1])

    def test_a_full_map_is_unchanged(self):
        """No silent behaviour change for the seeds people already play: 30 of 30 is still uncapped."""
        m = self.mod
        self.assertEqual(m.auto_ceiling_pct(30, 30), 100)
        self.assertEqual(m.ceiling_multiplier(m.auto_ceiling_pct(30, 30)), m.SCALING_HP_LADDER[-1])

    def test_the_curve_is_monotonic_in_run_length(self):
        """A longer run may never be capped lower than a shorter one."""
        m = self.mod
        pcts = [m.auto_ceiling_pct(n, 30) for n in range(1, 31)]
        for a, b in zip(pcts, pcts[1:]):
            self.assertLessEqual(a, b, "auto is not monotonic: %r" % pcts)

    def test_multiplier_space_would_have_been_a_NO_OP(self):
        """WHY THE CURVE IS IN INDEX SPACE, pinned so nobody 'simplifies' it back.

        The client's search takes the last rung NO STRONGER than the value. The multiplier-space
        answer for 5 regions is 7.422 * (5/30)**(1/3) = 4.084x, which resolves DOWN to rung 9 --
        3.703x, the OLD cap. That version of this function would have shipped a change that did
        nothing at all and looked correct in review."""
        m = self.mod
        naive = m.SCALING_HP_LADDER[-1] * (5.0 / 30.0) ** (1.0 / 3.0)
        self.assertEqual(m.tier_for_ceiling_multiplier(naive),
                         m.SCALING_HP_LADDER.index(3.703),
                         "the multiplier-space target no longer collapses onto the old cap; if the "
                         "ladder changed, re-derive the curve rather than deleting this test")
        self.assertNotEqual(m.ceiling_multiplier(m.auto_ceiling_pct(5, 30)),
                            m.SCALING_HP_LADDER[m.tier_for_ceiling_multiplier(naive)])

    def test_auto_never_lands_below_an_explicit_floor(self):
        """The player typed the floor and did NOT type the ceiling, so the floor wins and generation
        proceeds. Failing a seed over a value nobody chose would be the wrong call."""
        m = self.mod
        self.assertEqual(m.resolve_max_difficulty_pct(m.AUTO_CEILING, 5, 30, 80), 80)
        self.assertEqual(m.resolve_max_difficulty_pct(m.AUTO_CEILING, 5, 30, 0),
                         m.auto_ceiling_pct(5, 30))

    def test_explicit_values_pass_straight_through(self):
        m = self.mod
        for pct in (0, 25, 50, 75, 100):
            self.assertEqual(m.resolve_max_difficulty_pct(pct, 5, 30, 0), pct)

    def test_the_sentinel_can_never_be_read_as_a_percent(self):
        m = self.mod
        self.assertTrue(m.AUTO_CEILING < 0, "auto must sit outside 0..100")

    def test_a_nonsense_total_raises_instead_of_answering(self):
        """A derivation that cannot answer must FAIL, not answer (CONTRIBUTING rule 1)."""
        m = self.mod
        for bad in (0, -3):
            with self.assertRaises(ValueError):
                m.auto_ceiling_pct(5, bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)
