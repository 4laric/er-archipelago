#!/usr/bin/env python3
"""Wire the Archipelago client into matt's randomizer launcher -- without moving a single file.

WHAT THIS EDITS (measured on a live v0.11.4 install, 2026-08-21; spec on issue #944):

WHEN THE TOML DOES NOT EXIST YET it is CREATED, carrying only the one line this tool owns
(`modengine = { debug = false, external_dlls = [ ... ] }`, the app's own measured single-line
style). v0.4.11 acceptance, 2026-08-21: the original refusal instructed "open 'Add dll mod'
once, close it (the app writes the file)" -- Alaric followed it on a fresh install and NO file
appeared, so that instruction was an unverified assumption doing the work of a feature. If
matt's app dislikes a file it did not write, delete the toml and report it; nothing else is
touched.
matt's launcher persists its "Add dll mod" list in `config_eldenringrandomizer_dll.toml`
beside `EldenRingRandomizer.exe` -- a small machine-written TOML. The adjacent
`config_eldenringrandomizer.toml` is hash-guarded and AUTO-GENERATED ("DO NOT MODIFY");
the app regenerates it and merges the dll list at launch. This script therefore writes ONLY
the `_dll.toml`, and performs exactly one mutation: ensure its `external_dlls` array names
OUR `eldenring_archipelago.dll` -- by absolute path, IN PLACE inside the release's `me3/`
folder, where its two data tables live beside it.

Replace-by-basename IS the upgrade path: re-running after a release repoints a stale
versioned-folder path in one command (the frozen-pointer failure this exists to kill --
a launcher was measured loading a v0.3.12 client months into v0.4.10 because the remembered
path still said v0.3.12).

WHAT THIS REFUSES, loudly (exit 1):
  * the bundle is incomplete (dll or either data table missing -- a dll without
    `check_lots_table.json` / `shoplineup_flags.json` beside it double-pays vanilla items
    and never fires shop checks, so that failure belongs at install time);
  * the target folder has no `EldenRingRandomizer.exe`;
  * `EldenRingRandomizer.exe` is running (the app holds the dll list in memory and can
    rewrite the file over our edit);
  * `config_eldenringrandomizer_dll.toml` exists NEARBY but not in the target folder
    (--randomizer points at the wrong level; the refusal names where it was found).

OPTIONAL TORRENT REPAIR (`--with-torrent-repair`): adds only Elden Ring 1.17's four missing
Spectral Steed RideParam rows to Matt's regulation.bin. It backs up regulation.bin, preserves
every existing binder entry and RideParam row byte-for-byte, verifies the encrypted candidate,
and replaces the target atomically. Soulstruct is required only for this opt-in mode.

Exit codes: 0 = changed, 2 = already current (idempotent no-op), 1 = refused.
All output is ASCII. Timestamped backups are written before either owned file changes.
"""
from __future__ import annotations
import argparse
import datetime
import re
import shutil
import subprocess
import sys
from pathlib import Path

DLL_NAME = "eldenring_archipelago.dll"
TOML_NAME = "config_eldenringrandomizer_dll.toml"
EXE_NAME = "EldenRingRandomizer.exe"
# The dll is inert without these beside it (double-pay / dead shop checks).
BUNDLE = (DLL_NAME, "check_lots_table.json", "shoplineup_flags.json")
HELPER_WARNING = (
    "WARNING: RandomizerHelper.dll is in your dll-mod list. Loading it alongside the\n"
    "Archipelago client is the single most common way to end up with a connected client\n"
    "that cannot give you anything. It was left in place (the list is yours), but if\n"
    "items stop arriving, remove it first."
)


class InstallError(RuntimeError):
    pass


def _toml_quote(path: str) -> str:
    return '"%s"' % path.replace("\\", "\\\\")


def _entry_basename(entry: str) -> str:
    inner = entry.strip().strip('"')
    inner = inner.replace("\\\\", "\\")
    return inner.replace("/", "\\").rsplit("\\", 1)[-1].lower()


def mutate_dll_toml(text: str, dll_path: str) -> tuple[str, str]:
    """The one mutation, pure. Returns (new_text, action) with action in
    {"replaced", "appended", "current"}. Preserves every other entry, the array's
    single-line emission style, and the surrounding structure byte-for-byte."""
    m = re.search(r"external_dlls\s*=\s*\[(.*?)\]", text, re.S)
    if not m:
        # A file with no external_dlls array at all: the app tolerates keys it did not write the
        # same way it tolerates a file it did not write (the creation path in run() proves the
        # latter), so append the one line this tool owns rather than teaching a dialog dance
        # that does not produce the array either (measured 2026-08-21).
        sep = "" if (not text or text.endswith("\n")) else "\n"
        return text + sep + created_dll_toml(dll_path), "appended"
    entries = [e.strip() for e in m.group(1).split(",") if e.strip()]
    new_entry = _toml_quote(dll_path)
    action = "appended"
    for i, entry in enumerate(entries):
        if _entry_basename(entry) == DLL_NAME:
            if entry == new_entry:
                return text, "current"
            entries[i] = new_entry
            action = "replaced"
            break
    else:
        entries.append(new_entry)
    body = " " + ", ".join(entries) + " " if entries else " "
    return text[: m.start(1)] + body + text[m.end(1):], action


def created_dll_toml(dll_path: str) -> str:
    """The file written when the app has not written one: ONLY the line this tool owns, in the
    app's own measured single-line inline-table style (double-backslash paths). No `extension`
    key -- that block belongs to the app's mod list, and inventing a path for it would be a
    guess wearing a config's clothes."""
    return "modengine = { debug = false, external_dlls = [ %s ] }\n" % _toml_quote(dll_path)


def find_toml_nearby(target: Path) -> Path | None:
    """The wrong--randomizer-level detector: the toml in the target's parent or one subfolder
    down. Returns the found path (for the refusal to name it), never acts on it -- installing
    into a folder the user did not point at is how installers earn distrust."""
    candidates = [target.parent / TOML_NAME]
    try:
        candidates += [d / TOML_NAME for d in sorted(target.iterdir()) if d.is_dir()]
    except OSError:
        pass
    for c in candidates:
        if c.is_file():
            return c
    return None


def bundle_dir(script_path: Path) -> Path:
    """The release me3/ folder = the directory this script ships in. Refuse unless the
    bundle is intact -- an incomplete bundle must not be wired into anyone's launcher."""
    root = script_path.resolve().parent
    missing = [n for n in BUNDLE if not (root / n).is_file() or (root / n).stat().st_size == 0]
    if missing:
        raise InstallError(
            "this script must run from inside the release's me3/ folder, next to the\n"
            "client dll and its data tables. Missing or empty here: %s" % ", ".join(missing)
        )
    return root


def randomizer_dir(path: Path) -> Path:
    root = path.resolve()
    if not (root / EXE_NAME).is_file():
        raise InstallError(
            "%s not found in %s -- point --randomizer at the folder that contains it."
            % (EXE_NAME, root)
        )
    return root


def app_is_running() -> bool:
    """Best-effort, Windows only: the app rewrites the dll toml from memory, so editing
    under it is a lost update waiting to happen. Elsewhere (tests, Proton shells without
    tasklist) this returns False rather than guessing."""
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq %s" % EXE_NAME],
            capture_output=True, text=True, timeout=10, check=False,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return EXE_NAME.lower() in out.lower()


def run(argv: list[str] | None = None, script_path: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--randomizer", required=True,
                        help="matt's randomizer folder (contains %s)" % EXE_NAME)
    parser.add_argument("--with-flower", action="store_true",
                        help="also run the AP Flower icon installer against the same folder")
    parser.add_argument("--with-torrent-repair", action="store_true",
                        help="add the four missing Elden Ring 1.17 RideParam rows to regulation.bin")
    args = parser.parse_args(argv)

    me3 = bundle_dir(script_path or Path(__file__))
    target = randomizer_dir(Path(args.randomizer))
    if app_is_running():
        raise InstallError(
            "%s is running. Close it first -- it holds the dll list in memory and can\n"
            "rewrite the config over this edit." % EXE_NAME
        )

    toml_path = target / TOML_NAME
    dll_path = str(me3 / DLL_NAME)
    if not toml_path.is_file():
        elsewhere = find_toml_nearby(target)
        if elsewhere is not None:
            raise InstallError(
                "%s is not in %s, but it DOES exist at %s.\n"
                "--randomizer should point at the folder that holds the toml (with the exe\n"
                "beside it) -- re-run with that folder." % (TOML_NAME, target, elsewhere.parent)
            )
        # Genuinely absent: a fresh install. The app does NOT write this file just from opening
        # the 'Add dll mod' dialog (measured 2026-08-21), so waiting for it strands first-time
        # installs. Create it, carrying only the line this tool owns, in the app's own style.
        toml_path.write_text(created_dll_toml(dll_path), encoding="utf-8")
        print("Created %s (it did not exist -- fresh install)" % TOML_NAME)
        print("  now loading: %s" % dll_path)
        print(
            "  NOTE: this file was created by the installer, not by matt's app. If the app\n"
            "  refuses to start or the client does not load, delete it and report the issue."
        )
        _post_edit_notes(created_dll_toml(dll_path))
        return _maybe_extras(args, me3, target, 0)

    text = toml_path.read_text(encoding="utf-8-sig")
    new_text, action = mutate_dll_toml(text, dll_path)

    if action == "current":
        print("Already current: %s already points at %s" % (TOML_NAME, dll_path))
        rc = 2
    else:
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = toml_path.with_name(toml_path.name + ".bak-" + stamp)
        shutil.copy2(toml_path, backup)
        toml_path.write_text(new_text, encoding="utf-8")
        print("%s the client entry in %s" % (action.capitalize(), TOML_NAME))
        print("  now loading: %s" % dll_path)
        print("  backup: %s" % backup.name)
        rc = 0

    _post_edit_notes(new_text)
    return _maybe_extras(args, me3, target, rc)


def _post_edit_notes(toml_text: str) -> None:
    if "randomizerhelper.dll" in toml_text.lower():
        print(HELPER_WARNING)
    print(
        "Note: launched through matt's launcher there is NO separate AP_me3.sl2 save --\n"
        "your Archipelago character lives in the normal Elden Ring save file."
    )


def _maybe_extras(args, me3: Path, target: Path, rc: int) -> int:
    if args.with_flower:
        flower = me3 / "install_ap_flower.py"
        if not flower.is_file():
            raise InstallError("--with-flower: install_ap_flower.py not found beside this script")
        print("Running the AP Flower installer...")
        flower_rc = subprocess.run(
            [sys.executable, str(flower), "--destination", str(target)], check=False
        ).returncode
        if flower_rc != 0:
            print("AP Flower installer exited %d -- see its output above." % flower_rc)
            return 1
    if args.with_torrent_repair:
        try:
            from torrent_rideparam_repair import TorrentRepairError, repair_regulation
            state, backup = repair_regulation(target / "regulation.bin")
        except (ImportError, TorrentRepairError) as exc:
            raise InstallError("--with-torrent-repair: %s" % exc) from exc
        if state == "current":
            print("Torrent repair already current: all four 1.17 RideParam rows are present")
        else:
            print("Patched four Elden Ring 1.17 Spectral Steed rows into regulation.bin")
            print("  backup: %s" % backup.name)
            rc = 0
    return rc


def main() -> int:
    try:
        return run()
    except InstallError as exc:
        print("REFUSED: %s" % exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
