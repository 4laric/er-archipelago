# Thin Windows launcher for the client, optional flower assets, and optional Torrent repair.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Randomizer,
    [switch]$WithFlower,
    [switch]$WithTorrentRepair,
    [switch]$InstallTorrentDependency
)
$ErrorActionPreference = "Stop"
$python = Get-Command py -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python -ErrorAction SilentlyContinue }
if (-not $python) { throw "Python is required to run the installer." }

if ($WithTorrentRepair) {
    # Soulstruct 2.3.2 on PyPI omitted ParamCrypt's two generated metadata files. Probe the
    # exact capability we need, then offer the fixed upstream source snapshot without making
    # users decipher a Python traceback or copy a VCS requirement by hand.
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
        Write-Host "The installer can download the fixed upstream 2.3.2 source snapshot now."
        $install = $InstallTorrentDependency
        if (-not $install) {
            $answer = Read-Host "Install it for this Python? [Y/n]"
            $install = [string]::IsNullOrWhiteSpace($answer) -or $answer -match '^[Yy]'
        }
        if (-not $install) {
            Write-Host "Nothing was installed and regulation.bin was not touched."
            exit 1
        }
        $soulstruct = "https://github.com/Grimrukh/soulstruct/archive/d59dc41e607ed4221378519c81609557241dce6b.zip"
        # The broken PyPI wheel and fixed source snapshot both report 2.3.2. Force replacement;
        # otherwise pip can call the broken wheel "already satisfied" and change nothing.
        & $python.Source -m pip install --force-reinstall --no-cache-dir $soulstruct
        if ($LASTEXITCODE -ne 0) {
            throw "Soulstruct setup failed. Check the pip output above; regulation.bin was not touched."
        }
        & $python.Source -c $probe 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "Soulstruct installed but ParamCrypt is incomplete; regulation.bin was not touched."
        }
        Write-Host "Soulstruct setup complete. Continuing with the guarded Torrent repair..."
    }
}

$arguments = @((Join-Path $PSScriptRoot "install_into_matts_rando.py"), "--randomizer", $Randomizer)
if ($WithFlower) { $arguments += "--with-flower" }
if ($WithTorrentRepair) { $arguments += "--with-torrent-repair" }
& $python.Source @arguments
exit $LASTEXITCODE
