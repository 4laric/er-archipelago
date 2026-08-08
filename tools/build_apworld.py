#!/usr/bin/env python3
"""build_apworld.py -- pack greenfield/eldenring into `eldenring.apworld`, anywhere.

WHY A SECOND BUILDER EXISTS, AND WHY IT IS NOT A SECOND ANSWER
-------------------------------------------------------------
`build.ps1 -Apworld` has done this since 2026-06-20 and it is the one that cuts releases. It is
PowerShell, so it runs on Alaric's box and nowhere else -- which is exactly why
`release/DISTRIBUTION.md`'s promise of a bare `eldenring.apworld` asset beside every tag has never
been kept. Measured 2026-08-08: every release from v0.3.2 to v0.3.7 carries **one** asset, the
123.7 MB player bundle, and the doc's own argument for the bare one is that making a host download a
game-mod DLL to generate someone else's seed is "friction for nothing".

So this is the same pack, in Python, so a Linux CI runner can do it on a tag push.

🛑 THE EXCLUSION LIST IS PORTED VERBATIM FROM `build.ps1`, AND THAT IS THE WHOLE RISK HERE. Two
builders is two chances to disagree, and the disagreement would be invisible -- both produce a zip
that installs. `test_gf_apworld_build.py` asserts the two lists match by reading them out of the
PowerShell source, so a change to either side reds rather than drifts. The right end state is
`build.ps1` CALLING this; that is a Windows change and wants Alaric's box to verify, so it is filed
in SPEC-publishing-pipeline.md rather than done blind from here.

DETERMINISM. Entries are sorted, timestamps fixed and permissions normalised, so the same tree packs
to the same bytes on any machine -- otherwise "did the asset change?" is unanswerable and a release
job cannot dedupe or verify anything. (`ZipFile` writes the local mtime by default, which would make
every rebuild a new artifact.)

    python tools/build_apworld.py                 # -> ./eldenring.apworld
    python tools/build_apworld.py -o dist/x.apworld
    python tools/build_apworld.py --list          # print what would go in, pack nothing
"""
import argparse
import fnmatch
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "greenfield", "eldenring")
INNER = "eldenring"          # the AP inner root: worlds/<this>/...

# ---- ported from build.ps1 (`$excludeName` / `$excludeExact`); the test asserts they still agree --
EXCLUDE_GLOB = ("*.bak", "*.bak_*", "*.pyc", "*.pyo", "ER_SPHERE_TIERS_*", "ER_DIAG_*")
# region_map.csv is a gen INPUT that gf_test copies in beside the package for the derivation oracles;
# it is not part of the shipped world and packing it would ship a test fixture to players.
EXCLUDE_EXACT = ("ER_DIAG.txt", "ER_SPHERE_TIERS.txt", "region_map.csv")
EXCLUDE_DIR = ("__pycache__",)

# A fixed DOS timestamp (1980-01-01) -- zip's own epoch, and the conventional choice for a
# reproducible archive. Any constant works; what matters is that it is not `now`.
FIXED_DATE = (1980, 1, 1, 0, 0, 0)


def members(src=SRC):
    """Relative posix paths to pack, sorted. Sorting is not cosmetic: it is half of determinism."""
    out = []
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIR]
        for name in filenames:
            if name in EXCLUDE_EXACT:
                continue
            if any(fnmatch.fnmatch(name, pat) for pat in EXCLUDE_GLOB):
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), src).replace(os.sep, "/")
            out.append(rel)
    return sorted(out)


def build(out_path, src=SRC):
    rels = members(src)
    if not rels:
        sys.exit("[FAIL] nothing to pack -- %s is empty or missing" % src)
    if "archipelago.json" not in rels:
        # The manifest is what AP reads world_version and game from. A zip without it installs and
        # then behaves as an unversioned world, which is the failure this repo has already had once.
        sys.exit("[FAIL] archipelago.json is not in the pack -- refusing to ship an unversioned world")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    if os.path.exists(out_path):
        os.remove(out_path)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel in rels:
            info = zipfile.ZipInfo(f"{INNER}/{rel}", date_time=FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16      # normalise perms; the source tree's vary by clone
            with open(os.path.join(src, rel), "rb") as f:
                z.writestr(info, f.read())
    return out_path, rels


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=os.path.join(ROOT, "eldenring.apworld"))
    ap.add_argument("--list", action="store_true", help="print the members and exit")
    args = ap.parse_args(argv)
    if args.list:
        for rel in members():
            print(rel)
        return 0
    out, rels = build(args.out)
    size = os.path.getsize(out)
    print("[ok] %s -- %d file(s), %.1f KB" % (os.path.relpath(out, ROOT), len(rels), size / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
