import importlib.util, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("install_into_matts_rando",
                                              HERE / "install_into_matts_rando.py")
matts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(matts)

# The REAL persisted shape, verbatim from a live v0.11.4 install (paths anonymized). The app
# writes single-line inline tables with double-backslash paths; the mutation must hand back
# exactly this style or the app's next read is a gamble.
LIVE = (
    'modengine = { debug = false, external_dlls = [ '
    '"C:\\\\old\\\\v0.3.12\\\\me3\\\\eldenring_archipelago.dll", '
    '"C:\\\\rando\\\\dll\\\\RandomizerCrashFix.dll" ] }\n'
    'extension = { mod_loader = { enabled = true, loose_params = false, mods = [ '
    '{ enabled = true, name = "randomizer", path = "C:\\\\rando" } ] } }\n'
)
NEW_DLL = "C:\\new\\ER-Archipelago\\me3\\eldenring_archipelago.dll"


class MutationTests(unittest.TestCase):
    def test_replaces_a_stale_path_by_basename(self):
        # THE UPGRADE PATH: the frozen-pointer disease (a launcher measured loading a
        # v0.3.12 client months later) dies exactly here.
        out, action = matts.mutate_dll_toml(LIVE, NEW_DLL)
        self.assertEqual(action, "replaced")
        self.assertIn("ER-Archipelago\\\\me3\\\\eldenring_archipelago.dll", out)
        self.assertNotIn("v0.3.12", out)

    def test_preserves_every_other_entry_and_the_structure(self):
        out, _ = matts.mutate_dll_toml(LIVE, NEW_DLL)
        self.assertEqual(out.count("RandomizerCrashFix.dll"), 1)
        self.assertEqual(out.count("eldenring_archipelago.dll"), 1)
        self.assertEqual(out.count("{"), LIVE.count("{"), "inline-table structure moved")
        self.assertIn('extension = { mod_loader', out, "the untouched line survives verbatim")

    def test_appends_when_absent(self):
        bare = LIVE.replace(
            '"C:\\\\old\\\\v0.3.12\\\\me3\\\\eldenring_archipelago.dll", ', "")
        out, action = matts.mutate_dll_toml(bare, NEW_DLL)
        self.assertEqual(action, "appended")
        self.assertEqual(out.count("eldenring_archipelago.dll"), 1)
        self.assertEqual(out.count("RandomizerCrashFix.dll"), 1)

    def test_appends_into_an_empty_array(self):
        empty = 'modengine = { debug = false, external_dlls = [\n\n] }\n'
        out, action = matts.mutate_dll_toml(empty, NEW_DLL)
        self.assertEqual(action, "appended")
        self.assertIn("eldenring_archipelago.dll", out)

    def test_idempotent_second_run_is_current(self):
        once, _ = matts.mutate_dll_toml(LIVE, NEW_DLL)
        twice, action = matts.mutate_dll_toml(once, NEW_DLL)
        self.assertEqual(action, "current")
        self.assertEqual(twice, once, "a no-op must be byte-identical")

    def test_no_array_appends_our_own_modengine_line(self):
        # The old behaviour refused with "open 'Add dll mod' once, close it (the app writes the
        # file)" -- an instruction MEASURED FALSE on a fresh install (2026-08-21): the app writes
        # nothing on open+close. We own the line now.
        out, action = matts.mutate_dll_toml("someother = { x = 1 }\n", NEW_DLL)
        self.assertEqual(action, "appended")
        self.assertIn("modengine = { debug = false, external_dlls = [", out)
        self.assertEqual(out.count("eldenring_archipelago.dll"), 1)
        self.assertTrue(out.startswith("someother = { x = 1 }\n"), "existing content untouched")

    def test_created_toml_matches_the_apps_measured_style_and_rereads_current(self):
        text = matts.created_dll_toml(NEW_DLL)
        self.assertTrue(text.startswith("modengine = { debug = false, external_dlls = [ "))
        self.assertTrue(text.rstrip().endswith("] }"))
        self.assertIn("ER-Archipelago\\\\me3\\\\eldenring_archipelago.dll", text)
        # and the mutator recognises its own creation as current on a re-run
        _, action = matts.mutate_dll_toml(text, NEW_DLL)
        self.assertEqual(action, "current")


class _Fixture:
    """A fake bundle + fake randomizer folder for end-to-end runs."""

    def __init__(self, tmp: Path, with_toml=True, toml_text=LIVE):
        self.me3 = tmp / "me3"
        self.me3.mkdir()
        for name in matts.BUNDLE:
            (self.me3 / name).write_bytes(b"x")
        self.script = self.me3 / "install_into_matts_rando.py"
        self.script.write_bytes(b"# stand-in; run() receives script_path explicitly\n")
        self.rando = tmp / "rando"
        self.rando.mkdir()
        (self.rando / matts.EXE_NAME).write_bytes(b"x")
        if with_toml:
            (self.rando / matts.TOML_NAME).write_text(toml_text, encoding="utf-8")


class EndToEndTests(unittest.TestCase):
    def _run(self, fx):
        return matts.run(["--randomizer", str(fx.rando)], script_path=fx.script)

    def test_changed_then_current_and_a_backup_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = _Fixture(Path(tmp))
            self.assertEqual(self._run(fx), 0)
            backups = list(fx.rando.glob(matts.TOML_NAME + ".bak-*"))
            self.assertEqual(len(backups), 1, "backup before any change")
            self.assertIn("me3", (fx.rando / matts.TOML_NAME).read_text())
            self.assertEqual(self._run(fx), 2, "second run is the idempotent no-op")
            self.assertEqual(len(list(fx.rando.glob(matts.TOML_NAME + ".bak-*"))), 1,
                             "a no-op writes no second backup")

    def test_missing_exe_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = _Fixture(Path(tmp))
            (fx.rando / matts.EXE_NAME).unlink()
            with self.assertRaises(matts.InstallError):
                self._run(fx)

    def test_missing_toml_is_created_and_the_run_succeeds(self):
        # THE MOTIVATING CASE (v0.4.11 acceptance): fresh matt install, no toml anywhere, and the
        # old refusal's dialog instruction produces no file. One command must mean one command.
        with tempfile.TemporaryDirectory() as tmp:
            fx = _Fixture(Path(tmp), with_toml=False)
            self.assertEqual(self._run(fx), 0)
            text = (fx.rando / matts.TOML_NAME).read_text()
            self.assertIn("eldenring_archipelago.dll", text)
            self.assertIn("modengine = { debug = false, external_dlls = [", text)
            self.assertEqual(self._run(fx), 2, "second run reads its own creation as current")

    def test_toml_one_level_up_refuses_and_names_the_real_folder(self):
        # The other reading of "does not exist": --randomizer pointed one level too deep. Never
        # create a second toml next door to a real one -- refuse, and say where the real one is.
        with tempfile.TemporaryDirectory() as tmp:
            fx = _Fixture(Path(tmp), with_toml=False)
            (fx.rando.parent / matts.TOML_NAME).write_text(LIVE, encoding="utf-8")
            with self.assertRaises(matts.InstallError) as ctx:
                self._run(fx)
            self.assertIn(str(fx.rando.parent), str(ctx.exception))
            self.assertFalse((fx.rando / matts.TOML_NAME).exists(), "nothing created next door")

    def test_incomplete_bundle_refuses_naming_the_missing_table(self):
        # The double-pay footgun becomes an install-time refusal: a dll without its tables
        # must never be wired into anyone's launcher.
        with tempfile.TemporaryDirectory() as tmp:
            fx = _Fixture(Path(tmp))
            (fx.me3 / "check_lots_table.json").unlink()
            with self.assertRaises(matts.InstallError) as ctx:
                self._run(fx)
            self.assertIn("check_lots_table.json", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
