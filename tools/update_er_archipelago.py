#!/usr/bin/env python3
"""Update this Elden Ring Archipelago client install in place -- phase 2 of the updater.

Phase 1 (the in-game banner) tells you WHEN an update exists and WHETHER it is safe mid-seed;
this tool is what you run, between sessions, when the banner says so. It is deliberately never
automatic: a mid-seed player silently updated across a contract change is the one failure this
design must be incapable of, so the banner decides and the human runs.

WHAT IT DOES, in order, each step loud:
  1. locates the install as its own folder (it ships inside `me3/`, beside the dll);
  2. refuses while `eldenring.exe` is running (the dll is loaded; files are locked);
  3. reads https://peliarch.ca/er/latest.json -- the same file the banner reads, so the two can
     never disagree about what "latest" means;
  4. CONTRACT GATE: scans the installed dll for the latest contract hash. Found = same contract,
     drop-in even mid-seed. Not found = the contract MOVED (or the dll predates the stamp) --
     the tool stops and demands `--accept-contract-change`, and says what that means for a
     running seed. (The in-game banner is the authoritative verdict; this gate is the last
     chance to read it.)
  5. resolves the release bundle via the GitHub API (the one asset matching
     ER-Archipelago-*.zip on the tag), downloads it with an exact size check, and verifies the
     zip's own integrity table;
  6. swaps in the NEW bundle's `me3/` payload file-by-file: every replaced file is backed up
     first (into `.er-updater-backup-<timestamp>/`), and NOTHING outside the payload is touched
     -- `apconfig.json`, `ap_save_*.json`, `log/`, `reconcile.json` and anything else you or
     the client wrote stay exactly where they are;
  7. stamps `.er-updater-version` so the next run can say "already current" without a 120 MB
     download, and reminds matt's-launcher users to re-run `install-into-matts-rando`.

EXIT CODES -- 0 updated, 2 already current, 1 refused or failed. ASCII output only.

What it deliberately does NOT do: update the APWORLD (that is the room host's file, not this
install's), touch matt's randomizer folder, or delete anything (obsolete payload files from an
older release are left in place -- inert, and deleting on a guess is how updaters eat saves).
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

LATEST_URL = "https://peliarch.ca/er/latest.json"
API_RELEASE = "https://api.github.com/repos/4laric/er-archipelago/releases/tags/{tag}"
DLL_NAME = "eldenring_archipelago.dll"
EXE_NAME = "eldenring.exe"
STAMP = ".er-updater-version"
ASSET_RX = re.compile(r"^ER-Archipelago-.*\.zip$")


class UpdateError(RuntimeError):
    pass


def http_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "er-archipelago-updater",
                                               "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def install_dir(script_path: Path) -> Path:
    root = script_path.resolve().parent
    if not (root / DLL_NAME).is_file():
        raise UpdateError(
            "this tool must run from inside the install's me3/ folder, beside %s" % DLL_NAME
        )
    return root


def game_is_running() -> bool:
    """Best-effort, Windows only: the game holds our dll and tables locked."""
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq %s" % EXE_NAME],
                             capture_output=True, text=True, timeout=10, check=False).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return EXE_NAME.lower() in out.lower()


def parse_latest(body: str) -> dict:
    """Mirror of the client's parse: version/contract/url or refuse."""
    d = json.loads(body)
    for k in ("version", "contract", "url"):
        if not isinstance(d.get(k), str) or not d[k]:
            raise UpdateError("latest.json is missing %r -- refusing to act on it" % k)
    if len(d["contract"]) < 8 or not all(c in "0123456789abcdefABCDEF" for c in d["contract"][:8]):
        raise UpdateError("latest.json contract does not look like a hash prefix")
    return d


def dll_contains_contract(dll_bytes: bytes, contract8: str) -> bool:
    """The contract gate's membership test. The dll embeds its full 64-hex CONTRACT_HASH as an
    ASCII literal (measured on the shipped v0.3.1 dll: the handshake rodata carries it), so a
    build whose contract matches `latest` CONTAINS this prefix. Absence therefore means either
    the contract moved or the build predates the literal -- both are 'stop and ask'."""
    return contract8.lower().encode("ascii") in dll_bytes.lower()


def pick_asset(release: dict) -> tuple[str, int, str]:
    """(download_url, size, name) of the one bundle asset on the tag."""
    hits = [a for a in release.get("assets", []) if ASSET_RX.match(a.get("name", ""))]
    if len(hits) != 1:
        raise UpdateError(
            "expected exactly one ER-Archipelago-*.zip asset on the release, found %d"
            % len(hits)
        )
    a = hits[0]
    if not isinstance(a.get("size"), int) or a["size"] <= 0:
        raise UpdateError("the release asset has no usable size to verify against")
    return a["browser_download_url"], a["size"], a["name"]


def download(url: str, size: int, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "er-archipelago-updater"})
    done = 0
    with urllib.request.urlopen(req, timeout=60) as r, dest.open("wb") as f:
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            print("\r  downloading: %d / %d MB" % (done // 1048576, size // 1048576),
                  end="", flush=True)
    print()
    actual = dest.stat().st_size
    if actual != size:
        raise UpdateError("download size mismatch: got %d, the release says %d -- refusing a "
                          "truncated bundle" % (actual, size))


def payload_files(extracted_me3: Path) -> list[Path]:
    return sorted(p for p in extracted_me3.rglob("*") if p.is_file())


def swap_in(install: Path, new_me3: Path, stamp_version: str) -> tuple[int, int, list[str]]:
    """Replace the payload, back up what it replaces, touch nothing else.
    Returns (replaced, added, backed_up_names)."""
    files = payload_files(new_me3)
    # The bundle-intact rule, enforced BEFORE any write: a payload missing the dll or either
    # data table must never be half-installed.
    names = {p.relative_to(new_me3).as_posix() for p in files}
    for required in (DLL_NAME, "check_lots_table.json", "shoplineup_flags.json"):
        if required not in names:
            raise UpdateError("the downloaded bundle's me3/ is missing %s -- refusing" % required)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = install / (".er-updater-backup-" + stamp)
    replaced = added = 0
    backed: list[str] = []
    for src in files:
        rel = src.relative_to(new_me3)
        dst = install / rel
        if dst.exists():
            bak = backup_root / rel
            bak.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dst, bak)
            backed.append(rel.as_posix())
            replaced += 1
        else:
            added += 1
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    (install / STAMP).write_text(stamp_version + "\n", encoding="ascii")
    return replaced, added, backed


def run(argv: list[str] | None = None, script_path: Path | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--accept-contract-change", action="store_true",
                   help="proceed even though the new release's contract differs from this "
                        "install's (breaks pairing with any seed generated for the old pair)")
    p.add_argument("--latest-url", default=LATEST_URL, help=argparse.SUPPRESS)
    args = p.parse_args(argv)

    install = install_dir(script_path or Path(__file__))
    if game_is_running():
        raise UpdateError("%s is running -- close the game first; it holds these files" % EXE_NAME)

    with urllib.request.urlopen(
        urllib.request.Request(args.latest_url,
                               headers={"User-Agent": "er-archipelago-updater"}),
        timeout=30,
    ) as r:
        latest = parse_latest(r.read().decode("utf-8"))
    print("latest stable: v%s (contract %s)" % (latest["version"], latest["contract"]))

    stamp_file = install / STAMP
    if stamp_file.is_file() and stamp_file.read_text(encoding="ascii").strip() == latest["version"]:
        print("Already current: this install was updated to v%s by this tool." % latest["version"])
        return 2

    dll_bytes = (install / DLL_NAME).read_bytes()
    if dll_contains_contract(dll_bytes, latest["contract"][:8]):
        print("contract check: SAME contract -- this update is a drop-in, safe even mid-seed.")
    elif args.accept_contract_change:
        print("contract check: the contract MOVED (or this dll predates the stamp). Proceeding "
              "because --accept-contract-change was given. Seeds generated for your old pair "
              "will not run on the new client.")
    else:
        raise UpdateError(
            "the new release's contract (%s) was not found in your installed dll. That means "
            "the contract MOVED: updating now breaks the pairing with any seed you are mid-way "
            "through. Finish the seed first, or re-run with --accept-contract-change."
            % latest["contract"][:8]
        )

    tag = "v" + latest["version"]
    release = http_json(API_RELEASE.format(tag=tag))
    url, size, name = pick_asset(release)
    print("release asset: %s (%d MB)" % (name, size // 1048576))

    with tempfile.TemporaryDirectory(prefix="er-updater-") as tmp:
        tmpdir = Path(tmp)
        bundle = tmpdir / name
        download(url, size, bundle)
        with zipfile.ZipFile(bundle) as z:
            bad = z.testzip()
            if bad is not None:
                raise UpdateError("the downloaded zip failed its own integrity table at %s" % bad)
            members = [m for m in z.namelist() if m.startswith("me3/") and not m.endswith("/")]
            if not members:
                raise UpdateError("the bundle has no me3/ payload -- wrong asset?")
            z.extractall(tmpdir, members)
        replaced, added, backed = swap_in(install, tmpdir / "me3", latest["version"])

    print("Updated to v%s: %d file(s) replaced (backed up), %d added." %
          (latest["version"], replaced, added))
    if "ap.me3" in backed:
        print("NOTE: ap.me3 was replaced; your previous copy is in the backup folder if you "
              "had edited it (savefile line etc).")
    print("Nothing of yours was touched: apconfig.json, saves, logs and ledgers stay in place.")
    print("Launching through matt's randomizer? Re-run install-into-matts-rando so its dll "
          "pointer follows this folder (a no-op if you point at this folder already).")
    return 0


def main() -> int:
    try:
        return run()
    except UpdateError as exc:
        print("REFUSED: %s" % exc, file=sys.stderr)
        return 1
    except Exception as exc:  # network, zip, filesystem -- name it rather than traceback at a player
        print("FAILED: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
