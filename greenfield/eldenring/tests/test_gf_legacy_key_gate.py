"""features/legacy_key_gates -- the remaining key gates, and the one that was RETIRED.

🛑 THE ACADEMY GLINTSTONE KEY IS NO LONGER A GATE (2026-08-16, bobler + Alaric: "just neutralize the
academy glintstone key altogether, have the minted Academy Lock be the thing that grants all the
graces"). The class below used to prove the gate WORKED -- 70 m14 checks unreachable without the key,
the key upgraded to PROGRESSION, fill keeping one copy outside the gate. It now proves the gate is
GONE, which is the same test doing the same job pointed at the current ruling: it fails just as loudly
if the entry creeps back into _LEGACY_KEYS, and it is the only thing that would notice.

⭐ THE ASSERTION THAT MATTERS MOST is `bundle_withheld` -- removing the key from _LEGACY_KEYS is what
disarms graces.WALL_ARMED["Raya Lucaria Academy"], and that is the whole point of the change. A future
edit that keeps the key out of _LEGACY_KEYS but re-withholds the bundle some other way would satisfy
every other assertion here and still ship bobler's original complaint.

The Hole-Laden Necklace now also gates Rhia's bell reward (#664); the Lamenter's Gaol multi-key gate
is unchanged and still tested below.
"""
import pytest
WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from BaseClasses import ItemClassification as IC, CollectionState  # noqa: E402
from Fill import distribute_items_restrictive  # noqa: E402
from worlds.eldenring.features.legacy_key_gates import (  # noqa: E402
    LegacyKeyGates, _gated_location_ids, _multi_gated_location_ids, _MULTI_KEY_GATES, _LEGACY_KEYS,
    _LEGACY_EXTRA)
from worlds.eldenring.data import LOCATIONS  # noqa: E402
from ._util import world_items  # noqa: E402

GAME = "Elden Ring"
KEY = "Academy Glintstone Key"
CHAPEL_KEY = "Imbued Sword Key"
CHAPEL_FLAGS = (510030, 10017010, 10017900)


class LegacyKeyGateOn(WorldTestBase):
    game = GAME
    run_default_tests = False
    # all regions kept so Liurnia (hence m14) is present; vanilla items shuffled so the key exists;
    # minimal accessibility mirrors the shipped playtest (full-access + leyndell runes is a separate,
    # pre-existing tight-fill combo unrelated to this gate).
    options = {"item_shuffle": True, "num_regions": 0, "legacy_dungeon_keys": True,
               "leyndell_runes_required": 0, "accessibility": "minimal"}

    def test_the_academy_key_is_not_a_gate_and_not_progression(self):
        """The ruling, from three directions at once."""
        from worlds.eldenring.features import legacy_key_gates as lkg
        # 1. It is not in the table, which is what publishes gf_legacy_keys.
        assert KEY not in lkg._LEGACY_KEYS, \
            "the Academy Glintstone Key gate was retired 2026-08-16 -- see the module docstring"
        assert KEY not in lkg._LEGACY_EXTRA
        # 2. So it is not a GATING item either, i.e. fill may place it anywhere.
        assert KEY not in lkg._GATING_ITEMS
        # 3. And it classifies as ordinary loot, not progression.
        keys = [it for it in world_items(self) if it.name == KEY]
        assert keys, "the key must still EXIST as an item -- neutralised, not deleted"
        assert not any(it.classification & IC.progression for it in keys), \
            "the key is filler now; nothing in logic may require it"

    def test_chapel_return_checks_need_liurnia_and_the_imbued_key(self):
        """#1303: the repeatable route is the Liurnia Belfry gate and its consumed key."""
        w = self.multiworld.worlds[1]
        rows_by_flag = {}
        for region, rows in LOCATIONS.items():
            for _name, ap, flag in rows:
                rows_by_flag.setdefault(int(flag), []).append((region, ap))
        for flag in CHAPEL_FLAGS:
            assert flag in rows_by_flag, f"Chapel flag {flag} vanished"
            assert all(region == "Liurnia" for region, _ap in rows_by_flag[flag]), \
                f"Chapel flag {flag} must present as Liurnia"

        gated = _gated_location_ids(list(_LEGACY_KEYS))
        chapel_aps = {ap for flag in CHAPEL_FLAGS for _region, ap in rows_by_flag[flag]}
        assert len(chapel_aps) == 4, "three Chapel flags must mint the four known return checks"
        assert all(gated.get(ap) == CHAPEL_KEY for ap in chapel_aps)

        locs = {loc.address: loc for loc in self.multiworld.get_locations(1)}
        key = next(item for item in world_items(self) if item.name == CHAPEL_KEY)

        def state(with_key):
            result = CollectionState(self.multiworld)
            for item in world_items(self):
                if item.name == CHAPEL_KEY:
                    continue
                if item.classification & IC.progression:
                    result.collect(item, prevent_sweep=True)
            if with_key:
                result.collect(key, prevent_sweep=True)
            return result

        without_key, with_key = state(False), state(True)
        for ap in chapel_aps:
            assert not locs[ap].can_reach(without_key), f"{locs[ap].name} reachable without key"
            assert locs[ap].can_reach(with_key), f"{locs[ap].name} blocked with Liurnia + key"

        assert CHAPEL_KEY in w.gf_legacy_keys
        assert key.classification & IC.progression

    def test_the_academy_lock_grants_its_graces(self):
        """⭐ The player-visible half, and the reason the change was made.

        bobler received the Raya Lucaria Academy Lock and the client told him "walk in, the Academy
        Glintstone Key opens it (no grace warp)". `bundle_withheld` is the function that decided that.
        """
        from worlds.eldenring.features.graces import bundle_withheld, WALL_ARMED
        from worlds.eldenring.region_spine import REGION_PARENT
        w = self.multiworld.worlds[1]
        assert "Raya Lucaria Academy" in REGION_PARENT, \
            "still a gated child structurally -- only its WALL is gone"
        assert "Raya Lucaria Academy" in WALL_ARMED, \
            "the pairing must STAY: bundle_withheld fails CLOSED for an unpaired child, so deleting " \
            "this entry would withhold the bundle unconditionally -- the exact opposite of the ruling"
        assert not bundle_withheld(w, "Raya Lucaria Academy"), \
            "the Academy Lock must grant its full grace bundle"

    def test_the_m14_checks_need_only_the_region_lock(self):
        """The 70 checks the gate used to hold are now reachable on the Lock alone."""
        gated = _gated_location_ids(list(_LEGACY_KEYS))
        assert not any(v == KEY for v in gated.values()), "no check may still name the Academy key"
        m14 = [ap for (_n, ap, fl) in LOCATIONS.get("Raya Lucaria Academy", ())
               if isinstance(fl, int) and 14000000 <= fl < 15000000]
        assert m14, "sanity: Raya Lucaria still holds m14 checks"
        assert not (set(m14) & set(gated)), "m14 checks must be ungated"

    def test_the_seed_is_still_winnable_without_the_gate(self):
        """The half of the retired test that still means something: a full fill still beats."""
        mw = self.multiworld
        distribute_items_restrictive(mw)
        assert mw.can_beat_game(), "seed must be beatable with the Academy gate retired"

    def test_carian_statue_gates_the_inverted_route_and_not_the_standard_hall(self):
        statue = "Carian Inverted Statue"
        inverted_flags = {
            34117100, 34117110, 34117120,              # Mask, liver, fireflies
            34117400, 34117401, 34117402, 34117403,    # Tower Bridge Godskin set
            34117500,                                  # Cursemark + Stargazer Heirloom
            34117710,                                  # inverted Miriam: Lucidity
        }
        standard_flags = {34117010, 34117060, 34117080, 34117200, 34117700}
        expected = {ap for (_name, ap, flag) in LOCATIONS["Liurnia"] if flag in inverted_flags}
        standard = {ap for (_name, ap, flag) in LOCATIONS["Liurnia"] if flag in standard_flags}
        assert len(expected) == 10, "nine inverted flags must identify ten checks (two share f34117500)"
        assert len(standard) == 5, "the standard-side witness set drifted"
        assert _LEGACY_EXTRA[statue] == inverted_flags
        gated = _gated_location_ids(list(_LEGACY_KEYS))
        assert {ap for ap, key in gated.items() if key == statue} == expected
        assert not (standard & {ap for ap, key in gated.items() if key == statue}), \
            "standard Study Hall loot must not require the statue"

        items = [it for it in world_items(self) if it.name == statue]
        assert items and (items[0].classification & IC.progression), \
            "the statue is a physical gate and must classify as progression"

        locs = {loc.address: loc for loc in self.multiworld.get_locations(1)}
        checks = [locs[ap] for ap in expected]
        without = CollectionState(self.multiworld)
        with_statue = CollectionState(self.multiworld)
        for item in world_items(self):
            if not (item.classification & IC.progression) or item.name == statue:
                continue
            without.collect(item, prevent_sweep=True)
            with_statue.collect(item, prevent_sweep=True)
        with_statue.collect(items[0], prevent_sweep=True)
        for loc in checks:
            assert not loc.can_reach(without), f"{loc.name} reachable without the statue"
            assert loc.can_reach(with_statue), f"{loc.name} blocked with the statue"

    def test_metyr_chain_needs_the_necklace_and_both_region_locks(self):
        """Rhia + Dheo are necklace-gated; Metyr additionally needs Jagged Peak's Lock."""
        world = self.multiworld
        items = world_items(self)
        loc_by_flag = {int(flag): world.get_location(name, 1)
                       for locations in LOCATIONS.values() for (name, _ap, flag) in locations
                       if int(flag) in {2053467600, 2050407000, 510550}}
        necklace = next(it for it in items if it.name == "Hole-Laden Necklace")
        jagged = next(it for it in items if it.name == "Jagged Peak Lock")

        def _state(*extras):
            st = CollectionState(world)
            for item in items:
                if item.name in {necklace.name, jagged.name}:
                    continue
                if item.classification & IC.progression:
                    st.collect(item, prevent_sweep=True)
            for item in extras:
                st.collect(item, prevent_sweep=True)
            return st

        no_keys, necklace_only, jagged_only, both = (
            _state(), _state(necklace), _state(jagged), _state(necklace, jagged))
        rhia, dheo, metyr = (loc_by_flag[f] for f in (2053467600, 2050407000, 510550))
        assert not rhia.can_reach(no_keys) and rhia.can_reach(necklace_only)
        assert not dheo.can_reach(jagged_only), "Dheo must still need the necklace"
        assert dheo.can_reach(both)
        assert not metyr.can_reach(necklace_only), "Metyr must need the Jagged Peak Lock"
        assert metyr.can_reach(both)


def test_chapel_gate_respects_the_existing_option_switches():
    """The new key follows the feature's established opt-in predicate; no separate always-on rule."""
    from types import SimpleNamespace

    feature = LegacyKeyGates()

    def world(legacy, shuffled):
        return SimpleNamespace(
            options=SimpleNamespace(
                legacy_dungeon_keys=SimpleNamespace(value=legacy),
                item_shuffle=SimpleNamespace(value=shuffled),
            ),
            _kept=lambda: ["Liurnia"],
        )

    assert CHAPEL_KEY in feature._active_keys(world(True, True))
    assert CHAPEL_KEY not in feature._active_keys(world(False, True))
    assert CHAPEL_KEY not in feature._active_keys(world(True, False))


# ---- multi-key gate: DLC Lamenter's Gaol needs BOTH Gaol keys -------------------------------------
GAOL_KEYS = ("Gaol Upper Level Key", "Gaol Lower Level Key")


def test_lamenters_gaol_route_tiers_cover_exact_key_and_boss_checks():
    """The three adjudicated checks follow the nested-door route; unbound interior rows retain the
    conservative both-key fallback rather than inheriting a guessed position."""
    gate = next(g for g in _MULTI_KEY_GATES if g["id"] == "lamenters_gaol")
    gated = _multi_gated_location_ids([gate])
    # Look the checks up by their STABLE flags, not hard-coded ap-ids -- ap-ids are POSITIONAL and
    # renumber whenever a check is added/removed (the tracker-description pass shifted these by 2).
    # Charo's merged into Cerulean 2026-08-10; the gaol checks live there now.
    charos = {int(f): ap for (_n, ap, f) in LOCATIONS.get("Cerulean", ())}
    upper, lower, boss = (charos.get(flag) for flag in (41027000, 41027320, 520770))
    assert all(ap is not None for ap in (upper, lower, boss))
    assert upper not in gated, "Upper Key is before the first locked door"
    assert gated[lower] == ("Gaol Upper Level Key",)
    assert gated[boss] == GAOL_KEYS
    unknown = [ks for ap, ks in gated.items() if ap not in {lower, boss}]
    assert unknown and all(ks == GAOL_KEYS for ks in unknown)


class LamentersGaolGateOn(WorldTestBase):
    game = GAME
    run_default_tests = False
    # DLC on so Charo's (the Lamenter's Gaol) is kept; vanilla items shuffled so the keys exist.
    options = {"item_shuffle": True, "num_regions": 0, "enable_dlc": True,
               "legacy_dungeon_keys": True, "leyndell_runes_required": 0, "accessibility": "minimal"}

    def test_gaol_checks_follow_the_three_route_tiers(self):
        gate = next(g for g in _MULTI_KEY_GATES if g["id"] == "lamenters_gaol")
        gated = _multi_gated_location_ids([gate])
        locs = {l.address: l for l in self.multiworld.get_locations(1)}
        sample = [locs[a] for a in gated if a in locs][:10]
        assert sample, "gaol checks must exist with DLC on"

        def _state(*held_key_names):
            st = CollectionState(self.multiworld)
            for it in world_items(self):
                if it.name in GAOL_KEYS:
                    continue  # add the gaol keys explicitly below
                if it.classification & IC.progression:
                    st.collect(it, prevent_sweep=True)
            for kn in held_key_names:
                st.collect(next(it for it in world_items(self) if it.name == kn), prevent_sweep=True)
            return st

        neither, upper_only, both = _state(), _state("Gaol Upper Level Key"), _state(*GAOL_KEYS)
        by_flag = {int(l.name.rsplit("[f", 1)[1][:-1]): l for l in self.multiworld.get_locations(1)
                   if "[f" in l.name}
        upper_loc, lower_loc, boss_loc = (by_flag[f] for f in (41027000, 41027320, 520770))
        assert upper_loc.can_reach(neither), "Upper Key must be reachable before door 1"
        assert not lower_loc.can_reach(neither) and lower_loc.can_reach(upper_only)
        assert not boss_loc.can_reach(upper_only) and boss_loc.can_reach(both)
        for l in sample:
            assert l.can_reach(both), f"{l.name} blocked WITH both keys"

    def test_keys_are_progression_and_seed_winnable(self):
        for kn in GAOL_KEYS:
            ks = [it for it in world_items(self) if it.name == kn]
            assert ks and (ks[0].classification & IC.progression), f"{kn} must be PROGRESSION"
        mw = self.multiworld
        distribute_items_restrictive(mw)
        gated = set(_multi_gated_location_ids(
            [g for g in _MULTI_KEY_GATES if g["id"] == "lamenters_gaol"]))
        for kn in GAOL_KEYS:
            keylocs = [l for l in mw.get_locations(1) if l.item and l.item.name == kn]
            assert keylocs, f"{kn} must be placed"
            assert all(l.address not in gated for l in keylocs), \
                f"{kn} must not be placed behind an active gaol door"
        assert mw.can_beat_game(), "a DLC seed with the gaol gate active must be beatable"
