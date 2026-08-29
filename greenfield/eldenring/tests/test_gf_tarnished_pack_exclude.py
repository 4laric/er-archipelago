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

    def test_verified_player_equipment_is_a_strict_subset_of_the_row_census(self):
        self.assertEqual(len(tp.TARNISHED_PACK_EQUIPMENT), 26)
        self.assertEqual(len(set(tp.TARNISHED_PACK_EQUIPMENT.values())), 26)
        self.assertTrue(set(tp.TARNISHED_PACK_EQUIPMENT.values()) <= tp.TARNISHED_PACK_FULL_IDS)
        self.assertNotIn(3_910_000, tp.TARNISHED_PACK_EQUIPMENT.values())
        self.assertNotIn(13_900_000, tp.TARNISHED_PACK_EQUIPMENT.values())
        self.assertFalse(
            {0x4000_0000 | row_id for row_id in tp.TARNISHED_PACK_GOODS_IDS}
            & set(tp.TARNISHED_PACK_EQUIPMENT.values()))

    def test_typed_datamine_names_cover_every_player_equipment_row(self):
        self.assertEqual(len(tp.TARNISHED_PACK_PARAM_NAMES), len(tp.TARNISHED_PACK_EQUIPMENT))
        self.assertEqual(set(tp.TARNISHED_PACK_PARAM_NAMES.values()),
                         set(tp.TARNISHED_PACK_EQUIPMENT))

    def test_verified_location_slices_have_eleven_shops_and_three_field_pickups(self):
        self.assertEqual(len(tp.TARNISHED_PACK_LOCATION_FLAGS), 14)
        self.assertTrue({150680, 160660, 170090, 280960}
                        <= tp.TARNISHED_PACK_LOCATION_FLAGS)
        self.assertTrue({1_038_417_020, 1_047_427_000, 1_050_407_000}
                        <= tp.TARNISHED_PACK_LOCATION_FLAGS)
        self.assertEqual(frozenset(tp.TARNISHED_PACK_LOCATION_ORDER),
                         tp.TARNISHED_PACK_LOCATION_FLAGS)
        self.assertEqual(tp.TARNISHED_PACK_LOCATION_ORDER[-3:],
                         (1_038_417_020, 1_047_427_000, 1_050_407_000))

    def test_matching_catalog_items_follow_the_ownership_toggle(self):
        catalog = {
            f"Patch item {index}": full_id
            for index, full_id in enumerate(sorted(tp.TARNISHED_PACK_FULL_IDS))
        }
        catalog["Unrelated item"] = 123_456

        for dlc_on in (False, True):
            excluded = tp.pool_excluded_names(dlc_on, {"DLC item"}, catalog, False)
            self.assertTrue(set(catalog) - {"Unrelated item"} <= excluded)
            self.assertNotIn("Unrelated item", excluded)
            self.assertEqual("DLC item" in excluded, not dlc_on)
            enabled = tp.pool_excluded_names(dlc_on, {"DLC item"}, catalog, True)
            self.assertFalse(tp.tarnished_pack_names(catalog) & enabled)

    def test_nearby_ids_do_not_match(self):
        full_id = min(tp.TARNISHED_PACK_FULL_IDS)
        catalog = {"Patch item": full_id, "Adjacent row": full_id + 1}
        self.assertEqual(tp.tarnished_pack_names(catalog), frozenset({"Patch item"}))

    def test_generated_equipment_is_honorary_s_tier_in_the_right_category(self):
        def load(name):
            spec = importlib.util.spec_from_file_location(
                name, os.path.join(_HERE, "..", name + ".py"))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module

        item_ids = load("item_ids")
        item_tiers = load("item_tiers")
        for name, full_id in tp.TARNISHED_PACK_EQUIPMENT.items():
            self.assertEqual(item_ids.ITEM_CATALOG.get(name), full_id)
            self.assertEqual(item_tiers.ITEM_TIERS.get(name), 3, name)
            want_category = "ARMOR" if full_id & 0xF000_0000 == 0x1000_0000 else "WEAPON"
            self.assertEqual(item_tiers.ITEM_TIER_CATEGORY.get(name), want_category, name)


if __name__ == "__main__":
    unittest.main()
