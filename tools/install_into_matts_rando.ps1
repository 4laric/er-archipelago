# Thin Windows launcher for the client, optional flower assets, and optional Torrent repair.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Randomizer,
    [switch]$WithFlower,
    [switch]$WithTorrentRepair
)
$ErrorActionPreference = "Stop"
$python = Get-Command py -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python -ErrorAction SilentlyContinue }
if (-not $python) { throw "Python is required to run the installer." }
$arguments = @((Join-Path $PSScriptRoot "install_into_matts_rando.py"), "--randomizer", $Randomizer)
if ($WithFlower) { $arguments += "--with-flower" }
if ($WithTorrentRepair) { $arguments += "--with-torrent-repair" }
& $python.Source @arguments
exit $LASTEXITCODE
