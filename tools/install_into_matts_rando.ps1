# Thin Windows launcher. The Python installer edits ONLY config_eldenringrandomizer_dll.toml.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$Randomizer, [switch]$WithFlower)
$ErrorActionPreference = "Stop"
$python = Get-Command py -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python -ErrorAction SilentlyContinue }
if (-not $python) { throw "Python is required to run the installer." }
$arguments = @((Join-Path $PSScriptRoot "install_into_matts_rando.py"), "--randomizer", $Randomizer)
if ($WithFlower) { $arguments += "--with-flower" }
& $python.Source @arguments
exit $LASTEXITCODE
