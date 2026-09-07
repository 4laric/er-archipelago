"""M4G #1437: six one-time enemy awards and the Ghostflame sibling stone."""
import csv
import importlib.util
import json
from pathlib import Path
import runpy
import unittest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    from _util import find_repo_root, REPO_ONLY_REASON
# None when the world is installed into an AP checkout OUTSIDE the repo. The `next(...)` this
# replaced raised StopIteration at import time there and took the whole file down at collection.
_ROOT = find_repo_root(__file__)
ROOT = Path(_ROOT) if _ROOT else None
GF = ROOT / "greenfield" if ROOT else None
PKG = Path(__file__).resolve().parent.parent


class SomberRecoveries(unittest.TestCase):
    def test_distinct_acquisition_flags_replace_all_seven_native_lots(self):
        if ROOT is None:
            self.skipTest(REPO_ONLY_REASON)
        records = json.loads((GF / "evidence/mfg_somber_recoveries.json").read_text())["recoveries"]
        data = runpy.run_path(str(PKG / "tables/data.py"))
        by_flag = {f: (region, ap) for region, rows in data["LOCATIONS"].items() for _, ap, f in rows}
        slots = runpy.run_path(str(PKG / "tables/check_lots_data.py"))["CHECK_LOT_SLOTS_MAP"]
        with (GF / "flag_lots.tsv").open() as fh:
            lots = list(csv.DictReader(fh, delimiter="\t"))
        expected_ids = {530861: 7774642, 540424: 7774643, 540428: 7774644,
                        540912: 7774645, 540914: 7774646, 540920: 7774647, 540922: 7774648}
        self.assertEqual({r["flag"]: by_flag[r["flag"]][1] for r in records}, expected_ids)
        self.assertEqual(len(records), 7)
        self.assertEqual(len({r["lot"] for r in records}), 7)
        for r in records:
            self.assertIn(r["flag"], by_flag)
            self.assertEqual(slots[r["lot"]], [1])
            self.assertTrue(any(int(x["flag"]) == r["flag"] and int(x["lot"]) == r["lot"] for x in lots))
            if r["flag"] != r["display_flag"]:
                self.assertNotIn(r["display_flag"], by_flag)
        # One boss grants two distinct acquisition flags, not two checks for one flag.
        self.assertEqual(by_flag[530860][0], by_flag[530861][0])
        self.assertNotEqual(by_flag[530860][1], by_flag[530861][1])

    def test_corroborated_filler_candidates_resolve_without_reviving_all_filler(self):
        if ROOT is None:
            self.skipTest(REPO_ONLY_REASON)
        spec = importlib.util.spec_from_file_location("unplaced_somber", ROOT / "tools/datamine_unplaced_globals.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        candidates, _ = mod.candidates()
        resolved, _, _ = mod.resolve(candidates)
        rows = {f: m for f, m, _, _ in resolved}
        for flag, expected_map in mod.mfg_filler_recoveries().items():
            self.assertEqual(rows[flag], expected_map)
        # A dead Leyndell stone in the same global_filler class stays refused.
        self.assertNotIn("11007995", rows)

    def test_scarab_event_calls_match_the_pin_identity(self):
        if ROOT is None:
            self.skipTest(REPO_ONLY_REASON)
        records = json.loads((GF / "evidence/mfg_somber_recoveries.json").read_text())["recoveries"]
        events = ROOT / "elden_ring_artifacts/event"
        if not events.is_dir():
            self.skipTest("gen_inputs.db not extracted")
        for r in records:
            source = (events / (r["map"] + "_00.emevd.dcx.js")).read_text(encoding="utf-8")
            if r["event_id"] in (90005300, 90005301):
                self.assertIn(f'{r["event_id"]}, {r["defeat_flag"]}, {r["defeat_flag"]}, {r["lot"]}, 0, 0)', source)
            else:
                self.assertIn(f'90005860, {r["defeat_flag"]}, 0, {r["defeat_flag"]}, 1, 30860, 0)', source)


if __name__ == "__main__":
    unittest.main()
