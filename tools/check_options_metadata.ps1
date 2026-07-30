# check_options_metadata.ps1 -- CI drift gate for the yaml options wizard.
#
# Verifies that wizard/options-metadata.json, the JSON inlined in wizard/wizard.html, and
# presets/*.yaml all match a fresh dump of the LIVE GFOptions dataclass -- imported out of a
# pinned upstream Archipelago checkout, NOT ast-parsed. (This header used to claim an ast-dump of
# worlds/eldenring/options.py; that file no longer exists. Rule 10: claims rot.)
#
# Needs Python >= 3.11, because upstream AP 0.6.7 imports typing.Self. That is why this cannot run
# in the Linux sandbox (3.10) -- see test_gf_wizard_blob_sync.py for the AP-free half.
#
# Read-only; exit 0 = current, exit 1 = stale (fix command is printed).
#
# Wired into run_ci.ps1 as the WIZARD step. It was commented out there 2026-07-04 and that window
# ate a four-commit drift; do not disable it again without a replacement instrument.
#
# Usage: .\tools\check_options_metadata.ps1
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
& python (Join-Path $root "tools\dump_options_metadata.py") --check
exit $LASTEXITCODE
