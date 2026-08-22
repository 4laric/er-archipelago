"""Progressive ability lock (#945/#980): the locked abilities become findable 'Unlock: X' items.

Static mode is covered by test_gf_ability_lock_option. These guard the PROGRESSIVE additions:
the synthetic item ids (fixed base, disjoint, useful, not game-grantable), that they are pooled
ONLY in progressive mode, the abilityUnlockItems map shape + requiresClientFeatures handshake, and
that a full generate stays count-exact with the items in the pool.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring import contract  # noqa: E402

GAME = "Elden Ring"


# ---- AP-free id / contract facts -------------------------------------------------------------
def test_ids_are_a_disjoint_fixed_useful_block():
    from worlds.eldenring import core
    names = [nm for _k, nm in contract.ABILITY_UNLOCK_ITEM_NAMES]
    ids = [core.item_name_to_id[nm] for nm in names]
    # fixed, contiguous, at the declared base
    assert ids == [contract.ABILITY_UNLOCK_ITEM_BASE + i for i in range(len(names))]
    # useful, never filler (an unlock must not be swept or discarded)
    from BaseClasses import ItemClassification
    for nm in names:
        assert core._item_class[nm] == ItemClassification.useful
        # synthetic: the game is never asked to hand one over
        assert str(core.item_name_to_id[nm]) not in core._AP_IDS_TO_ITEM_IDS
    # disjoint from the spawn-trap block (7800000 + <10000)
    assert min(ids) >= core._SPAWN_TRAP_BASE + 10000


def test_map_is_a_declared_hashed_key():
    key = contract.BY_NAME["abilityUnlockItems"]
    assert key.shape == "STR_MAP"
    # it IS a top-level (hashed) key -- a new client capability, unlike the static option subkey
    assert "abilityUnlockItems" not in contract.OPTIONS_BY_NAME


# ---- static mode mints nothing ---------------------------------------------------------------
class StaticMintsNoItems(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "locked_abilities": ["roll", "r1"], "ability_lock_mode": "static"}

    def test_no_unlock_items_and_no_map(self):
        names = {nm for _k, nm in contract.ABILITY_UNLOCK_ITEM_NAMES}
        pool_names = {i.name for i in self.multiworld.itempool if i.player == self.player}
        assert not (names & pool_names), "static mode must not pool any Unlock: item"
        sd = self.world.fill_slot_data()
        assert "abilityUnlockItems" not in sd
        assert contract.ABILITY_UNLOCK_FEATURE not in sd.get("requiresClientFeatures", [])
        # the static set still rides the options echo
        assert sd["options"]["locked_abilities"] == ["r1", "roll"]


# ---- progressive mode pools exactly the locked set + ships the map ---------------------------
class ProgressivePoolsAndMaps(WorldTestBase):
    game = GAME
    options = {"num_regions": 0,
               "locked_abilities": ["roll", "r1", "jump"],
               "ability_lock_mode": "progressive"}

    def test_exactly_the_locked_abilities_are_pooled(self):
        want = {dict(contract.ABILITY_UNLOCK_ITEM_NAMES)[k] for k in ("roll", "r1", "jump")}
        pool_names = [i.name for i in self.multiworld.itempool if i.player == self.player]
        got = {n for n in pool_names if n.startswith("Unlock: ")}
        assert got == want, got
        # one copy each
        for n in want:
            assert pool_names.count(n) == 1, f"{n} appears {pool_names.count(n)}x"

    def test_map_shape_and_handshake(self):
        sd = self.world.fill_slot_data()
        m = sd["abilityUnlockItems"]
        assert set(m.values()) == {"roll", "r1", "jump"}
        for k in m:
            assert k == str(int(k)) and int(k) >= contract.ABILITY_UNLOCK_ITEM_BASE
        assert contract.ABILITY_UNLOCK_FEATURE in sd["requiresClientFeatures"]
        # the abilities ALSO start locked (client disables at connect, then unlocks on receipt)
        assert sd["options"]["locked_abilities"] == ["jump", "r1", "roll"]
        contract.validate_slot_data(sd, strict=True)

    # NB: count-exactness (items == fillable locations) is proven by WorldTestBase's own default
    # suite, which fills this very seed -- a surplus/deficit would raise FillError there. A naive
    # len(itempool) == len(get_locations) check is wrong (itempool excludes the precollected start
    # anchor and event locations), so it is deliberately not re-asserted here.
