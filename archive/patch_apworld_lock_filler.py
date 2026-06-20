#!/usr/bin/env python3
r"""
patch_apworld_lock_filler.py  (run on Windows from repo root)

_lock_class_at_vanilla pins vanilla items and removes them from the pool, but keeps their
progression classification. When such a location is behind a sealed region (num_regions /
region_lock), AP's accessibility sweep treats the locked progression item as required-reachable
and fails ("Could not access required locations"). All _lock_class_at_vanilla users are either
do-not-randomize flask/blessing or de-rando'd questline/Gurranq items -- NONE are goal-required --
so downgrade the pinned copy to filler (same fix dlc_only/spine already use). Idempotent.
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
old = ("            self.local_itempool.remove(item)" + NL +
       "            location.place_locked_item(item)")
new = ("            self.local_itempool.remove(item)" + NL +
       "            # Downgrade the vanilla-pinned copy to filler so AP's accessibility sweep doesn't" + NL +
       "            # treat it as required-reachable when its location is behind a sealed region" + NL +
       "            # (num_regions / region_lock). None of these are goal-required." + NL +
       "            item.classification = ItemClassification.filler" + NL +
       "            location.place_locked_item(item)")
if "Downgrade the vanilla-pinned copy to filler" in i:
    print("[OK] already applied -- no changes.")
else:
    n = i.count(old)
    if n != 1:
        raise SystemExit(f"[FAIL] anchor count = {n}")
    save(INIT, i.replace(old, new, 1))
    print("[OK] lock-filler patch applied.")
