"""Read the first-party furnace census and explicit region adjudications (#1543)."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'greenfield/evidence/furnace_golems'


def load():
    def rows(name):
        with (EVIDENCE / (name + '.tsv')).open(encoding='utf-8') as f:
            return list(csv.DictReader(f, delimiter='\t'))

    encounters, drops, rulings = rows('encounters'), rows('drops'), rows('regions')
    regions = {int(r['entity_id']): r['region'] for r in rulings}
    entities = {int(r['entity_id']) for r in encounters}
    if len(encounters) != 8 or len(entities) != 8 or len(rulings) != 8 or set(regions) != entities:
        raise ValueError('Incomplete or duplicate furnace encounter/region census')
    if len(drops) != 16 or len({int(r['acquisition_flag']) for r in drops}) != 16:
        raise ValueError('Incomplete or duplicate furnace reward census')
    rewards = {}
    taxonomy = {}
    for e in encounters:
        entity = int(e['entity_id'])
        own = [r for r in drops if int(r['entity_id']) == entity]
        if e['model'] != 'c5170' or len(own) != 2:
            raise ValueError(f'Invalid furnace entity {entity}')
        death = int(e['death_flag'])
        if death in taxonomy:
            raise ValueError(f'Duplicate furnace death flag {death}')
        taxonomy[death] = ('furnace_golem', 'overworld', e['event_maps'].split(';')[0],
                           regions[entity], 'Furnace Golem')
        for r in own:
            flag = int(r['acquisition_flag'])
            if (int(r['death_flag']) != death or int(r['base_lot']) != int(e['award_base_lot'])
                    or int(r['quantity']) != 1 or float(r['chance_percent']) != 100 or flag == death):
                raise ValueError(f'Invalid furnace reward {flag}')
            rewards[flag] = (regions[entity], entity)
    if len(rewards) != len(drops):
        raise ValueError('Unjoined furnace reward')
    return rewards, taxonomy
