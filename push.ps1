# push.ps1 -- commit & push across the ER Archipelago repos
#
# Usage (from the repo root):
#   .\push.ps1 -Status                      # show pending changes in every repo
#   .\push.ps1 -Message "what changed"      # commit (scoped paths only) + push, all repos
#   .\push.ps1 -Message "..." -Only Archipelago,SoulsIds    # subset
#
# Notes:
#  - Adds are SCOPED per repo so bake outputs never get committed (regulation.bin,
#    map\/event\/msg\ outputs, ap_* diags in SoulsRandomizers; output\ zips in Archipelago).
#  - SoulsRandomizers: keep the remote PRIVATE (thefifthmatt license: no distribution of
#    randomizer forks or config files; diste\ also contains v0.11.4-derived configs).
#  - Repo-root files (build.ps1, push.ps1, SPEC-*.md, HANDOFF.md) belong to NO repo and
#    are not covered here.

[CmdletBinding()]
param(
    [string]$Message = "",
    [string[]]$Only = @(),
    [switch]$Status
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

$Repos = @(
    @{ Name = "SoulsRandomizers"
       Adds = @("RandomizerCommon", "EldenRingRandomizer", "diste")
       Warn = "PRIVATE REMOTE ONLY (thefifthmatt license)" },
    @{ Name = "Dark-Souls-III-Archipelago-client"
       Adds = @("archipelago-client/*.cpp", "archipelago-client/*.h", "archipelago-client/*.hpp") },
    @{ Name = "Archipelago"
       Adds = @("worlds/eldenring") },
    @{ Name = "SoulsFormats"
       Adds = @("SoulsFormats") },
    @{ Name = "SoulsIds"
       Adds = @("SoulsIds") }
)

function Step($msg) { Write-Host "`n==== $msg" -ForegroundColor Cyan }

foreach ($repo in $Repos) {
    if ($Only.Count -gt 0 -and $Only -notcontains $repo.Name) { continue }
    $path = Join-Path $Root $repo.Name
    if (-not (Test-Path (Join-Path $path ".git"))) {
        Write-Warning "$($repo.Name): not a git repo, skipping"
        continue
    }

    Step $repo.Name
    if ($repo.Warn) { Write-Host "  ! $($repo.Warn)" -ForegroundColor Yellow }
    Push-Location $path
    try {
        # Stale lock from a crashed git process blocks everything; detect it loudly.
        if (Test-Path ".git\index.lock") {
            Write-Warning "stale .git\index.lock present -- if no git process is running:"
            Write-Warning "  Remove-Item `"$path\.git\index.lock`""
            continue
        }

        $branch = git branch --show-current
        if (-not $branch) {
            Write-Warning "detached HEAD -- name it first (git switch -c <branch>), skipping"
            continue
        }

        if ($Status) {
            git status -s -- $repo.Adds
            $pending = git status --porcelain -- $repo.Adds
            Write-Host "  [$branch] $(@($pending).Count) change(s) in scoped paths"
            continue
        }

        if (-not $Message) { throw "provide -Message (or use -Status)" }

        git add -- $repo.Adds
        git diff --cached --quiet
        if ($LASTEXITCODE -ne 0) {
            git commit -m $Message
            git push
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "push failed (no fork remote / no permission?). Commit is safe locally."
            }
        } else {
            Write-Host "  (no changes in scoped paths)"
        }
    } finally { Pop-Location }
}
