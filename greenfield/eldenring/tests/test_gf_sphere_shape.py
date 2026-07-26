"""SPHERE SHAPE -- a tripwire for "it genned" not meaning "it plays".

CONTRIBUTING, *Progression shape -- not a billion checks in sphere 0*:

    A seed that generates and is winnable can still be a bad seed. If sphere 0 holds a huge share of
    the checks, there's no progression gradient -- the whole game is effectively open from the start,
    locks aren't doing their job, and the multiworld has nothing to hand out over time. "It genned"
    does not mean "it plays." ... Treat a sudden jump in sphere-0 check count (or spheres collapsing
    to 1-2) as a regression to explain, the same way you'd treat a FillError.

Nothing enforced that. `run_ci.ps1` runs UNIT, FILL (run_fill_regression -> gen_sweep over the
reproducer yamls), DIVERSITY, FRESHNESS, TRACKER DRIFT, GREENFIELD, FUZZ and PURE -- and every one of
them asks whether a seed GENERATES. None looks at what its spheres look like. The sphere dump
CONTRIBUTING points at (`ER_DUMP_SPHERES`) does not exist in the tree; it is named in that document
and nowhere else. So the shape has only ever been checked by a human remembering to look.

This file is the tripwire. It rides the apworld suite, so it runs in GitHub CI on every push --
no PowerShell, no artifacts, no one's box.

⚠️ THE THRESHOLDS BELOW ARE DELIBERATELY LOOSE, AND THAT IS NOT LAZINESS.
A tight pin has to come from OBSERVED numbers across seeds, and the agent that wrote this could not
run an AP generation (the sandbox cannot provision the runtime). Inventing a precise-looking bound
from nothing is exactly the "confident wrong answer" this project keeps paying for -- a fabricated
floor would fail honest seeds and get raised until it meant nothing. So:

  * the ASSERTIONS only catch a collapse -- the disaster CONTRIBUTING names in so many words;
  * the real distribution is REPORTED on every run, so a green CI log hands the next person the
    actual numbers to tighten these from.

    ⚠️ It is reported through `warnings.warn`, NOT print, and that is deliberate: pytest CAPTURES
    stdout for a PASSING test, so the first version of this file printed its numbers into a void --
    the whole point of the loose thresholds, lost, and I had already claimed in a commit message
    that the log would carry them. The warnings summary is the one channel pytest always prints.
    `print` is kept as well for anyone running with -s.

Tighten them from that data. Do not guess them.

Why num_regions is large here: at 4 regions "spheres 0-1 are ~80% of a small seed" (see
test_gf_filler_economy_floor) -- almost everything is early by construction, so the shape carries no
information. The gradient only means something once the locks have something to gate.
"""
import warnings

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

GAME = "Elden Ring"

# --- TRIPWIRES, now CALIBRATED FROM OBSERVED CI RUNS (see the module docstring) ----------------
# First green run of this file (e58a661, num_regions 12, seed 0x5F4E3) reported:
#     7 spheres | 2690 own checks | sphere0 562 (20.9%)
#     checks/sphere      [562, 145, 265, 379, 812, 375, 152]
#     own progression 15 | sphere0 2 (13.3%) | per-sphere [2, 2, 2, 5, 3, 1, 0]
# That is a healthy gradient, and it is what these bounds are set against -- not a guess.
#
# ⚠️ TIGHTENED CONSERVATIVELY, because this is TWO seeds, not a distribution. "It genned on my one
# yaml" is the failure this project names; two is not much better. MIN_SPHERES is set well under the
# observed 7 and MAX_SPHERE0_SHARE at ~2.4x the observed share, so ordinary seed variance cannot trip
# them while a genuine collapse still does. Tighten further only from more seeds -- the numbers are
# in every CI log under 'sphere-shape'.
MIN_SPHERES = 4


class SphereShapeReport(UserWarning):
    """Carries the observed distribution into pytest's warnings summary, where a PASSING run can
    still show it. Grep CI for 'sphere-shape'."""


def _report(msg):
    print(msg)
    warnings.warn(msg, SphereShapeReport, stacklevel=2)

# Observed 20.9%. At >50% the map is effectively open from the start, which is the regression
# CONTRIBUTING describes; below that, seed variance has room.
MAX_SPHERE0_SHARE = 0.50
# One pinned seed, so a red run is reproducible (Generate.py picks a fresh seed each time, which is
# why this class of bug feels intermittent -- same reasoning as gen_sweep.ps1's pinned seeds).
SEED = 0x5F4E3        # sphere/location shape
SEED_B = 0xA11CE      # the item-side test uses a DIFFERENT seed, so the pair samples TWO worlds
                      # for the price of the fills we were already doing


class SphereShape(WorldTestBase):
    game = GAME
    # A real seed with real locks: the gradient is only observable where regions actually gate.
    options = {"num_regions": 12, "num_regions_order": "rolled", "item_shuffle": True}

    def test_the_seed_has_a_midgame(self):
        from Fill import distribute_items_restrictive

        self.world_setup(seed=SEED)
        distribute_items_restrictive(self.multiworld)
        player = self.world.player

        spheres = [set(s) for s in self.multiworld.get_spheres()]
        self.assertTrue(spheres, "no fill spheres at all -- the seed has no reachability structure")

        mine = [{l for l in s if getattr(l, "player", None) == player} for s in spheres]
        counts = [len(s) for s in mine]
        total = sum(counts)
        self.assertGreater(total, 0, "no own locations in any sphere -- the oracle is broken")

        # progression items per sphere: a gradient is items ARRIVING over time, not just locations
        prog = []
        for s in mine:
            prog.append(sum(1 for l in s
                            if l.item is not None and l.item.player == player and l.item.advancement))

        share0 = counts[0] / total
        _report("[sphere-shape] %d spheres | %d own checks | sphere0 %d (%.1f%%) | "
                "checks/sphere %s | progression/sphere %s | bounds are calibrated from 2 seeds: "
                "tighten MIN_SPHERES / MAX_SPHERE0_SHARE from MORE of these, never from a guess"
                % (len(spheres), total, counts[0], 100 * share0, counts[:24], prog[:24]))

        self.assertGreaterEqual(
            len(spheres), MIN_SPHERES,
            "the seed collapsed to %d sphere(s): everything is reachable at once, so the locks are "
            "gating nothing and the multiworld has nothing to hand out over time. CONTRIBUTING calls "
            "this out by name -- treat it like a FillError. Checks per sphere: %s"
            % (len(spheres), counts))
        self.assertLessEqual(
            share0, MAX_SPHERE0_SHARE,
            "sphere 0 holds %.1f%% of this world's %d checks (%d of them). The map is effectively "
            "open from the start -- a lock has probably spilled to start inventory, or the region "
            "graph is rooted so everything hangs off the first region. Checks per sphere: %s"
            % (100 * share0, total, counts[0], counts))

    def test_progression_is_not_all_in_the_first_sphere(self):
        """A gradient needs ITEMS arriving over time, not just locations existing later.

        Locations can spread across spheres while every progression item still sits in sphere 0 --
        which plays exactly like an open map. This is the same measurement from the item side.
        """
        from Fill import distribute_items_restrictive

        self.world_setup(seed=SEED_B)
        distribute_items_restrictive(self.multiworld)
        player = self.world.player

        spheres = [set(s) for s in self.multiworld.get_spheres()]
        prog = []
        for s in spheres:
            prog.append(sum(1 for l in s
                            if getattr(l, "player", None) == player and l.item is not None
                            and l.item.player == player and l.item.advancement))
        total_prog = sum(prog)
        if total_prog == 0:
            self.skipTest("no own progression items placed in own locations -- nothing to shape")
        share0 = prog[0] / total_prog
        _report("[sphere-shape] own progression items: %d total, %d in sphere 0 (%.1f%%) | "
                "per-sphere %s" % (total_prog, prog[0], 100 * share0, prog[:24]))
        self.assertLess(
            share0, 1.0,
            "EVERY progression item this world placed for itself sits in sphere 0 (%d of %d). "
            "Locations may be spread across %d spheres, but nothing is gated behind anything, so it "
            "plays as an open map. Per-sphere progression: %s"
            % (prog[0], total_prog, len(spheres), prog))
