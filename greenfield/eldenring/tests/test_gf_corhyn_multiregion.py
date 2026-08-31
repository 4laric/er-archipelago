"""#331: wandering Corhyn rows use the honest HUB/defaulted fallback, never Liurnia.

Corhyn shares ShopLineup block 1003 with Seluvis and Pidia, but never stands in Liurnia. His own
merchant placements span Roundtable, Leyndell, Altus and Mountaintops. The safe representation is
therefore a hub-collapsed check, optionally gated on its assertable Leyndell site, not the block's
legacy Liurnia label.
"""
import unittest

from .. import data
from ..location_tags import DEFAULTED_REGION_APS, HUB_COLLAPSED_SITE_APS


CORHYN_FLAGS = frozenset(range(130500, 130781, 10))


class CorhynMultiRegionFallback(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = [(region, name, ap, flag)
                    for region, locations in data.LOCATIONS.items()
                    for name, ap, flag in locations if flag in CORHYN_FLAGS]

    def test_all_29_corhyn_rows_are_present_in_the_hub(self):
        self.assertEqual({flag for _region, _name, _ap, flag in self.rows}, CORHYN_FLAGS)
        for region, name, _ap, _flag in self.rows:
            self.assertEqual(region, "Roundtable Hold")
            self.assertTrue(name.startswith("Roundtable Hold ::"), name)

    def test_no_corhyn_row_can_carry_progression(self):
        aps = {ap for _region, _name, ap, _flag in self.rows}
        self.assertEqual(aps - set(DEFAULTED_REGION_APS), set())

    def test_corhyn_uses_only_its_assertable_leyndell_site(self):
        aps = {ap for _region, _name, ap, _flag in self.rows}
        self.assertEqual({tuple(HUB_COLLAPSED_SITE_APS.get(ap, ())) for ap in aps},
                         {("Leyndell",)})


if __name__ == "__main__":
    unittest.main()
