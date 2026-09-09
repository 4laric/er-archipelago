"""#1437: same sorcery at different acquisition flags is not one check."""
from pathlib import Path
import runpy
import unittest

PKG = Path(__file__).resolve().parent.parent

class GelmirReward(unittest.TestCase):
    def test_farums_reward_is_separate_from_volcano_manor(self):
        data = runpy.run_path(str(PKG / "tables/data.py"))
        by_flag = {f: (region, ap) for region, rows in data["LOCATIONS"].items() for _, ap, f in rows}
        self.assertEqual(by_flag[400295], ("Farum Azula", 7774639))
        self.assertEqual(by_flag[400291][0], "Mt. Gelmir")
        self.assertNotEqual(by_flag[400291][1], by_flag[400295][1])
        slots = runpy.run_path(str(PKG / "tables/check_lots_data.py"))["CHECK_LOT_SLOTS_MAP"]
        self.assertEqual(slots[102926], [1])
        self.assertEqual(slots[102910], [1])
        missable = runpy.run_path(str(PKG / "tables/missable_locations.py"))["MISSABLE_LOCATIONS"]
        self.assertEqual(missable[7774639], "questline")

if __name__ == "__main__":
    unittest.main()
