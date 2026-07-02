<#
  gen_fuzz.ps1  --  random-YAML fuzz harness for ER Archipelago
  ---------------------------------------------------------------------------
  PURPOSE
    Tests the CONTRIBUTING headline gate: "flip any yaml option, in any
    combination, and get either a clean generation or a clear, actionable
    rejection -- never a stack trace, never a FillError, never a silent no-op."

    Complements gen_sweep.ps1 (random SEEDS x fixed yamls) by randomizing the
    YAML instead: emits N random-but-valid option-combination yamls via
    gen_fuzz_yamls.py, gens each one on a shared pinned seed, and classifies:

      SUCCESS    exit 0                                      -> gate PASS
      REJECT     OptionError raised (graceful, actionable)   -> gate PASS
      FILLERROR  FillError / unbeatable / no spots           -> gate FAIL
      HANG       exceeded -TimeoutSec, process killed        -> gate FAIL
      CRASH      any other traceback / non-zero exit         -> gate FAIL

    Every failing yaml is copied to gen-test\fuzz-failures\<ts>\ -- the yaml
    IS the reproducer (re-run it via -YamlDir with the same -GenSeed).

  USAGE (from the repo root, on Windows)
    .\gen_fuzz.ps1                                # 50 cases, fresh fuzz seed
    .\gen_fuzz.ps1 -Count 200 -Density 0.5        # bigger, denser combos
    .\gen_fuzz.ps1 -FuzzSeed 12345 -Count 50      # reproduce a whole batch
    .\gen_fuzz.ps1 -Full -Count 20                # every option set, 20 cases
    .\gen_fuzz.ps1 -YamlDir .\gen-test\fuzz-failures\20260702-101500 -GenSeed 987
                                                  # re-run archived reproducers
    .\gen_fuzz.ps1 -Pin @("enable_dlc=false")     # pin options across the batch

  NOTES
    - One PINNED gen seed shared by every case (printed + in the summary), so
      a failure reproduces from (yaml file, -GenSeed). Vary -GenSeed across
      batches; vary -FuzzSeed to explore new combos.
    - A world-side rejection only counts as REJECT if it raises OptionError.
      If a combo should be rejected, raise OptionError with both option names
      -- a bare Exception shows up here as CRASH, by design.
    - Sphere-shape checks (sphere-0 ballooning) are NOT wired yet; when the
      sphere dump lands in the sweep, add it here too (CONTRIBUTING wants it).
  OUTPUTS (repo root)
    genfuzz_<tag>_<ts>.csv / .md   per-case rows + summary w/ failure modes
    per-case generate_*.log (+ gendiag_*.txt) for failures
#>
[CmdletBinding()]
param(
    [int]      $Count = 50,          # number of fuzz yamls (ignored with -YamlDir)
    [long]     $FuzzSeed = 0,        # yaml-batch seed; 0 = roll fresh (printed)
    [double]   $Density = 0.4,       # per-option inclusion probability
    [switch]   $Full,                # set every option in every case
    [long]     $GenSeed = 0,         # shared Generate.py seed; 0 = roll fresh (printed)
    [int]      $TimeoutSec = 900,    # per-gen timeout -> HANG
    [string]   $YamlDir,             # skip emission; fuzz these existing yamls (reproduce mode)
    [string[]] $Pin,                 # passed through as --pin key=value (repeatable)
    [string]   $Tag = "fuzz",
    [switch]   $KeepZips,
    [switch]   $KeepLogs             # keep generate_*.log for SUCCESS/REJECT too (default: failures only)
)

$ErrorActionPreference = "Stop"
$Repo    = $PSScriptRoot
$ApDir   = Join-Path $Repo "Archipelago"
$GenPy   = Join-Path $ApDir "Generate.py"
$OutDir  = Join-Path $ApDir "output"
$Players = Join-Path $ApDir "Players"
$DlcDiag = Join-Path $Repo "dlcdiag.py"
$PreGen  = Join-Path $Repo "pregen.py"
$Emitter = Join-Path $Repo "gen_fuzz_yamls.py"
$LOGIC_RE  = 'FillError|appears as unbeatable|Could not access required locations|No more spots to place'
$REJECT_RE = 'OptionError'

if (-not (Test-Path $GenPy))   { throw "Generate.py not found at $GenPy -- run from the repo root." }
if (-not (Test-Path $Emitter)) { throw "gen_fuzz_yamls.py not found at $Emitter." }

function Step($m) { Write-Host "`n==== $m" -ForegroundColor Cyan }

# ----- pregen guard (stale .pyc / stranded-yaml-option check) -----------------
if (Test-Path $PreGen) { Step "pregen guard"; python $PreGen | Write-Host }

# ----- emit (or reuse) the fuzz yamls -----------------------------------------
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
if ($YamlDir) {
    $FuzzDir = (Resolve-Path $YamlDir).Path
    Step "reproduce mode: fuzzing existing yamls in $FuzzDir"
} else {
    $FuzzDir = Join-Path $Repo ("gen-test\fuzz-yamls-$stamp")
    Step "emitting $Count fuzz yamls -> $FuzzDir"
    $emitArgs = @("--count", $Count, "--out", $FuzzDir, "--density", $Density)
    if ($FuzzSeed -ne 0) { $emitArgs += @("--fuzz-seed", $FuzzSeed) }
    if ($Full)           { $emitArgs += "--full" }
    foreach ($p in ($Pin | Where-Object { $_ })) { $emitArgs += @("--pin", $p) }
    python $Emitter @emitArgs | Tee-Object -Variable emitOut | Write-Host
    if ($LASTEXITCODE -ne 0) { throw "gen_fuzz_yamls.py failed (exit $LASTEXITCODE)." }
    $fsLine = $emitOut | Select-String 'fuzz-seed\s*:\s*(\d+)' | Select-Object -First 1
    if ($fsLine) { $FuzzSeed = [long]$fsLine.Matches[0].Groups[1].Value }
}
$yamls = Get-ChildItem $FuzzDir -Filter *.yaml | Sort-Object Name
if (-not $yamls) { throw "no .yaml files in $FuzzDir." }

# manifest (options per case) for the failure-correlation table
$manifest = @{}
$manPath = Join-Path $FuzzDir "manifest.csv"
if (Test-Path $manPath) {
    Import-Csv $manPath | ForEach-Object { $manifest[$_.file] = $_.options_set }
}

# ----- advisory lint pass ------------------------------------------------------
$Lint = Join-Path $Repo "er_yaml_lint.py"
if (Test-Path $Lint) {
    Step "advisory lint pass (rule hits here should surface as REJECTs below)"
    python $Lint $FuzzDir | Select-String '\[ERROR|\[WARN|error\(s\)' | Select-Object -First 25 | ForEach-Object { Write-Host ("  " + $_.Line) -ForegroundColor DarkGray }
}

# ----- shared pinned gen seed --------------------------------------------------
if ($GenSeed -eq 0) {
    $rng = [System.Random]::new()
    $GenSeed = [long]([math]::Abs($rng.Next())) * 1000000007L + [long][math]::Abs($rng.Next())
}
Write-Host ("gen seed (shared, pinned): {0}" -f $GenSeed) -ForegroundColor Yellow

# ----- one case's gen run with timeout ------------------------------------------
function Invoke-FuzzRun($yamlPath, $idx, $n) {
    $yName = Split-Path $yamlPath -Leaf
    Write-Host ("  [{0}/{1}] {2}" -f $idx, $n, $yName) -ForegroundColor White
    $ts      = Get-Date -Format "yyyyMMdd-HHmmss-fff"
    $genLog  = Join-Path $Repo "generate_$ts.log"
    $genDiag = Join-Path $Repo "gendiag_$ts.txt"

    Get-ChildItem $Players -Filter *.yaml -ErrorAction SilentlyContinue | Remove-Item -Force
    Copy-Item -LiteralPath $yamlPath -Destination (Join-Path $Players $yName) -Force

    $env:AP_NONINTERACTIVE = "1"
    # < NUL: Generate.py's atexit input("Press enter to close.") fires on ERROR exits.
    # The AP_NONINTERACTIVE guard lives in a LOCAL patch to Generate.py that an AP
    # re-checkout silently drops (patch_generate_nopause_reapply.py restores it), so
    # feed EOF on stdin as well -- input() then raises EOFError instead of blocking.
    $cmdLine = "python Generate.py --seed $GenSeed < NUL > `"$genLog`" 2>&1"
    $p = Start-Process cmd -ArgumentList "/c", $cmdLine -WorkingDirectory $ApDir -WindowStyle Hidden -PassThru
    # Poll in short slices instead of one blocking WaitForExit: Ctrl+C can't interrupt
    # a blocking .NET wait (forcing a window-kill that SKIPS the finally and strands
    # the staged yaml in Players\); between 2s waits the pipeline stop is processed
    # and the finally below restores Players\.
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSec)
    $done = $false
    while (-not $done -and [DateTime]::UtcNow -lt $deadline) { $done = $p.WaitForExit(2000) }
    if (-not $done) {
        try { & taskkill /PID $p.Id /T /F 2>$null | Out-Null } catch {}
        $genExit = -999
    } else { $genExit = $p.ExitCode }

    if ($done -and (Test-Path $DlcDiag)) { python $DlcDiag $genLog $genDiag $genExit | Out-Null }

    $seedName = $null
    $mn = Select-String -Path $genLog -Pattern 'AP_(\d+)\.zip' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($mn) { $seedName = $mn.Matches[0].Groups[1].Value }

    $detail = ""
    if (-not $done) {
        $outcome = "HANG"; $detail = "exceeded ${TimeoutSec}s, killed"
    } elseif ($genExit -eq 0) {
        $outcome = "SUCCESS"
    } elseif (Select-String -Path $genLog -Pattern $REJECT_RE -Quiet -ErrorAction SilentlyContinue) {
        $outcome = "REJECT"
        $ln = Select-String -Path $genLog -Pattern 'OptionError' -ErrorAction SilentlyContinue | Select-Object -Last 1
        if ($ln) { $detail = $ln.Line.Trim() }
    } elseif (Select-String -Path $genLog -Pattern $LOGIC_RE -Quiet -ErrorAction SilentlyContinue) {
        $outcome = "FILLERROR"
        $ln = Select-String -Path $genLog -Pattern $LOGIC_RE -ErrorAction SilentlyContinue | Select-Object -Last 1
        if ($ln) { $detail = $ln.Line.Trim() }
    } else {
        $outcome = "CRASH"
        # skip the EOFError/atexit noise from the < NUL stdin redirect -- report the REAL error
        $ln = Select-String -Path $genLog -Pattern 'Error|Exception|Traceback' -ErrorAction SilentlyContinue |
              Where-Object { $_.Line -notmatch 'EOFError|atexit|Press enter' } | Select-Object -Last 1
        $detail = if ($ln) { $ln.Line.Trim() } else { "non-zero exit $genExit, no recognizable error line" }
    }

    $color = switch ($outcome) { "SUCCESS" {"Green"} "REJECT" {"DarkGreen"} "FILLERROR" {"Yellow"} default {"Red"} }
    Write-Host ("      -> {0}  {1}" -f $outcome, $detail) -ForegroundColor $color

    $isFail = $outcome -in @("FILLERROR","CRASH","HANG")
    if (-not $KeepZips -and $seedName) {
        foreach ($ext in '.zip','.apsave','.archipelago') {
            $f = Join-Path $OutDir ("AP_{0}{1}" -f $seedName, $ext)
            if (Test-Path $f) { Remove-Item -LiteralPath $f -Force -ErrorAction SilentlyContinue }
        }
    }
    if (-not $isFail -and -not $KeepLogs) {
        Remove-Item -LiteralPath $genLog -Force -ErrorAction SilentlyContinue
        if (Test-Path $genDiag) { Remove-Item -LiteralPath $genDiag -Force -ErrorAction SilentlyContinue }
    }

    return [pscustomobject]@{
        n=$idx; yaml=$yName; outcome=$outcome; fail=$isFail; detail=$detail; exit=$genExit
        log=$(if ($isFail -or $KeepLogs) { Split-Path $genLog -Leaf } else { "" })
        options=$(if ($manifest.ContainsKey($yName)) { $manifest[$yName] } else { "" })
    }
}

# ----- back up Players\, run every case, restore --------------------------------
# If a previous run died hard (window killed mid-hang), its staged fuzz yaml is
# still in Players\ -- purge it BEFORE the backup, or it gets adopted as one of
# the user's yamls and re-restored by every future run.
$leftover = @(Get-ChildItem $Players -Filter "ER-fuzz-*.yaml" -ErrorAction SilentlyContinue)
if ($leftover.Count -gt 0) {
    Write-Warning ("removing {0} stranded fuzz yaml(s) from Players\ (a previous run died before restore): {1}" -f `
        $leftover.Count, (($leftover | ForEach-Object Name) -join ", "))
    $leftover | Remove-Item -Force
}
$yamlBackup = @{}
Get-ChildItem $Players -Filter *.yaml -ErrorAction SilentlyContinue | ForEach-Object {
    $yamlBackup[$_.FullName] = Get-Content -LiteralPath $_.FullName -Raw
}
$results = New-Object System.Collections.Generic.List[object]
try {
    Step ("fuzzing {0} yaml(s), shared gen seed {1}" -f $yamls.Count, $GenSeed)
    $idx = 0
    foreach ($y in $yamls) {
        $idx++
        $results.Add((Invoke-FuzzRun $y.FullName $idx $yamls.Count))
    }
} finally {
    Get-ChildItem $Players -Filter *.yaml -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
    foreach ($yf in @($yamlBackup.Keys)) { Set-Content -LiteralPath $yf -Value $yamlBackup[$yf] -NoNewline }
    Write-Host "restored original Players\ yaml(s)." -ForegroundColor DarkGray
}

# ----- archive failing yamls as reproducers --------------------------------------
$fails = @($results | Where-Object fail)
$failDir = $null
if ($fails.Count -gt 0) {
    $failDir = Join-Path $Repo ("gen-test\fuzz-failures\$stamp")
    New-Item -ItemType Directory -Path $failDir -Force | Out-Null
    foreach ($f in $fails) {
        Copy-Item -LiteralPath (Join-Path $FuzzDir $f.yaml) -Destination (Join-Path $failDir $f.yaml) -Force
    }
    if (Test-Path $manPath) { Copy-Item -LiteralPath $manPath -Destination (Join-Path $failDir "manifest.csv") -Force }
    Set-Content -LiteralPath (Join-Path $failDir "REPRODUCE.txt") -Value @(
        "reproduce: .\gen_fuzz.ps1 -YamlDir `"$failDir`" -GenSeed $GenSeed",
        "fuzz-seed: $FuzzSeed   gen-seed: $GenSeed   batch: $stamp"
    )
}

# ----- summary -------------------------------------------------------------------
$csvPath = Join-Path $Repo "genfuzz_${Tag}_$stamp.csv"
$mdPath  = Join-Path $Repo "genfuzz_${Tag}_$stamp.md"
$results | Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding UTF8

$nOK   = @($results | Where-Object outcome -eq "SUCCESS").Count
$nRej  = @($results | Where-Object outcome -eq "REJECT").Count
$nFill = @($results | Where-Object outcome -eq "FILLERROR").Count
$nCrsh = @($results | Where-Object outcome -eq "CRASH").Count
$nHang = @($results | Where-Object outcome -eq "HANG").Count
$gate  = if ($fails.Count -eq 0) { "PASS" } else { "FAIL" }

$md = New-Object System.Collections.Generic.List[string]
$md.Add("# gen fuzz -- $Tag -- $stamp")
$md.Add("")
$md.Add("fuzz-seed: ``$FuzzSeed``   gen-seed (shared): ``$GenSeed``   cases: $($results.Count)   yamls: ``$FuzzDir``")
$md.Add("")
$md.Add("| headline gate | SUCCESS | REJECT | FILLERROR | CRASH | HANG |")
$md.Add("|---|---:|---:|---:|---:|---:|")
$md.Add("| **$gate** | $nOK | $nRej | $nFill | $nCrsh | $nHang |")
$md.Add("")

Step "RESULT"
Write-Host ("  headline gate: {0}   (SUCCESS {1} / REJECT {2} / FILLERROR {3} / CRASH {4} / HANG {5})" -f `
    $gate, $nOK, $nRej, $nFill, $nCrsh, $nHang) -ForegroundColor $(if ($gate -eq "PASS") {"Green"} else {"Red"})

if ($fails.Count -gt 0) {
    $md.Add("## failure modes (normalized)")
    $md.Add("")
    $groups = $fails | Group-Object { ($_.outcome + " " + ($_.detail -replace '\d+',' N ')).Trim() } | Sort-Object Count -Descending
    foreach ($g in $groups) {
        $sample = ($g.Group | Select-Object -First 1)
        Write-Host ("    [{0}x] {1}: {2}" -f $g.Count, $sample.outcome, $sample.detail) -ForegroundColor Yellow
        Write-Host ("          yamls: {0}" -f (($g.Group | ForEach-Object yaml) -join ", ")) -ForegroundColor DarkYellow
        $md.Add(("- **{0}x {1}** -- {2}" -f $g.Count, $sample.outcome, $sample.detail))
        $md.Add(("  - yamls: ``{0}``" -f (($g.Group | ForEach-Object yaml) -join "``, ``")))
    }
    $md.Add("")

    # option-frequency correlation: which options appear in failing yamls more than overall
    if ($manifest.Count -gt 0) {
        function Get-KeyCounts($rows) {
            $h = @{}
            foreach ($r in $rows) {
                foreach ($tok in ($r.options -split '\s+' | Where-Object { $_ })) {
                    $k = ($tok -split '=', 2)[0]
                    $h[$k] = ([int]$h[$k]) + 1
                }
            }
            return $h
        }
        $allCounts  = Get-KeyCounts $results
        $failCounts = Get-KeyCounts $fails
        $md.Add("## option frequency in failures vs overall (triage signal, not proof)")
        $md.Add("")
        $md.Add("| option | in failures | in all cases | fail-share |")
        $md.Add("|---|---:|---:|---:|")
        Step "OPTION FREQUENCY IN FAILURES (top 15)"
        $rows = foreach ($k in $failCounts.Keys) {
            $fShare = [math]::Round(100.0 * $failCounts[$k] / [math]::Max(1, $allCounts[$k]), 0)
            [pscustomobject]@{ opt=$k; inFail=$failCounts[$k]; inAll=$allCounts[$k]; share=$fShare }
        }
        $rows | Sort-Object share, inFail -Descending | Select-Object -First 15 | ForEach-Object {
            Write-Host ("    {0,-36} {1,3} / {2,-3} ({3,3}% of its cases failed)" -f $_.opt, $_.inFail, $_.inAll, $_.share)
            $md.Add(("| {0} | {1} | {2} | {3}% |" -f $_.opt, $_.inFail, $_.inAll, $_.share))
        }
        $md.Add("")
    }
    $md.Add("reproducers archived: ``$failDir`` (re-run: ``.\gen_fuzz.ps1 -YamlDir `"$failDir`" -GenSeed $GenSeed``)")
    Write-Host ("  reproducers -> {0}" -f $failDir) -ForegroundColor Yellow
} else {
    $md.Add("_No FILLERROR / CRASH / HANG across $($results.Count) random option combinations._")
}

# graceful-reject sample lines (are the messages actually actionable?)
$rejects = @($results | Where-Object outcome -eq "REJECT")
if ($rejects.Count -gt 0) {
    $md.Add("")
    $md.Add("## REJECT messages (spot-check: a player must be able to ACT on these)")
    $md.Add("")
    $rejects | Group-Object { ($_.detail -replace '\d+',' N ').Trim() } | Sort-Object Count -Descending | ForEach-Object {
        $md.Add(("- **{0}x** -- {1}" -f $_.Count, ($_.Group | Select-Object -First 1).detail))
    }
}

Set-Content -LiteralPath $mdPath -Value ($md -join "`r`n") -Encoding UTF8
Write-Host ""
Write-Host ("  CSV -> {0}" -f $csvPath) -ForegroundColor Green
Write-Host ("  MD  -> {0}" -f $mdPath)  -ForegroundColor Green

# CI contract (run_ci.ps1): non-zero exit iff the headline gate failed.
if ($fails.Count -gt 0) { exit 1 } else { exit 0 }
