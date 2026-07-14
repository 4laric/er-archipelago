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

GAME = "Elden Ring"
MORGOTT_IDS = set(_major_boss_ids(GOAL_REGION))


class TestTerminalGoalPure:
    def test_deeper_kept_region_beats_leyndell(self):
        # every base spine suffix deeper than Leyndell must out-rank the capital as the terminal.
        leyndell_rank = SPINE.index(GOAL_REGION)
        deeper = [r for r in base_regions() if SPINE.index(r) > leyndell_rank and _major_boss_ids(r)]
        assert deeper, "spine data lost its deeper-than-Leyndell majors; test basis broken"
        for r in deeper:
            region, ids = terminal_goal_ids({GOAL_REGION, "Altus", r})
            assert region == r, f"terminal must be {r}, got {region}"
            assert set(ids) == set(_major_boss_ids(r))
            assert set(ids) != MORGOTT_IDS

    def test_leyndell_terminal_only_when_deepest(self):
        region, ids = terminal_goal_ids({"Limgrave", "Altus", GOAL_REGION})
        # Sewer outranks Leyndell in SPINE but is not kept here; the capital is genuinely terminal.
        assert region == GOAL_REGION and set(ids) == MORGOTT_IDS

    def test_rolled_sweep_never_empty(self):
        rng = random.Random(20260714)
        pools = [base_regions(), dlc_regions(), list(base_regions()) + list(dlc_regions())]
        for _ in range(600):
            pool = pools[rng.randrange(3)]
            n = rng.randrange(1, len(pool) + 1)
            kept = compute_kept(n, "rolled", rng, pool)
            region, ids = terminal_goal_ids(set(kept))
            assert ids, f"empty goal for kept {sorted(kept)}"
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
    """Full base spine kept (num_regions 0, DLC off): the terminal region is Farum Azula (deepest
    base region), so the emitted goal must be its majors -- NOT Morgott."""
    game = GAME
    run_default_tests = False
    options = {"num_regions": 0}

    def test_goal_is_terminal_not_morgott(self):
        sd = self.world.fill_slot_data()
        got = set(sd["goalLocations"])
        kept = set(self.world._kept())
        deepest_with_major = next(r for r in _by_depth(kept) if _major_boss_ids(r))
        assert got == set(_major_boss_ids(deepest_with_major))
        assert got != MORGOTT_IDS, \
            "goal collapsed to Morgott on a seed keeping regions deeper than Leyndell"
        assert got, "goalLocations may never be empty"


class GoalCapitalRunSeed(WorldTestBase):
    """spine num_regions=3: kept = Limgrave/Weeping/Stormveil + goal closure (Leyndell+Altus); the
    capital IS the terminal region, so Morgott is the right goal here -- by depth, not preference."""
    game = GAME
    run_default_tests = False
    options = {"num_regions": 3, "num_regions_order": "spine"}

    def test_goal_is_morgott_because_terminal(self):
        sd = self.world.fill_slot_data()
        assert set(sd["goalLocations"]) == MORGOTT_IDS
