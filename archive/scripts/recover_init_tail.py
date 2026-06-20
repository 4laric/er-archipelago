#!/usr/bin/env python3
r"""
recover_init_tail.py  (run on Windows from the repo root)

Repairs the truncated worlds/eldenring/__init__.py (the write gremlin chopped fill_slot_data's
tail: no slot_data dict, no `return slot_data`, no apIdsToItemIds -> baker NullReferenceException
at ArchipelagoForm.cs:324). Grafts the full tail from __init__.py.bak_spelunkertorch onto your
current (patched) file, keeping every applied patch in the early part.

After this runs, RE-APPLY the natural-triggers patches to restore natural_key_triggers:
    python patch_apworld_natural_triggers.py
    python patch_apworld_natural_triggers_p2.py
Then gen-test + bake.
"""
import os, ast
ROOT = os.path.dirname(os.path.abspath(__file__))
INIT = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "__init__.py")
BAK  = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "__init__.py.bak_spelunkertorch")

def load(p):
    with open(p, "r", encoding="utf-8", newline="") as f: return f.read()
def save(p, s):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(s)

cur = load(INIT)
if "apIdsToItemIds" in cur and "return slot_data" in cur:
    raise SystemExit("[OK] __init__.py already has its tail (apIdsToItemIds + return slot_data); nothing to do.")
if not os.path.isfile(BAK):
    raise SystemExit(f"[FAIL] backup not found: {BAK}")
bak = load(BAK)
if "apIdsToItemIds" not in bak or "return slot_data" not in bak:
    raise SystemExit("[FAIL] __init__.py.bak_spelunkertorch is also missing the tail; pick another full .bak")

# Splice at the initial lock_notify_items dict-comp (present in both; natural-triggers inserts AFTER it).
anchor = '        lock_notify_items = {_lk: (_c | 0x40000000) for _lk, _c in _tmp.items()}'
if cur.count(anchor) != 1 or bak.count(anchor) != 1:
    raise SystemExit(f"[FAIL] splice anchor count cur={cur.count(anchor)} bak={bak.count(anchor)} (need 1/1)")
ic = cur.index(anchor) + len(anchor)
ib = bak.index(anchor) + len(anchor)
fixed = cur[:ic] + bak[ib:]

# sanity
assert "apIdsToItemIds" in fixed and "return slot_data" in fixed, "tail not restored"
ast.parse(fixed)  # must be valid Python

# backup the broken file, then write
save(INIT + ".bak_truncated", cur)
save(INIT, fixed)
print(f"[OK] tail restored ({fixed.count(chr(10))} lines). Broken copy saved as __init__.py.bak_truncated.")
print("NEXT: python patch_apworld_natural_triggers.py  &&  python patch_apworld_natural_triggers_p2.py")
