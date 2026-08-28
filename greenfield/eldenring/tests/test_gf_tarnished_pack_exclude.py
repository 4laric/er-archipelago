"""AP-free tests for the Patch 1.17 item-pool safety boundary (#1096)."""

import importlib.util
import os
import unittest


_HERE = os.path.dirname(os.path.abspath(__file__))
try:  # installed apworld (CI)
    from worlds.eldenring import tarnished_pack as tp  # type: ignore
except Exception:  # bare source tree (sandbox)
    _spec = importlib.util.spec_from_file_location(
        "tarnished_pack", os.path.join(_HERE, "..", "tarnished_pack.py"))
    tp = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(tp)


class TarnishedPackDecision(unittest.TestCase):
    def test_verified_census_has_expected_category_counts(self):
        self.assertEqual(len(tp.TARNISHED_PACK_WEAPON_IDS), 10)
        self.assertEqual(len(tp.TARNISHED_PACK_ARMOR_IDS), 18)
        self.assertEqual(len(tp.TARNISHED_PACK_GOODS_IDS), 3)
        self.assertEqual(len(tp.TARNISHED_PACK_FULL_IDS), 31)

    def test_full_ids_use_the_game_item_category_namespaces(self):
        self.assertTrue(tp.TARNISHED_PACK_WEAPON_IDS <= tp.TARNISHED_PACK_FULL_IDS)
        self.assertTrue(
            {0x1000_0000 | row_id for row_id in tp.TARNISHED_PACK_ARMOR_IDS}
            <= tp.TARNISHED_PACK_FULL_IDS)
        self.assertTrue(
            {0x4000_0000 | row_id for row_id in tp.TARNISHED_PACK_GOODS_IDS}
            <= tp.TARNISHED_PACK_FULL_IDS)

    def test_matching_catalog_items_are_excluded_unconditionally(self):
        catalog = {
            f"Patch item {index}": full_id
            for index, full_id in enumerate(sorted(tp.TARNISHED_PACK_FULL_IDS))
        }
        catalog["Unrelated item"] = 123_456

        for dlc_on in (False, True):
            excluded = tp.pool_excluded_names(dlc_on, {"DLC item"}, catalog)
            self.assertTrue(set(catalog) - {"Unrelated item"} <= excluded)
            self.assertNotIn("Unrelated item", excluded)
            self.assertEqual("DLC item" in excluded, not dlc_on)

    def test_nearby_ids_do_not_match(self):
        full_id = min(tp.TARNISHED_PACK_FULL_IDS)
        catalog = {"Patch item": full_id, "Adjacent row": full_id + 1}
        self.assertEqual(tp.tarnished_pack_names(catalog), frozenset({"Patch item"}))


if __name__ == "__main__":
    unittest.main()
