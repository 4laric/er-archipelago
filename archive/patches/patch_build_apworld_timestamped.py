#!/usr/bin/env python3
r"""patch_build_apworld_timestamped.py

Make build.ps1's -Apworld step also drop a TIMESTAMPED copy of the package:
  eldenring.apworld                      (canonical -- unchanged)
  eldenring_<yyyyMMdd-HHmmss>.apworld    (NEW -- freshness witness + snapshot)

WHY: -All repackages eldenring.apworld every clean build, but the canonical name is overwritten in
place, so its freshness is invisible through a stale sandbox mount (and easy to second-guess on
Windows too). A stamped copy makes "did this build actually repackage?" answerable at a glance
(Always-timestamp-dump-files convention). NOTE: -Generate loads the apworld from the SOURCE TREE,
not this package, so the package is for distribution / verification, not the dev gen loop.

Also tidies the package exclude list so the new ER_SPHERE_TIERS_<stamp>.txt / ER_DIAG_<stamp>.txt
gen dumps don't get bundled (the old exact-name excludes only caught the un-stamped versions).

Edits build.ps1 (two unique anchors). Idempotent (skips if 'timestamped copy' already present).
CRLF-preserving. Run on Windows from repo root:
    python patch_build_apworld_timestamped.py
"""
import os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PS1 = os.path.join(ROOT, "build.ps1")
if not os.path.exists(PS1):
    sys.exit("ERROR: build.ps1 not found (run from repo root).")

with open(PS1, "rb") as f:
    data = f.read()

if b"timestamped copy" in data:
    print("  [skip] build.ps1 already drops a timestamped apworld copy.")
    sys.exit(0)

nl = b"\r\n" if b"\r\n" in data else b"\n"


def repl(d, old, new, label):
    if d.count(old) != 1:
        sys.exit("  [FAIL] %s: anchor x%d (want 1). No write." % (label, d.count(old)))
    return d.replace(old, new, 1)


# 1) widen the exclude list to drop stamped gen dumps from the package
EXC_OLD = b"    $excludeName  = @('*.bak', '*.bak_*', '*.pyc', '*.pyo')"
EXC_NEW = b"    $excludeName  = @('*.bak', '*.bak_*', '*.pyc', '*.pyo', 'ER_SPHERE_TIERS_*', 'ER_DIAG_*')"
data = repl(data, EXC_OLD, EXC_NEW, "exclude list")

# 2) after the success line, copy the package to a timestamped name
SUCCESS = b'    Write-Host ("  -> {0}  ({1} files, {2} KB)" -f $outFile, $files.Count, $size) -ForegroundColor Green'
ADD = nl.join([
    b"",
    b"    # Timestamped copy: the canonical eldenring.apworld is overwritten in place each build, so its",
    b"    # freshness is invisible through a stale mount / same-name overwrite. This stamped twin is the",
    b"    # witness that THIS build repackaged, plus a distributable snapshot (Always-timestamp convention).",
    b"    $apwStamp = Get-Date -Format 'yyyyMMdd-HHmmss'",
    b'    $apwCopy  = Join-Path $Repo ("eldenring_{0}.apworld" -f $apwStamp)',
    b"    Copy-Item -LiteralPath $outFile -Destination $apwCopy -Force",
    b'    Write-Host ("  -> {0}  (timestamped copy)" -f $apwCopy) -ForegroundColor Green',
])
data = repl(data, SUCCESS, SUCCESS + ADD, "success line")

with open(PS1, "wb") as f:
    f.write(data)

print("  [ok]   build.ps1 -Apworld now writes eldenring.apworld + eldenring_<stamp>.apworld")
print("DONE -- next -Apworld / -All run drops a stamped copy in the repo root; if no fresh "
      "eldenring_<today>.apworld appears, packaging didn't run.")
