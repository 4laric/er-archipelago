"""goalLocations = clear the TERMINAL region (deepest kept by spine rank) -- never Leyndell-by-default.

Guards the 2026-07-14 playtest bug and the module docstring's invariants (features/goal_locations.py):
the old _terminal_region preferred GOAL_REGION whenever kept, GOAL_REGION is ALWAYS kept on a base
seed, and Leyndell's boss set is exactly one location (Morgott) -- so the client sent Goal (and
released every check) on Morgott's death on EVERY base seed, regardless of how deep the chain ran.
The docstring also promised Hoarah Loux and the Elden Beast as goal locations; neither is a location
at all. These tests fail if either lie ever comes back:
  * on a seed keeping regions deeper than Leyndell, the goal is NOT Morgott;
  * the goal ids are exactly the MajorBoss checks of the deepest kept region that has any;
  * goalLocations is never empty, across rolled draws including majorless dlc_only corners.
"""
import random

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring.data import LOCATIONS  # noqa: E402
from worlds.eldenring.region_spine import SPINE, GOAL_REGION, compute_kept, base_regions, dlc_regions  # noqa: E402
from worlds.eldenring.features.goal_locations import terminal_goal_ids, _major_boss_ids, _by_depth  # noqa: E402
from worlds.eldenring.features.finale import finale_active  # noqa: E402
from worlds.eldenring.data import FINALE_REGION, FINALE_REQUIRES  # noqa: E402

FINALE_IDS = set(_major_boss_ids(FINALE_REGION))

GAME = "Elden Ring"
MORGOTT_IDS = set(_major_boss_ids(GOAL_REGION))


class TestTerminalGoalPure:
    def test_deeper_kept_region_beats_leyndell(self):
        # every base spine suffix deeper than Leyndell must out-rank the capital as the terminal.
        #
        # ⭐ RE-PREMISED 2026-08-06 (SPEC-ashen-capital-lock). This is a TIER 1 test -- the spine
        # ladder -- and tier 0 now outranks the ladder on EVERY base-game seed, because the finale
        # is built unconditionally and entered by item rather than existing only when Farum Azula
        # and Leyndell were both kept. The old body carried an `if finale_active(kept)` branch for
        # that one kept set; with the finale always live, that branch would swallow every case here
        # and the ladder would go entirely untested. So the ladder is exercised with
        # finale_built=False -- the real `dlc_only` shape, and the exact keyword terminal_goal_ids
        # grew for this -- and the precedence claim the deleted branch used to make for one region
        # is asserted below for ALL of them, which is strictly more than it said.
        leyndell_rank = SPINE.index(GOAL_REGION)
        deeper = [r for r in base_regions() if SPINE.index(r) > leyndell_rank and _major_boss_ids(r)]
        assert deeper, "spine data lost its deeper-than-Leyndell majors; test basis broken"
        for r in deeper:
            kept = {GOAL_REGION, "Altus", r}
            region, ids = terminal_goal_ids(kept, finale_built=False)
            assert region == r, f"terminal must be {r}, got {region}"
            assert set(ids) == set(_major_boss_ids(r))
            assert set(ids) != MORGOTT_IDS
            # tier 0 outranks the ladder for the SAME kept set
            region0, ids0 = terminal_goal_ids(kept, finale_built=True)
            assert region0 == FINALE_REGION and set(ids0) == FINALE_IDS, (
                f"tier 0 must beat the ladder for kept {sorted(kept)}, got {region0}")

    def test_leyndell_terminal_only_when_deepest(self):
        # finale_built=False for the same reason as above: this asserts TIER 1, and on a base-game
        # kept set tier 0 (the Ashen Capital) would otherwise own the answer outright.
        region, ids = terminal_goal_ids({"Limgrave", "Altus", GOAL_REGION}, finale_built=False)
        # Sewer outranks Leyndell in SPINE but is not kept here; the capital is genuinely terminal.
        assert region == GOAL_REGION and set(ids) == MORGOTT_IDS

    def test_rolled_sweep_never_empty(self):
        rng = random.Random(20260714)
        pools = [base_regions(), dlc_regions(), list(base_regions()) + list(dlc_regions())]
        for _ in range(600):
            pool = pools[rng.randrange(3)]
            n = rng.randrange(1, len(pool) + 1)
            kept = compute_kept(n, rng, pool)
            region, ids = terminal_goal_ids(set(kept))
            assert ids, f"empty goal for kept {sorted(kept)}"
            if finale_active(kept):
                # tier 0: the finale region exists this seed (features/finale.py) and IS the goal.
                assert region == FINALE_REGION and set(ids) == FINALE_IDS
            else:
                assert region in kept
                kept_ap_ids = {aid for r in kept for (_n, aid, _f) in LOCATIONS.get(r, ())}
                assert set(ids) <= kept_ap_ids, "goal ids must live in kept regions"

    def test_every_region_currently_carries_a_major(self):
        # As of the 2026-07 "4 new region majors" regen every region has a MajorBoss-tagged check,
        # so tier 1 always resolves and tier 2 below is DATA-dead (defensive only). If a regen ever
        # drops a region's last major, this stops being true -- that is fine (tier 2 exists for it),
        # but it should be a conscious data change, so this test names it.
        majorless = [r for r in base_regions() + dlc_regions() if not _major_boss_ids(r)]
        assert not majorless, f"regions lost their last MajorBoss check: {majorless}"

    def test_majorless_kept_set_falls_back_to_region_clear(self, monkeypatch):
        # tier 2 (defensive): with the major tables emptied, the goal degrades to clearing the
        # terminal region -- every non-missable check of the deepest kept region, never empty.
        from worlds.eldenring.features import goal_locations as gl
        monkeypatch.setattr(gl, "LOCATION_TAGS", {})
        monkeypatch.setattr(gl, "REGION_BOSSES", {})
        kept = {"Limgrave", "Altus"}
        region, ids = gl.terminal_goal_ids(kept)
        assert region == "Altus" and ids, "majorless fallback must clear the terminal region"
        altus_ids = {aid for (_n, aid, _f) in LOCATIONS.get("Altus", ())}
        assert set(ids) <= altus_ids
        from worlds.eldenring.missable_locations import MISSABLE_LOCATIONS
        assert not (set(ids) & set(MISSABLE_LOCATIONS)),             "a missable check may never be part of the goal (permanently losable)"


class GoalDeepSpineSeed(WorldTestBase):
    """Full pool kept (num_regions 0): the base game is in play, so THE FINALE exists and IS the
    goal -- Godfrey/Hoarah Loux + the Elden Beast, the game's real terminus. NOT Morgott, and NOT
    Farum Azula's majors (the ruling 2026-07-14: the Ashen Capital outranks the spine). The
    existence rule moved on 2026-08-06 (SPEC-ashen-capital-lock) from "Farum Azula AND Leyndell are
    both kept" to "any base-game region is in play"; a full-pool seed satisfied both, so what this
    fixture asserts is unchanged."""
    game = GAME
    run_default_tests = False
    options = {"num_regions": 0}

    def test_goal_is_the_finale_not_morgott(self):
        sd = self.world.fill_slot_data()
        got = set(sd["goalLocations"])
        kept = set(self.world._kept())
        assert finale_active(kept), "num_regions 0 keeps base-game regions, so the finale is built"
        assert got == FINALE_IDS, "with the finale active the goal must be its major bosses"
        assert got != MORGOTT_IDS, \
            "goal collapsed to Morgott on a seed keeping regions deeper than Leyndell"
        assert got, "goalLocations may never be empty"


class GoalLadderDecidesSeed(WorldTestBase):
    """The goal is the DEEPEST KEPT region, decided by depth and not by any default -- asserted on
    real slot data rather than on the pure function.

    ⭐ WAS GoalCapitalRunSeed, "the capital IS a legitimate goal when it is the deepest kept
    region": the other half of the 2026-07-14 bug, whose fix must not overcorrect into never
    goaling on Morgott. That FIXTURE is unbuildable as of SPEC-ashen-capital-lock (2026-08-06) --
    the finale is built on every seed with the base game in play and tier 0 outranks the ladder, so
    no base-game seed can produce a Morgott goal at all any more. The pure-function half of the old
    claim survives verbatim in TestTerminalGoalPure.test_leyndell_terminal_only_when_deepest, which
    now says it with finale_built=False.

    What is re-premised here is the SEED half, moved to `dlc_only` -- the one mode with no finale,
    and therefore the one mode where the ladder still decides a real seed's goal. The protection is
    the same one, restated without naming the capital: search a fixed seed sequence for a draw
    whose terminal region is NOT the pool's globally deepest region (the case a "prefer region X"
    default would get wrong), and assert the SLOT DATA names that drawn region's majors.

    Exhausting the sequence FAILS rather than skips: a guard that never fires is an untested guard.
    """
    game = GAME
    run_default_tests = False
    # N=2, not 1: `start_with_region_lock` is frozen ON and core's clamp needs at least one lock
    # left in the pool, and a dlc_only seed mints no Ashen Capital Lock to make up the difference.
    # 2 is the floor that generates, and it keeps the draw narrow enough that the deepest DLC
    # region is usually NOT in it -- which is the case this fixture is hunting for.
    options = {"dlc_only": True, "num_regions": 2}
    SEEDS = tuple(range(12))

    def test_goal_is_the_deepest_kept_region_not_a_default(self):
        deepest_in_pool = max(dlc_regions(), key=SPINE.index)
        for seed in self.SEEDS:
            self.world_setup(seed=seed)
            kept = set(self.world._kept())
            assert not finale_active(kept), \
                "dlc_only seals the base game, so the finale must be inert -- otherwise tier 0 " \
                "owns this goal and the ladder is not what is under test"
            region, ids = terminal_goal_ids(kept)
            if region == deepest_in_pool:
                continue          # uninformative: a fixed default and the ladder would agree here
            sd = self.world.fill_slot_data()
            assert set(sd["goalLocations"]) == set(_major_boss_ids(region)), (
                "seed %d keeps %s as its deepest region, so the goal must be its majors; slot "
                "data said %s" % (seed, region, sorted(sd["goalLocations"])))
            assert region in kept
            assert region == max(kept, key=SPINE.index), (
                "the goal region must be the deepest KEPT region by spine rank, not a preference")
            return
        self.fail("no seed in range(%d) produced a draw whose TERMINAL region is anything but the "
                  "pool's deepest, so the decided-by-depth case went UNTESTED. Widen SEEDS, or the "
                  "draw/ladder has changed such that only the deepest region can ever be terminal "
                  "-- which would be a real regression of the 2026-07-14 ruling." % len(self.SEEDS))
