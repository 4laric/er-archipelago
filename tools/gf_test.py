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
REQUIRED_INPUTS = ("region_map.csv", "shop_rows.tsv", "EldenRing.yaml")


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
    tpl = REPO / "release-v0.2" / "EldenRing.yaml"
    if tpl.is_file():
        shutil.copy2(tpl, dst / tpl.name)

    missing = [n for n in REQUIRED_INPUTS if not (dst / n).is_file()]
    if missing:
        sys.exit(
            "gf_test: ground-truth input(s) missing from the installed world: %s.\n"
            "The derivation oracles would run BLIND -- they would not fail, they would quietly assert\n"
            "nothing. Refusing to report a pass that means nothing." % ", ".join(missing)
        )
    print("gf_test: installed greenfield/eldenring -> %s" % dst)


def main():
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument("--ap-dir", default=str(REPO / ".ap-test"),
                   help="Archipelago checkout to test in (default: .ap-test/, bootstrapped on demand)")
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
    r = subprocess.run([sys.executable, "-m", "pytest", "worlds/eldenring/tests", "-q", *pytest_args],
                       cwd=str(ap), env=env)
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
