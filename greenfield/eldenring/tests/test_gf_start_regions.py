"""start_regions -- N opening regions instead of one (features/start_grace.pick_anchor_regions).

MOTIVATING CASE (CONTRIBUTING rule 11). boblerrr, 2026-08-06: "is there an option to start with
more than 1 region unlocked?" There was not: `start_with_region_lock` precollected exactly one
Region Lock and `pick_anchor_region` returned exactly one region.

What this guards, and why each one is here rather than assumed:
  * n == 1 IS THE OLD DRAW -- same region AND the same rng stream afterwards. Every defaulted seed
    in the wild must keep rolling identically, and an extra rng call inside the n == 1 path would
    silently reroll everything downstream of it. region_spine appends GOAL_REGION AFTER its
    rng.sample for exactly this reason; the same discipline applies here.
  * never_extra bars a region from the EXTRAS only, never from the first draw -- filtering the
    first draw would move the anchor of every seed already rolled. A run that opens on the region
    it ends in is not a run, which is why the goal region is passed as never_extra; but the goal
    region is ALSO a gated child today and so cannot anchor at all. The two rules are separate and
    only one of them is testable through the goal region -- see
    test_never_extra_does_not_leak_into_the_first_draw.
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
        seen = 0
        for seed in range(400):
            seen += 1
            regs, rules, _ = pick_anchor_regions(REGIONS, random.Random(seed), COUNTS, DLC_REGIONS,
                                                 n=4, gated=self.GATED, never_extra=self.NEVER)
            self.assertEqual(len(set(regs)), 4, f"seed {seed}: duplicate anchor in {regs}")
            self.assertFalse(set(regs) & self.GATED, f"seed {seed}: gated child anchored: {regs}")
            self.assertNotIn(GOAL_REGION, regs[1:], f"seed {seed}: goal region rode in as an extra")
            self.assertFalse(set(regs) & set(DLC_REGIONS),
                             f"seed {seed}: DLC anchor while base regions are kept: {regs}")
            self.assertTrue(all(r.startswith("extra:") for r in rules[1:]), rules)
        self.assertGreater(seen, 0, "the sweep matched nothing")

    def test_the_goal_region_is_barred_by_the_GATED_rule_not_by_never_extra(self):
        """WHY THE OBVIOUS GUARD IS NOT HERE, written down so it is not re-added.

        This class used to end the sweep above by counting how often GOAL_REGION won the FIRST
        draw and asserting that count was greater than zero -- "a guard that barring extras did NOT
        quietly bar the first draw too". Good instinct, unwitnessable subject: GOAL_REGION is
        Leyndell, Leyndell is a REGION_PARENT child (the capital's main gate is a vanilla wall),
        and `pick_anchor_region` drops gated regions from eligibility before it weights anything.
        The count is therefore 0 on every seed and was 0 on the day the guard was written -- an
        assertion that could only ever fail, wearing a failure message blaming a mechanism
        (`never_extra` leaked into the anchor pick) that had nothing to do with it.

        So the invariant is split in two. This test pins the reason the goal region cannot anchor;
        test_never_extra_does_not_leak_into_the_first_draw pins the rule the old guard was actually
        aiming at, using a witness that CAN win a draw."""
        self.assertIn(GOAL_REGION, REGION_PARENT,
                      "GOAL_REGION is no longer a gated child, so the gated rule no longer bars it "
                      "from anchoring -- and never_extra, which bars EXTRAS only, is now the only "
                      "thing standing between a player and a run that opens where it ends. Decide "
                      "whether the first draw should be filtered too before deleting this")
        for seed in range(400):
            regs, _, _ = pick_anchor_regions(REGIONS, random.Random(seed), COUNTS, DLC_REGIONS,
                                             n=4, gated=self.GATED, never_extra=self.NEVER)
            self.assertNotIn(GOAL_REGION, regs, f"seed {seed}: a gated child anchored: {regs}")

    def test_never_extra_does_not_leak_into_the_first_draw(self):
        """THE COMPATIBILITY RULE, on a subject that can actually witness it. `never_extra` must
        bar its regions from the EXTRAS and leave the first draw exactly as it was: an extra filter
        on the anchor would move the opening region of every seed already rolled.

        The witness is the largest ELIGIBLE region (biggest weight -> it wins the size-weighted
        first draw often enough for 400 seeds to prove the point), not the goal region, which the
        gated rule bars from every draw -- see the test above."""
        witness = max(BASE_KEPT, key=lambda r: COUNTS[r])
        self.assertNotIn(witness, self.GATED, "the witness must be eligible or this proves nothing")
        first = 0
        for seed in range(400):
            regs, _, _ = pick_anchor_regions(REGIONS, random.Random(seed), COUNTS, DLC_REGIONS,
                                             n=4, gated=self.GATED,
                                             never_extra=frozenset({witness}))
            self.assertNotIn(witness, regs[1:], f"seed {seed}: never_extra region rode in as an "
                                                f"extra: {regs}")
            first += regs[0] == witness
        self.assertGreater(first, 0,
                           f"{witness!r} was barred as an extra and can no longer win the FIRST "
                           "draw either -- never_extra has leaked into the anchor pick, which "
                           "changes the opening region of every seed that shipped")

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
        # Without `only`, raising num_regions IS a real road out -- a bigger draw really can bring
        # another anchorable region in. The advice belongs here and nowhere else.
        self.assertIn("raise num_regions", str(cm.exception))

    def test_the_backstop_does_not_advise_raising_num_regions_under_a_pool(self):
        """#690. `only` NARROWS `kept` at the top of pick_anchor_regions, before the draw, so a
        bigger num_regions adds regions the filter immediately removes. The message used to say
        "lower start_regions or raise num_regions" unconditionally; bobler (2026-08-15) followed the
        second half at num_regions 9 and died identically.

        🛑 This is not "the wording changed". Advice a player can ACT ON and that provably cannot
        work costs them a generation to disprove, and the fix above (core's fourth refusal) means
        almost nobody reaches this text -- so the one player who does is the one who needs it right.
        """
        pool = [r for r in BASE_KEPT if r != GOAL_REGION][:2]
        only = frozenset(pool[:1])
        with self.assertRaises(ValueError) as cm:
            pick_anchor_regions(pool, random.Random(1), COUNTS, DLC_REGIONS, n=2,
                                gated=self.GATED, never_extra=self.NEVER, only=only)
        msg = str(cm.exception)
        self.assertNotIn("raise num_regions", msg,
                         "the backstop still offers the road start_region_pool closed: " + msg)
        self.assertIn("start_region_pool", msg, msg)
        self.assertIn("start_regions", msg, msg)

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
        # THE WITNESS (test_gf_vacuous_pass). Every assertion below is "this region's sphere is 0",
        # and 0 is the empty value -- so with no opening regions to iterate, this test passed by
        # looking at nothing. It is a three-anchor class; say so before believing the loop.
        locks = _precollected_locks(self)
        self.assertEqual(len(locks), 3,
                         f"expected three opening regions to check, got {locks}")
        for r in locks:
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


# ---- start_region_pool: WHICH region opens the run --------------------------------------------
class StartRegionPoolWired(WorldTestBase):
    """MOTIVATING CASE (rule 11). boblerrr, 2026-08-13: he wanted to choose the starting region, to
    test one region at a time. `start_regions` answers "how many", and there was no answer to
    "which" -- the anchor was a size-weighted draw with no way in.

    The one that matters is `test_the_named_region_opens_the_run`: everything else here guards a
    refusal, and a refusal that fires on a seed nobody asked for is cheap. Opening where the player
    said is the feature.
    """
    game = GAME
    options = {"num_regions": 4, "start_region_pool": ["Caelid"]}
    SEEDS = (1, 7, 13, 22222, 5551212)

    def test_the_named_region_opens_the_run(self):
        for seed in self.SEEDS:
            self.world_setup(seed=seed)
            self.assertEqual(_precollected_locks(self), ["Caelid"],
                             f"seed {seed}: start_region_pool named Caelid and the run opened "
                             f"elsewhere")

    def test_the_named_region_is_force_kept(self):
        """The pool NAMES a region, so the region has to be in the seed. num_regions is a draw size
        and this rides the same force-keep seam a named goal does -- if that seam ever stops being
        additive, the anchor above would still pass by opening in a region the draw happened to
        take, and this is the assertion that would not."""
        for seed in self.SEEDS:
            self.world_setup(seed=seed)
            self.assertIn("Caelid", list(self.world._kept()), f"seed {seed}")


class StartRegionPoolDrawsFromThePool(WorldTestBase):
    """Several names = a POOL, not a list to open all of. With start_regions 1 exactly one of them
    opens the run, and it is one of THOSE, not any kept region."""
    game = GAME
    options = {"num_regions": 6, "start_region_pool": ["Caelid", "Liurnia"]}

    def test_exactly_one_of_the_named_regions_opens(self):
        seen = set()
        for seed in (1, 7, 13, 22222, 5551212, 31337, 424242):
            self.world_setup(seed=seed)
            locks = _precollected_locks(self)
            self.assertEqual(len(locks), 1, f"seed {seed}: {locks}")
            self.assertIn(locks[0], {"Caelid", "Liurnia"}, f"seed {seed}: opened in {locks[0]}")
            seen.add(locks[0])
        # Not an assertion about fairness -- just that the pool is a POOL. If one name could never
        # win, "draw from these" would be a lie and a single-name test would never notice.
        self.assertEqual(seen, {"Caelid", "Liurnia"},
                         "over 7 seeds only %s ever opened the run, so the second name is dead"
                         % sorted(seen))


class StartRegionPoolComposesWithStartRegions(WorldTestBase):
    """`start_regions: 2` + two names = both open. The pool constrains WHICH; the count says HOW
    MANY, and neither had to learn about the other."""
    game = GAME
    options = {"num_regions": 8, "start_regions": 2,
               "start_region_pool": ["Caelid", "Liurnia"]}

    def test_both_named_regions_open(self):
        for seed in (1, 13, 22222):
            self.world_setup(seed=seed)
            self.assertEqual(sorted(_precollected_locks(self)), ["Caelid", "Liurnia"],
                             f"seed {seed}")


class StartRegionPoolRefusalsNameTheRegion(WorldTestBase):
    """Three ways a named region cannot open a run, and they are invisible to each other: your DLC
    toggles sealed it, your goal needs it, or it is a child reached through its parent. A single
    "not available" would send the player to the wrong one, so each refusal names the region AND
    which of the three it is. These assert the REASON, not just that something raised."""
    game = GAME
    auto_construct = False

    def _raises_with(self, options, *fragments):
        self.options = dict(options)
        with self.assertRaises(OptionError) as cm:
            self.world_setup(seed=7)
        msg = str(cm.exception)
        for f in fragments:
            self.assertIn(f, msg, "the refusal did not say %r -- it said: %s" % (f, msg))

    def test_a_dlc_region_with_the_dlc_off_says_so(self):
        self._raises_with({"num_regions": 4, "enable_dlc": False,
                           "start_region_pool": ["Belurat"]},
                          "start_region_pool", "Belurat", "enable_dlc")

    def test_a_base_region_under_dlc_only_says_so(self):
        self._raises_with({"num_regions": 4, "enable_dlc": True, "dlc_only": True,
                           "start_region_pool": ["Caelid"]},
                          "start_region_pool", "Caelid", "dlc_only")

    def test_a_gated_child_says_which_parent_to_name_instead(self):
        # Sewer is reached through Leyndell; its grace bundle is withheld, so the player could not
        # warp into it even if the Lock were in hand.
        self._raises_with({"num_regions": 4, "start_region_pool": ["Sewer"]},
                          "start_region_pool", "Sewer", "Leyndell")

    def test_the_goal_region_says_the_goal(self):
        # Enir Ilim, not Leyndell: the default goal's region is ALSO a gated child, so it trips the
        # gated rule first and the goal rule would never be reached through it. Two rules, and only
        # a non-gated goal region can tell them apart -- the same distinction
        # test_the_goal_region_is_barred_by_the_GATED_rule_not_by_never_extra draws above.
        self._raises_with({"num_regions": 6, "enable_dlc": True, "goal": "promised_consort",
                           "start_region_pool": ["Enir Ilim"]},
                          "start_region_pool", "Enir Ilim", "promised_consort")


class StartRegionPoolIsInertWhereThereIsNoAnchor(WorldTestBase):
    """natural_progression mints no Lock items, so there is no anchor to constrain. The option must
    do NOTHING rather than refuse: failing a seed over a setting that cannot apply to it is the
    failure mode `start_regions` already avoids, decided in the same place for the same reason.

    🛑 A no-op is the hardest thing to test and the easiest to fake -- asserting "it did not raise"
    would pass over an option that had silently stopped working everywhere. So this also asserts the
    seed really is the no-anchor case, via `kept_lock_names()`, which its own docstring calls THE
    single source for the locks completion requires and which is empty under natural progression.

    🛑 NOT a scan for items whose name ends in " Lock". That was the first version and it FAILED,
    reporting 28 of them: `_util.world_pool_items` counts items PRE-PLACED on locations as well as
    the itempool, and under natural progression the Locks exist there while none is minted into the
    pool and none is precollected. Two different questions, one substring."""
    game = GAME
    options = {"num_regions": 4, "natural_progression": True,
               "start_region_pool": ["Caelid"]}

    def test_it_generates_and_has_no_anchor_to_constrain(self):
        self.world_setup(seed=7)
        # WITNESSES FIRST (test_gf_vacuous_pass' ratchet, and it is the right rule here): both
        # assertions below are "this collection is empty", and an empty world would satisfy them
        # for the wrong reason. So: a real seed, with regions that COULD have minted locks and
        # locations that could have hosted them.
        #
        # 🛑 The obvious witness -- "precollected_items is non-empty, and no Lock is among them" --
        # is FALSE here and cost a red: under natural progression this world precollects NOTHING at
        # all, so that assertion fails on a seed that is behaving exactly as intended. The witness
        # has to be something the no-anchor case still has.
        self.assertGreater(len(list(self.world._kept())), 1)
        self.assertGreater(len(self.multiworld.get_locations(self.player)), 0)
        self.assertEqual(self.world.kept_lock_names(), [],
                         "natural_progression minted Region Locks, so this seed is not the "
                         "no-anchor case this test claims to cover")
        self.assertEqual(_precollected_locks(self), [],
                         "natural_progression precollected a Region Lock")


class StartRegionPoolMustSeatStartRegions(WorldTestBase):
    """MOTIVATING CASE (rule 11), issue #690. bobler, 2026-08-15:

        num_regions: 9
        start_regions: 2
        start_region_pool: ["Caelid"]

    Two anchors asked for, one region allowed to host them. Before this fix that was an unhandled
    ValueError out of features/start_grace -- a TRACEBACK, not a yaml diagnosis -- and the text it
    carried told him to raise num_regions, which cannot work: `only` narrows the kept set before the
    anchors are drawn, so a bigger seed just grows a set this option shrinks again. He tried it at 9
    and died identically.

    So the assertions are not "it raises". They are: the right EXCEPTION TYPE (OptionError is what
    AP renders as a yaml problem; ValueError is what it renders as a crash), and both option names
    in the text, because either one of the two is the knob the player meant to turn."""
    game = GAME
    auto_construct = False

    def test_a_one_name_pool_refuses_two_starting_regions_as_an_option_error(self):
        self.options = {"num_regions": 9, "start_regions": 2,
                        "start_region_pool": ["Caelid"]}
        with self.assertRaises(OptionError) as cm:
            self.world_setup(seed=7)
        msg = str(cm.exception)
        self.assertIn("start_region_pool", msg, msg)
        self.assertIn("start_regions", msg, msg)
        # The numbers, both of them -- "the pool is too small" without them is a riddle.
        self.assertIn("2", msg, msg)
        self.assertIn("Caelid", msg, msg)
        # And the dead road is named DEAD rather than left for him to try.
        self.assertIn("num_regions cannot fix this", msg, msg)

    def test_it_is_not_the_num_regions_value_that_decides(self):
        """It failed at the default 6 too. If the refusal ever starts depending on num_regions,
        that is the old confusion coming back through the front door."""
        for nr in (6, 9, 12):
            self.options = {"num_regions": nr, "start_regions": 2,
                            "start_region_pool": ["Caelid"]}
            with self.assertRaises(OptionError):
                self.world_setup(seed=7)


class StartRegionPoolBigEnoughStillGenerates(WorldTestBase):
    """THE CONTROL for the refusal above, and the reason it is a separate class: a guard that
    refuses everything would satisfy every assertion in StartRegionPoolMustSeatStartRegions. The
    same yaml with the pool one name longer must still generate AND still open in both named
    regions -- refusing the unsatisfiable case must not cost the satisfiable one."""
    game = GAME
    options = {"num_regions": 9, "start_regions": 2,
               "start_region_pool": ["Caelid", "Limgrave"]}

    def test_two_names_seat_two_starting_regions(self):
        for seed in (1, 7, 22222):
            self.world_setup(seed=seed)
            self.assertEqual(sorted(_precollected_locks(self)), ["Caelid", "Limgrave"],
                             f"seed {seed}")

    def test_a_pool_equal_to_the_count_is_allowed_not_merely_larger(self):
        """The bound is `start_regions > len(pool)`, not `>=`. Off by one here and the control
        above is the only case that survives, which is exactly the case nobody would file."""
        self.world_setup(seed=13)
        self.assertEqual(len(_precollected_locks(self)), 2)
