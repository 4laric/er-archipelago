#!/usr/bin/env python3
"""Regenerate the contract mirrors from eldenring_gf/contract.py (the single source of truth):
  greenfield/CONTRACT.md                                  -- human table
  greenfield/eldenring_gf/contract.json                   -- language-neutral reference
  from-software-archipelago-clients/.../src/contract_gen.rs -- Rust mirror (client validates same shapes)
Run after editing contract.py:  python greenfield/gen_contract.py
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, "eldenring_gf"))
import contract  # noqa: E402

def w(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("wrote", os.path.relpath(path, REPO), f"({len(text)} b)")

w(os.path.join(HERE, "CONTRACT.md"), contract.to_markdown())
w(os.path.join(HERE, "eldenring_gf", "contract.json"), contract.to_json())
rs = os.path.join(REPO, "from-software-archipelago-clients", "crates",
                  "eldenring-archipelago", "src", "contract_gen.rs")
if os.path.isdir(os.path.dirname(rs)):
    w(rs, contract.to_rust())
else:
    print("skip contract_gen.rs (client src dir absent)")
