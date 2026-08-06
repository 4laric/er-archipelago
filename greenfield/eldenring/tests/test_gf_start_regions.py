"""start_regions -- N opening regions instead of one (features/start_grace.pick_anchor_regions).

MOTIVATING CASE (CONTRIBUTING rule 11). boblerrr, 2026-08-06: "is there an option to start with
more than 1 region unlocked?" There was not: `start_with_region_lock` precollected exactly one
Region Lock and `pick_anchor_region` returned exactly one region.

What this guards, and why each one is here rather than assumed:
  * n == 1 IS THE OLD DRAW -- same region AND the same rng stream afterwards. Every defaulted seed
    in the wild must keep rolling identically, and an extra rng call inside the n == 1 path would
    silently reroll everything downstream of it. region_spine appends GOAL_REGION AFTER its
    rng.sample for exactly this reason; the same discipline applies here.
  * the goal region may still win the FIRST draw (that behaviour shipped, and at one anchor it is
    rare) but is NEVER an extra -- a run that opens on the region it ends in is not a run.
  * gated children (region_spine.REGION_PARENT) can never anchor at ANY n: their grace bundle is
    withheld by features/graces, so the player could not warp into one.
  * a pool that cannot supply n fails LOUDLY at both levels -- OptionError from core naming the
    yaml, ValueError from the picker naming the exclusions that bound cannot see.
  * count-neutrality survives n locks leaving the pool, and the goal stops requiring the locks the
    player is already holding.
  * every opening region is fill sphere 0, so the scaling ramp starts from the whole opening rather
    than from one region of it.

Expectations are DERIVED from data.LOCATIONS / region_spine at test time -- no hand-pinned region
sizes to rot when a re-tag moves checks between regions.

PIN num_regions in every world built here -- an unpinned num_regions is a known test-breaker.

Run (from the Archipelago dir, world installed):
    python -m pytest worlds/eldenring/tests/test_gf_start_regions.py
"""
import logging
import random
import unittest

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from Options import OptionError                                                 # noqa: E402
from worlds.eldenring.data import HUB, REGIONS, LOCATIONS                       # noqa: E402
from worlds.eldenring.region_spine import (  # noqa: E402
    DLC_REGIONS, GOAL_REGION, REGION_PARENT)
from worlds.eldenring.features.start_grace import (  # noqa: E402
    StartRegions, pick_anchor_region, pick_anchor_regions)
from worlds.eldenring.features.progression_surface import lock_region_name      # noqa: E402
from ._util import world_pool_items                                             # noqa: E402

GAME = "Elden Ring"

# The SAME derivation core.create_items feeds the picker (provenance: derive, don't pin).
COUNTS = {r: len(LOCATIONS.get(r, [])) for r in REGIONS}
BASE_KEPT = [r for r in REGIONS if r not in DLC_REGIONS and r not in REGION_PARENT]


def _precollected_locks(tc):
    return [lock_region_name(i.name)
            for i in tc.multiworld.precollected_items[tc.player] if i.name.endswith(" Lock")]


# ---- the pure picker -------------------------------------------------------------------------
class PickAnchorRegionsPure(unittest.TestCase):
    GATED = frozenset(REGION_PARENT)
    NEVER = frozenset({GOAL_REGION})

    def test_default_is_one_so_no_seed_in_the_wild_moves(self):
        self.assertEqual(StartRegions.default, 1)
        self.assertEqual(StartRegions.range_start, 1)

    def test_n_one_is_the_old_draw_and_leaves_the_rng_stream_untouched(self):
        """The compatibility guarantee, asserted on BOTH halves: the answer and the stream.

        Comparing only the returned region would pass even if the n == 1 path burned an extra draw
        -- and that draw would reroll every later decision in the seed."""
        for seed in range(200):
            r_old, r_new = random.Random(seed), random.Random(seed)
            old = pick_anchor_region(REGIONS, r_old, COUNTS, DLC_REGIONS, gated=self.GATED)
            new = pick_anchor_regions(REGIONS, r_new, COUNTS, DLC_REGIONS, n=1,
                                      gated=self.GATED, never_extra=self.NEVER)
            self.assertEqual(new[0], [old[0]], f"seed {seed}: n=1 changed the anchor")
            self.assertEqual(new[1], [old[1]], f"seed {seed}: n=1 changed the rule string")
            self.assertEqual(r_old.random(), r_new.random(),
                             f"seed {seed}: n=1 consumed the rng stream differently")

    def test_extras_are_distinct_never_gated_and_never_the_goal_region(self):
        goal_first = 0
        for seed in range(400):
            regs, rules, _ = pick_anchor_regions(REGIONS, random.Random(seed), COUNTS, DLC_REGIONS,
                                                 n=4, gated=self.GATED, never_extra=self.NEVER)
            self.assertEqual(len(set(regs)), 4, f"seed {seed}: duplicate anchor in {regs}")
            self.assertFalse(set(regs) & self.GATED, f"seed {seed}: gated child anchored: {regs}")
            self.assertNotIn(GOAL_REGION, regs[1:], f"seed {seed}: goal region rode in as an extra")
            self.assertFalse(set(regs) & set(DLC_REGIONS),
                             f"seed {seed}: DLC anchor while base regions are kept: {regs}")
            self.assertTrue(all(r.startswith("extra:") for r in rules[1:]), rules)
            goal_first += regs[0] == GOAL_REGION
        # Not an assertion about the rate -- a guard that barring extras did NOT quietly bar the
        # first draw too. That would be a behaviour change to every existing seed.
        self.assertGreater(goal_first, 0,
                           "the goal region can no longer win the FIRST draw -- never_extra leaked "
                           "into the anchor pick, which changes seeds that shipped")

    def test_extras_stay_size_weighted(self):
        """A corridor must stay unlikely as an EXTRA too, not just as the opening region."""
        sizes = []
        for seed in range(1500):
            regs, _, _ = pick_anchor_regions(REGIONS, random.Random(seed), COUNTS, DLC_REGIONS,
                                             n=3, gated=self.GATED, never_extra=self.NEVER)
            sizes += [COUNTS[r] for r in regs[1:]]
        uniform = sum(COUNTS[r] for r in BASE_KEPT) / len(BASE_KEPT)
        self.assertGreater(sum(sizes) / len(sizes), uniform * 1.05,
                           "extras look uniform -- the weighting is not reaching them")

    def test_pool_too_small_is_a_loud_failure(self):
        small = [GOAL_REGION] + [r for r in BASE_KEPT if r != GOAL_REGION][:1]
        with self.assertRaises(ValueError) as cm:
            pick_anchor_regions(small, random.Random(1), COUNTS, DLC_REGIONS, n=3,
                                gated=self.GATED, never_extra=self.NEVER)
        self.assertIn("start_regions", str(cm.exception))

    def test_major_boss_bias_binds_the_first_anchor_only(self):
        """Intersecting all n with the MajorBoss set can empty the pool outright. The bias is a
        bias: it decides where the run OPENS, and then gets out of the way."""
        major = [BASE_KEPT[0]]
        for seed in range(100):
            regs, _, _ = pick_anchor_regions(REGIONS, random.Random(seed), COUNTS, DLC_REGIONS,
                                             n=3, major=major, gated=self.GATED,
                                             never_extra=self.NEVER)
            self.assertEqual(regs[0], major[0], f"seed {seed}: strict bias lost the first anchor")
            self.assertEqual(len(set(regs)), 3, f"seed {seed}: {regs}")


# ---- production actually wires it ---------------------------------------------------------------
class StartRegionsWired(WorldTestBase):
    """A green predicate with no caller is a spec, not a feature. These build real worlds."""
    game = GAME
    options = {"num_regions": 6, "start_regions": 3}
    SEEDS = (1, 7, 13, 22222, 5551212)

    def test_three_regions_open_at_start_and_they_are_kept_and_distinct(self):
        for seed in self.SEEDS:
            self.world_setup(seed=seed)
            kept = list(self.world._kept())
            locks = _precollected_locks(self)
            self.assertEqual(len(locks), 3, f"seed {seed}: precollected {locks}")
            self.assertEqual(len(set(locks)), 3, f"seed {seed}: duplicate precollect {locks}")
            for r in locks:
                self.assertIn(r, kept, f"seed {seed}: {r} opened but not kept")
                self.assertNotIn(r, REGION_PARENT, f"seed {seed}: gated child {r} opened the run")
            self.assertNotIn(GOAL_REGION, locks[1:] if locks[0] == GOAL_REGION else locks[1:],
                             f"seed {seed}: goal region as an extra")

    def test_count_neutral_with_three_anchors(self):
        for seed in self.SEEDS:
            self.world_setup(seed=seed)
            kept = list(self.world._kept())
            total = (len(LOCATIONS.get(HUB, [])) + sum(len(LOCATIONS.get(r, [])) for r in kept)
                     + len(getattr(self.world, "gf_extra_locations", ())))
            self.assertEqual(len(world_pool_items(self)), total,
                             f"seed {seed}: pool not count-neutral after three precollects")

    def test_goal_stops_requiring_the_locks_you_already_hold(self):
        self.world_setup(seed=7)
        required = self.world.goal_required_lock_names()
        for r in _precollected_locks(self):
            self.assertNotIn(f"{r} Lock", required,
                             "the goal requires a lock that is never sent")
        self.assertTrue(required, "every lock precollected -- the goal is complete at connect")

    def test_every_opening_region_is_fill_sphere_zero(self):
        from worlds.eldenring.features.scaling import _region_fill_spheres
        self.world_setup(seed=13)
        spheres = _region_fill_spheres(self.world)
        if not spheres:
            self.skipTest("fill spheres uncomputable in this configuration")
        for r in _precollected_locks(self):
            self.assertEqual(spheres.get(r), 0,
                             f"{r} is open at start but not sphere 0 -- the scaling ramp would "
                             f"treat part of the opening as deeper than it is")

    def test_extras_are_named_in_the_gen_log(self):
        """SAY WHAT THE NUMBER DID (#409). The singular line stays exactly as it was."""
        with self.assertLogs("Greenfield", level=logging.INFO) as cm:
            self.world_setup(seed=7)
        singular = [m for m in cm.output if "start anchor:" in m]
        plural = [m for m in cm.output if "start anchors:" in m]
        self.assertEqual(len(singular), 1, f"the original anchor line changed: {singular}")
        self.assertEqual(len(plural), 1, f"extras were not announced: {plural}")
        self.assertIn("+2 extra", plural[0])


class StartRegionsClampIsLoud(WorldTestBase):
    """Asking for more opening regions than the seed kept must die at generation, not roll a seed
    that is already complete at connect. num_regions is a DRAW SIZE, so the ceiling is the KEPT
    count -- which is why this is checked in core and not in the option's own range."""
    game = GAME
    options = {"num_regions": 1, "start_regions": 10}
    auto_construct = False

    def test_more_start_regions_than_kept_is_a_generation_error(self):
        with self.assertRaises(OptionError) as cm:
            self.world_setup(seed=7)
        msg = str(cm.exception)
        self.assertIn("start_regions", msg)
        self.assertIn("num_regions", msg)
