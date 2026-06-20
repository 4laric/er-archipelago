# build.ps1 -- ER Archipelago build/bake/deploy driver
#
# Usage (from the repo root, any PowerShell):
#   .\build.ps1 -Randomizer              # build the C# static randomizer (clean, non-incremental)
#   .\build.ps1 -Client                  # build the C++ runtime client DLL (full rebuild)
#   .\build.ps1 -Generate                # regenerate the multiworld (Generate.py; REQUIRED after apworld changes)
#   .\build.ps1 -Serve                   # launch the AP server on the newest output zip (new window)
#   .\build.ps1 -Bake                    # launch the randomizer GUI w/ autoconnect (item rando only)
#   .\build.ps1 -Bake -Enemies           # ...with enemy randomization
#   .\build.ps1 -Deploy                  # copy bake outputs + client DLL + apconfig into the game
#   .\build.ps1 -All                     # the full pipeline (= -Randomizer -Client -Generate -Serve -Bake -Enemies -Deploy -Preflight)
#   .\build.ps1 -All -NoClient           # ...everything in -All EXCEPT the C++ client build (reuse the already-deployed DLL)
#   .\build.ps1 -Apworld                 # package Archipelago\worlds\eldenring into eldenring.apworld (excludes .bak/.pyc)
#   .\build.ps1 -Preflight               # timestamped preflight log + PASS/FAIL cross-checks (seed/slot/deploy freshness)
#   .\build.ps1 -LoopTest -Seeds 1,2,3    # bake a batch of seeds unattended (seed-dependent bug hunt, e.g. #7)
#   .\build.ps1 -LoopTest -Count 8        # ...or N fresh random seeds
#   .\build.ps1 -Clean                   # nuke all build intermediates (fixes stale builds)
#
# Notes:
#  - Both toolchains are prone to SILENT STALE BUILDS; this script always builds clean
#    (--no-incremental / /t:Rebuild). Use -Clean if a change still isn't landing.
#  - -Bake expects the AP server to be running (localhost:38281); use -Serve or start it
#    yourself. -Bake blocks until you close the randomizer window; Deploy runs AFTER.
#  - -Serve opens a NEW window; close any old server window first (one port, one server).
#  - apworld changes (Archipelago\worlds\eldenring) generate straight from the source tree;
#    -Generate picks up edits directly, no apworld reinstall step.

[CmdletBinding()]
param(
    [switch]$Randomizer,
    [switch]$Client,
    [switch]$NoClient,
    [switch]$Generate,
    [int]$GenRetries = 2,            # genretry: gen re-roll attempts on a seed-dependent FillError (0 = off)
    [switch]$GenBumpRegions,         # genretry: also bump num_regions +1 in Players\*.yaml per retry (restored after)
    [switch]$Serve,
    [switch]$Bake,
    [switch]$Enemies,
    [switch]$Deploy,
    [switch]$Apworld,
    [switch]$NoCrashFix,
    [switch]$Helper,
    [switch]$Clean,
    [switch]$Preflight,
    [switch]$LoopTest,
    [int[]]$Seeds,
    [int]$Count = 5,
    [switch]$All
)

$ErrorActionPreference = "Stop"

# ---- pwsh shim ------------------------------------------------------------------------------
# Some MSBuild build events / tools invoke `pwsh.exe` (PowerShell 7). If PS7 is not installed
# the step fails with "'pwsh.exe' is not recognized" (notably the C++ client build-stamp step),
# which is noisy but non-fatal. Make pwsh.exe resolve to Windows PowerShell for THIS build
# session (child processes inherit the PATH) so the call succeeds. Proper fix is still:
#   winget install --id Microsoft.PowerShell --source winget
if (-not (Get-Command pwsh.exe -ErrorAction SilentlyContinue)) {
    $shimDir = Join-Path $env:LOCALAPPDATA "er-build-pwsh-shim"
    $shimExe = Join-Path $shimDir "pwsh.exe"
    if (-not (Test-Path $shimExe)) {
        New-Item -ItemType Directory -Force -Path $shimDir | Out-Null
        $winps = (Get-Command powershell.exe -ErrorAction SilentlyContinue).Source
        if ($winps) { Copy-Item -LiteralPath $winps -Destination $shimExe -Force }
    }
    if (Test-Path $shimExe) {
        $env:PATH = "$shimDir;$env:PATH"
        Write-Host "  [pwsh-shim] PowerShell 7 not found -> shimming pwsh.exe to Windows PowerShell for this build (install PS7: winget install --id Microsoft.PowerShell)"
    } else {
        Write-Warning "pwsh.exe not found and could not shim it; PS7-dependent steps may fail. Install: winget install --id Microsoft.PowerShell"
    }
}

# -All = the full pipeline: build both, regenerate, serve, bake w/ enemies, deploy.
if ($All) {
    $Randomizer = $true; $Client = (-not $NoClient); $Generate = $true
    $Serve = $true; $Bake = $true; $Enemies = $true; $Deploy = $true; $Preflight = $true; $Apworld = $true
}

# ----- config ---------------------------------------------------------------------------------
$Repo     = $PSScriptRoot
$GameDir  = "C:\Program Files (x86)\Steam\steamapps\common\ELDEN RING\Game"
$ModsDir  = Join-Path $GameDir "mods"          # client DLL + apconfig.json live here (EML loads dlls from mods\)
# Game-file overrides (regulation.bin, event\, map\, msg\, script\) go in the GAME ROOT: the exe is
# UXM-unpacked+patched, so it reads loose files from Game\ directly. mods\ copies are ignored.
$AssetDir = $GameDir
$RandoDir = Join-Path $Repo "SoulsRandomizers"
$RandoExe = Join-Path $RandoDir "EldenRingRandomizer\bin\Release (Archipelago)\net6.0-windows\win-x64\EldenRingRandomizer.exe"
$ClientDir = Join-Path $Repo "Dark-Souls-III-Archipelago-client\archipelago-client"
$ClientDll = Join-Path $ClientDir "x64\Release\archipelago.dll"

# RandomizerCrashFix.dll -- fifthmatt's redistributable companion (shipped in the v0.11.4 package).
# Guards the cross-content enemy-placement CTDs that scripted legacy-dungeon intros are prone to once
# base + DLC enemies are shuffled together -- the prime suspect for the Raya Lucaria entry crash
# (TODO #10). Referenced from the package, NOT rebundled into source (licensing). Glob-resolved so the
# exact package folder suffix can vary.
$CrashFixDll = Get-ChildItem -Path $Repo -Directory -Filter 'Elden Ring Randomizer-428*' -ErrorAction SilentlyContinue |
    ForEach-Object { Join-Path $_.FullName 'randomizer\dll\RandomizerCrashFix.dll' } |
    Where-Object { Test-Path $_ } | Select-Object -First 1

# RandomizerHelper.dll -- fifthmatt's auto-equip/upgrade companion (same v0.11.4 package). We deploy
# it ONLY for weapon/ash auto-UPGRADE (the client lacks that); its auto-EQUIP is disabled via the
# project-tuned ini below to avoid colliding with the client's own AutoEquip. Opt-in via -Helper.
$HelperDll = Get-ChildItem -Path $Repo -Directory -Filter 'Elden Ring Randomizer-428*' -ErrorAction SilentlyContinue |
    ForEach-Object { Join-Path $_.FullName 'randomizer\dll\RandomizerHelper.dll' } |
    Where-Object { Test-Path $_ } | Select-Object -First 1
$HelperIni = Join-Path $Repo 'RandomizerHelper_config.ini'   # project-tuned: equip off, upgrade on
$ApDir     = Join-Path $Repo "Archipelago"     # AP source checkout: Generate.py, MultiServer.py, Players\, output\

function Step($msg) { Write-Host "`n==== $msg" -ForegroundColor Cyan }

# Locate an msbuild that has the C++ toolset. The PATH/devenv msbuild can come from a VS
# install WITHOUT the C++ workload (VCTargetsPath then points at a nonexistent .props), so
# ask vswhere for an install that includes VC.Tools first; PATH is only a fallback.
function Find-MSBuild {
    $vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    if (Test-Path $vswhere) {
        $path = & $vswhere -latest -products * `
            -requires Microsoft.Component.MSBuild Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
            -find "MSBuild\**\Bin\MSBuild.exe" | Select-Object -First 1
        if ($path) { return $path }
    }
    $cmd = Get-Command msbuild -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    throw "no msbuild with the C++ toolset found. Install VS2022 BuildTools' 'Desktop development with C++' workload."
}

# ----- server helpers (shared by -LoopTest) ---------------------------------------------------
function Stop-Server38281 {
    $listen = Get-NetTCPConnection -LocalPort 38281 -State Listen -ErrorAction SilentlyContinue
    if ($listen) {
        $listen | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
            try { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } catch {}
        }
        Start-Sleep -Seconds 1
    }
}
function Start-Server38281($zipPath) {
    Start-Process python -ArgumentList "MultiServer.py", "`"$zipPath`"" -WorkingDirectory $ApDir
    $deadline = (Get-Date).AddSeconds(60)
    while (-not (Get-NetTCPConnection -LocalPort 38281 -State Listen -ErrorAction SilentlyContinue)) {
        if ((Get-Date) -gt $deadline) { throw "AP server didn't open port 38281 within 60s -- check the server window" }
        Start-Sleep -Seconds 2
    }
}

if (-not ($Randomizer -or $Client -or $Generate -or $Serve -or $Bake -or $Deploy -or $Clean -or $Preflight -or $LoopTest -or $Apworld -or $All)) {
    Get-Content $PSCommandPath | Select-Object -Skip 1 -First 20 | ForEach-Object { $_ -replace '^#\s?', '' }
    return
}

# ----- clean ----------------------------------------------------------------------------------
if ($Clean) {
    Stop-Server38281   # -Clean also kills any stale AP server on :38281 (easy to forget; frees the port + the output-zip lock)
    Step "Cleaning build intermediates"
    $targets = @(
        (Join-Path $Repo "SoulsFormats\SoulsFormats\obj"), (Join-Path $Repo "SoulsFormats\SoulsFormats\bin"),
        (Join-Path $Repo "SoulsIds\SoulsIds\obj"),         (Join-Path $Repo "SoulsIds\SoulsIds\bin"),
        (Join-Path $RandoDir "RandomizerCommon\obj"),      (Join-Path $RandoDir "RandomizerCommon\bin"),
        (Join-Path $RandoDir "EldenRingRandomizer\obj"),   (Join-Path $RandoDir "EldenRingRandomizer\bin"),
        (Join-Path $Repo "yet-another-tab-control\obj"),   (Join-Path $Repo "yet-another-tab-control\bin"),
        (Join-Path $ClientDir "x64"),                      (Join-Path $ClientDir "obj")
    )
    foreach ($t in $targets) {
        if (Test-Path $t) { Remove-Item -Recurse -Force $t; Write-Host "  removed $t" }
    }
}

# ----- randomizer (C#) ------------------------------------------------------------------------
if ($Randomizer) {
    Step "Building static randomizer (Release (Archipelago), non-incremental)"
    Push-Location $RandoDir
    try {
        dotnet build -c "Release (Archipelago)" --no-incremental "EldenRingRandomizer\EldenRingRandomizer.csproj"
        if ($LASTEXITCODE -ne 0) { throw "randomizer build failed" }
    } finally { Pop-Location }
    if (-not (Test-Path $RandoExe)) { throw "build reported success but exe not found: $RandoExe" }
    Write-Host "  -> $RandoExe"
}

# ----- client (C++) ---------------------------------------------------------------------------
if ($Client) {
    Step "Building runtime client DLL (full rebuild -- incremental goes stale)"
    $msbuild = Find-MSBuild
    Push-Location $ClientDir
    try {
        & $msbuild "archipelago-client.sln" /t:Rebuild /p:Configuration=Release /p:Platform=x64 /m /v:minimal
        if ($LASTEXITCODE -ne 0) { throw "client build failed" }
    } finally { Pop-Location }
    if (-not (Test-Path $ClientDll)) { throw "build reported success but DLL not found: $ClientDll" }
    Write-Host "  -> $ClientDll  (check the er::Init BUILD stamp at launch to confirm freshness)"
}

# ----- generate multiworld --------------------------------------------------------------------
if ($Generate) {
    Step "Regenerating multiworld (Generate.py, players from Archipelago\Players)"
    if (-not (Test-Path (Join-Path $ApDir "Generate.py"))) { throw "AP checkout not found at $ApDir" }
    # Pre-gen guard (pregen.py): invalidate stale eldenring .pyc so a source edit can't be masked
    # by cached bytecode (the "same FillError 6x, edits do nothing" trap), and warn about per-game
    # yaml options stranded at the document root (silently ignored by AP). Warn-only.
    if (Test-Path (Join-Path $Repo "pregen.py")) {
        python (Join-Path $Repo "pregen.py") | Write-Host
    } else {
        Write-Warning "pregen.py not found -- skipping stale-bytecode/yaml guard"
    }
    # --- genretry: each Generate.py run picks a FRESH random seed, so a seed-dependent
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
    if ($genExit -ne 0) { throw ("multiworld generation FAILED after {0} attempt(s) (exit {1}) -- see diag/raw log above" -f $maxAttempts, $genExit) }
    $newest = Get-ChildItem (Join-Path $ApDir "output") -Filter "AP_*.zip" |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    Write-Host "  -> $($newest.FullName)"
}

# ----- package apworld ------------------------------------------------------------------------
if ($Apworld) {
    Step "Packaging eldenring.apworld from Archipelago\worlds\eldenring"
    $srcDir = Join-Path $ApDir "worlds\eldenring"
    if (-not (Test-Path (Join-Path $srcDir "__init__.py"))) { throw "apworld source not found: $srcDir\__init__.py" }
    $outFile = Join-Path $Repo "eldenring.apworld"
    Add-Type -AssemblyName System.IO.Compression.FileSystem | Out-Null
    # Exclude dev clutter: per-patch __init__ backups (*.bak*), bytecode caches, and the
    # gen-time diag dumps the world writes into its own folder. Keep the real package + data.
    $excludeName  = @('*.bak', '*.bak_*', '*.pyc', '*.pyo')
    $excludeExact = @('ER_DIAG.txt', 'ER_SPHERE_TIERS.txt')
    $srcFull = (Resolve-Path $srcDir).Path.TrimEnd('\')
    $files = Get-ChildItem -LiteralPath $srcFull -Recurse -File | Where-Object {
        $rel = $_.FullName.Substring($srcFull.Length).TrimStart('\','/')
        if ($rel -match '(^|[\\/])__pycache__([\\/]|$)') { return $false }
        if ($excludeExact -contains $_.Name) { return $false }
        foreach ($p in $excludeName) { if ($_.Name -like $p) { return $false } }
        return $true
    }
    if (Test-Path $outFile) { Remove-Item -LiteralPath $outFile -Force }
    $zip = [System.IO.Compression.ZipFile]::Open($outFile, 'Create')
    try {
        foreach ($f in $files) {
            $rel = $f.FullName.Substring($srcFull.Length).TrimStart('\','/').Replace('\','/')
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $f.FullName, "eldenring/$rel") | Out-Null
        }
    } finally { $zip.Dispose() }
    $size = [math]::Round((Get-Item $outFile).Length / 1KB, 1)
    Write-Host ("  -> {0}  ({1} files, {2} KB)" -f $outFile, $files.Count, $size) -ForegroundColor Green
}

# ----- serve ----------------------------------------------------------------------------------
if ($Serve) {
    $zip = Get-ChildItem (Join-Path $ApDir "output") -Filter "AP_*.zip" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $zip) { throw "no multiworld zip in $ApDir\output -- run with -Generate first" }
    $inUse = Get-NetTCPConnection -LocalPort 38281 -State Listen -ErrorAction SilentlyContinue
    if ($inUse) {
        Write-Warning "port 38281 already has a listener -- an OLD server is probably still running. Close it; this one won't bind."
    }
    Step "Launching AP server (new window): $($zip.Name)"
    Start-Process python -ArgumentList "MultiServer.py", "`"$($zip.FullName)`"" -WorkingDirectory $ApDir
    # Wait until it's actually listening before -Bake tries to autoconnect (up to 60s).
    $deadline = (Get-Date).AddSeconds(60)
    while (-not (Get-NetTCPConnection -LocalPort 38281 -State Listen -ErrorAction SilentlyContinue)) {
        if ((Get-Date) -gt $deadline) { throw "AP server didn't open port 38281 within 60s -- check the server window" }
        Start-Sleep -Seconds 2
    }
    Write-Host "  server is listening on 38281"
}

# ----- bake -----------------------------------------------------------------------------------
if ($Bake) {
    Step ("Launching bake (autoconnect{0}) -- needs the AP server on localhost:38281" -f $(if ($Enemies) { " + enemies" } else { "" }))
    if (-not (Test-Path $RandoExe)) { throw "randomizer exe not found -- run with -Randomizer first" }
    Push-Location $RandoDir   # cwd matters: outputs land here; apconfig.json lands at ..\
    try {
        $bakeArgs = @("/gui", "autoconnect", "headless"); if ($Enemies) { $bakeArgs += "enemies" }
        # Pass the slot name from the (single) Players yaml so the bake connects as the right
        # slot instead of the hardcoded "Player1" (TODO #3). First yaml wins (dev-loop = 1 yaml).
        $playerYaml = Get-ChildItem (Join-Path $ApDir "Players") -Filter *.yaml -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($playerYaml) {
            $nm = Select-String -Path $playerYaml.FullName -Pattern '^\s*name:\s*(.+?)\s*$' | Select-Object -First 1
            if ($nm) { $slot = $nm.Matches.Groups[1].Value.Trim(); $bakeArgs += "slot=$slot"; Write-Host "  bake slot = $slot" }
        }
        & $RandoExe @bakeArgs | Out-Default   # window auto-closes on completion (headless); no click needed
        $bakeExit = $LASTEXITCODE
    } finally { Pop-Location }
    if ($bakeExit -ne 0) { throw ("bake FAILED (exit {0}) -- see ap_bake_*.log / ap_error.txt in {1}" -f $bakeExit, $RandoDir) }
    Write-Host "  bake finished. Outputs: $RandoDir\{regulation.bin,event,msg,script,map} + $Repo\apconfig.json"
    # Surface the region-fog-gate bake diagnostic. RegionFogGates writes ap_region_gates_<stamp>.txt
    # to $RandoDir; the bake runs as a WinForms GUI so its Console output is otherwise not captured.
    $rfg = Get-ChildItem -Path $RandoDir -Filter "ap_region_gates_*.txt" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime | Select-Object -Last 1
    if ($rfg) {
        Step "Region fog gates (ap_region_gates)"
        Get-Content $rfg.FullName | Write-Host
        Write-Host ("  -> {0}" -f $rfg.FullName) -ForegroundColor Green
    } else {
        Write-Host "  RegionFogGates: no ap_region_gates_*.txt produced -- pass did not run (rebuild SoulsRandomizers?)" -ForegroundColor Yellow
    }
}

# ----- deploy ---------------------------------------------------------------------------------
if ($Deploy) {
    Step "Deploying to $ModsDir"
    if (-not (Test-Path $ModsDir)) { New-Item -ItemType Directory -Path $ModsDir | Out-Null }

    # Game-file overrides produced by the bake. 'map' only exists for enemy bakes.
    $reg = Join-Path $RandoDir "regulation.bin"
    if (Test-Path $reg) {
        Copy-Item $reg (Join-Path $AssetDir "regulation.bin") -Force
        Write-Host "  regulation.bin"
    } else { Write-Warning "no regulation.bin in $RandoDir -- did the bake run?" }
    # 'menu' carries the AP-icon override: the bake's InjectApItemIcon step writes
    # menu\hi\00_solo.tpfbnd.dcx with the telescope icon swapped for the Archipelago flower
    # (only when diste\Archipelago\ap_telescope_icon.dds exists). See SPEC-ap-icon.md.
    foreach ($dir in "event", "msg", "script", "map", "menu") {
        $src = Join-Path $RandoDir $dir
        if (Test-Path $src) {
            # Copy CONTENTS, not the dir itself: Copy-Item dir->existing-dir nests (Game\map\map),
            # and these dirs all exist in a UXM-unpacked game root.
            $dst = Join-Path $AssetDir $dir
            if (-not (Test-Path $dst)) { New-Item -ItemType Directory -Path $dst | Out-Null }
            Copy-Item (Join-Path $src "*") $dst -Recurse -Force
            Write-Host "  $dir\"
        }
    }

    # apconfig.json: written by the bake to <repo>\apconfig.json; the client reads it from mods\.
    # (The flag-polling 'location_flags' map travels in this file -- forgetting it = silent no-polling.)
    $apconfig = Join-Path $Repo "apconfig.json"
    if (Test-Path $apconfig) {
        Copy-Item $apconfig (Join-Path $ModsDir "apconfig.json") -Force
        Write-Host "  apconfig.json"
    } else { Write-Warning "no apconfig.json at $Repo -- bake must complete (incl. server connect) to write it" }

    # Client DLL.
    if (Test-Path $ClientDll) {
        Copy-Item $ClientDll (Join-Path $ModsDir "archipelago.dll") -Force
        Write-Host "  archipelago.dll"
    } else { Write-Warning "no client DLL at $ClientDll -- run with -Client first" }

    # RandomizerCrashFix.dll: EML auto-loads mods\*.dll, but on a DELAYED schedule (so mods attach
    # after the game's anti-tamper has settled). RandomizerCrashFix hooks EneDatMan and MUST load
    # BEFORE the game constructs it -- the delayed default load is too late and the dll aborts with
    # "initialized too late (EneDatMan already exists). Either add it to external_dlls or rename it
    # to dinput8.dll". EML's equivalent of ModEngine2's early external_dlls is a load order of 0,
    # which EML loads instantly, ignoring the delay (per its README). We pin that with a per-mod
    # load.txt: mods\RandomizerCrashFix\load.txt = 0. Anti-CTD guard for cross-content enemy
    # placements (Raya Lucaria etc., TODO #10). Use -NoCrashFix to deploy WITHOUT it and A/B.
    $cfOrderDir = Join-Path $ModsDir "RandomizerCrashFix"   # EML load-order folder (name = dll basename)
    $cfDll      = Join-Path $ModsDir "RandomizerCrashFix.dll"
    # The crash fix ONLY guards cross-content enemy placements, so it has no business in an
    # item-only deploy (it just hooks EneDatMan for nothing, and muddies the RLA A/B). Detect an
    # enemy bake by its "map" output -- item-only bakes never produce one (see deploy loop above) --
    # and fall back to the -Enemies switch for a bake+deploy in the same run.
    $enemyBake = (Test-Path (Join-Path $RandoDir "map")) -or $Enemies
    if ($enemyBake -and -not $NoCrashFix) {
        if ($CrashFixDll -and (Test-Path $CrashFixDll)) {
            Copy-Item $CrashFixDll $cfDll -Force
            # Force instant (pre-EneDatMan) load: order 0 ignores EML's load delay.
            if (-not (Test-Path $cfOrderDir)) { New-Item -ItemType Directory -Path $cfOrderDir | Out-Null }
            Set-Content -Path (Join-Path $cfOrderDir "load.txt") -Value "0" -NoNewline -Encoding ascii
            Write-Host "  RandomizerCrashFix.dll  (anti-CTD, load order 0; pass -NoCrashFix to omit)"
        } else {
            Write-Warning "RandomizerCrashFix.dll not found under $Repo -- enemy CTDs (RLA) may persist; see TODO #10"
        }
    } else {
        # Not an enemy bake (item-only) or active opt-out (-NoCrashFix): purge any stale copy + its
        # load-order folder so an item-only seed never inherits the enemy crash fix, and the A/B stays clean.
        if (Test-Path $cfDll) {
            Remove-Item $cfDll -Force
            $cfWhy = if ($NoCrashFix) { "-NoCrashFix" } else { "item-only bake, not needed" }
            Write-Host "  (removed stale RandomizerCrashFix.dll: $cfWhy)"
        }
        if (Test-Path $cfOrderDir) { Remove-Item $cfOrderDir -Recurse -Force }
    }

    # RandomizerHelper.dll (opt-in: -Helper). Auto-upgrade only; deploys the dll + our tuned ini
    # (equip OFF so it doesn't fight the client's AutoEquip). UNVERIFIED that its pickup-hook
    # upgrade fires on AP's direct-grant path -- check RandomizerHelper_log.txt in-game.
    if ($Helper) {
        if ($HelperDll -and (Test-Path $HelperDll)) {
            Copy-Item $HelperDll (Join-Path $ModsDir "RandomizerHelper.dll") -Force
            Write-Host "  RandomizerHelper.dll  (-Helper; auto-upgrade)"
            if (Test-Path $HelperIni) {
                Copy-Item $HelperIni (Join-Path $ModsDir "RandomizerHelper_config.ini") -Force
                Write-Host "  RandomizerHelper_config.ini  (equip off, upgrade on)"
            } else {
                Write-Warning "RandomizerHelper_config.ini missing at $Repo -- dll will fall back to defaults (autoEquip=true) and CONFLICT with the client"
            }
        } else {
            Write-Warning "RandomizerHelper.dll not found under $Repo -- -Helper had no effect"
        }
    }

    Write-Host "`nDeployed. Launch the game via Elden Mod Loader and check:" -ForegroundColor Green
    Write-Host "  - er::Init BUILD stamp matches this build time"
    Write-Host "  - 'Loaded N location flags for check polling' appears at startup"
}

# ----- preflight validation -------------------------------------------------------------------
# Writes a timestamped log and runs cross-checks that catch the failure modes this pipeline is
# prone to: a STALE server (bake connects to an old multiworld), a wrong SLOT, or a deploy that
# didn't refresh apconfig/dll. Run as the last step of -All, or standalone after a manual bake.
if ($Preflight) {
    Step "Preflight validation"
    $ts  = Get-Date -Format "yyyyMMdd-HHmmss"
    $log = Join-Path $Repo "preflight_$ts.log"
    $lines = New-Object System.Collections.Generic.List[string]
    $script:fails = 0
    function L($s) { $lines.Add([string]$s) | Out-Null; Write-Host $s }
    function Check($name, $ok, $detail) {
        if (-not $ok) { $script:fails++ }
        L ("[{0}] {1}{2}" -f $(if ($ok) { "PASS" } else { "FAIL" }), $name, $(if ($detail) { " -- $detail" } else { "" }))
    }
    try {
        L "ER AP preflight  $ts"
        L "repo: $Repo"
        L ""

        # intended slot(s) from Players\*.yaml
        $slotNames = @()
        foreach ($p in (Get-ChildItem (Join-Path $ApDir "Players") -Filter *.yaml -ErrorAction SilentlyContinue)) {
            $m = Select-String -Path $p.FullName -Pattern '^\s*name:\s*(.+?)\s*$' | Select-Object -First 1
            $nm = if ($m) { $m.Matches.Groups[1].Value.Trim() } else { "<no name:>" }
            $slotNames += $nm
            L ("player yaml : {0}  (name={1})" -f $p.Name, $nm)
        }
        # AP Generate reads EVERY file in Players\ (incl. .bak/.txt), not just *.yaml.
        $strayFiles = Get-ChildItem (Join-Path $ApDir "Players") -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Extension -notin @(".yaml", ".yml") }
        if ($strayFiles) { L ("stray in Players\: {0}" -f (($strayFiles | ForEach-Object { $_.Name }) -join ", ")) }

        # newest generated multiworld + its seed (filename AP_<seed>.zip)
        $zip = Get-ChildItem (Join-Path $ApDir "output") -Filter "AP_*.zip" -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending | Select-Object -First 1
        $zipSeed = if ($zip) { $zip.BaseName -replace '^AP_', '' } else { $null }
        L ("newest zip  : {0}  (seed={1}; written={2})" -f $(if ($zip) { $zip.Name } else { "<none>" }), $zipSeed, $(if ($zip) { $zip.LastWriteTime } else { "" }))

        # baked apconfig (repo) and deployed apconfig (mods\)
        $apr = $null; $apm = $null
        $apRepo = Join-Path $Repo "apconfig.json"
        $apMods = Join-Path $ModsDir "apconfig.json"
        if (Test-Path $apRepo) { $apr = Get-Content $apRepo -Raw | ConvertFrom-Json }
        if (Test-Path $apMods) { $apm = Get-Content $apMods -Raw | ConvertFrom-Json }
        $rFlags = if ($apr) { @($apr.location_flags.PSObject.Properties).Count } else { 0 }
        $mFlags = if ($apm) { @($apm.location_flags.PSObject.Properties).Count } else { 0 }
        if ($apr) { L ("apconfig repo    : slot={0} seed={1} url={2} flags={3}" -f $apr.slot, $apr.seed, $apr.url, $rFlags) } else { L "apconfig repo    : <missing>" }
        if ($apm) { L ("apconfig deployed: slot={0} seed={1} flags={2}" -f $apm.slot, $apm.seed, $mFlags) } else { L "apconfig deployed: <missing>" }

        # deployed artifact freshness
        $dll = Join-Path $ModsDir "archipelago.dll"
        $reg = Join-Path $AssetDir "regulation.bin"
        if (Test-Path $dll) { L ("client dll  : {0}" -f (Get-Item $dll).LastWriteTime) }
        if (Test-Path $reg) { L ("regulation  : {0}" -f (Get-Item $reg).LastWriteTime) }

        # server on 38281 (stale-server detector)
        $listen = Get-NetTCPConnection -LocalPort 38281 -State Listen -ErrorAction SilentlyContinue
        if ($listen) {
            $started = ""
            try { $started = (Get-Process -Id $listen.OwningProcess -ErrorAction SilentlyContinue).StartTime } catch {}
            L ("server 38281: LISTENING (pid={0} started={1})" -f $listen.OwningProcess, $started)
        } else { L "server 38281: no listener" }

        L ""
        L "---- verdicts ----"
        Check "baked slot is an intended player"   ($apr -and ($slotNames -contains $apr.slot)) ("baked='{0}' players=[{1}]" -f $(if($apr){$apr.slot}), ($slotNames -join ", "))
        Check "baked seed == newest generated seed" ($apr -and $zipSeed -and ($apr.seed -eq $zipSeed)) ("baked='{0}' newest='{1}'" -f $(if($apr){$apr.seed}), $zipSeed)
        Check "deployed apconfig matches baked"     ($apr -and $apm -and ($apr.seed -eq $apm.seed) -and ($apr.slot -eq $apm.slot)) ("deployed slot/seed={0}/{1}" -f $(if($apm){$apm.slot}), $(if($apm){$apm.seed}))
        # Pool-agnostic: deployed flag map must be non-empty AND equal the baked repo count
        # (lean ~494, trimmed ~2150, base ~3686, DLC ~4857). Catches broken bakes AND stale/
        # partial deploys regardless of location_pool. (Old flat >1000 floor failed on lean.)
        Check "deployed location_flags present"     ($mFlags -gt 0 -and $mFlags -eq $rFlags) ("deployed=$mFlags baked=$rFlags")
        Check "client dll deployed"                 (Test-Path $dll) $dll
        Check "Players\ has no stray files"          (-not $strayFiles) (($strayFiles | ForEach-Object { $_.Name }) -join ", ")

        L ""
        if ($script:fails -eq 0) {
            L "PREFLIGHT: PASS -- baked slot/seed match the newest gen and are deployed."
        } else {
            L ("PREFLIGHT: {0} FAILURE(S) -- do NOT trust this build for a sync (likely stale server or un-refreshed deploy)." -f $script:fails)
        }
    } catch {
        L ("preflight error: {0}" -f $_)
    }
    $lines | Set-Content -Path $log -Encoding UTF8
    Write-Host ("`npreflight log -> {0}" -f $log) -ForegroundColor Green
    if ($script:fails -gt 0) { Write-Warning "Preflight found problems (see verdicts above)." }
}

# ----- seed-loop bake test --------------------------------------------------------------------
# Bakes a batch of seeds unattended to shake out seed-dependent generation bugs (e.g. the
# volcano_town loop, TODO #7). Per seed: Generate.py (--seed for reproducibility), start a FRESH
# server for that exact zip (so the bake can't hit a stale server), then a HEADLESS bake (no
# dialogs, auto-close, exit code = pass/fail). Success is confirmed when apconfig.json's seed
# matches the freshly generated seed. Run -Randomizer first.
if ($LoopTest) {
    Step "Seed-loop bake test"
    if (-not (Test-Path $RandoExe)) { throw "randomizer exe not found -- run with -Randomizer first" }
    if (-not (Test-Path (Join-Path $ApDir "Generate.py"))) { throw "AP checkout not found at $ApDir" }

    # slot name from the single Players yaml (same rule as -Bake)
    $slot = $null
    $playerYaml = Get-ChildItem (Join-Path $ApDir "Players") -Filter *.yaml -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($playerYaml) {
        $nm = Select-String -Path $playerYaml.FullName -Pattern '^\s*name:\s*(.+?)\s*$' | Select-Object -First 1
        if ($nm) { $slot = $nm.Matches.Groups[1].Value.Trim() }
    }
    if (-not $slot) { throw "no 'name:' found in Players yaml -- can't pick a bake slot" }
    Write-Host "  bake slot = $slot"

    $useRandom = -not $Seeds
    $iter = if ($useRandom) { 1..$Count } else { $Seeds }
    $results = New-Object System.Collections.Generic.List[object]
    $n = 0
    foreach ($item in $iter) {
        $n++
        $tag = if ($useRandom) { "random $n/$($iter.Count)" } else { "seed=$item ($n/$($iter.Count))" }

        Step "[$n] Generate ($tag)"
        $genOk = $false
        Push-Location $ApDir
        try {
            if ($useRandom) { python Generate.py | Out-Default }
            else            { python Generate.py --seed $item | Out-Default }
            $genOk = ($LASTEXITCODE -eq 0)
        } finally { Pop-Location }
        if (-not $genOk) {
            $results.Add([pscustomobject]@{ n=$n; req=$item; seed='(gen failed)'; exit=''; match=$false; status='GEN-FAIL' })
            Write-Warning "  generation failed for $tag -- skipping bake"
            continue
        }
        $zip = Get-ChildItem (Join-Path $ApDir "output") -Filter "AP_*.zip" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        $genSeed = $zip.BaseName -replace '^AP_',''

        # fresh server for THIS zip (kills any stale listener first -- avoids the stale-server bake)
        Stop-Server38281
        Start-Server38281 $zip.FullName

        Step "[$n] Headless bake (seed $genSeed, slot $slot)"
        $bakeArgs = @("/gui","autoconnect","headless","slot=$slot"); if ($Enemies) { $bakeArgs += "enemies" }
        $proc = Start-Process -FilePath $RandoExe -ArgumentList $bakeArgs -WorkingDirectory $RandoDir -PassThru
        if (-not $proc.WaitForExit(420000)) {   # 7-min safety net against a hung bake
            try { $proc.Kill() } catch {}
            $results.Add([pscustomobject]@{ n=$n; req=$item; seed=$genSeed; exit='TIMEOUT'; match=$false; status='HANG' })
            Write-Warning "  bake timed out (>7min) on seed $genSeed -- killed"
            continue
        }
        $code = try { $proc.ExitCode } catch { 'n/a' }   # GUI exit code can be flaky; apconfig match is ground truth

        # success = apconfig.json now carries this seed (ground truth; exit code is a cross-check)
        $apr = $null; $apRepo = Join-Path $Repo "apconfig.json"
        if (Test-Path $apRepo) { $apr = Get-Content $apRepo -Raw | ConvertFrom-Json }
        $match = ($apr -and ($apr.seed -eq $genSeed))
        $status = if ($match -and $code -eq 0) { 'OK' } elseif ($match) { 'OK*' } else { 'BAKE-FAIL' }
        $results.Add([pscustomobject]@{ n=$n; req=$item; seed=$genSeed; exit=$code; match=$match; status=$status })
    }

    Step "Loop test results"
    $results | Format-Table -AutoSize | Out-Host
    $okCount = @($results | Where-Object { $_.status -like 'OK*' }).Count
    $col = if ($okCount -eq $results.Count) { 'Green' } else { 'Yellow' }
    Write-Host ("  {0}/{1} bakes matched the generated seed" -f $okCount, $results.Count) -ForegroundColor $col
}
