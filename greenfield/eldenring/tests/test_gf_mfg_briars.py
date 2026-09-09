"""Recover the real enemy award, without accepting the synthetic stone collision (#1437)."""
import ast
import csv
import json
from pathlib import Path
import unittest

from .test_gf_mfg_recovered_pickups import assignments


class MfgBriarsRecovery(unittest.TestCase):
    def test_identity_replacement_and_append_id(self):
        root = next(p for p in Path(__file__).resolve().parents
                    if (p / "greenfield/gen_data.py").is_file())
        world = root / "greenfield/eldenring"
        evidence = json.loads((root / "greenfield/evidence/mfg_briars_recovery.json").read_text())
        witness = evidence["witnesses"][0]
        self.assertEqual(witness["pin"]["itemLotId"], 438100012)
        self.assertEqual(witness["pin"]["map"], "m60_38_45")
        self.assertEqual(witness["rows"][0]["item_id"], "4900")
        rows = [r for r in csv.DictReader((root / "greenfield/region_map.csv").open(encoding="utf-8-sig"))
                if r["flag"] == "1038457500"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["flag_source"], "enemy_lot")
        self.assertEqual(rows[0]["item_name"], "Briars of Sin")
        data = assignments(world / "tables/data.py")
        checks = [(region, name, aid) for region, values in data["LOCATIONS"].items()
                  for name, aid, flag in values if flag == 1038457500]
        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0][0], "Liurnia")
        self.assertEqual(checks[0][2], 7774631)
        self.assertEqual(assignments(world / "tables/item_ids.py")["LOCATION_ITEM"][7774631], "Briars of Sin")
        self.assertEqual(assignments(world / "tables/check_lots_data.py")["CHECK_LOT_SLOTS_ENEMY"][438100012], [2])
        # Execute the actual synthetic predicate with controlled award/name evidence.
        # The historical false stone claim must remain rejected after source correction.
        tree = ast.parse((root / "greenfield/gen_data.py").read_text(encoding="utf-8"))
        predicate = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                         and n.name == "_synthetic_award_ok")
        env = {"_SYN_GUARD_ON": True, "LOT_ITEMS": {1038457500: {0x40000000 | 4900}},
               "_resolve_item": lambda name: (0x40000000 | (4900 if name == "Briars of Sin" else 10101), name)}
        exec(compile(ast.Module(body=[predicate], type_ignores=[]), "gen_data.py", "exec"), env)
        old = dict(rows[0], flag_source="synthetic", method="synthetic_areacode", item_name="Smithing Stone [2]")
        self.assertFalse(env["_synthetic_award_ok"](old))
        self.assertTrue(env["_synthetic_award_ok"](dict(old, item_name="Briars of Sin")))
