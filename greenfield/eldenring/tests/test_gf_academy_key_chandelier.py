"""#1001: the Church of the Cuckoo chandelier hands out a DUPLICATE Academy Glintstone Key.

There are two goods rows both named "Academy Glintstone Key": 8109 (the overworld corpse -- the
gate key, and the modelled AP check) and 8174 (the m14 chandelier). The chandelier flag 14007930 is
excluded from checks so the key stays a pool SINGLETON -- but its vanilla lot (14000930) was left
live, handing out a free duplicate key with no AP check (255, 2026-08-24). The fix neutralises the
LOT (goods-blank) without making it a check: blank it, don't pool it, don't check it.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

GAME = "Elden Ring"
CHANDELIER_LOT = 14000930          # ItemLotParam_map lot; goods 8174, cat GOODS, getItemFlagId 0
CHANDELIER_FLAG = 14007930         # MSB-object acquisition flag (stays in _SHEET_DROPS, not a check)


def test_chandelier_lot_is_in_the_goods_blank_table():
    # AP-free: the neutralise-only entry is present so the client blanks the duplicate-key lot.
    from worlds.eldenring.check_lots_data import CHECK_LOT_SLOTS_MAP
    assert CHECK_LOT_SLOTS_MAP.get(CHANDELIER_LOT) == [1], (
        "chandelier lot %d goods slot must be blanked (neutralise-only, #1001)" % CHANDELIER_LOT)


class ChandelierDedup(WorldTestBase):
    game = GAME
    options = {"num_regions": 0}

    def test_lot_blanked_emitted_and_key_stays_a_singleton(self):
        # The default WorldTestBase draw can move the one modelled key out of the itempool through
        # another seeded placement policy, leaving this pool-only assertion with zero witnesses.
        # Pin the draw whose premise this test owns: one key in the pool, never the chandelier's
        # duplicate.  This is about cardinality, not distribution across arbitrary seeds (#1065).
        self.world_setup(seed=1)
        sd = self.world.fill_slot_data()
        blank = sd.get("checkLotBlankMap", {})
        # WITNESS the map is populated, then the specific neutralisation.
        assert blank, "checkLotBlankMap must be emitted"
        assert str(CHANDELIER_LOT) in blank, (
            "chandelier lot must ride checkLotBlankMap so the client blanks it")
        # the duplicate never doubles the key: exactly one Academy Glintstone Key in the pool.
        names = [i.name for i in self.multiworld.itempool if i.player == self.player]
        assert names.count("Academy Glintstone Key") == 1, (
            "the chandelier duplicate must not add a second key to the pool")
