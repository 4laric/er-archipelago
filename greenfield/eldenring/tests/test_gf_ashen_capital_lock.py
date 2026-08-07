"""SPEC-ashen-capital-lock -- the Erdtree burn as a synthetic item.

THE MOTIVATING CASE (CONTRIBUTING rule 11), in Alaric's words on 2026-08-06:

    "num_regions 1 rolls Mountaintops, you just play Mountaintops, eventually get ashen lock and
     warp to ashen."

Every clause of that sentence is a test in this file, because every clause was impossible the day
it was said. `num_regions: 1` produced FOUR regions (the auto force-keep of Leyndell, its parent
closure, and goal: elden_beast's own pair); a seed that really kept one region died at generation
in `core.create_items`'s start_regions clamp, which counted KEPT REGIONS and had never been wrong
only because `kept == 1` was unreachable; and there was no lock to get, because the burn was game
data that only Farum Azula could fire.

The other half of the file is the WIRE, and it is here rather than in a client test because the
world side is what decides it: the burn's flag bundle rides `lockRevealFlags`, and its ORDER is
load-bearing in a way that no reader of the list would guess. `common.emevd $Event(900)` opens
with `GotoIf(L1, !EventFlag(118)); EndEvent();` -- so 118 is the event's OWN suppressor, and
setting it before the rest makes the event skip the body that places the Elden Beast's arena.
Alaric measured that on 2026-08-06 by falling into the resulting void and dying. 118 goes LAST.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from Options import OptionError  # noqa: E402
from worlds.eldenring import contract  # noqa: E402
from worlds.eldenring.data import (LOCATIONS, REGIONS, HUB, FINALE_REGION,  # noqa: E402
                                   FINALE_BURN_REGION, FINALE_KICK_OWNER,
                                   CAPITAL_WORLD_BURN_FLAG, CAPITAL_PRE_BURN_FLAG,
                                   CAPITAL_BURN_FLAG, CAPITAL_BURN_DONE_FLAG,
                                   CAPITAL_BURN_SIDE_EFFECT_FLAGS,
                                   CAPITAL_WORLD_BURN_READER_MAPS)
from worlds.eldenring.region_spine import parent_chain  # noqa: E402
from worlds.eldenring.region_open_flags import REGION_OPEN_FLAGS  # noqa: E402
from worlds.eldenring.region_graces import REGION_GRACE_POINTS  # noqa: E402
from worlds.eldenring.region_play_ids import REGION_PLAY_IDS  # noqa: E402
from worlds.eldenring.features.finale import ASHEN_LOCK_ITEM  # noqa: E402
from worlds.eldenring.features import capital as _capital  # noqa: E402

GAME = "Elden Ring"


class TestTheBurnBundle:
    """The world-state replay, asserted where it is emitted."""

    def test_the_done_latch_is_last_and_the_world_state_is_present(self):
        bundle = _capital.burn_reveal_flags()
        assert bundle, "the burn bundle may not be empty -- regenerate data.py"
        assert bundle[-1] == CAPITAL_BURN_DONE_FLAG, (
            "the burn-done latch must be the LAST flag in the bundle: it is $Event(900)'s own "
            "entry check, so setting it first makes the event skip its body and the Elden Beast's "
            "arena never gets placed (measured in game 2026-08-06 -- a void, and a death). Got %r"
            % (bundle,))
        assert CAPITAL_WORLD_BURN_FLAG in bundle, (
            "without the world-burn state flag the m19_00 arena is a VOID")
        assert bundle.index(CAPITAL_WORLD_BURN_FLAG) < bundle.index(CAPITAL_BURN_DONE_FLAG)

    def test_the_map_version_selector_never_rides_the_bundle(self):
        """9116 is held BY POSITION by the reconciler. Setting it on receipt is position-blind and
        loads the wrong Leyndell -- the exact strand the reconciler exists to end."""
        assert CAPITAL_BURN_FLAG not in _capital.burn_reveal_flags()

    def test_the_pre_burn_flag_is_not_in_the_bundle_because_it_is_an_OFF(self):
        """The client's reveal path writes ON only, so a flag that must be cleared cannot ride this
        key at all. It travels as its own contract value instead -- stated here so that nobody
        'fixes' its absence by adding it."""
        assert CAPITAL_PRE_BURN_FLAG not in _capital.burn_reveal_flags()

    def test_the_world_burn_flag_is_the_one_with_readers(self):
        """The derivation's discriminator, pinned. 300 is read in five maps; the other Set-ONs in
        the body have none, which is exactly why they are side effects and it is state."""
        assert CAPITAL_WORLD_BURN_FLAG not in CAPITAL_BURN_SIDE_EFFECT_FLAGS
        assert len(CAPITAL_WORLD_BURN_READER_MAPS) >= 3, CAPITAL_WORLD_BURN_READER_MAPS
        assert "m11_00_00_00" in CAPITAL_WORLD_BURN_READER_MAPS, (
            "Royal Leyndell reads the burn state (its elevators) -- if it stopped, the whole "
            "reason this flag is held by position rather than latched has changed")

    def test_the_royal_grace_wipe_is_never_replayed(self):
        """$Event(900) also runs BatchSetEventFlags(71100, 71110, OFF), wiping the Royal grace warp
        points. That wipe is the entire reason the capital reconciler exists; replaying it would
        re-strand the ~152 Royal checks the reconciler was built to give back."""
        bundle = set(_capital.burn_reveal_flags())
        wiped = set(range(71100, 71110))
        # WITNESS first: an empty bundle would satisfy the assertion below for free, and the
        # vacuous-quantifier meta-gate is right to say so. The bundle is non-empty and those flags
        # are real Royal grace-warp flags -- REGION_GRACE_POINTS proves the second half.
        assert bundle, "an empty burn bundle makes this test vacuous"
        assert wiped & set(REGION_GRACE_POINTS[FINALE_KICK_OWNER]), \
            "71100-71109 are supposed to be Royal Leyndell's grace-warp flags; if they are not, " \
            "this test is guarding the wrong band"
        assert not (bundle & wiped), sorted(bundle & wiped)


class TestTheGeometryIsItsOwn:
    """The Ashen Capital stopped borrowing Leyndell's lock, flag and buckets."""

    def test_it_has_its_own_open_flag_graces_and_buckets(self):
        assert FINALE_REGION in REGION_OPEN_FLAGS
        assert FINALE_REGION in REGION_GRACE_POINTS and REGION_GRACE_POINTS[FINALE_REGION]
        assert REGION_PLAY_IDS.get(FINALE_REGION) == [11050, 19000]
        assert REGION_PLAY_IDS.get(FINALE_KICK_OWNER) == [11000], (
            "the finale's buckets must have LEFT Leyndell, or both regions claim them and the "
            "kick is decided by dict order")

    def test_the_front_door_is_one_of_its_own_graces(self):
        assert REGION_OPEN_FLAGS[FINALE_REGION] == REGION_GRACE_POINTS[FINALE_REGION][0]

    def test_the_arena_and_post_goal_graces_stay_withheld(self):
        """Three of the six m11_05/m19_00 graces are NOT in the bundle, each by a derivation that
        outranks the spec's prose: 71120 (Elden Throne) and 71900 (Fractured Marika) are boss-gated
        bonfires that do not exist yet when the lock arrives, and 71121 sits 0.5 units inside boss
        arena 11050850 (arena_graces.tsv). Granting any of them hands out a warp to a bonfire that
        has not spawned, or into a live fight."""
        bundle = set(REGION_GRACE_POINTS[FINALE_REGION])
        assert bundle == {71122, 71123, 71124, 71125}, sorted(bundle)

    def test_the_reconciler_partition_is_unmoved_by_the_split(self):
        royal, ashen = _capital.capital_partition()
        assert royal == [11000] and ashen == [11050, 19000]

    def test_the_partition_still_hard_fails_on_an_unclaimed_bucket(self):
        """The split gave the partition a second source, so prove it still refuses to guess."""
        with pytest.raises(contract.ContractError):
            _capital.capital_partition(play_ids=[11000, 11050, 19000, 11070])

    def test_the_capital_is_still_never_rollable(self):
        assert FINALE_REGION not in REGIONS
        assert LOCATIONS.get(FINALE_REGION), "...but it still has its ten checks"


class OneRegionSeed(WorldTestBase):
    """⭐ THE MOTIVATING CASE. `num_regions: 1` with the shipped `start_regions: 1`.

    This world could not be built at all before 2026-08-06: the auto force-keep put Leyndell in
    every draw and its parent closure added Altus, so `kept` was never 1 -- and if it had been,
    `core.create_items`'s clamp (`_n_start >= len(kept)`) would have raised OptionError naming an
    option the player never set. `start_with_region_lock` is FROZEN ON, so there was no way to
    opt out of the clamp either."""
    game = GAME
    run_default_tests = False
    options = {"num_regions": 1}

    def test_one_region_is_kept_and_the_seed_generates(self):
        """🛑 THE CLAIM IS "NOTHING IS FORCE-KEPT", AND `len(kept) == 1` IS NOT THAT.

        The parent closure is a second, entirely legitimate way for the kept set to grow: a drawn
        gated child PULLS ITS ANCESTORS IN, because it is entered through them. Draw Leyndell and
        the seed correctly keeps {Leyndell, Altus}; draw the Sewer and it correctly keeps three.
        Three of the thirty eligible regions are REGION_PARENT children, so the old assertion
        failed on roughly one seed in ten -- under a message accusing the force-keep bobler
        reported, which was not what had happened and had in fact been deleted.

        Stated as the thing it means instead: the DRAWN set is one region, and every other kept
        region is an ancestor of it. A force-keep puts back a region that is neither, and still
        fails here."""
        kept = list(self.world._kept())
        ancestry = {a for r in kept for a in parent_chain(r)}
        drawn = [r for r in kept if r not in ancestry]
        assert len(drawn) == 1, (
            "num_regions: 1 kept %d region(s) that are not an ancestor of another kept region "
            "(%s; whole kept set %s) -- something is force-keeping again, which is the bug bobler "
            "reported twice" % (len(drawn), ", ".join(sorted(drawn)), ", ".join(sorted(kept))))
        assert set(kept) == set(drawn) | {a for r in drawn for a in parent_chain(r)}, (
            "kept %s is not the one drawn region plus its ancestors -- something entered the kept "
            "set by a third route" % (sorted(kept),))

    def test_the_ashen_lock_is_the_lock_that_stays_in_the_pool(self):
        """The clamp's real invariant: at least one progression lock is still findable. With one
        kept region its lock IS the start anchor, so the Ashen Capital Lock is the only thing
        standing between the player and a seed that is complete at connect."""
        free = {i.name for i in self.multiworld.precollected_items[self.player]}
        assert ASHEN_LOCK_ITEM not in free
        findable = [i for i in self.multiworld.itempool
                    if i.player == self.player and i.name.endswith(" Lock")]
        placed = [l.item for l in self.multiworld.get_locations(self.player)
                  if l.item is not None and l.item.name.endswith(" Lock")]
        assert ASHEN_LOCK_ITEM in {i.name for i in findable + placed}

    def test_the_goal_is_the_elden_beast_and_the_lock_is_required_for_it(self):
        sd = self.world.fill_slot_data()
        assert sd["goalLocations"], "goalLocations may never be empty"
        assert ASHEN_LOCK_ITEM in sd["goalRequiredItems"], (
            "the two terminal conditions read one list; a lock missing from goalRequiredItems is "
            "the 2026-07-30 drift returning")

    def test_the_client_can_gate_the_finale_space(self):
        """coarse key + open flag + grace bundle, the three things the client needs to enforce a
        region it was never told to roll."""
        sd = self.world.fill_slot_data()
        assert sd["regionCoarseKeys"][FINALE_REGION] == FINALE_REGION, (
            "the finale used to borrow Leyndell's coarse key via core._lockless_host; it owns one "
            "now, and a seed that does not keep Leyndell would have had no key at all")
        assert sd["regionOpenFlags"][ASHEN_LOCK_ITEM] == REGION_OPEN_FLAGS[FINALE_REGION]
        assert sd["regionGraces"][ASHEN_LOCK_ITEM] == REGION_GRACE_POINTS[FINALE_REGION]
        assert sd["lockRevealFlags"][ASHEN_LOCK_ITEM] == _capital.burn_reveal_flags()


class NaturalProgressionSeed(WorldTestBase):
    """natural_progression mints NO Lock items, so there is nothing to arm the burn with and the
    vanilla chain stands. The spec says so in one line; this is what that line has to mean."""
    game = GAME
    run_default_tests = False
    options = {"natural_progression": True}

    def test_no_ashen_lock_is_minted(self):
        names = {i.name for i in self.multiworld.itempool if i.player == self.player}
        names |= {l.item.name for l in self.multiworld.get_locations(self.player) if l.item}
        assert ASHEN_LOCK_ITEM not in names

    def test_the_entrance_falls_back_to_the_vanilla_burn_chain(self):
        from worlds.eldenring.features.finale import finale_requirement_locks
        assert set(finale_requirement_locks(self.world)) == {
            f"{FINALE_BURN_REGION} Lock", f"{FINALE_KICK_OWNER} Lock"}

    def test_goal_required_items_stays_omitted(self):
        sd = self.world.fill_slot_data()
        assert "goalRequiredItems" not in sd


class DLCOnlyRejectsTheNamedGoal(WorldTestBase):
    """The vacuous-quantifier guard, exercised.

    `_resolve_goal_choice` validates a named goal by checking `forced_regions(chosen)` are all
    eligible. `elden_beast` forces NOTHING now, so that quantifier is over an empty tuple and
    passes for free -- including under dlc_only, where features/finale.py builds no Ashen Capital
    at all and the seed would die later inside a completion lambda instead of here."""
    game = GAME
    run_default_tests = False
    options = {"dlc_only": True, "goal": "elden_beast"}
    auto_construct = False

    def test_it_dies_at_generation_naming_the_toggle(self):
        with pytest.raises(OptionError, match="base game"):
            self.world_setup()
