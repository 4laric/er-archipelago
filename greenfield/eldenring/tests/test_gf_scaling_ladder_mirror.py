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
LADDER_PY = os.path.join(GF_PKG, "scaling_ladder.py")


def _find_up(rel, start):
    """Walk UP for `rel` (the find_repo_root idiom, _util.py). Resolved POSITIONALLY ("N dirs up")
    this path pointed into _ap/worlds under the installed-world harness, so the gate skipped there
    forever -- in the CI `tests` job too, where the thing it needs sits a directory higher
    (2026-08-04 inert-test audit, finding #3)."""
    d = os.path.abspath(start)
    for _ in range(8):
        cand = os.path.join(d, rel)
        if os.path.exists(cand):
            return cand
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    return None


_SCALING_RS_REL = os.path.join(
    "from-software-archipelago-clients", "crates", "er-logic", "src", "scaling.rs")
ER_LOGIC_SCALING_RS = _find_up(_SCALING_RS_REL, HERE) or _SCALING_RS_REL


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

    def test_five_regions_sits_ON_the_playtested_rung(self):
        """THE MOTIVATING CASE, by name (CONTRIBUTING rule 11). Alaric playtested the pre-2026-07-27
        ladder -- which topped out at 3.703x -- and said of num_regions 5: "felt pretty close". The
        first curve put 5 regions one rung ABOVE that on purpose; then the region total moved from
        30 to 28 and pushed it up a second rung, to 4.844x, with nothing to say so. Recalibrated
        2026-09-06: `auto` at 5 regions lands exactly on the playtested rung, against the LIVE
        total -- pinned at both 28 and 30 so a moving total cannot silently re-tune the datum."""
        m = self.mod
        ladder = m.SCALING_HP_LADDER
        old_top = 3.703
        self.assertIn(old_top, ladder, "the old ladder's top rung is gone from the ladder")
        old_rung = ladder.index(old_top)
        for total in (28, 30):
            got = m.ceiling_multiplier(m.auto_ceiling_curve_pct(5, total))
            self.assertEqual(ladder.index(got), old_rung,
                             "auto at 5 of %d regions gave %.3fx (rung %d); the playtested cap is "
                             "%.3fx (rung %d)" % (total, got, ladder.index(got), old_top, old_rung))

    def test_the_recalibrated_table_against_the_live_total(self):
        """The whole 2026-09-06 table, so 'a scosh down' is a number and not a memory. 10 regions
        used to resolve to 6.563x, almost 90% of the full-map cap after a third of the map."""
        m = self.mod
        want = {5: 3.703, 10: 5.484, 15: 6.688, 20: 7.047, 28: 7.422}
        got = {n: m.ceiling_multiplier(m.auto_ceiling_curve_pct(n, 28)) for n in want}
        self.assertEqual(got, want)

    def test_num_regions_zero_means_ALL_regions_not_none(self):
        """THE TRAP. core.NumRegions: "0 = all regions (full Shattering)". Read as zero, the cube root
        returns pct 0 -- the BOTTOM rung -- which would cap every enemy in a default seed at 1.141x
        and make the whole game trivial while looking like a tuning change."""
        m = self.mod
        self.assertEqual(m.auto_ceiling_curve_pct(0, 30), 100,
                         "num_regions 0 must mean ALL regions, i.e. an uncapped run")
        self.assertEqual(m.ceiling_multiplier(m.auto_ceiling_curve_pct(0, 30)), m.SCALING_HP_LADDER[-1])

    def test_a_full_map_is_unchanged(self):
        """No silent behaviour change for the seeds people already play: 30 of 30 is still uncapped."""
        m = self.mod
        self.assertEqual(m.auto_ceiling_curve_pct(30, 30), 100)
        self.assertEqual(m.ceiling_multiplier(m.auto_ceiling_curve_pct(30, 30)), m.SCALING_HP_LADDER[-1])

    def test_the_curve_is_monotonic_in_run_length(self):
        """A longer run may never be capped lower than a shorter one."""
        m = self.mod
        pcts = [m.auto_ceiling_curve_pct(n, 30) for n in range(1, 31)]
        for a, b in zip(pcts, pcts[1:]):
            self.assertLessEqual(a, b, "auto is not monotonic: %r" % pcts)

    def test_multiplier_space_is_not_the_same_curve(self):
        """WHY THE CURVE IS IN INDEX SPACE, pinned so nobody 'simplifies' it back.

        The client's search takes the last rung NO STRONGER than the value, so a curve computed in
        multiplier space resolves DOWN through that search. Over the live total it disagrees with
        the index-space curve at more than one run length; a rewrite that lands on the multiplier
        answer everywhere has changed the difficulty of every short seed while looking equivalent."""
        m = self.mod
        top = m.SCALING_HP_LADDER[-1]
        differ = 0
        for n in range(1, 29):
            naive = top * (n / 28.0) ** m.AUTO_CEILING_EXPONENT
            if m.ceiling_multiplier(m.auto_ceiling_curve_pct(n, 28)) !=                     m.SCALING_HP_LADDER[m.tier_for_ceiling_multiplier(naive)]:
                differ += 1
        self.assertGreater(differ, 3, "the index-space and multiplier-space curves now coincide; "
                                      "re-derive the curve rather than deleting this test")

    def test_rounding_is_half_up_like_the_wizards_Math_round(self):
        """The wizard previews this curve in JavaScript. Python's round() is half-to-even and
        Math.round is half-up; at an exact .5 they disagree by a whole percent, and one percent can
        be a rung. The formula therefore rounds half-up by hand: 100 * (n/total)**k hits exactly
        .5 only by coincidence, so pin the direction on a synthetic case instead."""
        m = self.mod
        import math
        # Find any n/total whose raw value sits within 1e-9 of .5 and check it went UP; failing
        # that, assert the implementation is floor(x + 0.5) against a direct evaluation.
        for total in range(1, 61):
            for n in range(1, total + 1):
                raw = 100.0 * (n / total) ** m.AUTO_CEILING_EXPONENT
                self.assertEqual(m.auto_ceiling_curve_pct(n, total), int(math.floor(raw + 0.5)))

    def test_auto_never_lands_below_an_explicit_floor(self):
        """The player typed the floor and did NOT type the ceiling, so the floor wins and generation
        proceeds. Failing a seed over a value nobody chose would be the wrong call."""
        m = self.mod
        self.assertEqual(m.resolve_max_difficulty_pct(m.AUTO_CEILING, 5, 30, 80, True), 80)
        self.assertEqual(m.resolve_max_difficulty_pct(m.AUTO_CEILING, 5, 30, 0, True),
                         m.auto_ceiling_pct(5, 30, True))

    def test_explicit_values_pass_straight_through(self):
        m = self.mod
        for pct in (0, 25, 50, 75, 100):
            for blessed in (False, True):
                self.assertEqual(m.resolve_max_difficulty_pct(pct, 5, 30, 0, blessed), pct)

    def test_the_sentinel_can_never_be_read_as_a_percent(self):
        m = self.mod
        self.assertTrue(m.AUTO_CEILING < 0, "auto must sit outside 0..100")

    def test_a_nonsense_total_raises_instead_of_answering(self):
        """A derivation that cannot answer must FAIL, not answer (CONTRIBUTING rule 1)."""
        m = self.mod
        for bad in (0, -3):
            with self.assertRaises(ValueError):
                m.auto_ceiling_curve_pct(5, bad)


class WizardPreviewMirrorTests(unittest.TestCase):
    """wizard/wizard.html previews the cap in JavaScript from its OWN copy of the ladder and the
    `auto` exponent (ERW.scalingPreview). A re-tuned curve that leaves the page behind shows the
    player one rung and gives them another, silently -- so the page's constants are parsed here
    against the Python source. AP-free, like the rest of this file."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load_ladder()
        p = _find_up(os.path.join("wizard", "wizard.html"), HERE)
        cls.html = open(p, encoding="utf-8").read() if p else None

    def test_the_wizards_ladder_is_the_python_ladder(self):
        if self.html is None:
            self.skipTest("wizard/wizard.html not beside the source tree")
        m = re.search(r"const SCALING_HP_LADDER = \[([^\]]+)\];", self.html)
        self.assertIsNotNone(m, "wizard.html no longer carries SCALING_HP_LADDER")
        js = tuple(float(x) for x in m.group(1).replace("\n", " ").split(","))
        self.assertEqual(js, self.mod.SCALING_HP_LADDER)

    def test_the_wizards_exponent_is_the_python_exponent(self):
        if self.html is None:
            self.skipTest("wizard/wizard.html not beside the source tree")
        m = re.search(r"const AUTO_CEILING_EXPONENT = ([0-9.]+);", self.html)
        self.assertIsNotNone(m, "wizard.html no longer carries AUTO_CEILING_EXPONENT")
        self.assertEqual(float(m.group(1)), self.mod.AUTO_CEILING_EXPONENT)

    def test_the_two_roundings_agree_over_every_run_length(self):
        """JS Math.round is half-up; the Python side rounds half-up by hand. Evaluate the JS formula
        as written, in Python, and compare -- no node needed."""
        import math
        m = self.mod
        for total in (28, 30):
            for n in range(0, total + 1):
                nn = total if n <= 0 else min(n, total)
                js = math.floor(100 * (nn / total) ** m.AUTO_CEILING_EXPONENT + 0.5)
                self.assertEqual(m.auto_ceiling_curve_pct(n, total), js, (n, total))


class BaseGameGateTests(unittest.TestCase):
    """THE GATE (Alaric, 2026-09-06): `auto` is the base game's top unless the Scadutree Blessing
    applies everywhere and its fragments can enter the pool. 0xtako's 13-region default run met
    Caelid at Haligtree strength; the rungs above 3.703x are the DLC's ladder and assume a blessing."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load_ladder()

    def test_the_base_game_top_is_derived_not_chosen(self):
        """47 is the LARGEST percent that still resolves to 3.703x; 48 would be the same rung, and
        the constant is pinned to the boundary so the ladder rounding cannot drift under it."""
        m = self.mod
        top = m.SCALING_HP_LADDER.index(3.703)
        self.assertEqual(m.tier_for_ceiling_multiplier(m.ceiling_multiplier(m.BASE_GAME_CEILING_PCT)), top)
        # the first DLC rung is the next rung up, and 50 reaches it
        self.assertEqual(m.tier_for_ceiling_multiplier(m.ceiling_multiplier(50)), top + 1)

    def test_without_dlc_rungs_eligible_auto_is_flat_at_the_base_game_top(self):
        m = self.mod
        for n in (0, 1, 5, 13, 28):
            self.assertEqual(m.auto_ceiling_pct(n, 28, False), m.BASE_GAME_CEILING_PCT, n)
            self.assertEqual(m.ceiling_multiplier(m.auto_ceiling_pct(n, 28, False)), 3.703)

    def test_with_dlc_rungs_eligible_auto_follows_the_curve_from_the_base_game_top(self):
        m = self.mod
        for n in range(1, 29):
            self.assertEqual(m.auto_ceiling_pct(n, 28, True),
                             max(m.BASE_GAME_CEILING_PCT, m.auto_ceiling_curve_pct(n, 28)), n)
        self.assertEqual(m.auto_ceiling_pct(0, 28, True), 100, "a whole map with the blessing is uncapped")
        self.assertEqual(m.auto_ceiling_pct(1, 28, True), m.BASE_GAME_CEILING_PCT,
                         "the curve never drops a blessed seed below the base-game top")

    def test_base_game_target_cap_holds_under_both_client_formulas(self):
        """For every band the seed can hold, a target at the cap lands on BASE_GAME_TOP_TIER or
        lower under the band formula (clients since 2026-08-08) AND the older whole-ladder
        formula; one target above the cap does not, so the cap is tight, not merely safe."""
        m = self.mod
        n_top = len(m.SCALING_HP_LADDER) - 1
        top = m.BASE_GAME_TOP_TIER
        mx = 10000
        band = lambda t, f, c: min(f + round(t / mx * (c - f)), c)
        ladder = lambda t, f, c: min(max(round(t / mx * n_top), f), c)
        for c in range(0, n_top + 1):
            for f in range(0, c + 1):
                cap = m.base_game_target_cap(mx, f, c)
                if c <= top:
                    self.assertEqual(cap, mx, (f, c))
                    continue
                if f >= top:
                    self.assertEqual(cap, 0, (f, c))
                    continue
                self.assertLessEqual(band(cap, f, c), top, (f, c, cap))
                self.assertLessEqual(ladder(cap, f, c), top, (f, c, cap))
                # TIGHT TO WITHIN ONE RUNG-STEP, rounding-mode-agnostic: the cap is an integer
                # floor, so a target one above it can still round down, and Python rounds an
                # exact .5 to even where Rust rounds it away from zero. One full step above the
                # cap the RAW product clears top + 0.5 under at least one formula, so any
                # rounding lands on a DLC rung there.
                step = mx // min(c - f, n_top) + 1
                over = cap + step
                raw_band = f + over / mx * (c - f)
                raw_ladder = over / mx * n_top
                self.assertTrue(raw_band > top + 0.5 or raw_ladder > top + 0.5,
                                "cap %d is not tight for band (%d, %d)" % (cap, f, c))

    def test_the_motivating_thirteen_region_run(self):
        """13 of 28 with the DLC and the blessing everywhere still climbs (fragments are injected
        for it); the same yaml with the DLC off is vanilla Haligtree, not 6.56x."""
        m = self.mod
        self.assertEqual(m.ceiling_multiplier(m.auto_ceiling_pct(13, 28, True)), 6.563)
        self.assertEqual(m.ceiling_multiplier(m.auto_ceiling_pct(13, 28, False)), 3.703)


if __name__ == "__main__":
    unittest.main(verbosity=2)
