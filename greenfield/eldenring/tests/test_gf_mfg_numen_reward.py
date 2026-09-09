"""#1437: the Jarburg NPC uses map-lot rewards despite an enemy-labelled pin."""
import csv
from pathlib import Path
import runpy
import unittest

PKG = Path(__file__).resolve().parent.parent
try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    from _util import find_repo_root, REPO_ONLY_REASON
# None when the world is installed into an AP checkout OUTSIDE the repo (gf_test --ap-dir elsewhere):
# find_repo_root's contract is "return None rather than a wrong path", and Path(None) at import time
# turned that into a collection error that took the whole file -- and every collection -- down.
_ROOT = find_repo_root(__file__)
ROOT = Path(_ROOT) if _ROOT else None

class NumenReward(unittest.TestCase):
    def test_distinct_rune_flag_and_map_replacement(self):
        data = runpy.run_path(str(PKG / "tables/data.py"))
        by_flag = {f: (region, ap) for region, rows in data["LOCATIONS"].items() for _, ap, f in rows}
        self.assertEqual(by_flag[400452], ("Liurnia", 7774641))
        self.assertIn(12037800, by_flag)  # Ordinary rune pickup is independently tracked.
        lots = runpy.run_path(str(PKG / "tables/check_lots_data.py"))
        self.assertEqual(lots["CHECK_LOT_SLOTS_MAP"][104512], [1])
        self.assertNotIn(104512, lots["CHECK_LOT_SLOTS_ENEMY"])
        self.assertEqual(runpy.run_path(str(PKG / "tables/missable_locations.py"))["MISSABLE_LOCATIONS"][7774641], "questline")

    def test_npc_batch_namespace_from_committed_params(self):
        if ROOT is None:
            self.skipTest(REPO_ONLY_REASON)
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
