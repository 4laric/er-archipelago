"""THE FINALE: the Ashen-Capital / Elden-Throne checks (features/finale.py).

Ground truth (elden_ring_artifacts, 2026-07-14): common.emevd $Event(900) waits solely on flag
9116 (Maliketh dead, set only by m13_00 = Farum Azula) then warps into m11_05; $Event(1100) slots
6/7/23 award lots 10060/10070/10230 -> flags 510060/510070/510230; the m11_05 map lots are flags
11057000-11057100.

⭐ SPEC-ashen-capital-lock (2026-08-06) changed the per-seed RULE, not that ground truth. The burn
is an ITEM now, so the finale exists on every seed with the base game in play and its entrance is
gated on one synthetic `Ashen Capital Lock` rather than on a prerequisite region set. What this
file pins is the pair of invariants that survived the change -- when the finale exists it IS the
goal, and fill can never strand progression behind an unreachable Erdtree -- plus the emptiness of
FINALE_REQUIRES itself, because an empty tuple that nothing asserts about is how a vacuous
quantifier gets to live for a year. The gauntlet's own wiring is in test_gf_ashen_capital_lock.py.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring.data import (LOCATIONS, REGIONS, HUB, FINALE_REGION,  # noqa: E402
                                   FINALE_REQUIRES, FINALE_HOST_REGION, FINALE_BURN_REGION,
                                   FINALE_KICK_OWNER, NOT_RANDOMIZED)
from worlds.eldenring.features.finale import (finale_active, finale_entries,  # noqa: E402
                                              base_game_in_play, ASHEN_LOCK_ITEM)
from worlds.eldenring.region_spine import DLC_REGIONS  # noqa: E402
from worlds.eldenring.features.goal_locations import _major_boss_ids  # noqa: E402

GAME = "Elden Ring"
# TWELVE, not ten, since 2026-08-06 -- and the two extras are named because a count that moves
# without an explanation is how a regression gets laundered into a test (CONTRIBUTING).
#   3 boss rewards            510060 Gideon / 510070 Godfrey / 510230 Elden Beast
#   7 self-encoded map lots   1105xxxx, the m11_05 ItemLotParam rows
#   2 EVENT awards            9500 Mending Rune of Perfect Order + 400500 Goldmask's Rags, both
#                             off the Goldmask corpse (common90005750), which exists only in the
#                             post-burn capital. msb_flag_region.tsv placed them in m11_05 all
#                             along; data.py regioned them as base LEYNDELL, because they are
#                             neither boss rewards nor 1105xxxx lots and so rode the "around Elden
#                             Throne" place-name join. That claimed the Leyndell Lock reached them.
#                             It does not -- only the Ashen Capital Lock does. Found by
#                             test_gf_region_provenance_oracle the moment the Ashen Capital took
#                             ownership of bucket 11050 (Fable ruling 2026-08-06).
FINALE_EVENT_AWARD_FLAGS = {9500, 400500}
FINALE_FLAGS = {510060, 510070, 510230,
                11057000, 11057010, 11057020, 11057030, 11057040, 11057050,
                11057100} | FINALE_EVENT_AWARD_FLAGS


class TestFinaleData:
    def test_finale_bucket_is_exactly_the_derived_set(self):
        got = {f for (_n, _a, f) in LOCATIONS[FINALE_REGION]}
        assert got == FINALE_FLAGS

    def test_finale_region_is_never_rollable(self):
        assert FINALE_REGION not in REGIONS

    def test_nothing_is_force_kept_and_the_host_is_the_hub(self):
        """SPEC-ashen-capital-lock decisions 1 and 2, asserted where they are emitted.

        FINALE_REQUIRES was ('Farum Azula', 'Leyndell') and is now (), which is the whole reason
        `num_regions: 1` can finally keep one region. It is asserted EXPLICITLY rather than left
        to a `set(FINALE_REQUIRES) <= set(kept)` that now passes for free -- see
        test_the_emptiness_is_not_load_bearing_anywhere below."""
        assert FINALE_REQUIRES == (), \
            "the Ashen Capital Lock model force-keeps NOTHING; a non-empty FINALE_REQUIRES means " \
            "a force-keep crept back and num_regions is lying about its draw size again"
        assert FINALE_HOST_REGION == HUB, \
            "you reach the Ashen Capital by warping to its own graces, so it hangs off the hub"
        # The derivation still runs and still has to name real regions: the vanilla burn chain is
        # what natural_progression rides, and the kick owner is the provenance of the bucket split.
        assert FINALE_BURN_REGION in REGIONS and FINALE_KICK_OWNER in REGIONS
        assert FINALE_BURN_REGION == "Farum Azula" and FINALE_KICK_OWNER == "Leyndell"

    def test_the_emptiness_is_not_load_bearing_anywhere(self):
        """A guard that quantifies over FINALE_REQUIRES now passes for ANY input. Prove that no
        shipped predicate does that, by feeding `finale_active` a kept set that satisfies the OLD
        rule and one that cannot: the answers must differ on the BASE-GAME question, not on the
        prerequisite one."""
        assert set(FINALE_REQUIRES) <= set()          # the vacuous form, stated so it is visible
        assert finale_active({"Limgrave"}) is True     # old rule said False
        assert finale_active(set(DLC_REGIONS)) is False

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
        # coverage.build_coverage re-derives finale-ness for its world-less callers; this pins the
        # two predicates together so they cannot drift. (With a world it asks the world instead --
        # coverage._finale_base_game_in_play is only the static half.)
        from worlds.eldenring.coverage import _finale_base_game_in_play
        for kept in (set(REGIONS), {"Limgrave"}, {"Leyndell"}, {"Farum Azula"},
                     set(DLC_REGIONS), {"Belurat", "Ensis"}, set()):
            assert finale_active(kept) == base_game_in_play(kept)
            assert _finale_base_game_in_play(kept) == base_game_in_play(kept)

    def test_the_goldmask_awards_live_in_the_capital_they_are_placed_in(self):
        """The two event awards, and the protection that has to survive their move.

        They are QUEST-GATED (Goldmask's questline), so they are MISSABLE -- fill never puts
        required progression on them. That is a narrower instrument than the region, and it is why
        the old mis-regioning never stranded anybody. It is not a substitute for the region being
        right: a missable in the wrong region still lies to the tracker and to any future rule
        that trusts data.py."""
        from worlds.eldenring.missable_locations import MISSABLE_LOCATIONS
        here = {f: a for (_n, a, f) in LOCATIONS[FINALE_REGION]}
        for flag in sorted(FINALE_EVENT_AWARD_FLAGS):
            assert flag in here, f"event award {flag} is not in the Ashen Capital bucket"
            assert here[flag] in MISSABLE_LOCATIONS, (
                f"event award {flag} lost its missable tag when it changed region -- "
                f"MISSABLE_LOCATIONS is flag-keyed, so this means the regen dropped it")
        for region, locs in LOCATIONS.items():
            if region == FINALE_REGION:
                continue
            assert not (FINALE_EVENT_AWARD_FLAGS & {f for (_n, _a, f) in locs}), \
                f"an event award is ALSO in {region!r} -- the join duplicated instead of moving"

    def test_finale_majors_are_the_two_final_bosses(self):
        ids = _major_boss_ids(FINALE_REGION)
        flags = {f for (_n, a, f) in LOCATIONS[FINALE_REGION] if a in set(ids)}
        assert flags == {510070, 510230}, \
            "the finale goal must be Godfrey/Hoarah Loux + the Elden Beast, exactly -- the " \
            "bucket gained two members in 2026-08-06 and neither may become a goal location"


class FinaleActiveSeed(WorldTestBase):
    """num_regions 0: every region kept -> the finale EXISTS, is goal, and is lock-gated."""
    game = GAME
    run_default_tests = False
    options = {"num_regions": 0}

    def _finale_entrances(self):
        entrances = self.multiworld.get_region(FINALE_REGION, self.player).entrances
        assert entrances, "finale region has no entrance"
        assert {e.parent_region.name for e in entrances} == {FINALE_HOST_REGION}
        return entrances


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

    def test_the_ashen_lock_is_never_the_precollected_anchor(self):
        """SPEC decision 2: the Ashen Capital is not a place you play, so it can never be the
        region you start in. It is also the ONE lock whose precollection would hand the player the
        end of the game at connect -- `goalRequiredItems` would be satisfiable in sphere 0."""
        free = {i.name for i in self.multiworld.precollected_items[self.player]}
        assert ASHEN_LOCK_ITEM not in free

    def test_entrance_is_exactly_the_ashen_lock(self):
        """Held or not-held, and nothing else: the finale's reachability is one item now.

        Checked against a state stripped of the start anchor's free lock, so the answer is
        seed-independent -- the old two-lock matrix flaked at the anchor's draw rate because one
        leg asserted "closed without X" on ~3% of seeds where X was precollected."""
        from BaseClasses import CollectionState
        entrances = self._finale_entrances()
        mw, saved = self.multiworld, list(self.multiworld.precollected_items[self.player])
        mw.precollected_items[self.player] = [i for i in saved if not i.name.endswith(" Lock")]
        try:
            closed = CollectionState(mw)
            assert not any(e.access_rule(closed) for e in entrances), \
                "finale entrance open while holding no locks at all"
            open_ = CollectionState(mw)
            open_.collect(self.world.create_item(ASHEN_LOCK_ITEM), prevent_sweep=True)
            assert all(e.access_rule(open_) for e in entrances), \
                f"finale entrance must open on {ASHEN_LOCK_ITEM} alone"
            # ...and no OTHER lock opens it. This is the half that would catch a silent revert to
            # the region-prerequisite rule: under that rule holding Leyndell + Farum Azula opened
            # the door, and holding them now must not.
            others = CollectionState(mw)
            for r in (FINALE_BURN_REGION, FINALE_KICK_OWNER):
                others.collect(self.world.create_item(f"{r} Lock"), prevent_sweep=True)
            assert not any(e.access_rule(others) for e in entrances), \
                "the OLD prerequisite pair still opens the finale -- the burn is an item now"
        finally:
            mw.precollected_items[self.player] = saved


class FinaleUnconditionalOnASmallDraw(WorldTestBase):
    """THE change, stated as a seed: a base-game draw that keeps NEITHER old prerequisite still
    gets the finale.

    Before SPEC-ashen-capital-lock this class could not exist -- `goal: auto` force-kept Leyndell,
    whose parent closure dragged Altus in, so the finale's prerequisites were kept by construction
    and `num_regions: 1` produced four regions. The premise is VERIFIED per run rather than
    assumed (the draw is random): walk a fixed seed sequence until one keeps neither prerequisite,
    and fail loudly if none does -- a data change that shifts the pool moves the search, not the
    test."""
    game = GAME
    run_default_tests = False
    options = {"num_regions": 2}
    SEEDS = tuple(range(24))

    def _setup_draw_without_the_old_prerequisites(self):
        for seed in self.SEEDS:
            self.world_setup(seed=seed)
            kept = set(self.world._kept())
            if not {FINALE_BURN_REGION, FINALE_KICK_OWNER} & kept:
                return seed, kept
        self.fail("no seed in %r kept NEITHER %s nor %s at num_regions=2, so the whole point of "
                  "this spec went untested -- widen SEEDS, or something is force-keeping them "
                  "again (which is the regression)"
                  % (self.SEEDS, FINALE_BURN_REGION, FINALE_KICK_OWNER))

    def test_finale_exists_and_is_the_goal_without_either_prerequisite(self):
        _seed, kept = self._setup_draw_without_the_old_prerequisites()
        assert self.world.gf_finale_active, \
            f"finale inert on a base-game seed (kept={sorted(kept)})"
        names = {loc.name for loc in self.multiworld.get_locations(self.player)}
        assert {n for (n, _a, _f) in finale_entries()} <= names
        sd = self.world.fill_slot_data()
        assert set(sd["goalLocations"]) == set(_major_boss_ids(FINALE_REGION))
        # ...and the lock that opens it was minted exactly once, as progression. Counted across
        # the pool AND the already-placed locations: pre_fill (progression_surface) may already
        # have placed it, and a test that only looked at `itempool` would read that as "never
        # minted" -- a false red that invites someone to relax the real assertion.
        minted = [i for i in self.multiworld.itempool
                  if i.player == self.player and i.name == ASHEN_LOCK_ITEM]
        placed = [l.item for l in self.multiworld.get_locations(self.player)
                  if l.item is not None and l.item.name == ASHEN_LOCK_ITEM]
        free = [i for i in self.multiworld.precollected_items[self.player]
                if i.name == ASHEN_LOCK_ITEM]
        assert not free, "the Ashen Capital Lock may never be precollected -- it ends the run at connect"
        both = minted + placed
        assert len(both) == 1, ("expected exactly one %s: %d in pool + %d placed"
                                % (ASHEN_LOCK_ITEM, len(minted), len(placed)))
        assert both[0].advancement, "the burn item must be progression"

    def test_count_neutral_on_that_draw(self):
        self._setup_draw_without_the_old_prerequisites()
        locs = [l for l in self.multiworld.get_locations(self.player) if l.address is not None]
        pool = [i for i in self.multiworld.itempool if i.player == self.player]
        empty = [l for l in locs if l.item is None]
        assert len(pool) == len(empty), (len(pool), len(empty), len(locs))


class FinaleDLCOnlySeed(WorldTestBase):
    """dlc_only: the base game is sealed, so there is no Ashen Capital to unlock and no lock to
    mint -- the finale is inert and the goal comes from the DLC terminal-region ladder.

    This is the ONE remaining inert case for a lock-minting seed (natural_progression is the
    other, and it mints no locks at all), and it is also where the old terminus-first spine walk
    still lives. Deleting that ladder because "the finale is always the goal now" would break
    exactly this seed."""
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
