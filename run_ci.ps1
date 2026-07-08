<#
  run_ci.ps1  --  unified test gate for ER Archipelago (the "-Test command")
  ---------------------------------------------------------------------------
  Runs every automated gate from CONTRIBUTING.md in one command and reports a
  single PASS/FAIL:

    1. UNIT   python -m pytest worlds\eldenring\tests + \test  (option matrix, slot_data
              contract, per-feature gen tests)
    2. FILL   run_fill_regression.ps1  (17 reproducer yamls vs baseline floors)
    3. DIVERSITY  run_region_diversity.ps1  (num_regions/chain fixed-seed roll
                  diversity gate, incl. the cave/torch bundles; -SkipDiversity)
    3b. GREENFIELD  greenfield unit tests + isolated gen (data-drift check, pure data
                  invariants, then AP WorldTestBase fill/goal/slot_data; -SkipGreenfield,
                  or -OnlyGreenfield to run just this gate)
    4. FUZZ   gen_fuzz.ps1  (random option combinations -> clean gen or
              OptionError). CRASH/HANG ALWAYS fail; FILLERROR is soft -- PASS iff no
              CRASH/HANG AND >= -FuzzPassPct% SUCCESS+REJECT (default 80%).
    5. PURE   cargo test -p er-logic -p er-codec -p er-semver (Windows-free crates;
              default-on, -SkipPure to skip; consumes the fixture UNIT regenerates)
    6. CARGO  (opt-in, -Cargo) full cargo test in from-software-archipelago-clients

  Steps run in cheap-first order and ALL steps run even after a failure (you
  want the full picture from one CI pass); the final exit code is non-zero if
  ANY step failed.

  USAGE (from the repo root, on Windows)
    .\run_ci.ps1                          # unit + fill + fuzz(25)
    .\run_ci.ps1 -FuzzCount 100           # heavier fuzz pass
    .\run_ci.ps1 -SkipFuzz                # quick pre-commit gate
    .\run_ci.ps1 -SkipDiversity           # skip the num_regions diversity gate
    .\run_ci.ps1 -OnlyGreenfield          # run ONLY the greenfield gate (skip everything else)
    .\run_ci.ps1 -SkipGreenfield          # skip the greenfield world tests + gen gate
    .\run_ci.ps1 -FuzzPassPct 100         # require a perfectly clean fuzz batch
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
    [int]    $FuzzPassPct = 80,      # FUZZ step passes at >= this SUCCESS+REJECT rate (default 80%)
    [switch] $SkipUnit,
    [switch] $SkipFill,
    [switch] $SkipDiversity,
    [switch] $SkipGreenfield,
    [switch] $OnlyGreenfield,      # run ONLY the greenfield gate (skip all other steps)
    [switch] $Full,               # opt out of the greenfield-only default: run the full legacy CI
    [switch] $SkipFuzz,
    [switch] $SkipPure,
    [switch] $Cargo                  # opt-in: Rust client tests (Windows toolchain)
)

$ErrorActionPreference = "Stop"

# Default to the greenfield-only gate: the matt-lineage world is retired for v0.2, so its
# unit/fill/diversity/fuzz/pure steps should not gate the greenfield release. Pass -Full to run
# the whole legacy CI (respecting any individual -Skip* flags).
if (-not $Full) { $OnlyGreenfield = $true }
# -OnlyGreenfield: run just the greenfield gate; force-skip every other step.
if ($OnlyGreenfield) {
    $SkipUnit = $true; $SkipFill = $true; $SkipDiversity = $true
    $SkipFuzz = $true; $SkipPure = $true; $Cargo = $false; $SkipGreenfield = $false
}
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
            # parallel across matrix classes (pip install pytest-xdist); exit 4 =
            # unrecognized -n (xdist missing) -> serial fallback with a hint.
            python -m pytest "worlds\eldenring\tests" "worlds\eldenring\test" -q --tb=short -n auto
            if ($LASTEXITCODE -eq 4) {
                Write-Host "  pytest-xdist not installed (pip install pytest-xdist) -- serial rerun" -ForegroundColor Yellow
                python -m pytest "worlds\eldenring\tests" "worlds\eldenring\test" -q --tb=short
            }
        } finally { Pop-Location }
    }
}

# ----- 1b) options wizard metadata drift -- TEMPORARILY REMOVED (2026-07-04, Alaric) --
# The WIZARD step (tools\check_options_metadata.ps1) is disabled for now. Restore by
# un-commenting when the options-metadata surface stabilizes.
# Invoke-CiStep "WIZARD (options metadata drift)" {
#     & (Join-Path $Repo "tools\check_options_metadata.ps1")
# }

# ----- 2) fill regression (fixed reproducer seeds vs baseline floors) ----------
if (-not $SkipFill) {
    Invoke-CiStep "FILL (run_fill_regression.ps1)" {
        & (Join-Path $Repo "run_fill_regression.ps1")
    }
}

# ----- 2b) num_regions region-diversity gate (fixed-seed roll-diversity tripwire) -
if (-not $SkipDiversity) {
    Invoke-CiStep "DIVERSITY (run_region_diversity.ps1)" {
        & (Join-Path $Repo "run_region_diversity.ps1")
    }
}

# ----- 2d) greenfield world (data-derived, matt-free): drift + unit tests + isolated gen -
if (-not $SkipGreenfield) {
    Invoke-CiStep "GREENFIELD (drift + unit tests + isolated gen)" {
        $gfDir  = Join-Path $Repo "greenfield"
        $dataPy = Join-Path $gfDir "eldenring_gf\data.py"
        # (a) DATA DRIFT: regenerate from the backbone (region_map.csv + grace anchors); fail if
        #     data.py or region_open_flags.py differ from what is committed. Compared line-ending-
        #     NORMALIZED: gen_data writes CRLF on Windows / LF elsewhere -- only content matters.
        $openPy = Join-Path $gfDir "eldenring_gf\region_open_flags.py"
        $gfNorm = { param($p) if (Test-Path $p) { [IO.File]::ReadAllText($p).Replace("`r","") } else { "" } }
        $beforeData = & $gfNorm $dataPy
        $beforeOpen = & $gfNorm $openPy
        python (Join-Path $gfDir "gen_data.py")
        if ($LASTEXITCODE -ne 0) { throw "GREENFIELD: gen_data.py failed (exit $LASTEXITCODE)" }
        if ((& $gfNorm $dataPy) -ne $beforeData) {
            throw "GREENFIELD: eldenring_gf\data.py is stale -- gen_data.py regenerated different data; commit it."
        }
        if ((& $gfNorm $openPy) -ne $beforeOpen) {
            throw "GREENFIELD: eldenring_gf\region_open_flags.py is stale -- regenerated different flags; commit it."
        }
        # (b) PURE UNIT: structural invariants on data.py (no AP import). Run as a DIRECT
        #     unittest script, NOT pytest -- pytest would import the parent eldenring_gf
        #     package, whose __init__ pulls in Archipelago BaseClasses, defeating the AP-free
        #     design (the file ends in unittest.main(), so it exits 0/1 for CI).
        python (Join-Path $gfDir "eldenring_gf\tests\test_gf_data.py")
        if ($LASTEXITCODE -ne 0) { throw "GREENFIELD: data-invariant unit tests failed (exit $LASTEXITCODE)" }
        # (c) ISOLATED GEN: install the world into Archipelago\worlds and gen against
        #     greenfield\players in isolation (also copies tests\ into the installed world).
        #     gen-greenfield.ps1 throws on a non-zero Generate.py exit (fill error / crash).
        & (Join-Path $gfDir "gen-greenfield.ps1") -Repo $Repo
        if ($LASTEXITCODE -ne 0) { throw "GREENFIELD: isolated gen failed (exit $LASTEXITCODE)" }
        # (d) WORLD UNIT: AP WorldTestBase suite (fill/reachability/goal + slot_data
        #     contract) against the freshly-installed world.
        Push-Location $ApDir
        try {
            python -m pytest "worlds\eldenring_gf\tests" -q --ignore="worlds\eldenring_gf\tests\test_gf_data.py"
            $gfWorldExit = $LASTEXITCODE
        } finally { Pop-Location }
        if ($gfWorldExit -ne 0) { throw "GREENFIELD: AP world unit tests failed (exit $gfWorldExit)" }
        $global:LASTEXITCODE = 0
    }
}

# ----- 2b) greenfield yaml fuzz (headline gate for greenfield: any option combo -> clean gen or a
#            graceful OptionError; a FillError/crash/hang is a reproducer failure). Portable scorer
#            greenfield\fuzz_gf.py. Skipped by -SkipGreenfield or -SkipFuzz. -----
if ((-not $SkipGreenfield) -and ((-not $SkipFuzz) -or $OnlyGreenfield)) {
    Invoke-CiStep "GREENFIELD-FUZZ (fuzz_gf.py -Count $FuzzCount, pass >= $FuzzPassPct%)" {
        python (Join-Path $Repo "greenfield\fuzz_gf.py") --count $FuzzCount --pass-pct $FuzzPassPct --ap $ApDir
        if ($LASTEXITCODE -ne 0) { throw "GREENFIELD-FUZZ: pass rate below $FuzzPassPct% -- see the printed reproducer yaml" }
        $global:LASTEXITCODE = 0
    }
}

# ----- 3) yaml fuzz (headline gate; PASS at >= $FuzzPassPct% SUCCESS+REJECT) -----
if (-not $SkipFuzz) {
    Invoke-CiStep "FUZZ (gen_fuzz.ps1 -Count $FuzzCount, pass >= $FuzzPassPct%)" {
        $fa = @{ Count = $FuzzCount; TimeoutSec = $FuzzTimeoutSec; Tag = "ci" }
        if ($FuzzSeed -ne 0) { $fa.FuzzSeed = $FuzzSeed }
        if ($GenSeed -ne 0)  { $fa.GenSeed  = $GenSeed }
        & (Join-Path $Repo "gen_fuzz.ps1") @fa
        # Score the freshest ci-tagged CSV gen_fuzz just wrote. The soft tolerance
        # applies to FILLERROR ONLY: any CRASH or HANG hard-fails the step (a stack
        # trace or a hang is never acceptable). FILLERROR is tolerated up to a
        # (100 - $FuzzPassPct)% budget -> PASS iff no CRASH/HANG AND
        # (SUCCESS+REJECT)/total >= $FuzzPassPct%.
        $csv = Get-ChildItem $Repo -Filter "genfuzz_ci_*.csv" |
               Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if (-not $csv) { throw "FUZZ: no genfuzz_ci_*.csv produced -- gen_fuzz.ps1 did not run" }
        $rows   = @(Import-Csv -LiteralPath $csv.FullName)
        $tot    = $rows.Count
        if ($tot -eq 0) { throw "FUZZ: zero cases scored in $($csv.Name)" }
        $nCrash = @($rows | Where-Object { $_.outcome -eq "CRASH" }).Count
        $nHang  = @($rows | Where-Object { $_.outcome -eq "HANG" }).Count
        $nFill  = @($rows | Where-Object { $_.outcome -eq "FILLERROR" }).Count
        $good   = @($rows | Where-Object { $_.outcome -eq "SUCCESS" -or $_.outcome -eq "REJECT" }).Count
        $pct    = [math]::Round(100.0 * $good / $tot, 1)
        $fuzzOk = (($nCrash + $nHang) -eq 0) -and ($pct -ge $FuzzPassPct)
        Write-Host ("  fuzz: {0}% clean ({1}/{2} SUCCESS+REJECT); FILLERROR {3}, CRASH {4}, HANG {5} -- FILLERROR budget <= {6}%" -f `
            $pct, $good, $tot, $nFill, $nCrash, $nHang, (100 - $FuzzPassPct)) `
            -ForegroundColor $(if ($fuzzOk) { "Green" } else { "Red" })
        if (($nCrash + $nHang) -gt 0) { throw ("FUZZ: {0} CRASH + {1} HANG -- always fail, regardless of the FILLERROR budget" -f $nCrash, $nHang) }
        if ($pct -lt $FuzzPassPct)    { throw ("FUZZ: {0}% clean below threshold {1}% (FILLERROR {2}/{3})" -f $pct, $FuzzPassPct, $nFill, $tot) }
        $global:LASTEXITCODE = 0   # no CRASH/HANG and FILLERROR within budget
    }
}

# ----- 4) rust pure-crate tests (host-safe, default-on) --------------------------
if (-not $SkipPure) {
    Invoke-CiStep "PURE (cargo test er-logic er-codec er-semver)" {
        Push-Location $Client
        try { cargo test -p er-logic -p er-codec -p er-semver } finally { Pop-Location }
    }
}

# ----- 5) rust client tests (opt-in) ---------------------------------------------
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
