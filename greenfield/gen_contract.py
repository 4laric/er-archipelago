#!/usr/bin/env python3
"""Regenerate the contract mirrors from eldenring/contract.py (the single source of truth):
  greenfield/CONTRACT.md                                  -- human table
  greenfield/eldenring/contract.json                   -- language-neutral reference
  from-software-archipelago-clients/.../src/contract_gen.rs -- Rust mirror (client validates same shapes)
Run after editing contract.py:  python greenfield/gen_contract.py
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, "eldenring"))
import contract  # noqa: E402

def w(path, text):
    # Every generated file ends with a newline. tools/check_integrity.py treats a missing trailing
    # newline as a possible TRUNCATED TAIL, so a generator that omits one produces a permanent WARN
    # on a perfectly clean file -- and a gate that cries wolf on every run is a gate people stop
    # reading, which is how a real truncation gets waved through. Enforced here rather than in
    # to_json() so it holds for every future output of this script too.
    if not text.endswith("\n"):
        text += "\n"
    # IDEMPOTENT: do not rewrite a byte-identical file. An unconditional write is invisible in a
    # diff but it stamps a fresh mtime, and package_release.ps1 used to compare the shipped .dll's
    # mtime against these files -- so simply RUNNING this script guaranteed "the .dll is older than
    # contract_gen.rs" on the very next check. A no-op that changes the filesystem is not a no-op.
    try:
        with open(path, encoding="utf-8", newline="") as f:
            if f.read().replace("\r\n", "\n") == text:
                print("unchanged", os.path.relpath(path, REPO), f"({len(text)} b)")
                return
    except OSError:
        pass
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("wrote", os.path.relpath(path, REPO), f"({len(text)} b)")

w(os.path.join(HERE, "CONTRACT.md"), contract.to_markdown())
w(os.path.join(HERE, "eldenring", "contract.json"), contract.to_json())
rs = os.path.join(REPO, "from-software-archipelago-clients", "crates",
                  "eldenring-archipelago", "src", "contract_gen.rs")
if os.path.isdir(os.path.dirname(rs)):
    w(rs, contract.to_rust())
else:
    print("skip contract_gen.rs (client src dir absent)")
