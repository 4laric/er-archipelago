"""The version-site list stays COMPLETE, and stays LIVE.

MOTIVATING CASE (CONTRIBUTING rule 11). `check_version_sites.SITES` carries this comment:

    🛑 THE LIST. [...] Adding a site here is what "adding a version site" means -- there is no
    second place to remember.

On 2026-08-17 it listed FOUR sites and there were SEVEN. The three it did not know about were the
client's `contract_gen.rs` and the wizard's two copies of its metadata blob, and all three are
GENERATED -- which is precisely why nobody added them by hand. The consequence was not a silent
one, it was three consecutive windows of the same red:

    v0.4.4, v0.4.5, v0.4.6   "no client half was needed"  ->  `generators`: the PINNED client
                                                              commit does not contain the output
                                                              this repo generates

and at v0.4.6 a second one in the same window, when the wizard blob went out stale and step 12 of
`tests` caught it eight minutes and a push later. Every time, `check_version_sites` had reported
that every site agreed -- truthfully, about the sites it knew.

🛑 A GATE THAT REPORTS "2 SITES AGREE" WHILE THREE FILES DISAGREE IS WORSE THAN NO GATE. It is
evidence of the thing it failed to check, and it is why the opener stopped looking.

So the list itself needs a gate, and it cannot be another list. These two tests DERIVE the answer:

  1. every registered site still MATCHES -- a pattern that silently stopped matching is a site
     that stopped being checked, which is rule 4's "a filter with no tally is a lie";
  2. no UNREGISTERED tracked file carries the CURRENT version next to a version identifier -- so
     a site added later is registered, or this goes red the moment it is bumped.

Keying (2) on the CURRENT version is what makes it self-maintaining rather than an allowlist. The
docs quote `APWORLD_VERSION_EXPECTED = "0.3.0"` as an example, `greenfield/handoff/contract_gen.rs`
is a frozen 0.2.0 artifact, and `test_gf_contract_versions` pins 0.3.2 on purpose -- none of them
carry today's number, so none of them are false positives, and none of them need naming here.
"""

import os
import re
import subprocess
import sys

try:
    import pytest
except ImportError:  # 🛑 THE `generators` RUNNER HAS NO PYTEST. It runs this bucket as scripts on a
    # checkout with Archipelago's requirements installed and nothing else, so a module-level
    # `import pytest` is a hard failure there -- which is exactly how this file first went red in
    # CI while passing both ways locally. "AP-free" was the claim in the ledger; "pytest-free" is
    # the other half of it, and the two are not the same promise.
    pytest = None

# 🛑 REPO IS SEARCHED FOR, NOT COUNTED TO. gf_test.py copies this package into a pinned
# Archipelago checkout and copies NO tools/, so walking up a fixed number of directories resolves
# to `_ap` under the harness and dies on FileNotFoundError -- the exact way 45 tests went green
# locally and red in CI on 2026-07-27. `_util.find_repo_root` is where that story is written down
# and is the canonical version of this search.
#
# ⚠️ AND IT IS NOT IMPORTED FROM THERE, DELIBERATELY. `_util` imports the world package, which
# imports `BaseClasses` -- so importing it would drag Archipelago into a suite that is AP-free on
# purpose (that is why this file is in the ledger's GENERATORS bucket, which runs the suites as
# scripts with no AP on the path). Ten lines duplicated is the cheaper of the two wrongs; the
# comment above is the pointer that keeps them from drifting apart silently.
def _find_repo_root(start, marker=os.path.join("tools", "check_integrity.py")):
    d = os.path.abspath(start)
    for _ in range(8):
        if os.path.exists(os.path.join(d, marker)):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


def _unavailable(reason):
    """Skip under pytest; say so and stop when run as a script. Never pass silently."""
    if pytest is not None:
        pytest.skip(reason, allow_module_level=True)
    raise SystemExit("test_gf_version_sites: " + reason)


REPO = _find_repo_root(os.path.dirname(os.path.abspath(__file__)))
if REPO is None:
    _unavailable("needs the repo checkout (tools/ is not installed beside the world by "
                 "gf_test.py); the `generators` CI job runs this suite")
sys.path.insert(0, os.path.join(REPO, "tools"))

import check_version_sites  # noqa: E402  -- THE list. A plain import: it lives in the repo we
# just located, so a failure here is a real breakage and not a reason to skip.

# The identifier, then an optional closing quote (JSON writes `"world_version":`), then the
# separator, then Rust's `&str =`, then the value.
#
# ⚠️ THE OPTIONAL QUOTE IS LOAD-BEARING AND WAS MISSING FIRST TIME. Without it this pattern skips
# every JSON site -- including `archipelago.json`, the one a seed actually reports -- and the test
# passes by finding nothing. A scan that under-reports is the same failure as the list it polices.
VERSION_LINE = re.compile(
    r'(APWORLD_VERSION(?:_EXPECTED)?|apworld_version|world_version)"?\s*[:=]\s*'
    r'(?:&str\s*=\s*)?"(\d+\.\d+\.\d+)"')


def _current_version():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_er_contract_for_sites", os.path.join(REPO, "greenfield", "eldenring", "contract.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.APWORLD_VERSION


def _tracked_files():
    p = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True)
    if p.returncode != 0:
        _unavailable("not a git checkout, so the tracked-file scan cannot run")
    return [f for f in p.stdout.split("\n") if f]


def test_every_registered_site_still_matches():
    """A site whose pattern stopped matching is UNCHECKED, not clean."""
    checked = 0
    for site in check_version_sites.SITES:
        version, note = check_version_sites.read_site(site)
        if version is None and note == "absent" and site.get("optional"):
            continue                      # the client submodule, legitimately not checked out
        assert version is not None, (
            "%s: %s\nThe site is no longer being checked. Either the file moved, or its shape "
            "changed and the pattern in check_version_sites.SITES was not moved with it."
            % (site["what"], note))
        checked += 1
    # WITNESS (test_gf_vacuous_pass): "nothing failed" is also what an empty list looks like.
    assert checked >= 4, (
        "only %d site(s) were actually read. The world-repo half of SITES is archipelago.json, "
        "contract.py and the wizard's two files -- if fewer than that are readable, this test is "
        "passing on an empty set." % checked)


def test_no_unregistered_file_carries_the_current_version():
    """Any tracked file stamped with TODAY's version must be a registered site.

    This is the half that keeps the list COMPLETE. It cannot be satisfied by remembering: a new
    site goes red the first time it is stamped, which is the first time it could ever be wrong.
    """
    current = _current_version()
    registered = {os.path.realpath(s["path"]) for s in check_version_sites.SITES}

    # 🛑 WITNESS FIRST (test_gf_vacuous_pass, and this test was CAUGHT by that ratchet on its own
    # first run). Everything below asserts a list is EMPTY, which is also what a scan that matched
    # nothing produces -- a broken pattern, a `git ls-files` that returned nothing, a version that
    # read as None. The docstring above already warns that the optional quote in VERSION_LINE was
    # missing first time and silently skipped every JSON site; that is this failure mode, live.
    #
    # So: prove the instrument works on files we KNOW are sites before trusting its silence
    # anywhere else.
    proven = [s["what"] for s in check_version_sites.SITES
              if os.path.isfile(s["path"])
              and any(m.group(2) == current
                      for m in VERSION_LINE.finditer(
                          open(s["path"], encoding="utf-8", errors="ignore").read()))]
    assert len(proven) >= 3, (
        "the scan pattern found today's version (%s) in only %d registered site(s) -- %s.\n"
        "It cannot be trusted to find an UNregistered one, so the emptiness asserted below would "
        "mean nothing. Fix VERSION_LINE before reading anything into a clean result."
        % (current, len(proven), proven or "none"))

    strays = []
    for rel in _tracked_files():
        path = os.path.join(REPO, rel)
        if not os.path.isfile(path) or os.path.realpath(path) in registered:
            continue
        try:
            with open(path, encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
        except OSError:
            continue
        for m in VERSION_LINE.finditer(text):
            if m.group(2) == current:
                strays.append("%s -- %s = %r" % (rel, m.group(1), m.group(2)))
                break
    assert not strays, (
        "%d file(s) carry the current version (%s) but are NOT in check_version_sites.SITES:\n"
        "  %s\n\n"
        "Add them there -- that list is the single definition of 'a version site', and the last "
        "three release windows each went red in CI because it was missing one. If a file legitimately "
        "quotes the current version without BEING a site (an example in a doc), quote a different "
        "one: an example that tracks the live version is indistinguishable from a site that does."
        % (len(strays), current, "\n  ".join(strays)))


if __name__ == "__main__":
    # THE TESTS ARE CALLED DIRECTLY, not handed to pytest. The `generators` job runs this bucket as
    # scripts on a runner with NO Archipelago on the path, and `pytest.main([__file__])` would
    # collect through this directory's conftest, which imports the world package and therefore
    # `BaseClasses`. Calling the functions keeps the suite as AP-free as its ledger entry claims --
    # and a claim in a ledger that the file cannot honour is the kind of thing this file exists to
    # catch elsewhere.
    test_every_registered_site_still_matches()
    test_no_unregistered_file_carries_the_current_version()
    print("OK test_gf_version_sites: %d registered site(s), no unregistered file carries the "
          "current version" % len(check_version_sites.SITES))
