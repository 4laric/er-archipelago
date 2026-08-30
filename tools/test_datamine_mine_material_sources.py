import csv
import tempfile
import unittest
from pathlib import Path

from tools import datamine_mine_material_sources as census


class MineMaterialCensusTests(unittest.TestCase):
    def test_model_name_maps_to_asset_geometry_row(self):
        self.assertEqual(census.geometry_id("AEG099_860"), 99860)
        self.assertEqual(census.geometry_id("AEG099_879"), 99879)
        self.assertIsNone(census.geometry_id("c1000"))

    def test_placed_asset_keeps_map_and_instance_provenance(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            asset_dir = root / "m60_39_50_00-msb-dcx" / "Part" / "Asset"
            asset_dir.mkdir(parents=True)
            (asset_dir / "ore.xml").write_text(
                "<Asset><Name>ore_1</Name><ModelName>AEG099_863</ModelName>"
                "<InstanceID>9000</InstanceID><EntityID>1041501950</EntityID></Asset>",
                encoding="utf-8")
            templates = {99863: {"lot_field": "pickUpItemLotParamId", "lot_id": 998630,
                                 "repeatable": "yes", "break_on_pickup": "yes",
                                 "rewards": []}}
            self.assertEqual(list(census.placed_assets(str(root), templates)), [{
                "map_id": "m60_39_50", "asset_name": "ore_1", "model_name": "AEG099_863",
                "instance_id": 9000, "asset_entity_id": 1041501950, "geometry_id": 99863,
            }])

    def test_emit_keeps_capstone_separate(self):
        templates = {99868: {
            "lot_field": "pickUpItemLotParamId", "lot_id": 998680,
            "repeatable": "yes", "break_on_pickup": "yes", "rewards": [{
                "goods_id": 10140, "item_name": "Ancient Dragon Smithing Stone",
                "quantity": 1, "family": "regular", "tier": 0, "capstone": "yes",
            }],
        }}
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "census.tsv"
            rows = census.emit(str(out), templates, None)
            self.assertEqual(rows[0]["capstone"], "yes")
            parsed = list(csv.DictReader(
                (line for line in out.read_text(encoding="utf-8").splitlines()
                 if not line.startswith("#")), delimiter="\t"))
            self.assertEqual(parsed[0]["item_name"], "Ancient Dragon Smithing Stone")


if __name__ == "__main__":
    unittest.main()
