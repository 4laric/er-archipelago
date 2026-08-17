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

    It does not build the apworld (`tools/build_apworld.py`), the .dll (the client repo's CI does,
    on windows-latest) or the icon sheet (see below).

🛑 THE ICON SHEET IS NOT BUILDABLE HERE AND MUST NOT BE COMMITTED HERE.
    `me3/ap-package/menu/{hi,low}/01_common.tpf.dcx` is Elden Ring's 4096x2048 SB_Icon atlas with
    cell 92 repainted -- game data, PROVENANCE.md rule 1, and docs/AP-ICON-PIPELINE.md rules it out
    of this repo in as many words ("commit the derivation, never the derived game data"). The
    workflow supplies it from a PRIVATE repo. This script only checks it arrived: a bundle without
    it ships a literal telescope on every check, which is the bug a player reported on 2026-07-29.

EXIT CODES -- 0 clean, 1 hard failure, 2 staged WITH WARNINGS. 2 is load-bearing: it is how an
`--unofficial` build says "this is not a release", and it must never collapse into 0.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import zipfile
from datetime import datetime, timezone

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
             "shoplineup_flags.json", "ap-package")

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

    if os.path.isdir(args.me3):
        extra = [n for n in os.listdir(args.me3)
                 if n not in ME3_ALLOW and n != "apconfig.json"]
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


def gate_stage(stage_dir: str, unofficial: bool, allow_missing_ap_icon: bool = False) -> None:
    """Everything below is a CORRECTNESS gate and stays hard even for --unofficial."""
    me3 = os.path.join(stage_dir, "me3")

    dll = os.path.join(me3, "eldenring_archipelago.dll")
    if not os.path.isfile(dll):
        die("no eldenring_archipelago.dll in the stage")
    if os.path.getsize(dll) < 1024:
        die(f"eldenring_archipelago.dll is {os.path.getsize(dll)} bytes -- that is not a build")
    info(f"dll: {os.path.getsize(dll)/1e6:.2f} MB")

    if not os.path.isfile(os.path.join(me3, "ap.me3")):
        die("no ap.me3 in the stage -- me3 has nothing to load")

    # 🛑 THE REAL SHEET, not any file. build.ps1 also staged 00_solo.* as a hi-res extra, so an
    # any-file-present check passes on the cosmetic variant alone and still ships telescopes.
    menu = os.path.join(me3, "ap-package", "menu")
    sheets = []
    for root, _dirs, files in os.walk(menu):
        sheets += [os.path.join(root, f) for f in files if f.lower() == "01_common.tpf.dcx"]
    if not sheets:
        if not (unofficial and allow_missing_ap_icon):
            die("no 01_common.tpf.dcx under me3/ap-package/menu/ -- the AP icon override is missing, and "
                "the client writes iconId 92 unconditionally, so every check and AP shop slot would "
                "render as a Telescope. See docs/AP-ICON-PIPELINE.md.")
        warning = ("AP icon override intentionally omitted from this development build; checks and "
                   "AP shop slots use the vanilla Telescope icon")
        warn(warning)
        with open(os.path.join(stage_dir, "DEVELOPMENT-BUILD-NO-AP-ICON.txt"), "w",
                  encoding="ascii", newline="\n") as f:
            f.write(warning + ".\nStable releases still require the flower icon override.\n")
        info("ap-package: omitted by explicit development-build opt-out")
    else:
        info(f"ap-package: {len(sheets)} icon sheet(s)")

    # Walk once for the remaining two content gates.
    leaked, foreign = [], []
    for root, _dirs, files in os.walk(stage_dir):
        for f in files:
            low = f.lower()
            if low.startswith("ap_save_") and low.endswith(".json"):
                leaked.append(os.path.relpath(os.path.join(root, f), stage_dir))
            # Case-INSENSITIVE on purpose. It was implicitly so on Windows; a naive port makes it
            # case-sensitive and `Eldenring_Archipelago.dll` newly trips this gate.
            if low.endswith((".dll", ".exe", ".asi")) and low not in [b.lower() for b in OUR_BINARIES]:
                foreign.append(os.path.relpath(os.path.join(root, f), stage_dir))
    if leaked:
        die(f"player save state staged: {', '.join(leaked)}")
    if foreign:
        die(f"third-party binaries staged: {', '.join(foreign)}")
    info("no save state, no third-party binaries")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--apworld", required=True, help="path to the built eldenring.apworld")
    ap.add_argument("--me3", default=os.path.join(REPO, "me3"), help="staging source for me3/")
    ap.add_argument("--client-dir", default=None, help="client repo tree, for the version site")
    ap.add_argument("--out", default=os.path.join(REPO, "dist"))
    ap.add_argument("--unofficial", action="store_true")
    ap.add_argument("--allow-missing-ap-icon", action="store_true",
                    help="development builds only: ship without the private flower-icon override")
    ap.add_argument("--stamp", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    version = args.version.lstrip("vV")
    if args.unofficial and not args.stamp:
        die("--stamp is REQUIRED with --unofficial: the label is the whole point, so a bug report "
            "against a preview build can be tied back to a build")
    if args.allow_missing_ap_icon and not args.unofficial:
        die("--allow-missing-ap-icon is only valid with --unofficial; stable releases must carry "
            "the flower icon override")
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
    gate_stage(stage_dir, args.unofficial, args.allow_missing_ap_icon)

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
