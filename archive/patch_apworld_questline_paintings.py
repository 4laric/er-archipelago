#!/usr/bin/env python3
r"""
patch_apworld_questline_paintings.py  (run after patch_apworld_questline_derando.py + _derando_extras.py)

Extend QUESTLINE_DERANDO with the remaining unique puzzle/quest items that gate nothing in logic
(verified refs=0): all 10 paintings, the 3 sorcery/incant scrolls, and Margit's Shackle. They
de-randomize with `derandomize_questlines`. Idempotent.
"""
import os
ROOT = os.path.dirname(os.path.abspath(__file__))
CUR  = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "curation.py")

def load(p):
    with open(p, "r", encoding="utf-8", newline="") as f: return f.read()
def save(p, s):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(s)
def nl_of(s): return "\r\n" if "\r\n" in s else "\n"

c = load(CUR); NL = nl_of(c)
marker = "extras v2 (unplaced-audit"
if marker in c:
    print("[OK] already applied -- no changes.")
else:
    anchor = '    "Secret Rite Scroll",'
    if c.count(anchor) != 1:
        raise SystemExit(f"[FAIL] anchor count = {c.count(anchor)}")
    add = NL.join([
        '    "Secret Rite Scroll",',
        '    # extras v2 (unplaced-audit 2026-06-19): all paintings + scrolls + Margit\'s Shackle (refs=0)',
        '    "\\"Homing Instinct\\" Painting", "\\"Champion\'s Song\\" Painting", "\\"Sorcerer\\" Painting",',
        '    "\\"Prophecy\\" Painting", "\\"Flightless Bird\\" Painting", "\\"Redmane\\" Painting",',
        '    "\\"Resurrection\\" Painting", "\\"Incursion\\" Painting", "\\"The Sacred Tower\\" Painting",',
        '    "\\"Domain of Dragons\\" Painting",',
        '    "Royal House Scroll", "Academy Scroll", "Conspectus Scroll", "Margit\'s Shackle",',
    ])
    c = c.replace(anchor, add, 1)
    save(CUR, c)
    print("[OK] questline-paintings patch applied.")
