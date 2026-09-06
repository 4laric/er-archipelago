#!/usr/bin/env python3
"""Parse the bounded generated MapEntry format without executing C++.

Real coordinates precede visual de-overlap. Three-field map IDs deliberately
retain the generated parameter's missing fourth map byte.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
ENTRY = re.compile(
    r'\{(?P<id>\d+)ull,\s*\{(?P<fields>.*?)\},\s*Category::(?P<category>\w+),'
    r'\s*-?\d+,\s*-?\d+,\s*(?P<object>nullptr|"(?:\\.|[^"\\])*"),'
    r'\s*(?P<lot>\d+)u,\s*(?P<table>\d+),\s*(?P<x>' + NUMBER + r')f,'
    r'\s*(?P<z>' + NUMBER + r')f\},', re.S)
FIELD = re.compile(r'\.(\w+)\s*=\s*([^,]+),')

def parse_generated(text: str) -> list[dict]:
    count = re.search(r'const size_t MAP_ENTRY_COUNT = (\d+);', text)
    if not count or int(count[1]) == 0:
        raise ValueError('Missing or empty generated marker count')
    rows, ids = [], set()
    for match in ENTRY.finditer(text):
        rid, lot, table = (int(match[k]) for k in ('id', 'lot', 'table'))
        if rid in ids or table not in (0, 1, 2) or ((table == 0) != (lot == 0)):
            raise ValueError(f'Invalid or duplicate marker identity: {rid}')
        ids.add(rid)
        fields = {}
        if FIELD.sub('', match['fields']).strip():
            raise ValueError(f'Unparsed generated field content: {rid}')
        for key, raw in FIELD.findall(match['fields']):
            if key in fields:
                raise ValueError(f'Duplicate field {key}: {rid}')
            raw = raw.strip()
            if raw in ('true', 'false'):
                fields[key] = raw == 'true'
            elif re.fullmatch(NUMBER + r'[fu]?', raw):
                value = raw.rstrip('fu')
                fields[key] = float(value) if any(c in value.lower() for c in '.e') else int(value)
            else:
                raise ValueError(f'Unsupported field literal {key}: {raw}')
        area, gx, gz = (int(fields.get(k, 0)) for k in ('areaNo', 'gridXNo', 'gridZNo'))
        if not all(0 <= n <= 99 for n in (area, gx, gz)):
            raise ValueError(f'Invalid map fields: {rid}')
        x, y, z = float(match['x']), float(fields.get('posY', 0)), float(match['z'])
        if not all(math.isfinite(n) for n in (x, y, z)):
            raise ValueError(f'Nonfinite coordinates: {rid}')
        generated_xyz = [x, y, z]
        # generate_data.py parse_massedit_files applies this display transform
        # BEFORE snapshotting real_posX/Z (fork e3aa511, lines 252-267).
        # Undo it to compare MSB-local positions; retain both representations.
        transform = None
        if (area, gx) == (11, 10):
            x, z = x + 2195.0, z + 352.0
            transform = 'inverse_roundtable_display_shift'
        rows.append(dict(reference_id=str(rid), map=f'm{area:02}_{gx:02}_{gz:02}',
                         x=x, y=y, z=z, coordinate_frame='map_local',
                         map_precision='three_fields', itemLotId=lot,
                         generated_xyz=generated_xyz, coordinate_transform=transform,
                         lotSource={0:None, 1:'map', 2:'enemy'}[table],
                         lot_source_status='generated_profile', source='native_generated_pin',
                         category=match['category'], param_fields=fields,
                         object_name=None if match['object'] == 'nullptr' else json.loads(match['object'])))
    if len(rows) != int(count[1]):
        raise ValueError(f'Parsed {len(rows)} of {count[1]} declared markers; format changed')
    return rows

def verify_manifest(root: Path, manifest: dict) -> None:
    if manifest.get('profile') != 'vanilla':
        raise ValueError('Expected an explicitly vanilla profile')
    entries = manifest.get('files')
    if not isinstance(entries, list) or not entries:
        raise ValueError('Manifest must list input files')
    paths = [entry['path'] for entry in entries]
    if len(set(paths)) != len(paths):
        raise ValueError('Duplicate manifest paths')
    if 'src/generated_vanilla/goblin_map_data.cpp' not in paths:
        raise ValueError('Consumed map-data file is missing from manifest')
    for entry in entries:
        path = (root / entry['path']).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError('Manifest path escapes bundle')
        data = path.read_bytes()
        if len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError('Manifest mismatch: ' + entry['path'])

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((args.bundle / 'MANIFEST.json').read_text(encoding='utf-8-sig'))
    verify_manifest(args.bundle, manifest)
    rows = parse_generated((args.bundle / 'src/generated_vanilla/goblin_map_data.cpp').read_text(encoding='utf-8-sig'))
    args.output.write_text(json.dumps(rows, indent=2) + '\n', encoding='utf-8')
    print(f'Verified {len(manifest["files"])} input hashes; exported {len(rows)} native pins')

if __name__ == '__main__':
    main()
