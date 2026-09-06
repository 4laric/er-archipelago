"""#1437: bind the shipped Poleblade check to the actual invasion award."""
import ast
from pathlib import Path
import unittest

PKG = Path(__file__).resolve().parent.parent

def value(file, name):
    for node in ast.parse((PKG / file).read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(name)

class EleonoraReward(unittest.TestCase):
    def test_actual_reward_uses_the_existing_id(self):
        locations = value("data.py", "LOCATIONS")
        rows = [(region, name, ap, flag) for region, group in locations.items() for name, ap, flag in group]
        actual = [r for r in rows if r[3] == 400162]
        self.assertEqual(len(actual), 1)
        self.assertEqual((actual[0][0], actual[0][2]), ("Altus", 7774254))
        self.assertFalse(any(r[3] == 1039527700 for r in rows))

    def test_only_the_live_weapon_lot_is_replaced(self):
        lots = value("check_lots_data.py", "CHECK_LOT_ZERO_MAP")
        self.assertEqual(lots[101621], [1])
        self.assertNotIn(1039520700, lots)

if __name__ == "__main__":
    unittest.main()
