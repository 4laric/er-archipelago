#!/usr/bin/env python3
"""pack_release.py -- assemble the player-facing ER Archipelago bundle, on any OS.

The portable half of `package_release.ps1`, which is being retired. That script is 687 lines of
PowerShell that only ever ran on one Windows box, and every release therefore depended on one
machine being healthy and one person remembering the switches. `release.yaml` in this repo records
the consequence in its own header -- "the bundle stays a Windows-built manual upload" -- and the
pin record has broken at v0.2.17, v0.3.1, v0.3.5, v0.3.7 and v0.3.11, every time with a .dll that
"was built separately".

WHAT THIS DOES NOT DO, ON PURPOSE
    It does not re-implement gates that are already Python. `tools/gf_zip_gen_smoke.py`,
    `tools/check_release_pairing.py` and `tools/gen_region_locks.py --check` are portable as they
    stand and the workflow calls them directly. A second copy of a check is a second thing to drift.

    It does not build the apworld (`tools/build_apworld.py`) or the .dll (the client repo's CI does,
    on windows-latest). It copies an optional, privately supplied `flower-package` verbatim; the
    installer authenticates its manifest before any destination write.

EXIT CODES -- 0 clean, 1 hard failure, 2 staged WITH WARNINGS. 2 is load-bearing: it is how an
`--unofficial` build says "this is not a release", and it must never collapse into 0.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import zipfile
from datetime import datetime, timezone

from package_me3_profile import (
    ProfileError,
    configure_release_profile,
    validate_release_profile,
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REL = os.path.join(REPO, "release")

WARNINGS: list[str] = []


def info(m: str) -> None:
    print(f"  {m}")


def warn(m: str) -> None:
    WARNINGS.append(m)
    print(f"::warning::pack_release: {m}")


def die(m: str) -> "None":
    print(f"::error::pack_release: {m}", file=sys.stderr)
    raise SystemExit(1)


def flower_manifest(root: str, version: str) -> None:
    files = []
    for relative in ("menu/hi/01_common.tpf.dcx", "menu/low/01_common.tpf.dcx"):
        path = os.path.join(root, *relative.split("/"))
        if not os.path.isfile(path):
            die(f"AP flower release input is missing {relative}")
        digest = hashlib.sha256()
        with open(path, "rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        files.append({"path": relative, "size": os.path.getsize(path),
                      "sha256": digest.hexdigest()})
    with open(os.path.join(root, "manifest.json"), "w", encoding="utf-8", newline="\n") as stream:
        json.dump({"schema": 1, "asset_version": version, "files": files}, stream, indent=2)
        stream.write("\n")


def soft(m: str, hard: bool) -> None:
    """A gate that is hard for a release and a warning for an --unofficial build.

    🛑 ONLY THE IDENTITY GATES MAY USE THIS. package_release.ps1 draws the line exactly here and the
    reasoning is worth keeping: the changelog match and the version-lockstep sites exist to stop a
    build CLAIMING to be a release it is not, and an unofficial build claims nothing. Every
    CORRECTNESS gate stays hard, because a preview build goes to somebody who will play it and a
    mispaired apworld/client does not fail at the door -- it boots, connects, and misbehaves.
    """
    die(m) if hard else warn(m)


# -- the me3 allowlist ----------------------------------------------------------------------------
# ALLOWLIST, NOT BLACKLIST, and this is the second time that has had to be said. The original copied
# me3\ wholesale and stripped a hand-list of cruft, so anything the strip-list did not anticipate
# rode into the release. A strip-list is always one surprise behind.
# apconfig.json is absent deliberately -- it is written fresh below.
ME3_ALLOW = ("ap.me3", "eldenring_archipelago.dll", "check_lots_table.json",
             "shoplineup_flags.json")

# The only binary we ship. Anything else matching *.dll/*.exe/*.asi in the stage is a hard failure.
OUR_BINARIES = ("eldenring_archipelago.dll",)

DOCS = [
    ("release/LICENSE", True),
    ("release/EldenRing.yaml", True),
    ("release/SETUP.md", True),
    ("release/RELEASE-NOTES-v0.2.md", True),
    ("release/CHANGELOG.md", True),
    ("release/KNOWN-ISSUES.md", True),
    ("release/ATTRIBUTION.md", True),
    ("release/PROVENANCE.md", True),
    ("release/ENEMY-AND-STARTING-CLASS-RANDOMIZATION.md", True),
    ("Elden-Ring-Archipelago-Player-Guide.md", True),
    ("release/SCREENSHOTS.md", False),
    ("release/DISTRIBUTION.md", False),
]

# 🛑 BYTE-IDENTICAL TO WHAT THE CLIENT WRITES. `shared::config::serialize_config` pretty-prints on
# save and the client test `the_template_shape_is_what_we_ship` asserts these exact bytes. LF, no
# BOM, trailing newline -- CRLF here would make the player's first connect rewrite every line ending.
# The port is a PLACEHOLDER, not a value: archipelago.gg assigns a room its port at creation, so no
# number could be right, and `PORT` cannot be mistaken for a working setting.
APCONFIG = (
    '{\n'
    '  "url": "archipelago.gg:PORT",\n'
    '  "slot": "Player1",\n'
    '  "seed": "",\n'
    '  "client_version": null,\n'
    '  "password": null\n'
    '}\n'
)


def read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def gate_changelog(version: str, hard: bool) -> None:
    p = os.path.join(REL, "CHANGELOG.md")
    if not os.path.isfile(p):
        die("CHANGELOG.md not found -- it ships as a required doc")
    m = re.search(r"^## v(\d+\.\d+(?:\.\d+)?)", read(p), re.M)
    if not m:
        soft("CHANGELOG.md has no `## vX.Y.Z` heading", hard)
    elif m.group(1) != version:
        soft(f"CHANGELOG.md's newest entry is v{m.group(1)}, packaging v{version}", hard)
    else:
        info(f"changelog: v{version} OK")


def gate_version_lockstep(version: str, client_dir: str | None, hard: bool) -> None:
    """The three places the version is written must be one number.

    Mirrors test_gf_apworld_manifest.py::test_the_three_version_numbers_are_one_number. The client
    site is OPTIONAL and skips loudly when the tree is absent -- silently skipping it is how
    v0.2.17 passed a VERSION: OK check against a 0.2.15 dll.
    """
    sites = [
        ("greenfield/eldenring/archipelago.json", r'"world_version"\s*:\s*"([^"]+)"', REPO),
        ("greenfield/eldenring/contract.py", r'APWORLD_VERSION\s*=\s*"([^"]+)"', REPO),
    ]
    if client_dir:
        sites.append(("crates/eldenring-archipelago/Cargo.toml", r'^version\s*=\s*"([^"]+)"', client_dir))
    else:
        warn("client tree absent -- the Cargo.toml version site was NOT checked")

    for rel, pat, root in sites:
        p = os.path.join(root, rel)
        if not os.path.isfile(p):
            soft(f"version site missing: {rel}", hard)
            continue
        m = re.search(pat, read(p), re.M)
        if not m:
            soft(f"version site unreadable: {rel}", hard)
        elif m.group(1) != version:
            soft(f"{rel} says {m.group(1)}, packaging {version}", hard)
        else:
            info(f"version site OK: {rel}")


def stage(args, stage_dir: str) -> None:
    os.makedirs(stage_dir, exist_ok=True)

    # 1. apworld
    if not os.path.isfile(args.apworld):
        die(f"apworld not found: {args.apworld}")
    shutil.copy2(args.apworld, os.path.join(stage_dir, "eldenring.apworld"))
    info("+ eldenring.apworld")

    # 2. me3/, allowlisted
    me3_dst = os.path.join(stage_dir, "me3")
    os.makedirs(me3_dst, exist_ok=True)
    copied = 0
    for name in ME3_ALLOW:
        src = os.path.join(args.me3, name)
        if not os.path.exists(src):
            continue
        dst = os.path.join(me3_dst, name)
        shutil.copytree(src, dst, dirs_exist_ok=True) if os.path.isdir(src) else shutil.copy2(src, dst)
        copied += 1
    info(f"+ me3/ (allowlisted {copied} of {len(ME3_ALLOW)})")

    icon_installer = os.path.join(REPO, "tools", "install_ap_flower.ps1")
    icon_installer_py = os.path.join(REPO, "tools", "install_ap_flower.py")
    if not os.path.isfile(icon_installer) or not os.path.isfile(icon_installer_py):
        die("AP flower packaged-asset installer is missing")
    shutil.copy2(icon_installer, os.path.join(me3_dst, "install-ap-flower.ps1"))
    shutil.copy2(icon_installer_py, os.path.join(me3_dst, "install_ap_flower.py"))
    # The matt's-launcher installer pair (#944): ships beside the dll it wires in, because
    # bundle_dir() resolves the bundle as "the folder this script runs from".
    matts_installer = os.path.join(REPO, "tools", "install_into_matts_rando.ps1")
    matts_installer_py = os.path.join(REPO, "tools", "install_into_matts_rando.py")
    if not os.path.isfile(matts_installer) or not os.path.isfile(matts_installer_py):
        die("matt's-randomizer installer is missing")
    shutil.copy2(matts_installer, os.path.join(me3_dst, "install-into-matts-rando.ps1"))
    shutil.copy2(matts_installer_py, os.path.join(me3_dst, "install_into_matts_rando.py"))
    flower_package = os.path.join(args.me3, "flower-package")
    staged_package: str | None = None
    if os.path.isdir(flower_package):
        flower_manifest(flower_package, args.version)
        shutil.copytree(flower_package, os.path.join(me3_dst, "flower-package"))
        staged_package = "flower-package"
        info("+ AP flower installers + packaged hi/low atlases")
    elif not args.unofficial:
        die("stable release requires me3/flower-package with both AP Flower atlases")
    else:
        warn("AP Flower release assets unavailable; installer will report that clearly")

    profile_path = Path(me3_dst, "ap.me3")
    if not profile_path.is_file():
        die("no ap.me3 in the stage -- me3 has nothing to load")
    try:
        configured = configure_release_profile(profile_path, Path(me3_dst), staged_package)
    except ProfileError as exc:
        die(f"could not configure staged me3 profile: {exc}")
    info(f"+ me3/ap.me3 package = {configured[0] if configured else '<none>'}")

    if os.path.isdir(args.me3):
        extra = [n for n in os.listdir(args.me3)
                 if n not in ME3_ALLOW
                 and n not in ("apconfig.json", "ap-package", "flower-package")]
        if extra:
            warn(f"excluded {len(extra)} non-release item(s) from me3/: {', '.join(sorted(extra)[:25])}")

    # 3. apconfig.json, generated
    with open(os.path.join(me3_dst, "apconfig.json"), "w", encoding="utf-8", newline="") as f:
        f.write(APCONFIG)
    info("+ me3/apconfig.json (generic template)")

    # 4. screenshots
    shots = os.path.join(REL, "screenshots")
    if os.path.isdir(shots):
        shutil.copytree(shots, os.path.join(stage_dir, "screenshots"), dirs_exist_ok=True)
        info(f"+ screenshots/ ({len(os.listdir(shots))} files)")

    # 5. docs, flat at the root
    for rel, required in DOCS:
        src = os.path.join(REPO, rel)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(stage_dir, os.path.basename(rel)))
            info(f"+ {os.path.basename(rel)}")
        elif required:
            die(f"missing required file: {rel}")


def gate_stage(stage_dir: str, unofficial: bool) -> None:
    """Everything below is a CORRECTNESS gate and stays hard even for --unofficial."""
    me3 = os.path.join(stage_dir, "me3")

    dll = os.path.join(me3, "eldenring_archipelago.dll")
    if not os.path.isfile(dll):
        die("no eldenring_archipelago.dll in the stage")
    if os.path.getsize(dll) < 1024:
        die(f"eldenring_archipelago.dll is {os.path.getsize(dll)} bytes -- that is not a build")
    info(f"dll: {os.path.getsize(dll)/1e6:.2f} MB")

    profile_path = Path(me3, "ap.me3")
    if not profile_path.is_file():
        die("no ap.me3 in the stage -- me3 has nothing to load")

    installer = os.path.join(me3, "install-ap-flower.ps1")
    installer_py = os.path.join(me3, "install_ap_flower.py")
    if not os.path.isfile(installer):
        die("no install-ap-flower.ps1 in the stage")
    if not os.path.isfile(installer_py):
        die("no install_ap_flower.py in the stage")
    package = os.path.join(me3, "flower-package")
    if os.path.isdir(package):
        try:
            from install_ap_flower import load_package
            load_package(Path(package))
        except Exception as exc:
            die(f"invalid packaged AP Flower assets: {exc}")
    elif not unofficial:
        die("stable stage has no authenticated flower-package")
    info("AP flower: packaged-asset installer present")

    expected_package = "flower-package" if os.path.isdir(package) else None
    try:
        profile_packages = validate_release_profile(profile_path, Path(me3), expected_package)
    except ProfileError as exc:
        die(f"staged me3 profile/package mismatch: {exc}")
    info(f"me3 profile package: {profile_packages[0] if profile_packages else '<none>'} -- exists")

    # Walk once for the remaining two content gates.
    leaked, foreign, loose_atlases = [], [], []
    for root, _dirs, files in os.walk(stage_dir):
        for f in files:
            low = f.lower()
            if low.startswith("ap_save_") and low.endswith(".json"):
                leaked.append(os.path.relpath(os.path.join(root, f), stage_dir))
            if low == "01_common.tpf.dcx" and not os.path.relpath(
                    os.path.join(root, f), me3).replace("\\", "/").startswith("flower-package/menu/"):
                loose_atlases.append(os.path.relpath(os.path.join(root, f), stage_dir))
            # Case-INSENSITIVE on purpose. It was implicitly so on Windows; a naive port makes it
            # case-sensitive and `Eldenring_Archipelago.dll` newly trips this gate.
            if low.endswith((".dll", ".exe", ".asi")) and low not in [b.lower() for b in OUR_BINARIES]:
                foreign.append(os.path.relpath(os.path.join(root, f), stage_dir))
    if leaked:
        die(f"player save state staged: {', '.join(leaked)}")
    if foreign:
        die(f"third-party binaries staged: {', '.join(foreign)}")
    if loose_atlases:
        die(f"AP Flower atlas outside authenticated flower-package: {', '.join(loose_atlases)}")
    info("no save state, no third-party binaries")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--apworld", required=True, help="path to the built eldenring.apworld")
    ap.add_argument("--me3", default=os.path.join(REPO, "me3"), help="staging source for me3/")
    ap.add_argument("--client-dir", default=None, help="client repo tree, for the version site")
    ap.add_argument("--out", default=os.path.join(REPO, "dist"))
    ap.add_argument("--unofficial", action="store_true")
    ap.add_argument("--stamp", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    version = args.version.lstrip("vV")
    if args.unofficial and not args.stamp:
        die("--stamp is REQUIRED with --unofficial: the label is the whole point, so a bug report "
            "against a preview build can be tied back to a build")
    stamp = re.sub(r"[^A-Za-z0-9._-]", "-", args.stamp)
    name = f"ER-Archipelago-v{version}" + (f"-UNOFFICIAL-{stamp}" if args.unofficial else "")

    hard = not args.unofficial
    print("== identity gates ==")
    gate_changelog(version, hard)
    gate_version_lockstep(version, args.client_dir, hard)

    stage_dir = os.path.join(args.out, name)
    if os.path.isdir(stage_dir):
        shutil.rmtree(stage_dir)
    print("== staging ==")
    stage(args, stage_dir)

    print("== correctness gates ==")
    gate_stage(stage_dir, args.unofficial)

    if args.unofficial:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
        body = [f"UNOFFICIAL BUILD -- {stamp}", f"cut {ts}", "",
                "This is NOT a release. It was cut for one person, from one commit.", ""]
        body += [f"world  {os.environ.get('GITHUB_SHA', '(unknown)')}",
                 f"client {os.environ.get('CLIENT_SHA', '(unknown)')}", ""]
        body += ["warnings:"] + [f"  - {w}" for w in WARNINGS] if WARNINGS else ["no warnings"]
        # CRLF + ASCII, matching the original. Deliberately NOT unified with apconfig's LF.
        with open(os.path.join(stage_dir, "UNOFFICIAL-BUILD.txt"), "w",
                  encoding="ascii", errors="replace", newline="\r\n") as f:
            f.write("\n".join(body) + "\n")
        info("+ UNOFFICIAL-BUILD.txt")

    if args.dry_run:
        print(f"== dry run: staged at {stage_dir}, not zipping ==")
        return 2 if WARNINGS else 0

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    zip_path = os.path.join(args.out, f"{name}-{ts}.zip")
    # 🛑 NO TOP-LEVEL FOLDER. Entries sit at the zip root -- every line of SETUP.md assumes it.
    # 🛑 FORWARD SLASHES. Windows PowerShell 5.1's Compress-Archive wrote `\` into entry paths;
    # zipfile writes `/`, which is what the format actually specifies. Sorted for determinism.
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(stage_dir):
            dirs.sort()
            for f in sorted(files):
                full = os.path.join(root, f)
                z.write(full, os.path.relpath(full, stage_dir).replace(os.sep, "/"))
    print(f"== {zip_path} ({os.path.getsize(zip_path)/1e6:.1f} MB) ==")

    bare = os.path.join(args.out, f"{name}-{ts}.apworld")
    shutil.copy2(args.apworld, bare)
    print(f"== {bare} ==")

    if WARNINGS:
        print(f"\n{len(WARNINGS)} warning(s) -- review before shipping")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
