#!/usr/bin/env python3
r"""patch_build_gen_retry.py

Add a re-roll RETRY loop to build.ps1's -Generate step (also used by -All).

WHY
---
Some ER gen failures are seed-dependent FillErrors (e.g. num_regions + warp
rolls that seal a region the goal route needs). Generate.py picks a FRESH random
seed every run, so simply re-running usually clears them. This wraps the gen
step so a FillError auto-re-rolls up to -GenRetries times (default 2 => up to 3
attempts). Config/syntax errors (no 'FillError' in the log) are treated as fatal
immediately -- retrying those just wastes time.

Adds two params:
  -GenRetries N      retry count on a seed-dependent FillError (default 2; 0 = off)
  -GenBumpRegions    on each retry, also bump num_regions +1 in Players\*.yaml to
                     loosen the constraint a notch (originals restored afterward)

USAGE (Windows, repo root):
    python patch_build_gen_retry.py
Idempotent. Edits only build.ps1.
"""
import io
import os
import sys

MARKER = "genretry"

PARAM_ANCHOR = "    [switch]$Generate,"
PARAM_NEW = (
    "    [switch]$Generate,\n"
    "    [int]$GenRetries = 2,            # " + MARKER + ": gen re-roll attempts on a seed-dependent FillError (0 = off)\n"
    "    [switch]$GenBumpRegions,         # " + MARKER + ": also bump num_regions +1 in Players\\*.yaml per retry (restored after)"
)

START_ANCHOR = '    $ts = Get-Date -Format "yyyyMMdd-HHmmss"'
END_ANCHOR = '    if ($genExit -ne 0) { throw ("multiworld generation FAILED (exit {0}) -- see diag/raw log above" -f $genExit) }'

# Replacement for the inclusive span START_ANCHOR .. END_ANCHOR.
NEW_BLOCK = r'''    # --- genretry: each Generate.py run picks a FRESH random seed, so a seed-dependent
    # FillError usually clears on a retry. Config/syntax errors (no 'FillError' in the log) are
    # fatal immediately. -GenRetries sets the count; -GenBumpRegions also bumps num_regions +1.
    $maxAttempts = 1 + [math]::Max(0, $GenRetries)
    $genExit = 1
    $playersDir = Join-Path $ApDir "Players"
    $yamlBackup = @{}
    if ($GenBumpRegions) {
        Get-ChildItem $playersDir -Filter *.yaml -ErrorAction SilentlyContinue | ForEach-Object {
            $yamlBackup[$_.FullName] = Get-Content -LiteralPath $_.FullName -Raw
        }
    }
    try {
        for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
            if ($attempt -gt 1) {
                Write-Warning ("gen re-roll: attempt {0} of {1} (fresh seed)" -f $attempt, $maxAttempts)
            }
            $ts = Get-Date -Format "yyyyMMdd-HHmmss"
            $genLog  = Join-Path $Repo "generate_$ts.log"
            $genDiag = Join-Path $Repo "gendiag_$ts.txt"
            Push-Location $ApDir
            try {
                $env:AP_NONINTERACTIVE = "1"   # suppress Generate.py's atexit "Press enter to close." pause
                cmd /c "python Generate.py > `"$genLog`" 2>&1"
                $genExit = $LASTEXITCODE
            } finally { Pop-Location }
            if (Test-Path (Join-Path $Repo "dlcdiag.py")) {
                python (Join-Path $Repo "dlcdiag.py") $genLog $genDiag $genExit | Out-Null
                if (Test-Path $genDiag) { Get-Content $genDiag | Write-Host }
            }
            Write-Host ("generation raw log -> {0}" -f $genLog)  -ForegroundColor Green
            if (Test-Path $genDiag) { Write-Host ("generation diag    -> {0}" -f $genDiag) -ForegroundColor Green }
            if ($genExit -eq 0) { break }
            $isFill = Select-String -Path $genLog -SimpleMatch -Pattern "FillError" -Quiet
            if (-not $isFill) {
                throw ("multiworld generation FAILED (exit {0}; not a FillError -- not retrying) -- see diag/raw log above" -f $genExit)
            }
            if ($attempt -lt $maxAttempts) {
                Write-Warning "  seed-dependent FillError -- re-rolling."
                if ($GenBumpRegions) {
                    foreach ($yf in @($yamlBackup.Keys)) {
                        $c = Get-Content -LiteralPath $yf -Raw
                        $c2 = [regex]::Replace($c, '(?m)^(\s*num_regions:[ \t]*)(\d+)', { param($m) $m.Groups[1].Value + ([int]$m.Groups[2].Value + 1) })
                        if ($c2 -ne $c) {
                            Set-Content -LiteralPath $yf -Value $c2 -NoNewline
                            Write-Warning ("  bumped num_regions +1 in {0}" -f (Split-Path $yf -Leaf))
                        }
                    }
                }
            }
        }
    } finally {
        foreach ($yf in @($yamlBackup.Keys)) {
            Set-Content -LiteralPath $yf -Value $yamlBackup[$yf] -NoNewline   # restore the yaml the user wrote
        }
    }
    if ($genExit -ne 0) { throw ("multiworld generation FAILED after {0} attempt(s) (exit {1}) -- see diag/raw log above" -f $maxAttempts, $genExit) }'''


def _find_target():
    here = os.path.dirname(os.path.abspath(__file__))
    for c in (os.path.join(here, "build.ps1"), os.path.join(os.getcwd(), "build.ps1")):
        if os.path.isfile(c):
            return c
    sys.exit("ERROR: build.ps1 not found (run from the er-archipelago repo root).")


def main():
    path = _find_target()
    with io.open(path, "r", encoding="utf-8", newline="") as f:
        raw = f.read()
    nl = "\r\n" if "\r\n" in raw else "\n"
    text = raw.replace("\r\n", "\n")

    if MARKER in text:
        print("[skip] already applied (%s marker present): %s" % (MARKER, path))
        return

    # 1) insert params
    if text.count(PARAM_ANCHOR) != 1:
        sys.exit("ERROR: param anchor %r found %d times (need 1)." % (PARAM_ANCHOR, text.count(PARAM_ANCHOR)))
    text = text.replace(PARAM_ANCHOR, PARAM_NEW, 1)

    # 2) replace the gen-invocation span (START .. END inclusive) via line indices
    lines = text.split("\n")
    starts = [i for i, l in enumerate(lines) if l == START_ANCHOR]
    ends = [i for i, l in enumerate(lines) if l == END_ANCHOR]
    if len(starts) != 1 or len(ends) != 1:
        sys.exit("ERROR: gen-block anchors not unique (start=%d, end=%d) -- source changed."
                 % (len(starts), len(ends)))
    s, e = starts[0], ends[0]
    if e < s:
        sys.exit("ERROR: gen-block END precedes START -- aborting.")
    lines[s:e + 1] = NEW_BLOCK.split("\n")
    text = "\n".join(lines)

    out = text.replace("\n", nl)
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(out)

    with io.open(path, "r", encoding="utf-8", newline="") as f:
        check = f.read()
    if check.count(MARKER) < 2 or "maxAttempts" not in check:
        sys.exit("ERROR: patch did not persist as expected -- inspect build.ps1.")
    print("[ok] patched: %s" % path)
    print("     -Generate / -All now re-roll up to -GenRetries times (default 2) on a FillError.")
    print("     Optional: add -GenBumpRegions to also bump num_regions +1 per retry.")


if __name__ == "__main__":
    main()
