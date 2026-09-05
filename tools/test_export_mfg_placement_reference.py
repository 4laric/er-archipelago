import hashlib
from pathlib import Path
import tempfile
import unittest
from export_mfg_placement_reference import parse_generated, verify_manifest

SAMPLE = '''const size_t MAP_ENTRY_COUNT = 1;
{123ull, {.areaNo = 60, .gridXNo = 42, .gridZNo = 37,
.posX = 9.0f, .posY = -2.0f, .posZ = 8.0f,
.textDisableFlagId1 = 1234,}, Category::LootConsumables, -1, -1,
nullptr, 456u, 1, 1.25f, 3.5f},'''

class ExportTests(unittest.TestCase):
    def test_real_not_display_coordinates(self):
        row = parse_generated(SAMPLE)[0]
        self.assertEqual((row['x'], row['y'], row['z']), (1.25, -2, 3.5))
        self.assertEqual(row['map'], 'm60_42_37')
        self.assertEqual(row['lotSource'], 'map')
        self.assertNotIn('eventFlag', row)
    def test_roundtable_display_shift_is_undone(self):
        text = SAMPLE.replace('.areaNo = 60', '.areaNo = 11').replace('.gridXNo = 42', '.gridXNo = 10')
        row = parse_generated(text)[0]
        self.assertEqual(row['generated_xyz'], [1.25, -2, 3.5])
        self.assertEqual((row['x'], row['z']), (2196.25, 355.5))
        self.assertEqual(row['coordinate_transform'], 'inverse_roundtable_display_shift')
    def test_missing_default_fields(self):
        row = parse_generated(SAMPLE.replace('.gridXNo = 42, .gridZNo = 37,', ''))[0]
        self.assertEqual(row['map'], 'm60_00_00')
    def test_format_drift_and_identity_rejected(self):
        for text in (SAMPLE.replace('COUNT = 1', 'COUNT = 2'),
                     SAMPLE.replace('456u, 1', '456u, 0'),
                     SAMPLE.replace('456u, 1', '456u, 3'),
                     SAMPLE.replace('Category::', 'Other::')):
            with self.assertRaises(ValueError):
                parse_generated(text)
    def test_manifest_hash_and_path_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'input').write_bytes(b'abc')
            manifest = {'profile':'vanilla', 'files':[{'path':'input', 'bytes':3,
                'sha256':hashlib.sha256(b'abc').hexdigest()}]}
            verify_manifest(root, manifest)
            (root / 'input').write_bytes(b'abd')
            with self.assertRaises(ValueError):
                verify_manifest(root, manifest)
            manifest['files'][0]['path'] = '../outside'
            with self.assertRaises(ValueError):
                verify_manifest(root, manifest)

if __name__ == '__main__':
    unittest.main()
