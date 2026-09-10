"""The eight placed golems each yield two distinct, correctly regioned checks."""
import unittest
from ..tables import data, boss_taxonomy

# Acquisition flags and region rulings from #1540's MSB -> 90005301 -> lot-group join.
PAIRS = (
    (2045467500, 65420, 'Ancient Ruins'),
    (2050467500, 65450, 'Scadu Altus'),
    (2050467510, 65440, 'Scadu Altus'),
    (2046397060, 65460, 'Cerulean'),
    (2046427980, 65470, 'Gravesite'),
    (2048407020, 65400, 'Cerulean'),
    (2048467701, 65410, 'Scadu Altus'),
    (2051457700, 65430, 'Scadu Altus'),
)


class FurnaceChecks(unittest.TestCase):
    def test_both_rewards_are_live_and_regioned_together(self):
        by_flag = {}
        for region, rows in data.LOCATIONS.items():
            for name, ap, flag in rows:
                by_flag.setdefault(flag, []).append((region, name, ap))
        aps = set()
        for visage, tear, expected in PAIRS:
            for flag in (visage, tear):
                self.assertIn(flag, by_flag)
                self.assertEqual(len(by_flag[flag]), 1)
                region, name, ap = by_flag[flag][0]
                self.assertEqual(region, expected)
                self.assertIn('defeat Furnace Golem', name)
                aps.add(ap)
        self.assertEqual(len(aps), 16)
        deaths = {f for f, r in boss_taxonomy.BOSS_TAXONOMY.items() if r[0] == 'furnace_golem'}
        self.assertEqual(len(deaths), 8)
        self.assertFalse(deaths & {f for pair in PAIRS for f in pair[:2]})

    def test_existing_tear_ids_are_stable(self):
        by_flag = {f: a for rows in data.LOCATIONS.values() for _, a, f in rows}
        for index in range(8):
            self.assertEqual(by_flag[65400 + 10 * index], 7773680 + index)
