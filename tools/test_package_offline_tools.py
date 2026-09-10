"""Release archive integrity and actual Bash deployment of old/new release assets."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from tools.package_offline_tools import ARCHIVE_NAME, PAGES, package
from tools.update_er_archipelago import pick_asset

ROOT = Path(__file__).resolve().parents[1]
BASH = (r"C:\Program Files\Git\bin\bash.exe" if os.name == "nt" else shutil.which("bash"))


class OfflineToolsTests(unittest.TestCase):
    def test_complete_deterministic_archive_and_missing_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for page in PAGES:
                (directory / page).write_text('<html>sentinel</html>')
            output = package(directory)
            before = output.read_bytes()
            self.assertEqual(package(directory).read_bytes(), before)
            with ZipFile(output) as archive:
                self.assertEqual(set(archive.namelist()), {*PAGES, 'README.txt'})
                self.assertIsNone(archive.testzip())
                self.assertIn(b'does not contain eldenring_archipelago.dll', archive.read('README.txt'))
            (directory / PAGES[0]).unlink()
            with self.assertRaises(FileNotFoundError):
                package(directory)
            self.assertEqual(output.read_bytes(), before)
            (directory / PAGES[0]).write_text(' ')
            with self.assertRaises(ValueError):
                package(directory)
            self.assertEqual(output.read_bytes(), before)

    def test_existing_updater_still_selects_only_client(self):
        assets = [{'name': name, 'size': 123, 'browser_download_url': name}
                  for name in [ARCHIVE_NAME, 'ER-Archipelago-v0.6.0.7-20260910.zip']]
        self.assertEqual(pick_asset({'assets': assets})[2], assets[1]['name'])

    @unittest.skipUnless(BASH, 'Bash required for deployment regression')
    def test_deploy_old_new_and_failed_downloads(self):
        script = (ROOT / 'tools/deploy_wizard.sh').read_text()
        functions = script[script.index('src_url() {'):script.index('\n[ "$DRY" = "1" ] || [ -d "$DEST" ]')]
        for mode in ['old', 'zip', 'absent', 'broken', 'missing', 'sentinel', 'network', 'zipnetwork']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp)
                for page in PAGES:
                    (directory / page).write_text('<html>sentinel</html>')
                archive = package(directory)
                if mode == 'broken':
                    archive.write_bytes(b'bad zip')
                elif mode == 'missing':
                    with ZipFile(archive, 'w') as z:
                        z.writestr('other.html', 'sentinel')
                elif mode == 'sentinel':
                    with ZipFile(archive, 'w') as z:
                        z.writestr(PAGES[1], '<html>login</html>')
                (directory / 'output.html').write_text('original')
                harness = r'''set -euo pipefail
RELEASES=release RAW=raw PAGES_SITE=pages DRY=0 beta_ref=main
CURRENT_TMP="" OFFLINE_ZIP="" OFFLINE_REF="" OFFLINE_HTTP="" SKIPPED_ARTIFACTS=0
trap 'rm -f "$CURRENT_TMP" "$OFFLINE_ZIP"' EXIT
say() { printf '%s\n' "$*"; }
die() { echo "$*" >&2; exit 1; }
curl() {
  local out="$5" url="$6"
  case "$url" in
    *.zip)
      echo zip >> requests
      case "$MODE" in
        absent) printf 404 ;;
        zipnetwork) printf 503 ;;
        *) cp Optional-Offline-Tools.zip "$out"; printf 200 ;;
      esac ;;
    *)
      case "$MODE" in
        old) printf '<html>sentinel</html>' > "$out"; printf 200 ;;
        network) printf 503 ;;
        *) printf 404 ;;
      esac ;;
  esac
}
'''
                harness += functions + '\n'
                harness += 'install_one v1 er-archipelago-check-browser.html output.html sentinel check\n'
                harness += 'install_one v1 er-archipelago-evidence-browser.html evidence.html sentinel evidence\n'
                (directory / 'harness.sh').write_text(harness, newline='\n')
                result = subprocess.run([BASH, 'harness.sh'], cwd=directory,
                                        env={**os.environ, 'MODE': mode}, capture_output=True, text=True)
                success = mode in ['old', 'zip', 'absent']
                self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
                expected = '<html>sentinel</html>' if mode in ['old', 'zip'] else 'original'
                self.assertEqual((directory / 'output.html').read_text(), expected)
                requests = directory / 'requests'
                self.assertEqual(requests.read_text().splitlines() if requests.exists() else [],
                                 [] if mode in ['old', 'network'] else ['zip'])
                self.assertEqual(list(directory.glob('*.tmp')), [])


if __name__ == '__main__':
    unittest.main()
