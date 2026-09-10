"""Read-only local furnace census; outputs derived facts, never copies source assets."""
import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--msb', required=True, type=Path)
    ap.add_argument('--artifacts', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    sources = {}

    def source(p):
        for root, label in [(a.msb, "msb"), (a.artifacts, "artifacts")]:
            if p.is_relative_to(root):
                return label + "/" + p.relative_to(root).as_posix()
        raise ValueError(f"Source outside declared roots: {p}")

    def read(p):
        b = p.read_bytes()
        sources[source(p)] = {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}
        return b.decode('utf-8-sig')

    vv = a.artifacts / 'vanilla_er/vanilla_er'
    def param(name):
        rows = list(csv.DictReader(read(vv / (name + '.csv')).splitlines()))
        require(len({r['ID'] for r in rows}) == len(rows), name)
        return {int(r['ID']): r for r in rows}

    npc = param('NpcParam')
    lots = param('ItemLotParam_map')
    enemy_lots = param('ItemLotParam_enemy')
    goods = {}
    for p in sorted((a.artifacts / 'msg/engus').glob('*/GoodsName*.fmg.xml')):
        for e in ET.fromstring(read(p)).iter('text'):
            if e.text:
                key = int(e.attrib['id'])
                goods.setdefault(key, set()).add(e.text)
    require(goods, 'No English goods names found')

    maps = sorted(a.msb.glob('*-msb-dcx'))
    require(maps, 'No Witchy MSB directories')
    placements = []
    models = Counter()
    files_scanned = 0
    pool = ThreadPoolExecutor(max_workers=12)
    for map_index, d in enumerate(maps):
        for kind in ['Enemy', 'DummyEnemy']:
            paths = sorted((d / 'Part' / kind).glob('*.xml'))
            for p, b in pool.map(lambda p: (p, p.read_bytes()), paths):
                files_scanned += 1
                match = re.search(rb'<ModelName>([^<]+)</ModelName>', b)
                if not match:
                    root = ET.fromstring(b)
                    node = root.find('ModelName')
                    require((node is not None and not node.text) or (root.tag == 'DummyEnemy' and node is None), f'Missing model field: {p}')
                    models['<empty>'] += 1
                    continue
                model = match[1].decode()
                models[model] += 1
                if model != 'c5170':
                    continue
                t = ET.fromstring(read(p))
                require(t.tag in ('Enemy', 'DummyEnemy'), p)
                row = {k: t.findtext(k) for k in ['Name', 'ModelName', 'NPCParamID', 'EntityID', 'ThinkParamID']}
                require(all(v is not None for v in row.values()), p)
                row.update(msb_map=d.name.removesuffix('-msb-dcx'), part_kind=kind,
                           source=source(p), sha256=sources[source(p)]['sha256'])
                row.update({axis.lower(): float(t.findtext('Position/' + axis)) for axis in 'XYZ'})
                placements.append(row)
        if (map_index + 1) % 200 == 0:
            print(f'Scanned {map_index + 1}/{len(maps)} maps, {files_scanned} records', flush=True)
    pool.shutdown()
    print(f'Scanned {len(maps)} MSBs / {files_scanned} enemy XMLs; c5170={len(placements)}, c4900={models["c4900"]}', flush=True)
    require(placements, 'No c5170 placements')
    by_entity = defaultdict(list)
    for row in placements:
        eid = int(row['EntityID'])
        require(eid > 0, row)
        by_entity[eid].append(row)
    for eid, rows in by_entity.items():
        require(len({r['NPCParamID'] for r in rows}) == 1, (eid, rows))

    awards = defaultdict(list)
    script_count = 0
    call_pattern = re.compile(r'\$InitializeCommonEvent\(\s*\d+,\s*90005301,\s*(\d+),\s*(\d+),\s*(\d+),\s*([\d.]+),\s*(\d+)\s*\);')
    for p in sorted((a.artifacts / 'event').glob('*.js')):
        script_count += 1
        text = p.read_text(encoding='utf-8-sig')
        for m in call_pattern.finditer(text):
            flag, eid, base, delay, value = m.groups()
            if int(eid) in by_entity:
                read(p)
                require(value == '0', (p, m[0]))
                awards[int(eid)].append({'death_flag': int(flag), 'base_lot': int(base),
                                        'delay_seconds': float(delay), 'event_source': source(p),
                                        'event_line': text[:m.start()].count('\n') + 1,
                                        'event_map': p.name.split('.')[0], 'call': m[0]})
    common = a.artifacts / 'event/common_func.emevd.dcx.js'
    text = read(common)
    start = text.index('$Event(90005301,')
    body = text[start:text.index('\n});', start)]
    for instruction in ['WaitFor(CharacterRatioDead(chrEntityId))',
                        'SetEventFlagID(eventFlagId, ON)', 'AwardItemsIncludingClients(itemLotId)']:
        require(instruction in body, instruction)
    require(set(awards) == set(by_entity), ('Unresolved entities', set(by_entity) - set(awards)))
    encounters, drops = [], []
    for eid, ps in sorted(by_entity.items()):
        calls = awards[eid]
        require(len({(r['death_flag'], r['base_lot']) for r in calls}) == 1, (eid, calls))
        call = calls[0]
        n = npc[int(ps[0]['NPCParamID'])]
        # Both NPC channels are checked, even though these placements award through EMEVD.
        require(int(n['itemLotId_map']) == -1, (eid, n['itemLotId_map']))
        enemy_base = int(n['itemLotId_enemy'])
        current = enemy_base
        while current in enemy_lots:
            er = enemy_lots[current]
            require(all(int(er[f'lotItemId{i:02}']) == 0 for i in range(1, 9)), (eid, current))
            current += 1
        require(enemy_base in enemy_lots, enemy_base)
        row = dict(entity_id=eid, npc_id=int(n['ID']), model='c5170',
                   death_flag=call['death_flag'], award_base_lot=call['base_lot'],
                   event_maps=';'.join(sorted({c['event_map'] for c in calls})),
                   placement_records=len(ps), npc_enemy_lot=enemy_base,
                   npc_getSoul_raw=int(n['getSoul']),
                   event_sources=';'.join(f"{c['event_source']}:{c['event_line']}" for c in calls))
        base = call['base_lot']
        require(base in lots, base)
        current = base
        while current in lots:
            lot = lots[current]
            total = sum(int(lot[f'lotItemBasePoint{i:02}']) for i in range(1, 9))
            for i in range(1, 9):
                item = int(lot[f'lotItemId{i:02}'])
                weight = int(lot[f'lotItemBasePoint{i:02}'])
                if item > 0 and weight > 0:
                    category = int(lot[f'lotItemCategory{i:02}'])
                    require(category == 1 and item in goods and len(goods[item]) == 1, (current, item, category))
                    drops.append(dict(entity_id=eid, death_flag=call['death_flag'],
                                      base_lot=base, lot_id=current, slot=i, category=category,
                                      item_id=item, item_name=next(iter(goods[item])),
                                      quantity=int(lot[f'lotItemNum{i:02}']),
                                      acquisition_flag=int(lot['getItemFlagId']),
                                      weight=weight, total_weight=total,
                                      chance_percent=100 * weight / total))
            current += 1
        row['drops'] = '; '.join(f"{d['item_name']} x{d['quantity']}" for d in drops if d['entity_id'] == eid)
        own_drops = [d for d in drops if d['entity_id'] == eid]
        require(len(own_drops) == 2, (eid, 'Expected two reward rows', own_drops))
        encounters.append(row)
    # Validate the full scan's observed result rather than treating a partial scan as complete.
    require(len(encounters) == 8 and len(drops) == 16, (len(encounters), len(drops)))
    require(all(d['chance_percent'] == 100 and d['quantity'] == 1 for d in drops), "Furnace census validation failed: all(d['chance_percent'] == 100 and d['quantity'] == 1 for d in drops)")
    a.out.mkdir(parents=True, exist_ok=True)
    for name, rows in [('placements', placements), ('encounters', encounters), ('drops', drops)]:
        with (a.out / (name + '.tsv')).open('w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter='\t', lineterminator='\n')
            w.writeheader()
            w.writerows(rows)
    manifest = dict(utc=datetime.now(timezone.utc).isoformat(), msb_root='msb',
                    artifacts_root='artifacts', msb_directories=len(maps),
                    enemy_xmls_scanned=files_scanned, event_scripts_scanned=script_count,
                    c4900_records=models['c4900'], c5170_records=models['c5170'],
                    empty_model_records=models['<empty>'],
                    distinct_entities=len(encounters), reward_rows=len(drops),
                    common_event_source=f'{source(common)}:{text[:start].count(chr(10)) + 1}',
                    sources=sources)
    (a.out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    lines = ['# Furnace golem datamine', '', f"Run: {manifest['utc']}", '',
             f"Scanned {len(maps)} Witchy MSB directories, {files_scanned} Enemy/DummyEnemy XMLs, and {script_count} event scripts.", '',
             f'**Result: {len(encounters)} distinct c5170 entities, {len(placements)} placements, {len(drops)} guaranteed item rewards.**', '',
             'The extra placement is entity 2045460200 in map versions m61_11_11_02 and m61_11_11_12. It is one encounter, not two.', '',
             'The repository note naming c4900 is incorrect for this corpus. The full enemy-part scan finds zero c4900 records.', '',
             'Each golem awards one tear plus one Furnace Visage through common event 90005301. Its NPC enemy-lot table rolls only an empty slot. Death flags and item acquisition flags are separate columns; do not substitute one for the other.', '',
             '| Event map | Entity ID | Death flag | Award base lot | Drops |',
             '|---|---:|---:|---:|---|']
    for r in encounters:
        lines.append(f"| {r['event_maps']} | {r['entity_id']} | {r['death_flag']} | {r['award_base_lot']} | {r['drops']} |")
    lines += ['', '## Evidence and limits', '',
              '- `placements.tsv`: all nine original records, NPC IDs, raw map-local XYZ, map versions, source paths, and hashes.',
              '- `encounters.tsv`: deduplicated entities and event call file/line references.',
              '- `drops.tsv`: all sixteen item rows, quantities, weights, item IDs, and acquisition flags.',
              '- `manifest.json`: timestamp, scan coverage, and hashes of the source files used in the joins.',
              '- Coordinates belong to the containing MSB map, not the fine map embedded in the part name.',
              '- `npc_getSoul_raw` is the raw param reward; scaling effects were not evaluated, so it is not a final in-game rune payout.',
              '- Static datamine of the local unpacked corpus. No live-game test, world regeneration, or taxonomy integration was performed.',
              '- Common event 90005301 waits for CharacterRatioDead, delays, sets the death flag, and awards the item-lot group in the player\'s own world. See the exact common-event source reference in the manifest.', '']
    (a.out / 'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(encounters, indent=2), flush=True)


if __name__ == '__main__':
    main()
