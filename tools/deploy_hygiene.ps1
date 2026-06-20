#requires -Version 5
<#
  deploy_hygiene.ps1 -- manifest-scoped vanilla restore for the ER bake/deploy.

  WHY: build.ps1 -Deploy writes mod files directly over the UXM-unpacked vanilla in the game
  root and only OVERWRITES (never removes); -Clean only nukes build intermediates. So a file
  modded by a previous run that the current bake doesn't regenerate (classically the enemy-rando
  map\ MSBs -- 'map only exists for enemy bakes') stays LIVE, contaminating the next run (e.g. a
  DLC-only seed inheriting the last enemy run's MSBs -> ?NpcName? / garbled msgs / crashes).

  FIX: keep a manifest of what each deploy wrote; before the next deploy, restore those exact
  files from the pristine source SoulsRandomizers\diste\Vanilla (flat index, matched by filename),
  then let the deploy overlay the new bake.

  USAGE (wrap a deploy):
    .\tools\deploy_hygiene.ps1 -Restore      # BEFORE bake/deploy: revert last run's files to vanilla
    .\build.ps1 -All                         # (or -Bake -Deploy) -- your normal pipeline
    .\tools\deploy_hygiene.ps1 -Snapshot     # AFTER deploy: record what was just deployed

  Or wire the two calls into build.ps1's Deploy step (Restore at the top, Snapshot at the end).
  First run has no manifest (no-op restore); do a one-time full vanilla restore once to clear any
  pre-existing stale files, then this keeps every run hermetic.
#>
[CmdletBinding()]
param(
    [switch]$Restore,
    [switch]$Snapshot,
    [string]$GameDir = "C:\Program Files (x86)\Steam\steamapps\common\ELDEN RING\Game"
)
$ErrorActionPreference = "Stop"

$Repo       = Split-Path $PSScriptRoot -Parent          # tools\ -> repo root
$RandoDir   = Join-Path $Repo "SoulsRandomizers"
$VanillaDir = Join-Path $RandoDir "diste\Vanilla"        # pristine source (1347 MSBs, 589 emevd, msg\, regulation)
$Manifest   = Join-Path $Repo "deploy_manifest.txt"
$Categories = @("event","msg","script","map","menu")     # mirrors build.ps1's Deploy override dirs

function Build-VanillaIndex {
    $idx = @{}
    if (Test-Path $VanillaDir) {
        Get-ChildItem $VanillaDir -Recurse -File | ForEach-Object { $idx[$_.Name] = $_.FullName }
    }
    return $idx
}

function Get-DeployTargets {
    # The game-root dest paths the CURRENT bake would deploy (mirrors build.ps1's Deploy copy logic),
    # so the manifest can be computed from the bake outputs without instrumenting the copy loop.
    $t = New-Object System.Collections.Generic.List[string]
    if (Test-Path (Join-Path $RandoDir "regulation.bin")) { [void]$t.Add((Join-Path $GameDir "regulation.bin")) }
    foreach ($dir in $Categories) {
        $src = Join-Path $RandoDir $dir
        if (Test-Path $src) {
            Get-ChildItem $src -Recurse -File | ForEach-Object {
                $rel = $_.FullName.Substring($src.Length).TrimStart('\')
                [void]$t.Add((Join-Path (Join-Path $GameDir $dir) $rel))
            }
        }
    }
    return $t
}

if ($Restore) {
    if (-not (Test-Path $Manifest)) {
        Write-Host "No manifest ($Manifest) -- nothing to restore (first run / already clean)."
    } else {
        $idx = Build-VanillaIndex
        if ($idx.Count -eq 0) { throw "Vanilla source missing/empty: $VanillaDir" }
        $restored = 0; $removed = 0; $skipped = 0
        foreach ($p in (Get-Content $Manifest)) {
            if (-not $p -or -not (Test-Path $p)) { continue }
            $name = Split-Path $p -Leaf
            if ($idx.ContainsKey($name)) { Copy-Item $idx[$name] $p -Force; $restored++ }
            elseif ($name -ieq "regulation.bin") { $skipped++ }   # rebaked by the next bake anyway
            else { Remove-Item $p -Force; $removed++ }            # tool-added file with no vanilla counterpart
        }
        Remove-Item $Manifest -Force
        Write-Host "Restore: $restored vanilla restored, $removed tool-only removed, $skipped skipped. Manifest cleared."
    }
}

if ($Snapshot) {
    $targets = Get-DeployTargets
    if ($targets.Count -eq 0) { Write-Warning "No bake outputs found under $RandoDir -- did the bake run? Manifest NOT written." }
    else {
        $targets | Set-Content $Manifest -Encoding UTF8
        Write-Host "Snapshot: recorded $($targets.Count) deployed file(s) -> $Manifest"
    }
}

if (-not $Restore -and -not $Snapshot) {
    Write-Host "Usage:"
    Write-Host "  .\tools\deploy_hygiene.ps1 -Restore    # BEFORE deploy: revert last run's game files to vanilla"
    Write-Host "  .\tools\deploy_hygiene.ps1 -Snapshot   # AFTER deploy: record what was deployed (for next restore)"
}
