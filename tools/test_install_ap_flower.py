import importlib.util
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("install_ap_flower", HERE / "install_ap_flower.py")
flower = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(flower)


class DestinationDetection(unittest.TestCase):
    def test_standard_bundle_uses_ap_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            me3 = Path(tmp) / "me3"
            me3.mkdir()
            self.assertEqual(flower.detect_destination(me3, me3), me3 / "ap-package")

    def test_nearest_matt_output_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "randomizer"
            dll = root / "dll"
            dll.mkdir(parents=True)
            (root / "123.randomizeopt").write_text("", encoding="ascii")
            self.assertEqual(flower.detect_destination(dll, dll), root.resolve())

    def test_data_mod_root_is_detected_without_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "mod"
            nested = root / "nested" / "dll"
            nested.mkdir(parents=True)
            (root / "regulation.bin").write_bytes(b"")
            self.assertEqual(flower.detect_destination(nested, nested), root.resolve())


class InstallMarker(unittest.TestCase):
    def test_remove_only_deletes_recorded_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            owned = root / flower.OUTPUTS[0]
            other = root / "menu/keep.txt"
            owned.parent.mkdir(parents=True)
            owned.write_bytes(b"atlas")
            other.write_text("keep", encoding="ascii")
            (root / flower.MARKER).write_text(
                '{"files":["menu/hi/01_common.tpf.dcx"]}', encoding="utf-8"
            )
            self.assertTrue(flower.remove_installed(root))
            self.assertFalse(owned.exists())
            self.assertTrue(other.exists())


if __name__ == "__main__":
    unittest.main()
