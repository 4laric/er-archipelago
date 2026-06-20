<#
  snapshot_seed.ps1 -- capture the Windows-only halves of this seed so the save stays resumable.
  Run this AFTER your final play session for the seed (it grabs the live save + .apsave).

  Captures into this archive folder:
    - game-files\   : the 163 deployed mod files from deploy_manifest.txt (regulation.bin, event\, msg\, script\, map\)
    - mods\         : apconfig.json + archipelago.dll  (seed/server pointer + client)
    - save\<steamid>\ : your ER save (*.sl2 / *.sl2.bak)
    - ap-server\    : refreshes the live AP multidata (.zip) + server progress (.apsave)

  Usage:
    cd <this folder>;  .\snapshot_seed.ps1
    (optional) .\snapshot_seed.ps1 -GameDir "D:\Steam\...\ELDEN RING\Game"
#>
param(
  [string]$GameDir = "C:\Program Files (x86)\Steam\steamapps\common\ELDEN RING\Game"
)
$ErrorActionPreference = "Stop"
$Seed = "97943139363536579023"
$Dest = $PSScriptRoot
$Repo = (Resolve-Path (Join-Path $Dest "..\..")).Path   # seeds-archive\seed-XXX -> repo root
Write-Host "Snapshotting seed $Seed" -ForegroundColor Cyan
Write-Host "  archive : $Dest"
Write-Host "  repo    : $Repo"
Write-Host "  game    : $GameDir"

# 1) deployed mod files (exact set from the manifest) ------------------------
$manifest = Join-Path $Dest "deploy_manifest.txt"
$prefix = ($GameDir.TrimEnd('\')) + '\'
$n = 0; $miss = 0
Get-Content $manifest | Where-Object { $_ -match '\S' } | ForEach-Object {
  $src = $_.Trim()
  if (-not $src.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
    # manifest baked with a different GameDir -> remap onto the real one
    $src = Join-Path $GameDir ($src -replace '^.*?ELDEN RING\\Game\\','')
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

# 2) mods\ : client + apconfig ----------------------------------------------
$modsOut = Join-Path $Dest "mods"; New-Item -ItemType Directory -Force -Path $modsOut | Out-Null
foreach ($f in "apconfig.json","archipelago.dll") {
  $s = Join-Path $GameDir "mods\$f"
  if (Test-Path $s) { Copy-Item -LiteralPath $s -Destination $modsOut -Force; Write-Host "  mods\$f" -ForegroundColor Green }
  else { Write-Warning "missing: $s" }
}

# 3) ER save (*.sl2) ---------------------------------------------------------
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

# 4) refresh the live AP server state ---------------------------------------
$apOut = Join-Path $Dest "ap-server"; New-Item -ItemType Directory -Force -Path $apOut | Out-Null
foreach ($ext in "zip","apsave") {
  $s = Join-Path $Repo "Archipelago\output\AP_$Seed.$ext"
  if (Test-Path $s) { Copy-Item -LiteralPath $s -Destination $apOut -Force; Write-Host "  ap-server\AP_$Seed.$ext (refreshed)" -ForegroundColor Green }
}

# 5) stamp -------------------------------------------------------------------
"snapshot taken : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`nseed           : $Seed`nslot           : Alaric`ngame dir       : $GameDir" |
  Set-Content (Join-Path $Dest "snapshot-info.txt")
Write-Host "`nDone. Seed $Seed is fully archived in:`n  $Dest" -ForegroundColor Cyan
