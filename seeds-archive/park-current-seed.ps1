<#
  park-current-seed.ps1 -- snapshot WHATEVER seed is currently deployed, into its own
  seeds-archive\seed-<seed>\ folder. Auto-detects the seed + slot from the live
  Game\mods\apconfig.json, so you never have to edit a seed number by hand.

  Run this AFTER your final play session for the current seed (quit ER first so the
  .sl2 is flushed). It captures the four Windows-only halves and drops a matching
  restore_seed.ps1 into the folder so the seed is fully self-contained / resumable.

  Captured into seeds-archive\seed-<seed>\:
    - deploy_manifest.txt : the exact deployed mod-file list (copied from repo root)
    - game-files\         : every file in that manifest (regulation.bin, event/msg/script/map)
    - mods\               : apconfig.json + archipelago.dll
    - save\<steamid>\     : your ER save (*.sl2 / *.sl2.bak)
    - ap-server\          : AP multidata (.zip) + server progress (.apsave)
    - restore_seed.ps1    : generated; redeploys this seed later

  Usage:
    cd <seeds-archive folder>;  .\park-current-seed.ps1
    (optional) .\park-current-seed.ps1 -GameDir "D:\Steam\...\ELDEN RING\Game"
#>
param(
  [string]$GameDir = "C:\Program Files (x86)\Steam\steamapps\common\ELDEN RING\Game"
)
$ErrorActionPreference = "Stop"
$ScriptRoot = $PSScriptRoot                                  # seeds-archive\
$Repo = (Resolve-Path (Join-Path $ScriptRoot "..")).Path     # repo root

# 0) detect the currently-deployed seed -------------------------------------
$cfgPath = Join-Path $GameDir "mods\apconfig.json"
if (-not (Test-Path $cfgPath)) { throw "no apconfig.json at $cfgPath -- is a seed deployed?" }
$cfg  = Get-Content $cfgPath -Raw | ConvertFrom-Json
$Seed = "$($cfg.seed)"
$Slot = "$($cfg.slot)"
if ([string]::IsNullOrWhiteSpace($Seed)) { throw "apconfig.json has no 'seed' field" }
Write-Host "Parking current seed $Seed (slot $Slot)" -ForegroundColor Cyan

$Dest = Join-Path $ScriptRoot "seed-$Seed"
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
Write-Host "  archive : $Dest"

# 1) deploy manifest (snapshot the current one for a reproducible capture) ---
$manifest = Join-Path $Repo "deploy_manifest.txt"
if (-not (Test-Path $manifest)) { throw "deploy_manifest.txt missing at repo root: $manifest" }
Copy-Item -LiteralPath $manifest -Destination (Join-Path $Dest "deploy_manifest.txt") -Force

# 2) deployed mod files (exact set from the manifest) ------------------------
$prefix = ($GameDir.TrimEnd('\')) + '\'
$n = 0; $miss = 0
Get-Content (Join-Path $Dest "deploy_manifest.txt") | Where-Object { $_ -match '\S' } | ForEach-Object {
  $src = $_.Trim()
  if (-not $src.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
    $src = Join-Path $GameDir ($src -replace '^.*?ELDEN RING\\Game\\','')   # remap onto real GameDir
  }
  $rel = $src.Substring($prefix.Length)
  $out = Join-Path (Join-Path $Dest "game-files") $rel
  if (Test-Path $src) {
    New-Item -ItemType Directory -Force -Path (Split-Path $out) | Out-Null
    Copy-Item -LiteralPath $src -Destination $out -Force
    $n++
  } else { Write-Warning "missing: $src"; $miss++ }
}
Write-Host "  game-files copied: $n  (missing: $miss)" -ForegroundColor Green

# 3) mods\ : client + apconfig ----------------------------------------------
$modsOut = Join-Path $Dest "mods"; New-Item -ItemType Directory -Force -Path $modsOut | Out-Null
foreach ($f in "apconfig.json","archipelago.dll") {
  $s = Join-Path $GameDir "mods\$f"
  if (Test-Path $s) { Copy-Item -LiteralPath $s -Destination $modsOut -Force; Write-Host "  mods\$f" -ForegroundColor Green }
  else { Write-Warning "missing: $s" }
}

# 4) ER save (*.sl2) ---------------------------------------------------------
$saveRoot = Join-Path $env:APPDATA "EldenRing"
if (Test-Path $saveRoot) {
  Get-ChildItem $saveRoot -Directory | ForEach-Object {
    $files = Get-ChildItem $_.FullName -Filter *.sl2* -ErrorAction SilentlyContinue
    if ($files) {
      $so = Join-Path (Join-Path $Dest "save") $_.Name
      New-Item -ItemType Directory -Force -Path $so | Out-Null
      $files | Copy-Item -Destination $so -Force
      Write-Host "  save: $($_.Name) ($($files.Count) file(s))" -ForegroundColor Green
    }
  }
} else { Write-Warning "no EldenRing save folder at $saveRoot" }

# 5) refresh the live AP server state ---------------------------------------
$apOut = Join-Path $Dest "ap-server"; New-Item -ItemType Directory -Force -Path $apOut | Out-Null
foreach ($ext in "zip","apsave") {
  $s = Join-Path $Repo "Archipelago\output\AP_$Seed.$ext"
  if (Test-Path $s) { Copy-Item -LiteralPath $s -Destination $apOut -Force; Write-Host "  ap-server\AP_$Seed.$ext (refreshed)" -ForegroundColor Green }
  else { Write-Warning "missing AP $ext for $Seed in Archipelago\output -- host/run the server before parking to capture progress" }
}

# 6) generate a matching restore_seed.ps1 (seed derived from the folder name)-
$restorePath = Join-Path $Dest "restore_seed.ps1"
$restoreBody = @'
<#
  restore_seed.ps1 -- redeploy this archived seed so the paired save loads again.
  Seed is read from this folder's name (seed-<seed>). Backs up whatever is currently
  in place before overwriting. Use -SkipSave to redeploy without touching your save.
#>
param(
  [string]$GameDir = "C:\Program Files (x86)\Steam\steamapps\common\ELDEN RING\Game",
  [switch]$SkipSave
)
$ErrorActionPreference = "Stop"
$Dest = $PSScriptRoot
$Seed = (Split-Path $Dest -Leaf) -replace '^seed-',''
$Repo = (Resolve-Path (Join-Path $Dest "..\..")).Path
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$bk = Join-Path $Dest "_pre-restore-backup-$stamp"
Write-Host "Restoring seed $Seed" -ForegroundColor Cyan

# 1) game files
$gf = Join-Path $Dest "game-files"
if (-not (Test-Path $gf)) { throw "game-files\ missing -- park this seed first." }
Get-ChildItem $gf -Recurse -File | ForEach-Object {
  $rel = $_.FullName.Substring($gf.Length).TrimStart('\')
  $tgt = Join-Path $GameDir $rel
  if (Test-Path $tgt) {
    $b = Join-Path (Join-Path $bk "game-files") $rel
    New-Item -ItemType Directory -Force -Path (Split-Path $b) | Out-Null
    Copy-Item -LiteralPath $tgt -Destination $b -Force
  }
  New-Item -ItemType Directory -Force -Path (Split-Path $tgt) | Out-Null
  Copy-Item -LiteralPath $_.FullName -Destination $tgt -Force
}
Write-Host "  game files restored" -ForegroundColor Green

# 2) mods
$md = Join-Path $Dest "mods"
if (Test-Path $md) {
  Get-ChildItem $md -File | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $GameDir "mods\$($_.Name)") -Force
  }
  Write-Host "  mods restored" -ForegroundColor Green
}

# 3) AP server files
$apIn = Join-Path $Dest "ap-server"; $apOut = Join-Path $Repo "Archipelago\output"
New-Item -ItemType Directory -Force -Path $apOut | Out-Null
foreach ($ext in "zip","apsave") {
  $s = Join-Path $apIn "AP_$Seed.$ext"
  if (Test-Path $s) { Copy-Item -LiteralPath $s -Destination $apOut -Force }
}
Write-Host "  AP multidata + .apsave restored to Archipelago\output" -ForegroundColor Green

# 4) save
if (-not $SkipSave) {
  $saveArc = Join-Path $Dest "save"
  if (Test-Path $saveArc) {
    Get-ChildItem $saveArc -Directory | ForEach-Object {
      $tgtDir = Join-Path (Join-Path $env:APPDATA "EldenRing") $_.Name
      if (Test-Path $tgtDir) {
        $b = Join-Path (Join-Path $bk "save") $_.Name
        New-Item -ItemType Directory -Force -Path $b | Out-Null
        Get-ChildItem $tgtDir -Filter *.sl2* | Copy-Item -Destination $b -Force
      } else { New-Item -ItemType Directory -Force -Path $tgtDir | Out-Null }
      Get-ChildItem $_.FullName -File | Copy-Item -Destination $tgtDir -Force
      Write-Host "  save restored: $($_.Name)" -ForegroundColor Green
    }
  }
} else { Write-Host "  (save restore skipped)" -ForegroundColor Yellow }

Write-Host "`nRestored. Backup of what was replaced: $bk" -ForegroundColor Cyan
Write-Host "Next: serve AP_$Seed.zip, launch ER via the mod loader, Load Game." -ForegroundColor Cyan
'@
Set-Content -LiteralPath $restorePath -Value $restoreBody -Encoding UTF8

# 7) stamp -------------------------------------------------------------------
"snapshot taken : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`nseed           : $Seed`nslot           : $Slot`ngame dir       : $GameDir" |
  Set-Content (Join-Path $Dest "snapshot-info.txt")
Write-Host "`nDone. Seed $Seed is fully archived in:`n  $Dest" -ForegroundColor Cyan
Write-Host "Resume later with:  cd `"$Dest`"; .\restore_seed.ps1" -ForegroundColor Cyan
