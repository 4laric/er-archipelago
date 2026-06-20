#!/usr/bin/env python3
r"""
patch_apworld_derando_extras.py  (run on Windows from repo root; needs patch_apworld_questline_derando.py applied first)

Two small follow-ups from the unplaced-items audit:

1) Extend QUESTLINE_DERANDO (curation.py) with unique quest items that gate only optional
   content (verified: no region/goal entrance rules): Two Fingers' Prayerbook, the Twinned set
   (Helm/Armor/Gauntlets/Greaves -- D's body, Fia's quest), "Resurrection" Painting,
   Mohg's Shackle, Golden Order Principia. They de-randomize with `derandomize_questlines`.
   (Starlight Shards / Festering Bloody Finger / Seedbed Curse are NOT here -- they're
   multi-location consumables / the Dung Eater ladder, handled separately.)

2) progressive_physick: drop the redundant base "Flask of Wondrous Physick" from the pool
   (the progressive ladder's step 1 already grants the flask).

Idempotent; asserts anchors.
"""
import os
ROOT = os.path.dirname(os.path.abspath(__file__))
ER   = os.path.join(ROOT, "Archipelago", "worlds", "eldenring")
INIT = os.path.join(ER, "__init__.py")
CUR  = os.path.join(ER, "curation.py")

def load(p):
    with open(p, "r", encoding="utf-8", newline="") as f: return f.read()
def save(p, s):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(s)
def nl_of(s): return "\r\n" if "\r\n" in s else "\n"
def once(s, old, new, label, marker):
    if marker in s: return s, False
    n = s.count(old)
    if n != 1: raise SystemExit(f"[FAIL] {label}: expected 1 anchor, found {n}")
    return s.replace(old, new, 1), True

changed = False

# 1) curation.py -- extend QUESTLINE_DERANDO
c = load(CUR); NL = nl_of(c)
anchor = '    "Secret Rite Scroll",'
add = NL.join([
'    "Secret Rite Scroll",',
'    # extras (unplaced-audit 2026-06-19): unique quest items, optional-gating only',
'    "Two Fingers\' Prayerbook", "Golden Order Principia",',
'    "Twinned Helm", "Twinned Armor", "Twinned Gauntlets", "Twinned Greaves",',
'    \'"Resurrection" Painting\', "Mohg\'s Shackle",',
])
c, ch = once(c, anchor, add, "curation: extend QUESTLINE_DERANDO",
             "unplaced-audit 2026-06-19"); changed |= ch
save(CUR, c)

# 2) __init__.py -- drop base Flask under progressive_physick (generate_early, after merchant bells)
i = load(INIT); NL = nl_of(i)
mb = (
'        if self.options.merchant_bell_logic.value == 1:' + NL +
'            for _bell in merchant_bell_names(bool(self.options.enable_dlc)):' + NL +
'                item_table[_bell].skip = False' + NL +
'                item_table[_bell].classification = ItemClassification.progression')
phys = NL + NL.join([
"",
"        # progressive_physick: the ladder's step 1 grants the flask, so drop the redundant base",
"        # \"Flask of Wondrous Physick\" from the pool (was double-counted). (unplaced-audit 2026-06-19.)",
"        if self._progressive_physick_active() and \"Flask of Wondrous Physick\" in item_table:",
"            item_table[\"Flask of Wondrous Physick\"].skip = True",
])
i, ch = once(i, mb, mb + phys, "init: drop base flask under progressive_physick",
             "progressive_physick: the ladder's step 1 grants the flask"); changed |= ch
save(INIT, i)

print("[OK] derando-extras patch applied." if changed else "[OK] already applied -- no changes.")
