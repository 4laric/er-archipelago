#!/usr/bin/env python3
"""Wire the Archipelago client into matt's randomizer launcher -- without moving a single file.

WHAT THIS EDITS (measured on a live v0.11.4 install, 2026-08-21; spec on issue #944):
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
  * `config_eldenringrandomizer_dll.toml` does not exist or has no `external_dlls` array
    (open "Add dll mod" once, close it, re-run -- creating the app's own state file for it
    is deliberately out of scope until the app's tolerance for that is verified).

Exit codes: 0 = changed, 2 = already current (idempotent no-op), 1 = refused.
All output is ASCII. A timestamped backup of the toml is written before any change.
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
        raise InstallError(
            "%s has no external_dlls array. Open matt's 'Add dll mod' dialog once, close\n"
            "it (the app writes the file), then re-run this installer." % TOML_NAME
        )
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
    args = parser.parse_args(argv)

    me3 = bundle_dir(script_path or Path(__file__))
    target = randomizer_dir(Path(args.randomizer))
    if app_is_running():
        raise InstallError(
            "%s is running. Close it first -- it holds the dll list in memory and can\n"
            "rewrite the config over this edit." % EXE_NAME
        )

    toml_path = target / TOML_NAME
    if not toml_path.is_file():
        raise InstallError(
            "%s does not exist yet. Open matt's 'Add dll mod' dialog once, close it\n"
            "(the app writes the file), then re-run this installer." % TOML_NAME
        )

    dll_path = str(me3 / DLL_NAME)
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

    if "randomizerhelper.dll" in new_text.lower():
        print(HELPER_WARNING)
    print(
        "Note: launched through matt's launcher there is NO separate AP_me3.sl2 save --\n"
        "your Archipelago character lives in the normal Elden Ring save file."
    )

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
    return rc


def main() -> int:
    try:
        return run()
    except InstallError as exc:
        print("REFUSED: %s" % exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
