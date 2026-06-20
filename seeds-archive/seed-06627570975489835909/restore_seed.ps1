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
