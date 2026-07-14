"""start_with_region_lock anchor pick -- size-weighted over the kept BASE-game regions.

The precollected region Lock IS the run's opening region: the only region open from Roundtable at
sphere 0. The old pick was `random.choice` over every kept lock -- uniform -- which ignored two facts
the generated data already knows: region check counts span 13..543 (a uniform draw over all 31 opened
~1 run in 3 on a region under 80 checks; playtest 2026-07-14 opened on Castle Ensis, 31 checks), and
EVERY sub-80 region is DLC, where a fresh character also has zero scadutree blessing. The fix is
features/start_grace.pick_anchor_region: size-weighted (weight = emitted check count, derived from
data.LOCATIONS -- never a frozen table) over kept BASE regions, DLC fallback only when no base region
is kept (dlc_only), and the strict-surface MajorBoss bias INTERSECTING that eligibility instead of
replacing it.

What this guards (every expectation DERIVED from data.LOCATIONS / region_spine at test time -- no
hand-pinned region sizes to rot when a re-tag moves checks):
  * the anchor is NEVER a DLC region while any base region is kept, and never below the base floor;
  * the weighting BITES: the mean anchor size over many draws sits far above the old uniform-draw
    expectation AND above a merely-base-uniform pick (so DLC-exclusion alone can't pass it);
  * dlc_only degrades to a size-weighted DLC draw: deterministic, never a crash, and the smallest
    kept region is rare instead of 1-in-N;
  * strict surface (progression_surface_mode == 2) intersects; an empty intersection degrades
    (rule says so) instead of raising;
  * count-neutrality holds across the sweep (the precollected lock leaves the pool; items == locations);
  * production CALLS the pure fn: the WorldTestBase sweep + the telemetry log line prove the wired
    path, not just the predicate (a green predicate with no caller is a spec, not a fix).

PIN num_regions in every world built here -- an unpinned num_regions is a known test-breaker.

Run (from the Archipelago dir, world installed):
    python -m pytest worlds/eldenring/tests/test_gf_start_anchor.py
"""
import random
import statistics
import unittest

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring.data import HUB, REGIONS, LOCATIONS                       # noqa: E402
from worlds.eldenring.region_spine import (  # noqa: E402
    DLC_REGIONS, REGION_PARENT, base_regions, dlc_regions)
from worlds.eldenring.features.start_grace import pick_anchor_region            # noqa: E402
from worlds.eldenring.features.progression_surface import (                     # noqa: E402
    lock_region_name, regions_with_major_boss)
from ._util import world_pool_items                                             # noqa: E402

GAME = "Elden Ring"

# Weights are the region's emitted check count -- the SAME derivation core.create_items feeds the
# picker, recomputed here from the world's own location data (provenance: derive, don't pin).
COUNTS = {r: len(LOCATIONS.get(r, [])) for r in REGIONS}


def _weighted_mean(regions):
    """Exact expectation of a size-weighted draw over `regions`: sum(c^2)/sum(c)."""
    tot = sum(COUNTS[r] for r in regions)
    return sum(COUNTS[r] ** 2 for r in regions) / tot


# ---- the pure picker ------------------------------------------------------------------------------
class PickAnchorPure(unittest.TestCase):
    N = 4000

    def test_data_sanity_regions_have_checks(self):
        """The weights this whole file reasons about must be real: every region emits checks, and the
        counts genuinely spread (if LOCATIONS collapsed, every assertion below would be vacuous)."""
        self.assertEqual(len(COUNTS), len(REGIONS))
        for r, c in COUNTS.items():
            self.assertGreater(c, 0, f"{r} emits no checks -- location data broken/ungenerated")
        self.assertGreater(max(COUNTS.values()), 4 * min(COUNTS.values()),
                           "region sizes should spread; a flat table makes weighting untestable")
        self.assertTrue(base_regions() and dlc_regions(), "need both partitions to test eligibility")

    def test_never_dlc_never_below_base_floor_when_base_kept(self):
        """Sweep: with every region kept (the widest kept set), the anchor must always be a base
        region -- so it can never land in the sub-base-floor tail, which today is entirely DLC."""
        rng = random.Random(1234)
        floor = min(COUNTS[r] for r in base_regions())
        for _ in range(self.N):
            region, rule, n = pick_anchor_region(REGIONS, rng, COUNTS, DLC_REGIONS)
            self.assertNotIn(region, DLC_REGIONS,
                             f"anchor {region} is DLC while base regions are kept")
            self.assertGreaterEqual(COUNTS[region], floor,
                                    f"anchor {region} ({COUNTS[region]}) below the base floor {floor}")
            self.assertEqual(rule, "base-weighted")
            self.assertEqual(n, len(base_regions()))

    def test_weighting_bites_mean_far_above_uniform(self):
        """Prove the weighting actually changes the distribution, with three teeth:
        (1) mean anchor size >> the OLD uniform-over-all-kept expectation;
        (2) mean anchor size >  a uniform-over-base pick too (DLC-exclusion alone cannot pass);
        (3) mean matches the exact weighted expectation (so the weights are the check counts,
            not merely 'something non-uniform')."""
        rng = random.Random(99)
        draws = [COUNTS[pick_anchor_region(REGIONS, rng, COUNTS, DLC_REGIONS)[0]]
                 for _ in range(self.N)]
        mean = statistics.mean(draws)
        uniform_all = statistics.mean(COUNTS[r] for r in REGIONS)      # the old pick's expectation
        uniform_base = statistics.mean(COUNTS[r] for r in base_regions())
        expect = _weighted_mean(base_regions())
        self.assertGreater(mean, uniform_all * 1.5,
                           f"mean anchor {mean:.1f} vs uniform-all {uniform_all:.1f}: weighting inert?")
        self.assertGreater(mean, uniform_base * 1.15,
                           f"mean anchor {mean:.1f} vs uniform-base {uniform_base:.1f}: draw looks "
                           "uniform over base -- the size weights are not being applied")
        self.assertAlmostEqual(mean, expect, delta=expect * 0.06,
                               msg=f"mean anchor {mean:.1f} != weighted expectation {expect:.1f}: "
                                   "weights are not the check counts")

    def test_deterministic_same_seed_same_sequence(self):
        r1, r2 = random.Random(7), random.Random(7)
        s1 = [pick_anchor_region(REGIONS, r1, COUNTS, DLC_REGIONS)[0] for _ in range(25)]
        s2 = [pick_anchor_region(REGIONS, r2, COUNTS, DLC_REGIONS)[0] for _ in range(25)]
        self.assertEqual(s1, s2, "same seed must draw the same anchors")

    def test_dlc_only_fallback_weighted_deterministic_no_crash(self):
        """No base region kept: the draw degrades to size-weighted over kept DLC regions. The
        smallest kept region must be RARE (well under uniform 1/N), and the mean must sit near the
        weighted expectation -- a small start is unavoidable there, not the likely one."""
        kept = dlc_regions()
        smallest = min(kept, key=lambda r: COUNTS[r])
        rng = random.Random(4242)
        picks = []
        for _ in range(self.N):
            region, rule, n = pick_anchor_region(kept, rng, COUNTS, DLC_REGIONS)
            self.assertIn(region, DLC_REGIONS)
            self.assertEqual(rule, "dlc-fallback-weighted")
            self.assertEqual(n, len(kept))
            picks.append(region)
        freq_smallest = picks.count(smallest) / self.N
        self.assertLess(freq_smallest, 1.0 / (2 * len(kept)),
                        f"{smallest} drawn {freq_smallest:.3f} of the time -- looks uniform "
                        f"(uniform would be {1.0 / len(kept):.3f}); the fallback lost its weights")
        mean = statistics.mean(COUNTS[r] for r in picks)
        self.assertGreater(mean, statistics.mean(COUNTS[r] for r in kept) * 1.3,
                           "dlc fallback mean anchor size looks uniform, not size-weighted")
        # deterministic
        again = random.Random(4242)
        picks2 = [pick_anchor_region(kept, again, COUNTS, DLC_REGIONS)[0] for _ in range(50)]
        self.assertEqual(picks[:50], picks2, "dlc fallback must be seed-stable")

    def test_empty_kept_is_a_loud_failure(self):
        with self.assertRaises(ValueError):
            pick_anchor_region([], random.Random(1), COUNTS, DLC_REGIONS)

    def test_zero_weights_is_a_loud_failure(self):
        """An eligible pool whose regions emit no checks is broken data, not a clean run."""
        with self.assertRaises(ValueError):
            pick_anchor_region(["Limgrave"], random.Random(1), {"Limgrave": 0}, DLC_REGIONS)

    def test_gated_children_never_anchor(self):
        """gated-children fix (2026-07-14): a REGION_PARENT child may never open the run -- its
        opening grant is exactly the grace bundle features/graces.py withholds (East Capital
        Rampart, playtest). The exclusion applies BEFORE weighting and before the major bias."""
        rng = random.Random(714)
        for _ in range(2000):
            region, _rule, _n = pick_anchor_region(REGIONS, rng, COUNTS, DLC_REGIONS,
                                                   gated=frozenset(REGION_PARENT))
            self.assertNotIn(region, REGION_PARENT, f"anchor {region} is a gated child")

    def test_all_gated_kept_set_is_a_loud_failure(self):
        """A kept set that is ONLY gated children cannot exist post-closure (a child always pulls a
        non-child ancestor in); handed one anyway, refuse loudly rather than anchor past a wall."""
        with self.assertRaises(ValueError):
            pick_anchor_region(list(REGION_PARENT), random.Random(1), COUNTS, DLC_REGIONS,
                               gated=frozenset(REGION_PARENT))

    def test_major_boss_intersects_eligibility_not_replaces_it(self):
        """strict mode: a major set spanning base+DLC must narrow to its BASE members only -- the old
        code replaced the pool with the major set, which could re-admit a DLC anchor."""
        some_base = max(base_regions(), key=lambda r: COUNTS[r])
        some_dlc = max(dlc_regions(), key=lambda r: COUNTS[r])
        rng = random.Random(5)
        for _ in range(200):
            region, rule, n = pick_anchor_region(REGIONS, rng, COUNTS, DLC_REGIONS,
                                                 major={some_base, some_dlc})
            self.assertEqual(region, some_base,
                             f"major covers {{{some_base}, {some_dlc}}} but only {some_base} is base")
            self.assertEqual(rule, "major-boss^base-weighted")
            self.assertEqual(n, 1)

    def test_major_boss_empty_intersection_degrades_never_raises(self):
        """A major set with no base member (or empty) degrades to the plain weighted draw, and the
        rule SAYS so -- the defined, logged order instead of a throw."""
        only_dlc_major = {next(iter(dlc_regions()))}
        for major in (only_dlc_major, set()):
            region, rule, n = pick_anchor_region(REGIONS, random.Random(3), COUNTS, DLC_REGIONS,
                                                 major=major)
            self.assertNotIn(region, DLC_REGIONS)
            self.assertIn("degraded", rule, f"degrade must be visible in the rule; got {rule!r}")
            self.assertEqual(n, len(base_regions()))


# ---- production wiring: the world must CALL the picker ---------------------------------------------
def _anchor_lock(tc):
    """The one precollected region Lock of this world (boss keys etc. filtered by the ' Lock' name)."""
    locks = [i for i in tc.multiworld.precollected_items[tc.player] if i.name.endswith(" Lock")]
    tc.assertEqual(len(locks), 1,
                   f"expected exactly ONE precollected region Lock, got {[i.name for i in locks]}")
    return lock_region_name(locks[0].name)


class AnchorRolledSweep(WorldTestBase):
    """rolled num_regions: across seeds the anchor must always be a kept BASE region (the goal region
    is base and always kept, so a base region always exists), and the pool stays count-neutral."""
    game = GAME
    options = {"num_regions": 6, "num_regions_order": "rolled"}
    SEEDS = (1, 2, 3, 5, 7, 11, 13, 22222, 101, 5551212)

    def test_anchor_never_dlc_and_count_neutral_across_seeds(self):
        for seed in self.SEEDS:
            self.world_setup(seed=seed)
            kept = list(self.world._kept())
            base_kept = [r for r in kept if r not in DLC_REGIONS]
            self.assertTrue(base_kept, f"seed {seed}: no base region kept?! goal region is base")
            region = _anchor_lock(self)
            self.assertIn(region, kept, f"seed {seed}: anchor {region} not a kept region")
            self.assertNotIn(region, DLC_REGIONS,
                             f"seed {seed}: anchor {region} is DLC while base {base_kept} are kept")
            self.assertNotIn(region, REGION_PARENT,
                             f"seed {seed}: anchor {region} is a gated child -- its bundle is "
                             f"withheld, so it can never be the opening region (wiring lost?)")
            eligible = [r for r in base_kept if r not in REGION_PARENT]
            floor = min(COUNTS[r] for r in eligible)
            self.assertGreaterEqual(COUNTS[region], floor, f"seed {seed}: anchor below base floor")
            # count-neutral: location-payers == locations (the precollected lock left the pool and
            # its freed slot became filler).
            total = len(LOCATIONS.get(HUB, [])) + sum(len(LOCATIONS.get(r, [])) for r in kept)
            self.assertEqual(len(world_pool_items(self)), total,
                             f"seed {seed}: pool not count-neutral after the anchor precollect")

    def test_anchor_telemetry_logs_the_decision(self):
        """CONTRIBUTING: a feature is armed, or it says why not. The gen log must carry the pick."""
        import logging
        with self.assertLogs("Greenfield", level=logging.INFO) as cm:
            self.world_setup(seed=7)
        lines = [m for m in cm.output if "start anchor:" in m]
        self.assertEqual(len(lines), 1, f"expected ONE anchor telemetry line, got {lines}")
        self.assertIn("via", lines[0])
        self.assertIn("eligible", lines[0])


class AnchorDistributionSweep(WorldTestBase):
    """End-to-end distribution: over rolled seeds the WORLD's anchor sizes must average materially
    above the uniform expectation over its kept sets -- proving production wired the weighted pick,
    not just that the predicate exists. (The heavy statistics live in PickAnchorPure; this sweep is
    sized to stay fast while still going red under a uniform pick.)"""
    game = GAME
    options = {"num_regions": 6, "num_regions_order": "rolled"}
    SEEDS = tuple(range(201, 221))  # 20 seeds

    def test_mean_anchor_size_beats_uniform_expectation(self):
        anchor_sizes, uniform_expects = [], []
        for seed in self.SEEDS:
            self.world_setup(seed=seed)
            kept = list(self.world._kept())
            anchor_sizes.append(COUNTS[_anchor_lock(self)])
            uniform_expects.append(statistics.mean(COUNTS[r] for r in kept))  # the OLD pick's mean
        mean_anchor = statistics.mean(anchor_sizes)
        mean_uniform = statistics.mean(uniform_expects)
        self.assertGreater(
            mean_anchor, mean_uniform * 1.35,
            f"mean anchor size {mean_anchor:.1f} vs uniform expectation {mean_uniform:.1f} over "
            f"{len(self.SEEDS)} seeds -- the size weighting is not reaching production")


class AnchorDlcOnly(WorldTestBase):
    """dlc_only: no base region is ever kept, so the anchor comes from the DLC fallback -- weighted,
    deterministic, never a crash, never None."""
    game = GAME
    options = {"dlc_only": True, "num_regions": 5, "num_regions_order": "rolled"}
    SEEDS = (3, 11, 29, 404)

    def test_anchor_is_kept_dlc_and_deterministic(self):
        for seed in self.SEEDS:
            self.world_setup(seed=seed)
            kept = list(self.world._kept())
            self.assertTrue(all(r in DLC_REGIONS for r in kept),
                            f"seed {seed}: dlc_only kept a base region {kept}")
            region = _anchor_lock(self)
            self.assertIn(region, kept)
            self.assertIn(region, DLC_REGIONS)
        # two builds of the SAME seed agree (seed-stability of the new draw)
        self.world_setup(seed=29)
        first = _anchor_lock(self)
        self.world_setup(seed=29)
        self.assertEqual(_anchor_lock(self), first, "same seed, same options -> same anchor")


class AnchorStrictSurfaceIntersect(WorldTestBase):
    """progression_surface_mode=2 (strict): the MajorBoss bias must INTERSECT base eligibility --
    anchor in majors-cap-base when that set is non-empty, else still a base region (degrade, no
    throw). Note mode 2 is also the DEFAULT, so the other sweeps exercise it too; this class pins it
    explicitly so a default flip can't silently drop the coverage."""
    game = GAME
    options = {"progression_surface_mode": 2, "num_regions": 6, "num_regions_order": "rolled"}
    SEEDS = (1, 4, 9, 16, 25)

    def test_anchor_in_major_cap_base_when_nonempty(self):
        for seed in self.SEEDS:
            self.world_setup(seed=seed)
            kept = list(self.world._kept())
            majors = regions_with_major_boss(kept)
            base_kept = {r for r in kept if r not in DLC_REGIONS}
            region = _anchor_lock(self)
            self.assertIn(region, base_kept, f"seed {seed}: strict anchor {region} not base")
            # gated children (REGION_PARENT) leave eligibility BEFORE the major bias -- Leyndell
            # hosts Morgott (a major) but may never anchor, so intersect on the reduced pool.
            inter = (majors & base_kept) - set(REGION_PARENT)
            if inter:
                self.assertIn(region, inter,
                              f"seed {seed}: anchor {region} outside majors-cap-base {sorted(inter)}")
