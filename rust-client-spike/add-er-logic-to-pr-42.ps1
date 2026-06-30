# Add the er-logic test crate + a `cargo test` CI step to the ER client draft (PR #42).
# Lands on the eldenring-client-draft branch because er-logic depends on er-codec/er-semver,
# which live on that branch (not fswap main).
# Run in PowerShell. Requires: gh/git, cargo (for the local preflight).
$ErrorActionPreference = "Stop"
function Run($cmd) { & $cmd[0] @($cmd[1..($cmd.Count-1)]); if ($LASTEXITCODE -ne 0) { throw "FAILED: $($cmd -join ' ')" } }

$SPIKE  = "C:\Users\alari\Documents\er-archipelago\rust-client-spike\crates\er-logic"
$CLIENT = "C:\Users\alari\Documents\from-software-archipelago-clients"

Set-Location $CLIENT
Run @('git','checkout','eldenring-client-draft')

# 1. Vendor the verified crate into the workspace
Copy-Item $SPIKE "$CLIENT\crates\er-logic" -Recurse -Force
Remove-Item "$CLIENT\crates\er-logic\target" -Recurse -Force -ErrorAction SilentlyContinue

# 2. Register it as a workspace member (after er-semver)
$wf = "$CLIENT\Cargo.toml"
(Get-Content -Raw $wf) -replace '"crates/er-semver",', "`"crates/er-semver`",`r`n    `"crates/er-logic`"," |
    Set-Content -NoNewline $wf

# 3. Add a `cargo test` step to CI (right after the existing `cargo build`)
$tf = "$CLIENT\.github\workflows\test.yaml"
(Get-Content -Raw $tf) -replace '(- run: cargo build)', "`$1`r`n    - run: cargo test -p er-codec -p er-semver -p er-logic" |
    Set-Content -NoNewline $tf

# 4. Local preflight to fswap's bar BEFORE pushing (fswap CI is fmt + clippy -D warnings + build).
#    er-logic was authored without a compiler here, so shake out fmt/clippy nits now.
Run @('cargo','fmt','-p','er-logic')
Run @('cargo','clippy','-p','er-logic','--','-D','warnings')   # if this errors, paste it and stop
Run @('cargo','test','-p','er-logic')                          # expect 56 passed

# 5. Commit + push -> updates draft PR #42 and re-runs its CI (now including the test step)
Run @('git','add','crates/er-logic','Cargo.toml','.github/workflows/test.yaml')
Run @('git','commit','-m','Add er-logic host-tested crate (56 tests) + cargo test CI step')
Run @('git','push')

Write-Host "`nPushed. PR #42 CI will now run fmt/clippy/build + the er-logic test suite."