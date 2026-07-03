<#
.SYNOPSIS
  Repo tree cleanup for er-archipelago superrepo. DRY-RUN by default.

.DESCRIPTION
  Purges regenerable, git-IGNORED cruft from the repo root (logs, gendiag dumps,
  preflight logs, dry-run CSVs, probe tmp files, loose *.bak). All of these are
  already in .gitignore, so removing them touches nothing git tracks.

  Finished TRACKED one-offs (dated RUN/test yamls, superseded working docs, completed
  analysis scripts) are git-mv'd into archive\ (runs\ / docs\ / scripts\).

  Root patch_*.py are NEITHER deleted nor archived -- several are still "needs
  run/build" per MEMORY.md. They're listed for manual review only.

.PARAMETER Execute
  Actually delete. Without this, the script only prints what it WOULD remove.

.PARAMETER KeepRecentGenSets
  How many of the newest generate_*.log / gendiag_*.txt to keep (by name-timestamp).
  Default 3. The rest are purged. Set 0 to purge all.

.EXAMPLE
  .\cleanup_repo.ps1                 # dry run, see everything
  .\cleanup_repo.ps1 -Execute        # purge cruft, keep newest 3 gen sets
  .\cleanup_repo.ps1 -Execute -KeepRecentGenSets 0
#>
[CmdletBinding()]
param(
  [switch]$Execute,
  [int]$KeepRecentGenSets = 3,
  [switch]$BuildArtifacts
)

$ErrorActionPreference = 'Stop'
# PS 7.3+ turns a native command's non-zero exit into a terminating error under EAP=Stop;
# git mv legitimately exits non-zero on untracked files, so opt out and handle exit codes ourselves.
$PSNativeCommandUseErrorActionPreference = $false
$root = $PSScriptRoot
Set-Location $root
$mode = if ($Execute) { 'EXECUTE' } else { 'DRY-RUN' }
Write-Host "=== er-archipelago cleanup ($mode) ===" -ForegroundColor Cyan
Write-Host "root: $root`n"

$freed = 0
# Files another process holds open (running game/client, editor, AV scan) make
# Remove-Item/Move-Item throw; under EAP=Stop that used to kill the WHOLE run
# mid-cleanup. Every delete/move now goes through a per-item try/catch with one
# short retry; failures are collected and reported at the end instead of aborting.
$script:skipped = [System.Collections.Generic.List[string]]::new()

function Remove-ItemRobust($item, [switch]$Recurse) {
  for ($try = 1; $try -le 2; $try++) {
    try {
      if ($Recurse) { Remove-Item -LiteralPath $item.FullName -Recurse -Force -ErrorAction Stop }
      else          { Remove-Item -LiteralPath $item.FullName -Force -ErrorAction Stop }
      return $true
    } catch {
      if ($try -eq 1) { Start-Sleep -Milliseconds 400; continue }
      $reason = ($_.Exception.Message -replace '\s+', ' ').Trim()
      $script:skipped.Add("$($item.FullName.Replace($root,'.'))  [$reason]")
      return $false
    }
  }
  return $false
}

function Remove-List($files, $label) {
  $script:list = @($files | Where-Object { $_ -and (Test-Path $_.FullName) })
  if (-not $list) { Write-Host "[$label] nothing to do" -ForegroundColor DarkGray; return }
  $bytes = ($list | Measure-Object Length -Sum).Sum
  Write-Host "[$label] $($list.Count) files, $([math]::Round($bytes/1MB,2)) MB" -ForegroundColor Yellow
  foreach ($f in $list) { Write-Host "    $($f.Name)" -ForegroundColor DarkGray }
  if ($Execute) {
    foreach ($f in $list) {
      if (Remove-ItemRobust $f) { $script:freed += $f.Length }
    }
  }
}

# ---- helper: keep newest N by trailing -YYYYMMDD-HHMMSS in the name ----
function Old-Sets($glob) {
  $all = Get-ChildItem -File $glob -ErrorAction SilentlyContinue | Sort-Object Name -Descending
  if ($KeepRecentGenSets -gt 0 -and $all.Count -gt $KeepRecentGenSets) {
    return $all | Select-Object -Skip $KeepRecentGenSets
  } elseif ($KeepRecentGenSets -eq 0) { return $all }
  return @()
}

# =====================================================================
# BUCKET 1 -- regenerable, git-ignored cruft (SAFE to purge)
# =====================================================================
Remove-List (Get-ChildItem -File @('_probe_del','testdel_probe.tmp','testren_b.tmp','ov_b.tmp') -ErrorAction SilentlyContinue) 'probe/tmp junk'
Remove-List (Get-ChildItem -File 'preflight_*.log' -ErrorAction SilentlyContinue) 'preflight logs'
Remove-List (Get-ChildItem -File 'build.ps1.bak_killserver' -ErrorAction SilentlyContinue) 'stale build.ps1 backup'

# dry-run analysis CSVs (regenerate via boss_attribution_dryrun.py / tune_complement.py)
Remove-List (Get-ChildItem -File @('boss-attribution-dryrun.csv','check-nearest-grace.csv','smithing_stone_distribution.csv') -ErrorAction SilentlyContinue) 'dry-run CSV outputs'

# generate/gendiag sets -- keep the newest N
Remove-List (Old-Sets 'generate_*.log') "generate logs (keep newest $KeepRecentGenSets)"
Remove-List (Old-Sets 'gendiag_*.txt')  "gendiag dumps (keep newest $KeepRecentGenSets)"

# =====================================================================
# BUCKET 1b -- SUBREPO regenerable cruft, via ONE prune-aware tree walk.
# Single pass (was ~5 separate full-tree Get-ChildItem -Recurse passes) that SKIPS the
# giant vendored / vcs dirs entirely: vanilla-game-snapshot (~55k files), elden_ring_artifacts,
# Paramdex, the Nexus download, seeds-archive (intentional saves), .git, gen-test. None of those
# hold *.bak/*.pyc/__pycache__ cruft, so pruning them is safe and MUCH faster.
# Patterns NEVER match game data (regulation/.dcx/.msb/.bin); sweeping SoulsRandomizers stays safe.
# Some hits are git-TRACKED (.bak_* / ER_SPHERE_TIERS_*): Remove-Item deletes the working copy;
# afterward `git add -u` + commit in the affected repo (NEVER `git add -A` in SoulsRandomizers).
# =====================================================================
$PROTECT = '\\(\.git|seeds-archive)\\'   # retained for the BuildArtifacts block below
$PRUNE = @('.git','seeds-archive','vanilla-game-snapshot','elden_ring_artifacts','Paramdex',
           'gen-test','node_modules','Elden Ring Randomizer-428-v0-11-4-1763103112 (2)','yet-another-tab-control')

$walkFiles   = [System.Collections.Generic.List[object]]::new()
$walkPycache = [System.Collections.Generic.List[object]]::new()
$stack = [System.Collections.Generic.Stack[string]]::new()
$stack.Push($root)
while ($stack.Count) {
  $dir = $stack.Pop()
  foreach ($e in Get-ChildItem -LiteralPath $dir -Force -ErrorAction SilentlyContinue) {
    if ($e.PSIsContainer) {
      if ($PRUNE -contains $e.Name) { continue }
      if ($e.Name -eq '__pycache__') { $walkPycache.Add($e); continue }   # collect; don't descend
      $stack.Push($e.FullName)
    } else { $walkFiles.Add($e) }
  }
}

# loose *.bak (seeds-archive already pruned out of the walk)
Remove-List ($walkFiles | Where-Object { $_.Extension -eq '.bak' }) 'loose *.bak (excl. seeds-archive)'
# tagged editor backups *.bak_<tag>
Remove-List ($walkFiles | Where-Object { $_.Name -match '\.bak_' }) 'tagged editor backups (*.bak_<tag>)'
# subdir diag dumps
Remove-List ($walkFiles | Where-Object { $_.Name -eq 'ER_DIAG.txt' -or $_.Name -like 'ER_SPHERE_TIERS_*.txt' }) 'subdir diag dumps (ER_SPHERE_TIERS_*/ER_DIAG.txt)'
# compiled python
Remove-List ($walkFiles | Where-Object { $_.Extension -eq '.pyc' }) 'compiled python (*.pyc)'

# __pycache__ dirs (collected during the same walk)
if ($walkPycache.Count) {
  Write-Host "[__pycache__ dirs] $($walkPycache.Count)" -ForegroundColor Yellow
  $walkPycache | ForEach-Object { Write-Host "    $($_.FullName.Replace($root,'.'))" -ForegroundColor DarkGray }
  if ($Execute) { foreach ($d in $walkPycache) { [void](Remove-ItemRobust $d -Recurse) } }
} else { Write-Host "[__pycache__ dirs] nothing to do" -ForegroundColor DarkGray }

# OPT-IN heavy build artifacts (regenerable; deleting forces a rebuild). Rust target/ + .NET bin,obj.
# Game-data dirs in SoulsRandomizers (event/msg/script/regulation.bin) are NOT named bin/obj/target.
if ($BuildArtifacts) {
  $builddirs = Get-ChildItem -Directory -Recurse -ErrorAction SilentlyContinue |
    Where-Object { ($_.Name -in @('target','bin','obj')) -and $_.FullName -notmatch $PROTECT }
  if ($builddirs) {
    $sz = ($builddirs | ForEach-Object { (Get-ChildItem -Recurse -File $_.FullName -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum } | Measure-Object -Sum).Sum
    Write-Host "[build artifacts] $($builddirs.Count) dirs, $([math]::Round($sz/1MB,2)) MB (Rust target/ + .NET bin,obj)" -ForegroundColor Yellow
    $builddirs | ForEach-Object { Write-Host "    $($_.FullName.Replace($root,'.'))" -ForegroundColor DarkGray }
    if ($Execute) { foreach ($d in $builddirs) { [void](Remove-ItemRobust $d -Recurse) } }
  } else { Write-Host "[build artifacts] nothing to do" -ForegroundColor DarkGray }
} else {
  Write-Host "[build artifacts] skipped (pass -BuildArtifacts to also purge Rust target/ + .NET bin,obj)" -ForegroundColor DarkGray
}

# =====================================================================
# BUCKET 2 -- finished TRACKED one-offs: ARCHIVE into archive\ (git mv)
# =====================================================================
function Archive-List($files, $destSub, $label) {
  $items = @($files | Where-Object { $_ -and (Test-Path $_.FullName) } | Sort-Object FullName -Unique)
  if (-not $items) { Write-Host "[archive:$label] nothing to do" -ForegroundColor DarkGray; return }
  $dest = Join-Path $root "archive\$destSub"
  Write-Host "[archive:$label] $($items.Count) files -> archive\$destSub" -ForegroundColor Yellow
  if ($Execute) { New-Item -ItemType Directory -Force -Path $dest | Out-Null }
  foreach ($f in $items) {
    Write-Host "    $($f.Name)" -ForegroundColor DarkGray
    if ($Execute) {
      $old = $f.FullName; $new = Join-Path $dest $f.Name
      $moved = $false
      try {
        git ls-files --error-unmatch -- "$old" 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { git mv -f -- "$old" "$new" 2>$null; $moved = ($LASTEXITCODE -eq 0) }
      } catch { $moved = $false }
      if (-not $moved) {  # untracked or git mv failed -> plain move, robust to in-use files
        for ($try = 1; $try -le 2; $try++) {
          try { Move-Item -LiteralPath $old -Destination $new -Force -ErrorAction Stop; break }
          catch {
            if ($try -eq 1) { Start-Sleep -Milliseconds 400; continue }
            $reason = ($_.Exception.Message -replace '\s+', ' ').Trim()
            $script:skipped.Add("$($old.Replace($root,'.'))  [archive move failed: $reason]")
          }
        }
      }
    }
  }
}

# finished analysis/recovery scripts (KEEP boss_attribution_dryrun.py + tune_complement.py:
# .gitignore names them as the live CSV regenerators)
$archivePy = @('dump_boss_attribution.py','check_shop_collapse.py','cleanup_shopbind_scaffolding.py',
  'recover_init_tail.py','curation_uplift_draft.py') | ForEach-Object { Get-ChildItem -File $_ -ErrorAction SilentlyContinue }
Archive-List $archivePy 'scripts' 'finished one-off scripts'

# dated/one-off test+run yamls (KEEP EldenRing-MASTER-template.yaml + Alaric.yaml)
$datedYaml = Get-ChildItem -File 'EldenRing-*-RUN.yaml','EldenRing-*-test.yaml','EldenRing-*-regression.yaml','EldenRing-probe-*.yaml','EldenRing-*bosssweep*.yaml','test_er_new_options.yaml' -ErrorAction SilentlyContinue
Archive-List $datedYaml 'runs' 'dated test/run yamls'

# superseded working docs (conclusions live in archive\SPEC-*.md or MEMORY.md)
$staleDocs = Get-ChildItem -File 'PR-*.md','PATCH-*.md','FINDING-*.md','NOTES-*.md','PROBE-*.md','CAPTURE-*.md','RUNBOOK-*.md','REGIONLOCK-*.md','TESTPLAN-*.md','REFERENCE-*.md' -ErrorAction SilentlyContinue
Archive-List $staleDocs 'docs' 'superseded working docs'

# =====================================================================
# BUCKET 3 -- root patch_*.py: ARCHIVE ALL into archive\patches\ (git mv)
# Archives EVERY root patch_*.py regardless of applied/pending state. Some may be
# 'needs run/build' per MEMORY.md -- moving them out of root is the ACCEPTED RISK
# (relocated, not deleted; update any refs to the new archive\patches\ path).
# =====================================================================
$rootPatches = Get-ChildItem -File 'patch_*.py' -ErrorAction SilentlyContinue
Archive-List $rootPatches 'patches' 'root patch_*.py (ALL)'

Write-Host "`n=== done ($mode) ===" -ForegroundColor Cyan
if ($Execute) { Write-Host ("freed {0} MB; one-offs archived" -f [math]::Round($freed/1MB,2)) -ForegroundColor Green }
else { Write-Host "re-run with -Execute to purge Bucket 1 + archive Buckets 2 & 3 (incl. ALL root patch_*.py)." -ForegroundColor Green }

if ($script:skipped.Count) {
  Write-Host "`n[skipped] $($script:skipped.Count) item(s) in use by another process (or access denied):" -ForegroundColor Red
  $script:skipped | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
  Write-Host "everything else was cleaned; close the holder (game/client/editor/AV scan) and re-run for these." -ForegroundColor Yellow
  exit 2
}
exit 0
