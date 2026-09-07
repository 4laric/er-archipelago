#!/usr/bin/env python3
"""mfg_pin.py -- the MapForGoblins engine pin: check it against the fork, bump it, keep it honest.

THE BUILD IS ALREADY IN THE PIPELINE. `er-release.yaml`'s `mfg-dll` job clones the fork at
`release/MFG-VERSION.json` `source_commit`, fetches the pinned vanilla inputs, builds, writes the AP
preset and records provenance. It builds EXACTLY the commit the pin names -- which is the whole
point, and also the trap: when the fork moves and nobody bumps the pin, the release faithfully
ships the old engine, and nothing says so. v0.6.0.1 (2026-09-07): the fork merged the
progression-rings default (PR #8), the packager started requiring the new preset key, and the pin
still said the commit before it. Nothing was red until packaging.

So this file gives the pin the same treatment the client gitlink gets:

  --check         fail when `source_commit` is not the fork's default-branch head (CI: the
                  `mfg-pin-drift` job on main, and the `mfg-dll` release job unless
                  `allow_stale_mfg` is set). Also fails when the world's preset
                  (`package_mfg.PRESET`) names a key the fork's `tools/make_ap_ini.py` does not
                  set to the same value -- the two tables are one preset written twice.
  --bump [SHA]    rewrite `source_commit` to SHA (default: the fork's default-branch head). The
                  inputs pin (`input_release`, `input_sha256`) is untouched: the vanilla inputs
                  change on their own schedule, in the private inputs repository.

Network: `git ls-remote` for the head, and one raw-file fetch for the fork's preset script. No
Archipelago, no client checkout, no secrets -- the fork is public.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCK = os.path.join(REPO, "release", "MFG-VERSION.json")
PRESET_SCRIPT = "tools/make_ap_ini.py"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import package_mfg  # noqa: E402  -- PRESET: what the packager will REQUIRE of the built ini


def load_lock():
    with open(LOCK, encoding="utf-8-sig") as fh:
        return json.load(fh)


def remote_head(repo_url):
    out = subprocess.run(["git", "ls-remote", repo_url, "HEAD"], capture_output=True, text=True,
                         check=True).stdout
    for line in out.splitlines():
        sha, ref = line.split("\t")
        if ref == "HEAD":
            return sha
    raise RuntimeError("git ls-remote returned no HEAD for %s" % repo_url)


def raw_url(repo_url, sha, path):
    m = re.match(r"https://github\.com/([^/]+)/([^/.]+)(?:\.git)?/?$", repo_url)
    if not m:
        raise RuntimeError("cannot derive a raw URL from %r" % repo_url)
    return "https://raw.githubusercontent.com/%s/%s/%s/%s" % (m.group(1), m.group(2), sha, path)


def fork_preset(repo_url, sha):
    """{section: {key: value}} from the fork's make_ap_ini.py SETTINGS at `sha`."""
    with urllib.request.urlopen(raw_url(repo_url, sha, PRESET_SCRIPT), timeout=30) as resp:
        src = resp.read().decode("utf-8")
    m = re.search(r"^SETTINGS\s*=\s*(\{.*?\n\})", src, re.S | re.M)
    if not m:
        raise RuntimeError("%s at %s has no SETTINGS table" % (PRESET_SCRIPT, sha[:12]))
    ns = {}
    exec("SETTINGS = " + m.group(1), ns)  # noqa: S102 -- a dict literal from a pinned public file
    return ns["SETTINGS"]


def preset_drift(world, fork):
    """Keys the world REQUIRES that the fork's preset script does not write, or writes differently.
    A key the fork leaves to the engine's schema default is reported as a WARNING (the stock ini
    still carries it); a conflicting value is an ERROR (the build cannot satisfy the packager)."""
    errors, warnings = [], []
    for section, fields in world.items():
        for key, value in fields.items():
            got = fork.get(section, {}).get(key)
            if got is None:
                warnings.append("[%s] %s=%s is required by package_mfg.PRESET but the fork's "
                                "%s leaves it to the schema default" % (section, key, value,
                                                                        PRESET_SCRIPT))
            elif str(got).strip().lower() != str(value).strip().lower():
                errors.append("[%s] %s: world requires %s, the fork's %s writes %s"
                              % (section, key, value, PRESET_SCRIPT, got))
    return errors, warnings


def check(allow_behind=False):
    lock = load_lock()
    head = remote_head(lock["source_repository"])
    pinned = lock["source_commit"]
    print("mfg_pin: pinned %s  fork head %s" % (pinned[:12], head[:12]))
    rc = 0
    if pinned != head:
        msg = ("release/MFG-VERSION.json pins %s but %s is at %s -- the next release would build "
               "the OLD engine. Bump with: python tools/mfg_pin.py --bump"
               % (pinned[:12], lock["source_repository"], head[:12]))
        if allow_behind:
            print("WARN mfg_pin: " + msg)
        else:
            print("ERROR mfg_pin: " + msg, file=sys.stderr)
            rc = 1
    errors, warnings = preset_drift(package_mfg.PRESET, fork_preset(lock["source_repository"], pinned))
    for w in warnings:
        print("WARN mfg_pin: " + w)
    for e in errors:
        print("ERROR mfg_pin: " + e, file=sys.stderr)
        rc = 1
    if rc == 0:
        print("OK mfg_pin: the pin is the fork's head and the preset tables agree")
    return rc


def bump(sha=None):
    lock = load_lock()
    target = sha or remote_head(lock["source_repository"])
    if not re.fullmatch(r"[0-9a-f]{40}", target):
        print("ERROR mfg_pin: --bump wants a full 40-hex sha, got %r" % target, file=sys.stderr)
        return 2
    if target == lock["source_commit"]:
        print("mfg_pin: already pinned at %s" % target[:12])
        return 0
    with open(LOCK, encoding="utf-8-sig", newline="") as fh:
        text = fh.read()
    new = text.replace('"source_commit": "%s"' % lock["source_commit"],
                       '"source_commit": "%s"' % target)
    if new == text:
        print("ERROR mfg_pin: could not rewrite source_commit in place", file=sys.stderr)
        return 1
    with open(LOCK, "w", encoding="utf-8", newline="") as fh:
        fh.write(new)
    print("mfg_pin: source_commit %s -> %s (inputs pin untouched)"
          % (lock["source_commit"][:12], target[:12]))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--bump", nargs="?", const="", metavar="SHA")
    ap.add_argument("--allow-behind", action="store_true",
                    help="with --check: a pin behind the fork head warns instead of failing")
    args = ap.parse_args(argv)
    if args.check:
        return check(allow_behind=args.allow_behind)
    return bump(args.bump or None)


if __name__ == "__main__":
    sys.exit(main())
