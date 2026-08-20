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


_GF_FILE_SECONDS = {}


def pytest_runtest_logreport(report):
    # PER-FILE DURATIONS, first, because everything below this returns early.
    #
    # A committed weights file is a claim about how long things take, and claims rot. This one rots
    # SILENTLY and specifically: stale weights do not break a run, they stop balancing it, and CI
    # gets slower while every gate stays green. So a sharded run measures what it actually ran and
    # ships the numbers beside its manifest for tools/gf_shard_verdict.py to check the split it got
    # against the split it assumed.
    #
    # Controller-only, for the same reason the census below is: under xdist every worker report also
    # passes through the controller, and counting both would double every duration.
    if not os.environ.get("PYTEST_XDIST_WORKER") and not getattr(report, "context", None):
        _f = report.nodeid.split("::")[0]
        _GF_FILE_SECONDS[_f] = _GF_FILE_SECONDS.get(_f, 0.0) + getattr(report, "duration", 0.0)

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
    # The durations ride out here, BEFORE the spy's own early return -- they are recorded whenever
    # a shard manifest was asked for, whether or not the spy is armed.
    _out = os.environ.get("GF_SHARD_MANIFEST_OUT")
    if _out and _GF_FILE_SECONDS:
        with open(os.path.join(os.path.dirname(os.path.abspath(_out)), "durations.json"),
                  "w", encoding="utf-8") as _fh:
            json.dump({"files": {k: round(v, 3) for k, v in sorted(_GF_FILE_SECONDS.items())}},
                      _fh, indent=1)

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
        # BOTH sets, because the STALE half of the verdict is a claim about what this run REACHED,
        # and a reader that only gets `empty` cannot evaluate it. Until 2026-08-18 this file was
        # written by nobody's request and read by nobody at all; the shard aggregator
        # (tools/gf_shard_verdict.py) is its first consumer, so the format is free to say what a
        # consumer actually needs.
        with open(out, "w", encoding="utf-8") as fh:
            json.dump({"empty": sorted(empty), "seen": sorted(seen)}, fh)
    if os.environ.get("GF_QUANTIFIER_SPY_DEFER") == "1":
        # 🛑 THE SHARDING TRAP. `stale` fires for a waived site that RAN and was never empty. Split
        # the suite across shards and the site that is empty in shard 3 is merely non-empty in
        # shard 1 -- so shard 1 calls a correct waiver stale and goes red, and the redness is an
        # artifact of the split, not a fact about the code. The verdict is only sound over the
        # UNION of shards, so a deferring run records and says nothing; tools/gf_shard_verdict.py
        # reassembles the union and renders it once. `unwaived` is deferred with it rather than
        # kept here: two half-verdicts in two places is how a gate ends up fired by neither.
        return
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


# ---------------------------------------------------------------------------------------------
# FILE-LEVEL SHARDING (2026-08-18, #865).
#
# The `tests` job was one 18-minute pytest step: 1069s of a 1113s job, already spread over both
# cores of the hosted runner by `-n 2 --dist loadfile`. Splitting it across several jobs is the
# only lever that does not need new hardware.
#
# The partition is by FILE, not by test, for the same reason `--dist loadfile` is: a module's tests
# may carry collection/order assumptions, and a split that can land two of them in different
# processes would be trading a slow suite for a flaky one.
#
# It is DERIVED, never listed. A shard is `index/total` over the sorted collected files, so a test
# file added tomorrow lands in a shard by arithmetic. A hand-maintained shard manifest is a gate
# that quietly stops covering new tests while stalling green -- the same failure this suite already
# names for lint rules whose options vanished and waivers that match nothing.
# ---------------------------------------------------------------------------------------------

def _gf_parse_shard(spec):
    """'2/4' -> (2, 4), validated. Raises ValueError with a usable message."""
    try:
        idx_s, total_s = spec.split("/", 1)
        idx, total = int(idx_s), int(total_s)
    except Exception:
        raise ValueError("GF_SHARD must look like '2/4' (1-based index / total), got %r" % (spec,))
    if total < 1 or not (1 <= idx <= total):
        raise ValueError("GF_SHARD %r is out of range: need 1 <= index <= total and total >= 1"
                         % (spec,))
    return idx, total


GF_SHARD_WEIGHTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shard_weights.json")


def gf_load_weights(path=GF_SHARD_WEIGHTS):
    """{file: seconds} from the committed measurement, or {} if there is none.

    Absence is a supported state, not an error: the first sharded run has no weights and must still
    partition correctly. That is the bootstrap -- it runs round-robin, emits the durations it
    measured, and the next commit of shard_weights.json is balanced.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            return {k: float(v) for k, v in json.load(fh)["files"].items()}
    except (OSError, KeyError, ValueError, TypeError):
        return {}


def gf_shard_owner(files, total, weights=None):
    """file -> shard index (1-based). Pure, so it is testable without pytest:
    see tests/test_gf_shard_partition.py.

    WITH weights: longest-processing-time-first. Sort by cost descending and hand each file to
    whichever shard is currently lightest. LPT is provably within 4/3 of optimal, which is far more
    than this suite needs -- its cost is a handful of generation-heavy modules and the rest is dust.

    WITHOUT weights: round-robin over the sorted list. Kept as the fallback rather than deleted,
    because a first run, a renamed file or a deleted weights file must still produce a CORRECT
    partition -- just a slower one.

    🛑 WHY NOT ROUND-ROBIN ALWAYS: it balances FILES, and a file is not the unit of cost. Measured
    on the first sharded CI run (#866), a 4-way round-robin gave shard 4 550s and shard 2 197s --
    it had put five of the expensive modules in one place. The slowest shard IS the wall time, so
    that 2.8x spread was the entire loss.

    Ties break on the filename so the split is deterministic. The same tree must always produce the
    same partition, or "which shard is this test in" stops being answerable and a flaky shard
    becomes impossible to reproduce.
    """
    files = sorted(files)
    if not weights:
        return {f: (i % total) + 1 for i, f in enumerate(files)}

    # An unknown file gets the MEDIAN of what we know, not zero. Zero would pile every newly added
    # test file onto whichever shard is lightest at the end -- and a new file is exactly the case
    # where nobody is looking.
    known = sorted(weights.values())
    default = known[len(known) // 2] if known else 1.0

    load = [[0.0, i + 1] for i in range(total)]        # [cost so far, shard index]
    owner = {}
    for f in sorted(files, key=lambda n: (-weights.get(n, default), n)):
        load.sort(key=lambda x: (x[0], x[1]))
        load[0][0] += weights.get(f, default)
        owner[f] = load[0][1]
    return owner


def pytest_collection_modifyitems(config, items):
    spec = os.environ.get("GF_SHARD")
    if not spec:
        return
    idx, total = _gf_parse_shard(spec)
    owner = gf_shard_owner({item.nodeid.split("::")[0] for item in items}, total,
                           gf_load_weights())

    keep, drop = [], []
    for item in items:
        (keep if owner[item.nodeid.split("::")[0]] == idx else drop).append(item)

    # THE ARITHMETIC THIS SHARD SAW, recorded before anything runs. Every shard collects the WHOLE
    # suite and then deselects, so each one independently knows the full population -- which makes
    # "did sharding drop a test?" answerable by comparison rather than by trust. A shard that
    # silently loses a module is indistinguishable from a fast shard in a green run; this is the
    # instrument that tells them apart, and tools/gf_shard_verdict.py asserts
    # sum(selected) == collected, on one agreed collected.
    out = os.environ.get("GF_SHARD_MANIFEST_OUT")
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            json.dump({"shard": idx, "total_shards": total,
                       "collected": len(items), "selected": len(keep),
                       "files": sorted({i.nodeid.split("::")[0] for i in keep})}, fh)

    if drop:
        config.hook.pytest_deselected(items=drop)
    items[:] = keep
