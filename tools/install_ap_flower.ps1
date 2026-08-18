# Build and install the AP flower override from the player's own Elden Ring files.
# No generated atlas or Oodle binary is shipped. WitchyBND is downloaded from its pinned upstream
# release and verified before use; the game's own oo2core DLL supplies KRAK decompression.
[CmdletBinding()]
param(
    [string]$GameDir = "C:\Program Files (x86)\Steam\steamapps\common\ELDEN RING\Game",
    [string]$Destination,
    [string]$Payload,
    [string]$WitchyBND,
    [switch]$Force,
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"
$WitchyVersion = "3.0.1.0"
$WitchyUrl = "https://github.com/ividyon/WitchyBND/releases/download/$WitchyVersion/WitchyBND-$WitchyVersion-win-x64.zip"
$WitchySha256 = "a3e6b2a0f7eac13f5e83b6602a1149322439c0662baa140ecdd84be28af50364"
$MarkerName = ".er-ap-flower.json"
$RelativeOutputs = @("menu\hi\01_common.tpf.dcx", "menu\low\01_common.tpf.dcx")

$DestinationWasDefault = -not $Destination
if (-not $Destination) { $Destination = Join-Path $PSScriptRoot "ap-package" }

if (-not $Payload) {
    $payloadCandidates = @(
        (Join-Path $PSScriptRoot "ap_flower_160.bc7"),
        (Join-Path $PSScriptRoot "ap_icon_src\ap_flower_160.bc7")
    )
    $Payload = $payloadCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } |
        Select-Object -First 1
    if (-not $Payload) { $Payload = $payloadCandidates[0] }
}

function Fail([string]$Message) { throw "install_ap_flower: $Message" }

function Remove-InstalledFiles([string]$Root) {
    $marker = Join-Path $Root $MarkerName
    if (-not (Test-Path -LiteralPath $marker)) { return $false }
    $record = Get-Content -LiteralPath $marker -Raw | ConvertFrom-Json
    foreach ($relative in @($record.files)) {
        $path = Join-Path $Root $relative
        if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
    }
    Remove-Item -LiteralPath $marker -Force
    return $true
}

if ($Uninstall) {
    if (Remove-InstalledFiles $Destination) {
        Write-Host "Removed the locally generated AP flower override from $Destination"
    } else {
        Write-Host "No AP flower install marker found under $Destination; nothing removed."
    }
    exit 0
}

$menu = Join-Path $GameDir "menu"
$oodle = Get-ChildItem -LiteralPath $GameDir -Filter "oo2core*_win64.dll" -File -ErrorAction SilentlyContinue |
    Sort-Object Name | Select-Object -First 1
if (-not (Test-Path -LiteralPath $menu -PathType Container)) {
    Fail "no menu directory at $menu. Verify -GameDir points at the installed Elden Ring Game folder."
}
if (-not $oodle) { Fail "no oo2core*_win64.dll beside eldenring.exe in $GameDir" }
if (-not (Test-Path -LiteralPath $Payload -PathType Leaf)) {
    Fail "project-owned BC7 payload is missing: $Payload"
}
if ((Get-Item -LiteralPath $Payload).Length -ne 25600) {
    Fail "BC7 payload must be exactly 25,600 bytes: $Payload"
}

function Get-Witchy {
    if ($WitchyBND) {
        if (-not (Test-Path -LiteralPath $WitchyBND -PathType Leaf)) {
            Fail "-WitchyBND does not exist: $WitchyBND"
        }
        return (Resolve-Path -LiteralPath $WitchyBND).Path
    }
    $root = Join-Path $env:LOCALAPPDATA "ERArchipelago\tools\WitchyBND-$WitchyVersion"
    $exe = Join-Path $root "WitchyBND.exe"
    if (Test-Path -LiteralPath $exe) { return $exe }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $root) | Out-Null
    $zip = Join-Path ([IO.Path]::GetTempPath()) "WitchyBND-$WitchyVersion.zip"
    Write-Host "Downloading pinned WitchyBND $WitchyVersion ..."
    Invoke-WebRequest -Uri $WitchyUrl -OutFile $zip -UseBasicParsing
    $actual = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $WitchySha256) {
        Remove-Item -LiteralPath $zip -Force -ErrorAction SilentlyContinue
        Fail "WitchyBND archive hash mismatch (got $actual); refusing to execute it."
    }
    if (Test-Path -LiteralPath $root) { Remove-Item -LiteralPath $root -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $root | Out-Null
    Expand-Archive -LiteralPath $zip -DestinationPath $root -Force
    Remove-Item -LiteralPath $zip -Force
    $found = Get-ChildItem -LiteralPath $root -Filter WitchyBND.exe -File -Recurse |
        Select-Object -First 1
    if (-not $found) { Fail "verified WitchyBND archive contained no WitchyBND.exe" }
    if ($found.DirectoryName -ne $root) {
        Get-ChildItem -LiteralPath $found.DirectoryName -Force | Move-Item -Destination $root -Force
    }
    if (-not (Test-Path -LiteralPath $exe)) { Fail "could not stage WitchyBND.exe under $root" }
    return $exe
}

$witchy = Get-Witchy
$oldPath = $env:PATH
$env:PATH = "$($oodle.DirectoryName);$env:PATH"
$work = Join-Path ([IO.Path]::GetTempPath()) ("er-ap-flower-" + [guid]::NewGuid().ToString("N"))

function Invoke-Witchy([string[]]$Arguments, [string]$Purpose) {
    & $witchy -s @Arguments
    if ($LASTEXITCODE -ne 0) { Fail "WitchyBND failed during $Purpose (exit $LASTEXITCODE)" }
}

function Expand-Witchy([string]$Source, [string]$Folder) {
    New-Item -ItemType Directory -Force -Path $Folder | Out-Null
    $local = Join-Path $Folder (Split-Path -Leaf $Source)
    Copy-Item -LiteralPath $Source -Destination $local -Force
    Invoke-Witchy @("-u", $local) "unpack of $Source"
    $dirs = @(Get-ChildItem -LiteralPath $Folder -Directory | Where-Object {
        $_.Name.StartsWith(([IO.Path]::GetFileNameWithoutExtension($local)).Split('.')[0])
    })
    if ($dirs.Count -ne 1) { Fail "expected one unpacked directory beside $local, found $($dirs.Count)" }
    return $dirs[0].FullName
}

function Find-FlowerRect([string]$LayoutRoot) {
    $hits = @()
    foreach ($file in Get-ChildItem -LiteralPath $LayoutRoot -Filter *.xml -File -Recurse) {
        try { [xml]$xml = Get-Content -LiteralPath $file.FullName -Raw } catch { continue }
        foreach ($node in $xml.SelectNodes('//*[@name and @x and @y and (@width or @w) and (@height or @h)]')) {
            if ($node.name -match 'ItemIcon_0*92(?!\d)') {
                $hits += [pscustomobject]@{
                    Atlas = ([IO.Path]::GetFileNameWithoutExtension($file.Name) + ".dds")
                    X = [int]$node.x; Y = [int]$node.y
                    W = [int]$(if ($node.width) { $node.width } else { $node.w })
                    H = [int]$(if ($node.height) { $node.height } else { $node.h })
                }
            }
        }
    }
    if ($hits.Count -ne 1) { Fail "expected one ItemIcon 92 layout entry, found $($hits.Count)" }
    return $hits[0]
}

function Read-U32([byte[]]$Bytes, [int]$Offset) {
    return [BitConverter]::ToUInt32($Bytes, $Offset)
}

function Write-FlowerBlocks([string]$Dds, $Rect) {
    [byte[]]$head = [IO.File]::ReadAllBytes($Dds)
    if ($head.Length -lt 148 -or [Text.Encoding]::ASCII.GetString($head, 0, 4) -ne "DDS ") {
        Fail "$Dds is not a complete DDS"
    }
    $height = Read-U32 $head 12; $width = Read-U32 $head 16; $mips = Read-U32 $head 28
    $fourcc = [Text.Encoding]::ASCII.GetString($head, 84, 4); $dxgi = Read-U32 $head 128
    if ($fourcc -ne "DX10" -or $dxgi -notin @(98, 99)) {
        Fail "expected BC7 DX10 atlas, found fourcc=$fourcc dxgi=$dxgi"
    }
    if ($mips -ne 1) { Fail "expected one atlas mip, found $mips; lower mips are not splice-safe" }
    foreach ($n in @($Rect.X, $Rect.Y, $Rect.W, $Rect.H)) {
        if ($n -le 0 -or $n % 4 -ne 0) { Fail "flower rect is not positive and BC-block aligned" }
    }
    if ($Rect.X + $Rect.W -gt $width -or $Rect.Y + $Rect.H -gt $height) {
        Fail "flower rect falls outside the ${width}x${height} atlas"
    }
    [byte[]]$payloadBytes = [IO.File]::ReadAllBytes($Payload)
    $rowBytes = ($Rect.W / 4) * 16; $rows = $Rect.H / 4; $stride = ($width / 4) * 16
    if ($payloadBytes.Length -ne $rowBytes * $rows) { Fail "payload size does not match layout rect" }
    $stream = [IO.File]::Open($Dds, [IO.FileMode]::Open, [IO.FileAccess]::ReadWrite,
                             [IO.FileShare]::None)
    try {
        for ($row = 0; $row -lt $rows; $row++) {
            $offset = 148 + (($Rect.Y / 4 + $row) * $stride) + (($Rect.X / 4) * 16)
            $stream.Position = $offset
            $stream.Write($payloadBytes, $row * $rowBytes, $rowBytes)
        }
    } finally { $stream.Dispose() }
}

function Set-DfltManifest([string]$Root) {
    $hits = @()
    foreach ($file in Get-ChildItem -LiteralPath $Root -Filter *.xml -File -Recurse) {
        try { [xml]$xml = Get-Content -LiteralPath $file.FullName -Raw } catch { continue }
        if ($xml.DocumentElement.SelectSingleNode('compression')) {
            $hits += [pscustomobject]@{ File = $file.FullName; Xml = $xml }
        }
    }
    if ($hits.Count -ne 1) { Fail "expected one Witchy compression manifest, found $($hits.Count)" }
    $xml = $hits[0].Xml; $root = $xml.DocumentElement
    $root.compression = "DCX_DFLT"
    foreach ($name in @("compressionLevel", "oodleCompressorType")) {
        $node = $root.SelectSingleNode($name); if ($node) { [void]$root.RemoveChild($node) }
    }
    $fields = [ordered]@{ dfltUnk04="69632"; dfltUnk10="68"; dfltUnk14="76";
                           dfltUnk30="9"; dfltUnk38="21" }
    foreach ($entry in $fields.GetEnumerator()) {
        $node = $root.SelectSingleNode($entry.Key)
        if (-not $node) { $node = $xml.CreateElement($entry.Key); [void]$root.AppendChild($node) }
        $node.InnerText = $entry.Value
    }
    $xml.Save($hits[0].File)
}

function Assert-Dflt([string]$Path) {
    [byte[]]$bytes = [IO.File]::ReadAllBytes($Path)
    $prefix = [Text.Encoding]::ASCII.GetString($bytes, 0, [Math]::Min(192, $bytes.Length))
    if (-not $prefix.Contains("DCP`0DFLT")) { Fail "repacked output is not DCX_DFLT: $Path" }
}

try {
    New-Item -ItemType Directory -Force -Path $work | Out-Null
    $staged = Join-Path $work "output"
    foreach ($bundle in @("hi", "low")) {
        $source = Join-Path $menu "$bundle\01_common.tpf.dcx"
        $layout = Join-Path $menu "$bundle\01_common.sblytbnd.dcx"
        if (-not (Test-Path -LiteralPath $source)) { Fail "missing installed atlas: $source" }
        if (-not (Test-Path -LiteralPath $layout)) { Fail "missing installed layout: $layout" }
        $layoutRoot = Expand-Witchy $layout (Join-Path $work "$bundle-layout")
        $rect = Find-FlowerRect $layoutRoot
        $tpfRoot = Expand-Witchy $source (Join-Path $work $bundle)
        $dds = @(Get-ChildItem -LiteralPath $tpfRoot -Filter $rect.Atlas -File -Recurse)
        if ($dds.Count -ne 1) { Fail "layout names $($rect.Atlas), TPF yielded $($dds.Count) matches" }
        Write-FlowerBlocks $dds[0].FullName $rect
        Set-DfltManifest $tpfRoot
        Invoke-Witchy @($tpfRoot) "DFLT repack of $bundle atlas"
        $built = Join-Path (Split-Path -Parent $tpfRoot) "01_common.tpf.dcx"
        if (-not (Test-Path -LiteralPath $built)) { Fail "Witchy produced no $built" }
        Assert-Dflt $built
        $target = Join-Path $staged "menu\$bundle\01_common.tpf.dcx"
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
        Copy-Item -LiteralPath $built -Destination $target -Force
    }

    $marker = Join-Path $Destination $MarkerName
    $owned = Test-Path -LiteralPath $marker
    foreach ($relative in $RelativeOutputs) {
        $target = Join-Path $Destination $relative
        if ((Test-Path -LiteralPath $target) -and -not $owned -and -not $Force -and
            -not $DestinationWasDefault) {
            Fail "$target already exists without an AP install marker. It may belong to another mod; " +
                 "move it, choose another -Destination, or pass -Force explicitly."
        }
    }
    if ($owned) { [void](Remove-InstalledFiles $Destination) }
    foreach ($relative in $RelativeOutputs) {
        $source = Join-Path $staged $relative; $target = Join-Path $Destination $relative
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
        Copy-Item -LiteralPath $source -Destination $target -Force
    }
    $record = [ordered]@{
        schema = 1; generatedBy = "er-archipelago"; witchy = $WitchyVersion
        payloadSha256 = (Get-FileHash -LiteralPath $Payload -Algorithm SHA256).Hash.ToLowerInvariant()
        files = $RelativeOutputs
    }
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    $record | ConvertTo-Json | Set-Content -LiteralPath $marker -Encoding UTF8
    Write-Host "AP flower override installed under $Destination" -ForegroundColor Green
} finally {
    $env:PATH = $oldPath
    if (Test-Path -LiteralPath $work) { Remove-Item -LiteralPath $work -Recurse -Force }
}
