"""The explicit `goal` option (core.Goal + features/goal_locations.GOAL_CHOICES).

MOTIVATING CASE (rule 11 -- it IS the acceptance test). dafranky67, 2026-07-30: "I'd like to have
PCR and Elden Beast options". Today the goal is fully derived, and tier 0 (the finale) outranks the
spine walk UNCONDITIONALLY -- so on any full base+DLC seed the run ends at the Elden Beast and Enir
Ilim / Promised Consort Radahn is optional content that can never be the goal by luck.

So the pin is exactly that case, both legs, on the SAME draw:
  * num_regions 0 + `goal: promised_consort`  -> goalLocations == [7770670]  (PCR, and NOT the pair)
  * num_regions 0 + default (`goal: auto`)    -> goalLocations == {7770655, 7770664}  (the pair)

The rest guards the failure modes this design was chosen to avoid:
  * a named goal must never SILENTLY degrade to the ladder -- an impossible one raises at
    generation (the "I set my goal and the game ignored it" class);
  * the force-keep must make the choice hold over ROLLED draws, not just the full pool;
  * the choice must outrank tier 0 -- and because no fixture in the corpus exercises that override
    on a finale-active kept set, TestChoiceOutranksFinale calls terminal_goal_ids DIRECTLY (a guard
    the corpus never triggers is an untested guard);
  * the finale's ten checks must SURVIVE as ordinary locations under a PCR goal -- the option moves
    the goal, it does not delete content.
"""
import random

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from Options import OptionError  # noqa: E402
from worlds.eldenring.data import FINALE_REGION, FINALE_REQUIRES  # noqa: E402
from worlds.eldenring.region_spine import (SPINE, REGIONS, GOAL_REGION, compute_kept,  # noqa: E402
                                           base_regions, dlc_regions, parent_chain)
from worlds.eldenring.features.finale import finale_active, finale_entries  # noqa: E402
from worlds.eldenring import contract  # noqa: E402
from worlds.eldenring.features.goal_locations import (  # noqa: E402
    GOAL_CHOICES, MALENIA_ENTRY_GRACE, MALENIA_GOAL_LOCATION, MALENIA_REGION,
    forced_regions, terminal_goal_ids, _major_boss_ids)

GAME = "Elden Ring"
PCR_REGION = "Enir Ilim"
PCR_IDS = set(_major_boss_ids(PCR_REGION))
FINALE_IDS = set(_major_boss_ids(FINALE_REGION))
# All four AP-id pins in this file moved DOWN by exactly 100 on 2026-08-25 (#1013): the
# Enia-vanilla exclusion removed her 100 shop checks from the location pool and every later id
# shifted. Pin by defeat flag if a fifth move is ever needed.
LORETTA_LOCATION = 7773790  # -1 after dead f400020 left the positional-id pool (#1111)


class TestGoalChoiceTable:
    """The table is data; these pin the data itself so a regen cannot quietly empty a choice."""

    def test_pcr_is_the_sole_major_of_enir_ilim(self):
        assert PCR_IDS == {7770670}, \
            "Promised Consort Radahn (f510430) must be Enir Ilim's only MajorBoss check"

    def test_finale_pair_is_hoarah_loux_and_the_elden_beast(self):
        assert FINALE_IDS == {7770655, 7770664}

    def test_every_choice_names_a_region_with_majors(self):
        for value, spec in GOAL_CHOICES.items():
            region, need = spec.region, spec.forced
            assert _major_boss_ids(region), f"goal {value!r} -> {region!r} has no MajorBoss checks"
            # A named goal must be able to GUARANTEE its region is in the seed, and there are now
            # exactly TWO ways to do that. This line read `assert need` until 2026-08-06, when
            # force-keeping was the only way. SPEC-ashen-capital-lock gave the finale the other
            # one: it is not a rollable region at all -- it is BUILT on every seed with the base
            # game in play and entered through the Ashen Capital Lock -- so there is nothing to
            # force, and forcing something would force a region the draw cannot even keep.
            # Anything else still has to force, and the empty-forced-set exemption is spelt as an
            # equality so a third choice cannot quietly inherit it.
            if region == FINALE_REGION:
                assert need == (), (
                    f"goal {value!r} names the never-rollable finale; its forced set must be "
                    f"empty, not {need!r}")
                assert finale_active(base_regions()), (
                    f"goal {value!r} is allowed to force nothing ONLY because its region exists "
                    f"on every base-game seed -- that is no longer true, so it needs a forced set")
            else:
                assert need, f"goal {value!r} forces nothing -- it could not guarantee its own region"

    def test_forced_regions_are_rollable_and_auto_forces_nothing(self):
        assert forced_regions("auto") == () and forced_regions(None) == ()
        assert forced_regions("not_a_choice") == ()
        for value in GOAL_CHOICES:
            assert set(forced_regions(value)) <= set(REGIONS), \
                "a forced region must be one compute_kept can actually keep"

    def test_named_choices_are_the_ones_that_were_asked_for(self):
        # A conscious-change gate: adding a value is fine, silently dropping one is not.
        assert {"elden_beast", "promised_consort", "malenia"} <= set(GOAL_CHOICES)
        assert GOAL_CHOICES["elden_beast"].region == FINALE_REGION
        assert GOAL_CHOICES["elden_beast"].forced == tuple(FINALE_REQUIRES)
        assert GOAL_CHOICES["promised_consort"].region == PCR_REGION
        assert GOAL_CHOICES["promised_consort"].forced == (PCR_REGION,)
        malenia = GOAL_CHOICES["malenia"]
        assert malenia.region == MALENIA_REGION
        assert malenia.forced == (MALENIA_REGION,)
        assert malenia.location_ids == (MALENIA_GOAL_LOCATION,)
        assert malenia.entry_grace == MALENIA_ENTRY_GRACE

    def test_malenia_pin_is_the_remembrance_check_not_every_haligtree_major(self):
        assert MALENIA_GOAL_LOCATION == 7770662
        assert MALENIA_GOAL_LOCATION in _major_boss_ids(MALENIA_REGION)
        assert LORETTA_LOCATION in _major_boss_ids(MALENIA_REGION)
        region, ids = terminal_goal_ids(set(REGIONS), "malenia")
        assert region == MALENIA_REGION
        assert ids == [MALENIA_GOAL_LOCATION]
        assert LORETTA_LOCATION not in ids


class TestChoiceOutranksFinale:
    """⭐ THE GUARD THE CORPUS NEVER TRIGGERS, called directly.

    Every generated fixture below either keeps the finale prerequisites or does not; none of them
    exercises "finale IS active AND the player chose something else" through the pure function. That
    branch is the entire point of the feature, so it gets a direct call and a mutation-style
    negative: the result must NOT be the finale pair."""

    def test_pcr_choice_beats_an_active_finale(self):
        kept = set(REGIONS)                      # full pool: the finale is unambiguously active
        assert finale_active(kept), "test basis broken: full pool must arm the finale"
        region, ids = terminal_goal_ids(kept, "promised_consort")
        assert region == PCR_REGION
        assert set(ids) == PCR_IDS
        assert set(ids) != FINALE_IDS, "the choice did NOT override tier 0 -- goal fell to the finale"

    def test_malenia_choice_beats_an_active_finale(self):
        kept = set(REGIONS)
        assert finale_active(kept)
        region, ids = terminal_goal_ids(kept, "malenia")
        assert region == MALENIA_REGION
        assert ids == [MALENIA_GOAL_LOCATION]
        assert set(ids) != FINALE_IDS

    def test_elden_beast_choice_agrees_with_tier_zero(self):
        kept = set(REGIONS)
        region, ids = terminal_goal_ids(kept, "elden_beast")
        assert region == FINALE_REGION and set(ids) == FINALE_IDS

    def test_auto_is_byte_identical_to_the_unchosen_ladder(self):
        # The default path must not have moved: same answer with no arg, None, and "auto".
        for kept in (set(REGIONS), set(base_regions()), {"Leyndell", "Altus"},
                     {"Limgrave"}, set(dlc_regions())):
            base = terminal_goal_ids(kept)
            assert terminal_goal_ids(kept, None) == base
            assert terminal_goal_ids(kept, "auto") == base

    def test_choice_holds_across_rolled_draws(self):
        # The force-keep is what makes the choice survive a random draw; 200 draws over every
        # legal N, each asserted to still goal on PCR.
        rng = random.Random(20260730)
        pool = list(REGIONS)
        for _ in range(200):
            n = rng.randint(1, len(pool) - 1)
            kept = compute_kept(n, rng, pool, forced=forced_regions("promised_consort"))
            assert PCR_REGION in kept, "force-keep failed: the chosen goal region was not kept"
            region, ids = terminal_goal_ids(kept, "promised_consort")
            assert region == PCR_REGION and set(ids) == PCR_IDS

    def test_forced_append_does_not_disturb_the_rng_stream(self):
        # 🛑 THE one implementation detail that could silently rewrite every existing rolled seed:
        # the forced append must happen AFTER rng.sample and must not consume randomness.
        #
        # RESTATED 2026-08-05 -- the PREMISE changed, not the numbers. This used to assert
        # `set(plain) <= set(forced)`: the kept set only ever GREW, because GOAL_REGION was appended
        # unconditionally and a named goal's region piled on top. GOAL_REGION is now force-kept ONLY
        # under `auto`, so naming a goal legitimately DROPS the capital (and Altus, its only parent)
        # from the draw. Subset in either direction is now the wrong shape; what survives is that
        # both draws sampled the SAME regions and differ ONLY inside their two force-keep closures.
        pool = list(REGIONS)
        capital_dropped = False
        for n in (1, 3, 8, 17, 25):
            r_plain, r_forced = random.Random(4242), random.Random(4242)
            plain = compute_kept(n, r_plain, pool)
            forced = compute_kept(n, r_forced, pool,
                                  forced=forced_regions("promised_consort"))
            # (1) the rng is left in the SAME state -- no extra draws were taken. UNCHANGED: this is
            # still the assertion that protects every rolled seed in existence.
            assert r_plain.random() == r_forced.random(), \
                "the forced append consumed randomness -- every rolled seed just changed"
            # (2) same seed, same n, same pool -> rng.sample drew the SAME base in both. So the two
            # kept sets may differ only by what each one FORCED, plus that region's REGION_PARENT
            # chain (derived from parent_chain, never re-pinned: Leyndell pulls Altus, Enir Ilim
            # pulls nothing). Anything else means the sample itself moved.
            goal_closure = {GOAL_REGION, *parent_chain(GOAL_REGION)}
            pcr_closure = {PCR_REGION, *parent_chain(PCR_REGION)}
            assert set(plain) - set(forced) <= goal_closure, \
                "the auto draw kept something the named-goal draw did not, outside the capital's " \
                "closure -- rng.sample no longer drew the same base"
            assert set(forced) - set(plain) <= pcr_closure, \
                "the named-goal draw kept something neither sampled nor forced"
            assert PCR_REGION in forced
            capital_dropped |= GOAL_REGION not in forced
        # (3) ⭐ THE NEGATIVE THAT MAKES (2) MEAN SOMETHING. Every assertion above is satisfied by
        # the OLD unconditional-append code, which kept the capital in 100% of seeds. At least one
        # of these draws must actually be free of it, or this test has stopped testing the change.
        assert capital_dropped, \
            "the capital was kept in EVERY named-goal draw -- the unconditional GOAL_REGION append " \
            "is back, and legs (1) and (2) cannot see it"


class GoalPCRFullSeed(WorldTestBase):
    """🔥 THE MOTIVATING CASE. Full base+DLC draw, PCR goal -> goalLocations is PCR alone."""
    game = GAME
    run_default_tests = False
    options = {"num_regions": 0, "goal": "promised_consort"}

    def test_goal_is_pcr_and_not_the_finale_pair(self):
        sd = self.world.fill_slot_data()
        assert set(sd["goalLocations"]) == {7770670}
        assert set(sd["goalLocations"]) != FINALE_IDS

    def test_enir_ilim_is_kept(self):
        assert PCR_REGION in self.world._kept()

    def test_the_finale_survives_as_ordinary_content(self):
        # Moving the goal must not delete the Ashen Capital: its region still exists, its ten
        # checks are still locations, and their flags still reach the client.
        assert finale_active(self.world._kept()), "finale must still be ARMED under a PCR goal"
        names = {loc.name for loc in self.multiworld.get_locations(self.player)}
        assert {n for (n, _a, _f) in finale_entries()} <= names
        lf = self.world.fill_slot_data()["locationFlags"]
        for (_n, ap_id, flag) in finale_entries():
            assert lf.get(str(ap_id)) == flag


class GoalAutoFullSeed(WorldTestBase):
    """The CONTRAST LEG -- the same draw with the default must be unchanged (the Ashen pair)."""
    game = GAME
    run_default_tests = False
    options = {"num_regions": 0}

    def test_goal_is_still_the_finale_pair(self):
        sd = self.world.fill_slot_data()
        assert set(sd["goalLocations"]) == FINALE_IDS


class GoalMaleniaPhysicalRoute(WorldTestBase):
    """#861: open at Canopy, walk Loretta -> Elphael -> Malenia, and goal on Malenia alone."""
    game = GAME
    run_default_tests = False
    options = {
        "num_regions": 3,
        "goal": "malenia",
        # Both deliberately try to widen/split every normal bundle. The named route must outrank
        # them or an unrelated setting turns Canopy-only back into a Prayer Room shortcut.
        "region_grace_unlock": "all",
        "grace_attunement": 4,
    }

    def test_haligtree_is_kept_and_its_lock_is_withheld(self):
        assert MALENIA_REGION in self.world._kept()
        assert all(item.name != "Haligtree Lock" for item in self.multiworld.itempool)
        assert "Haligtree Lock" not in self.world.kept_lock_names()

    def test_goal_is_malenia_alone(self):
        sd = self.world.fill_slot_data()
        assert sd[contract.GOAL_LOCATIONS] == [MALENIA_GOAL_LOCATION]
        assert sd[contract.LOCATION_FLAGS][str(MALENIA_GOAL_LOCATION)] == 510200
        assert LORETTA_LOCATION not in sd[contract.GOAL_LOCATIONS]

    def test_only_canopy_is_granted_even_under_all_plus_attunement(self):
        sd = self.world.fill_slot_data()
        assert sd[contract.REGION_GRACES]["Haligtree Lock"] == [MALENIA_ENTRY_GRACE]
        assert "Haligtree Lock" not in sd.get(contract.GRACE_ATTUNEMENT, {})
        assert MALENIA_ENTRY_GRACE == 71506


class GoalMaleniaComposesWithBothIndependentAxes(WorldTestBase):
    """The boss choice does not collapse either the Great-Rune or completed-region axis."""
    game = GAME
    run_default_tests = False
    options = {
        "num_regions": 3,
        "goal": "malenia",
        "item_shuffle": True,
        "ending_condition": "great_runes",
        "goal_great_runes": 4,
        "goal_region_unlock_policy": "regions_completed",
    }

    def test_malenia_rides_both_existing_gates(self):
        sd = self.world.fill_slot_data()
        assert sd[contract.GOAL_LOCATIONS] == [MALENIA_GOAL_LOCATION]
        assert sd["great_runes_required"] == 4
        assert "region_completion_goal_gate" in sd[contract.REQUIRES_CLIENT_FEATURES]
        assert contract.GOAL_REQUIRED_ITEMS not in sd
        assert sd[contract.REGION_GRACES]["Haligtree Lock"] == [MALENIA_ENTRY_GRACE]


@pytest.mark.parametrize("runes", [False, True], ids=["no_runes", "four_runes"])
@pytest.mark.parametrize("policy", ["items_held", "regions_completed", "none"])
def test_malenia_goal_axis_matrix_fills_clean(runes, policy):
    """All 2 x 3 combinations are real fills, not just six slot-data spellings."""
    from Fill import distribute_items_restrictive

    options = {
        "num_regions": 4,
        "goal": "malenia",
        "goal_region_unlock_policy": policy,
    }
    if runes:
        options.update(item_shuffle=True, ending_condition="great_runes", goal_great_runes=4)

    class _T(WorldTestBase):
        game = GAME
        auto_construct = False

    test = _T("runTest")
    test.options = options
    test.world_setup(20260819)
    try:
        distribute_items_restrictive(test.multiworld)
        sd = test.world.fill_slot_data()
        assert sd[contract.GOAL_LOCATIONS] == [MALENIA_GOAL_LOCATION]
        assert sd[contract.REGION_GRACES]["Haligtree Lock"] == [MALENIA_ENTRY_GRACE]
        assert sd["great_runes_required"] == (4 if runes else 0)
        assert (contract.GOAL_REQUIRED_ITEMS in sd) == (policy == "items_held")
    finally:
        test.tearDown()


class GoalEldenBeastNeedsNoForcing(WorldTestBase):
    """`goal: elden_beast` on a small draw, which used to be the case that PROVED the force-keep.

    It asserted that the choice dragged Farum Azula + Leyndell into a 3-region draw, because
    before SPEC-ashen-capital-lock the finale could not exist without both. Now it forces nothing
    and exists anyway, so the same protection -- "a named goal's region is really built" -- is
    asserted directly instead of through the mechanism that used to guarantee it.

    🛑 The old assertion could not simply be re-pointed at `finale_active(kept)`: the finale's
    existence keys on the seed's ELIGIBLE pool, not on the draw, and a 3-region draw with the DLC
    on can legitimately keep only DLC regions while the base game is very much in play. Asking
    `kept` there gives the wrong answer -- which is exactly why core exposes ONE answer,
    `world.gf_finale_active`, and why everything reads it."""
    game = GAME
    run_default_tests = False
    options = {"num_regions": 3, "goal": "elden_beast"}

    def test_the_finale_is_built_without_anything_being_forced(self):
        from worlds.eldenring.features.goal_locations import forced_regions
        assert forced_regions("elden_beast") == (), \
            "elden_beast must force NOTHING -- a force-keep here is num_regions lying again"
        assert self.world.gf_finale_active, \
            "goal: elden_beast on a base-game seed must have a finale to end on"
        # ...and the draw is genuinely small, so this is not passing because everything was kept.
        #
        # 🛑 THE BOUND IS DERIVED, NOT GUESSED, and that is a repair. This read
        # `<= 5`, and 5 is not a fact about anything: `num_regions: 3` keeps three DRAWN regions
        # plus the parent closure of those three, and REGION_PARENT holds a two-deep chain
        # (Sewer -> Leyndell -> Altus). One draw that lands on the Sewer therefore keeps six
        # legitimately, which is a real seed and not a bug -- so the assertion failed whenever the
        # suite's random seed found one, roughly 1 run in 15, on a test nobody was editing. A
        # magic-number bound over a random draw is a coin flip wearing an assertion.
        #
        # What it was defending is that the goal forces nothing extra in, and that is asserted
        # exactly two lines above and again, deterministically over 120 seeds, in
        # test_gf_region_selection.py::test_auto_keeps_only_its_draw_and_the_closure. What is left
        # for this line is the weaker claim it actually makes -- the seed is SMALL -- so it is
        # stated against the ceiling the data allows and the closure invariant that produced it.
        kept = set(self.world._kept())
        n = int(self.world.options.num_regions.value)
        deepest = max(len(parent_chain(r)) for r in REGIONS)
        assert len(kept) <= n * (1 + deepest), (
            "kept %d regions from a %d-region draw, past the %d the parent closure can explain "
            "(deepest REGION_PARENT chain is %d): %s"
            % (len(kept), n, n * (1 + deepest), deepest, sorted(kept)))
        # ...and every extra IS closure, never something kept for its own sake: a kept region's
        # ancestors are kept too, which is the only rule allowed to grow the set past n.
        for r in kept:
            for ancestor in parent_chain(r):
                assert ancestor in kept, (
                    "%s is kept but its ancestor %s is not -- the closure is broken, and the size "
                    "bound above is measuring something else" % (r, ancestor))

    def test_goal_is_the_pair(self):
        assert set(self.world.fill_slot_data()["goalLocations"]) == FINALE_IDS


class GoalPCRUnderDLCOnly(WorldTestBase):
    """dlc_only + PCR is the natural pairing and must generate (the finale is inert; the choice is
    not relying on tier 0 at all)."""
    game = GAME
    run_default_tests = False
    options = {"num_regions": 0, "dlc_only": True, "goal": "promised_consort"}

    def test_goal_is_pcr_with_the_finale_inert(self):
        kept = set(self.world._kept())
        assert not finale_active(kept), "dlc_only must leave the finale inert"
        assert set(self.world.fill_slot_data()["goalLocations"]) == {7770670}


class TestImpossibleChoicesDieAtGeneration:
    """A named goal its own toggles removed from play must RAISE, never fall back.

    This is the whole reason the design forces regions instead of falling back: a silent downgrade
    is indistinguishable, from the player's seat, from the option not working."""

    def _generate(self, **options):
        from test.general import setup_multiworld  # noqa: E402
        from worlds.eldenring.core import GreenfieldEldenRingWorld  # noqa: E402
        return setup_multiworld(GreenfieldEldenRingWorld, ("generate_early",), options=options)

    def test_pcr_without_dlc_raises(self):
        # The message must NAME the missing region: "your goal is impossible" without saying which
        # knob to turn is a bug report waiting to happen.
        with pytest.raises(OptionError, match="Enir Ilim"):
            self._generate(num_regions=0, enable_dlc=False, goal="promised_consort")

    def test_elden_beast_under_dlc_only_raises(self):
        # It used to match "Farum Azula|Leyndell": the forced set was those two regions, and the
        # raise came from core's `missing = [r for r in need if r not in eligible]` quantifier.
        # SPEC-ashen-capital-lock empties that set, so the quantifier now passes VACUOUSLY and
        # would happily pin a region dlc_only cannot build; core._resolve_goal_choice replaced it
        # with an explicit base-game-in-play test. Same protection, same reason it exists -- the
        # raise must say WHICH region is impossible and WHICH knob caused it -- asserted against
        # the new guard's message instead of the old one's.
        with pytest.raises(OptionError) as excinfo:
            self._generate(num_regions=0, dlc_only=True, goal="elden_beast")
        msg = str(excinfo.value)
        assert FINALE_REGION in msg, msg     # which region is impossible
        assert "base game" in msg, msg       # why it is impossible
        assert "dlc_only" in msg, msg        # which knob to turn

    def test_malenia_under_dlc_only_raises(self):
        with pytest.raises(OptionError, match="Haligtree"):
            self._generate(num_regions=0, dlc_only=True, goal="malenia")

    def test_the_legal_pairings_do_not_raise(self):
        # The mirror leg -- a guard that rejects everything is not a guard. These must generate.
        self._generate(num_regions=0, goal="promised_consort")
        self._generate(num_regions=0, goal="elden_beast")
        self._generate(num_regions=0, dlc_only=True, goal="promised_consort")
        self._generate(num_regions=0, enable_dlc=False, goal="elden_beast")
        self._generate(num_regions=0, enable_dlc=False, goal="malenia")
