#!/usr/bin/env python3
"""
patch_build_deploy_hygiene.py -- wire tools\\deploy_hygiene.ps1 into build.ps1.

Alaric 2026-06-19: "clean can do a restore. i already have a snapshot from earlier."
WHY: build.ps1 -Deploy only OVERWRITES game files (never removes), so a previous enemy/scale bake's
map\\ MSBs stay live and contaminate the next run (?NpcName? / garbled msgs / crashes). The fix tool
already exists (tools\\deploy_hygiene.ps1 + deploy_manifest.txt); this just calls it automatically:

  - $Clean block  -> deploy_hygiene.ps1 -Restore   (revert last run's deployed files to vanilla)
  - $Deploy block -> deploy_hygiene.ps1 -Snapshot  (record what we just deployed, for next restore)

In the -Clean -All flow this orders correctly: Clean(restore vanilla) -> Bake -> Deploy(overlay) ->
Snapshot. Restore is no-op if no manifest; Alaric already has a snapshot from an earlier deploy, so the
first -Clean will actually revert that run's files. Both use -GameDir $GameDir (= $AssetDir, game root).

NOTE: restore is tied to -Clean (per Alaric). A bare -Deploy WITHOUT -Clean still won't restore -- run
clean builds when switching seed shape (matches the -Clean -All convention).

build.ps1 is CRLF. Idempotent, binary I/O preserves CRLF, count==1 anchor guards. Run on Windows
(or anywhere -- it only edits build.ps1). Safe to re-run.
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(ROOT, "build.ps1")


def _read(p):
    with open(p, "rb") as f:
        return f.read()


def _write(p, d):
    with open(p, "wb") as f:
        f.write(d)


def _crlf(t):
    return t.replace("\n", "\r\n").encode("utf-8")


def _ins_after(data, anchor, insert, label):
    if data.count(anchor) != 1:
        raise SystemExit(f"[FAIL] {label}: anchor x{data.count(anchor)} (want 1). No write.")
    return data.replace(anchor, anchor + insert, 1)


# 1. Restore at the end of the $Clean block (after the intermediates-removal foreach).
CLEAN_ANCHOR = _crlf(
    '    foreach ($t in $targets) {\n'
    '        if (Test-Path $t) { Remove-Item -Recurse -Force $t; Write-Host "  removed $t" }\n'
    '    }\n'
)
CLEAN_INSERT = _crlf(
    '\n'
    '    # Deploy hygiene: revert the PREVIOUS run\'s deployed game files to vanilla before we rebuild,\n'
    '    # so stale map\\ MSBs from an enemy/scale bake don\'t leak into this run (?NpcName?/crashes).\n'
    '    # No-op on the first run (no manifest). See tools\\deploy_hygiene.ps1 / er-deploy-hygiene-gap.\n'
    '    $hygiene = Join-Path $Repo "tools\\deploy_hygiene.ps1"\n'
    '    if (Test-Path $hygiene) {\n'
    '        Step "Deploy hygiene: restoring last run\'s game files to vanilla"\n'
    '        & $hygiene -Restore -GameDir $GameDir\n'
    '    } else {\n'
    '        Write-Warning "tools\\deploy_hygiene.ps1 not found -- skipping vanilla restore (stale files may leak)"\n'
    '    }\n'
)

# 2. Snapshot at the end of the $Deploy block (right after the final launch-checklist Write-Host).
DEPLOY_ANCHOR = _crlf(
    '    Write-Host "  - \'Loaded N location flags for check polling\' appears at startup"\n'
)
DEPLOY_INSERT = _crlf(
    '\n'
    '    # Deploy hygiene: record exactly what we just deployed so the NEXT -Clean restore knows which\n'
    '    # game files to revert to vanilla. See tools\\deploy_hygiene.ps1.\n'
    '    $hygiene = Join-Path $Repo "tools\\deploy_hygiene.ps1"\n'
    '    if (Test-Path $hygiene) {\n'
    '        & $hygiene -Snapshot -GameDir $GameDir\n'
    '    } else {\n'
    '        Write-Warning "tools\\deploy_hygiene.ps1 not found -- skipping deploy snapshot (next restore will be a no-op)"\n'
    '    }\n'
)


def main():
    if not os.path.isfile(BUILD):
        raise SystemExit(f"[FAIL] not found: {BUILD}")
    data = _read(BUILD)
    if b"deploy_hygiene.ps1" in data:
        print("[skip] build.ps1 already wired for deploy hygiene.")
        return
    data = _ins_after(data, CLEAN_ANCHOR, CLEAN_INSERT, "Clean -Restore")
    data = _ins_after(data, DEPLOY_ANCHOR, DEPLOY_INSERT, "Deploy -Snapshot")
    _write(BUILD, data)
    print("[ok] patched build.ps1: -Clean now restores vanilla, -Deploy now snapshots the manifest.")


if __name__ == "__main__":
    main()
