#!/usr/bin/env python3
r"""
patch_apworld_questline_crowns.py  (run after the other questline patches)

Extend QUESTLINE_DERANDO with more unique puzzle/quest items that gate only optional content
(verified): the 5 Academy Glintstone Crowns (gate the Converted Tower check via Erudition + a
crown disjunction), the 6 remaining merchant Prayerbooks (refs=0), and Fingerprint Grape
(frenzied/Three Fingers puzzle; no frenzied goal exists). Erudition itself is left in the pool
(inject-flagged; the crowns already satisfy the disjunction's crown half). Idempotent.
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
marker = "extras v3 (unplaced-audit"
if marker in c:
    print("[OK] already applied -- no changes.")
else:
    anchor = '    "Secret Rite Scroll",'
    if c.count(anchor) != 1:
        raise SystemExit(f"[FAIL] anchor count = {c.count(anchor)}")
    add = NL.join([
        '    "Secret Rite Scroll",',
        '    # extras v3 (unplaced-audit 2026-06-19): Academy Glintstone Crowns (Converted Tower puzzle),',
        '    # the rest of the merchant prayerbooks (refs=0), and Fingerprint Grape (frenzied puzzle).',
        '    "Twinsage Glintstone Crown", "Olivinus Glintstone Crown", "Lazuli Glintstone Crown",',
        '    "Karolos Glintstone Crown", "Witch\'s Glintstone Crown",',
        '    "Godskin Prayerbook", "Assassin\'s Prayerbook", "Fire Monks\' Prayerbook",',
        '    "Giant\'s Prayerbook", "Dragon Cult Prayerbook", "Ancient Dragon Prayerbook",',
        '    "Fingerprint Grape",',
    ])
    c = c.replace(anchor, add, 1)
    save(CUR, c)
    print("[OK] questline-crowns patch applied.")
