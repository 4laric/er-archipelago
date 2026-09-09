"""Stable and prerelease bundles keep strict paired MFG and version identity gates."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pack_release as pack
import package_mfg as mfg


class MfgPackageTests(unittest.TestCase):
    def test_stable_archive_loads_pinned_mfg_and_keeps_numeric_handshake(self):
        self.check_archive("")

    def test_alpha_archive_loads_pinned_mfg_and_keeps_numeric_handshake(self):
        self.check_archive("alpha.1")

    def check_archive(self, prerelease):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            me3, artifact = root / 'me3', root / 'mfg'
            me3.mkdir(); artifact.mkdir()
            (me3 / 'eldenring_archipelago.dll').write_bytes(b'x' * 1024)
            # No local ap.me3 or detection tables: the clean-checkout packaging path.
            for size in ('hi', 'low'):
                sheet = me3 / 'flower-package' / 'menu' / size / '01_common.tpf.dcx'
                sheet.parent.mkdir(parents=True)
                sheet.write_bytes(b'fixture')
            dll = bytearray(1024)
            dll[:2] = b'MZ'
            struct.pack_into('<I', dll, 0x3c, 0x80)
            dll[0x80:0x84] = b'PE\0\0'
            struct.pack_into('<H', dll, 0x84, 0x8664)
            struct.pack_into('<H', dll, 0x96, 0x2000)
            (artifact / 'MapForGoblins.dll').write_bytes(dll)
            (artifact / 'MapForGoblins.ini').write_text('\n'.join(
                '[' + section + ']\n' + '\n'.join(k+'='+v for k, v in fields.items())
                for section, fields in mfg.PRESET.items()))
            (artifact / 'LICENSE.txt').write_text('VirusAlex\nPermission is hereby granted\n')
            mfg.record_artifact(artifact, Path(pack.REL, 'MFG-VERSION.json'))
            apworld = root / 'eldenring.apworld'
            apworld.write_bytes(b'fixture')
            argv = ['pack_release', '--version', '0.6.0',
                    '--mfg', str(artifact), '--me3', str(me3), '--apworld', str(apworld),
                    '--out', str(root / 'out')]
            if prerelease:
                argv += ["--prerelease", prerelease]
            pack.WARNINGS.clear()
            with patch.object(sys, 'argv', argv), patch.object(pack, 'gate_changelog') as notes, \
                    patch.object(pack, 'gate_version_lockstep') as versions, \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(pack.main(), 0)
            notes.assert_called_once_with('0.6.0', True)
            versions.assert_called_once_with('0.6.0', None, True)
            label = '0.6.0' + ('-' + prerelease if prerelease else '')
            with zipfile.ZipFile(next((root / 'out').glob(f'ER-Archipelago-v{label}-*.zip'))) as archive:
                names = archive.namelist()
                build = json.loads(archive.read("RELEASE-BUILD.json"))
                self.assertEqual(build["prerelease"], prerelease or None)
                self.assertEqual(build["version"], "0.6.0")
                profile_name = next(n for n in names if n == 'me3/ap.me3')
                profile = tomllib.loads(archive.read(profile_name).decode())
                self.assertIs(profile['mem_patch'], False)
                self.assertEqual([n['path'] for n in profile['natives']],
                                 ['eldenring_archipelago.dll', 'MapForGoblins.dll'])
                self.assertEqual(profile.get('packages', []), [])
                self.assertFalse(any('flower-package/' in n or n.endswith('.tpf.dcx') for n in names))
                prefix = profile_name.removesuffix('ap.me3')
                for name in ['MFG-PROVENANCE.json', 'MFG-LICENSE.txt', 'MapForGoblins.ini',
                             'check_lots_table.json', 'shoplineup_flags.json']:
                    self.assertIn(prefix + name, names)
                self.assertFalse(any("torrent_rideparam_repair" in n.lower() or "tarnished-torrent" in n.lower() for n in names))
                self.assertIsNone(archive.testzip())

    def test_stable_cannot_omit_mfg(self):
        argv = ["pack_release", "--version", "0.6.0", "--apworld", "unused"]
        with patch.object(sys, "argv", argv), self.assertRaises(SystemExit), \
                contextlib.redirect_stderr(io.StringIO()):
            pack.main()

    def test_alpha_cannot_omit_mfg_or_relax_identity_gates(self):
        for extra in ([], ['--unofficial', '--stamp', 'test'], ['--prerelease', '../bad']):
            argv = ['pack_release', '--version', '0.6.0', '--prerelease', 'alpha.1',
                    '--apworld', 'unused', *extra]
            with patch.object(sys, 'argv', argv), self.assertRaises(SystemExit), \
                    contextlib.redirect_stderr(io.StringIO()):
                pack.main()


class StaleFlowerAtlasGateTests(unittest.TestCase):
    """The pre-Tarnished atlases (#1181) are refused by sha256, not by a version literal.

    The v0.6.0 omission branch matches the version string "0.6.0" EXACTLY, so v0.6.0.4 and
    v0.6.0.5 took the other arm and re-shipped the stale atlases. The defect is in the bytes.
    """

    HI = 'menu/hi/01_common.tpf.dcx'
    LOW = 'menu/low/01_common.tpf.dcx'

    def build_package(self, tmp, hi=b'fresh-hi', low=b'fresh-low'):
        root = Path(tmp) / 'flower-package'
        for relative, payload in ((self.HI, hi), (self.LOW, low)):
            path = root.joinpath(*relative.split('/'))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        return root

    def test_the_two_known_stale_digests_are_the_documented_ones(self):
        self.assertEqual(pack.STALE_FLOWER_SHA256, {
            self.HI: '80e84edb3aaaa2674c566a098465201816dc8a94fefe220c7b2c6dd63461a8af',
            self.LOW: 'ad6aede6be0e1090968308d0ed32d6ef1fa473cb66b0ea13c9ba1ed07b1f43ec',
        })

    def test_fresh_atlases_pass_and_are_manifested(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.build_package(tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                pack.flower_manifest(str(root), '0.6.0.6')
            manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['asset_version'], '0.6.0.6')
            self.assertEqual([f['path'] for f in manifest['files']], [self.HI, self.LOW])
            self.assertNotIn(manifest['files'][0]['sha256'], pack.STALE_FLOWER_SHA256.values())

    def check_refusal(self, stale_hi, stale_low):
        """Either stale atlas alone must stop the pack, and say why."""
        with tempfile.TemporaryDirectory() as tmp:
            hi = b'the-stale-hi-atlas'
            low = b'the-stale-low-atlas'
            root = self.build_package(tmp, hi=hi, low=low)
            digests = dict(pack.STALE_FLOWER_SHA256)
            if stale_hi:
                digests[self.HI] = hashlib.sha256(hi).hexdigest()
            if stale_low:
                digests[self.LOW] = hashlib.sha256(low).hexdigest()
            err, out = io.StringIO(), io.StringIO()
            with patch.object(pack, 'STALE_FLOWER_SHA256', digests),                     contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
                with self.assertRaises(SystemExit) as raised:
                    pack.flower_manifest(str(root), '0.6.0.6')
            self.assertEqual(raised.exception.code, 1)
            message = err.getvalue()
            self.assertIn('KNOWN-STALE', message)
            self.assertIn('#1181', message)
            self.assertIn('2.7.1.0', message)
            self.assertIn('build_ap_icon.py', message)
            self.assertIn(self.HI if stale_hi else self.LOW, message)
            # It refuses BEFORE writing, so a stale package never leaves a manifest behind.
            self.assertFalse((root / 'manifest.json').exists())

    def test_stale_hi_atlas_is_refused(self):
        self.check_refusal(stale_hi=True, stale_low=False)

    def test_stale_low_atlas_is_refused(self):
        self.check_refusal(stale_hi=False, stale_low=True)

    def test_both_stale_atlases_are_refused(self):
        self.check_refusal(stale_hi=True, stale_low=True)


if __name__ == '__main__':
    unittest.main()
