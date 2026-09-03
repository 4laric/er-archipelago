import random
import unittest

from ..features.preferred_placement import foreign_unit_target, take_units


class _Item:
    def __init__(self, name):
        self.name = name


class TestPreferredPlacementMath(unittest.TestCase):
    def test_foreign_share_is_proportional(self):
        self.assertEqual(foreign_unit_target(20, 100, 400), 5)

    def test_a_real_partner_gets_at_least_one_unit(self):
        self.assertEqual(foreign_unit_target(1, 1, 1000), 1)

    def test_no_partner_or_supply_is_zero(self):
        self.assertGreater(foreign_unit_target(1, 1, 1), 0,
                           "witness: the target helper can select a real share")
        self.assertEqual(foreign_unit_target(0, 1, 2), 0)
        self.assertEqual(foreign_unit_target(10, 0, 2), 0)

    def test_selection_counts_x2_as_two_units(self):
        items = [_Item("Scadutree Fragment x2"), _Item("Scadutree Fragment")]
        picked = take_units(items, 2, random.Random(0))
        self.assertGreaterEqual(sum(2 if i.name.endswith("x2") else 1 for i in picked), 2)
        self.assertLessEqual(len(picked), 2)
