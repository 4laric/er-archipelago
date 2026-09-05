#!/usr/bin/env python3
"""Compare AP recorded sites against the accepted MapForGoblins placement reference.

Input: JSON list (native items_database.json or a normalized pin export). Each
record has map, x/y/z, itemLotId, lotSource ('map'/'enemy'), optional reference_id
(default list index), source and coordinate_frame ('map_local', default, or
'folded_world' for m60/m61). Unknown lotSource stays unknown; source='enemy'
never substitutes for the lot table. Display/event flags are not identities.
A profile manifest is required and retained with SHA-256 fingerprints.

This reports spatial comparison and existing AP region labels separately. No
region is inferred from a tile, nearest neighbour, or item name. Thresholds are
explicit report inputs; agreement means within both horizontal and height limits.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re

from export_mfg_check_registry import ROOT, build
from overworld_fold import world_xz
from resolve_mfg_hover import resolve


def position(row):
    map_id = row['map']
    if not isinstance(map_id, str) or not re.fullmatch(r'm[0-9]{2}(?:_[0-9]{2}){0,3}', map_id):
        raise ValueError('Invalid map: ' + repr(map_id))
    xyz = [row[k] for k in ('x', 'y', 'z')]
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in xyz):
        raise ValueError('Invalid coordinates: ' + repr(xyz))
    frame = row.get('coordinate_frame', 'map_local')
    if frame not in ('map_local', 'folded_world'):
        raise ValueError('Unknown coordinate frame: ' + repr(frame))
    if frame == 'folded_world':
        if map_id not in ('m60', 'm61'):
            raise ValueError('folded_world requires m60 or m61')
        space, normalized = map_id, xyz
    else:
        folded = world_xz(map_id, xyz[0], xyz[2])
        if folded:
            space, normalized = folded[0], [folded[1], xyz[1], folded[2]]
        else:
            if map_id.startswith(('m60', 'm61')):
                raise ValueError('Incomplete overworld map-local frame')
            space, normalized = map_id, xyz
    return dict(map=map_id, xyz=xyz, coordinate_frame=frame,
                space=space, normalized_xyz=normalized)


def compare(reference, sites, horizontal, vertical):
    if not sites:
        return {'status': 'newly_positioned', 'nearest': None}
    distances = []
    for site in sites:
        point = position(dict(map=site['map_id'], **dict(zip(('x', 'y', 'z'), site['map_local_xyz']))))
        a, b = reference['space'], point['space']
        partial = False
        if a != b:
            # A compatible interior prefix permits a coordinate comparison, but
            # cannot establish which version/layer owns it. Preserve that distinction.
            partial = (a.startswith(b + '_') or b.startswith(a + '_'))
            if not partial:
                continue
        elif a not in ('m60', 'm61') and a.count('_') < 3:
            partial = True
        a, b = reference['normalized_xyz'], point['normalized_xyz']
        distances.append(dict(horizontal=math.hypot(a[0]-b[0], a[2]-b[2]),
                              vertical=abs(a[1]-b[1]), ap_site=site,
                              partial_map=partial))
    if not distances:
        return {'status': 'different_map', 'nearest': None}
    matching = [d for d in distances if d['horizontal'] <= horizontal and d['vertical'] <= vertical]
    nearest = min(matching or distances, key=lambda d: math.hypot(d['horizontal'], d['vertical']))
    full_matches = [d for d in matching if not d['partial_map']]
    if full_matches:
        status = 'agreement'
        nearest = min(full_matches, key=lambda d: math.hypot(d['horizontal'], d['vertical']))
    elif matching:
        status = 'agreement_partial_map'
    elif any(d['partial_map'] for d in distances):
        status = 'coordinate_disagreement_partial_map'
    else:
        status = 'coordinate_disagreement'
    return {'status': status, 'nearest': nearest, 'matching_site_count': len(matching)}



def report(manifest, records, profile, horizontal=2.0, vertical=2.0):
    if not isinstance(profile, dict) or not profile:
        raise ValueError('Nonempty profile provenance object required')
    if not isinstance(records, list) or not records:
        raise ValueError('Reference must be a nonempty JSON list')
    if any(not math.isfinite(v) or v < 0 for v in (horizontal, vertical)):
        raise ValueError('Tolerances must be finite and nonnegative')
    by_id = {c['ap_id']: c for c in manifest['checks']}
    observations, check_rows, seen = [], {}, set()
    for index, row in enumerate(records):
        if not isinstance(row, dict):
            raise ValueError('Reference row must be an object')
        ref_id = str(row.get('reference_id', index))
        if ref_id in seen:
            raise ValueError('Duplicate reference_id: ' + ref_id)
        seen.add(ref_id)
        pos = position(row)
        table, lot = row.get('lotSource'), row.get('itemLotId')
        if table is not None and table not in ('map', 'enemy', 'unknown'):
            raise ValueError('Invalid lotSource: ' + repr(table))
        if lot is not None and (isinstance(lot, bool) or not isinstance(lot, int) or lot < 0):
            raise ValueError('Invalid itemLotId')
        identity = resolve(manifest, lot_table=table, lot_row=lot) if table in ('map', 'enemy') and lot else {'status': 'unknown_identity', 'groups': []}
        ids = [ap for g in identity['groups'] for ap in g['ap_ids']]
        obs = dict(reference_id=ref_id, reference_position=pos, lot_table=table,
                   lot_row=lot, source=row.get('source'), reference_metadata={k: v for k, v in row.items() if k not in ('x', 'y', 'z')}, identity_status=identity['status'],
                   candidate_ap_ids=ids, comparisons=[])
        for ap_id in ids:
            check = by_id[ap_id]
            comparison = compare(pos, check['physical_sites'], horizontal, vertical)
            comparison.update(ap_id=ap_id, ap_assigned_region=check['region'])
            obs['comparisons'].append(comparison)
            check_rows.setdefault(ap_id, []).append(dict(reference_id=ref_id,
                identity_status=identity['status'], **comparison))
        observations.append(obs)
    checks = []
    for ap_id, check in sorted(by_id.items()):
        rows = check_rows.get(ap_id, [])
        statuses = {r['status'] for r in rows}
        if not rows:
            status = 'no_reference_match'
        elif any(r['identity_status'] == 'ambiguous_candidates' for r in rows):
            status = 'ambiguous_identity'
        elif statuses <= {'agreement', 'agreement_partial_map'}:
            status = 'agreement_partial_map' if 'agreement_partial_map' in statuses else 'agreement'
        elif len(statuses) == 1:
            status = next(iter(statuses))
        else:
            status = 'mixed_reference_sites'
        checks.append(dict(ap_id=ap_id, name=check['name'], ap_assigned_region=check['region'],
                           status=status, reference_site_count=len(rows),
                           ap_site_count=len(check['physical_sites']), comparisons=rows))
    return dict(schema_version=1, reference_authority='accepted_mapforgoblins_placement',
                region_comparison='not_inferred', profile=profile,
                registry_sources_sha256=manifest['sources_sha256'],
                tolerances=dict(horizontal=horizontal, vertical=vertical),
                total_checks=len(checks), total_reference_records=len(records),
                check_status_counts=dict(sorted(Counter(c['status'] for c in checks).items())),
                identity_status_counts=dict(sorted(Counter(o['identity_status'] for o in observations).items())),
                spatial_comparison_counts=dict(sorted(Counter(c['status'] for o in observations for c in o['comparisons']).items())),
                checks=checks, references=observations)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('--profile-manifest', type=Path, required=True)
    parser.add_argument('--repo', type=Path, default=ROOT)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--horizontal-tolerance', type=float, default=2.0)
    parser.add_argument('--vertical-tolerance', type=float, default=2.0)
    args = parser.parse_args()
    try:
        source = args.reference.read_bytes()
        profile_bytes = args.profile_manifest.read_bytes()
        result = report(build(args.repo), json.loads(source), json.loads(profile_bytes),
                        args.horizontal_tolerance, args.vertical_tolerance)
        result['input_sha256'] = {'reference': hashlib.sha256(source).hexdigest(),
                      
                                 'profile_manifest': hashlib.sha256(profile_bytes).hexdigest()}
    except (ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('total_checks', 'total_reference_records', 'check_status_counts', 'identity_status_counts')}, sort_keys=True))


if __name__ == '__main__':
    main()
