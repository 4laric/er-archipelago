"""Hidden Path ordinary traversal recovery: identity, warp geography and kick geometry (#1437)."""
import csv
import json
from pathlib import Path
import unittest
from .test_gf_mfg_recovered_pickups import assignments


class SilverScarabRecovery(unittest.TestCase):
    def test_supported_route_and_replacement_share_one_region(self):
        root = next(p for p in Path(__file__).resolve().parents
                    if (p / 'greenfield/gen_data.py').is_file())
        world = root / 'greenfield/eldenring'
        evidence = json.loads((root / 'greenfield/evidence/mfg_silver_scarab.json').read_text())
        region = 'Consecrated Snowfield'
        self.assertEqual(evidence['access']['inventory_requirements'], [])
        self.assertEqual(evidence['pin']['reference_id'], '2600045')
        self.assertEqual(evidence['pin']['itemLotId'], 30200900)
        self.assertEqual(evidence['pin']['param_fields']['textDisableFlagId1'], 30207900)
        checks = [(reg, aid) for reg, rows in assignments(world / 'data.py')['LOCATIONS'].items()
                  for _, aid, flag in rows if flag == 30207900]
        self.assertEqual(checks, [(region, 7774650)])
        self.assertEqual(assignments(world / 'item_ids.py')['LOCATION_ITEM'][7774650], 'Silver Scarab')
        self.assertEqual(assignments(world / 'check_lots_data.py')['CHECK_LOT_ZERO_MAP'][30200900], [1])
        graces = assignments(world / 'region_graces.py')
        self.assertIn(73020, graces['REGION_GRACE_POINTS'][region])
        self.assertIn(73020, graces['REGION_GRACE_LANDMARKS'][region])
        self.assertIn(30200, assignments(world / 'region_play_ids.py')['REGION_PLAY_IDS'][region])
        with (root / 'greenfield/item_play_regions.tsv').open(encoding='utf-8-sig') as f:
            row = next(r for r in csv.DictReader((line for line in f if not line.startswith('#')), delimiter='\t') if r.get('flag') == '30207900')
        # Both chest volumes fold into the same kick group as its warp anchor.
        self.assertIn('3020002;3020003', row.values())
        self.assertIn('30200', row.values())
        self.assertNotIn(30207900, assignments(world / 'data.py')['NOT_RANDOMIZED'])
        # The other talisman's actual scripted combat gate remains unresolved.
        self.assertIn(1050567820, assignments(world / 'data.py')['NOT_RANDOMIZED'])


def test_silver_scarab_uses_its_own_dungeon_sweep():
    from worlds.eldenring.boss_sweeps import DUNGEON_SWEEPS, SWEEP_REGION
    assert [boss for boss, members in DUNGEON_SWEEPS.items() if 7774650 in members] == [30200800]
    assert SWEEP_REGION[30200800] == "Consecrated Snowfield"
