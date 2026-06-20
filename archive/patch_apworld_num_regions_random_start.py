#!/usr/bin/env python3
r"""
patch_apworld_num_regions_random_start.py  (run on Windows from repo root)

Let random_start_region roll the free hub under num_regions. Today the random-start path bails
whenever a region-seal goal is active (it's geographic for capital/region_count/messmer/godrick).
But num_regions is warp-based, so any KEPT region can be the free hub. This:
  1. tags the num_regions resolution with self._num_regions_active = True,
  2. un-gates the random-start path for that case (still bails for the other spine goals),
  3. restricts the start candidates to KEPT regions (the inject=True filter already does this; the
     explicit sealed-set check is belt-and-suspenders).
The existing machinery does the rest (inject Limgrave Lock, precollect the chosen region's lock,
warp-to-start, Roundtable re-root). Only fires when BOTH num_regions and random_start_region are set.
Idempotent; asserts anchors.
"""
import os
ROOT = os.path.dirname(os.path.abspath(__file__))
INIT = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "__init__.py")

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

i = load(INIT); NL = nl_of(i)
changed = False

# 1) tag num_regions resolution
warp = (
'                if self.options.region_access.value != 1:' + NL +
'                    self.options.region_access.value = 1' + NL +
'                    warning(f"{self.player_name}: num_regions forces region_access=warp "')
i, c = once(i, warp,
            '                self._num_regions_active = True' + NL + warp,
            "tag _num_regions_active", "self._num_regions_active = True"); changed |= c

# 2) un-gate random-start for num_regions
i, c = once(i,
            '            if getattr(self, "_spine_active", False):',
            '            if getattr(self, "_spine_active", False) and not getattr(self, "_num_regions_active", False):',
            "un-gate random_start for num_regions",
            'and not getattr(self, "_num_regions_active", False):'); changed |= c

# 3) restrict candidates to kept regions under num_regions
cands_tail = '                          and getattr(item_table[REGION_LOCK_ITEM[r]], "inject", False)]'
i, c = once(i, cands_tail,
            cands_tail + NL +
            '                if getattr(self, "_num_regions_active", False):' + NL +
            '                    _cands = [r for r in _cands if r not in getattr(self, "_spine_sealed_regions", set())]',
            "restrict candidates to kept", "_cands = [r for r in _cands if r not in getattr(self, \"_spine_sealed_regions\""); changed |= c

save(INIT, i)
print("[OK] num_regions random-start patch applied." if changed else "[OK] already applied -- no changes.")
