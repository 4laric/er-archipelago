#!/usr/bin/env python3
"""Run the greenfield apworld's test suite against a PINNED, UPSTREAM Archipelago.

WHY THIS EXISTS
---------------
The tests live in `greenfield/eldenring/tests`, but they cannot run there: they need
`test.bases.WorldTestBase` and an importable `worlds.eldenring`, both of which only exist inside an
Archipelago checkout. So the suite has always been run by installing the world into an AP checkout --
and locally that checkout was `<repo>/Archipelago`, whatever it happened to be.

That is not a harness, it is a coincidence, and on 2026-07-13 it bit exactly as you would predict.
`Archipelago/` had been replaced with a clone of **fswap/Archipelago** (Bedrock's fork) in order to
play his seeds, so `run_ci.ps1` was gating the apworld against a DIFFERENT Archipelago than CI. It
collected 661 tests where CI collected 686; its `Fill.py` produced different spheres; a test that is
green on CI failed on the dev box. Neither number was wrong -- they were answers to different questions.

So the harness is a THING now, not a coincidence, and it is the SAME thing in CI and on the dev box:

  * the AP version comes from `.ap-version` -- the one pin, already read by bootstrap-ap.ps1 and CI;
  * the checkout is UPSTREAM ArchipelagoMW, and we REFUSE to run against a fork (that is the whole bug);
  * it lives in its own directory (`.ap-test/`), so your working `Archipelago/` -- fork, dirty, mid-
    playtest, whatever -- is never touched and never consulted;
  * the world is INSTALLED (copied), not symlinked. Several oracles resolve their ground-truth inputs
    relative to the package dir, and a symlink lets `..` escape into the source tree -- which is how a
    test passes locally while silently asserting nothing in CI.

Usage:
    python tools/gf_test.py                 # bootstrap .ap-test/ if needed, install, run everything
    python tools/gf_test.py -k shop         # extra args are passed through to pytest
    python tools/gf_test.py --ap-dir _ap    # CI: reuse the checkout the workflow already made
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
UPSTREAM = "https://github.com/ArchipelagoMW/Archipelago.git"

# The ground-truth inputs the derivation oracles re-derive against. They live beside the package in the
# source tree and must be copied INTO it. Without them the oracle suites (boss sweeps, shop release-gate)
# do not fail -- they quietly assert nothing, which is worse than failing. So their absence is fatal.
REQUIRED_INPUTS = ("region_map.csv", "shop_rows.tsv", "merchant_shops.tsv", "EldenRing.yaml")


def sh(*cmd, cwd=None):
    r = subprocess.run(list(cmd), cwd=cwd)
    if r.returncode != 0:
        sys.exit("gf_test: command failed (%d): %s" % (r.returncode, " ".join(cmd)))


def ap_pin():
    return (REPO / ".ap-version").read_text(encoding="utf-8").strip()


def origin_of(d):
    r = subprocess.run(["git", "-C", str(d), "remote", "get-url", "origin"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def ensure_ap(ap, pin):
    """A pinned UPSTREAM checkout at `ap`, cloning it if absent. Refuses to run against a fork."""
    if not (ap / "worlds").is_dir():
        print("gf_test: bootstrapping Archipelago %s -> %s" % (pin, ap))
        sh("git", "clone", "--depth", "1", "--branch", pin, UPSTREAM, str(ap))
        return

    origin = origin_of(ap)
    if origin and "ArchipelagoMW/Archipelago" not in origin:
        # THE 2026-07-13 BUG, made unrepresentable. A fork's Fill.py produces different spheres, so the
        # suite silently answers a different question than CI does. Fail loudly rather than hand back a
        # green (or a red) that means nothing.
        sys.exit(
            "gf_test: %s is NOT upstream Archipelago -- its origin is:\n"
            "    %s\n"
            "A fork's Fill.py gives different spheres, so this suite would gate the apworld against a\n"
            "different Archipelago than CI does, and its result would mean nothing. Point --ap-dir at an\n"
            "upstream checkout, or delete that directory and let this script bootstrap one." % (ap, origin)
        )
    sh("git", "-C", str(ap), "fetch", "--depth", "1", "origin", "tag", pin, "--no-tags")
    sh("git", "-C", str(ap), "checkout", "--force", pin)


def install_world(ap):
    dst = ap / "worlds" / "eldenring"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(REPO / "greenfield" / "eldenring", dst,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    gf = REPO / "greenfield"
    for src in sorted(gf.glob("*.csv")) + sorted(gf.glob("*.tsv")):
        shutil.copy2(src, dst / src.name)
    # THE region spine, so test_gf_play_region_buckets can assert REGION_GROUPS against the
    # tracked bucket universe (play_region_buckets.tsv rides in via the glob above).
    shutil.copy2(gf / "region_groups.py", dst / "region_groups.py")
    tpl = REPO / "release" / "EldenRing.yaml"
    if tpl.is_file():
        shutil.copy2(tpl, dst / tpl.name)
    # The SHIPPED player guide (repo root -- the one package_release.ps1 marks required, NOT
    # release/PLAYER-GUIDE.md, which is packaged by nothing). test_gf_player_guide asserts the
    # options it names are real and that the difficulty knobs are documented there; without this
    # copy that gate would silently SKIP in the installed-world run, which is the run CI does.
    guide = REPO / "Elden-Ring-Archipelago-Player-Guide.md"
    if guide.is_file():
        shutil.copy2(guide, dst / guide.name)
    # release/KNOWN-ISSUES.md, for the same reason and under its own `release/` so the test's
    # two-place resolve finds it unchanged. Without it `test_known_issues_lists_the_curated_pool_
    # as_by_design` SKIPS in the installed-world run -- and an unledgered skip fails the skip
    # census, which is how PR #621 went red with 2225 tests PASSING. A doc gate that can only skip
    # in the run CI does is the "green tick over nothing" this project already named once.
    known = REPO / "release" / "KNOWN-ISSUES.md"
    if known.is_file():
        (dst / "release").mkdir(exist_ok=True)
        shutil.copy2(known, dst / "release" / known.name)
    # The rescue guide is another shipped, player-facing contract. Install it beside KNOWN-ISSUES
    # so test_gf_player_guide exercises the same bytes package_release.ps1 sends to players.
    unstuck = REPO / "release" / "GETTING-UNSTUCK.md"
    if unstuck.is_file():
        (dst / "release").mkdir(exist_ok=True)
        shutil.copy2(unstuck, dst / "release" / unstuck.name)

    missing = [n for n in REQUIRED_INPUTS if not (dst / n).is_file()]
    if missing:
        sys.exit(
            "gf_test: ground-truth input(s) missing from the installed world: %s.\n"
            "The derivation oracles would run BLIND -- they would not fail, they would quietly assert\n"
            "nothing. Refusing to report a pass that means nothing." % ", ".join(missing)
        )
    print("gf_test: installed greenfield/eldenring -> %s" % dst)


def check_skip_census(expected_path: Path, observed_path: Path) -> int:
    """Compare the skips pytest just recorded (tests/conftest.py, one JSON line per skip) against
    the committed expected census. Returns 0 on agreement, 1 on ANY drift.

    WHY (inert-test audit finding #3, 2026-08-04): the difference between "deliberately
    dev-box-only" and "dark by accident" is invisible in a green run. The `tests` job carried ~114
    skips, several of them accidents nobody could see -- item_exists' skip message had been false
    for a week (its inputs shipped in the gen_inputs bundle on 2026-07-27), and the
    MAJOR_BOSS_EXTRAS oracle had never run in ANY job. So the skip inventory is now a committed,
    asserted artifact: every observed skip reason must match a ledgered family, and every family's
    count must be exact. A new skip family, a vanished one, or a count change all go RED -- waking
    or darkening a test is then a reviewed diff to expected_skips_ci.json, never an accident.

    The census is only meaningful for the FULL suite in the CI layout (artifacts ensured, client at
    the gitlink beside the repo); that is why it is opt-in via --skip-census rather than always-on.
    """
    import re
    exp = json.loads(expected_path.read_text(encoding="utf-8"))
    observed = []
    if observed_path.is_file():
        with observed_path.open(encoding="utf-8") as fh:
            observed = [json.loads(line) for line in fh if line.strip()]

    counts = {f["family"]: 0 for f in exp["families"]}
    unledgered = []
    for rec in observed:
        for fam in exp["families"]:
            if re.search(fam["pattern"], rec["reason"]):
                counts[fam["family"]] += 1
                break
        else:
            unledgered.append(rec)

    errors = []
    for fam in exp["families"]:
        got, want = counts[fam["family"]], fam["count"]
        if got != want:
            errors.append("family %r: expected %d skip(s), observed %d -- %s"
                          % (fam["family"], want, got,
                             "a ledgered skip has WOKEN or its reason string changed; if the wake "
                             "is real, celebrate and update expected_skips_ci.json" if got < want
                             else "something new is skipping under a known reason; find it before "
                                  "it goes dark"))
    for rec in unledgered:
        errors.append("UNLEDGERED skip (no census family matches): %s\n    reason: %s"
                      % (rec["nodeid"], rec["reason"]))

    if errors:
        print("\ngf_test: SKIP CENSUS FAILED (%d observed skips, %d ledgered families):"
              % (len(observed), len(exp["families"])))
        for e in errors:
            print("  * " + e)
        print("  The committed census is %s -- a skip-inventory change must be a reviewed diff "
              "there, not scenery in a green run." % expected_path)
        return 1
    print("gf_test: skip census OK -- %d skips, all in %d ledgered families"
          % (len(observed), len(exp["families"])))
    return 0


def main():
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument("--ap-dir", default=str(REPO / ".ap-test"),
                   help="Archipelago checkout to test in (default: .ap-test/, bootstrapped on demand)")
    p.add_argument("--quantifier-spy", action="store_true",
                   help="wrap all()/any() during the run and FAIL if any is called on an empty "
                        "iterable -- an assertion that passed without examining anything. Opt-in "
                        "for the same reason as --skip-census: a plain pytest run in any layout "
                        "must be unaffected. See tests/test_gf_vacuous_pass.py.")
    p.add_argument("--skip-census", metavar="EXPECTED_JSON", default=None,
                   help="After the run, assert the observed skip inventory matches this committed "
                        "census (CI passes greenfield/eldenring/tests/expected_skips_ci.json). Only "
                        "meaningful for a FULL-suite run in the CI layout.")
    p.add_argument("--install-only", action="store_true",
                   help="Install the world into --ap-dir and exit -- no bootstrap, no fork check, no "
                        "pytest. This makes install_world() the ONE definition of 'the installed "
                        "world', reused by gen-greenfield.ps1, ci-linux.sh and run_ci.ps1 so the "
                        "beside-package inputs (region_map.csv, *.tsv, region_groups.py, the shipping "
                        "yaml) can never drift between harnesses again. The caller owns the AP checkout.")
    args, pytest_args = p.parse_known_args()

    ap = Path(args.ap_dir).resolve()
    if args.install_only:
        # Caller-owned AP dir: just copy the world + its beside-package inputs in. No clone/pin/fork
        # check -- that is the standalone-harness concern (below), not the shared install step.
        install_world(ap)
        return 0
    pin = ap_pin()
    ensure_ap(ap, pin)
    install_world(ap)

    print("gf_test: pytest worlds/eldenring/tests  (Archipelago %s, %s)" % (pin, ap))
    env = dict(os.environ)
    env["AP_NONINTERACTIVE"] = "1"
    if args.quantifier_spy:
        env["GF_QUANTIFIER_SPY"] = "1"
    census_out = None
    if args.skip_census:
        census_out = ap / "_gf_skip_census.jsonl"
        if census_out.exists():
            census_out.unlink()
        env["GF_SKIP_CENSUS_OUT"] = str(census_out)
    r = subprocess.run([sys.executable, "-m", "pytest", "worlds/eldenring/tests", "-q", *pytest_args],
                       cwd=str(ap), env=env)
    if args.skip_census:
        census_rc = check_skip_census(Path(args.skip_census).resolve(), census_out)
        if r.returncode == 0:
            return census_rc
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
