#!/usr/bin/env python3
"""Validate and stage the pinned, paired vanilla Map For Goblins build."""
from __future__ import annotations
import argparse
import configparser
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import shutil
import struct
import tomllib

IDENTITY = ('schema_version', 'source_repository', 'source_commit', 'profile', 'input_sha256')
FILES = {'dll_sha256': 'MapForGoblins.dll', 'ini_sha256': 'MapForGoblins.ini', 'license_sha256': 'LICENSE.txt'}
PRESET = {'Loot': {'show_material_nodes': 'false', 'show_crafting_materials': 'true'},
          'Archipelago': {'ap_checks_only': 'true', 'ap_progression_only': 'false',
                         'ap_in_logic_only': 'false', 'ap_progression_rings': 'false',
                         'ap_progression_scale': '1.5'}}
MANIFEST = 'MFG-PROVENANCE.json'


class MfgError(ValueError):
    """Invalid or unpaired release artifact."""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_lock(path: Path) -> dict:
    lock = json.loads(path.read_text(encoding='utf-8-sig'))
    if lock.get('schema_version') != 1 or lock.get('profile') != 'vanilla':
        raise MfgError('MFG lock requires schema 1 and vanilla profile')
    if lock.get('source_repository') != 'https://github.com/4laric/ERR-MapForGoblins-DLL':
        raise MfgError('MFG source repository is not the approved fork')
    for key, size in [('source_commit', 40), ('input_sha256', 64)]:
        if not re.fullmatch('[0-9a-f]{' + str(size) + '}', str(lock.get(key, ''))):
            raise MfgError('Invalid MFG lock ' + key)
    return lock


def validate_dll(path: Path) -> None:
    raw = path.read_bytes()
    if len(raw) < 1024 or raw[:2] != b'MZ':
        raise MfgError('MFG DLL is missing or not a Windows binary')
    offset = struct.unpack_from('<I', raw, 0x3c)[0]
    if offset < 0x40 or offset + 24 > len(raw) or raw[offset:offset+4] != b'PE\0\0':
        raise MfgError('MFG DLL has an invalid PE header')
    if struct.unpack_from('<H', raw, offset+4)[0] != 0x8664 or not struct.unpack_from('<H', raw, offset+22)[0] & 0x2000:
        raise MfgError('MFG binary must be an x64 DLL')


def validate_ini(path: Path) -> None:
    ini = configparser.ConfigParser(interpolation=None, inline_comment_prefixes=('#', ';'))
    try:
        ini.read_string(path.read_text(encoding='utf-8-sig'))
        for section, fields in PRESET.items():
            for key, value in fields.items():
                if not ini.has_option(section, key) or ini[section][key].strip().lower() != value:
                    raise MfgError(f'MFG AP preset requires [{section}] {key}={value}')
    except configparser.Error as exc:
        raise MfgError('Invalid MFG INI: ' + str(exc)) from exc


def validate_files(directory: Path, staged=False) -> None:
    for name in ('MapForGoblins.dll', 'MapForGoblins.ini', 'MFG-LICENSE.txt' if staged else 'LICENSE.txt'):
        path = directory / name
        if not path.is_file() or path.is_symlink():
            raise MfgError('Missing or linked MFG artifact: ' + name)
    validate_dll(directory / 'MapForGoblins.dll')
    validate_ini(directory / 'MapForGoblins.ini')
    license_text = (directory / ('MFG-LICENSE.txt' if staged else 'LICENSE.txt')).read_text(encoding='utf-8-sig')
    if 'VirusAlex' not in license_text or 'Permission is hereby granted' not in license_text:
        raise MfgError('MFG license notice missing')


def record_artifact(directory: Path, lock_path: Path) -> dict:
    """Record trusted build output; build workflow must check out the lock commit."""
    lock = load_lock(lock_path)
    validate_files(directory)
    manifest = {key: lock[key] for key in IDENTITY}
    manifest.update({key: digest(directory / name) for key, name in FILES.items()})
    (directory / MANIFEST).write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest


def validate_artifact(directory: Path, lock_path: Path, staged=False) -> dict:
    lock = load_lock(lock_path)
    validate_files(directory, staged)
    manifest = json.loads((directory / MANIFEST).read_text(encoding='utf-8-sig'))
    for key in IDENTITY:
        if manifest.get(key) != lock[key]:
            raise MfgError('MFG provenance does not match lock: ' + key)
    for key, name in FILES.items():
        if staged and name == 'LICENSE.txt':
            name = 'MFG-LICENSE.txt'
        if manifest.get(key) != digest(directory / name):
            raise MfgError('MFG artifact hash mismatch: ' + name)
    return manifest


def configured_profile(text: str, require=False) -> str:
    document = tomllib.loads(text)
    natives = document.get('natives', [])
    if not isinstance(natives, list) or any(not isinstance(n, dict) for n in natives):
        raise MfgError('Invalid native entries in ap.me3')
    found = []
    for native in natives:
        path = native.get('path')
        if not isinstance(path, str):
            raise MfgError('Native path must be a string')
        if PureWindowsPath(path).name.lower() == 'mapforgoblins.dll':
            found.append(native)
    if len(found) > 1:
        raise MfgError('Duplicate MapForGoblins native entries')
    if found:
        if found[0].get('path') != 'MapForGoblins.dll':
            raise MfgError('MapForGoblins native must use exact portable path')
        return text
    if require:
        raise MfgError('Missing MapForGoblins native entry')
    return text.rstrip() + '\n\n[[natives]]\npath = "MapForGoblins.dll"\n'


def stage_mfg(artifact_dir: Path, me3_dir: Path, lock_path: Path) -> dict:
    artifact_dir, me3_dir, lock_path = map(Path, (artifact_dir, me3_dir, lock_path))
    manifest = validate_artifact(artifact_dir, lock_path)
    profile = me3_dir / 'ap.me3'
    text = configured_profile(profile.read_text(encoding='utf-8-sig'))
    # Validate the complete inputs/profile before copying; exact allowlist only.
    for source, target in [('MapForGoblins.dll', 'MapForGoblins.dll'), ('MapForGoblins.ini', 'MapForGoblins.ini'),
                           ('LICENSE.txt', 'MFG-LICENSE.txt'), (MANIFEST, MANIFEST)]:
        shutil.copy2(artifact_dir / source, me3_dir / target)
    profile.write_text(text, encoding='utf-8')
    validate_staged_mfg(me3_dir, lock_path)
    return manifest


def validate_staged_mfg(me3_dir: Path, lock_path: Path) -> dict:
    me3_dir, lock_path = Path(me3_dir), Path(lock_path)
    manifest = validate_artifact(me3_dir, lock_path, staged=True)
    configured_profile((me3_dir / 'ap.me3').read_text(encoding='utf-8-sig'), require=True)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--record-artifact', type=Path)
    mode.add_argument('--stage', type=Path, help='Paired artifact directory')
    mode.add_argument('--validate-stage', type=Path)
    parser.add_argument('--me3-dir', type=Path)
    parser.add_argument('--lock', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.record_artifact:
            result = record_artifact(args.record_artifact, args.lock)
        elif args.stage:
            if not args.me3_dir:
                parser.error('--stage requires --me3-dir')
            result = stage_mfg(args.stage, args.me3_dir, args.lock)
        else:
            result = validate_staged_mfg(args.validate_stage, args.lock)
    except (OSError, ValueError) as exc:
        parser.exit(1, f'MFG packaging failed: {exc}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
