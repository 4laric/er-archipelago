<#
  run_fill_regression.ps1  --  fill-issue REGRESSION GATE for ER Archipelago
  ---------------------------------------------------------------------------
  Drives gen_sweep.ps1 over gen-test\fill-regression-yamls (a curated set of
  configs, one per historically-recorded fill bug) against ONE shared seed
  list, then compares every config's pass-rate to a recorded floor in
  baseline.json and EXITS NON-ZERO if any config regressed. CI-friendly.

  Each yaml pins a combination that used to FillError / "No more spots" /
  "appears as unbeatable" / strand a region. As long as every config stays at
  or above its floor, the fill fixes are holding.

  USAGE (repo root, Windows)
    .\run_fill_regression.ps1                  # fixed reproducer seeds (deterministic gate)
    .\run_fill_regression.ps1 -Count 25        # 25 random shared seeds (volume hunt)
    .\run_fill_regression.ps1 -Seeds 123,456   # explicit seeds (reproduce a report)
    .\run_fill_regression.ps1 -Apworld .\eldenring.apworld   # host-faithful (packaged world)
    .\run_fill_regression.ps1 -UpdateBaseline  # rewrite baseline.json from THIS run's rates
    .\run_fill_regression.ps1 -Margin 5        # tolerate 5 percentage points under each floor

  WHAT COUNTS AS A FAIL
    A config whose pass-rate < (floor - Margin). A CONFIG/syntax error shows as a
    near-0% pass (gen_sweep aborts that config after one seed) and therefore fails
    the gate too. The seeds that hit each failure are printed so you can re-feed
    them with -Seeds after a fix.

  NOTE  gen_sweep itself does the staging/seed-pinning/classification; this is a
        thin pass/fail verdict on top of its CSV. Source-tree mode by default;
        pass -Apworld to gate what a host actually loads.
#>
[CmdletBinding()]
param(
    [int]      $Count = 0,           # >0 = that many random shared seeds; 0 = fixed reproducer seeds
    [long[]]   $Seeds,               # explicit seeds (overrides -Count and the fixed set)
    [string]   $Tag = "fillreg",     # gen_sweep summary tag (also the CSV/MD filename stem)
    [string]   $Apworld,             # gate the PACKAGED .apworld instead of the source tree
    [int]      $Margin = 0,          # percentage points of slack allowed under each floor
    [switch]   $UpdateBaseline,      # write observed rates back to baseline.json (calibration)
    [switch]   $KeepZips,
    [switch]   $Serial           # legacy single gen_sweep call (no parallel jobs)
)

$ErrorActionPreference = "Stop"
$Repo     = $PSScriptRoot
$Suite    = Join-Path $Repo "gen-test\fill-regression-yamls"
$GenSweep = Join-Path $Repo "gen_sweep.ps1"
$BaseJson = Join-Path $Suite "baseline.json"

if (-not (Test-Path $GenSweep)) { throw "gen_sweep.ps1 not found next to this script ($GenSweep). Run from the repo root." }
if (-not (Test-Path $Suite))    { throw "suite folder not found: $Suite" }

# Fixed reproducer seeds -> deterministic gate (same seeds every run). Swap in
# known-bad seeds (from a gensweep MD failure list) via -Seeds to lock a fix.
[long[]] $FixedSeeds = @(
    1111111111111111111L, 2222222222222222222L, 3333333333333333333L, 4444444444444444444L,
    5555555555555555555L, 6666666666666666666L, 7777777777777777777L, 8888888888888888888L
)

# ----- build the gen_sweep call (splat) --------------------------------------
$p = @{ Yaml = $Suite; Tag = $Tag }
if ($KeepZips) { $p.KeepZips = $true }
if ($Apworld)  { $p.Apworld  = (Resolve-Path $Apworld).Path }
if ($Seeds -and $Seeds.Count) { $p.Seeds = $Seeds; $mode = "explicit ($($Seeds.Count) seeds)" }
elseif ($Count -gt 0)         { $p.Count = $Count; $mode = "$Count random shared seeds" }
else                          { $p.Seeds = $FixedSeeds; $mode = "fixed reproducer seeds ($($FixedSeeds.Count))" }

Write-Host "==== fill regression gate -- mode: $mode" -ForegroundColor Cyan

# ----- run the sweep: parallel per-config jobs (default) or -Serial legacy -----
$rows = @()
$srcNote = ""
if ($Serial) {
    & $GenSweep @p
    $csv = Get-ChildItem $Repo -Filter "gensweep_${Tag}_*.csv" -ErrorAction SilentlyContinue |
           Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $csv) { throw "no gensweep_${Tag}_*.csv was produced -- did gen_sweep fail before the summary?" }
    $rows = Import-Csv -LiteralPath $csv.FullName
    $srcNote = $csv.FullName
} else {
    $t0 = Get-Date
    $yamls = @(Get-ChildItem $Suite -Filter *.yaml | Sort-Object Name)
    if (-not $yamls.Count) { throw "no yamls in $Suite" }
    $throttle = [Math]::Max(1, [Math]::Min(4, [Environment]::ProcessorCount - 1))
    Write-Host ("  parallel: {0} configs, {1} concurrent jobs (use -Serial for the legacy path)" -f $yamls.Count, $throttle)
    $jobs = @(); $qi = 0
    foreach ($y in $yamls) {
        while (@($jobs | Where-Object State -eq "Running").Count -ge $throttle) { Start-Sleep -Milliseconds 500 }
        $qi++
        $jp = @{} + $p
        $jp.Yaml = $y.FullName
        $jp.Tag  = "{0}p{1}" -f $Tag, $qi
        $jobs += Start-Job -ScriptBlock {
            param($gs, $ht)
            & $gs @ht *> $null
        } -ArgumentList $GenSweep, $jp
    }
    $jobs | Wait-Job | Out-Null
    $jobs | ForEach-Object { Receive-Job $_ -ErrorAction SilentlyContinue | Out-Null; Remove-Job $_ -Force }
    $csvs = @(Get-ChildItem $Repo -Filter "gensweep_${Tag}p*_*.csv" -ErrorAction SilentlyContinue |
              Where-Object { $_.LastWriteTime -gt $t0 } | Sort-Object Name)
    if (-not $csvs.Count) { throw "no per-config gensweep CSVs produced -- rerun with -Serial to see gen_sweep output" }
    if ($csvs.Count -lt $yamls.Count) {
        Write-Host ("  WARNING: {0}/{1} configs produced a CSV -- a job may have died; rerun with -Serial to debug" -f $csvs.Count, $yamls.Count) -ForegroundColor Yellow
    }
    $rows = @($csvs | ForEach-Object { Import-Csv -LiteralPath $_.FullName })
    $srcNote = ($csvs | ForEach-Object { $_.Name }) -join ", "
}

# ----- floors ----------------------------------------------------------------
$floors = @{}
if (Test-Path $BaseJson) {
    $bj = Get-Content -LiteralPath $BaseJson -Raw | ConvertFrom-Json
    foreach ($prop in $bj.PSObject.Properties) {
        if ($prop.Name -eq "_comment") { continue }
        $floors[$prop.Name] = [double]$prop.Value
    }
}

# ----- verdict per config ----------------------------------------------------
$verdicts = foreach ($g in ($rows | Group-Object config)) {
    $t    = $g.Group.Count
    $pass = ($g.Group | Where-Object outcome -eq "SUCCESS").Count
    $rate = if ($t) { [math]::Round(100.0 * $pass / $t, 1) } else { 0 }
    $floor = if ($floors.ContainsKey($g.Name)) { $floors[$g.Name] } else { 100 }
    $eff   = [math]::Max(0, $floor - $Margin)
    $ok    = $rate -ge $eff
    [pscustomobject]@{
        config  = $g.Name; runs = $t; pass = $pass; rate = $rate; floor = $floor
        verdict = $(if ($ok) { "OK" } else { "REGRESSED" })
    }
}
$verdicts = $verdicts | Sort-Object verdict, config   # REGRESSED sorts before OK

Write-Host "`n==== VERDICT (floor from baseline.json; margin $Margin)" -ForegroundColor Cyan
$verdicts | Format-Table config, runs, pass, @{n='pass%';e={$_.rate}}, @{n='floor%';e={$_.floor}}, verdict -AutoSize | Out-Host

$regressed = @($verdicts | Where-Object verdict -eq "REGRESSED")
foreach ($r in $regressed) {
    $seeds = ($rows | Where-Object { $_.config -eq $r.config -and $_.outcome -ne "SUCCESS" } |
              ForEach-Object { $_.seed }) -join ", "
    Write-Host ("  {0}: {1}% < floor {2}% (margin {3})  reproduce: -Seeds {4}" -f `
        $r.config, $r.rate, $r.floor, $Margin, $seeds) -ForegroundColor Red
}

# ----- optional calibration --------------------------------------------------
if ($UpdateBaseline) {
    $obj = [ordered]@{ "_comment" = "Auto-written by run_fill_regression.ps1 -UpdateBaseline. Floors = observed pass-rates from that run; subtract a margin by hand if you want headroom." }
    foreach ($v in ($verdicts | Sort-Object config)) { $obj[$v.config] = $v.rate }
    ($obj | ConvertTo-Json) | Set-Content -LiteralPath $BaseJson -Encoding UTF8
    Write-Host "`n  baseline.json updated from this run's rates -> $BaseJson" -ForegroundColor Yellow
}

Write-Host ""
Write-Host ("  source CSV(s) -> {0}" -f $srcNote) -ForegroundColor DarkGray
if ($regressed.Count -gt 0) {
    Write-Host ("  GATE: FAIL -- {0} config(s) regressed." -f $regressed.Count) -ForegroundColor Red
    exit 1
} else {
    Write-Host "  GATE: PASS -- every config at or above its floor." -ForegroundColor Green
    exit 0
}
