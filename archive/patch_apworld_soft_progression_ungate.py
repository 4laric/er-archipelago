#!/usr/bin/env python3
r"""
patch_apworld_soft_progression_ungate.py  (run after patch_apworld_soft_progression.py)

Remove the accessibility gate from soft_progression. The original only demoted under full/items
on the theory that minimal spills everything -- but with num_regions sealing regions, the valid-
location budget is tight under minimal too, so the bells must demote there as well. Now it demotes
whenever the toggle is on, regardless of accessibility. Idempotent.
"""
import os
ROOT = os.path.dirname(os.path.abspath(__file__))
INIT = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "__init__.py")

def load(p):
    with open(p, "r", encoding="utf-8", newline="") as f: return f.read()
def save(p, s):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(s)
def nl_of(s): return "\r\n" if "\r\n" in s else "\n"

i = load(INIT); NL = nl_of(i)
old = ("        if (self.options.soft_progression.value" + NL +
       "                and self.options.accessibility.value != self.options.accessibility.option_minimal):")
new = "        if self.options.soft_progression.value:"
if new + NL in i and old not in i:
    print("[OK] already applied -- no changes.")
else:
    n = i.count(old)
    if n != 1:
        raise SystemExit(f"[FAIL] gated-condition anchor count = {n}")
    i = i.replace(old, new, 1)
    save(INIT, i)
    print("[OK] soft_progression ungate applied.")
