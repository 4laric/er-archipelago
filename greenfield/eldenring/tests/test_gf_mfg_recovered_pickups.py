"""Accepted native M4G witnesses for five previously culled physical rewards (#1437)."""
import ast
import json
import hashlib
from pathlib import Path
import unittest


def assignments(path):
    result = {}
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign):
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    result[target.id] = value
    return result


class MfgRecoveredPickups(unittest.TestCase):
    def test_native_rewards_are_checks_and_neutralized(self):
        root = next(p for p in Path(__file__).resolve().parents
                    if (p / "greenfield/gen_data.py").is_file())
        world = root / "greenfield/eldenring"
        evidence = json.loads((root / "greenfield/evidence/mfg_recovered_pickups.json").read_text())
        locations = assignments(world / "tables/data.py")["LOCATIONS"]
        by_flag = {}
        for region, rows in locations.items():
            for name, ap_id, flag in rows:
                by_flag.setdefault(flag, []).append((region, name, ap_id))
        blanks = assignments(world / "tables/check_lots_data.py")
        expected = {2046407001: "Gravesite", 2046407002: "Gravesite",
                    2046407003: "Gravesite", 2046407004: "Gravesite", 2047447901: "Ensis"}
        self.assertEqual({r["flag"] for r in evidence["rows"]}, set(expected))
        # Preserve the shipped identity hash, normalizing Eleonora's corrected flag.
        original = sorted((1039527700 if (flag, aid) == (400162, 7774254) else flag, aid)
                          for flag, values in by_flag.items() for _, _, aid in values
                          if aid <= 7774635 or aid >= 7900000)
        self.assertEqual(len(original), 4925)
        self.assertEqual(hashlib.sha256(json.dumps(original, separators=(",", ":")).encode()).hexdigest(),
                         "0c479eeae9fe422f2c1d4403cb68b856abe66a0052736484b5ad61f8bd2b9309")
        for row in evidence["rows"]:
            flag, pin, item = row["flag"], row["pin"], row["item"]
            with self.subTest(flag=flag):
                self.assertEqual(pin["lotSource"], "map")
                self.assertEqual(pin["itemLotId"], item["itemLotId"])
                self.assertEqual(item["eventFlag"], flag)
                self.assertEqual(len(by_flag.get(flag, [])), 1)
                region, name, ap_id = by_flag[flag][0]
                self.assertEqual(region, expected[flag])
                self.assertIn(item["items"][0]["name"], name)
                self.assertEqual(assignments(world / "tables/item_ids.py")["LOCATION_ITEM"][ap_id],
                                 item["items"][0]["name"])
                table = "CHECK_LOT_SLOTS_MAP" if flag == 2047447901 else "CHECK_LOT_ZERO_MAP"
                self.assertIn(1, blanks[table].get(pin["itemLotId"], []))


if __name__ == "__main__":
    unittest.main()
