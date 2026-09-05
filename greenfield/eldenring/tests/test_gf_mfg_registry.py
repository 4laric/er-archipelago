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
        "mfg_registry", ROOT / "tools/export_mfg_check_registry.py")
    registry = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(registry)
    sys.path.insert(0, str(ROOT / "tools"))
    from resolve_mfg_hover import resolve
    from report_mfg_marker_coverage import report


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

    def test_native_marker_coverage_preserves_groups_and_namespaces(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            data = registry.build(root)
        csv = (b"marker_row_id,lot_table,lot_row\n"
               b"1,1,20\n2,2,20\n3,0,0\n4,1,99\n")
        result = report(data, csv)
        self.assertEqual(result["checks_with_candidate_markers"], [1, 2])
        self.assertEqual(result["checks_without_candidate_markers"], [3])
        self.assertEqual(result["marker_status_counts"], {
            "shared_flag_candidates": 2, "unknown_identity": 1, "unmatched": 1})
        self.assertEqual(result["marker_status_counts_by_table"], {
            "0": {"unknown_identity": 1},
            "1": {"shared_flag_candidates": 1, "unmatched": 1},
            "2": {"shared_flag_candidates": 1},
        })
        self.assertEqual(result["candidate_check_status_counts"], {
            "no_candidate_marker": 1, "shared_flag_candidate": 2,
        })
        self.assertEqual(result["checks_by_candidate_status"], {
            "no_candidate_marker": [3], "shared_flag_candidate": [1, 2],
        })
        self.assertEqual(result["registry_sources_sha256"], data["sources_sha256"])
        self.assertEqual(result["markers"][0]["groups"][0]["ap_ids"], [1, 2])
        # Same numeric row in the wrong namespace must not match.
        data["checks"][0]["source_identity"]["item_lots"] = [{"table": "map", "row_id": 20}]
        data["checks"][1]["source_identity"]["item_lots"] = [{"table": "map", "row_id": 20}]
        self.assertEqual(report(data, csv)["markers"][1]["status"], "unmatched")

    def test_candidate_classification_keeps_cross_flag_ambiguity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            data = registry.build(root)
        data["checks"].append({
            "ap_id": 4,
            "original_acquisition_flag": 11,
            "source_identity": {"item_lots": [{"table": "map", "row_id": 20}]},
        })
        marker_csv = b"marker_row_id,lot_table,lot_row\n1,1,20\n2,2,20\n"
        result = report(data, marker_csv)
        self.assertEqual(result["marker_status_counts"], {
            "multiple_flag_candidates": 1, "shared_flag_candidates": 1,
        })
        self.assertEqual(result["candidate_check_status_counts"], {
            "multiple_flag_candidate": 3, "no_candidate_marker": 1,
        })
        self.assertEqual(result["checks_by_candidate_status"], {
            "multiple_flag_candidate": [1, 2, 4], "no_candidate_marker": [3],
        })

    def test_native_marker_inventory_rejects_malformed_and_unknown_pairs(self):
        data = registry.build()
        header = b"marker_row_id,lot_table,lot_row\n"
        for rows in (b"", b"1,0,2\n", b"1,1,0\n", b"1,3,2\n",
                     b"1,1,20\n1,2,20\n", b"bad,1,2\n", b"1,2\n",
                     b"1,2,3,4\n", b"-1,1,2\n"):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                report(data, header + rows)
        with self.assertRaises(ValueError):
            report(data, b"wrong,header\n")

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
