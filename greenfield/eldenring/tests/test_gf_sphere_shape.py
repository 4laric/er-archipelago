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
  * the real distribution is PRINTED on every run, so the first green CI log hands the next person
    the actual numbers to tighten these from.

Tighten them from that data. Do not guess them.

Why num_regions is large here: at 4 regions "spheres 0-1 are ~80% of a small seed" (see
test_gf_filler_economy_floor) -- almost everything is early by construction, so the shape carries no
information. The gradient only means something once the locks have something to gate.
"""
import collections

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

GAME = "Elden Ring"

# --- TRIPWIRES, not pins. See the module docstring before touching these. ---------------------
# "spheres collapsing to 1-2" is CONTRIBUTING's own phrasing for the regression, so 3 is the
# smallest number that is not the thing it warns about.
MIN_SPHERES = 3
# A ceiling loose enough that only "the whole map is open from the start" trips it. A healthy large
# seed should be FAR below this; if the printed number is anywhere near it, that is the finding.
MAX_SPHERE0_SHARE = 0.90
# One pinned seed, so a red run is reproducible (Generate.py picks a fresh seed each time, which is
# why this class of bug feels intermittent -- same reasoning as gen_sweep.ps1's pinned seeds).
SEED = 0x5F4E3


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
        print("\n[sphere-shape] %d spheres | %d own checks | sphere0 %d (%.1f%%)"
              % (len(spheres), total, counts[0], 100 * share0))
        print("[sphere-shape] checks per sphere:      %s" % counts[:24])
        print("[sphere-shape] progression per sphere: %s" % prog[:24])
        print("[sphere-shape] TRIPWIRES ARE LOOSE ON PURPOSE -- tighten MIN_SPHERES / "
              "MAX_SPHERE0_SHARE from these observed numbers, not from a guess.")

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

        self.world_setup(seed=SEED)
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
        print("\n[sphere-shape] own progression items: %d total, %d in sphere 0 (%.1f%%)"
              % (total_prog, prog[0], 100 * share0))
        self.assertLess(
            share0, 1.0,
            "EVERY progression item this world placed for itself sits in sphere 0 (%d of %d). "
            "Locations may be spread across %d spheres, but nothing is gated behind anything, so it "
            "plays as an open map. Per-sphere progression: %s"
            % (prog[0], total_prog, len(spheres), prog))
