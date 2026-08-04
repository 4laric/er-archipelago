"""Skip-census recorder (2026-08-04, inert-test audit finding #3).

A green run cannot distinguish "deliberately dev-box-only" from "dark by accident": the CI `tests`
job sat at ~114 skips for weeks while several of them were accidents (test_gf_item_exists' skip
message claimed the GitHub runner could not run it -- false since the 2026-07-27 gen_inputs bundle;
the MAJOR_BOSS_EXTRAS oracle had never run in ANY job because of a positional path). The census
makes the skip INVENTORY an asserted artifact instead of scenery.

Mechanism: when GF_SKIP_CENSUS_OUT is set (tools/gf_test.py --skip-census sets it), every skipped
test appends one JSON line {nodeid, when, reason} to that file. gf_test.py then classifies the
reasons against the committed expected census (tests/expected_skips_ci.json) and fails the run on
any unrecognised skip reason or any count change. Without the env var this hook is inert, so plain
pytest runs, run_ci.ps1 and dev-box layouts (whose skip sets legitimately differ) are untouched.

Kept dependency-free on purpose: it must load in every layout the suite runs in (installed world,
repo tree, dev box) without adding an import the harness would then have to ship.
"""
import json
import os


def pytest_runtest_logreport(report):
    out = os.environ.get("GF_SKIP_CENSUS_OUT")
    if not out or not report.skipped:
        return
    if hasattr(report, "wasxfail"):        # xfail is a different ledger, not a skip
        return
    if getattr(report, "context", None):   # pytest-subtests sub-reports shadow their parent nodeid
        return
    if isinstance(report.longrepr, tuple):
        reason = report.longrepr[2]
    else:
        reason = str(report.longrepr)
    if reason.startswith("Skipped: "):
        reason = reason[len("Skipped: "):]
    with open(out, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"nodeid": report.nodeid, "when": report.when,
                             "reason": reason}) + "\n")
