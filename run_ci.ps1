<#
  run_ci.ps1  --  unified test gate for ER Archipelago (the "-Test command")
  ---------------------------------------------------------------------------
  Runs every automated gate from CONTRIBUTING.md in one command and reports a
  single PASS/FAIL:

    1. UNIT   python -m pytest worlds\eldenring\tests  (option matrix, slot_data
              contract, per-feature gen tests)
    2. FILL   run_fill_regression.ps1  (17 reproducer yamls vs baseline floors)
    3. FUZZ   gen_fuzz.ps1  (random option combinations -> clean gen or
              OptionError; the headline gate)
    4. CARGO  (opt-in, -Cargo) cargo test in from-software-archipelago-clients

  Steps run in cheap-first order and ALL steps run even after a failure (you
  want the full picture from one CI pass); the final exit code is non-zero if
  ANY step failed.

  USAGE (from the repo root, on Windows)
    .\run_ci.ps1                          # unit + fill + fuzz(25)
    .\run_ci.ps1 -FuzzCount 100           # heavier fuzz pass
    .\run_ci.ps1 -SkipFuzz                # quick pre-commit gate
    .\run_ci.ps1 -Cargo                   # include Rust client tests
    .\run_ci.ps1 -FuzzSeed 12345 -GenSeed 987   # reproduce a CI fuzz failure

  PREREQ: patch_generate_nopause_reapply.py applied after any AP re-checkout
  (the harnesses have a < NUL backstop, but the patch keeps logs clean).
#>
[CmdletBinding()]
param(
    [int]    $FuzzCount = 25,
    [long]   $FuzzSeed = 0,          # 0 = fresh (printed by gen_fuzz)
    [long]   $GenSeed = 0,           # 0 = fresh (printed by gen_fuzz)
    [int]    $FuzzTimeoutSec = 900,
    [switch] $SkipUnit,
    [switch] $SkipFill,
    [switch] $SkipFuzz,
    [switch] $Cargo                  # opt-in: Rust client tests (Windows toolchain)
)

$ErrorActionPreference = "Stop"
$Repo   = $PSScriptRoot
$ApDir  = Join-Path $Repo "Archipelago"
$Client = Join-Path $Repo "from-software-archipelago-clients"
$steps  = New-Object System.Collections.Generic.List[object]

function Step($m) { Write-Host "`n==== $m" -ForegroundColor Cyan }

function Invoke-CiStep([string]$name, [scriptblock]$body) {
    Step "CI STEP: $name"
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $code = 1
    try {
        & $body
        $code = if ($LASTEXITCODE -ne $null) { $LASTEXITCODE } else { 0 }
    } catch {
        Write-Host ("  step threw: {0}" -f $_.Exception.Message) -ForegroundColor Red
        $code = 1
    }
    $sw.Stop()
    $ok = ($code -eq 0)
    Write-Host ("  {0}: {1}  ({2:n0}s)" -f $name, $(if ($ok) {"PASS"} else {"FAIL (exit $code)"}), $sw.Elapsed.TotalSeconds) `
        -ForegroundColor $(if ($ok) {"Green"} else {"Red"})
    $steps.Add([pscustomobject]@{ step=$name; result=$(if ($ok) {"PASS"} else {"FAIL"}); seconds=[math]::Round($sw.Elapsed.TotalSeconds,0); exit=$code })
}

# ----- 1) apworld unit tests (cheapest, most specific) -------------------------
if (-not $SkipUnit) {
    Invoke-CiStep "UNIT (pytest worlds\eldenring\tests)" {
        Push-Location $ApDir
        try {
            $env:AP_NONINTERACTIVE = "1"
            python -m pytest "worlds\eldenring\tests" -q --tb=short
        } finally { Pop-Location }
    }
}

# ----- 2) fill regression (fixed reproducer seeds vs baseline floors) ----------
if (-not $SkipFill) {
    Invoke-CiStep "FILL (run_fill_regression.ps1)" {
        & (Join-Path $Repo "run_fill_regression.ps1")
    }
}

# ----- 3) yaml fuzz (the headline gate) -----------------------------------------
if (-not $SkipFuzz) {
    Invoke-CiStep "FUZZ (gen_fuzz.ps1 -Count $FuzzCount)" {
        $fa = @{ Count = $FuzzCount; TimeoutSec = $FuzzTimeoutSec; Tag = "ci" }
        if ($FuzzSeed -ne 0) { $fa.FuzzSeed = $FuzzSeed }
        if ($GenSeed -ne 0)  { $fa.GenSeed  = $GenSeed }
        & (Join-Path $Repo "gen_fuzz.ps1") @fa
    }
}

# ----- 4) rust client tests (opt-in) ---------------------------------------------
if ($Cargo) {
    Invoke-CiStep "CARGO (client tests)" {
        Push-Location $Client
        try { cargo test } finally { Pop-Location }
    }
}

# ----- verdict --------------------------------------------------------------------
Step "CI VERDICT"
$steps | Format-Table step, result, seconds -AutoSize | Out-Host
$failed = @($steps | Where-Object result -eq "FAIL")
if ($steps.Count -eq 0) {
    Write-Host "  nothing ran (every step skipped)." -ForegroundColor Yellow
    exit 2
}
if ($failed.Count -gt 0) {
    Write-Host ("  CI: FAIL -- {0} of {1} step(s) failed: {2}" -f $failed.Count, $steps.Count, (($failed | ForEach-Object step) -join "; ")) -ForegroundColor Red
    exit 1
}
Write-Host ("  CI: PASS -- all {0} step(s) green." -f $steps.Count) -ForegroundColor Green
exit 0
