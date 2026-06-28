#!/usr/bin/env python3
"""Add an -Apworld step to build.ps1 that packages eldenring.apworld.

`build.ps1 -Apworld` zips Archipelago\\worlds\\eldenring into <repo>\\eldenring.apworld
with the AP-required inner root (eldenring/...), excluding dev clutter:
  - per-patch __init__ backups (*.bak, *.bak_*)   <- the big one (~30 copies)
  - bytecode caches (__pycache__, *.pyc, *.pyo)
  - the gen-time diag dumps the world writes into its own folder
The packaging is also wired into -All so the committed artifact stays fresh.
(Gen itself still reads the worlds/eldenring SOURCE directly; the .apworld is the
distributable artifact, which otherwise drifts stale.)

Idempotent, CRLF-aware. Run from the repo root:  python patch_build_apworld.py
"""
import io, os, sys

TARGET = "build.ps1"

STEP_BLOCK = '''
# ----- package apworld ------------------------------------------------------------------------
if ($Apworld) {
    Step "Packaging eldenring.apworld from Archipelago\\worlds\\eldenring"
    $srcDir = Join-Path $ApDir "worlds\\eldenring"
    if (-not (Test-Path (Join-Path $srcDir "__init__.py"))) { throw "apworld source not found: $srcDir\\__init__.py" }
    $outFile = Join-Path $Repo "eldenring.apworld"
    Add-Type -AssemblyName System.IO.Compression.FileSystem | Out-Null
    # Exclude dev clutter: per-patch __init__ backups (*.bak*), bytecode caches, and the
    # gen-time diag dumps the world writes into its own folder. Keep the real package + data.
    $excludeName  = @('*.bak', '*.bak_*', '*.pyc', '*.pyo')
    $excludeExact = @('ER_DIAG.txt', 'ER_SPHERE_TIERS.txt')
    $srcFull = (Resolve-Path $srcDir).Path.TrimEnd('\\')
    $files = Get-ChildItem -LiteralPath $srcFull -Recurse -File | Where-Object {
        $rel = $_.FullName.Substring($srcFull.Length).TrimStart('\\','/')
        if ($rel -match '(^|[\\\\/])__pycache__([\\\\/]|$)') { return $false }
        if ($excludeExact -contains $_.Name) { return $false }
        foreach ($p in $excludeName) { if ($_.Name -like $p) { return $false } }
        return $true
    }
    if (Test-Path $outFile) { Remove-Item -LiteralPath $outFile -Force }
    $zip = [System.IO.Compression.ZipFile]::Open($outFile, 'Create')
    try {
        foreach ($f in $files) {
            $rel = $f.FullName.Substring($srcFull.Length).TrimStart('\\','/').Replace('\\','/')
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $f.FullName, "eldenring/$rel") | Out-Null
        }
    } finally { $zip.Dispose() }
    $size = [math]::Round((Get-Item $outFile).Length / 1KB, 1)
    Write-Host ("  -> {0}  ({1} files, {2} KB)" -f $outFile, $files.Count, $size) -ForegroundColor Green
}
'''

EDITS = [
    # 1. usage comment line
    ('#   .\\build.ps1 -Preflight               # timestamped preflight log + PASS/FAIL cross-checks (seed/slot/deploy freshness)',
     '#   .\\build.ps1 -Apworld                 # package Archipelago\\worlds\\eldenring into eldenring.apworld (excludes .bak/.pyc)\n'
     '#   .\\build.ps1 -Preflight               # timestamped preflight log + PASS/FAIL cross-checks (seed/slot/deploy freshness)'),

    # 2. param switch
    ('    [switch]$Deploy,',
     '    [switch]$Deploy,\n    [switch]$Apworld,'),

    # 3. -All wires it on
    ('    $Serve = $true; $Bake = $true; $Enemies = $true; $Deploy = $true; $Preflight = $true',
     '    $Serve = $true; $Bake = $true; $Enemies = $true; $Deploy = $true; $Preflight = $true; $Apworld = $true'),

    # 4. arg guard (so -Apworld alone is a valid invocation)
    ('-or $LoopTest -or $All)) {',
     '-or $LoopTest -or $Apworld -or $All)) {'),

    # 5. the step block, appended right after the -Generate block closes
    ('    Write-Host "  -> $($newest.FullName)"\n}\n',
     '    Write-Host "  -> $($newest.FullName)"\n}\n' + STEP_BLOCK),
]


def main():
    if not os.path.exists(TARGET):
        sys.exit("ERROR: %s not found -- run from the repo root." % TARGET)
    with io.open(TARGET, "r", encoding="utf-8", newline="") as f:
        content = f.read()
    eol = "\r\n" if "\r\n" in content else "\n"

    changed = False
    for old, new in EDITS:
        o = old.replace("\n", eol)
        n = new.replace("\n", eol)
        if n in content:
            print("  [skip] already applied: %s" % old.splitlines()[0][:60])
            continue
        c = content.count(o)
        if c != 1:
            sys.exit("ERROR: expected 1 match, found %d for anchor:\n%s" % (c, old.splitlines()[0]))
        content = content.replace(o, n)
        changed = True
        print("  [ok]   applied: %s" % old.splitlines()[0][:60])

    if changed:
        with io.open(TARGET, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        print("Wrote %s (EOL=%s)." % (TARGET, repr(eol)))
    else:
        print("No changes.")


if __name__ == "__main__":
    main()
