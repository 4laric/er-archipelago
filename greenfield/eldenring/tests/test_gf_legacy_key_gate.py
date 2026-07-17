"""features/legacy_key_gates: the Academy Glintstone Key gates the folded Raya Lucaria (m14) checks.

Verifies the gate is winnable-by-construction: the key is upgraded to PROGRESSION, all 67 m14 checks
require it in logic (unreachable without, reachable with), fill keeps at least one key OUTSIDE the m14
gate, and a full seed stays beatable. Off -> key stays filler and nothing is gated.
"""
import pytest
WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from BaseClasses import ItemClassification as IC, CollectionState  # noqa: E402
from Fill import distribute_items_restrictive  # noqa: E402
from worlds.eldenring.features.legacy_key_gates import (  # noqa: E402
    _gated_location_ids, _multi_gated_location_ids, _MULTI_KEY_GATES)
from worlds.eldenring.data import LOCATIONS  # noqa: E402
from ._util import world_items  # noqa: E402

GAME = "Elden Ring"
KEY = "Academy Glintstone Key"


class LegacyKeyGateOn(WorldTestBase):
    game = GAME
    run_default_tests = False
    # all regions kept so Liurnia (hence m14) is present; vanilla items shuffled so the key exists;
    # minimal accessibility mirrors the shipped playtest (full-access + leyndell runes is a separate,
    # pre-existing tight-fill combo unrelated to this gate).
    options = {"item_shuffle": True, "num_regions": 0, "legacy_dungeon_keys": True,
               "leyndell_runes_required": 0, "accessibility": "minimal"}

    def test_key_is_progression(self):
        keys = [it for it in world_items(self) if it.name == KEY]
        assert keys, "Academy Glintstone Key must be created (pool or pre-placed) under item_shuffle + Liurnia kept"
        assert all(it.classification & IC.progression for it in keys)

    def test_all_67_m14_checks_gated_by_key(self):
        # 67 after the matt-free GLOBAL-recovery change (gen_data _recover_tile full coverage) surfaced
        # one more real Raya Lucaria academy drop -- Living Jar Shard, flag 14007997 (m14 -> Liurnia),
        # previously a SKIPped `global` row -- as a check. It is inside the m14 range, so it is correctly
        # gated by the Academy Glintstone Key (was 66 before recovery).
        gated = _gated_location_ids([KEY])
        assert len(gated) == 68 and all(v == KEY for v in gated.values())  # 69 -> 68: dropped the phantom 2nd Academy Glintstone Key f14007930 (Alaric 2026-07-17)
        st = CollectionState(self.multiworld)
        for it in world_items(self):
            if it.name != KEY and (it.classification & IC.progression):
                st.collect(it, prevent_sweep=True)
        locs = {l.address: l for l in self.multiworld.get_locations(1)}
        sample = [locs[a] for a in gated if a in locs][:10]
        assert sample
        for l in sample:
            assert not l.can_reach(st), f"{l.name} reachable WITHOUT the key"
        st.collect(next(it for it in world_items(self) if it.name == KEY), prevent_sweep=True)
        for l in sample:
            assert l.can_reach(st), f"{l.name} blocked WITH the key"

    def test_fill_keeps_key_reachable_and_seed_winnable(self):
        mw = self.multiworld
        distribute_items_restrictive(mw)
        gated = set(_gated_location_ids([KEY]))
        keylocs = [l for l in mw.get_locations(1) if l.item and l.item.name == KEY]
        assert keylocs, "keys must be placed"
        assert any(l.address not in gated for l in keylocs), \
            "at least one Academy Glintstone Key must be placed OUTSIDE the m14 gate"
        assert mw.can_beat_game(), "seed with the gate active must be beatable"


# ---- multi-key gate: DLC Lamenter's Gaol needs BOTH Gaol keys -------------------------------------
GAOL_KEYS = ("Gaol Upper Level Key", "Gaol Lower Level Key")


def test_lamenters_gaol_multi_gate_covers_both_keys_and_boss():
    """Every Lamenter's Gaol check -- the two Gaol key LOCATIONS and the Lamenter boss reward -- is
    gated behind BOTH keys (map-lot range 4102xxxx + the f520770 boss-reward extra). Pure over data."""
    gate = next(g for g in _MULTI_KEY_GATES if g["id"] == "lamenters_gaol")
    gated = _multi_gated_location_ids([gate])
    # Look the checks up by their STABLE flags, not hard-coded ap-ids -- ap-ids are POSITIONAL and
    # renumber whenever a check is added/removed (the tracker-description pass shifted these by 2).
    charos = {int(f): ap for (_n, ap, f) in LOCATIONS.get("Charo's", ())}
    for flag in (41027000, 41027320, 520770):  # Upper Key loc, Lower Key loc, Lamenter's Mask (boss)
        ap = charos.get(flag)
        assert ap is not None, f"flag {flag} is not a Charo's location"
        assert ap in gated, f"gaol check flag {flag} (ap {ap}) not gated"
    assert all(set(ks) == set(GAOL_KEYS) for ks in gated.values()), "every gaol check needs BOTH keys"


class LamentersGaolGateOn(WorldTestBase):
    game = GAME
    run_default_tests = False
    # DLC on so Charo's (the Lamenter's Gaol) is kept; vanilla items shuffled so the keys exist.
    options = {"item_shuffle": True, "num_regions": 0, "enable_dlc": True,
               "legacy_dungeon_keys": True, "leyndell_runes_required": 0, "accessibility": "minimal"}

    def test_gaol_checks_need_both_keys(self):
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
        for l in sample:
            assert not l.can_reach(neither), f"{l.name} reachable with NEITHER gaol key"
            assert not l.can_reach(upper_only), f"{l.name} reachable with only the Upper key"
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
                f"{kn} must be placed OUTSIDE the gaol it gates"
        assert mw.can_beat_game(), "a DLC seed with the gaol gate active must be beatable"


