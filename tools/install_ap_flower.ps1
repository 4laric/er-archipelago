# Thin Windows launcher. The Python installer only copies authenticated release assets.
[CmdletBinding()]
param([string]$Package, [string]$Destination, [switch]$ReplaceExisting, [switch]$Uninstall)
$ErrorActionPreference = "Stop"
$python = Get-Command py -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python -ErrorAction SilentlyContinue }
if (-not $python) { throw "Python is required to install AP Flower." }
$arguments = @((Join-Path $PSScriptRoot "install_ap_flower.py"))
if ($Package) { $arguments += @("--package", $Package) }
if ($Destination) { $arguments += @("--destination", $Destination) }
if ($ReplaceExisting) { $arguments += "--replace-existing" }
if ($Uninstall) { $arguments += "--uninstall" }
& $python.Source @arguments
exit $LASTEXITCODE
