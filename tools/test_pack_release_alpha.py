"""Stable and prerelease bundles keep strict paired MFG and version identity gates."""
import contextlib
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


if __name__ == '__main__':
    unittest.main()
