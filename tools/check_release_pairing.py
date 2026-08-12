#!/usr/bin/env python3
"""Refuse to package a release whose CLIENT IDENTITY does not agree with itself.

Four instruments in this project can see the client pin and each looked at something different, so
each could be green while the release was wrong. v0.3.11 is the case that paid for this file: the
tag pinned client `a9830ebe` while client main was `1982599` -- 41 commits and 17 merged PRs apart.

READ THIS BEFORE "FIXING" ANYTHING HERE: v0.3.11 did NOT ship players a stale client. The bundle was
CURRENT. `package_release.ps1` packages the client WORKING TREE, and that tree was up to date. Two
separate reviewers have since inferred the artifact from the pin and been wrong about it in writing.

    A GITLINK IS A RECORD, NOT A BUILD INPUT.

The defect is that the record and the artifact can DISAGREE, so a bug report against a tag cannot be
resolved to a client commit -- and no later fix recovers which build shipped. This tool makes that
disagreement unable to produce a publishable bundle, by asserting one equality chain:

    PIN   git ls-tree HEAD from-software-archipelago-clients      (what the tag records)
 == TREE  git -C from-software-archipelago-clients rev-parse HEAD (what gets packaged), CLEAN
 == MAIN  git ls-remote <client> main                             (what the world thinks is current)
 == DLL   the staged dll contains TREE[:12] and not TREE[:12]+"-dirty"

PIN==TREE is the v0.3.11 failure -- record versus artifact -- and takes NO override. PIN==MAIN is
staleness, which can be a legitimate shipping decision, so it takes ALLOW_STALE_PIN=1; that has to be
typed, which is the point. TREE-clean is hard: a bundle from a dirty tree is the unrecoverable-record
problem in its worst form. The DLL scan is the artifact identifying itself -- `build.rs` already bakes
ER_GIT_SHA (short-12, "-dirty" suffixed) into the binary and `game.rs` prints it in the connect
banner, so nothing new is embedded here; we only check that what shipped says what we think it says.

Why this file and not a CI step: a red job can be routed around, and on v0.3.11 one was -- the
release workflow's pin step went red AFTER the tag was public and the release shipped anyway,
minus two assets. This runs where the zip is BORN. No agreement, no zip; no zip, nothing to upload.

One implementation, N call sites: `package_release.ps1` (the binding site), `release.yaml`'s
pin-record job (the alarm), and any future cut_release.py -- all call THIS, none re-implement it.

Exit codes:  0 = the chain holds   2 = stale pin, allowed by ALLOW_STALE_PIN   1 = hard failure
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass, field

CLIENT_DIR = "from-software-archipelago-clients"
CLIENT_URL = "https://github.com/4laric/from-software-archipelago-clients.git"

OK, STALE_ALLOWED, HARD = 0, 2, 1


@dataclass
class Facts:
    """The five strings the verdict is computed from. Gathering is separated from checking so the
    unit test can inject the v0.3.11 triple without a repo, a network or a dll."""

    pin: str = ""
    tree: str = ""
    tree_dirty: bool = False
    tree_present: bool = True
    main: str = ""
    main_present: bool = True
    dll_name: str = ""
    dll_bytes: bytes = b""
    dll_present: bool = False
    notes: list = field(default_factory=list)


def _run(args, cwd=None):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def gather(repo: str, dll: str | None, allow_no_remote: bool = False) -> Facts:
    f = Facts()
    rc, out, _ = _run(["git", "ls-tree", "HEAD", CLIENT_DIR], cwd=repo)
    if rc == 0:
        for line in out.splitlines():
            parts = line.split()
            # <mode> commit <sha>\t<path> -- the gitlink is the row whose type is `commit`
            if len(parts) >= 3 and parts[1] == "commit":
                f.pin = parts[2]

    client = os.path.join(repo, CLIENT_DIR)
    if not os.path.exists(os.path.join(client, ".git")):
        # CI checks out the world without the submodule. That is not a failure -- it is a smaller
        # question, and saying so beats asserting nothing while looking green.
        f.tree_present = False
        f.notes.append("submodule not checked out -- TREE, clean and DLL checks SKIPPED")
    else:
        rc, out, _ = _run(["git", "rev-parse", "HEAD"], cwd=client)
        if rc == 0:
            f.tree = out
        rc, out, _ = _run(["git", "status", "--porcelain"], cwd=client)
        f.tree_dirty = rc == 0 and bool(out.strip())

    rc, out, err = _run(["git", "ls-remote", CLIENT_URL, "main"])
    if rc == 0 and out:
        f.main = out.split()[0]
    else:
        f.main_present = False
        f.notes.append("could not reach client main (%s)" % (err or "no output"))
        if not allow_no_remote:
            f.notes.append("network failure blocks packaging on purpose; -AllowStalePin is the "
                           "conscious escape")

    if dll:
        f.dll_name = dll
        if os.path.isfile(dll):
            f.dll_present = True
            with open(dll, "rb") as fh:
                f.dll_bytes = fh.read()
    return f


def check(f: Facts, allow_stale: bool) -> tuple[int, list]:
    """Pure. Returns (exit code, lines to print). Every line names the facts it compared -- a gate
    that fires without saying what it compared sends the reader back to the source."""
    lines, verdict = [], OK
    for n in f.notes:
        lines.append("note   : %s" % n)
    lines.append("pin    : %s" % (f.pin or "(none)"))
    lines.append("tree   : %s%s" % (f.tree or "(skipped)", " DIRTY" if f.tree_dirty else ""))
    lines.append("main   : %s" % (f.main or "(unavailable)"))
    if f.dll_name:
        lines.append("dll    : %s%s" % (f.dll_name, "" if f.dll_present else " (MISSING)"))

    if not f.pin:
        lines.append("FAIL   : no gitlink at %s -- this tree does not record a client at all." % CLIENT_DIR)
        return HARD, lines

    if f.tree_present:
        if not f.tree:
            lines.append("FAIL   : the submodule is checked out but HEAD could not be read.")
            return HARD, lines
        if f.tree != f.pin:
            lines.append("FAIL   : PIN != TREE. The gitlink records %s; the client tree that would be" % f.pin[:12])
            lines.append("         packaged is %s. The bundle and its record would name different" % f.tree[:12])
            lines.append("         builds, and no later fix recovers which one shipped. This is the")
            lines.append("         v0.3.11 defect exactly. Commit the gitlink bump, then package.")
            lines.append("         There is deliberately NO override for this one.")
            return HARD, lines
        if f.tree_dirty:
            lines.append("FAIL   : the client working tree is DIRTY, so the dll about to be packaged")
            lines.append("         corresponds to no commit at all. Commit or stash, then package.")
            return HARD, lines

    if not f.main_present:
        if allow_stale:
            lines.append("WARN   : client main unreachable; allowed by ALLOW_STALE_PIN.")
            verdict = STALE_ALLOWED
        else:
            lines.append("FAIL   : client main could not be read, so the pin cannot be shown current.")
            return HARD, lines
    elif f.pin != f.main:
        if allow_stale:
            lines.append("WARN   : the pin (%s) trails client main (%s), allowed by" % (f.pin[:12], f.main[:12]))
            lines.append("         ALLOW_STALE_PIN. The release will record a deliberate lag.")
            verdict = STALE_ALLOWED
        else:
            lines.append("FAIL   : the pin (%s) is not client main (%s)." % (f.pin[:12], f.main[:12]))
            lines.append("         Bump the gitlink, or set ALLOW_STALE_PIN=1 if the lag is deliberate.")
            return HARD, lines

    if f.dll_name and f.tree_present:
        if not f.dll_present:
            lines.append("FAIL   : %s does not exist, so the artifact cannot identify itself." % f.dll_name)
            return HARD, lines
        short = f.tree[:12].encode("ascii")
        if short + b"-dirty" in f.dll_bytes:
            lines.append("FAIL   : the dll stamps %s-dirty -- it was built from uncommitted work." % f.tree[:12])
            return HARD, lines
        if short not in f.dll_bytes:
            lines.append("FAIL   : the dll does not carry ER_GIT_SHA %s. It was built from a" % f.tree[:12])
            lines.append("         different commit than the tree about to be recorded. Rebuild the")
            lines.append("         client from this tree before packaging.")
            return HARD, lines
        lines.append("dll ok : carries ER_GIT_SHA %s" % f.tree[:12])
    elif f.dll_name and not f.tree_present:
        lines.append("FAIL   : --dll needs the submodule checked out to know what sha to expect.")
        return HARD, lines

    if verdict == STALE_ALLOWED:
        # 🛑 Do NOT say "agree" here. They do not agree; the operator bought the lag on purpose,
        # and a summary line that rounds that up to PASS is how a warning becomes invisible.
        lines.append("ALLOWED: staged with a KNOWN-STALE pin. Exit 2 -- review before shipping.")
    else:
        lines.append("PASS   : pin, client tree, client main%s agree."
                     % (" and the dll" if f.dll_present else ""))
    return verdict, lines


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    help="world repo root (default: this tool's repo)")
    ap.add_argument("--dll", default=None,
                    help="staged client dll to scan for its embedded ER_GIT_SHA")
    args = ap.parse_args(argv)
    allow_stale = os.environ.get("ALLOW_STALE_PIN", "0") == "1"
    facts = gather(args.repo, args.dll, allow_no_remote=allow_stale)
    code, lines = check(facts, allow_stale)
    for line in lines:
        print(line)
    return code


if __name__ == "__main__":
    sys.exit(main())
