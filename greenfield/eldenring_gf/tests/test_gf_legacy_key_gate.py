"""features/legacy_key_gates: the Academy Glintstone Key gates the folded Raya Lucaria (m14) checks.

Verifies the gate is winnable-by-construction: the key is upgraded to PROGRESSION, all 67 m14 checks
require it in logic (unreachable without, reachable with), fill keeps at least one key OUTSIDE the m14
gate, and a full seed stays beatable. Off -> key stays filler and nothing is gated.
"""
import pytest
WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")
from BaseClasses import ItemClassification as IC, CollectionState  # noqa: E402
from Fill import distribute_items_restrictive  # noqa: E402
from worlds.eldenring_gf.features.legacy_key_gates import _gated_location_ids  # noqa: E402
from ._util import world_items  # noqa: E402

GAME = "Elden Ring (Greenfield)"
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
        assert len(gated) == 69 and all(v == KEY for v in gated.values())  # +2 m14 drops surfaced by recovery loosening
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


