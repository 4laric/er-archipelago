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
$root = $PSScriptRoot
Set-Location $root
$mode = if ($Execute) { 'EXECUTE' } else { 'DRY-RUN' }
Write-Host "=== er-archipelago cleanup ($mode) ===" -ForegroundColor Cyan
Write-Host "root: $root`n"

$freed = 0
function Remove-List($files, $label) {
  $script:list = @($files | Where-Object { $_ -and (Test-Path $_.FullName) })
  if (-not $list) { Write-Host "[$label] nothing to do" -ForegroundColor DarkGray; return }
  $bytes = ($list | Measure-Object Length -Sum).Sum
  Write-Host "[$label] $($list.Count) files, $([math]::Round($bytes/1MB,2)) MB" -ForegroundColor Yellow
  foreach ($f in $list) { Write-Host "    $($f.Name)" -ForegroundColor DarkGray }
  if ($Execute) { $list | Remove-Item -Force; $script:freed += $bytes }
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

# loose *.bak across the tree, EXCLUDING seeds-archive (intentional save backups)
$bak = Get-ChildItem -File -Recurse -Filter '*.bak' -ErrorAction SilentlyContinue |
  Where-Object { $_.FullName -notmatch '\\seeds-archive\\' -and $_.FullName -notmatch '\\\.git\\' }
Remove-List $bak 'loose *.bak (excl. seeds-archive)'

# =====================================================================
# BUCKET 1b -- SUBREPO regenerable cruft (tree-wide; SAFE patterns only)
# Catches what the root sweep misses: tagged editor backups (*.bak_<tag>), __pycache__/*.pyc, and
# diag dumps left in subdirs (e.g. Archipelago/worlds/eldenring). Excludes .git + seeds-archive.
# These patterns NEVER match game data (regulation/.dcx/.msb/.bin) so sweeping SoulsRandomizers is
# safe. Some are git-TRACKED (apworld .bak_* / ER_SPHERE_TIERS_*): Remove-Item deletes the working
# copy; afterward run `git add -u` + commit in the affected repo (NEVER `git add -A` in SoulsRandomizers).
# =====================================================================
$PROTECT = '\\(\.git|seeds-archive)\\'

$bakTagged = Get-ChildItem -File -Recurse -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -match '\.bak_' -and $_.FullName -notmatch $PROTECT }
Remove-List $bakTagged 'tagged editor backups (*.bak_<tag>)'

$diag = Get-ChildItem -File -Recurse -Include 'ER_SPHERE_TIERS_*.txt','ER_DIAG.txt' -ErrorAction SilentlyContinue |
  Where-Object { $_.FullName -notmatch $PROTECT }
Remove-List $diag 'subdir diag dumps (ER_SPHERE_TIERS_*/ER_DIAG.txt)'

$pyc = Get-ChildItem -File -Recurse -Filter '*.pyc' -ErrorAction SilentlyContinue |
  Where-Object { $_.FullName -notmatch $PROTECT }
Remove-List $pyc 'compiled python (*.pyc)'

$pycache = Get-ChildItem -Directory -Recurse -Filter '__pycache__' -ErrorAction SilentlyContinue |
  Where-Object { $_.FullName -notmatch $PROTECT }
if ($pycache) {
  Write-Host "[__pycache__ dirs] $($pycache.Count)" -ForegroundColor Yellow
  $pycache | ForEach-Object { Write-Host "    $($_.FullName.Replace($root,'.'))" -ForegroundColor DarkGray }
  if ($Execute) { $pycache | Remove-Item -Recurse -Force }
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
    if ($Execute) { $builddirs | Remove-Item -Recurse -Force }
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
      git mv -- "$old" "$new" 2>$null
      if ($LASTEXITCODE -ne 0) { Move-Item -Force -- "$old" "$new" }  # untracked -> plain move
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
# BUCKET 3 -- root patch_*.py: REVIEW ONLY (NOT archived -- may be pending)
# =====================================================================
Write-Host "`n--- REVIEW: root patch_*.py (NOT touched; several are 'needs run/build' per MEMORY.md) ---" -ForegroundColor Cyan
$rootPatches = Get-ChildItem -File 'patch_*.py' -ErrorAction SilentlyContinue
Write-Host "$($rootPatches.Count) patches -- archive by hand once applied+committed:" -ForegroundColor Yellow
$rootPatches | ForEach-Object { Write-Host "    $($_.Name)" -ForegroundColor DarkGray }

Write-Host "`n=== done ($mode) ===" -ForegroundColor Cyan
if ($Execute) { Write-Host ("freed {0} MB; one-offs archived" -f [math]::Round($freed/1MB,2)) -ForegroundColor Green }
else { Write-Host "re-run with -Execute to purge Bucket 1 + archive Bucket 2. Bucket 3 stays for manual review." -ForegroundColor Green }
