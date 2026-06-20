#!/usr/bin/env python3
r"""
patch_apworld_num_regions_random_start_REVERT.py  (run on Windows from repo root)

Reverts patch_apworld_num_regions_random_start.py. That feature let random_start_region re-root
the hub under num_regions, which deterministically conflicts with the num_regions spine (the spine
bootstraps the lock chain + great-rune path from Limgrave-as-free-root; re-rooting -> goal
unreachable -> "Game appears as unbeatable"). Restores the original guard (random_start bails when
any region-seal spine goal is active) and removes the num_regions tag + kept-set candidate filter.
Idempotent.
"""
import os
ROOT = os.path.dirname(os.path.abspath(__file__))
INIT = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "__init__.py")
def load(p):
    with open(p, "r", encoding="utf-8", newline="") as f: return f.read()
def save(p, s):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(s)
def nl_of(s): return "\r\n" if "\r\n" in s else "\n"
def rev(s, new, old, label):
    # new = text introduced by the feature; old = original. revert new->old.
    if new not in s:
        return s, False
    if s.count(new) != 1:
        raise SystemExit(f"[FAIL] {label}: expected 1 occurrence of feature text, found {s.count(new)}")
    return s.replace(new, old, 1), True

i = load(INIT); NL = nl_of(i)
changed = False
# 2) restore guard
i, c = rev(i,
    '            if getattr(self, "_spine_active", False) and not getattr(self, "_num_regions_active", False):',
    '            if getattr(self, "_spine_active", False):',
    "restore guard"); changed |= c
# 1) remove the _num_regions_active tag
i, c = rev(i,
    '                self._num_regions_active = True' + NL + '                if self.options.region_access.value != 1:',
    '                if self.options.region_access.value != 1:',
    "remove tag"); changed |= c
# 3) remove the kept-set candidate filter
i, c = rev(i,
    '                          and getattr(item_table[REGION_LOCK_ITEM[r]], "inject", False)]' + NL +
    '                if getattr(self, "_num_regions_active", False):' + NL +
    '                    _cands = [r for r in _cands if r not in getattr(self, "_spine_sealed_regions", set())]',
    '                          and getattr(item_table[REGION_LOCK_ITEM[r]], "inject", False)]',
    "remove kept filter"); changed |= c
save(INIT, i)
print("[OK] random-start-under-num_regions reverted." if changed else "[OK] already reverted -- no changes.")
