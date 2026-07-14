"""THE FINALE: conditional Ashen-Capital / Elden-Throne checks (features/finale.py).

Ground truth (elden_ring_artifacts, 2026-07-14): common.emevd $Event(900) waits solely on flag
9116 (Maliketh dead, set only by m13_00 = Farum Azula) then warps into m11_05; $Event(1100) slots
6/7/23 award lots 10060/10070/10230 -> flags 510060/510070/510230; the m11_05 map lots are flags
11057000-11057100. The finale exists per-seed iff every data.FINALE_REQUIRES region is kept; when
it exists it IS the goal; fill may never strand progression behind an unburnable Erdtree (the
entrance requires every prerequisite Lock).
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring.data import (LOCATIONS, REGIONS, FINALE_REGION, FINALE_REQUIRES,  # noqa: E402
                                   FINALE_HOST_REGION, NOT_RANDOMIZED)
from worlds.eldenring.features.finale import finale_active, finale_entries  # noqa: E402
from worlds.eldenring.features.goal_locations import _major_boss_ids  # noqa: E402

GAME = "Elden Ring"
FINALE_FLAGS = {510060, 510070, 510230,
                11057000, 11057010, 11057020, 11057030, 11057040, 11057050, 11057100}


class TestFinaleData:
    def test_finale_bucket_is_exactly_the_derived_set(self):
        got = {f for (_n, _a, f) in LOCATIONS[FINALE_REGION]}
        assert got == FINALE_FLAGS

    def test_finale_region_is_never_rollable(self):
        assert FINALE_REGION not in REGIONS

    def test_requires_are_rollable_regions_and_host_is_a_member(self):
        assert set(FINALE_REQUIRES) <= set(REGIONS)
        assert FINALE_HOST_REGION in FINALE_REQUIRES
        # the derived prerequisite set (burn trigger + kick owner); a change here is a change to
        # the burn chain's ground truth and must be a conscious one.
        assert set(FINALE_REQUIRES) == {"Farum Azula", "Leyndell"}

    def test_finale_flags_left_the_not_randomized_ledger(self):
        dead = set(NOT_RANDOMIZED) & FINALE_FLAGS
        assert not dead, f"revived finale flags still ledgered as dropped: {sorted(dead)}"

    def test_invented_gideon_twins_are_ledgered_phantom(self):
        # 190540/190550 (synthetic 'LAC/LCA' twins of Gideon's real 510060): zero occurrences in
        # params or EMEVD -> phantom, ledgered, never checks.
        for fl in (190540, 190550):
            assert fl in NOT_RANDOMIZED and NOT_RANDOMIZED[fl].startswith("phantom_flag")
        for locs in LOCATIONS.values():
            assert not any(f in (190540, 190550) for (_n, _a, f) in locs)

    def test_coverage_predicate_matches_the_feature(self):
        # coverage.build_coverage re-computes finale-ness as FINALE_REQUIRES <= kept; this pins the
        # two predicates together so they cannot drift.
        for kept in (set(REGIONS), set(FINALE_REQUIRES), {"Limgrave"},
                     {"Leyndell"}, {"Farum Azula"}, {"Farum Azula", "Leyndell", "Altus"}):
            assert finale_active(kept) == (set(FINALE_REQUIRES) <= kept)

    def test_finale_majors_are_the_two_final_bosses(self):
        ids = _major_boss_ids(FINALE_REGION)
        flags = {f for (_n, a, f) in LOCATIONS[FINALE_REGION] if a in set(ids)}
        assert flags == {510070, 510230}, \
            "the finale goal must be Godfrey/Hoarah Loux + the Elden Beast, exactly"


class FinaleActiveSeed(WorldTestBase):
    """num_regions 0: every region kept -> the finale EXISTS, is goal, and is lock-gated."""
    game = GAME
    run_default_tests = False
    options = {"num_regions": 0}

    def test_locations_exist_and_flags_reach_the_client(self):
        names = {loc.name for loc in self.multiworld.get_locations(self.player)}
        finale_names = {n for (n, _a, _f) in finale_entries()}
        assert finale_names <= names, "finale locations missing from an active seed"
        sd = self.world.fill_slot_data()
        lf = sd["locationFlags"]
        for (_n, ap_id, flag) in finale_entries():
            assert lf.get(str(ap_id)) == flag, f"finale ap {ap_id} absent from locationFlags"

    def test_goal_is_the_finale(self):
        sd = self.world.fill_slot_data()
        assert set(sd["goalLocations"]) == set(_major_boss_ids(FINALE_REGION))

    def test_count_neutral(self):
        # items == locations (AP invariant): the feature contributed one item per finale location.
        # pre_fill (progression_surface) has already moved some pool items onto locations, so the
        # invariant at this stage is pool == still-EMPTY locations.
        locs = [l for l in self.multiworld.get_locations(self.player) if l.address is not None]
        pool = [i for i in self.multiworld.itempool if i.player == self.player]
        empty = [l for l in locs if l.item is None]
        assert len(pool) == len(empty), (len(pool), len(empty), len(locs))

    def test_entrance_requires_every_prerequisite_lock(self):
        # fill can never strand progression behind an unburnable Erdtree: the finale entrance
        # is closed until EVERY prerequisite Lock is held.
        from BaseClasses import CollectionState
        state = CollectionState(self.multiworld)
        region = self.multiworld.get_region(FINALE_REGION, self.player)
        entrances = region.entrances
        assert entrances, "finale region has no entrance"
        parent_names = {e.parent_region.name for e in entrances}
        assert parent_names == {FINALE_HOST_REGION}
        locks = [f"{r} Lock" for r in FINALE_REQUIRES]
        for i in range(len(locks)):
            state = CollectionState(self.multiworld)
            for j, lk in enumerate(locks):
                if j != i:
                    state.collect(self.world.create_item(lk), prevent_sweep=True)
            assert not all(e.access_rule(state) for e in entrances), \
                f"finale entrance opened without {locks[i]}"
        state = CollectionState(self.multiworld)
        for lk in locks:
            state.collect(self.world.create_item(lk), prevent_sweep=True)
        assert any(e.access_rule(state) for e in entrances), \
            "finale entrance must open once every prerequisite Lock is held"


class FinaleInertSeed(WorldTestBase):
    """spine num_regions=3 keeps Limgrave/Weeping/Stormveil (+ goal closure Leyndell/Altus) but NOT
    Farum Azula -> the finale must NOT exist and the goal falls back to the terminal region."""
    game = GAME
    run_default_tests = False
    options = {"num_regions": 3, "num_regions_order": "spine"}

    def test_finale_absent_and_goal_falls_back(self):
        kept = set(self.world._kept())
        assert not finale_active(kept), "test premise: Farum Azula must not be kept here"
        names = {loc.name for loc in self.multiworld.get_locations(self.player)}
        finale_names = {n for (n, _a, _f) in finale_entries()}
        assert not (finale_names & names), "finale locations leaked into a seed missing a prerequisite"
        sd = self.world.fill_slot_data()
        assert sd["goalLocations"], "goalLocations may never be empty"
        lf = sd["locationFlags"]
        for (_n, ap_id, _f) in finale_entries():
            assert str(ap_id) not in lf, "inert finale ap leaked into locationFlags"
        assert not any(r.name == FINALE_REGION for r in self.multiworld.get_regions(self.player))

    def test_count_neutral_when_inert(self):
        locs = [l for l in self.multiworld.get_locations(self.player) if l.address is not None]
        pool = [i for i in self.multiworld.itempool if i.player == self.player]
        empty = [l for l in locs if l.item is None]
        assert len(pool) == len(empty), (len(pool), len(empty), len(locs))


class FinaleDLCOnlySeed(WorldTestBase):
    """dlc_only: every base region sealed -> no Farum Azula, no Leyndell -> finale inert, goal
    non-empty via the DLC terminal-region ladder."""
    game = GAME
    run_default_tests = False
    options = {"dlc_only": True, "num_regions": 4}

    def test_finale_inert_goal_nonempty(self):
        kept = set(self.world._kept())
        assert not finale_active(kept)
        sd = self.world.fill_slot_data()
        assert sd["goalLocations"]
        names = {loc.name for loc in self.multiworld.get_locations(self.player)}
        assert not ({n for (n, _a, _f) in finale_entries()} & names)
