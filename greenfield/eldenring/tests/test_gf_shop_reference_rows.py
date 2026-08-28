"""Non-merchant ShopLineupParam reference blocks never become AP locations.

The normal row filter has always excluded ``method=shop_reference``. The later derived-shop
recovery pass used to resurrect the same flags and their block siblings as unresolved Roundtable
checks, producing the v0.4.10 tracker's starting-class and caster-kit rows (#1097).
"""
import unittest

from ..data import LOCATIONS
from ..shop_data import SHOP_ROW_FLAGS


# Complete limited-stock flag populations of reference blocks 16001 and 16004. The generator
# derives the blocks from region_map's shop_reference seed rows; this expected population makes a
# changed param block visible instead of silently weakening the regression.
REFERENCE_BLOCK_FLAGS = frozenset({
    220500, 220510, 220520, 220530, 220540, 220550, 220560, 220570,
    220580, 220590, 220600, 220610, 220620, 220630, 220640, 220650,
    220680, 220690, 220700, 220710, 220720,
    230000, 230010, 230020, 230030, 230040, 230050, 230060, 230070,
    230080, 230090, 230100, 230110, 230120, 230130, 230140, 230150,
    230160, 230170, 230190,
})


class TestShopReferenceRows(unittest.TestCase):

    def test_reference_block_flags_are_not_locations(self):
        live = {flag for rows in LOCATIONS.values() for _name, _ap, flag in rows}
        self.assertTrue(live, "generated location corpus vanished")
        self.assertFalse(
            live & REFERENCE_BLOCK_FLAGS,
            "non-merchant starting-kit/caster-kit reference rows were minted as AP locations",
        )

    def test_reference_block_flags_have_no_client_shop_rewrite(self):
        rewritten = set(SHOP_ROW_FLAGS.values())
        self.assertTrue(rewritten, "generated shop rewrite contract vanished")
        self.assertFalse(
            rewritten & REFERENCE_BLOCK_FLAGS,
            "non-merchant reference rows reached the client's shop rewrite contract",
        )


if __name__ == "__main__":
    unittest.main()
