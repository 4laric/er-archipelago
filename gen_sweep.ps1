<#
  gen_sweep.ps1  --  seed-sweep gen-test harness for ER Archipelago
  ---------------------------------------------------------------------------
  PURPOSE
    Hunt INTERMITTENT (seed-dependent) gen-logic bugs, and compare configs.
    Runs Generate.py many times -- each on a pinned --seed -- WITHOUT
    bake/serve/deploy, classifies every run (SUCCESS / logic-FillError /
    config-error), and tallies the failure modes so you can see which recur
    and get reproducer seeds.

    With -Yaml you can sweep SEVERAL config yamls against the SAME seed list in
    one run and compare their pass-rates side by side (e.g. num_regions 4 vs 5
    vs 6) -- a fair A/B because every config faces identical seeds.

    Gen-only counterpart to build.ps1 -LoopTest (which BAKES) and a superset of
    -Generate's single retry loop (which stops at the first pass and discards
    the failures you actually want to study).

  WHY PINNED SEEDS
    Generate.py picks a fresh random seed each run, which is why these bugs feel
    "intermittent". This harness generates the seeds ITSELF and passes --seed,
    so every run -- and the whole sweep -- is reproducible. The summary lists
    the exact seeds that hit each failure; re-feed them with -Seeds to confirm a
    fix (regression mode).

  USAGE (from the repo root, on Windows)
    .\gen_sweep.ps1                              # 25 random seeds, current Players\ yaml
    .\gen_sweep.ps1 -Count 60                     # 60 seeds
    .\gen_sweep.ps1 -Yaml .\EldenRing-godrick-curated-RUN.yaml -Count 40
    .\gen_sweep.ps1 -Yaml .\sweep-configs\ -Count 40      # every *.yaml in the folder, shared seeds
    .\gen_sweep.ps1 -Yaml .\a.yaml,.\b.yaml,.\c.yaml -Count 40   # explicit list of configs
    .\gen_sweep.ps1 -Seeds 26199700892360198662,123,456  # re-run specific seeds (regression)
    .\gen_sweep.ps1 -Count 40 -Tag numreg -KeepZips
    .\gen_sweep.ps1 -Apworld .\eldenring.apworld -Count 80   # sweep the PACKAGED apworld (host-faithful)

  -Yaml accepts: a single file, a directory (-> all *.yaml in it), or a
  comma-separated list of files/dirs. Omit it to sweep whatever is in Players\.
  Players\ is backed up before staging and restored afterward (try/finally).

  OUTPUTS (repo root)
    gensweep_<tag>_<ts>.csv   one row per (config,seed): config, seed, seedname, outcome, detail, ...
    gensweep_<tag>_<ts>.md    summary: per-config pass-rate comparison + failure modes w/ seeds
    per-seed generate_*.log + gendiag_*.txt (same format build.ps1 emits)

  NOTES
    - Logic failures = FillError / "appears as unbeatable" / "Could not access
      required locations" / "No more spots to place". A non-zero exit WITHOUT
      one of those is a CONFIG/syntax error -- same every seed, so that config
      is aborted after the first seed (override with -DontStopOnConfigError).
    - Determinism is relative to the apworld SOURCE. Edit the world and the same
      seed can behave differently -- that's the point (verify a fix vs. the
      recorded failing seeds).
#>
[CmdletBinding()]
param(
    [int]      $Count = 25,                 # number of random seeds (ignored if -Seeds given)
    [long[]]   $Seeds,                      # explicit seeds to test (reproduce / regress)
    [string[]] $Yaml,                       # config yaml(s): file, dir, or list. Omit = current Players\
    [string]   $Tag = "sweep",              # label for the summary filenames
    [switch]   $KeepZips,                   # keep each run's output AP_*.zip (default: delete)
    [switch]   $DontStopOnConfigError,      # keep going even on a non-FillError (config/syntax) failure
    [string]   $Apworld                     # sweep the PACKAGED .apworld (what a host runs), not the source tree
)

$ErrorActionPreference = "Stop"
$Repo    = $PSScriptRoot
$ApDir   = Join-Path $Repo "Archipelago"
$GenPy   = Join-Path $ApDir "Generate.py"
$OutDir  = Join-Path $ApDir "output"
$Players = Join-Path $ApDir "Players"
$DlcDiag = Join-Path $Repo "dlcdiag.py"
$PreGen  = Join-Path $Repo "pregen.py"
$LOGIC_RE = 'FillError|appears as unbeatable|Could not access required locations|No more spots to place'

if (-not (Test-Path $GenPy)) { throw "Generate.py not found at $GenPy -- run from the repo root." }

function Step($m) { Write-Host "`n==== $m" -ForegroundColor Cyan }

# ----- resolve the config list (files / dirs / current Players) --------------
$SENTINEL = "(current Players\)"
$configList = New-Object System.Collections.Generic.List[string]
if ($Yaml -and $Yaml.Count) {
    foreach ($y in $Yaml) {
        $rp = (Resolve-Path $y).Path
        if (Test-Path $rp -PathType Container) {
            Get-ChildItem $rp -Filter *.yaml | Sort-Object Name | ForEach-Object { $configList.Add($_.FullName) }
        } else { $configList.Add($rp) }
    }
    if ($configList.Count -eq 0) { throw "-Yaml matched no .yaml files." }
} else {
    $configList.Add($SENTINEL)
}

# ----- shared seed list (built once; same seeds for every config) ------------
if ($Seeds -and $Seeds.Count -gt 0) {
    $seedList = $Seeds
    Write-Host ("Regression mode: {0} explicit seed(s)." -f $seedList.Count) -ForegroundColor Yellow
} else {
    $rng = [System.Random]::new()
    $seedList = 1..$Count | ForEach-Object {
        [long]([math]::Abs($rng.Next())) * 1000000007L + [long][math]::Abs($rng.Next())
    }
    Write-Host ("Random mode: {0} pinned seeds (shared across all configs; reproducible via -Seeds)." -f $seedList.Count) -ForegroundColor Yellow
}
Write-Host ("Configs to sweep: {0}" -f $configList.Count) -ForegroundColor Yellow

# ----- pregen guard once: invalidate stale eldenring .pyc (source mode only) -
if (-not $Apworld -and (Test-Path $PreGen)) { Step "pregen guard (stale .pyc / stranded-yaml-option check)"; python $PreGen | Write-Host }

# ----- one seed's gen run; returns a result row ------------------------------
function Invoke-SeedRun($configName, $seed, $idx, $n) {
    Write-Host ("    [{0}/{1}] seed {2}" -f $idx, $n, $seed) -ForegroundColor White
    $ts      = Get-Date -Format "yyyyMMdd-HHmmss-fff"
    $genLog  = Join-Path $Repo "generate_$ts.log"
    $genDiag = Join-Path $Repo "gendiag_$ts.txt"

    Push-Location $ApDir
    try {
        $env:AP_NONINTERACTIVE = "1"   # suppress Generate.py's atexit "Press enter to close." pause
        cmd /c "python Generate.py --seed $seed > `"$genLog`" 2>&1"
        $genExit = $LASTEXITCODE
    } finally { Pop-Location }

    if (Test-Path $DlcDiag) { python $DlcDiag $genLog $genDiag $genExit | Out-Null }

    # seed_name = the AP zip basename (≠ the internal seed). Parse from the log.
    $seedName = $null
    $mn = Select-String -Path $genLog -Pattern 'AP_(\d+)\.zip' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($mn) { $seedName = $mn.Matches[0].Groups[1].Value }

    $isLogic = Select-String -Path $genLog -Pattern $LOGIC_RE -Quiet -ErrorAction SilentlyContinue
    if ($genExit -eq 0) {
        $outcome = "SUCCESS"; $detail = ""
        $raised = Select-String -Path $genLog -Pattern 'raised to \d+' -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($raised) { $detail = $raised.Line.Trim() }
    }
    elseif ($isLogic) {
        $outcome = "FILLERROR"; $detail = ""
        if (Test-Path $genDiag) {
            $miss = Select-String -Path $genDiag -Pattern '^MISSING\s*:' -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($miss -and $miss.Line -notmatch 'none found') { $detail = ($miss.Line -replace '^MISSING\s*:\s*','').Trim() }
        }
        if (-not $detail) {
            $ln = Select-String -Path $genLog -Pattern $LOGIC_RE -ErrorAction SilentlyContinue | Select-Object -Last 1
            if ($ln) { $detail = $ln.Line.Trim() }
        }
    }
    else {
        $outcome = "CONFIGERROR"
        $ln = Select-String -Path $genLog -Pattern 'Error|Exception|Traceback' -ErrorAction SilentlyContinue | Select-Object -Last 1
        $detail = if ($ln) { $ln.Line.Trim() } else { "non-zero exit $genExit, no recognizable error line" }
    }

    Write-Host ("        -> {0}  {1}" -f $outcome, $detail) -ForegroundColor $(switch ($outcome) { "SUCCESS" {"Green"} "FILLERROR" {"Yellow"} default {"Red"} })

    if (-not $KeepZips -and $seedName) {
        foreach ($ext in '.zip','.apsave','.archipelago') {
            $f = Join-Path $OutDir ("AP_{0}{1}" -f $seedName, $ext)
            if (Test-Path $f) { Remove-Item -LiteralPath $f -Force -ErrorAction SilentlyContinue }
        }
    }

    return [pscustomobject]@{
        config=$configName; n=$idx; seed=$seed; seedname=$seedName; outcome=$outcome;
        detail=$detail; exit=$genExit; log=(Split-Path $genLog -Leaf); diag=(Split-Path $genDiag -Leaf)
    }
}

# ----- back up Players\ once (only when we stage configs) --------------------
$staging   = ($configList[0] -ne $SENTINEL)
$yamlBackup = @{}
if ($staging) {
    Get-ChildItem $Players -Filter *.yaml -ErrorAction SilentlyContinue | ForEach-Object {
        $yamlBackup[$_.FullName] = Get-Content -LiteralPath $_.FullName -Raw
    }
}

# ----- optional: swap the source-tree world for the PACKAGED apworld ---------
# A host installs your eldenring.apworld; your -Generate reads the worlds\eldenring
# source. To test what the host actually runs, hide the source dir and load the
# apworld from custom_worlds\. Restored in the finally (even on error; a leftover
# aside from a crashed run is auto-recovered before any new swap).
$apAside = $null; $apInstalled = $null; $sweptAgainst = "source tree (worlds\eldenring)"
$srcWorld = Join-Path $ApDir "worlds\eldenring"
function Restore-Apworld {
    if ($apInstalled -and (Test-Path $apInstalled)) { Remove-Item -LiteralPath $apInstalled -Force -ErrorAction SilentlyContinue }
    if ($apAside -and (Test-Path $apAside) -and -not (Test-Path $srcWorld)) { Rename-Item -LiteralPath $apAside -NewName "eldenring" }
}
if ($Apworld) {
    $ApwPath = (Resolve-Path $Apworld).Path
    Step "Apworld mode: validate + install $(Split-Path $ApwPath -Leaf) (host-faithful sweep)"
    Add-Type -AssemblyName System.IO.Compression.FileSystem | Out-Null
    $manifestTxt = $null
    try {
        $zr = [System.IO.Compression.ZipFile]::OpenRead($ApwPath)
        $ents = @($zr.Entries.FullName)
        $me = $zr.Entries | Where-Object { $_.FullName -like '*archipelago.json' } | Select-Object -First 1
        if ($me) { $sr = New-Object System.IO.StreamReader($me.Open()); $manifestTxt = $sr.ReadToEnd(); $sr.Dispose() }
        $zr.Dispose()
    } catch { throw "'$ApwPath' is not a readable .apworld zip ($_). Rebuild it with build.ps1 -Apworld." }
    if (-not ($ents -contains 'eldenring/__init__.py')) { throw "apworld is missing eldenring/__init__.py -- packaging is broken. Rebuild with build.ps1 -Apworld." }
    # AP looks for *archipelago.json* (NOT manifest.json). The zip-read path indexes
    # manifest['game'] and manifest['compatible_version'] directly -- both must exist
    # or the host's load raises (0.6.6 warns + still loads; 0.7.0 rejects).
    if (-not $manifestTxt) {
        Write-Warning "apworld has no archipelago.json -- AP errors on load (0.6.6 warns + loads; 0.7.0 rejects). Add worlds\eldenring\archipelago.json and rebuild."
    } else {
        $mj = $null; try { $mj = $manifestTxt | ConvertFrom-Json } catch { Write-Warning "  archipelago.json is not valid JSON: $_" }
        if ($mj) {
            if (-not $mj.game) { Write-Warning "  archipelago.json missing 'game' -- AP read raises KeyError." }
            if ($null -eq $mj.compatible_version) { Write-Warning "  archipelago.json missing 'compatible_version' -- hand-zipped apworlds need it (AP read indexes manifest['compatible_version'])." }
            if ($mj.game -and $null -ne $mj.compatible_version) { Write-Host ("  manifest ok: game='{0}' compatible_version={1} min_ap={2}" -f $mj.game, $mj.compatible_version, $mj.minimum_ap_version) -ForegroundColor DarkGray }
        }
    }
    Write-Host ("  ok: {0} zip entries, eldenring/__init__.py present." -f $ents.Count) -ForegroundColor DarkGray
    Get-ChildItem (Join-Path $ApDir "worlds") -Directory -Filter "eldenring.__apsweep_aside*" -ErrorAction SilentlyContinue | ForEach-Object {
        if (-not (Test-Path $srcWorld)) { Write-Warning "recovering source dir left by a prior run: $($_.Name)"; Rename-Item -LiteralPath $_.FullName -NewName "eldenring" }
    }
    if (-not (Test-Path $srcWorld)) { throw "worlds\eldenring source not found and no recoverable aside -- aborting before any swap." }
    $apAside = Join-Path $ApDir ("worlds\eldenring.__apsweep_aside_{0}" -f (Get-Date -Format yyyyMMddHHmmss))
    Rename-Item -LiteralPath $srcWorld -NewName (Split-Path $apAside -Leaf)
    $customWorlds = Join-Path $ApDir "custom_worlds"
    if (-not (Test-Path $customWorlds)) { New-Item -ItemType Directory -Path $customWorlds | Out-Null }
    $apInstalled = Join-Path $customWorlds "eldenring.apworld"
    Copy-Item -LiteralPath $ApwPath -Destination $apInstalled -Force
    $sweptAgainst = "packaged apworld -> $ApwPath"
    Write-Host "  source tree hidden; apworld installed to custom_worlds\eldenring.apworld (restored at end)." -ForegroundColor Yellow
}

$results = New-Object System.Collections.Generic.List[object]
try {
    foreach ($cfg in $configList) {
        $cfgName = if ($cfg -eq $SENTINEL) { $SENTINEL } else { Split-Path $cfg -Leaf }
        Step ("CONFIG: {0}" -f $cfgName)
        if ($staging) {
            Get-ChildItem $Players -Filter *.yaml -ErrorAction SilentlyContinue | Remove-Item -Force
            Copy-Item -LiteralPath $cfg -Destination (Join-Path $Players (Split-Path $cfg -Leaf)) -Force
        }

        $idx = 0
        foreach ($seed in $seedList) {
            $idx++
            $row = Invoke-SeedRun $cfgName $seed $idx $seedList.Count
            $results.Add($row)
            if ($row.outcome -eq "CONFIGERROR" -and -not $DontStopOnConfigError) {
                Write-Warning ("    CONFIG/syntax error in {0} -- same every seed, skipping the rest of this config." -f $cfgName)
                Write-Warning ("    Fix it or pass -DontStopOnConfigError. See {0}" -f $row.log)
                break
            }
        }
    }
}
finally {
    if ($staging) {
        Get-ChildItem $Players -Filter *.yaml -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
        foreach ($yf in @($yamlBackup.Keys)) { Set-Content -LiteralPath $yf -Value $yamlBackup[$yf] -NoNewline }
        Write-Host "restored original Players\ yaml(s)." -ForegroundColor DarkGray
    }
    if ($Apworld) { Restore-Apworld; Write-Host "restored source tree (worlds\eldenring); removed installed apworld." -ForegroundColor DarkGray }
}

# ----- summary ---------------------------------------------------------------
$stamp   = Get-Date -Format "yyyyMMdd-HHmmss"
$csvPath = Join-Path $Repo "gensweep_${Tag}_$stamp.csv"
$mdPath  = Join-Path $Repo "gensweep_${Tag}_$stamp.md"
$results | Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding UTF8

$md = New-Object System.Collections.Generic.List[string]
$md.Add("# gen sweep -- $Tag -- $stamp")
$md.Add("")
$md.Add("seeds per config: $($seedList.Count)   configs: $($configList.Count)")
$md.Add("swept against: $sweptAgainst")
$md.Add("")
Write-Host ("swept against: {0}" -f $sweptAgainst) -ForegroundColor Cyan

# per-config comparison table
Step "PER-CONFIG COMPARISON"
$md.Add("## per-config comparison")
$md.Add("")
$md.Add("| config | runs | pass | fill | cfgerr | pass-rate |")
$md.Add("|---|---:|---:|---:|---:|---:|")
$byConfig = $results | Group-Object config
$cmp = foreach ($c in $byConfig) {
    $t = $c.Group.Count
    $p = ($c.Group | Where-Object outcome -eq "SUCCESS").Count
    $f = ($c.Group | Where-Object outcome -eq "FILLERROR").Count
    $e = ($c.Group | Where-Object outcome -eq "CONFIGERROR").Count
    $r = if ($t) { [math]::Round(100.0 * $p / $t, 1) } else { 0 }
    [pscustomobject]@{ config=$c.Name; runs=$t; pass=$p; fill=$f; cfgerr=$e; rate=$r }
}
$cmp = $cmp | Sort-Object rate -Descending
$cmp | Format-Table config, runs, pass, fill, cfgerr, @{n='pass%';e={$_.rate}} -AutoSize | Out-Host
foreach ($c in $cmp) {
    $md.Add(("| {0} | {1} | {2} | {3} | {4} | {5}% |" -f $c.config,$c.runs,$c.pass,$c.fill,$c.cfgerr,$c.rate))
}
$md.Add("")

# failure modes, grouped per config
$md.Add("## failure modes (normalized; reproduce with -Seeds <list>)")
$md.Add("")
foreach ($c in $byConfig) {
    $fails = $c.Group | Where-Object { $_.outcome -ne "SUCCESS" }
    if (-not $fails) { continue }
    Write-Host ("`n  {0}:" -f $c.Name) -ForegroundColor Yellow
    $md.Add(("### {0}" -f $c.Name))
    $groups = $fails | Group-Object { ($_.detail -replace '\d+',' N ').Trim() } | Sort-Object Count -Descending
    foreach ($g in $groups) {
        $seedsHit = ($g.Group | ForEach-Object { $_.seed }) -join ", "
        $sample   = ($g.Group | Select-Object -First 1).detail
        Write-Host ("    [{0}x] {1}" -f $g.Count, $sample) -ForegroundColor Yellow
        Write-Host ("          seeds: {0}" -f $seedsHit) -ForegroundColor DarkYellow
        $md.Add(("- **{0}x** -- {1}" -f $g.Count, $sample))
        $md.Add(("  - seeds: ``{0}``" -f $seedsHit))
    }
    $md.Add("")
}
if (-not ($results | Where-Object outcome -ne "SUCCESS")) {
    Write-Host "`n  no failures across any config -- seed-robust." -ForegroundColor Green
    $md.Add("_No failures across any config -- seed-robust._")
}

# ----- region frequency (needs the named kept-region log line from -----------
# patch_apworld_numregions_log_kept_regions.py; older logs won't have it) ------
$regionTally = @{}; $regionSeen = 0
foreach ($r in $results) {
    $lp = Join-Path $Repo $r.log
    if (-not (Test-Path $lp)) { continue }
    $rm = Select-String -Path $lp -Pattern "middle region\(s\) \[(.*?)\]" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($rm) {
        $regionSeen++
        # region names contain commas (e.g. "Leyndell, Royal Capital") and Python repr quotes
        # each element ('...' or "..." when it has an apostrophe) -- so extract QUOTED tokens,
        # never split on comma (that double-counts the capital sub-regions).
        foreach ($qm in [regex]::Matches($rm.Matches[0].Groups[1].Value, "'([^']*)'|""([^""]*)""")) {
            $name = if ($qm.Groups[1].Success) { $qm.Groups[1].Value } else { $qm.Groups[2].Value }
            if ($name) { $regionTally[$name] = ([int]$regionTally[$name]) + 1 }
        }
    }
}
if ($regionSeen -gt 0) {
    Step ("REGION FREQUENCY (kept middle regions across {0} seeds)" -f $regionSeen)
    $md.Add(""); $md.Add(("## regions kept (frequency across {0} seeds)" -f $regionSeen)); $md.Add("")
    $md.Add("| region | kept | % |"); $md.Add("|---|---:|---:|")
    $regionTally.GetEnumerator() | Sort-Object Value -Descending | ForEach-Object {
        $pct = [math]::Round(100.0 * $_.Value / $regionSeen, 0)
        Write-Host ("  {0,-30} {1,3}  ({2,3}%)" -f $_.Key, $_.Value, $pct)
        $md.Add(("| {0} | {1} | {2}% |" -f $_.Key, $_.Value, $pct))
    }
} else {
    Write-Host "  (region frequency unavailable -- gen logs don't name regions yet; apply patch_apworld_numregions_log_kept_regions.py, rebuild the apworld, then re-sweep)" -ForegroundColor DarkYellow
}

Set-Content -LiteralPath $mdPath -Value ($md -join "`r`n") -Encoding UTF8
Write-Host ""
Write-Host ("  CSV -> {0}" -f $csvPath) -ForegroundColor Green
Write-Host ("  MD  -> {0}" -f $mdPath)  -ForegroundColor Green
Write-Host "  (per-seed generate_*.log / gendiag_*.txt left in the repo root for the failures.)"
