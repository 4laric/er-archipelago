"""#1437: the Jarburg NPC uses map-lot rewards despite an enemy-labelled pin."""
import csv
from pathlib import Path
import runpy
import unittest

PKG = Path(__file__).resolve().parents[1]
ROOT = next(p for p in Path(__file__).resolve().parents if (p / "greenfield/gen_data.py").is_file())

class NumenReward(unittest.TestCase):
    def test_distinct_rune_flag_and_map_replacement(self):
        data = runpy.run_path(str(PKG / "data.py"))
        by_flag = {f: (region, ap) for region, rows in data["LOCATIONS"].items() for _, ap, f in rows}
        self.assertEqual(by_flag[400452], ("Liurnia", 7774651))
        self.assertIn(12037800, by_flag)  # Ordinary rune pickup is independently tracked.
        lots = runpy.run_path(str(PKG / "check_lots_data.py"))
        self.assertEqual(lots["CHECK_LOT_SLOTS_MAP"][104512], [1])
        self.assertNotIn(104512, lots["CHECK_LOT_SLOTS_ENEMY"])
        self.assertEqual(runpy.run_path(str(PKG / "missable_locations.py"))["MISSABLE_LOCATIONS"][7774651], "questline")

    def test_npc_batch_namespace_from_committed_params(self):
        path = ROOT / "elden_ring_artifacts/vanilla_er/vanilla_er/NpcParam.csv"
        if not path.exists():
            self.skipTest("committed gen_inputs.db not extracted")
        with path.open(encoding="utf-8-sig") as f:
            npc = next(r for r in csv.DictReader(f) if r["ID"] == "523140220")
        self.assertEqual(npc["itemLotId_map"], "104510")
        self.assertEqual(npc["itemLotId_enemy"], "-1")
        with (path.parent / "ItemLotParam_map.csv").open(encoding="utf-8-sig") as f:
            rows = {r["ID"]: r for r in csv.DictReader(f)}
        self.assertTrue(all(str(i) in rows for i in (104510,104511,104512)))
        self.assertEqual(rows["104512"]["getItemFlagId"], "400452")
        self.assertEqual(rows["104512"]["lotItemId01"], "2913")
        self.assertEqual(rows["104512"]["lotItemNum01"], "1")

if __name__ == "__main__":
    unittest.main()
