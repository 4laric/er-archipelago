#!/usr/bin/env python3
"""
check_version_sites.py -- the version-lockstep gate, all sites at once.

The release version lives at FOUR sites across two repos. They must be one number: a
seed reports `archipelago.json`'s, the client announces `Cargo.toml`'s, and a bug
report carries whichever one happens to be printed. v0.2.14 shipped stamped 0.2.13
because one site went unchecked.

MOTIVATING CASE (CONTRIBUTING rule 11), 2026-08-03: cutting v0.3.3, `package_release.ps1`
reported ONE stale site and threw. Every other site was stale too -- nothing had been
bumped -- so the same cut would have failed four times, once per round trip, each error
naming a single file and saying "Bump it". That is the `inputs_hash` ripple shape: a gate
that reports the FIRST problem teaches you the wrong size of the job.

So this tool never stops at the first. It reads every site it can reach, prints all of
them, and names ALL the stale ones in one error.

Deliberately AP-free and import-free -- textual reads only -- so it runs in the cheap CI
job, in the Linux sandbox, and on a box with no Archipelago checkout. Same constraint as
check_release_notes.py and check_contract_version.py, for the same reason.

Usage:
    python3 tools/check_version_sites.py                # all sites must AGREE
    python3 tools/check_version_sites.py --expect 0.3.3 # ...and equal this
    python3 tools/check_version_sites.py --check        # no-op alias (house convention)

Exit 0 = clean, 1 = >=1 ERROR, 2 = bad invocation / a site could not be read.
"""
import argparse
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT = os.path.join(REPO, "from-software-archipelago-clients")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")

# 🛑 THE LIST. `package_release.ps1` carries the same one; when that script becomes Python
# this becomes the single copy. Adding a site here is what "adding a version site" means --
# there is no second place to remember.
#
# `optional` = legitimately absent in a world-only checkout (the client is a submodule).
# Absence is reported LOUDLY and never silently skipped: an unchecked site is exactly how
# v0.2.14 shipped mis-stamped.
SITES = [
    {
        "what": "archipelago.json world_version",
        "path": os.path.join(REPO, "greenfield", "eldenring", "archipelago.json"),
        "kind": "json",
        "key": "world_version",
    },
    {
        "what": "contract.py APWORLD_VERSION",
        "path": os.path.join(REPO, "greenfield", "eldenring", "contract.py"),
        "kind": "regex",
        "rx": re.compile(r'^APWORLD_VERSION\s*=\s*"(\d+(?:\.\d+)+)"', re.M),
    },
    {
        "what": "client Cargo.toml version",
        "path": os.path.join(CLIENT, "crates", "eldenring-archipelago", "Cargo.toml"),
        "kind": "regex",
        # The FIRST `version =` under [package]. Anchored to line start so a dependency's
        # `version = "1.2"` three lines down cannot be mistaken for the crate's own.
        "rx": re.compile(r'^version\s*=\s*"(\d+(?:\.\d+)+)"', re.M),
        "optional": True,
    },
    {
        "what": "client Cargo.lock eldenring-archipelago",
        "path": os.path.join(CLIENT, "Cargo.lock"),
        "kind": "regex",
        # The lock is TRACKED, so a bumped Cargo.toml with an unbumped lock is a dirty tree
        # on someone else's machine. cargo rewrites it on the next build, which is precisely
        # why it gets forgotten. package_release.ps1 does not check this site at all.
        "rx": re.compile(
            r'^name = "eldenring-archipelago"\s*\nversion = "(\d+(?:\.\d+)+)"', re.M
        ),
        "optional": True,
    },
]


def read_site(site):
    """(version, note) -- version is None when the site is absent or unreadable."""
    path = site["path"]
    if not os.path.isfile(path):
        return None, "absent"
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if site["kind"] == "json":
        try:
            value = json.loads(text).get(site["key"])
        except json.JSONDecodeError as exc:
            return None, "unparseable JSON: %s" % exc
        if value is None:
            return None, "no %r key" % site["key"]
        return str(value), None
    m = site["rx"].search(text)
    if not m:
        # Rule 4: a filter with no tally is a lie, and a regex that stops matching is a
        # site that stopped being checked without anyone being told.
        return None, "pattern no longer matches -- the site is UNCHECKED, not clean"
    return m.group(1), None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--expect", metavar="X.Y.Z",
                    help="require every site to read this exact version")
    ap.add_argument("--check", action="store_true",
                    help="no-op alias; the house convention for repo-level gates")
    args = ap.parse_args(argv)

    if args.expect and not SEMVER.match(args.expect):
        print("check_version_sites: --expect %r is not X.Y.Z" % args.expect, file=sys.stderr)
        return 2

    errors, skipped, found = [], [], {}
    for site in SITES:
        version, note = read_site(site)
        if version is None:
            if note == "absent" and site.get("optional"):
                # LOUD skip. A silent one is the same unchecked site by another route.
                skipped.append(site["what"])
                print("  SKIP %s -- not checked out at %s"
                      % (site["what"], os.path.relpath(site["path"], REPO)))
                continue
            errors.append("%s: %s (%s)"
                          % (site["what"], note, os.path.relpath(site["path"], REPO)))
            continue
        found[site["what"]] = version
        print("  %-42s %s" % (site["what"], version))

    if errors:
        for e in errors:
            print("ERROR check_version_sites: " + e, file=sys.stderr)
        return 1

    if not found:
        # Rule 2: an empty result is a FAILURE, not a clean run.
        print("ERROR check_version_sites: no version site was readable at all -- this gate "
              "checked NOTHING and must not report success.", file=sys.stderr)
        return 1

    distinct = sorted(set(found.values()))
    target = args.expect or (distinct[0] if len(distinct) == 1 else None)

    if len(distinct) > 1 or (args.expect and distinct != [args.expect]):
        print("", file=sys.stderr)
        print("ERROR check_version_sites: the version sites disagree.", file=sys.stderr)
        if target:
            # A target is known, so "stale" is a fact about each site and can be marked.
            stale = {w: v for w, v in found.items() if v != target}
            print("  expected v%s (--expect)" % args.expect, file=sys.stderr)
            for what, version in sorted(found.items()):
                mark = "  STALE ->" if what in stale else "        ok"
                print("  %s %-42s v%s" % (mark, what, version), file=sys.stderr)
            print("", file=sys.stderr)
            print("  ALL %d stale site(s) are listed above -- bump them together, in one "
                  "commit." % len(stale), file=sys.stderr)
        else:
            # No --expect and the sites disagree, so WHICH ONE IS RIGHT IS NOT KNOWABLE HERE.
            # Marking them all STALE would be a confident wrong answer about three correct
            # files; picking a majority would invent an authority this tool does not have.
            # Say what is true -- they differ -- and hand the decision back.
            for what, version in sorted(found.items()):
                print("  %-42s v%s" % (what, version), file=sys.stderr)
            print("", file=sys.stderr)
            print("  %d distinct versions across %d site(s): %s"
                  % (len(distinct), len(found), ", ".join("v" + d for d in distinct)),
                  file=sys.stderr)
            print("  This tool cannot tell which is intended -- re-run with --expect X.Y.Z "
                  "to be told\n  exactly which sites to bump.", file=sys.stderr)
        print("  A seed reports archipelago.json's number and the client announces "
              "Cargo.toml's;\n  two builds that disagree introduce themselves to a bug report "
              "identically.", file=sys.stderr)
        if skipped:
            print("  ⚠️  %d site(s) were SKIPPED and are NOT covered by this verdict: %s"
                  % (len(skipped), ", ".join(skipped)), file=sys.stderr)
        return 1

    print("OK check_version_sites: %d site(s) agree at v%s%s"
          % (len(found), distinct[0],
             (", %d skipped" % len(skipped)) if skipped else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
