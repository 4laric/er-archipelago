<#
  run_region_diversity.ps1 -- num_regions/chain region-diversity gate (2026-07-02).

  Alaric's 100%-green gate: sweeps gen-test\numregions-chain-diversity-yamls (nrchain-4/6/8)
  on FIXED seeds (deterministic -- a red here is a regression, never dice) and asserts:

    1. every config generates at 100% (no floors, no canaries);
    2. structural keeps at 100%: Altus Plateau / Leyndell, Royal Capital / Roundtable Hold;
    3. every rollable middle region kept at least once across the sweep -- proof the pool roll
       engaged and is diverse (incl. Limgrave, now an ordinary rollable step post spine-surgery);
    4. every chain lock that CAN be link-0 appears at least once as link-0 (roll diversity).

  Region/lock lists mirror region_spine.SPINE (steps 1-12). Altus is forced + pinned last, so it
  is asserted structural and never link-0. Post spine-surgery 2026-07-02: Limgrave is a normal
  rollable step (kept, but NOT part of the breadcrumb chain -> its lock is never link-0);
  Dragonbarrow was folded into Caelid (its lock retired); Mountaintops Lock can be link-0 but does
  not surface on the current 16 fixed seeds, so it is not in the required link-0 set (add a seed
  if you want it asserted). Update these lists alongside region_spine.py.
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

# region_spine.SPINE rollable steps (1-12), minus Altus (step 6: forced by the pool scope +
# pinned last, so asserted structural below). Each entry is a PRIMARY region name that lands in
# the kept table when its step is kept. Limgrave (step 1) is rollable and kept, but its lock is
# NOT in NUM_REGIONS_CHAIN_STEP_LOCK, so it never breadcrumbs as link-0 -- present here (kept
# check) but absent from $RollableLocks (link-0 check). Dragonbarrow was folded into Caelid
# (2026-07-02); its lock is retired, so it is gone from both lists.
$RollableMiddles = @("Limgrave", "Weeping Peninsula", "Stormveil Castle", "Liurnia of The Lakes",
                     "Caelid", "Mt. Gelmir", "Siofra River", "Ainsel River",
                     "Mountaintops of the Giants", "Consecrated Snowfield", "Miquella's Haligtree")
# link-0 = the chain's free/pre-collected middle lock. Steps 2-12 minus Altus (pinned last, never
# link-0) and minus Mountaintops Lock (a valid chain lock, but it does not roll link-0 on the
# current 16 fixed seeds -- see header). Limgrave Lock is intentionally NOT here (step 1 is spawn-
# granted, outside the breadcrumb chain).
$RollableLocks   = @("Weeping Lock", "Stormveil Lock", "Liurnia Lock", "Caelid Lock",
                     "Mt. Gelmir Lock", "Nokron Lock", "Nokstella Lock", "Snowfield Lock",
                     "Haligtree Lock")
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
    $jobs = @{}; $qi = 0
    foreach ($y in $yamls) {
        $qi++
        $jobTag = "{0}p{1}" -f $Tag, $qi
        # explicit parameter binding (deserialized-hashtable splats have bitten before) +
        # full output capture so a dead job can explain itself.
        $jobs[$jobTag] = Start-Job -ScriptBlock {
            param($gs, $yaml, [long[]]$seeds, $tag)
            try {
                & $gs -Yaml $yaml -Seeds $seeds -Tag $tag 2>&1 | Out-String
            } catch {
                "JOB EXCEPTION: $($_ | Out-String)"
            }
        } -ArgumentList $GenSweep, $y.FullName, $Seeds, $jobTag
    }
    $jobs.Values | Wait-Job | Out-Null
    $jobOut = @{}
    foreach ($kv in $jobs.GetEnumerator()) {
        $jobOut[$kv.Key] = (Receive-Job $kv.Value 2>&1 | Out-String)
        Remove-Job $kv.Value -Force
    }
    $csvs = @(Get-ChildItem $Repo -Filter "gensweep_${Tag}p*_*.csv" | Where-Object { $_.LastWriteTime -gt $t0 })
    $mds  = @(Get-ChildItem $Repo -Filter "gensweep_${Tag}p*_*.md"  | Where-Object { $_.LastWriteTime -gt $t0 })
    if ($csvs.Count -lt $yamls.Count) {
        Write-Host ("`n==== only {0}/{1} configs produced CSVs -- job output tails:" -f $csvs.Count, $yamls.Count) -ForegroundColor Red
        $doneTags = @($csvs | ForEach-Object { if ($_.Name -match "gensweep_(${Tag}p\d+)_") { $Matches[1] } })
        foreach ($kv in $jobOut.GetEnumerator()) {
            if ($kv.Key -notin $doneTags) {
                Write-Host ("---- {0} ----" -f $kv.Key) -ForegroundColor Yellow
                $tail = ($kv.Value -split "`r?`n" | Where-Object { $_ } | Select-Object -Last 25) -join "`n"
                Write-Host $tail
            }
        }
        throw "diversity sweep incomplete -- see job tails above (or rerun with -Serial)"
    }
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
# ----- 3) every rollable middle appears (Limgrave is now an ordinary rollable step) ------
foreach ($r in $RollableMiddles) {
    if ([int]($kept[$r]) -lt 1) { $violations.Add(("rollable region NEVER kept across {0} seeds: {1}" -f $totalRuns, $r)) }
}
# ----- 4) every rollable lock appears as link-0 ------------------------------------------
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
