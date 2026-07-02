# check_options_metadata.ps1 -- CI drift gate for the yaml options wizard.
#
# Verifies that wizard/options-metadata.json AND the JSON inlined in
# wizard/wizard.html match a fresh ast-dump of worlds/eldenring/options.py,
# so the wizard can never describe an option surface that no longer exists.
# Read-only; exit 0 = current, exit 1 = stale (fix command is printed).
#
# Suggested run_ci.ps1 hook (owned by the CI track; add there, not here):
#   Invoke-CiStep "WIZARD (options metadata drift)" { .\tools\check_options_metadata.ps1 }
#
# Usage: .\tools\check_options_metadata.ps1
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
& python (Join-Path $root "tools\dump_options_metadata.py") --check
exit $LASTEXITCODE
