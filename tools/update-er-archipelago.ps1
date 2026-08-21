# Thin Windows launcher. The Python updater replaces only the shipped me3/ payload, backs up
# what it replaces, and never touches apconfig.json, saves, logs, or ledgers.
[CmdletBinding()]
param([switch]$AcceptContractChange)
$ErrorActionPreference = "Stop"
$python = Get-Command py -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python -ErrorAction SilentlyContinue }
if (-not $python) { throw "Python is required to run the updater." }
$arguments = @((Join-Path $PSScriptRoot "update_er_archipelago.py"))
if ($AcceptContractChange) { $arguments += "--accept-contract-change" }
& $python.Source @arguments
exit $LASTEXITCODE
