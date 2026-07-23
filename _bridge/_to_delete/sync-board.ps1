<#
  sync-board.ps1 - two-way bridge between cards.json and GitHub issues (4laric/er-archipelago).

  MODEL (board-authoritative + pull state):
    - cards.json is the SOURCE OF TRUTH for content: title, desc, pri, cat, and the active column
      (ready/blocked/progress/backlog). These are PUSHED to issues every sync (board wins).
    - GitHub is the source of truth for: open/closed, assignee, comment count. These are PULLED
      back into cards.json (and shown on the board).
    - The done<->open axis is 3-way merged against .sync-snapshot.json so a change on EITHER side
      propagates: close an issue on GitHub -> card moves to Done; set a card to Done in cards.json
      (or drag+Export in the board) -> issue closes. True conflicts prefer the board and are logged.

  LINKING: an issue is matched to a card by (1) card.issue number, else (2) a hidden
    "<!-- card:ID -->" marker in the issue body, else (3) normalized title. On first run the 92
    pre-existing issues are adopted by title and stamped with the marker for robustness thereafter.

  Regenerates er-archipelago-kanban.html from board.template.html each run.

  Requires: PowerShell 5.1+, $env:GH_TOKEN (repo scope). Run from the folder holding cards.json +
  board.template.html.

  Usage:
    $env:GH_TOKEN = "ghp_xxx"
    .\sync-board.ps1 -DryRun     # preview every action, write nothing
    .\sync-board.ps1             # full reconcile (pull state, push content, regen board)
    .\sync-board.ps1 -Mode push  # only push board->issues (no state pull)
    .\sync-board.ps1 -Mode pull  # only pull issues->board (no content push)
#>
param(
  [string]$Owner = "4laric",
  [string]$Repo  = "er-archipelago",
  [ValidateSet("sync","push","pull")][string]$Mode = "sync",
  [string]$BoardOut = "",   # where to write the regenerated board; default = next to this script
  [switch]$DryRun,
  [switch]$NoRegen,
  [int]$DelayMs = 600
)

$ErrorActionPreference = "Stop"
$dir       = Split-Path -Parent $MyInvocation.MyCommand.Path
$cardsPath = Join-Path $dir "cards.json"
$tplPath   = Join-Path $dir "board.template.html"
$snapPath  = Join-Path $dir ".sync-snapshot.json"
$boardOut  = if ($BoardOut) { $BoardOut } else { Join-Path $dir "er-archipelago-kanban.html" }
$activeCols = @("ready","blocked","progress","backlog")

if (-not $env:GH_TOKEN) { Write-Error "Set `$env:GH_TOKEN to a token with 'repo' scope first."; exit 1 }
$headers = @{
  Authorization          = "token $($env:GH_TOKEN)"
  Accept                 = "application/vnd.github+json"
  "X-GitHub-Api-Version" = "2022-11-28"
  "User-Agent"           = "er-board-bridge"
}
$api = "https://api.github.com/repos/$Owner/$Repo"

function GH {
  param([string]$Method, [string]$Url, $BodyObj)
  $p = @{ Method = $Method; Uri = $Url; Headers = $headers }
  if ($null -ne $BodyObj) {
    $j = $BodyObj | ConvertTo-Json -Depth 6 -Compress
    $p.Body        = [System.Text.Encoding]::UTF8.GetBytes($j)
    $p.ContentType = "application/json; charset=utf-8"
  }
  return Invoke-RestMethod @p
}
function Pause { if (-not $DryRun) { Start-Sleep -Milliseconds $DelayMs } }

# normalize a title for matching: drop any leading non-letter/digit run (emoji, arrows), lower, trim
function Norm([string]$t) { (($t -replace '^[^\p{L}\p{N}(]+','').Trim()).ToLower() }
# the title actually written to the issue: strip leading emoji/symbols, keep case
function PushTitle([string]$t) { ($t -replace '^[^\p{L}\p{N}(]+','').Trim() }

function LabelsFor($c) {
  $ls = @($c.pri, ("area:" + ($c.cat.ToLower() -replace '\s+','-')))
  if ($c.col -ne "done") { $ls += ("status:" + $c.col) }
  return $ls
}
function BodyFor($c) {
  $col = $c.col
  $foot = "`n`n---`n_Area: $($c.cat) | Priority: $($c.pri) | Board column: $col | synced from cards.json_"
  $marker = "`n`n<!-- card:$($c.id) -->"
  return ([string]$c.desc) + $foot + $marker
}
function LabelColor([string]$n) {
  switch -Regex ($n) {
    "^P0$" {"ef4444";break} "^P1$" {"f59e0b";break} "^P2$" {"3b82f6";break} "^P3$" {"6b7280";break}
    "^status:" {"8b5cf6";break} "^area:" {"0e8a16";break} default {"ededed"}
  }
}
function SameLabels($a, $b) {
  $x = @($a | Sort-Object) -join "||"; $y = @($b | Sort-Object) -join "||"; return $x -eq $y
}

# ---- load state ----
$cards = @(Get-Content -Raw -Encoding UTF8 $cardsPath | ConvertFrom-Json)
$snap  = @{}
if (Test-Path $snapPath) {
  (Get-Content -Raw -Encoding UTF8 $snapPath | ConvertFrom-Json).PSObject.Properties | ForEach-Object { $snap[$_.Name] = $_.Value }
}
try { $null = GH GET $api } catch { Write-Error "Cannot reach $Owner/$Repo - $($_.Exception.Message)"; exit 1 }

# ---- fetch all issues (skip PRs) ----
Write-Host "Fetching issues..."
$all = @(); $page = 1
while ($true) {
  $batch = @(GH GET "$api/issues?state=all&per_page=100&page=$page")
  if ($batch.Count -eq 0) { break }
  $all += $batch | Where-Object { -not $_.pull_request }
  if ($batch.Count -lt 100) { break }
  $page++
}
Write-Host "  $($all.Count) issue(s) on the repo."
$byNum = @{}; $byMarker = @{}; $byNorm = @{}
foreach ($i in $all) {
  $byNum[[string]$i.number] = $i
  if ($i.body -and ($i.body -match '<!--\s*card:([A-Za-z0-9\-_]+)\s*-->')) { $byMarker[$matches[1]] = $i }
  $n = Norm $i.title; if (-not $byNorm.ContainsKey($n)) { $byNorm[$n] = $i }
}

# ---- ensure labels exist (push modes only) ----
if ($Mode -ne "pull") {
  $wantLabels = @{}; foreach ($c in $cards) { foreach ($l in (LabelsFor $c)) { $wantLabels[$l] = $true } }
  foreach ($l in $wantLabels.Keys) {
    try { if (-not $DryRun) { GH POST "$api/labels" @{ name=$l; color=(LabelColor $l) } | Out-Null } }
    catch { if (-not ($_.Exception.Response -and $_.Exception.Response.StatusCode.value__ -eq 422)) { throw } }
  }
}

$stat = @{ created=0; contentUpdated=0; closed=0; reopened=0; pulled=0; conflicts=0; adopted=0 }
$newSnap = @{}

foreach ($c in $cards) {
  # ---- resolve the linked issue ----
  $iss = $null
  if ($c.issue -and $byNum.ContainsKey([string]$c.issue)) { $iss = $byNum[[string]$c.issue] }
  elseif ($byMarker.ContainsKey($c.id))                   { $iss = $byMarker[$c.id] }
  else {
    $n = Norm $c.title
    if ($byNorm.ContainsKey($n)) { $iss = $byNorm[$n]; if (-not ($iss.body -match "card:$($c.id)\b")) { $stat.adopted++ } }
  }

  $boardDone = ($c.col -eq "done")

  if ($null -eq $iss) {
    # ---- CREATE (board drives) ----
    if ($Mode -eq "pull") { $newSnap[$c.id] = @{ done=$boardDone; issue=$null }; continue }
    Write-Host ("CREATE  {0}  [{1}]" -f $c.id, $c.col)
    if (-not $DryRun) {
      $created = GH POST "$api/issues" @{ title=(PushTitle $c.title); body=(BodyFor $c); labels=@(LabelsFor $c) }
      $c.issue = $created.number
      if ($boardDone) { Pause; GH PATCH "$api/issues/$($created.number)" @{ state="closed" } | Out-Null; $stat.closed++ }
      $c.assignee = $null; $c.comments = 0
      Pause
    }
    $stat.created++
    $newSnap[$c.id] = @{ done=$boardDone; issue=$c.issue }
    continue
  }

  $c.issue = $iss.number
  $ghDone  = ($iss.state -eq "closed")
  $prev    = if ($snap.ContainsKey($c.id)) { [bool]$snap[$c.id].done } else { $null }

  # ---- reconcile the done<->open bit (3-way) ----
  $finalDone = $boardDone
  if ($Mode -eq "push") {
    # board wins; push state if it differs on GitHub
    if ($boardDone -ne $ghDone) {
      if ($boardDone) { Write-Host ("CLOSE   #{0} {1}" -f $iss.number,$c.id); if(-not $DryRun){Pause;GH PATCH "$api/issues/$($iss.number)" @{state="closed"}|Out-Null}; $stat.closed++ }
      else            { Write-Host ("REOPEN  #{0} {1}" -f $iss.number,$c.id); if(-not $DryRun){Pause;GH PATCH "$api/issues/$($iss.number)" @{state="open"}|Out-Null};  $stat.reopened++ }
    }
    $finalDone = $boardDone
  }
  elseif ($Mode -eq "pull") {
    # GitHub wins; move the card to match issue state
    if ($ghDone -ne $boardDone) {
      if ($ghDone) { if ($c.col -ne "done") { $c.activeCol = $c.col }; $c.col = "done" }
      else         { $c.col = if ($c.activeCol) { $c.activeCol } else { "ready" } }
      $stat.pulled++
    }
    $finalDone = $ghDone
  }
  else {
    # full sync: 3-way merge on the done bit
    $boardChanged = ($null -ne $prev) -and ($boardDone -ne $prev)
    $ghChanged    = ($null -ne $prev) -and ($ghDone    -ne $prev)
    if ($null -eq $prev) {
      # first time we see this pair: board is authoritative
      if ($boardDone -ne $ghDone) {
        if ($boardDone) { Write-Host ("CLOSE   #{0} {1} (adopt)" -f $iss.number,$c.id); if(-not $DryRun){Pause;GH PATCH "$api/issues/$($iss.number)" @{state="closed"}|Out-Null}; $stat.closed++ }
        else            { Write-Host ("REOPEN  #{0} {1} (adopt)" -f $iss.number,$c.id); if(-not $DryRun){Pause;GH PATCH "$api/issues/$($iss.number)" @{state="open"}|Out-Null};  $stat.reopened++ }
      }
      $finalDone = $boardDone
    }
    elseif ($boardChanged -and -not $ghChanged) {
      if ($boardDone) { Write-Host ("CLOSE   #{0} {1} (board)" -f $iss.number,$c.id); if(-not $DryRun){Pause;GH PATCH "$api/issues/$($iss.number)" @{state="closed"}|Out-Null}; $stat.closed++ }
      else            { Write-Host ("REOPEN  #{0} {1} (board)" -f $iss.number,$c.id); if(-not $DryRun){Pause;GH PATCH "$api/issues/$($iss.number)" @{state="open"}|Out-Null};  $stat.reopened++ }
      $finalDone = $boardDone
    }
    elseif ($ghChanged -and -not $boardChanged) {
      if ($ghDone) { if ($c.col -ne "done") { $c.activeCol = $c.col }; $c.col = "done" }
      else         { $c.col = if ($c.activeCol) { $c.activeCol } else { "ready" } }
      Write-Host ("PULL    #{0} {1} -> {2} (github)" -f $iss.number,$c.id,$c.col)
      $stat.pulled++; $finalDone = $ghDone
    }
    else {
      # both changed (or both equal). If they disagree it's a conflict -> board wins.
      if ($boardDone -ne $ghDone) {
        $stat.conflicts++
        Write-Host ("CONFLICT #{0} {1}: board={2} github={3} -> keeping BOARD" -f $iss.number,$c.id,$boardDone,$ghDone) -ForegroundColor Yellow
        if ($boardDone) { if(-not $DryRun){Pause;GH PATCH "$api/issues/$($iss.number)" @{state="closed"}|Out-Null}; $stat.closed++ }
        else            { if(-not $DryRun){Pause;GH PATCH "$api/issues/$($iss.number)" @{state="open"}|Out-Null};  $stat.reopened++ }
      }
      $finalDone = $boardDone
    }
  }

  # ---- push content (board authoritative) ----
  if ($Mode -ne "pull") {
    $wantTitle = PushTitle $c.title
    $wantBody  = BodyFor $c
    $wantLabs  = @(LabelsFor $c)
    $curLabs   = @($iss.labels | ForEach-Object { $_.name })
    if (($iss.title -ne $wantTitle) -or ($iss.body -ne $wantBody) -or -not (SameLabels $curLabs $wantLabs)) {
      Write-Host ("UPDATE  #{0} {1}" -f $iss.number,$c.id)
      if (-not $DryRun) { Pause; GH PATCH "$api/issues/$($iss.number)" @{ title=$wantTitle; body=$wantBody; labels=$wantLabs } | Out-Null }
      $stat.contentUpdated++
    }
  }

  # ---- pull display fields (assignee, comments) ----
  if ($Mode -ne "push") {
    $c.assignee = if ($iss.assignee) { [string]$iss.assignee.login } else { $null }
    $c.comments = [int]$iss.comments
  }

  $newSnap[$c.id] = @{ done=$finalDone; issue=$c.issue }
}

# ---- persist cards.json + snapshot ----
if (-not $DryRun) {
  ($cards | ConvertTo-Json -Depth 6) | Set-Content -Encoding UTF8 $cardsPath
  ($newSnap | ConvertTo-Json -Depth 6) | Set-Content -Encoding UTF8 $snapPath
}

# ---- regenerate the HTML board from the template ----
if (-not $NoRegen) {
  $tpl  = Get-Content -Raw -Encoding UTF8 $tplPath
  $json = ($cards | ConvertTo-Json -Depth 6)
  if ($cards.Count -eq 1) { $json = "[$json]" }   # PS wraps a single object, not an array
  $json = $json.Replace("</","<\/")               # never let a desc break out of <script>
  $html = $tpl.Replace("__CARDS_JSON__", $json)
  if (-not $DryRun) { [System.IO.File]::WriteAllText($boardOut, $html, (New-Object System.Text.UTF8Encoding($false))) }
  Write-Host "Regenerated $boardOut"
}

Write-Host ""
Write-Host ("Done{0}. created={1} content-updated={2} closed={3} reopened={4} pulled={5} adopted={6} conflicts={7}" -f `
  ($(if($DryRun){" (DRY RUN - nothing written)"}else{""})), $stat.created, $stat.contentUpdated, $stat.closed, $stat.reopened, $stat.pulled, $stat.adopted, $stat.conflicts)
if ($stat.conflicts -gt 0) { Write-Host "Review the CONFLICT lines above - the board value was kept." -ForegroundColor Yellow }
