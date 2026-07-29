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
# Exit codes: 0 = clean, 2 = staged but with warnings (review before shipping).

[CmdletBinding()]
param(
    [string]$Version = "0.2",
    [switch]$SkipApworld,
    [switch]$SkipGenSmoke,   # skip the zipped-apworld generation gate (NOT recommended for a real release)
    [switch]$SkipCrossRepoCheck, # skip the apworld<->client data-agreement gate (NOT recommended)
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
# Normalize the version: accept -Version 0.1.1 OR v0.1.1; the zip name prepends its own "v".
$Version = $Version -replace '^[vV]', ''
$Repo  = $PSScriptRoot
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Name  = "ER-Archipelago-v$Version"
$Dist  = Join-Path $Repo "dist"
$Stage = Join-Path $Dist $Name
$Rel   = Join-Path $Repo "release-v0.2"

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
if ($chgVer -ne $Version) {
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
    if ($siteVer -ne $Version) {
        throw ("package_release: " + $site.What + " is v$siteVer but this build is v$Version. " +
               "Every seed would report v$siteVer, so a bug report could not tell this release " +
               "from that one -- exactly how v0.2.14 shipped stamped 0.2.13. Bump it, or pass " +
               "-Version $siteVer if that is the build you meant.")
    }
    Write-Host ("  version:   " + $site.What + " is v$siteVer, matches the build") -ForegroundColor DarkGray
}

$Warnings = New-Object System.Collections.Generic.List[string]

function Info($m) { Write-Host "[pkg]  $m" }
function Warn($m) { Write-Host "[warn] $m" -ForegroundColor Yellow; $Warnings.Add($m) | Out-Null }
function Die($m)  { throw "[pkg] $m" }

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

# AP-icon override = me3\ap-package\menu textures. Warn loudly if empty so a
# bundle without the flower-icon swap never ships silently.
$IconMenu = Join-Path $Me3Dst "ap-package\menu"
$IconFiles = @()
if (Test-Path $IconMenu) {
    $IconFiles = @(Get-ChildItem -Path $IconMenu -Recurse -File -ErrorAction SilentlyContinue)
}
if ($IconFiles.Count -eq 0) {
    Info "  (no AP flower-icon texture staged -- shipping with the vanilla goods icon. This is a cosmetic nicety, not a feature: the placeholder is NAMED (Archipelago Item) and suppressed either way.)"
} else {
    Info "+ AP-icon override ($($IconFiles.Count) texture file(s) in ap-package\menu)"
}

# Ship a GENERIC apconfig so a personal slot name never leaks into the release.
$ApConfig = Join-Path $Me3Dst "apconfig.json"
'{"url":"localhost:38281","slot":"Player1","seed":"","client_version":null,"password":null}' |
    Set-Content -Path $ApConfig -Encoding ASCII -NoNewline
Info "+ apconfig.json (generic template: localhost / Player1)"

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
    $Zip = Join-Path $Dist ("{0}-{1}.zip" -f $Name, $Stamp)
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
    $BareApworld = Join-Path $Dist ("{0}-{1}.apworld" -f $Name, $Stamp)
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
} else {
    Info "DONE clean -- bundle ready."
    exit 0
}
