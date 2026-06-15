# ship.ps1 -- commit & push ONLY the #7 / bake-stability fixes + -LoopTest tooling.
#
# Unlike push.ps1 (which scopes by whole dirs and would sweep in pre-existing WIP, bake
# artifacts, and diste/ config churn), this stages an EXPLICIT short file list so nothing
# else rides along. Two commits: the code in the SoulsRandomizers submodule, then the
# tooling + submodule-pointer bump in the root superrepo.
#
# Usage (from the repo root):
#   .\ship.ps1            # commit both + push to origin
#   .\ship.ps1 -DryRun    # show exactly what would be staged; commit/push nothing

[CmdletBinding()]
param([switch]$DryRun)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Sub  = Join-Path $Root "SoulsRandomizers"

$SubFiles = @(
    "RandomizerCommon/KeyItemsPermutation.cs",
    "RandomizerCommon/ArchipelagoForm.cs",
    "EldenRingRandomizer/Program.cs"
)
# Root tooling/docs + the submodule gitlink (bumped to the new SoulsRandomizers HEAD).
$RootFiles = @("build.ps1", "NOTES-fix-7-volcano-loop.md", "SoulsRandomizers")

$SubMsg = @"
Fix #7 volcano_town loop + bake slot-data / headless / url

KeyItemsPermutation.CollapseReqs: iterate the findLoops cycle scan to a fixed point
so every dependency cycle gets a cut edge. Fixes seed-dependent "Loop detection
failed on volcano_town" crashes on DLC-pruned base-game bakes (3/3 deterministic
seeds now bake clean).

ArchipelagoForm: request slot data at login and read LoginSuccessful.SlotData from
the Connected packet instead of the synchronous DataStorage.GetSlotData() (which
timed out: "_read_slot_data_N"). Add headless batch-bake mode (no dialogs, auto-
close, 0/1 exit code) and force localhost under autoconnect so a stale apconfig URL
can't leak into the dev-loop / -LoopTest bake.

Program.cs: parse `headless` and `url=` launch args.
"@

$RootMsg = @"
build.ps1 -LoopTest: unattended multi-seed bake test; bump SoulsRandomizers

-LoopTest (-Seeds / -Count [-Enemies]) bakes a batch of seeds headless, each against
a fresh local server, and prints a pass/fail table -- verifies the #7 fix across many
seeds in one run. NOTES-fix-7-volcano-loop.md documents the root cause, fix, and bake-
test steps. Bumps the SoulsRandomizers submodule pointer to the fix commit.
"@

function Commit-And-Push($repoPath, $files, $message, $label) {
    Write-Host "`n==== $label" -ForegroundColor Cyan
    Push-Location $repoPath
    try {
        if (Test-Path ".git\index.lock") { throw "stale .git\index.lock in $label -- remove it if no git is running" }
        $branch = git branch --show-current
        if (-not $branch) { throw "$label is in detached HEAD -- run 'git -C `"$repoPath`" switch ap-sync-2026-06-13' first" }

        if ($DryRun) {
            Write-Host "  [$branch] would stage:" -ForegroundColor Yellow
            git add --dry-run -- $files
            Write-Host "  --- diff stat (unstaged preview) ---"
            git diff --stat -- $files
            return
        }

        git add -- $files
        git diff --cached --quiet
        if ($LASTEXITCODE -eq 0) { Write-Host "  (nothing staged -- already committed?)"; return }

        Write-Host "  staged:" -ForegroundColor Green
        git diff --cached --name-only -- $files | ForEach-Object { Write-Host "    $_" }
        git commit -m $message
        git push
        if ($LASTEXITCODE -ne 0) { Write-Warning "push failed (no remote / no permission?). Commit is safe locally; re-push manually." }
        else { Write-Host "  pushed [$branch]" -ForegroundColor Green }
    } finally { Pop-Location }
}

# 1) submodule code first, so the root can record the resulting HEAD.
Commit-And-Push $Sub  $SubFiles  $SubMsg  "SoulsRandomizers (PRIVATE remote -- thefifthmatt license)"
# 2) superrepo: tooling/docs + bump the SoulsRandomizers pointer.
Commit-And-Push $Root $RootFiles $RootMsg "superrepo (root: tooling + submodule pointer)"

Write-Host "`nDone." -ForegroundColor Green
if ($DryRun) { Write-Host "(dry run -- nothing committed or pushed)" -ForegroundColor Yellow }
