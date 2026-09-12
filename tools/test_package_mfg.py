import json
import hashlib
from unittest.mock import patch
import package_mfg
from pathlib import Path
import struct
import tempfile
import unittest
from package_mfg import MfgError, PRESET, record_artifact, stage_mfg, validate_staged_mfg


class MfgPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.artifact, self.me3 = root / 'artifact', root / 'me3'
        self.artifact.mkdir()
        self.me3.mkdir()
        self.lock = root / 'lock.json'
        self.lock.write_text(json.dumps({'schema_version': 1,
            'source_repository': 'https://github.com/4laric/ERR-MapForGoblins-DLL',
            'source_commit': 'a'*40, 'profile': 'vanilla', 'input_sha256': 'b'*64}))
        dll = bytearray(1024)
        dll[:2] = b'MZ'
        struct.pack_into('<I', dll, 0x3c, 0x80)
        dll[0x80:0x84] = b'PE\0\0'
        struct.pack_into('<H', dll, 0x84, 0x8664)
        struct.pack_into('<H', dll, 0x96, 0x2000)
        (self.artifact / 'MapForGoblins.dll').write_bytes(dll)
        (self.artifact / 'MapForGoblins.ini').write_text('\n'.join('['+section+']\n'+'\n'.join(k+'='+v for k,v in fields.items()) for section,fields in PRESET.items()))
        (self.artifact / 'LICENSE.txt').write_text('VirusAlex\nPermission is hereby granted\n')
        (self.me3 / 'ap.me3').write_text('[[natives]]\npath="eldenring_archipelago.dll"\n')
        record_artifact(self.artifact, self.lock)

    def test_paired_stage_is_idempotent_and_allowlisted(self):
        (self.artifact / 'unrelated.dll').write_bytes(b'not shipped')
        stage_mfg(self.artifact, self.me3, self.lock)
        stage_mfg(self.artifact, self.me3, self.lock)
        validate_staged_mfg(self.me3, self.lock)
        self.assertEqual((self.me3 / 'ap.me3').read_text().count('MapForGoblins.dll'), 1)
        self.assertFalse((self.me3 / 'unrelated.dll').exists())
        self.assertTrue((self.me3 / 'MFG-LICENSE.txt').exists())

    def test_tampered_dll_rejected_before_staging(self):
        path = self.artifact / 'MapForGoblins.dll'
        path.write_bytes(path.read_bytes() + b'tamper')
        with self.assertRaisesRegex(MfgError, 'hash mismatch'):
            stage_mfg(self.artifact, self.me3, self.lock)
        self.assertFalse((self.me3 / 'MapForGoblins.dll').exists())

    def test_missing_ini_rejected(self):
        (self.artifact / 'MapForGoblins.ini').unlink()
        with self.assertRaisesRegex(MfgError, 'Missing'):
            stage_mfg(self.artifact, self.me3, self.lock)

    def test_wrong_preset_cannot_be_blessed(self):
        path = self.artifact / 'MapForGoblins.ini'
        path.write_text(path.read_text().replace('ap_checks_only=true', 'ap_checks_only=false'))
        with self.assertRaisesRegex(MfgError, 'preset'):
            record_artifact(self.artifact, self.lock)

    def test_duplicate_profile_rejected(self):
        (self.me3 / 'ap.me3').write_text('[[natives]]\npath="MapForGoblins.dll"\n[[natives]]\npath="mapforgoblins.dll"\n')
        with self.assertRaisesRegex(MfgError, 'Duplicate'):
            stage_mfg(self.artifact, self.me3, self.lock)

    def test_nonportable_profile_rejected(self):
        (self.me3 / 'ap.me3').write_text('[[natives]]\npath="../MapForGoblins.dll"\n')
        with self.assertRaisesRegex(MfgError, 'portable'):
            stage_mfg(self.artifact, self.me3, self.lock)

    def test_other_source_commit_and_input_refused(self):
        for field in ('source_commit', 'input_sha256'):
            lock = json.loads(self.lock.read_text())
            original = lock[field]
            lock[field] = 'c' * len(original)
            self.lock.write_text(json.dumps(lock))
            with self.assertRaisesRegex(MfgError, 'provenance'):
                stage_mfg(self.artifact, self.me3, self.lock)
            lock[field] = original
            self.lock.write_text(json.dumps(lock))

    def test_staged_tampering_detected(self):
        stage_mfg(self.artifact, self.me3, self.lock)
        (self.me3 / 'MFG-LICENSE.txt').write_text('VirusAlex\nPermission is hereby granted\ntamper')
        with self.assertRaisesRegex(MfgError, 'hash mismatch'):
            validate_staged_mfg(self.me3, self.lock)

    def test_arbitrary_binary_not_recordable(self):
        (self.artifact / 'MapForGoblins.dll').write_bytes(b'x'*1024)
        with self.assertRaisesRegex(MfgError, 'Windows binary'):
            record_artifact(self.artifact, self.lock)


class AdapterPackageTests(MfgPackageTests):
    def setUp(self):
        super().setUp()
        raw = (self.artifact / 'MapForGoblins.dll').read_bytes()
        upstream_hash = hashlib.sha256(raw).hexdigest()
        self.enterContext(patch.object(package_mfg, 'UPSTREAM_SHA256', upstream_hash))
        lock = json.loads(self.lock.read_text())
        lock.update(schema_version=2, upstream_version='2.1.3', upstream_sha256=upstream_hash)
        self.lock.write_text(json.dumps(lock))
        (self.artifact / 'MapForGoblins.upstream.dll').write_bytes(raw)
        (self.artifact / 'MapForGoblins.AP.ini').write_text('[AP]\nchecks_only=1\nprogression_only=0\nin_logic_only=1\n')
        (self.artifact / 'licenses').mkdir()
        for name in ('adapter', 'minhook'):
            (self.artifact / 'licenses' / (name + '.txt')).write_text('fixture license')
        record_artifact(self.artifact, self.lock)

    def test_wrong_preset_cannot_be_blessed(self):
        path = self.artifact / 'MapForGoblins.AP.ini'
        path.write_text(path.read_text().replace('checks_only=1', 'checks_only=0'))
        with self.assertRaisesRegex(MfgError, 'preset'):
            record_artifact(self.artifact, self.lock)

    def test_wrong_upstream_cannot_be_blessed(self):
        path = self.artifact / 'MapForGoblins.upstream.dll'
        path.write_bytes(path.read_bytes() + b'wrong release')
        with self.assertRaisesRegex(MfgError, 'renderer hash'):
            record_artifact(self.artifact, self.lock)

    def test_each_dependency_required_before_any_stage_write(self):
        for name in package_mfg.ADAPTER_FILES.values():
            path = self.artifact / name
            raw = path.read_bytes()
            path.unlink()
            with self.assertRaisesRegex(MfgError, 'Missing'):
                stage_mfg(self.artifact, self.me3, self.lock)
            self.assertFalse((self.me3 / 'MapForGoblins.dll').exists())
            path.write_bytes(raw)

    def test_direct_upstream_native_refused(self):
        (self.me3 / 'ap.me3').write_text('[[natives]]\npath="MapForGoblins.upstream.dll"\n')
        with self.assertRaisesRegex(MfgError, 'only by the adapter'):
            stage_mfg(self.artifact, self.me3, self.lock)


if __name__ == '__main__':
    unittest.main()
