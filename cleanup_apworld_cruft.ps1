# cleanup_apworld_cruft.ps1  (run from er-archipelago repo root)
#
# Removes git-TRACKED dev cruft from worlds/eldenring so the apworld package is PR-clean, and adds a
# .gitignore so the diag/backup files don't creep back in. cleanup_repo.ps1 misses these because the
# backups are `*.bak_<tag>` (not `*.bak`) and the dumps are `ER_SPHERE_TIERS_*`.
#
# DRY RUN by default — lists what it would remove. Pass -Execute to actually `git rm` + write .gitignore.
#
#   .\cleanup_apworld_cruft.ps1            # preview
#   .\cleanup_apworld_cruft.ps1 -Execute   # apply, then review `git status` and commit
param([switch]$Execute)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$w = "Archipelago/worlds/eldenring"

# Tracked files matching cruft patterns. NOTE: "item script/" and "location script/" are scratch
# generator dirs that don't belong in the apworld package — included here. If you still want them,
# MOVE them to a tools/ dir instead of deleting (comment those two lines out before -Execute).
$cruft = git ls-files -- "$w" | Where-Object {
    $_ -match '\.bak' -or                          # __init__.py.bak_*, options.py.bak_*, region_spine.py.bak_*
    $_ -match 'ER_SPHERE_TIERS_.*\.txt$' -or        # sphere-tier diag dumps
    $_ -match '/ER_DIAG\.txt$' -or
    $_ -match '/old locations\.py$' -or
    $_ -match '/_ .*\.(md|txt)$' -or                # "_ naming.md", "_ todo.txt"
    $_ -match '/region lock ideas\.md$' -or
    $_ -match '/item script/' -or
    $_ -match '/location script/'
}

if (-not $cruft) {
    Write-Host "No tracked cruft found in $w." -ForegroundColor Green
} else {
    Write-Host "Tracked cruft in ${w} ($($cruft.Count) files):" -ForegroundColor Yellow
    $cruft | ForEach-Object { Write-Host "  $_" }
    if ($Execute) {
        $cruft | ForEach-Object { git rm -q -- "$_" }
        Write-Host "`n+ git rm done ($($cruft.Count) files). Review 'git status', then commit." -ForegroundColor Green
    } else {
        Write-Host "`nDRY RUN — re-run with -Execute to remove these." -ForegroundColor Cyan
    }
}

# .gitignore in the apworld dir so dumps/backups never get tracked again.
if ($Execute) {
    $gi = Join-Path $w ".gitignore"
    @(
        "# dev cruft — do not commit",
        "*.bak",
        "*.bak_*",
        "ER_DIAG.txt",
        "ER_SPHERE_TIERS_*.txt",
        "__pycache__/",
        "*.pyc"
    ) | Set-Content -Path $gi -Encoding utf8
    git add -- $gi
    Write-Host "+ wrote $gi (and staged it)" -ForegroundColor Green
}
