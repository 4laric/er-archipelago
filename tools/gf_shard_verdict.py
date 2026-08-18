#!/usr/bin/env python3
"""Render the run-level verdicts that a SHARDED test run cannot render for itself (#865).

WHY THIS EXISTS
---------------
The `tests` job was 1113s, of which 1069s was one pytest step -- already spread over both cores of
the hosted runner by `-n 2 --dist loadfile`, so the only lever left without new hardware is running
it as several jobs. Splitting it is easy. Splitting it WITHOUT disarming the two instruments this
suite added on purpose is the whole problem, because both of them are statements about a run, and a
shard is not a run:

  * **the skip census** counts skips per ledgered family and demands an EXACT match. Any single
    shard sees a fraction of them, so every shard fails, and the natural way to make CI green again
    is to stop passing `--skip-census` to the shards -- at which point the census still exists,
    still looks armed, and gates nothing. That is precisely the "dark by accident" state the census
    was built to expose.

  * **the vacuous-quantifier spy** has a second half that is worse, because it fails in the
    direction of a FALSE RED. `stale` fires for a waived site that ran and was never empty. Split
    the suite and a site that is genuinely empty in shard 3 is merely non-empty in shard 1, so
    shard 1 calls a correct waiver stale. The conftest already refuses to judge staleness for
    sites a run did not reach; a shard reaches them and still cannot judge, which is a different
    hole in the same floor.

So both verdicts are deferred by `gf_test.py --artifact-dir` and reassembled here over the UNION.

It also answers the question a green sharded run cannot answer on its own -- **did every test
actually run?** A shard that silently loses a module looks exactly like a fast shard. Every shard
collects the whole suite before deselecting, so each independently records the full population;
this asserts they agree on it and that the selections sum to it.

Usage:
    tools/gf_shard_verdict.py --artifacts <dir-of-shard-dirs> \\
        --expected-skips greenfield/eldenring/tests/expected_skips_ci.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TESTS = REPO / "greenfield" / "eldenring" / "tests"


def _load(path: Path, name: str):
    """Import a module by path -- the same idiom test_gf_vacuous_pass.py uses on conftest.

    Deliberately NOT a reimplementation: `_qspy_verdict` and `check_skip_census` are the live
    definitions, unit-tested where they live. A second copy here would be two rules that agree
    until the day they don't, and the day they don't is the day this gate lies.
    """
    spec = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def reconcile(manifests):
    """(errors, collected, selected_total) -- pure, so its red cases are unit-testable."""
    errors = []
    if not manifests:
        return (["no shard manifests found -- the shards either did not run or did not upload"],
                0, 0)

    totals = {m["total_shards"] for m in manifests}
    if len(totals) != 1:
        errors.append("shards disagree on total_shards: %s" % sorted(totals))
    total = manifests[0]["total_shards"]

    seen_idx = sorted(m["shard"] for m in manifests)
    if seen_idx != list(range(1, total + 1)):
        errors.append("expected shards %s, got %s -- a missing shard is a silently unrun slice "
                      "of the suite" % (list(range(1, total + 1)), seen_idx))

    collected = {m["collected"] for m in manifests}
    if len(collected) != 1:
        errors.append("shards disagree on the COLLECTED population: %s. They each collect the "
                      "whole suite before deselecting, so a disagreement means they were not "
                      "looking at the same tree." % sorted(collected))
    n_collected = manifests[0]["collected"]

    n_selected = sum(m["selected"] for m in manifests)
    if n_selected != n_collected:
        errors.append("shards ran %d of %d collected tests -- %d test(s) were selected by NO shard. "
                      "A lost module is indistinguishable from a fast shard in a green run."
                      % (n_selected, n_collected, n_collected - n_selected))

    owners = {}
    for m in manifests:
        for f in m.get("files", []):
            owners.setdefault(f, []).append(m["shard"])
    for f, who in sorted(owners.items()):
        if len(who) > 1:
            errors.append("file %s ran in MORE than one shard %s -- the partition is not a "
                          "partition, and its duplicated skips will inflate the census" % (f, who))
    return errors, n_collected, n_selected


def _self_test():
    """Prove RECONCILE CAN GO RED, in the four ways sharding can actually break (the repo already
    runs a `--self-test` on the multiworld smoke for this reason). A reconciliation that cannot
    fail is a green tick over an unchecked claim -- and this one guards the question a sharded
    green run cannot otherwise answer at all: did every test run?"""
    ok = lambda n, m: {"shard": n, "total_shards": m, "collected": 100,
                       "selected": 50, "files": ["f%d.py" % n]}
    cases = [
        ("a missing shard", [ok(1, 2)]),
        ("tests selected by no shard",
         [dict(ok(1, 2), selected=10), dict(ok(2, 2), selected=10)]),
        ("shards that collected different populations",
         [ok(1, 2), dict(ok(2, 2), collected=99)]),
        ("a file claimed by two shards",
         [dict(ok(1, 2), files=["dup.py"]), dict(ok(2, 2), files=["dup.py"])]),
        ("no manifests at all", []),
    ]
    bad = []
    for name, manifests in cases:
        errors, _, _ = reconcile(manifests)
        if not errors:
            bad.append(name)
    if bad:
        print("gf_shard_verdict --self-test FAILED -- these red cases did not go red:")
        for b in bad:
            print("  * " + b)
        return 1
    errors, _, _ = reconcile([ok(1, 2), dict(ok(2, 2), files=["f2.py"])])
    if errors:
        print("gf_shard_verdict --self-test FAILED -- a HEALTHY pair of shards was rejected:")
        for e in errors:
            print("  * " + e)
        return 1
    print("gf_shard_verdict: self-test OK -- %d red case(s) fire, the healthy case does not"
          % len(cases))
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--self-test", action="store_true",
                   help="prove the reconciliation can go red, then exit without reading artifacts")
    p.add_argument("--artifacts",
                   help="directory holding one subdirectory per shard (as downloaded by "
                        "actions/download-artifact)")
    p.add_argument("--expected-skips", default=str(TESTS / "expected_skips_ci.json"))
    args = p.parse_args()
    if args.self_test:
        return _self_test()
    if not args.artifacts:
        p.error("--artifacts is required (or use --self-test)")

    root = Path(args.artifacts).resolve()
    manifests, censuses, spies = [], [], []
    for d in sorted(root.iterdir()) if root.is_dir() else []:
        if (d / "manifest.json").is_file():
            manifests.append(json.loads((d / "manifest.json").read_text(encoding="utf-8")))
        if (d / "census.jsonl").is_file():
            censuses.append(d / "census.jsonl")
        if (d / "spy.json").is_file():
            spies.append(json.loads((d / "spy.json").read_text(encoding="utf-8")))

    rc = 0

    # ---------------------------------------------------------------- 1. did everything run?
    errors, n_collected, n_selected = reconcile(manifests)
    if errors:
        print("gf_shard_verdict: SHARD RECONCILIATION FAILED:")
        for e in errors:
            print("  * " + e)
        rc = 1
    else:
        print("gf_shard_verdict: shards OK -- %d shard(s), %d/%d collected tests selected exactly "
              "once" % (len(manifests), n_selected, n_collected))

    # ---------------------------------------------------------------- 2. the skip census, unioned
    gf_test = _load(REPO / "tools" / "gf_test.py", "gf_test_for_verdict")
    merged = root / "_census_union.jsonl"
    with merged.open("w", encoding="utf-8") as out:
        for c in censuses:
            out.write(c.read_text(encoding="utf-8"))
    if gf_test.check_skip_census(Path(args.expected_skips).resolve(), merged) != 0:
        rc = 1

    # ---------------------------------------------------------------- 3. the spy, unioned
    if spies:
        conftest = _load(TESTS / "conftest.py", "gf_conftest_for_verdict")
        empty, seen = set(), set()
        for s in spies:
            empty |= set(s.get("empty", []))
            seen |= set(s.get("seen", []))
        try:
            waived = json.loads((TESTS / "expected_vacuous_quantifiers.json").read_text(
                encoding="utf-8"))
        except OSError:
            waived = {}
        unwaived, stale = conftest._qspy_verdict(empty, seen, waived)
        if unwaived:
            print("\nVACUOUS QUANTIFIER(S) -- all()/any() over an EMPTY iterable, i.e. an assertion "
                  "that passed without examining anything. Fix it, or waive it in "
                  "expected_vacuous_quantifiers.json WITH A REASON:")
            for s_ in unwaived:
                print("   " + s_)
        if stale:
            print("\nSTALE VACUOUS-QUANTIFIER WAIVER(S) -- these ran and were never empty across "
                  "ANY shard, so the waiver is protecting nothing. Delete them:")
            for s_ in stale:
                print("   %s  (%s)" % (s_, waived[s_]))
        if unwaived or stale:
            rc = 1
        else:
            print("gf_shard_verdict: quantifier spy OK -- %d site(s) reached, %d empty, all waived"
                  % (len(seen), len(empty)))
    else:
        # A spy that produced no artifact is a spy that did not run. Saying nothing here would let
        # the whole guard disappear from CI without a single red tick.
        print("gf_shard_verdict: NO spy artifacts -- the quantifier spy did not run in any shard")
        rc = 1

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
