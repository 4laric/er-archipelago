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
import sys


def pytest_runtest_logreport(report):
    out = os.environ.get("GF_SKIP_CENSUS_OUT")
    if not out or not report.skipped:
        return
    # pytest-xdist sends every worker report back through this hook on the controller. Recording
    # in BOTH processes doubles the census while pytest itself still (correctly) reports one skip.
    # The controller has the complete stream and no PYTEST_XDIST_WORKER marker, so it is the sole
    # writer under xdist. A normal one-process run has no marker either and remains unchanged.
    if os.environ.get("PYTEST_XDIST_WORKER"):
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


# ---------------------------------------------------------------------------------------------
# QUANTIFIER-EMPTINESS SPY (2026-08-05, inert-test audit finding: the one buildable guard from the
# 2026-08-04 list that had not been built).
#
# `all(...)` over an empty iterable is True. `any(...)` over an empty one is False. Both are the
# answer the test wanted, so a quantifier whose subject set has silently become empty passes for
# exactly the same reason it would pass if the mechanism worked. The audit measured 38 such sites in
# this suite and found zero empty AT THAT MOMENT -- which is the point: they are fine until the day
# a table is renamed, a filter stops matching or a feature is deleted, and on that day nothing goes
# red.
#
# The spy pulls ONE element to decide emptiness and chains it back, so laziness and short-circuiting
# are preserved exactly -- `all`/`any` would have pulled that element anyway. Only calls made from
# this suite's own files are recorded; library internals are none of our business.
#
# Off unless GF_QUANTIFIER_SPY=1 (tools/gf_test.py --quantifier-spy and the CI `tests` job set it),
# for the same reason the skip census is opt-in: a plain `pytest` run in any layout must be
# unaffected.
import builtins
import itertools

_QSPY_HITS = []                          # sites called on an EMPTY iterable
_QSPY_SEEN = []                          # every site called at all -- needed to catch a STALE waiver
_QSPY_WAIVERS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "expected_vacuous_quantifiers.json")
_QSPY_DIR = os.path.dirname(os.path.abspath(__file__))


def _qspy_note(bucket, name):
    """Record the CALLER as `file::function name()`.

    Keyed on the function, not the line: a line number drifts the moment anything above it is
    edited, and a waiver keyed on a drifting id silently stops matching -- which is the exact
    failure this whole file exists to catch."""
    f = sys._getframe(2)
    if os.path.dirname(os.path.abspath(f.f_code.co_filename)) != _QSPY_DIR:
        return
    bucket.append("%s::%s %s()" % (os.path.basename(f.f_code.co_filename),
                                   f.f_code.co_name, name))


def _qspy_wrap(fn, name):
    # 🛑 NEVER DOUBLE-WRAP. Found by the spy on itself, in CI: `test_gf_vacuous_pass`'s red case
    # wraps the GLOBAL `all`, which by then is already this wrapper -- so the inner one saw the outer
    # one's `fn(())` and reported `conftest.py::wrapper all()`. A diagnostic that reports its own
    # plumbing trains people to ignore it. Also makes a second pytest_configure a no-op.
    if getattr(fn, "_qspy", False):
        return fn

    def wrapper(*args):
        if len(args) != 1:
            return fn(*args)
        it = iter(args[0])
        try:
            first = next(it)
        except StopIteration:
            _qspy_note(_QSPY_HITS, name)
            return fn(())
        _qspy_note(_QSPY_SEEN, name)
        return fn(itertools.chain((first,), it))
    wrapper.__name__ = name
    wrapper._qspy = True
    return wrapper


def pytest_configure(config):
    if os.environ.get("GF_QUANTIFIER_SPY") != "1":
        return
    builtins.all = _qspy_wrap(builtins.all, "all")
    builtins.any = _qspy_wrap(builtins.any, "any")


def _qspy_verdict(empty, seen, waived):
    """(unwaived, stale) -- the whole decision, pure, so both directions are unit-testable.

    `stale` is judged ONLY over sites this run actually reached: a partial run must never report a
    waiver as stale merely because its file did not execute."""
    return (sorted(set(empty) - set(waived)),
            sorted(k for k in waived if k not in set(empty) and k in set(seen)))


def pytest_sessionfinish(session, exitstatus):
    """Two directions, because a waiver list is a claim and claims rot.

    * a site that came up EMPTY and is not waived -> fail. It is an assertion that examined nothing.
    * a site that IS waived but was called with a NON-empty iterable every time it ran -> fail as
      STALE. "An exclusion that matches nothing is a lie": the waiver reads like protection while the
      thing it protects has moved on. Only judged for sites this run actually reached, so a partial
      run never reports a waiver as stale just because its file did not execute.
    """
    if os.environ.get("GF_QUANTIFIER_SPY") != "1":
        return
    empty, seen = set(_QSPY_HITS), set(_QSPY_SEEN)
    waived = {}
    try:
        with open(_QSPY_WAIVERS, encoding="utf-8") as fh:
            waived = json.load(fh)
    except OSError:
        pass
    out = os.environ.get("GF_QUANTIFIER_SPY_OUT")
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write("\n".join(sorted(empty)) + "\n")
    unwaived, stale = _qspy_verdict(empty, seen, waived)
    if unwaived:
        print("\nVACUOUS QUANTIFIER(S) -- all()/any() over an EMPTY iterable, i.e. an assertion "
              "that passed without examining anything. Fix it, or waive it in "
              "expected_vacuous_quantifiers.json WITH A REASON:")
        for s in unwaived:
            print("   " + s)
    if stale:
        print("\nSTALE VACUOUS-QUANTIFIER WAIVER(S) -- these ran and were never empty, so the "
              "waiver is protecting nothing. Delete them:")
        for s in stale:
            print("   %s  (%s)" % (s, waived[s]))
    if unwaived or stale:
        session.exitstatus = session.exitstatus or 1
