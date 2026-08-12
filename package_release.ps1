# package_release.ps1 -- assemble the player-facing ER Archipelago release bundle.
#
# Pure-runtime: NO FromSoftware game data ships. This wraps the three things a
# player needs into one zip:
#   1. eldenring.apworld            (built by build.ps1 -Apworld = the greenfield world)
#   2. me3\ runtime                 (client DLL + ap-package AP-icon override +
#                                    apconfig.json)
#   3. the flagship yaml + SETUP.md + CHANGELOG.md
# (The PopTracker pack stays in the repo, not bundled; the built-in F6 tracker ships.)
#
# The AP-icon override IS me3\ap-package (a me3 VFS texture swap: AP items show the
# flower icon). It is bundled by copying me3\ wholesale; the script WARNS if the
# ap-package menu textures are missing so an empty icon package never ships silently.
#
# Usage (from the repo root):
#   .\package_release.ps1                 # build apworld, stage, zip -> dist\
#   .\package_release.ps1 -SkipApworld    # reuse the existing eldenring.apworld
#   .\package_release.ps1 -Version 0.1    # version tag used in the zip name
#   .\package_release.ps1 -DryRun         # stage + report only; do not zip
#
#   .\package_release.ps1 -Unofficial -Stamp auto-equip-preview
#                                         # cut a build that is NOT a release
#
# Exit codes: 0 = clean, 2 = staged but with warnings (review before shipping).
#
# ---- UNOFFICIAL BUILDS -------------------------------------------------------------------------
# -Unofficial cuts a bundle for one person: a preview, a repro build, a "try this and tell me if
# it still happens". It is NOT a way to skip the gates. The split is deliberate:
#
#   RELAXED to warnings (so the run exits 2, never 0)   -- the IDENTITY gates. The changelog match
#   and the version-lockstep sites both exist to stop a build CLAIMING to be a release it is not.
#   An unofficial build claims nothing, so mismatches there are expected, not dangerous.
#
#   STILL HARD FAILURES  -- every CORRECTNESS gate. The zip-gen gate, the apworld<->client data
#   agreement, the third-party binary gate. These matter MORE here, not less: a preview build goes
#   to somebody who will play it, and a mispaired apworld/client does not fail at the door -- it
#   boots, connects, and misbehaves quietly.
#
# -Stamp is REQUIRED with -Unofficial, and lands in the zip name and in UNOFFICIAL-BUILD.txt along
# with the world and client SHAs. That file is the whole point. v0.2.17 named two different builds
# and a VERSION: OK check passed on a 0.2.15 dll; if somebody reports a bug against a build cut
# here, the SHAs have to be recoverable from the artifact itself.

[CmdletBinding()]
param(
    [string]$Version = "0.2",
    [switch]$SkipApworld,
    [switch]$SkipGenSmoke,   # skip the zipped-apworld generation gate (NOT recommended for a real release)
    [switch]$SkipCrossRepoCheck, # skip the apworld<->client data-agreement gate (NOT recommended)
    [switch]$DryRun,
    [switch]$Unofficial,     # cut a NON-RELEASE build: identity gates warn, correctness gates still fail
    [switch]$AllowStalePin,  # the gitlink deliberately trails client main (sets ALLOW_STALE_PIN=1)
    [string]$Stamp = ""      # REQUIRED with -Unofficial: free-text label, e.g. auto-equip-preview
)

$ErrorActionPreference = "Stop"
# Normalize the version: accept -Version 0.1.1 OR v0.1.1; the zip name prepends its own "v".
$Version = $Version -replace '^[vV]', ''
$Repo      = $PSScriptRoot
$TimeStamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Dist      = Join-Path $Repo "dist"
$Rel       = Join-Path $Repo "release"

# Helpers are declared HERE, above the gates, not below them. They used to sit at the top of
# section 1, which put them after the changelog and version checks -- so those two gates had no
# way to warn even when warning was the right answer, and the only tool they had was throw.
$Warnings = New-Object System.Collections.Generic.List[string]

function Info($m) { Write-Host "[pkg]  $m" }
function Warn($m) { Write-Host "[warn] $m" -ForegroundColor Yellow; $Warnings.Add($m) | Out-Null }
function Die($m)  { throw "[pkg] $m" }

# ---- UNOFFICIAL MODE --------------------------------------------------------------------------
if ($Unofficial) {
    if ([string]::IsNullOrWhiteSpace($Stamp)) {
        throw ("package_release: -Unofficial requires -Stamp <label>. An unlabelled one-off is " +
               "the identification problem this whole script exists to prevent -- name it for " +
               "what it is, e.g. -Stamp auto-equip-preview.")
    }
    # Keep the label filename-safe; it goes straight into the zip name.
    $Stamp = ($Stamp -replace '[^A-Za-z0-9._-]', '-') -replace '-{2,}', '-'
    $Stamp = $Stamp.Trim('-')
    if ([string]::IsNullOrWhiteSpace($Stamp)) {
        throw "package_release: -Stamp contained no usable characters after sanitising."
    }
    $Name = "ER-Archipelago-v$Version-UNOFFICIAL-$Stamp"
    Write-Host ""
    Write-Host "  *** UNOFFICIAL BUILD -- '$Stamp' ***" -ForegroundColor Magenta
    Write-Host "  Identity gates will WARN instead of failing; correctness gates still fail hard." -ForegroundColor Magenta
    Write-Host "  This run can never exit 0. Do not publish this artifact as a release." -ForegroundColor Magenta
    Write-Host ""
} else {
    if (-not [string]::IsNullOrWhiteSpace($Stamp)) {
        throw "package_release: -Stamp is only meaningful with -Unofficial."
    }
    $Name = "ER-Archipelago-v$Version"
}
$Stage = Join-Path $Dist $Name

# ---- THE CHANGELOG MUST DESCRIBE THE VERSION BEING PACKAGED -----------------------------------
# v0.2.10 shipped to GitHub and Nexus with NO changelog entry at all (issue #216), and v0.2.11 was
# tagged one commit BEFORE its entry landed -- so a clean checkout of the tag would have packaged a
# CHANGELOG whose newest release was 0.2.9. Both slipped because "tag the green commit" and "tag the
# commit whose docs describe the release" pull in opposite directions when the docs land last.
# Nothing was checking, and CHANGELOG.md is shipped required=$true, so the bad file goes to players.
#
# This is a CONTENT check, deliberately: the previous freshness gate here compared timestamps and was
# unpassable by construction. Read the first "## vX.Y.Z" heading and require it to be the version
# being built. Passable by doing the right thing (write the entry, then package), and it fails loudly
# when it is not done.
$chgPath = Join-Path $Rel "CHANGELOG.md"
if (-not (Test-Path $chgPath)) {
    throw "package_release: CHANGELOG.md not found at $chgPath -- it ships as a required doc."
}
$chgTop = (Select-String -Path $chgPath -Pattern '^##\s+v([0-9]+(?:\.[0-9]+)+)' |
           Select-Object -First 1)
if (-not $chgTop) {
    throw "package_release: no '## vX.Y.Z' heading found in CHANGELOG.md -- cannot confirm this " +
          "build is documented. Fix the changelog rather than removing this check."
}
$chgVer = $chgTop.Matches[0].Groups[1].Value
if ($chgVer -ne $Version -and $Unofficial) {
    Warn ("changelog's newest entry is v$chgVer, this build is v$Version -- expected for an " +
          "unofficial cut, but the bundled CHANGELOG will NOT describe what you are handing over. " +
          "Say so when you send it.")
} elseif ($chgVer -ne $Version) {
    throw ("package_release: CHANGELOG.md's newest entry is v$chgVer but this build is v$Version. " +
           "Players get whatever is in that file, so shipping it would describe the wrong release " +
           "(this is exactly how v0.2.10 shipped undocumented). Write the v$Version entry FIRST, " +
           "then tag and package -- or pass -Version $chgVer if that is the build you meant.")
}
Write-Host "  changelog: newest entry is v$chgVer, matches the build" -ForegroundColor DarkGray

# ---- VERSION LOCKSTEP -------------------------------------------------------------------------
# The changelog gate above covers ONE site. It did not cover the others, and on 2026-07-28 v0.2.14
# shipped with APWORLD_VERSION still reading "0.2.13": the tag said one thing and every seed built
# from it reported another, so a bug report could not tell the two releases apart. A gate that
# checks one of four places is why that was invisible.
#
# These are the sites that must all equal -Version. Strict three-component semver, because Cargo's
# version field will not parse "0.2.12.1" (the Nexus LABEL is free text; the number is not).
# !! THE SITE LIST IS THE TEST'S, NOT A SECOND ONE. test_gf_apworld_manifest.py
# ::test_the_three_version_numbers_are_one_number already names the sites (archipelago.json,
# contract.py, the client crate). On 2026-07-28 this gate was first written with a hand-made list
# that MISSED archipelago.json, reported "all sites agree", and the suite caught the third site --
# a readiness check that derives its own definition of ready is the confident wrong answer this repo
# is full of. Keep these in sync with that test; if they drift, the test is right.
$verSites = @(
    @{ Path = (Join-Path $Repo "greenfield\eldenring\archipelago.json");
       Rx   = '"world_version"\s*:\s*"([0-9]+(?:\.[0-9]+)+)"'; What = "archipelago.json world_version" },
    @{ Path = (Join-Path $Repo "greenfield\eldenring\contract.py");
       Rx   = '^APWORLD_VERSION\s*=\s*"([0-9]+(?:\.[0-9]+)+)"'; What = "contract.py APWORLD_VERSION" },
    @{ Path = (Join-Path $Repo "from-software-archipelago-clients\crates\eldenring-archipelago\Cargo.toml");
       Rx   = '^version\s*=\s*"([0-9]+(?:\.[0-9]+)+)"'; What = "client Cargo.toml version"; Optional = $true }
)
foreach ($site in $verSites) {
    if (-not (Test-Path $site.Path)) {
        if ($site.Optional) {
            # The client is a submodule: legitimately absent in a world-only checkout. SKIP LOUDLY --
            # a silent skip is the same unchecked site by another route.
            Write-Host ("  version:   SKIP " + $site.What + " -- not checked out at " + $site.Path) -ForegroundColor Yellow
            continue
        }
        throw ("package_release: version site missing -- " + $site.What + " at " + $site.Path +
               ". Fix the path rather than dropping the check; an unchecked site is how v0.2.14 " +
               "shipped stamped 0.2.13.")
    }
    $m = (Select-String -Path $site.Path -Pattern $site.Rx | Select-Object -First 1)
    if (-not $m) {
        throw ("package_release: could not read a version out of " + $site.What +
               ". The pattern no longer matches -- a silently unmatched regex is an unchecked site.")
    }
    $siteVer = $m.Matches[0].Groups[1].Value
    if ($siteVer -ne $Version -and $Unofficial) {
        Warn ($site.What + " is v$siteVer but this build is labelled v$Version -- seeds will " +
              "report v$siteVer. Fine for an unofficial cut; the SHAs in UNOFFICIAL-BUILD.txt are " +
              "what identifies it, not the version number.")
    } elseif ($siteVer -ne $Version) {
        throw ("package_release: " + $site.What + " is v$siteVer but this build is v$Version. " +
               "Every seed would report v$siteVer, so a bug report could not tell this release " +
               "from that one -- exactly how v0.2.14 shipped stamped 0.2.13. Bump it, or pass " +
               "-Version $siteVer if that is the build you meant.")
    }
    Write-Host ("  version:   " + $site.What + " is v$siteVer, matches the build") -ForegroundColor DarkGray
}

# ---------------------------------------------------------------------------
# 1. Fresh apworld
# ---------------------------------------------------------------------------
$Apworld = Join-Path $Repo "eldenring.apworld"
if (-not $SkipApworld) {
    Info "Building fresh apworld (build.ps1 -Apworld) ..."
    & (Join-Path $Repo "build.ps1") -Apworld
    if ($LASTEXITCODE -ne 0) { Die "build.ps1 -Apworld failed (exit $LASTEXITCODE)." }
}
if (-not (Test-Path $Apworld)) {
    Die "eldenring.apworld not found at $Apworld. Run without -SkipApworld, or build it first."
}

# ---------------------------------------------------------------------------
# 1a. ZIP-GEN GATE -- the artifact must actually generate from custom_worlds.
# ---------------------------------------------------------------------------
# The apworld we are about to ship is a ZIP. Code that reads a bundled data file via
# open(dirname(__file__)/name) works unpacked (every unit test) and raises inside the archive -- which
# is how the 2026-07-19 build shipped un-generatable: coverage.py's open() on check_lots_table.json
# failed in the zip, the coverage gate raised CoverageError at post_fill, and every custom_worlds
# generation died. Gate on the EXACT artifact here (gf_zip_gen_smoke.py --apworld drops it into a
# custom_worlds\ checkout and runs one generation), so a broken .apworld can never leave this script.
if (-not $SkipGenSmoke) {
    Info "Gen-smoke: generating one seed from the built apworld (custom_worlds) ..."
    python (Join-Path $Repo "tools\gf_zip_gen_smoke.py") --apworld $Apworld
    if ($LASTEXITCODE -ne 0) {
        Die "the built eldenring.apworld FAILED to generate from custom_worlds (exit $LASTEXITCODE) -- a bundled-resource read is not zip-safe. Refusing to package an un-generatable artifact (the 2026-07-19 crash class)."
    }
    Info "Gen-smoke: OK -- the artifact generates cleanly from a zip."
}

# ---------------------------------------------------------------------------
# 2. Clean staging dir
# ---------------------------------------------------------------------------
if (Test-Path $Stage) { Remove-Item $Stage -Recurse -Force }
New-Item -ItemType Directory -Force -Path $Stage | Out-Null
Info "Staging into $Stage"

# ---------------------------------------------------------------------------
# 3. apworld
# ---------------------------------------------------------------------------
Copy-Item $Apworld (Join-Path $Stage "eldenring.apworld") -Force
Info "+ eldenring.apworld"

# ---------------------------------------------------------------------------
# 3b. CROSS-REPO DATA AGREEMENT -- the apworld and the client must be built from the
#     SAME world data.
# ---------------------------------------------------------------------------
# TWO generated tables are emitted BY the world INTO the client: contract_gen.rs and region_locks.rs.
# (There were three; tracker_regions.rs was retired 2026-07-28 when the tracker's region model moved
# into slot_data, which removes a whole class of cross-repo drift rather than gating it.) They ship
# COMPILED INTO the .dll while the data they were derived from ships in the .apworld -- two halves of
# one bundle, from two repos, with nothing tying them together at package time.
#
# 2026-07-24, the release that prompted this gate: world main and client main disagreed by 465 lines
# of tracker_regions.rs (the client's copy had been generated from a feature branch's data -- 4853
# locations vs main's 4848). The apworld's own CI step was GREEN; only the cross-repo check was red,
# and a bundle was published from that state. A contract mismatch surfaces to a PLAYER on connect,
# which is the worst possible place to find it.
#
# So: re-derive the three tables from THIS tree and refuse to package if the client's committed
# copies differ. Then check the .dll being shipped is NEWER than them -- source agreement proves
# nothing if the binary predates the regen.
if (-not $SkipCrossRepoCheck) {
    $Client = Join-Path $Repo "from-software-archipelago-clients"
    if (-not (Test-Path (Join-Path $Client ".git"))) {
        Warn "client submodule not checked out -- cross-repo data agreement UNVERIFIED"
    } else {
        Info "Cross-repo: re-deriving the client's generated tables from this world tree ..."
        # tools\gen_location_regions.py was RETIRED 2026-07-28 along with tracker_regions.rs: the
        # tracker's region model ships in slot_data now (locationRegions / regionCoarseKeys), so
        # there is no generated table left to drift. It is off this list rather than left to fail.
        foreach ($t in @("tools\gen_region_locks.py")) {
            $tPath = Join-Path $Repo $t
            # A MISSING GENERATOR IS NOT A STALE TABLE. python exits nonzero on "No such file", and
            # this loop read every nonzero as STALE -- so deleting a generator produced "the client's
            # generated table is STALE. Regenerate (build.ps1 -All)", advice that cannot work because
            # the tool it names does not exist. Separate the two before running it.
            if (-not (Test-Path $tPath)) {
                Die ("$t does not exist, so this check cannot run. It was NOT reporting a stale " +
                     "table -- a missing generator exits nonzero exactly like a stale one. Either " +
                     "restore the tool or remove it from this list, whichever matches why it went.")
            }
            & python $tPath --check
            if ($LASTEXITCODE -eq 4) { Warn "$t --check: no client tree; UNVERIFIED" }
            elseif ($LASTEXITCODE -ne 0) {
                Die ("$t reports the client's generated table is STALE. The .apworld and the .dll " +
                     "would ship from DIFFERENT world data -- the contract mismatch lands on the " +
                     "player at connect. Regenerate (build.ps1 -All), rebuild the client, push both.")
            }
        }
        # contract_gen.rs has no --check: emit it and compare the client working tree instead.
        & python (Join-Path $Repo "greenfield\gen_contract.py")
        if ($LASTEXITCODE -ne 0) { Die "gen_contract.py FAILED -- cannot verify the client contract table." }
        $dirty = & git -C $Client status --porcelain -- `
                    "crates/er-logic/src/region_locks.rs" `
                    "crates/eldenring-archipelago/src/contract_gen.rs"
        if ($dirty) {
            Die ("the client's generated tables do not match this world tree:`n$dirty`n" +
                 "Commit + push the client, rebuild the .dll, then package.")
        }
        Info "Cross-repo: apworld and client generated tables AGREE."

        # The .dll is a BUILD ARTIFACT: matching sources prove nothing if the binary was built from
        # different bytes. The question is "was this .dll compiled from the tables about to ship?",
        # and NO TIMESTAMP CAN ANSWER IT. Both previous attempts were unpassable:
        #   * file mtime -- a git checkout stamps it without changing content, so a current .dll
        #     read as stale; and this script used to rewrite contract_gen.rs a few lines above,
        #     guaranteeing its own next failure.
        #   * git commit time -- worse, unpassable BY CONSTRUCTION: you necessarily commit the
        #     regenerated tables AFTER you build the .dll from them, so the table always post-dates
        #     the binary and the gate can never go green. (Caught by Alaric, 2026-07-26.)
        # So compare CONTENT. build.ps1 -Rust writes the SHA-256 of the three generated tables next
        # to the .dll it just compiled, and -Me3Deploy carries that stamp along with the binary.
        $xrDll = Join-Path (Join-Path $Repo "me3") "eldenring_archipelago.dll"
        $xrStampPath = "$xrDll.tables.json"
        if (-not (Test-Path $xrDll)) {
            Warn "me3\eldenring_archipelago.dll not present yet -- .dll freshness UNVERIFIED"
        } elseif (-not (Test-Path $xrStampPath)) {
            Warn ("no build stamp beside the .dll -- it predates build.ps1's table stamping. " +
                  ".dll/table agreement UNVERIFIED; run build.ps1 -Rust -Me3Deploy to produce one.")
        } else {
            $xrStamp = Get-Content -LiteralPath $xrStampPath -Raw | ConvertFrom-Json
            $xrMismatch = @()
            # tracker_regions.rs was here until 2026-07-28. It is DELETED, and `Test-Path ... continue`
            # below would have skipped it forever -- a list entry that always skips is dead weight
            # that reads like coverage.
            foreach ($xrRel in @("crates/er-logic/src/region_locks.rs",
                               "crates/eldenring-archipelago/src/contract_gen.rs")) {
                $xrFile = Join-Path $Client ($xrRel -replace "/", "\")
                if (-not (Test-Path $xrFile)) { continue }
                $xrNow = (Get-FileHash -Algorithm SHA256 -LiteralPath $xrFile).Hash
                $xrWas = $xrStamp.$xrRel
                if (-not $xrWas) { $xrMismatch += "$xrRel (not in the build stamp)" }
                elseif ($xrWas -ne $xrNow) { $xrMismatch += "$xrRel (built from $($xrWas.Substring(0,12))..., tree has $($xrNow.Substring(0,12))...)" }
            }
            if ($xrMismatch.Count -gt 0) {
                $xrMsg = "the staged .dll was built from DIFFERENT generated tables than the ones about to ship:`n"
                $xrMsg += ($xrMismatch -join "`n")
                $xrMsg += "`nRebuild the client (build.ps1 -Rust -Me3Deploy) before packaging."
                Die $xrMsg
            }
            Info "Cross-repo: the staged .dll was built from exactly these generated tables (SHA-256)."
        }
    }
}

# ---------------------------------------------------------------------------
# 3c. CLIENT IDENTITY -- the pin, the tree, client main and the .dll must name ONE build.
# ---------------------------------------------------------------------------
# 3b above proves the apworld and the .dll were built from the same DATA. This proves the release
# can still SAY, afterwards, which client it was. Different question, and v0.3.11 is why it is here:
# the tag pinned client a9830ebe while the tree that got packaged -- and client main -- were at
# 19825995, 41 commits apart.
#
# 🛑 READ THIS BEFORE CHANGING ANYTHING BELOW. v0.3.11's BUNDLE WAS CURRENT. This script packages
# the client WORKING TREE, so players got the right .dll and every gate that looked at the artifact
# was correctly green. Two reviewers have since inferred the artifact from the pin and been wrong
# about it in writing. A GITLINK IS A RECORD, NOT A BUILD INPUT. What was lost is the PAIRING: no
# bug report against that tag can ever be resolved to a client commit, and no later fix recovers it.
#
# The check itself lives in Python (tools\check_release_pairing.py) so CI and any future
# cut_release.py run the SAME code -- the four-instruments-four-answers situation this defect grew
# out of is retired by having one implementation. It runs HERE because a CI job can be routed
# around and on v0.3.11 one was: release.yaml's pin step went red AFTER the tag was public and the
# release shipped anyway. This is the moment the zip is born. No agreement, no zip.
$pairTool = Join-Path $Repo "tools\check_release_pairing.py"
if (-not (Test-Path $pairTool)) {
    Die ("tools\check_release_pairing.py is missing, so client identity cannot be verified. " +
         "Restore it -- do not package around it.")
}
if ($AllowStalePin) { $env:ALLOW_STALE_PIN = "1" } else { $env:ALLOW_STALE_PIN = "0" }
$pairDll = Join-Path (Join-Path $Repo "me3") "eldenring_archipelago.dll"
$pairArgs = @($pairTool, "--repo", $Repo)
if (Test-Path $pairDll) { $pairArgs += @("--dll", $pairDll) }
& python @pairArgs
$pairExit = $LASTEXITCODE
$env:ALLOW_STALE_PIN = $null
# Under -Unofficial this is an IDENTITY gate by the script's own taxonomy (see the header): an
# unofficial build claims to be nothing, so a mismatch is expected rather than dangerous. It still
# warns, so the run exits 2 and the operator has read the SHAs. There is deliberately no -Skip
# switch: the whole failure mode was a check that could be walked past.
if ($pairExit -eq 1) {
    if ($Unofficial) { Warn "client identity does not agree (see above) -- unofficial build, continuing." }
    else {
        Die ("the pin, the client tree, client main and the .dll do not name one build (see above). " +
             "A release packaged from here could never be resolved back to a client commit. Fix the " +
             "pairing, or pass -AllowStalePin if the gitlink deliberately trails client main.")
    }
} elseif ($pairExit -eq 2) {
    Warn "packaging with a KNOWN-STALE client pin (see above). Review before shipping."
} elseif ($pairExit -ne 0) {
    Die "check_release_pairing.py exited $pairExit -- it did not run, so identity is UNVERIFIED."
} else {
    Info "Client identity: the pin, the client tree, client main and the .dll name one build."
}

# ---------------------------------------------------------------------------
# 4. me3 runtime (client + AP-icon override + config)
# ---------------------------------------------------------------------------
$Me3Src = Join-Path $Repo "me3"
if (-not (Test-Path $Me3Src)) { Die "me3\ runtime folder not found at $Me3Src." }
$Me3Dst = Join-Path $Stage "me3"
New-Item -ItemType Directory -Force -Path $Me3Dst | Out-Null

# ALLOWLIST, not blacklist. The old code copied me3\ WHOLESALE and then stripped a hand-list of cruft
# (saves / logs / .bak) -- so anything the strip-list didn't anticipate rode into the release: stale
# .NET / old-loader artifacts, leftover mods\, a second dll, whatever was in your working me3\. A
# strip-list is always one surprise behind. Copy ONLY the known release entries instead, so nothing
# unexpected can ever ship. apconfig.json is (re)written fresh below, so it is deliberately NOT here.
$Me3Allow = @('ap.me3', 'eldenring_archipelago.dll', 'check_lots_table.json', 'shoplineup_flags.json', 'ap-package')
$copied = 0
foreach ($name in $Me3Allow) {
    $src = Join-Path $Me3Src $name
    if (Test-Path $src) { Copy-Item $src (Join-Path $Me3Dst $name) -Recurse -Force; $copied++ }
}
Info "+ me3\ (allowlisted $copied of $($Me3Allow.Count) entries)"

# Report -- loudly -- everything in your working me3\ that was NOT shipped, so cruft is visible (and you
# can go clean it) even though the allowlist already kept it OUT of the release. apconfig.json is
# expected (written fresh below) so it isn't flagged.
$skipped = @(Get-ChildItem -Path $Me3Src -Force -ErrorAction SilentlyContinue |
             Where-Object { $_.Name -notin $Me3Allow -and $_.Name -ne 'apconfig.json' })
if ($skipped.Count -gt 0) {
    Warn ("excluded $($skipped.Count) non-release item(s) from your working me3\ (NOT shipped -- clean them up): " +
          (($skipped | Select-Object -First 25 | ForEach-Object { $_.Name }) -join ", "))
}
# Belt-and-suspenders: the save state must NEVER ship (the allowlist already excludes it, but assert).
$LeakedSaves = @(Get-ChildItem -Path $Me3Dst -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'ap_save_*.json' })
if ($LeakedSaves.Count -gt 0) { Die ("save-state file(s) staged despite the allowlist: " + ($LeakedSaves.Name -join ", ")) }

# Hard requirements: without these the game will not load the client.
$Dll   = Join-Path $Me3Dst "eldenring_archipelago.dll"
$Prof  = Join-Path $Me3Dst "ap.me3"
if (-not (Test-Path $Dll))  { Die "missing client DLL: me3\eldenring_archipelago.dll" }
if ((Get-Item $Dll).Length -lt 1024) { Die "client DLL looks empty ( < 1 KB ): $Dll" }
if (-not (Test-Path $Prof)) { Die "missing me3 profile: me3\ap.me3" }

# Freshness guard: the wholesale me3\ copy can carry a STALE client DLL if build.ps1
# -Rust / -Me3Deploy wasn't run after code changes. Compare staged vs freshly-built.
$BuiltDll = Join-Path $Repo "from-software-archipelago-clients\target\x86_64-pc-windows-msvc\release\eldenring_archipelago.dll"
$StagedDllTime = (Get-Item $Dll).LastWriteTime
if (Test-Path $BuiltDll) {
    $BuiltDllTime = (Get-Item $BuiltDll).LastWriteTime
    if ($BuiltDllTime -gt $StagedDllTime) {
        Warn ("staged client DLL is OLDER than the last cargo build (staged {0:yyyy-MM-dd HH:mm} < built {1:yyyy-MM-dd HH:mm}) -- run build.ps1 -Rust -Me3Deploy before packaging or the release ships a stale client." -f $StagedDllTime, $BuiltDllTime)
    } else {
        Info ("client DLL is current (staged {0:yyyy-MM-dd HH:mm} >= last build {1:yyyy-MM-dd HH:mm})" -f $StagedDllTime, $BuiltDllTime)
    }
} else {
    Warn "no built client DLL under from-software-archipelago-clients\target\...\release\ to compare against -- cannot confirm the staged DLL is current (did you run build.ps1 -Rust?)."
}
Info ("staged client DLL timestamp: {0:yyyy-MM-dd HH:mm:ss}" -f $StagedDllTime)

# Detection table + config: warn (not fatal) if absent.
# er_static_detection_table.json was removed from the project entirely (2026-07-12) -- an
# unreproducible baker-era file that only ever existed on the dev box. Nothing stages it, so
# there is nothing to check for here.

# AP-icon override = me3\ap-package\menu textures. HARD FAIL if absent.
#
# This used to Info "cosmetic nicety, not a feature" and ship anyway. That rationale was wrong, and
# it is why the flower has never actually shipped from this tree. The CLIENT unconditionally points
# the placeholder AND every repointed shop slot at iconId 92 (check_lots.rs dress_placeholder,
# shop_icon.rs), on the assumption that ap-package repaints cell 92 into the AP flower. Without the
# package, that assumption is false and every one of those slots renders a literal TELESCOPE --
# which is exactly what a player reported on Nexus 2026-07-29 ("with ... telescope icon but i dont
# know what ap item it is"). A client that writes an icon id and a bundle that does not define it
# are two halves of one feature; shipping half of it silently is the failure mode this whole
# repo's gates exist to stop.
#
# !! THE TEXTURE ITSELF IS NOT AND MUST NOT BE COMMITTED -- it is a repainted FromSoft sprite sheet
# (menu\hi|low\01_common.tpf.dcx), i.e. game data, barred by PROVENANCE.md rule 1. It is BUILT per
# machine from the local install. What must be committed is the TOOL that builds it.
$IconMenu = Join-Path $Me3Dst "ap-package\menu"
$IconFiles = @()
if (Test-Path $IconMenu) {
    $IconFiles = @(Get-ChildItem -Path $IconMenu -Recurse -File -ErrorAction SilentlyContinue)
}
$IconSheets = @($IconFiles | Where-Object { $_.Name -ieq "01_common.tpf.dcx" })
if ($IconSheets.Count -eq 0) {
    Die ("no AP flower-icon sprite sheet staged at $IconMenu (need menu\hi and/or menu\low " +
         "01_common.tpf.dcx). The client points the placeholder and every repointed shop slot at " +
         "iconId 92 and RELIES on this override to repaint it; without it players see a literal " +
         "telescope. Build it, then re-run: " +
         "python build_ap_icon.py --icon01 --icon-id 92 --black-to-alpha --bundles hi,low --menu ""<game>\menu""")
}
Info "+ AP-icon override ($($IconSheets.Count) sprite sheet(s), $($IconFiles.Count) file(s) in ap-package\menu)"

# Ship a GENERIC apconfig so a personal slot name never leaks into the release.
#
# archipelago.gg, NOT localhost (2026-08-11). Almost nobody self-hosts, so `localhost:38281` was a
# default that worked for the few and silently failed for everyone else -- and it failed by LOOKING
# plausible, which is the worst way for a default to be wrong.
#
# 🛑 THE PORT IS A DELIBERATE PLACEHOLDER, NOT A VALUE. archipelago.gg assigns every room its own
# port when the room is created, so there is no number that could go here and be right; 38281 is the
# LOCAL default and putting it beside archipelago.gg would teach exactly the wrong thing. `PORT`
# cannot be mistaken for a working setting. It is safe to ship because the client treats an
# unparseable port the same way it treats a blank url -- it does not attempt the connection and the
# in-game overlay asks instead (shared::config::is_connectable, client PR pairing this one). Do not
# revert this to a number without checking that guard is still there.
#
# MULTI-LINE, and it must stay byte-identical to what the client would write (Alaric, 2026-08-12:
# "can we write that so it's formatted across multiple lines?"). This is a file we ask players to
# OPEN AND EDIT -- url, slot, and since the probe work the diagnostic flags too -- so shipping it as
# one 96-character line was a poor thing to hand someone. `shared::config::serialize_config` (client
# PR pairing this one) pretty-prints on save; if THIS stayed one line the player's file would still
# reflow under them the first time they connected through the overlay, which is the same surprise
# with a delay. `the_template_shape_is_what_we_ship` over there asserts these exact bytes.
#
# LF and no BOM, via WriteAllText -- `Set-Content` would emit CRLF on Windows and the client writes
# LF, so the first save would rewrite every line ending for no reason. ASCII-safe by construction.
$ApConfig = Join-Path $Me3Dst "apconfig.json"
$ApConfigText = @(
    '{'
    '  "url": "archipelago.gg:PORT",'
    '  "slot": "Player1",'
    '  "seed": "",'
    '  "client_version": null,'
    '  "password": null'
    '}'
) -join "`n"
[IO.File]::WriteAllText($ApConfig, $ApConfigText + "`n", [Text.UTF8Encoding]::new($false))
Info "+ apconfig.json (generic template: archipelago.gg / Player1 -- port is a placeholder)"

# ---------------------------------------------------------------------------
# 5. Flagship yaml + docs
#    (PopTracker pack is intentionally NOT bundled -- it lives in the repo for
#    anyone who wants it; the built-in F6 tracker is the shipped tracker.)
# ---------------------------------------------------------------------------
# The REAL doc set. This list required five files that DO NOT EXIST -- LICENSE,
# EldenRing-Shattering.yaml, HOW-THE-SHATTERING-WORKS.md, CHECKS-AND-PROGRESSION.md and
# ENEMY-AND-STARTING-CLASS-RANDOMIZATION.md -- so the packager Died on the first one and there was
# no working way to build a release. The two that were worth keeping have been WRITTEN (LICENSE,
# ENEMY-AND-STARTING-CLASS-RANDOMIZATION.md); the rest were folded into the Player Guide.
$Docs = @(
    @{ src = (Join-Path $Rel  "LICENSE");                                  required = $true  },
    @{ src = (Join-Path $Rel  "EldenRing.yaml");                           required = $true  },
    @{ src = (Join-Path $Rel  "SETUP.md");                                 required = $true  },
    @{ src = (Join-Path $Rel  "RELEASE-NOTES-v0.2.md");                    required = $true  },
    @{ src = (Join-Path $Rel  "CHANGELOG.md");                             required = $true  },
    @{ src = (Join-Path $Rel  "KNOWN-ISSUES.md");                          required = $true  },
    @{ src = (Join-Path $Rel  "ATTRIBUTION.md");                           required = $true  },
    @{ src = (Join-Path $Rel  "PROVENANCE.md");                            required = $true  },
    @{ src = (Join-Path $Rel  "ENEMY-AND-STARTING-CLASS-RANDOMIZATION.md"); required = $true  },
    @{ src = (Join-Path $Repo "Elden-Ring-Archipelago-Player-Guide.md");   required = $true  },
    @{ src = (Join-Path $Rel  "SCREENSHOTS.md");                           required = $false },
    @{ src = (Join-Path $Rel  "DISTRIBUTION.md");                          required = $false }
)

# The docs reference screenshots/*.png with relative paths. Ship the folder or every image link
# in the release zip is a broken image.
$Shots = Join-Path $Rel "screenshots"
if (Test-Path $Shots) {
    Copy-Item $Shots (Join-Path $Stage "screenshots") -Recurse -Force
    Info ("+ screenshots/ (" + (Get-ChildItem $Shots -Filter *.png).Count + " images)")
}
foreach ($d in $Docs) {
    if (Test-Path $d.src) {
        Copy-Item $d.src $Stage -Force
        Info ("+ " + (Split-Path $d.src -Leaf))
    } elseif ($d.required) {
        Die ("missing required file: " + $d.src)
    }
}

# ---------------------------------------------------------------------------
# 6b. Third-party binary gate -- we ship OUR binaries and nobody else's
# ---------------------------------------------------------------------------
# We point players at thefifthmatt's randomizer rather than redistribute it (PROVENANCE.md), and
# his terms forbid shipping a modified fork. Players commonly run our DLL alongside third-party
# ones -- RandomizerCrashFix.dll, RandomizerHelper.dll -- by dropping them in the same me3 natives
# list. That is THEIR machine and entirely their business. The hazard is that a dev staging a
# release from a working game folder sweeps those DLLs into our zip and we redistribute someone
# else's binary without a licence to do it.
#
# ALLOWLIST, not a denylist. A list of known-bad names would pass the next third-party DLL nobody
# thought of, which is the failure this gate exists to prevent. Anything binary in the stage that
# is not ours stops the build; add it here deliberately, with a reason, or do not ship it.
$OurBinaries = @(
    "eldenring_archipelago.dll"   # our client, built from the sibling client repo
)
$Foreign = @()
Get-ChildItem -Path $Stage -Recurse -File -Include *.dll,*.exe,*.asi | ForEach-Object {
    if ($OurBinaries -notcontains $_.Name) {
        $Foreign += $_.FullName.Substring($Stage.Length + 1)
    }
}
if ($Foreign.Count -gt 0) {
    Die ("refusing to package third-party binaries: " + ($Foreign -join ", ") + ". We redistribute only our own DLL (PROVENANCE.md); point players at the upstream download instead. If one of these is genuinely ours, add it to `$OurBinaries in package_release.ps1 with a reason.")
}
Info ("third-party binary gate: OK -- " + $OurBinaries.Count + " allowed binary name(s), 0 foreign.")

# ---------------------------------------------------------------------------
# 6c. UNOFFICIAL-BUILD.txt -- so the artifact can identify itself
#
# A version number cannot identify an unofficial cut: by construction the version sites still say
# whatever main says. The SHAs can. Both of them -- the world alone is not enough, because CI
# checks the client out from ITS main and the gitlink is what a local build actually compiled.
# ---------------------------------------------------------------------------
if ($Unofficial) {
    function GitAt($dir, $args) {
        if (-not (Test-Path $dir)) { return "(not checked out)" }
        try   { $o = (& git -C $dir $args 2>$null); if ($LASTEXITCODE -eq 0 -and $o) { return ($o | Select-Object -First 1).ToString().Trim() } }
        catch { }
        return "(unavailable)"
    }
    $clientDir = Join-Path $Repo "from-software-archipelago-clients"
    $worldSha  = GitAt $Repo       @("rev-parse","HEAD")
    $worldBr   = GitAt $Repo       @("rev-parse","--abbrev-ref","HEAD")
    $worldDty  = GitAt $Repo       @("status","--porcelain")
    $cliSha    = GitAt $clientDir  @("rev-parse","HEAD")
    $cliBr     = GitAt $clientDir  @("rev-parse","--abbrev-ref","HEAD")
    $cliDty    = GitAt $clientDir  @("status","--porcelain")

    $lines = @(
        "UNOFFICIAL BUILD -- NOT A RELEASE",
        "",
        "label:        $Stamp",
        "built:        $TimeStamp",
        "version label: v$Version  (the version SITES may disagree -- see warnings below)",
        "",
        "world  commit: $worldSha  branch: $worldBr",
        "client commit: $cliSha  branch: $cliBr",
        ""
    )
    if ($worldDty -and $worldDty -ne "(unavailable)" -and $worldDty -ne "(not checked out)") {
        $lines += "WARNING: the world tree had UNCOMMITTED CHANGES at build time."
        $lines += "         The commit above does not fully describe this artifact."
        $lines += ""
    }
    if ($cliDty -and $cliDty -ne "(unavailable)" -and $cliDty -ne "(not checked out)") {
        $lines += "WARNING: the client tree had UNCOMMITTED CHANGES at build time."
        $lines += "         The commit above does not fully describe this artifact."
        $lines += ""
    }
    $lines += "If you are reporting a bug against this build, quote the two commits above."
    $lines += "A version number alone cannot identify it."
    if ($Warnings.Count -gt 0) {
        $lines += ""
        $lines += "Packaging warnings:"
        foreach ($w in $Warnings) { $lines += "  - $w" }
    }
    $infoPath = Join-Path $Stage "UNOFFICIAL-BUILD.txt"
    Set-Content -Path $infoPath -Value $lines -Encoding ascii
    Info "unofficial: wrote UNOFFICIAL-BUILD.txt (world $worldSha / client $cliSha)"
}

# ---------------------------------------------------------------------------
# 7. Manifest + zip
# ---------------------------------------------------------------------------
Info "----- bundle contents -----"
Get-ChildItem -Path $Stage -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($Stage.Length + 1)
    $kb  = [math]::Round($_.Length / 1KB, 1)
    Write-Host ("       {0,8} KB  {1}" -f $kb, $rel)
}
$totalMB = [math]::Round((Get-ChildItem -Path $Stage -Recurse -File | Measure-Object Length -Sum).Sum / 1MB, 1)
Info "total staged size: $totalMB MB"

if ($DryRun) {
    Info "DryRun: staged at $Stage (no zip written)."
} else {
    $Zip = Join-Path $Dist ("{0}-{1}.zip" -f $Name, $TimeStamp)
    if (Test-Path $Zip) { Remove-Item $Zip -Force }
    Compress-Archive -Path (Join-Path $Stage "*") -DestinationPath $Zip -Force
    Info "zip written: $Zip"

    # SECOND ASSET: the bare apworld, for HOSTS.
    #
    # Someone generating a multiworld needs the apworld and nothing else -- they may not even be
    # playing Elden Ring. Making them pull a 10 MB bundle containing a game-mod DLL, in order to
    # generate somebody else's seed, is friction for nothing.
    #
    # It ships from the SAME TAG as the bundle on purpose. The apworld and the client .dll are a
    # HASH-MATCHED PAIR (the client compares the apworld's contract hash on connect and errors on
    # skew), and a mismatched pair does not fail at the door -- it boots, connects, and misbehaves
    # quietly. Same tag, or nothing. See DISTRIBUTION.md.
    $BareApworld = Join-Path $Dist ("{0}-{1}.apworld" -f $Name, $TimeStamp)
    Copy-Item $Apworld $BareApworld -Force
    Info "bare apworld: $BareApworld  (upload this ALONGSIDE the zip, same release tag)"
}

# ---------------------------------------------------------------------------
# 8. Summary
# ---------------------------------------------------------------------------
if ($Warnings.Count -gt 0) {
    Write-Host ""
    Write-Host "[pkg] DONE with $($Warnings.Count) warning(s):" -ForegroundColor Yellow
    foreach ($w in $Warnings) { Write-Host "        - $w" -ForegroundColor Yellow }
    exit 2
} elseif ($Unofficial) {
    # No warnings fired, but this still is not a release. Exit 2 so nothing downstream can mistake
    # an unofficial cut for a green release build.
    Write-Host ""
    Write-Host "[pkg] DONE -- UNOFFICIAL build '$Stamp'. Not a release; see UNOFFICIAL-BUILD.txt." -ForegroundColor Magenta
    exit 2
} else {
    Info "DONE clean -- bundle ready."
    exit 0
}