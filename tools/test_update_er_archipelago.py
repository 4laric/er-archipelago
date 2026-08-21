import importlib.util, io, json, tempfile, unittest, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("update_er_archipelago",
                                              HERE / "update_er_archipelago.py")
upd = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(upd)

LATEST = '{"version": "0.4.10", "contract": "dc0dc687", "url": "x"}'


class ParseTests(unittest.TestCase):
    def test_the_live_emission_parses(self):
        # MOTIVATING CASE: the exact shape deploy_wizard.sh emitted 2026-08-21.
        d = upd.parse_latest(LATEST)
        self.assertEqual((d["version"], d["contract"]), ("0.4.10", "dc0dc687"))

    def test_garbage_refuses(self):
        for bad in ('{"version": "0.4.10"}', '{"version": "", "contract": "x", "url": "x"}',
                    '{"version": "1", "contract": "nothex!!", "url": "x"}'):
            with self.assertRaises(Exception, msg=bad):
                upd.parse_latest(bad)


class ContractGateTests(unittest.TestCase):
    def test_a_dll_carrying_the_hash_is_same_contract(self):
        # The dll embeds its full 64-hex CONTRACT_HASH as ASCII (the v0.3.1 dll measurement);
        # the gate is a membership test over the 8-char prefix, case-insensitive.
        dll = b"\x00rodata\x00" + b"dc0dc687f38de1a6c48d90950375de26" + b"\x00"
        self.assertTrue(upd.dll_contains_contract(dll, "dc0dc687"))
        self.assertTrue(upd.dll_contains_contract(dll.upper(), "dc0dc687"))

    def test_a_moved_contract_is_absent(self):
        self.assertFalse(upd.dll_contains_contract(b"contract/5c2b9bf2 elsewhere", "dc0dc687"))


class AssetTests(unittest.TestCase):
    def test_exactly_one_bundle_asset_is_chosen(self):
        rel = {"assets": [
            {"name": "eldenring.apworld", "size": 9, "browser_download_url": "a"},
            {"name": "ER-Archipelago-v0.4.10.zip", "size": 125000000,
             "browser_download_url": "https://example/bundle.zip"},
            {"name": "er-options-wizard.html", "size": 9, "browser_download_url": "w"},
        ]}
        url, size, name = upd.pick_asset(rel)
        self.assertEqual(name, "ER-Archipelago-v0.4.10.zip")
        self.assertEqual(size, 125000000)

    def test_zero_or_two_bundles_refuse(self):
        with self.assertRaises(upd.UpdateError):
            upd.pick_asset({"assets": []})
        two = {"assets": [
            {"name": "ER-Archipelago-a.zip", "size": 1, "browser_download_url": "a"},
            {"name": "ER-Archipelago-b.zip", "size": 1, "browser_download_url": "b"},
        ]}
        with self.assertRaises(upd.UpdateError):
            upd.pick_asset(two)


class SwapTests(unittest.TestCase):
    """The half that must never eat user state."""

    def _fixture(self, tmp: Path):
        install = tmp / "me3"; install.mkdir()
        # existing payload (old versions) + USER STATE that must survive untouched
        (install / upd.DLL_NAME).write_bytes(b"old dll")
        (install / "check_lots_table.json").write_text("old")
        (install / "shoplineup_flags.json").write_text("old")
        (install / "apconfig.json").write_text('{"slot": "4laric"}')
        (install / "ap_save_123_bob.json").write_text("save")
        (install / "log").mkdir(); (install / "log" / "a.log").write_text("x")
        new = tmp / "new_me3"; new.mkdir()
        (new / upd.DLL_NAME).write_bytes(b"new dll")
        (new / "check_lots_table.json").write_text("new")
        (new / "shoplineup_flags.json").write_text("new")
        (new / "ap.me3").write_text("profile")  # a file the old install lacked
        return install, new

    def test_payload_replaced_user_state_untouched_backup_written(self):
        with tempfile.TemporaryDirectory() as t:
            install, new = self._fixture(Path(t))
            replaced, added, backed = upd.swap_in(install, new, "0.4.10")
            self.assertEqual((replaced, added), (3, 1))
            self.assertEqual((install / upd.DLL_NAME).read_bytes(), b"new dll")
            # WITNESS the user-state promise, file by file:
            self.assertEqual((install / "apconfig.json").read_text(), '{"slot": "4laric"}')
            self.assertEqual((install / "ap_save_123_bob.json").read_text(), "save")
            self.assertEqual((install / "log" / "a.log").read_text(), "x")
            # the backup holds the OLD payload bytes
            bdir = next(install.glob(".er-updater-backup-*"))
            self.assertEqual((bdir / upd.DLL_NAME).read_bytes(), b"old dll")
            self.assertIn(upd.DLL_NAME, backed)
            # and the stamp names the version for the already-current fast path
            self.assertEqual((install / upd.STAMP).read_text().strip(), "0.4.10")

    def test_a_bundle_missing_a_table_refuses_before_any_write(self):
        with tempfile.TemporaryDirectory() as t:
            install, new = self._fixture(Path(t))
            (new / "check_lots_table.json").unlink()
            with self.assertRaises(upd.UpdateError):
                upd.swap_in(install, new, "0.4.10")
            self.assertEqual((install / upd.DLL_NAME).read_bytes(), b"old dll",
                             "a refused swap must leave the install untouched")
            self.assertEqual(list(install.glob(".er-updater-backup-*")), [])


class InstallDirTests(unittest.TestCase):
    def test_refuses_outside_an_install(self):
        with tempfile.TemporaryDirectory() as t:
            script = Path(t) / "update_er_archipelago.py"; script.write_text("#")
            with self.assertRaises(upd.UpdateError):
                upd.install_dir(script)


if __name__ == "__main__":
    unittest.main()
