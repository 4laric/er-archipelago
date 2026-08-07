"""vanilla_placement -- every item back where the base game keeps it.

Motivating case (CONTRIBUTING rule 11: the motivating case IS the acceptance test) -- Discord,
"Kro", 2026-08-07: a group who want a co-op deathlink run of the base game with the Dectus halves,
the Golden Seeds and everything else in their normal locations.

Subclasses WorldTestBase so the generic suite (test_fill, reachability, beatability) runs for free
against a real generated multiworld; on top of that we assert the four properties the mode's safety
argument actually rests on: the pinning is exact, the world is HERMETIC, no synthetic gating is
minted, and the client is told to seal nothing.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from Options import OptionError  # noqa: E402
from worlds.eldenring.item_ids import LOCATION_ITEM  # noqa: E402
from worlds.eldenring.features import vanilla_placement as _vp  # noqa: E402

GAME = "Elden Ring"


class VanillaPlacementTest(WorldTestBase):
    game = GAME
    options = {"vanilla_placement": "all", "enable_dlc": True}

    # ---- THE MOTIVATING CASE -------------------------------------------------------------
    def test_every_location_holds_its_own_vanilla_item(self):
        """The whole feature in one assertion: a check's item is the item the base game puts there.

        Compared against the pairing core PUBLISHED (gf_vanilla_pins), not a raw LOCATION_ITEM
        lookup, because the resolved name legitimately differs for a DLC-excluded or hold-capped
        location -- and comparing against the raw table would then fail for the right behaviour.
        LOCATION_ITEM agreement is asserted separately below, where it must hold."""
        world = self.multiworld.worlds[self.player]
        pins = dict(world.gf_vanilla_pins)
        assert pins, "core published no pairing"
        wrong = []
        for loc in self.multiworld.get_locations(self.player):
            if loc.address is None:
                continue  # the "<R> Reached" events
            want = pins.get(loc.address)
            if loc.item is None or loc.item.name != want:
                wrong.append((loc.name, want, loc.item.name if loc.item else None))
        assert not wrong, f"{len(wrong)} location(s) do not hold their paired item, e.g. {wrong[:5]}"

    def test_dectus_and_golden_seeds_are_where_the_base_game_keeps_them(self):
        """The player's own words. Enable_dlc is on and nothing is hold-capped for these, so here
        the resolved pin must equal the raw vanilla table."""
        world = self.multiworld.worlds[self.player]
        watch = ("Dectus Medallion (Left)", "Dectus Medallion (Right)", "Academy Glintstone Key",
                 "Rold Medallion", "Golden Seed")
        seen = {}
        for loc in self.multiworld.get_locations(self.player):
            if loc.address is None:
                continue
            vanilla = LOCATION_ITEM.get(loc.address)
            if vanilla in watch:
                seen.setdefault(vanilla, 0)
                seen[vanilla] += 1
                assert loc.item is not None and loc.item.name == vanilla, (
                    f"{loc.name} should hold its vanilla {vanilla}, holds "
                    f"{loc.item.name if loc.item else None}")
        for nm in ("Dectus Medallion (Left)", "Dectus Medallion (Right)", "Golden Seed"):
            assert seen.get(nm), f"no {nm} location in the seed -- the assertion above was vacuous"

    # ---- HERMETICITY (the safety argument) -----------------------------------------------
    def test_no_unfilled_locations_and_an_empty_pool(self):
        """Zero unfilled locations is WHY no foreign item can enter: fill has nowhere to put one.
        This is the property that makes the flat region graph's sphere-0 lie harmless."""
        locs = [l for l in self.multiworld.get_locations(self.player) if l.address is not None]
        # WITNESS (test_gf_vacuous_pass): both assertions below are "this is empty", which passes
        # for free if the scan stops matching. Prove the scan saw the world first.
        assert len(locs) > 4000, f"only {len(locs)} real locations -- the scan below is vacuous"
        unfilled = [l.name for l in locs if l.item is None]
        assert not unfilled, f"{len(unfilled)} unfilled, e.g. {unfilled[:5]}"
        left = [i.name for i in self.multiworld.itempool if i.player == self.player]
        assert not left, f"{len(left)} item(s) left in the pool, e.g. {left[:5]}"

    def test_no_foreign_items_and_nothing_leaves(self):
        for loc in self.multiworld.get_locations(self.player):
            if loc.item is not None:
                assert loc.item.player == self.player, (
                    f"{loc.name} holds player {loc.item.player}'s item -- the world is not hermetic")

    # ---- NO SYNTHETIC GATING -------------------------------------------------------------
    def test_no_receivable_region_locks(self):
        p = self.player
        receivable = [i for i in self.multiworld.itempool if i.player == p]
        receivable += list(self.multiworld.precollected_items[p])
        for loc in self.multiworld.get_locations(p):
            if loc.item is not None and loc.item.player == p and loc.item.code is not None:
                receivable.append(loc.item)
        locks = sorted({i.name for i in receivable
                        if i.name.endswith(" Lock") and i.code is not None})
        assert locks == [], f"vanilla_placement must mint NO receivable '<Region> Lock'; got {locks}"

    def test_whole_map_is_in_play_and_reachable_at_spawn(self):
        world = self.multiworld.worlds[self.player]
        assert sorted(world._kept()) == sorted(world.gf_eligible), \
            "vanilla_placement plays the whole eligible map"
        state = self.multiworld.get_all_state(False)
        for r in world._kept():
            assert state.can_reach(r, "Region", self.player), f"{r} unreachable"

    def test_the_run_still_ends_at_the_elden_beast(self):
        """A vanilla run ends where vanilla ends. Found by a Generate smoke run, not by the suite:
        an earlier draft switched the finale OFF under this mode on the reasoning that the Erdtree
        burn is the base game's again -- true, but the Ashen Capital REGION is what carries Godfrey
        and the Elden Beast, so `goal: auto` fell through to the DLC finale and a base+DLC vanilla
        seed ended at Enir Ilim. The finale now takes natural_progression's branch: its entrance is
        the vanilla chain (Farum Azula AND Leyndell reachable), not a minted burn item."""
        world = self.multiworld.worlds[self.player]
        assert getattr(world, "gf_finale_active", False), \
            "the Ashen Capital must exist: it is where vanilla's ending is"
        sd = world.fill_slot_data()
        goal_regions = {g.get("region") for g in (sd.get("goalLocations") or [])
                        if isinstance(g, dict)}
        assert sd.get("goalLocations"), "goalLocations must not be empty"
        # the Ashen Capital's checks are pinned like any other location
        finale_locs = [l for l in self.multiworld.get_locations(self.player)
                       if l.parent_region is not None
                       and l.parent_region.name == "Ashen Capital" and l.address is not None]
        assert finale_locs, "the finale built no locations"
        for l in finale_locs:
            assert l.item is not None and l.item.player == self.player, \
                f"{l.name} is unfilled or foreign -- the pin walk missed the feature-owned locations"

    # ---- THE START IS VANILLA TOO --------------------------------------------------------
    def test_no_start_loadout(self):
        """The 2026-08-07 smoke log showed three Roundtable checks collecting themselves at connect
        -- start_with_bell / _physick / _whetstone are unique grants keyed to flags 60110 / 60020 /
        60130, and those flags ARE their locations' check flags. Every name in VANILLA_START is
        FROZEN ON in defaults.py, so no yaml can do this; the mode has to."""
        world = self.multiworld.worlds[self.player]
        # WITNESS (test_gf_vacuous_pass): every assertion here is "this is empty", which passes for
        # free if the names go stale. Prove the options still EXIST before proving they are off --
        # a renamed option would otherwise read as a passing test.
        present = [nm for nm in _vp.VANILLA_START if getattr(world.options, nm, None) is not None]
        assert present == list(_vp.VANILLA_START), (
            f"VANILLA_START names no longer match the real options; missing "
            f"{sorted(set(_vp.VANILLA_START) - set(present))}")
        still_on = [nm for nm in _vp.VANILLA_START
                    if int(getattr(getattr(world.options, nm, None), "value", 0))]
        assert not still_on, f"start-loadout option(s) still on under vanilla placement: {still_on}"
        sd = world.fill_slot_data()
        assert "startItems" in sd and "uniqueStartGrants" in sd, \
            "both keys must still be EMITTED (empty), not dropped -- the client reads them"
        assert not sd["startItems"], f"startItems must be empty, got {len(sd['startItems'])}"
        assert not sd["uniqueStartGrants"], \
            f"uniqueStartGrants must be empty, got {sd['uniqueStartGrants']}"

    def test_the_husks_checks_are_not_collected_at_connect(self):
        """The motivating symptom, asserted at the location rather than the option: the three checks
        whose flags the start grants would have set must still be sitting there unclaimed, holding
        their own vanilla items."""
        watch = {"Flask of Wondrous Physick", "Spirit Calling Bell", "Whetstone Knife"}
        seen = set()
        for loc in self.multiworld.get_locations(self.player):
            if loc.address is None:
                continue
            vanilla = LOCATION_ITEM.get(loc.address)
            if vanilla in watch and "Twin Maiden Husks" in loc.name:
                seen.add(vanilla)
                assert loc.item is not None and loc.item.name == vanilla, \
                    f"{loc.name} should still hold its own {vanilla}"
        assert seen == watch, f"expected all three Husks checks in the seed, saw {sorted(seen)}"

    # ---- THE CLIENT IS TOLD TO SEAL NOTHING ----------------------------------------------
    def test_slot_data_emits_no_seals(self):
        """The born-softlocked regression. area_locks emits kick-watch ranges for ALL regions
        unconditionally; with no Lock item in existence nothing could ever bloom them, so the
        player would be ejected from every region on arrival -- silently, because each individual
        range is correct."""
        sd = self.multiworld.worlds[self.player].fill_slot_data()
        assert sd.get("areaLockFlags") == [], \
            "areaLockFlags must be empty or the seed is born-softlocked"
        assert not sd.get("regionOpenFlags"), "regionOpenFlags must be empty"
        assert not sd.get("regionGraces"), "regionGraces must be empty"
        assert not sd.get("naturalKeyTriggers"), "naturalKeyTriggers must be empty"
        assert sd.get("goalRequiredItems") in ([], None, {}), \
            "no lock is required to finish; goalRequiredItems must be empty"


class VanillaPlacementRejectsNaturalProgressionTest(WorldTestBase):
    """The self-gating collapse is an OptionError, never a FillError and never a quietly
    unwinnable seed: Stormveil is gated on the Rusty Key, which lives inside Stormveil."""
    game = GAME
    options = {"vanilla_placement": "all", "natural_progression": True}
    auto_construct = False

    def test_rejected_by_name(self):
        with pytest.raises(OptionError) as e:
            self.world_setup()
        msg = str(e.value)
        assert "Rusty Key" in msg and "Stormveil" in msg, \
            f"the error must name the concrete collision; got: {msg}"


class VanillaPlacementOffIsUnchangedTest(WorldTestBase):
    """Options default to no change: an untouched yaml still gets the randomizer."""
    game = GAME
    options = {}

    def test_default_is_off_and_locks_are_minted(self):
        world = self.multiworld.worlds[self.player]
        assert not _vp.is_on(world)
        receivable = [i.name for i in self.multiworld.itempool if i.player == self.player]
        receivable += [i.name for i in self.multiworld.precollected_items[self.player]]
        assert any(n.endswith(" Lock") for n in receivable), \
            "with the mode off the seed must still mint region locks"

    def test_off_keeps_the_start_loadout(self):
        world = self.multiworld.worlds[self.player]
        on = [nm for nm in _vp.VANILLA_START
              if int(getattr(getattr(world.options, nm, None), "value", 0))]
        assert on, "with the mode off the frozen start loadout must be untouched"
        assert world.fill_slot_data().get("uniqueStartGrants"), \
            "an ordinary seed still grants the Husks items at connect"
