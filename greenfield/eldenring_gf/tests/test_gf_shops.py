"""Phase 4 shop tests -- WorldTestBase. shopRowFlags is the client purchase-detect table:
{stringified ap-id -> positive int stock flag}, scoped to hub + kept regions, non-empty. Each shop
ap-id must be a real location; shopPreviewGoods must be a subset with positive FullID good ids
(equipId | ER category nibble, so the client previews the good in the right param table).
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")
from worlds.eldenring_gf.shop_data import (  # noqa: E402
    SHOP_ROW_FLAGS, SHOP_LOC_REGION, SHOP_PREVIEW_GOODS,
)

GAME = "Elden Ring (Greenfield)"

# ER FullID category nibbles (see core.py). A preview value is equipId | one of these.
_NIBBLES = {0x00000000, 0x10000000, 0x20000000, 0x40000000, 0x80000000}
_NIBBLE_MASK = 0xF0000000
_GOODS_NIBBLE = 0x40000000


class ShopDataAll(WorldTestBase):
    game = GAME

    def test_shop_data_nonempty_and_valid(self):
        self.assertTrue(SHOP_ROW_FLAGS, "shop_data.py must be generated")
        # every SHOP_ROW_FLAGS key has a region so the feature can scope it
        for aid in SHOP_ROW_FLAGS:
            self.assertIn(int(aid), SHOP_LOC_REGION, "every shop row needs a region")

    def test_preview_values_are_fullids(self):
        # Preview values are FullIDs (equipId | category nibble), NOT raw equipIds. Every value must
        # be a positive int whose top nibble is one of the five ER category nibbles.
        self.assertTrue(SHOP_PREVIEW_GOODS, "single-good shop rows must have preview FullIDs")
        for aid, fid in SHOP_PREVIEW_GOODS.items():
            self.assertIsInstance(fid, int)
            self.assertGreater(fid, 0, "preview FullIDs must be positive ints")
            self.assertIn(fid & _NIBBLE_MASK, _NIBBLES,
                          "preview FullID %r for %s must carry a valid category nibble" % (fid, aid))

    def test_known_goods_preview_carries_goods_bit(self):
        # 7770029 previews a vanilla consumable (ShopLineupParam equipId 105, equipType 3 = goods),
        # so its FullID must carry the GOODS nibble 0x40000000. At least one goods preview must exist.
        goods = {a: f for a, f in SHOP_PREVIEW_GOODS.items()
                 if (f & _NIBBLE_MASK) == _GOODS_NIBBLE}
        self.assertTrue(goods, "at least one preview must be a GOODS FullID")
        if "7770029" in SHOP_PREVIEW_GOODS:
            self.assertEqual(SHOP_PREVIEW_GOODS["7770029"] & _NIBBLE_MASK, _GOODS_NIBBLE,
                             "known goods shop good must carry the 0x40000000 GOODS bit")
            self.assertEqual(SHOP_PREVIEW_GOODS["7770029"] & ~_NIBBLE_MASK, 105,
                             "GOODS FullID must preserve the low-bits equipId (105)")

    def test_shop_row_flags_shape(self):
        sd = self.world.fill_slot_data()
        srf = sd["shopRowFlags"]
        self.assertTrue(srf, "shopRowFlags must be non-empty at full scope")
        self.assertIsInstance(srf, dict)
        catalog = set(self.world.location_name_to_id.values())
        for k, v in srf.items():
            self.assertEqual(k, str(int(k)), "shopRowFlags keys are stringified ap-ids")
            self.assertIsInstance(v, int)
            self.assertGreater(v, 0, "stock flags must be positive ints")
            self.assertIn(int(k), catalog, "shop ap-id must be a real location")

    def test_preview_goods_subset(self):
        sd = self.world.fill_slot_data()
        srf = sd["shopRowFlags"]
        spg = sd["shopPreviewGoods"]
        self.assertIsInstance(spg, dict)
        for k, g in spg.items():
            self.assertIn(k, srf, "preview good must belong to an emitted shop row")
            self.assertIsInstance(g, int)
            self.assertGreater(g, 0, "vanilla good FullID must be a positive int")
            self.assertIn(g & _NIBBLE_MASK, _NIBBLES, "preview good must be a FullID with a nibble")


class ShopScopedSealed(WorldTestBase):
    game = GAME
    options = {"num_regions": 1, "num_regions_order": "spine"}

    def test_scoped_to_kept_plus_hub(self):
        # hub is always in play; kept() is the spokes. Every emitted row must live in that scope.
        from worlds.eldenring_gf.data import HUB
        sd = self.world.fill_slot_data()
        srf = sd["shopRowFlags"]
        scope = {HUB} | set(self.world._kept())
        for k in srf:
            self.assertIn(SHOP_LOC_REGION.get(int(k)), scope,
                          "sealed-region shop checks must be excluded")
        self.assertTrue(srf, "hub shop checks keep shopRowFlags non-empty even when sealed to 1 region")
