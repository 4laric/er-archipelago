import hashlib, importlib.util, json, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("install_ap_flower", HERE / "install_ap_flower.py")
flower = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(flower)

def make_package(root: Path, version="1", corrupt=False):
    package = root / "flower-package"; rows = []
    for i, relative in enumerate(flower.EXPECTED):
        data = (b"high" if i == 0 else b"low") + version.encode()
        path = package / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        rows.append({"path": str(relative), "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    (package / "manifest.json").write_text(json.dumps({"schema": 1, "asset_version": version, "files": rows}), encoding="utf-8")
    if corrupt: (package / flower.EXPECTED[1]).write_bytes(b"bad")
    return package

class DestinationTests(unittest.TestCase):
    def test_nested_matt_layout_resolves_to_randomizer_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/"randomizer"; dll = root/"archipelago/dll"; dll.mkdir(parents=True)
            (root/"seed.randomizeopt").write_text("")
            self.assertEqual(flower.resolve_destination([dll])[0], root.resolve())

    def test_strong_nearby_matt_fingerprint_beats_outer_weak_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            outer = Path(tmp); (outer/"regulation.bin").write_bytes(b"")
            root = outer/"randomizer"; dll = root/"archipelago/dll"; dll.mkdir(parents=True)
            (root/"seed.randomizeopt").write_text("")
            self.assertEqual(flower.resolve_destination([dll])[0], root.resolve())

    def test_explicit_destination_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, explicit = Path(tmp)/"matt", Path(tmp)/"chosen"; root.mkdir(); (root/"x.randomizeopt").write_text("")
            self.assertEqual(flower.resolve_destination([root], explicit)[0], explicit.resolve())

    def test_equal_candidates_refuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/"a", Path(tmp)/"b"; a.mkdir(); b.mkdir()
            (a/"a.randomizeopt").write_text(""); (b/"b.randomizeopt").write_text("")
            with self.assertRaisesRegex(flower.InstallError, "ambiguous"): flower.resolve_destination([a, b])

    def test_no_candidate_refuses_instead_of_using_ap_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(flower.InstallError, "--destination"):
                flower.resolve_destination([Path(tmp)])

    def test_prompt_rejects_a_folder_without_matt_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            from unittest.mock import patch
            with patch.object(flower.sys.stdin, "isatty", return_value=True), \
                 patch("builtins.input", return_value=tmp):
                with self.assertRaisesRegex(flower.InstallError, "does not look like"):
                    flower.prompt_destination()

class InstallTests(unittest.TestCase):
    def test_missing_or_corrupt_package_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); package = make_package(root, corrupt=True); destination = root/"dest"
            with self.assertRaises(flower.InstallError): flower.install(package, destination)
            self.assertFalse(destination.exists())

    def test_install_repeat_update_and_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); destination = root/"dest"
            self.assertIn("restart", flower.install(make_package(root, "1"), destination))
            self.assertEqual(flower.install(make_package(root, "1"), destination), "already installed")
            (destination/flower.EXPECTED[0]).unlink()
            self.assertIn("restart", flower.install(make_package(root, "2"), destination))
            for p in flower.EXPECTED: self.assertTrue((destination/p).is_file())

    def test_unowned_conflict_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); package = make_package(root); target = root/"dest"/flower.EXPECTED[0]
            target.parent.mkdir(parents=True); target.write_bytes(b"other")
            with self.assertRaisesRegex(flower.InstallError, "conflict"): flower.install(package, root/"dest")
            self.assertEqual(target.read_bytes(), b"other")

    def test_replace_backs_up_and_uninstall_restores(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); package = make_package(root); destination = root/"dest"; target = destination/flower.EXPECTED[0]
            target.parent.mkdir(parents=True); target.write_bytes(b"other")
            flower.install(package, destination, True); flower.uninstall(destination)
            self.assertEqual(target.read_bytes(), b"other")

    def test_uninstall_retains_user_modified_owned_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); destination = root/"dest"; flower.install(make_package(root), destination)
            target = destination/flower.EXPECTED[0]; target.write_bytes(b"modified")
            self.assertTrue(any("retained" in x for x in flower.uninstall(destination)))
            self.assertEqual(target.read_bytes(), b"modified")

    def test_failed_pair_commit_rolls_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); destination = root/"dest"; flower.install(make_package(root, "1"), destination)
            before = [(destination/p).read_bytes() for p in flower.EXPECTED]
            with self.assertRaisesRegex(flower.InstallError, "simulated"):
                flower.install(make_package(root, "2"), destination, fail_after=1)
            self.assertEqual([(destination/p).read_bytes() for p in flower.EXPECTED], before)

class EntrypointTests(unittest.TestCase):
    def _round_trip(self, command: list[str]) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); package = make_package(root); destination = root/"matt-output"
            installed = subprocess.run(
                command + ["--package", str(package), "--destination", str(destination)],
                check=True, capture_output=True, text=True,
            )
            self.assertIn("restart Elden Ring", installed.stdout)
            for relative in flower.EXPECTED:
                self.assertEqual((destination/relative).read_bytes(), (package/relative).read_bytes())
            removed = subprocess.run(
                command + ["--destination", str(destination), "--uninstall"],
                check=True, capture_output=True, text=True,
            )
            self.assertIn("uninstalled", removed.stdout)
            self.assertFalse((destination/flower.MARKER).exists())
            for relative in flower.EXPECTED:
                self.assertFalse((destination/relative).exists())

    def test_python_cli_install_and_uninstall(self):
        self._round_trip([sys.executable, str(HERE/"install_ap_flower.py")])

    def test_powershell_launcher_install_and_uninstall(self):
        shell = shutil.which("pwsh") or shutil.which("powershell")
        if shell is None:
            self.skipTest("PowerShell is not installed")
        self._round_trip([shell, "-NoProfile", "-File", str(HERE/"install_ap_flower.ps1")])

if __name__ == "__main__": unittest.main()
