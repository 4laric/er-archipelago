"""The registry must preserve unknowns and arity, including non-outdoor sites."""
import importlib.util
from pathlib import Path
import tempfile
import sys
import unittest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _util import find_repo_root, REPO_ONLY_REASON

found_root = find_repo_root(__file__)
ROOT = Path(found_root) if found_root else None
registry = None
if ROOT:
    SPEC = importlib.util.spec_from_file_location(
        "mfg_registry", ROOT / "tools/build_mfg_check_registry.py")
    registry = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(registry)
    sys.path.insert(0, str(ROOT / "tools"))
    from resolve_mfg_hover import resolve


@unittest.skipUnless(ROOT, REPO_ONLY_REASON)
class RegistryTests(unittest.TestCase):
    def fixture(self, root):
        for name in registry.INPUTS:
            (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / registry.INPUTS[0]).write_text(
            "LOCATIONS = {'area': [('A', 1, 10), ('B', 2, 10), ('C', 3, 11)]}",
            encoding="utf-8")
        (root / registry.INPUTS[1]).write_text(
            "flag\ttable\tlot\n10\tmap\t20\n10\tenemy\t20\n", encoding="utf-8")
        (root / registry.INPUTS[2]).write_text(
            "stock_flag\trow_id\n11\t30\n", encoding="utf-8")
        (root / registry.INPUTS[3]).write_text(
            "kind\tkey\tmap_id\tx\ty\tz\n"
            "item\t10\tm10_00_00_00\t1\t2\t3\n"
            "item\t10\tm10_00_00_00\t1\t2\t3\n"
            "item\t10\tm10_00_00_00\t1\t8\t3\n"
            "grace\t99\tm10_00_00_00\t9\t9\t9\n", encoding="utf-8")

    def test_shared_flag_floors_and_id_spaces_are_not_collapsed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            data = registry.build(root)
        a, b, c = data["checks"]
        self.assertEqual(a["co_triggered_ap_ids"], [1, 2])
        self.assertEqual(b["site_status"], "ambiguous_shared_flag")
        self.assertEqual(len(a["physical_sites"]), 2)
        self.assertEqual(a["source_identity"]["item_lots"],
                         [{"table": "enemy", "row_id": 20}, {"table": "map", "row_id": 20}])
        self.assertEqual(c["site_status"], "unresolved")
        self.assertEqual(c["physical_sites"], [])
        self.assertEqual(c["source_identity"]["shop_rows"], [30])
        self.assertTrue(all(site["display_position"] is None for site in a["physical_sites"]))
        self.assertEqual(data["excluded_rows"], {"grace_rows": 1})

    def test_missing_or_invalid_inputs_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            coords = root / registry.INPUTS[3]
            coords.write_text(coords.read_text().replace("\t1\t2\t3", "\tnan\t2\t3"))
            with self.assertRaisesRegex(ValueError, "Invalid physical"):
                registry.build(root)
            coords.unlink()
            with self.assertRaises(FileNotFoundError):
                registry.build(root)

    def test_hover_preserves_shared_siblings_and_rejects_conflicting_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            data = registry.build(root)
        self.assertEqual(resolve(data, 10, "map", 20)["groups"],
                         [{"original_acquisition_flag": 10, "ap_ids": [1, 2]}])
        self.assertEqual(resolve(data, 0, "enemy", 20)["status"], "ambiguous_candidates")
        self.assertEqual(resolve(data, 11, "map", 20)["status"], "unmatched")
        self.assertEqual(resolve(data)["status"], "unmatched")
        with self.assertRaises(ValueError):
            resolve(data, 0, "map")

    def test_real_baked_lot_witness_and_shared_flag(self):
        data = registry.build()
        # flag_lots.tsv: Dark Moon Ring map lot, original acquisition flag 114.
        self.assertEqual(resolve(data, 0, "map", 14000960)["groups"],
                         [{"original_acquisition_flag": 114, "ap_ids": [7770000]}])
        # flag 197 co-fires two AP checks; lot 10180 must NOT select one sibling.
        self.assertEqual(resolve(data, 197, "map", 10180)["groups"],
                         [{"original_acquisition_flag": 197, "ap_ids": [7770007, 7900004]}])
        self.assertEqual(resolve(data, 114, "enemy", 14000960)["status"], "unmatched")

    def test_actual_catalog_totality_determinism_and_provenance(self):
        data = registry.build()
        declared = {ap_id for rows in registry.locations(ROOT / registry.INPUTS[0]).values()
                    for _, ap_id, _ in rows}
        self.assertEqual({r["ap_id"] for r in data["checks"]}, declared)
        self.assertGreaterEqual(len(declared), 4900)
        self.assertEqual(sum(data["coverage"].values()), len(declared))
        self.assertEqual(registry.encode(data), registry.encode(registry.build()))
        self.assertEqual(set(data["sources_sha256"]), set(registry.INPUTS))
        self.assertEqual(data["evidence_kind"], "game_data_derived_not_independent_corroboration")
        self.assertTrue(any(site["map_id"].startswith("m10_") for r in data["checks"]
                            for site in r["physical_sites"]))


if __name__ == "__main__":
    unittest.main()
