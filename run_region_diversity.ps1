<#
  run_region_diversity.ps1 -- num_regions/chain region-diversity gate (2026-07-02).

  Alaric's 100%-green gate: sweeps gen-test\numregions-chain-diversity-yamls (nrchain-4/6/8)
  on FIXED seeds (deterministic -- a red here is a regression, never dice) and asserts:

    1. every config generates at 100% (no floors, no canaries);
    2. structural keeps at 100%: Altus Plateau / Leyndell, Royal Capital / Roundtable Hold;
    3. Limgrave kept ZERO times -- pool+chain excludes it from the roll (this doubles as proof
       the pool-only rune scope actually engaged; regions-mode force-kept Limgrave);
    4. every rollable middle region kept at least once across the sweep;
    5. every chain lock appears at least once as link-0 (roll diversity, not just gen success).

  Region/lock lists mirror region_spine.SPINE middles (steps 2-8; Altus forced separately).
  Runs one gen_sweep job per config in parallel (same pattern as run_fill_regression.ps1).

  USAGE:  .\run_region_diversity.ps1            # fixed 16 seeds x 3 configs
          .\run_region_diversity.ps1 -Seeds 123,456   # explicit seeds (repro)
#>
[CmdletBinding()]
param(
    [long[]]  $Seeds,
    [string]  $Tag = "nrdiv",
    [switch]  $Serial
)

$ErrorActionPreference = "Stop"
$Repo     = $PSScriptRoot
$Suite    = Join-Path $Repo "gen-test\numregions-chain-diversity-yamls"
$GenSweep = Join-Path $Repo "gen_sweep.ps1"
if (-not (Test-Path $GenSweep)) { throw "gen_sweep.ps1 not found ($GenSweep) -- run from the repo root." }
if (-not (Test-Path $Suite))    { throw "suite folder not found: $Suite" }

[long[]] $FixedSeeds = @(
    1000000000000000001L, 1000000000000000002L, 1000000000000000003L, 1000000000000000004L,
    1000000000000000005L, 1000000000000000006L, 1000000000000000007L, 1000000000000000008L,
    1000000000000000009L, 1000000000000000010L, 1000000000000000011L, 1000000000000000012L,
    1000000000000000013L, 1000000000000000014L, 1000000000000000015L, 1000000000000000016L
)
if (-not ($Seeds -and $Seeds.Count)) { $Seeds = $FixedSeeds }

# region_spine.SPINE middles (steps 2-8). Altus is forced by the pool scope, so it is asserted
# structural; the other six are the ROLLABLE set. Update alongside region_spine.py.
$RollableMiddles = @("Weeping Peninsula", "Stormveil Castle", "Liurnia of The Lakes",
                     "Caelid", "Dragonbarrow", "Mt. Gelmir")
$RollableLocks   = @("Weeping Lock", "Stormveil Lock", "Liurnia Lock",
                     "Caelid Lock", "Dragonbarrow Lock", "Mt. Gelmir Lock")
$Structural      = @("Altus Plateau", "Leyndell, Royal Capital", "Roundtable Hold")

Write-Host ("==== region-diversity gate -- {0} fixed seeds x nrchain configs" -f $Seeds.Count) -ForegroundColor Cyan

# ----- sweep (parallel per config; -Serial for one call with visible output) -----
$t0 = Get-Date
$rows = @(); $mds = @()
$yamls = @(Get-ChildItem $Suite -Filter *.yaml | Sort-Object Name)
if (-not $yamls.Count) { throw "no yamls in $Suite" }
if ($Serial) {
    & $GenSweep -Yaml $Suite -Seeds $Seeds -Tag $Tag
    $csvs = @(Get-ChildItem $Repo -Filter "gensweep_${Tag}_*.csv" | Where-Object { $_.LastWriteTime -gt $t0 })
    $mds  = @(Get-ChildItem $Repo -Filter "gensweep_${Tag}_*.md"  | Where-Object { $_.LastWriteTime -gt $t0 })
} else {
    $jobs = @(); $qi = 0
    foreach ($y in $yamls) {
        $qi++
        $jp = @{ Yaml = $y.FullName; Seeds = $Seeds; Tag = ("{0}p{1}" -f $Tag, $qi) }
        $jobs += Start-Job -ScriptBlock {
            param($gs, $ht)
            & $gs @ht *> $null
        } -ArgumentList $GenSweep, $jp
    }
    $jobs | Wait-Job | Out-Null
    $jobs | ForEach-Object { Receive-Job $_ -ErrorAction SilentlyContinue | Out-Null; Remove-Job $_ -Force }
    $csvs = @(Get-ChildItem $Repo -Filter "gensweep_${Tag}p*_*.csv" | Where-Object { $_.LastWriteTime -gt $t0 })
    $mds  = @(Get-ChildItem $Repo -Filter "gensweep_${Tag}p*_*.md"  | Where-Object { $_.LastWriteTime -gt $t0 })
}
if ($csvs.Count -lt $yamls.Count) { throw ("only {0}/{1} configs produced CSVs -- rerun with -Serial to debug" -f $csvs.Count, $yamls.Count) }
$rows = @($csvs | ForEach-Object { Import-Csv -LiteralPath $_.FullName })

$violations = New-Object System.Collections.Generic.List[string]

# ----- 1) 100% gen success per config ------------------------------------------
foreach ($g in ($rows | Group-Object config)) {
    $bad = @($g.Group | Where-Object outcome -ne "SUCCESS")
    if ($bad.Count) {
        $seedsBad = ($bad | ForEach-Object { $_.seed }) -join ", "
        $violations.Add(("{0}: {1}/{2} seeds failed (reproduce: -Seeds {3})" -f $g.Name, $bad.Count, $g.Group.Count, $seedsBad))
    }
}
$totalRuns = $rows.Count

# ----- parse the kept-region + link-0 tables out of the MDs -----------------------
$kept  = @{}
$link0 = @{}
foreach ($md in $mds) {
    $section = ""
    foreach ($line in (Get-Content -LiteralPath $md.FullName)) {
        if ($line -match "^## regions kept")       { $section = "kept";  continue }
        if ($line -match "^## chain link-0")       { $section = "link0"; continue }
        if ($line -match "^## ")                   { $section = "";      continue }
        if ($section -and $line -match "^\|\s*(.+?)\s*\|\s*(\d+)\s*\|") {
            $name = $Matches[1]; $n = [int]$Matches[2]
            if ($name -in @("region", "link-0 lock") -or $name -match "^-+$") { continue }
            if ($section -eq "kept")  { $kept[$name]  = [int]($kept[$name])  + $n }
            if ($section -eq "link0") { $link0[$name] = [int]($link0[$name]) + $n }
        }
    }
}
if (-not $kept.Count) { throw "no kept-region tables parsed from the sweep MDs -- gen_sweep format change?" }

# ----- 2) structural at 100% ------------------------------------------------------
foreach ($r in $Structural) {
    $n = [int]($kept[$r])
    if ($n -ne $totalRuns) { $violations.Add(("structural region '{0}' kept {1}/{2}" -f $r, $n, $totalRuns)) }
}
# ----- 3) Limgrave never kept (pool+chain roll exclusion) --------------------------
$lim = [int]($kept["Limgrave"])
if ($lim -ne 0) { $violations.Add(("Limgrave kept {0}x -- pool+chain must exclude it (is the pool scope engaged?)" -f $lim)) }
# ----- 4) every rollable middle appears ---------------------------------------------
foreach ($r in $RollableMiddles) {
    if ([int]($kept[$r]) -lt 1) { $violations.Add(("rollable region NEVER kept across {0} seeds: {1}" -f $totalRuns, $r)) }
}
# ----- 5) every lock appears as link-0 ------------------------------------------------
foreach ($l in $RollableLocks) {
    if ([int]($link0[$l]) -lt 1) { $violations.Add(("lock NEVER rolled as link-0: {0}" -f $l)) }
}

# ----- report -------------------------------------------------------------------------
Write-Host "`n  kept-region spread (rollable middles):" -ForegroundColor Cyan
foreach ($r in $RollableMiddles) { Write-Host ("    {0,-22} {1,4}x" -f $r, [int]($kept[$r])) }
Write-Host "  link-0 spread:" -ForegroundColor Cyan
foreach ($l in $RollableLocks)   { Write-Host ("    {0,-22} {1,4}x" -f $l, [int]($link0[$l])) }

if ($violations.Count) {
    Write-Host "`n==== DIVERSITY: FAIL" -ForegroundColor Red
    foreach ($v in $violations) { Write-Host ("  " + $v) -ForegroundColor Red }
    exit 1
}
Write-Host ("`n==== DIVERSITY: PASS -- {0} runs, 100% gen, full roll spread" -f $totalRuns) -ForegroundColor Green
exit 0
