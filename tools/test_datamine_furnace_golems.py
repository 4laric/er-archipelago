"""Synthetic end-to-end census fixtures; no game files are needed."""
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


TOOL = Path(__file__).with_name('datamine_furnace_golems.py')


class FurnaceCensusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.msb = self.root / 'maps'
        self.ar = self.root / 'artifacts'
        self.out = self.root / 'results'
        self.vv = self.ar / 'vanilla_er/vanilla_er'
        self.vv.mkdir(parents=True)
        event = self.ar / 'event'
        event.mkdir()
        self.event = event / 'synthetic.js'
        calls, npcs, lots, enemy, names = [], [], [], [], []
        for i in range(8):
            eid = 100 + i
            npc = 200 + i
            lot = 1000 + i * 10
            self.part(f'm{i:02}_00_00_00', eid, npc)
            calls.append(f'$InitializeCommonEvent(0, 90005301, {300+i}, {eid}, {lot}, 4, 0);')
            npcs.append(dict(ID=npc, itemLotId_map=-1, itemLotId_enemy=400+i, getSoul=0))
            enemy.append(dict(ID=400+i, **{f'lotItemId{j:02}': 0 for j in range(1, 9)}))
            for offset in range(2):
                item = 500 + i * 2 + offset
                row = dict(ID=lot+offset, getItemFlagId=600+i*2+offset)
                for j in range(1, 9):
                    row.update({f'lotItemId{j:02}': item if j == 1 else 0,
                                f'lotItemBasePoint{j:02}': 1000 if j == 1 else 0,
                                f'lotItemCategory{j:02}': 1 if j == 1 else 0,
                                f'lotItemNum{j:02}': 1 if j == 1 else 0})
                lots.append(row)
                names.append(f'<text id="{item}">Synthetic reward {item}</text>')
        self.part('m00_00_00_10', 100, 200)
        dummy = self.msb / 'm00_00_00_00-msb-dcx/Part/DummyEnemy/empty.xml'
        dummy.parent.mkdir()
        dummy.write_text('<DummyEnemy><Name>synthetic empty dummy</Name></DummyEnemy>')
        self.event.write_text('\n'.join(calls), encoding='utf-8')
        (event / 'common_func.emevd.dcx.js').write_text(
            '$Event(90005301, Restart, function() {\n'
            'WaitFor(CharacterRatioDead(chrEntityId));\n'
            'SetEventFlagID(eventFlagId, ON);\n'
            'AwardItemsIncludingClients(itemLotId);\n});', encoding='utf-8')
        self.write_csv('NpcParam', npcs)
        self.write_csv('ItemLotParam_enemy', enemy)
        self.write_csv('ItemLotParam_map', lots)
        fmg = self.ar / 'msg/engus/synthetic/GoodsName.fmg.xml'
        fmg.parent.mkdir(parents=True)
        fmg.write_text('<fmg>' + ''.join(names) + '</fmg>', encoding='utf-8')

    def part(self, map_id, eid, npc):
        p = self.msb / f'{map_id}-msb-dcx/Part/Enemy/arbitrary-filename.xml'
        p.parent.mkdir(parents=True)
        p.write_text(f'<Enemy><Name>synthetic-{eid}</Name><ModelName>c5170</ModelName>'
                     f'<NPCParamID>{npc}</NPCParamID><EntityID>{eid}</EntityID>'
                     '<ThinkParamID>1</ThinkParamID><Position><X>1</X><Y>2</Y><Z>3</Z>'
                     '</Position></Enemy>', encoding='utf-8')

    def write_csv(self, name, rows):
        with (self.vv / (name + '.csv')).open('w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)

    def run_tool(self, optimized=False):
        return subprocess.run([sys.executable, *(['-O'] if optimized else []), str(TOOL),
                               '--msb', str(self.msb), '--artifacts', str(self.ar),
                               '--out', str(self.out)], capture_output=True, text=True)

    def test_full_join_deduplicates_versions_and_keeps_both_rewards(self):
        result = self.run_tool()
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((self.out / 'manifest.json').read_text())
        self.assertEqual((manifest['distinct_entities'], manifest['reward_rows'],
                          manifest['c5170_records'], manifest['empty_model_records']), (8, 16, 9, 1))
        self.assertNotIn(str(self.root), (self.out / 'manifest.json').read_text())
        with (self.out / 'drops.tsv').open() as f:
            drops = list(csv.DictReader(f, delimiter='\t'))
        self.assertEqual([d['lot_id'] for d in drops if d['entity_id'] == '100'], ['1000', '1001'])
        self.assertNotEqual(drops[0]['death_flag'], drops[0]['acquisition_flag'])

    def test_missing_award_refuses_even_with_python_optimization(self):
        lines = self.event.read_text().splitlines()
        self.event.write_text('\n'.join(lines[:-1]))
        result = self.run_tool(optimized=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Unresolved entities', result.stderr)
        self.assertFalse(self.out.exists())

    def test_missing_sibling_reward_refuses_to_publish(self):
        with (self.vv / 'ItemLotParam_map.csv').open() as f:
            rows = list(csv.DictReader(f))
        self.write_csv('ItemLotParam_map', [r for r in rows if r['ID'] != '1001'])
        result = self.run_tool()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Expected two reward rows', result.stderr)
        self.assertFalse(self.out.exists())


if __name__ == '__main__':
    unittest.main()
