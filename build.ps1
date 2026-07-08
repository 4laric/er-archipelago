# build.ps1 -- ER Archipelago (pure-runtime) build / deploy driver
#
# Pure-runtime only: vanilla ELDEN RING + the apworld + the Rust client under me3.
# No SoulsRandomizers baker, no C++ client, no regulation/event/msg/script/map overlays.
# (The baker + C++ client were retired 2026-07-01; see git history for the old build.ps1.)
#
# Usage (from the repo root, any PowerShell):
#   .\build.ps1 -Apworld                 # package Archipelago\worlds\eldenring -> eldenring.apworld
#   .\build.ps1 -Generate                # regenerate the multiworld (Generate.py); REQUIRED after apworld changes
#   .\build.ps1 -Rust                    # cargo test + build the Rust client cdylib (eldenring_archipelago.dll)
#   .\build.ps1 -Me3Deploy               # stage DLL + apconfig + AP icon into me3\, write the ap.me3 profile
#   .\build.ps1 -Me3Restore              # un-park the EML client dll (revert -Me3Deploy's park)
#   .\build.ps1 -RustDeploy              # (EML alt loader) drop the Rust DLL into mods\ instead of me3
#   .\build.ps1 -Serve                   # launch the AP server on the newest output zip (new window)
#   .\build.ps1 -PureRuntime  (-Mvp)     # the whole loop: Generate + Rust + Me3Deploy + Serve
#   .\build.ps1 -All                     # alias for -PureRuntime, plus -Apworld and -Preflight
#   .\build.ps1 -Preflight               # timestamped PASS/FAIL cross-checks (seed / staged dll / server)
#   .\build.ps1 -Clean                   # cargo clean + kill any stale AP server on :38281
#
# Launch the game after a deploy:
#   me3 launch --profile <repo>\me3\ap.me3        (vanilla game files -- NOT UXM-patched)
#
# Notes:
#  - cargo build is always release for x86_64-pc-windows-msvc; -Clean also runs `cargo clean`.
#  - -Serve opens a NEW window; close any old server window first (one port, one server).
#  - apworld changes (Archipelago\worlds\eldenring) generate straight from the source tree;
#    -Generate picks up edits directly, no apworld reinstall step.

[CmdletBinding()]
param(
    [switch]$Apworld,
    [switch]$Greenfield,           # -Greenfield: gen the data-derived greenfield apworld in isolation
    [switch]$Generate,
    [switch]$ShowGenDiag,          # echo the per-generate gendiag (resolved-yaml debug) to console
    [int]$GenRetries = 2,          # gen re-roll attempts on a seed-dependent FillError (0 = off)
    [switch]$GenBumpRegions,       # also bump num_regions +1 in Players\*.yaml per retry (restored after)
    [switch]$Rust,                 # cargo test + build the injected cdylib
    [switch]$RustDeploy,           # EML alt: drop the Rust DLL into mods\ (me3 is the primary loader)
    [switch]$Me3Deploy,            # stage DLL + apconfig + icon into me3\, write ap.me3 (primary loader)
    [switch]$Me3Restore,           # un-park the EML client dll (revert -Me3Deploy)
    [Alias('Mvp')]
    [switch]$PureRuntime,          # Generate + Rust + Me3Deploy + Serve
    [switch]$Serve,
    [switch]$Preflight,
    [switch]$Clean,
    [switch]$All
)

$ErrorActionPreference = "Stop"

# -All = the full loop plus packaging + preflight. -PureRuntime is the runtime umbrella.
if ($All) { $PureRuntime = $true; $Apworld = $true; $Preflight = $true }

# -PureRuntime: apworld source already emits slot_data (locationFlags/checkItemIds/checkItemFlags/
# shopRowFlags) straight from __init__.py, so this is just Generate -> Rust -> Me3Deploy -> Serve.
# The game runs VANILLA; the Rust client flag-polls slot_data and grants come from the AP server.
if ($PureRuntime) {
    $Generate  = $true
    $Rust      = $true
    $Me3Deploy = $true
    $Serve     = $true
}

# ----- config ---------------------------------------------------------------------------------
$Repo     = $PSScriptRoot
$GameDir  = "C:\Program Files (x86)\Steam\steamapps\common\ELDEN RING\Game"
$ModsDir  = Join-Path $GameDir "mods"          # EML alt loader path (-RustDeploy); me3 is primary
$ApDir    = Join-Path $Repo "Archipelago"      # AP checkout: Generate.py, MultiServer.py, Players\, output\

# -Greenfield: build/gen the standalone data-derived apworld, then stop.
if ($Greenfield) { & (Join-Path $Repo "greenfield\gen-greenfield.ps1") -Repo $Repo; exit $LASTEXITCODE }

# Rust client is now an in-repo submodule (was the sibling from-software-archipelago-clients).
$RustDir     = Join-Path $Repo "from-software-archipelago-clients"
$RustTarget  = "x86_64-pc-windows-msvc"
$RustDll     = Join-Path $RustDir "target\$RustTarget\release\eldenring_archipelago.dll"

$Me3Dir      = Join-Path $Repo "me3"                 # me3 profile + package live here
$Me3Package  = Join-Path $Me3Dir "ap-package"        # me3 VFS package: mirrors the game root (menu\hi, menu\low)
$Me3Profile  = Join-Path $Me3Dir "ap.me3"            # the .me3 ModProfile (TOML)
$Me3DllDest  = Join-Path $Me3Dir "eldenring_archipelago.dll"
$IconMenu    = Join-Path $Repo "build\ap_icon\menu"    # build_ap_icon.py (00_solo MENU_Knowledge hi-res variant, cosmetic)
$IconMenu01  = Join-Path $Repo "build\ap_icon01\menu"  # build_ap_icon.py --icon01 (01_common SB_Icon sheet -- the REAL icon)

function Step($msg) { Write-Host "`n==== $msg" -ForegroundColor Cyan }

# ----- server helpers -------------------------------------------------------------------------
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

if (-not ($Apworld -or $Generate -or $Rust -or $RustDeploy -or $Me3Deploy -or $Me3Restore -or $PureRuntime -or $Serve -or $Preflight -or $Clean)) {
    Get-Content $PSCommandPath | Select-Object -Skip 1 -First 22 | ForEach-Object { $_ -replace '^#\s?', '' }
    return
}

# ----- clean ----------------------------------------------------------------------------------
if ($Clean) {
    Stop-Server38281   # free :38281 + the output-zip lock
    Step "Cleaning build intermediates (cargo clean)"
    if (Test-Path (Join-Path $RustDir "Cargo.toml")) {
        Push-Location $RustDir
        try { cargo clean } finally { Pop-Location }
        Write-Host "  cargo clean done"
    } else {
        Write-Warning "  Rust submodule not found at $RustDir -- did the submodule init? (git submodule update --init)"
    }
}

# ----- package apworld ------------------------------------------------------------------------
if ($Apworld) {
    Step "Packaging eldenring.apworld from Archipelago\worlds\eldenring"
    $srcDir = Join-Path $ApDir "worlds\eldenring"
    if (-not (Test-Path (Join-Path $srcDir "__init__.py"))) { throw "apworld source not found: $srcDir\__init__.py" }
    $outFile = Join-Path $Repo "eldenring.apworld"
    Add-Type -AssemblyName System.IO.Compression.FileSystem | Out-Null
    # Exclude dev clutter: per-patch __init__ backups (*.bak*), bytecode, gen-time diag dumps.
    $excludeName  = @('*.bak', '*.bak_*', '*.pyc', '*.pyo', 'ER_SPHERE_TIERS_*', 'ER_DIAG_*')
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
    # Timestamped twin: the canonical name is overwritten in place, so freshness is invisible through
    # a same-name overwrite. This stamped copy witnesses THIS build (Always-timestamp convention).
    $apwStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $apwCopy  = Join-Path $Repo ("eldenring_{0}.apworld" -f $apwStamp)
    Copy-Item -LiteralPath $outFile -Destination $apwCopy -Force
    Write-Host ("  -> {0}  (timestamped copy)" -f $apwCopy) -ForegroundColor Green
}

# ----- generate multiworld --------------------------------------------------------------------
if ($Generate) {
    Step "Regenerating multiworld (Generate.py, players from Archipelago\Players)"
    if (-not (Test-Path (Join-Path $ApDir "Generate.py"))) { throw "AP checkout not found at $ApDir" }
    # Pre-gen guard: invalidate stale eldenring .pyc so a source edit can't be masked by cached
    # bytecode, and warn about per-game yaml options stranded at the document root. Warn-only.
    if (Test-Path (Join-Path $Repo "pregen.py")) {
        python (Join-Path $Repo "pregen.py") | Write-Host
    } else {
        Write-Warning "pregen.py not found -- skipping stale-bytecode/yaml guard"
    }
    # genretry: each Generate.py run picks a FRESH random seed, so a seed-dependent FillError usually
    # clears on a retry. Config/syntax errors (no 'FillError' in the log) are fatal immediately.
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
                if ($ShowGenDiag -and (Test-Path $genDiag)) { Get-Content $genDiag | Write-Host }
            }
            Write-Host ("generation raw log -> {0}" -f $genLog)  -ForegroundColor Green
            $erCounts = Select-String -LiteralPath $genLog -Pattern 'ER_COUNTS' -ErrorAction SilentlyContinue
            if ($erCounts) { foreach ($m in $erCounts) { Write-Host ("  " + $m.Line.Trim()) -ForegroundColor Green } }
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

# ----- rust client build ----------------------------------------------------------------------
# cargo test (er-codec/er-semver/er-logic pure-logic contract; on Windows also typechecks the
# in-process game module) THEN builds the injected cdylib for the MSVC target.
if ($Rust) {
    Step "Rust client: cargo test + cdylib build"
    if (-not (Test-Path (Join-Path $RustDir "Cargo.toml"))) { throw "Rust submodule not found at $RustDir -- run: git submodule update --init" }
    Step "  regenerate generated tables (tracker_regions.rs) from greenfield data"
    & python (Join-Path $Repo "tools\gen_location_regions.py")
    if ($LASTEXITCODE -ne 0) { throw "gen_location_regions.py FAILED -- tracker_regions.rs not regenerated (see output above)." }
    if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
        throw "cargo not found on PATH. Install rustup from https://rustup.rs, then re-open the shell."
    }
    if (-not ((rustup target list --installed 2>$null) -match $RustTarget)) {
        Write-Host "  installing rust target $RustTarget ..."
        rustup target add $RustTarget
        if ($LASTEXITCODE -ne 0) { throw "rustup target add $RustTarget failed" }
    }
    Push-Location $RustDir
    try {
        Step "  cargo test (pure-logic contract)"
        cargo test
        if ($LASTEXITCODE -ne 0) { throw "cargo test failed -- a pure-logic test broke OR the game module did not compile. See output above." }
        $cargoBuildArgs = @("build", "--release", "--target", $RustTarget, "-p", "eldenring-archipelago")
        Step ("  cargo {0} (injected cdylib)" -f ($cargoBuildArgs -join ' '))
        cargo @cargoBuildArgs
        if ($LASTEXITCODE -ne 0) { throw "cargo build failed -- see output above." }
    } finally { Pop-Location }
    if (-not (Test-Path $RustDll)) { throw "build reported success but DLL not found: $RustDll" }
    Write-Host "  -> $RustDll" -ForegroundColor Green
}

# ----- rust client deploy to EML (alt loader) -------------------------------------------------
# me3 is the primary loader (-Me3Deploy). -RustDeploy is the EML fallback: drop the DLL into mods\.
# EML auto-loads every mods\*.dll, so make sure the me3 native isn't ALSO loading it (double
# AddItemFunc hook = crash) -- use one loader at a time.
if ($RustDeploy) {
    Step "Deploying Rust client (eldenring_ap.dll) -> $ModsDir  (EML)"
    if (-not (Test-Path $RustDll)) { throw "Rust DLL not found at $RustDll -- run with -Rust first" }
    if (-not (Test-Path $ModsDir)) { New-Item -ItemType Directory -Path $ModsDir | Out-Null }
    Copy-Item $RustDll (Join-Path $ModsDir "eldenring_ap.dll") -Force
    Write-Host "  -> eldenring_ap.dll  (EML will load this)" -ForegroundColor Green
}

# ----- me3 (ModEngine3) deploy ----------------------------------------------------------------
# me3's VFS serves file overrides from a package folder and loads the client DLL as a native,
# against a VANILLA exe. -Me3Deploy (re)writes the profile, fills the package with the AP icon
# override + apconfig, and parks the EML client copy so it isn't double-loaded. Launch:
#   me3 launch --profile <repo>\me3\ap.me3
if ($Me3Deploy) {
    Step "me3 deploy (profile + package + config) -> $Me3Dir"
    if (-not (Test-Path $RustDll)) { throw "Rust DLL not found at $RustDll -- run with -Rust first" }

    # Stage the DLL into me3\ so it + apconfig.json share one stable dir. shared::Config reads
    # apconfig.json next to the DLL (current_module_directory), so the natives path points HERE,
    # not target\release (which cargo clean wipes).
    Copy-Item $RustDll $Me3DllDest -Force
    Write-Host "  client DLL -> $Me3DllDest"

    New-Item -ItemType Directory -Force -Path (Join-Path $Me3Package "menu\hi"), (Join-Path $Me3Package "menu\low") | Out-Null

    # AP icon override. 01_common.tpf.dcx (SB_Icon sprite-sheet cell for iconId 92, from
    # `build_ap_icon.py --icon01`) is the REAL shop/inventory icon. 00_solo.* is harmless extra.
    $copiedIcon = $false
    foreach ($sub in "hi", "low") {
        $dstSub = Join-Path $Me3Package "menu\$sub"
        $sheet = Join-Path $IconMenu01 "$sub\01_common.tpf.dcx"
        if (Test-Path $sheet) {
            Copy-Item $sheet $dstSub -Force
            Write-Host "  icon override: menu\$sub\01_common.tpf.dcx  (--icon01 sprite-sheet; the real one)"
            $copiedIcon = $true
        }
        $solo = Join-Path $IconMenu "$sub\00_solo.tpfbhd"
        if (Test-Path $solo) {
            Copy-Item $solo $dstSub -Force
            Copy-Item (Join-Path $IconMenu "$sub\00_solo.tpfbdt") $dstSub -Force
            Write-Host "  icon override: menu\$sub\00_solo.*  (hi-res variant)"
        }
    }
    if (-not $copiedIcon) {
        Write-Warning "  no 01_common.tpf.dcx at $IconMenu01 -- build it first:"
        Write-Warning '    python build_ap_icon.py --icon01 --icon-id 92 --black-to-alpha --bundles hi,low --menu "<game>\menu"'
    }

    # apconfig.json next to the staged DLL (url + slot; the flag-poll table travels in slot_data now).
    $apconfig = Join-Path $Repo "apconfig.json"
    if (Test-Path $apconfig) {
        Copy-Item $apconfig (Join-Path $Me3Dir "apconfig.json") -Force
        Write-Host "  apconfig.json -> $Me3Dir"
    } else { Write-Warning "  no apconfig.json at $Repo -- create one with `"url`" + `"slot`" (see shared\config.rs schema)" }

    # Sweep-flag bridge (2026-07-01 playtest gap: table was never next to the DLL -> 0 sweep groups).
    # flagpoll merge_table_file reads er_static_detection_table.json from the DLL's dir; it supplies
    # the overworld/castle sweep groups the retired baker used to write into apconfig (e.g. Castle
    # Morne 1044320800). Durable fix = emit sweepFlags in slot_data; this staging bridges until then.
    $sweepTable = Join-Path $Repo "Archipelago\worlds\eldenring\er_static_detection_table.json"
    if (Test-Path $sweepTable) {
        Copy-Item $sweepTable (Join-Path $Me3Dir "er_static_detection_table.json") -Force
        Write-Host "  er_static_detection_table.json -> $Me3Dir  (sweep-flag bridge)"
        # 2026-07-02: the client's mod_directory() resolves to the me3 INSTALL dir (where its logs
        # and ap_save_*.json land), NOT the profile dir where the DLL is staged -- confirmed live:
        # "static detection table absent at ...garyttierney\me3\...". Stage the table there too so
        # the sweep bridge actually finds it. (Durable fix stays: emit sweepFlags in slot_data.)
        $me3Install = Join-Path $env:LOCALAPPDATA "Programs\garyttierney\me3"
        if (Test-Path $me3Install) {
            Copy-Item $sweepTable (Join-Path $me3Install "er_static_detection_table.json") -Force
            Write-Host "  er_static_detection_table.json -> $me3Install  (client mod_directory)"
        } else { Write-Warning "  me3 install dir not found at $me3Install -- sweep table staged to profile dir only" }
    } else { Write-Warning "  no er_static_detection_table.json at Archipelago\worlds\eldenring -- sweep groups won't poll" }

    # Shop-check flags: client key_resolver reads shoplineup_flags.json from the DLL dir
    # (mod_directory), same staging as the sweep table. Maps shop rows -> eventFlag_forStock.
    $shopTable = Join-Path $Repo "Archipelago\worlds\eldenring\shoplineup_flags.json"
    if (Test-Path $shopTable) {
        Copy-Item $shopTable (Join-Path $Me3Dir "shoplineup_flags.json") -Force
        Write-Host "  shoplineup_flags.json -> $Me3Dir  (shop check flags)"
        $me3InstallShop = Join-Path $env:LOCALAPPDATA "Programs\garyttierney\me3"
        if (Test-Path $me3InstallShop) {
            Copy-Item $shopTable (Join-Path $me3InstallShop "shoplineup_flags.json") -Force
            Write-Host "  shoplineup_flags.json -> $me3InstallShop  (client mod_directory)"
        }
    } else { Write-Warning "  no shoplineup_flags.json at Archipelago\worlds\eldenring -- shop checks will not resolve" }

    # park the EML client copy so me3's native is the ONLY loader of eldenring_ap.dll
    $emlDll = Join-Path $ModsDir "eldenring_ap.dll"
    $emlOff = Join-Path $ModsDir "eldenring_ap.dll.me3off"
    if (Test-Path $emlDll) {
        if (Test-Path $emlOff) { Remove-Item $emlOff -Force }
        Rename-Item $emlDll $emlOff -Force
        Write-Host "  parked EML client -> eldenring_ap.dll.me3off (restore with -Me3Restore)"
    }

    # write the ModProfile. disable_arxan=true: me3 neuters Arxan on the vanilla exe (our client hooks
    # native code -- AddItemFunc -- which Arxan would otherwise revert).
    # Paths are RELATIVE to the profile's own directory (me3 resolves them against the .me3 file;
    # docs: "profiles can be stored anywhere, reference relative or absolute paths") -- the whole
    # me3\ folder is portable/zippable for onboarding, no machine-specific paths baked in.
    $profileText = @"
profileVersion = "v1"
savefile = "AP_me3.sl2"
disable_arxan = true

[[supports]]
game = "eldenring"

[[packages]]
path = 'ap-package'

[[natives]]
path = 'eldenring_archipelago.dll'
"@
    Set-Content -Path $Me3Profile -Value $profileText -Encoding UTF8
    Write-Host "  profile -> $Me3Profile" -ForegroundColor Green
    Write-Host "`nme3 ready (requires VANILLA game files -- NOT UXM-patched). Launch:" -ForegroundColor Cyan
    Write-Host "    me3 launch --profile `"$Me3Profile`""
}

if ($Me3Restore) {
    Step "me3 restore (un-park the EML client dll)"
    $emlDll = Join-Path $ModsDir "eldenring_ap.dll"
    $emlOff = Join-Path $ModsDir "eldenring_ap.dll.me3off"
    if (Test-Path $emlOff) {
        if (Test-Path $emlDll) { Remove-Item $emlDll -Force }
        Rename-Item $emlOff $emlDll -Force
        Write-Host "  restored EML client -> eldenring_ap.dll" -ForegroundColor Green
    } else { Write-Host "  (no eldenring_ap.dll.me3off to restore)" }
}

# ----- serve ----------------------------------------------------------------------------------
if ($Serve) {
    $zip = Get-ChildItem (Join-Path $ApDir "output") -Filter "AP_*.zip" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $zip) { throw "no multiworld zip in $ApDir\output -- run with -Generate first" }
    $inUse = Get-NetTCPConnection -LocalPort 38281 -State Listen -ErrorAction SilentlyContinue
    if ($inUse) {
        Write-Host "  port 38281 busy -- stopping stale AP server before relaunch" -ForegroundColor Yellow
        Stop-Server38281
    }
    Step "Launching AP server (new window): $($zip.Name)"
    Start-Server38281 $zip.FullName
    Write-Host "  server is listening on 38281" -ForegroundColor Green
    if ($PureRuntime) {
        Write-Host "`nPure-runtime ready (NO bake, vanilla Game\):" -ForegroundColor Green
        Write-Host "  - Rust client : $Me3DllDest  (loaded by me3 native)"
        Write-Host "  - Multiworld  : $($zip.FullName)"
        Write-Host "  - AP server   : localhost:38281"
        Write-Host "`nTo play: me3 launch --profile `"$Me3Profile`"  (vanilla game files)." -ForegroundColor Cyan
    }
}

# ----- preflight validation -------------------------------------------------------------------
# Pure-runtime cross-checks: seed of the newest gen, staged client dll + apconfig freshness, and
# a stale-server detector on :38281. (No baked regulation/location_flags to check anymore.)
if ($Preflight) {
    Step "Preflight validation (pure-runtime)"
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
        L "ER AP pure-runtime preflight  $ts"
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
        $strayFiles = Get-ChildItem (Join-Path $ApDir "Players") -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Extension -notin @(".yaml", ".yml") }
        if ($strayFiles) { L ("stray in Players\: {0}" -f (($strayFiles | ForEach-Object { $_.Name }) -join ", ")) }

        # newest generated multiworld + its seed (filename AP_<seed>.zip)
        $zip = Get-ChildItem (Join-Path $ApDir "output") -Filter "AP_*.zip" -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending | Select-Object -First 1
        $zipSeed = if ($zip) { $zip.BaseName -replace '^AP_', '' } else { $null }
        L ("newest zip  : {0}  (seed={1}; written={2})" -f $(if ($zip) { $zip.Name } else { "<none>" }), $zipSeed, $(if ($zip) { $zip.LastWriteTime } else { "" }))

        # staged apconfig (me3\) -- url + slot
        $apm = $null
        $apStaged = Join-Path $Me3Dir "apconfig.json"
        if (Test-Path $apStaged) { $apm = Get-Content $apStaged -Raw | ConvertFrom-Json }
        if ($apm) { L ("apconfig me3: slot={0} url={1}" -f $apm.slot, $apm.url) } else { L "apconfig me3: <missing>" }

        # staged client dll freshness
        if (Test-Path $Me3DllDest) { L ("client dll  : {0}  ({1})" -f $Me3DllDest, (Get-Item $Me3DllDest).LastWriteTime) }

        # server on 38281 (stale-server detector)
        $listen = Get-NetTCPConnection -LocalPort 38281 -State Listen -ErrorAction SilentlyContinue
        if ($listen) {
            $started = ""
            try { $started = (Get-Process -Id $listen.OwningProcess -ErrorAction SilentlyContinue).StartTime } catch {}
            L ("server 38281: LISTENING (pid={0} started={1})" -f $listen.OwningProcess, $started)
        } else { L "server 38281: no listener" }

        L ""
        L "---- verdicts ----"
        Check "newest multiworld zip present"    ($null -ne $zip) ("newest={0}" -f $(if ($zip) { $zip.Name }))
        # url is now OPTIONAL: the in-client connect overlay collects server/slot/password in-game,
        # so a staged apconfig only needs a slot (a blank url just means "enter it in-game").
        Check "apconfig staged (slot; url optional, entered in-game)" ($apm -and $apm.slot) ("slot={0} url={1}" -f $(if($apm){$apm.slot}), $(if($apm -and $apm.url){$apm.url}else{"<entered in-game>"}))
        Check "staged slot is an intended player" ($apm -and ($slotNames -contains $apm.slot)) ("staged='{0}' players=[{1}]" -f $(if($apm){$apm.slot}), ($slotNames -join ", "))
        Check "client dll staged"                (Test-Path $Me3DllDest) $Me3DllDest
        Check "Players\ has no stray files"       (-not $strayFiles) (($strayFiles | ForEach-Object { $_.Name }) -join ", ")

        L ""
        if ($script:fails -eq 0) {
            L "PREFLIGHT: PASS -- staged client + apconfig look consistent with the newest gen."
        } else {
            L ("PREFLIGHT: {0} FAILURE(S) -- do NOT trust this build for a sync." -f $script:fails)
        }
    } catch {
        L ("preflight error: {0}" -f $_)
    }
    $lines | Set-Content -Path $log -Encoding UTF8
    Write-Host ("`npreflight log -> {0}" -f $log) -ForegroundColor Green
    if ($script:fails -gt 0) { Write-Warning "Preflight found problems (see verdicts above)." }
}
