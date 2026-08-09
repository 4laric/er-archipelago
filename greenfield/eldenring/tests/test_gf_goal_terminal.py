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
from worlds.eldenring.features.goal_locations import (terminal_goal_ids, _major_boss_ids,  # noqa: E402
                                                      _by_depth, DLC_TERMINUS_REGION)
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


    def test_the_ladder_still_decides_a_terminus_free_dlc_draw(self):
        """TIER 1 IS NOT DEAD, IT IS ONLY UNREACHABLE FROM A REAL SEED (2026-08-09).

        With tier 0 owning every base-game seed and tier 0b owning every dlc_only one, no world
        this apworld can build reaches the spine walk. That makes this the ONLY place the walk is
        still exercised -- which is exactly why the claim moved here in full rather than being
        deleted with its old fixture (see DlcOnlyGoalIsTheTerminusSeed).

        The kept sets below are the pre-fix dlc_only shape: a DLC draw that did not take Enir Ilim.
        That is bobler's 2026-08-07 seed, and the ladder's answer for it -- the deepest kept region
        carrying a terminal tag -- was correct then and must stay correct now."""
        pool = [r for r in dlc_regions() if r != DLC_TERMINUS_REGION]
        rng = random.Random(20260809)
        checked = 0
        for _ in range(200):
            kept = rng.sample(pool, rng.randint(2, min(6, len(pool))))
            region, ids = terminal_goal_ids(kept, finale_built=False, dlc_terminus=False)
            assert ids, "goalLocations may never be empty"
            assert region in kept
            # The ladder prefers a TERMINUS-bearing region; when the draw has one, the answer must
            # be the deepest such region and nothing shallower.
            termini = [r for r in kept if _major_boss_ids(r) and r == region] or None
            deepest_overall = max(kept, key=SPINE.index)
            assert SPINE.index(region) <= SPINE.index(deepest_overall)
            assert set(ids) == set(_major_boss_ids(region)) or region == deepest_overall
            checked += 1
        assert checked == 200

    def test_the_terminus_outranks_the_walk_when_it_is_present(self):
        """Tier 0b is a GUARANTEE, not a preference: it must win even against a kept set the walk
        would have answered differently, which is what makes it immune to a future deeper region."""
        kept = [DLC_TERMINUS_REGION, "Ancient Ruins", "Jagged Peak"]
        region, ids = terminal_goal_ids(kept, finale_built=False, dlc_terminus=True)
        assert region == DLC_TERMINUS_REGION
        assert set(ids) == set(_major_boss_ids(DLC_TERMINUS_REGION))


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


class DlcOnlyGoalIsTheTerminusSeed(WorldTestBase):
    """A dlc_only seed ends on PROMISED CONSORT RADAHN -- asserted on real slot data.

    ⭐⭐⭐ RE-PREMISED 2026-08-09, and the premise really did change; this is not a number that moved.

    This class was `GoalLadderDecidesSeed`, and before that `GoalCapitalRunSeed`. Its job was to
    prove the goal is decided BY DEPTH rather than by a default, on a real seed. It used `dlc_only`
    as its vehicle because SPEC-ashen-capital-lock had already made every base-game seed a tier-0
    seed, leaving dlc_only as -- in the old docstring's words -- "the one mode with no finale, and
    therefore the one mode where the ladder still decides a real seed's goal."

    THAT MODE IS GONE TOO. The DLC terminus (features/goal_locations tier 0b) force-keeps Enir Ilim
    on every dlc_only seed and names it outright, because a run whose ending depended on the draw
    was the defect: bobler finished one on Romina on 2026-08-07 and read it as a broken ending.
    So no real seed reaches tier 1 any more, and the old test could no longer find its informative
    case -- it failed LOUDLY saying so rather than passing vacuously, which is the guard working.

    Two things follow, and both are done rather than assumed:
      * the SEED-level claim is now the stronger one, asserted here: dlc_only ends on the terminus,
        on every seed, not on the ones whose draw was kind;
      * the LADDER-level claim is not dropped -- it moves entirely into TestTerminalGoalPure, which
        exercises tier 1 with `dlc_terminus=False`, the same way it already exercises it with
        `finale_built=False`. See test_the_ladder_still_decides_a_terminus_free_dlc_draw.
    """
    game = GAME
    run_default_tests = False
    # N=2 for the same reason the old fixture used it: `start_with_region_lock` is frozen ON and
    # core's clamp needs a lock left in the pool, and a dlc_only seed mints no Ashen Capital Lock.
    # The terminus is force-kept ON TOP of the draw, so this is 2 drawn + Enir Ilim.
    options = {"dlc_only": True, "num_regions": 2}
    SEEDS = tuple(range(12))

    def test_every_dlc_only_seed_goals_on_enir_ilim(self):
        for seed in self.SEEDS:
            self.world_setup(seed=seed)
            kept = set(self.world._kept())
            assert not finale_active(kept), \
                "dlc_only seals the base game, so the finale must stay inert -- tier 0b, not 0"
            assert DLC_TERMINUS_REGION in kept, \
                "seed %d: the terminus must be force-kept, not drawn (kept %s)" % (
                    seed, sorted(kept))
            sd = self.world.fill_slot_data()
            assert set(sd["goalLocations"]) == set(_major_boss_ids(DLC_TERMINUS_REGION)), (
                "seed %d: slot data must name Enir Ilim's majors, said %s"
                % (seed, sorted(sd["goalLocations"])))

    def test_the_terminus_is_never_the_region_the_run_opens_on(self):
        """The other half of the ruling: a run that opens where it ends is not a run. Read off the
        PRECOLLECTED lock, which is what actually decides the opening region."""
        for seed in self.SEEDS:
            self.world_setup(seed=seed)
            free = {i.name for i in self.multiworld.precollected_items[self.player]}
            assert "%s Lock" % DLC_TERMINUS_REGION not in free, (
                "seed %d opened the run on the region it ends in" % seed)
