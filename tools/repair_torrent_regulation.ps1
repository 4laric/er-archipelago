# Standalone post-randomization repair for Matt's pre-1.17 regulation.bin.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Randomizer,
    [switch]$InstallDependency
)
$ErrorActionPreference = "Stop"
$python = Get-Command py -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python -ErrorAction SilentlyContinue }
if (-not $python) { throw "Python is required to run the Torrent repair." }

$root = (Resolve-Path -LiteralPath $Randomizer).Path
$regulation = Join-Path $root "regulation.bin"
if (-not (Test-Path -LiteralPath $regulation -PathType Leaf)) {
    throw "regulation.bin not found in $root -- run Matt's randomizer first."
}

$probe = @'
from pathlib import Path
import sys
from soulstruct.base.params.ParamCrypt import ParamCrypt
p = Path(sys.modules[ParamCrypt.__module__].__file__).parent
assert (p / "ParamCrypt.deps.json").is_file()
assert (p / "ParamCrypt.runtimeconfig.json").is_file()
'@
& $python.Source -c $probe 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Torrent repair needs Soulstruct's regulation reader (one-time setup)."
    Write-Host "The repair can download the fixed upstream 2.3.2 source snapshot now."
    $install = $InstallDependency
    if (-not $install) {
        $answer = Read-Host "Install it for this Python? [Y/n]"
        $install = [string]::IsNullOrWhiteSpace($answer) -or $answer -match '^[Yy]'
    }
    if (-not $install) {
        Write-Host "Nothing was installed and regulation.bin was not touched."
        exit 1
    }
    $source = "https://github.com/Grimrukh/soulstruct/archive/d59dc41e607ed4221378519c81609557241dce6b.zip"
    & $python.Source -m pip install --force-reinstall --no-cache-dir $source
    if ($LASTEXITCODE -ne 0) {
        throw "Soulstruct setup failed. regulation.bin was not touched."
    }
    & $python.Source -c $probe 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Soulstruct installed but ParamCrypt is incomplete. regulation.bin was not touched."
    }
    Write-Host "Soulstruct setup complete."
}

& $python.Source (Join-Path $PSScriptRoot "torrent_rideparam_repair.py") `
    --regulation $regulation
exit $LASTEXITCODE
