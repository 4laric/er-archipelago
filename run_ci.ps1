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
    3a. FRESHNESS  gen-input stamp gate (tools\gen_manifest.py --verify): the committed
                  greenfield generated data must match a hash of the gen inputs on disk. STALE
                  = FAIL; artifacts absent (can't recompute) = PASS with a SKIP note. Runs BEFORE
                  GREENFIELD, which regenerates (and would rewrite the stamp, masking staleness).
    3b. GREENFIELD  greenfield unit tests + isolated gen (data-drift check, pure data
                  invariants, then AP WorldTestBase fill/goal/slot_data; -SkipGreenfield,
                  or -OnlyGreenfield to run just this gate)
    4. FUZZ   gen_fuzz.ps1  (random option combinations -> clean gen or
              OptionError). CRASH/HANG ALWAYS fail; FILLERROR is soft -- PASS iff no
              CRASH/HANG AND >= -FuzzPassPct% SUCCESS+REJECT (default 100%).
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
    .\run_ci.ps1 -FuzzPassPct 90          # allow a rougher batch (crashes still fail)
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
    [int]    $FuzzPassPct = 100,     # FUZZ passes at >= this SUCCESS+REJECT rate. 100 since
                                     # 2026-07-24 (Alaric): the greenfield world holds a clean
                                     # batch; the matt-based world never did. A crash or
                                     # FillError fails regardless of this number.
    [switch] $SkipUnit,
    [switch] $SkipZipGen,          # skip the zipped-apworld (custom_worlds) generation smoke
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

# ----- 0) WHICH CLIENT ARE WE GATING AGAINST? -----------------------------------
# A THIRD answer, and it is deliberate -- say it out loud rather than let a reader assume this matches
# CI. Three resolutions exist in this repo and they differ:
#   * tests.yaml `generators`        -> the PINNED gitlink (the pairing a release bundle ships).
#   * tests.yaml `client-main-drift` -> client `main` (has the client run ahead of the pin?).
#   * this script and greenfield\ci-linux.sh -> WHATEVER IS ON DISK in $Client, working-tree edits and
#     all. Correct for a dev box (you are usually editing both halves at once, and a script that
#     checked anything out would clobber that), but it means PASS here says nothing about the pin.
# Neither local script runs gen_contract / gen_region_locks, so neither can produce the cross-repo
# staleness signal at all; only the `generators` job can. What this block does is stop the ambiguity
# being silent. It never fails -- it prints, so the number is on the transcript.
Step "CLIENT PIN (which client this run is gating against)"
if (Test-Path (Join-Path $Client ".git")) {
    $cHead = (& git -C $Client rev-parse HEAD 2>$null)
    $cPin  = (& git -C $Repo ls-tree HEAD from-software-archipelago-clients 2>$null)
    if ($cPin) { $cPin = ($cPin -split '\s+')[2] }
    $cDirty = (& git -C $Client status --porcelain 2>$null)
    Write-Host ("  on disk : {0}{1}" -f $cHead, $(if ($cDirty) { "  (DIRTY working tree)" } else { "" }))
    Write-Host ("  gitlink : {0}" -f $(if ($cPin) { $cPin } else { "<none>" }))
    if ($cPin -and ($cHead -ne $cPin)) {
        Write-Host "  NOTE: on-disk client != the gitlink. The cross-side gates and the PURE/CARGO steps read" -ForegroundColor Yellow
        Write-Host "        the ON-DISK tree; CI's generators job reads the gitlink. Not a failure here." -ForegroundColor Yellow
    }
} else {
    Write-Host "  submodule not checked out -- the cross-side gates will SKIP and gate NOTHING." -ForegroundColor Yellow
}
$global:LASTEXITCODE = 0

# ----- 1) apworld unit tests (cheapest, most specific) -------------------------
# THE HARNESS IS tools\gf_test.py, and it is the SAME one CI runs. This step used to Push-Location into
# $ApDir -- i.e. <repo>\Archipelago, whatever that happened to be -- and pytest there. On 2026-07-13 that
# directory was a clone of fswap/Archipelago (Bedrock's fork, kept to play his seeds), so this gate was
# testing the apworld against a DIFFERENT Archipelago than CI: 661 tests collected vs CI's 686, a
# different Fill.py, different fill spheres, and a test that was green on CI failed here. The result was
# not wrong, it was an answer to a different question -- which is worse, because it looks like an answer.
#
# gf_test.py pins .ap-version, installs into its OWN .ap-test\ checkout (your Archipelago\ is never
# touched or consulted -- keep whatever fork you like there), and REFUSES to run against a non-upstream
# remote rather than hand back a number that means nothing.
if (-not $SkipUnit) {
    Invoke-CiStep "UNIT (tools\gf_test.py -- pinned upstream AP)" {
        python (Join-Path $Repo "tools\gf_test.py") --tb=short
        if ($LASTEXITCODE -ne 0) { throw "GREENFIELD: AP world unit tests failed (exit $LASTEXITCODE)" }
    }
}

# ----- 1a) zipped-apworld generation smoke (the custom_worlds crash class) -----
# The UNIT step above installs and tests the world UNPACKED. A released .apworld is a ZIP, and code
# that reads a bundled data file via open(dirname(__file__)/name) works unpacked but raises inside the
# archive -- invisible to every unpacked test. That shipped the 2026-07-19 hotfix: coverage.py's
# open() on check_lots_table.json failed inside the zip, the coverage gate saw an empty table and
# raised CoverageError at post_fill, and EVERY custom_worlds (Nexus) generation died. This step zips
# the world CI just validated into custom_worlds\ and runs one generation from it, so a non-zip-safe
# resource read fails HERE, before release, instead of on a user's machine. Runs after UNIT (which
# leaves the installed world in .ap-test\) so it zips exactly those bits.
if (-not $SkipZipGen) {
    Invoke-CiStep "ZIP-GEN (custom_worlds generation smoke)" {
        python (Join-Path $Repo "tools\gf_zip_gen_smoke.py")
        if ($LASTEXITCODE -ne 0) { throw "GREENFIELD: zipped-apworld generation failed (exit $LASTEXITCODE) -- a bundled-resource read is not zip-safe (the custom_worlds crash class)" }
    }
}

# ----- 1b) options wizard metadata drift ---------------------------------------
# RE-ARMED 2026-07-29. This step was commented out 2026-07-04 "until the options-metadata surface
# stabilizes", and the surface then did the opposite: the disable window ate a four-commit drift
# (3381174..9ce2476) in which the JSON was regenerated but the copy inlined in wizard/wizard.html
# was not, so the wizard page silently lost dungeon_sweep, pool_builder_intensity and
# region_grace_unlock. Nothing released was affected -- wizard/ is not staged into the zip -- but
# the reason nobody noticed for 36 hours is that the only instrument was switched off. Churn is
# exactly when this gate pays. The half-applying default that caused it is fixed at the source
# (dump_options_metadata.py now emits all three artifacts on a plain run).
Invoke-CiStep "WIZARD (options metadata drift)" {
    & (Join-Path $Repo "tools\check_options_metadata.ps1")
}

# ----- 1b2) the wizard's seed-size math, JS vs Python --------------------------
# wizard/region-census.json is gated by test_gf_region_census; the JS that reads it is not gated by
# any Python test, and the JS is what the player sees. Differential run under node. Exit 4 = node
# absent = SKIP (reported, not silently passed).
Invoke-CiStep "WIZARD-CENSUS-JS (seed-size math: JS vs Python)" {
    python (Join-Path $Repo "tools\check_wizard_census_js.py")
    if ($LASTEXITCODE -eq 4) { Write-Host "  SKIP: node not on PATH -- the wizard's JS math is ungated on this box." }
    elseif ($LASTEXITCODE -ne 0) { throw "WIZARD-CENSUS-JS: the wizard's JS seed-size math disagrees with the Python reference" }
}

# ----- 1c) release notes for the open version ----------------------------------
# CONTRIBUTING rule 14. v0.3.0 shipped 2026-08-01; by the next morning main carried five more
# player-visible fixes (two off Nexus bug reports) with no v0.3.1 changelog section and no blurb,
# and no BLURB-v0.3.0.md either -- the blurb series had stopped at v0.2.18 and nothing said so.
# AP-free and import-free (APWORLD_VERSION is parsed out of contract.py textually), so it costs
# nothing and runs anywhere. Carries a documented ratchet: v0.3.0 is exempt from the BLURB check
# only. Nothing may be added to that set.
Invoke-CiStep "RELEASE-NOTES (changelog + blurb for APWORLD_VERSION)" {
    python (Join-Path $Repo "tools\check_release_notes.py")
    if ($LASTEXITCODE -ne 0) { throw "RELEASE-NOTES: the open version has no changelog section and/or no blurb (CONTRIBUTING rule 14)" }
}

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

# ----- 2c) gen-input stamp freshness (SPEC-gen-input-hash-gate-20260710.md) ---------------
# Recompute the gen-input content hash and compare it to the _GEN_STAMP the generator wrote into
# greenfield\eldenring. This is the invariant that retires the "NEEDS WINDOWS REGEN" marker: a
# committed generated tree that no longer matches its inputs FAILS CI here.
# MUST run before the GREENFIELD step, which re-runs gen_data.py (rewriting the stamp, which would
# make a stale tree self-heal and pass unnoticed).
#   exit 0 = fresh -> PASS
#   exit 3 = STALE -> FAIL (regen: .\build.ps1 -Greenfield)
#   exit 4 = cannot verify (elden_ring_artifacts absent -- licensing-restricted, not in git) -> SKIP,
#            reported PASS so an artifact-less CI box is not blocked. Mirrors the ci-linux DRIFT skip.
if (-not $SkipGreenfield) {
    Invoke-CiStep "FRESHNESS (gen-input stamp vs greenfield generated data)" {
        $manifest = Join-Path $Repo "tools\gen_manifest.py"
        $stamp    = Join-Path $Repo "greenfield\eldenring\_gen_stamp.json"
        if (-not (Test-Path $manifest)) { throw "FRESHNESS: tools\gen_manifest.py not found -- cannot verify gen-input freshness" }
        if (-not (Test-Path $stamp))    { throw "FRESHNESS: greenfield\eldenring\_gen_stamp.json missing -- data was generated by a pre-stamp gen_data.py. Run: .\build.ps1 -Greenfield" }
        python $manifest --verify $stamp
        $stampExit = $LASTEXITCODE
        if ($stampExit -eq 4) {
            Write-Host "  SKIP: elden_ring_artifacts absent (licensing-restricted, not in git) -- cannot recompute the input hash on this box." -ForegroundColor Yellow
        } elseif ($stampExit -ne 0) {
            throw ("FRESHNESS: greenfield generated data is STALE vs the gen inputs on disk (exit {0}) -- regenerate and commit: .\build.ps1 -Greenfield" -f $stampExit)
        } else {
            Write-Host "  gen-input stamp FRESH -- committed greenfield data matches the inputs on disk." -ForegroundColor Green
        }
        $global:LASTEXITCODE = 0
    }
}

# ----- 2c2) ARTIFACT-DERIVED TABLE DRIFT: the gates only a box with elden_ring_artifacts can run --
# check_lots_table.json is the STATIC vanilla-suppression table, derived from ItemLotParam. It needs
# elden_ring_artifacts, so the GitHub runner CANNOT gate it -- this is the sighted gate, and the only
# one that can see it go stale.
#
# !! THE TRACKER HALF OF THIS STEP IS GONE (2026-07-28), and deliberately so. It used to run
# tools\gen_location_regions.py --check against the client's tracker_regions.rs, a cross-repo
# generated table. That table is DELETED: the tracker's region model now ships in slot_data
# (locationRegions / regionCoarseKeys), because a table generated from the full data.LOCATIONS
# described the DEFAULT seed and was quietly wrong for every num_regions seed -- a corpus fact
# standing in for a seed fact. There is nothing left to drift, so the gate is removed rather than
# left to fail looking for a file that no longer exists.
if (-not $SkipGreenfield) {
    Invoke-CiStep "ARTIFACT TABLE DRIFT (check_lots_table.json vs the params)" {
        $lotGen = Join-Path $Repo "tools\gen_check_lots_table.py"
        if (Test-Path $lotGen) {
            & python $lotGen --check
            if ($LASTEXITCODE -ne 0) {
                throw "CHECK-LOTS TABLE: check_lots_table.json is STALE vs the params. Regenerate and commit: python tools\gen_check_lots_table.py"
            }
            Write-Host "  check_lots_table.json FRESH -- the vanilla-suppression table matches the params." -ForegroundColor Green
        } else {
            Write-Host "  SKIP: tools\gen_check_lots_table.py not found." -ForegroundColor Yellow
        }
        $global:LASTEXITCODE = 0
    }
}

# ----- 2d) greenfield world (data-derived, matt-free): drift + unit tests + isolated gen -
if (-not $SkipGreenfield) {
    Invoke-CiStep "GREENFIELD (drift + unit tests + isolated gen)" {
        $gfDir  = Join-Path $Repo "greenfield"
        $dataPy = Join-Path $gfDir "eldenring\data.py"
        # (a) DATA DRIFT: regenerate from the backbone (region_map.csv + grace anchors); fail if
        #     data.py or region_open_flags.py differ from what is committed. Compared line-ending-
        #     NORMALIZED: gen_data writes CRLF on Windows / LF elsewhere -- only content matters.
        $openPy = Join-Path $gfDir "eldenring\region_open_flags.py"
        $gfNorm = { param($p) if (Test-Path $p) { [IO.File]::ReadAllText($p).Replace("`r","") } else { "" } }
        $beforeData = & $gfNorm $dataPy
        $beforeOpen = & $gfNorm $openPy
        python (Join-Path $gfDir "gen_data.py")
        if ($LASTEXITCODE -ne 0) { throw "GREENFIELD: gen_data.py failed (exit $LASTEXITCODE)" }
        if ((& $gfNorm $dataPy) -ne $beforeData) {
            throw "GREENFIELD: eldenring\data.py is stale -- gen_data.py regenerated different data; commit it."
        }
        if ((& $gfNorm $openPy) -ne $beforeOpen) {
            throw "GREENFIELD: eldenring\region_open_flags.py is stale -- regenerated different flags; commit it."
        }
        # (b) PURE UNIT: structural invariants on data.py (no AP import). Run as a DIRECT
        #     unittest script, NOT pytest -- pytest would import the parent eldenring
        #     package, whose __init__ pulls in Archipelago BaseClasses, defeating the AP-free
        #     design (the file ends in unittest.main(), so it exits 0/1 for CI).
        python (Join-Path $gfDir "eldenring\tests\test_gf_data.py")
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
            python -m pytest "worlds\eldenring\tests" -q --ignore="worlds\eldenring\tests\test_gf_data.py"
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
