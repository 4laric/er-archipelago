#!/usr/bin/env python3
r"""
patch_apworld_num_regions_altus.py  (run on Windows from repo root)

Fix num_regions "Game appears as unbeatable": the random capital subset sealed Altus, but Leyndell
has no region lock (it's the great-rune-gated capstone), so the warp model has no way to reach the
capital and Altus is the only physical route. num_regions_floor wrongly assumed warp ignores Altus.

Fix (region_spine.py): force ALTUS_STEP into the kept middle steps, and raise num_regions_floor by 1
to fund it (2 + great_runes_required + 1[Altus]). So num_regions:4 / great_runes_required:2 now
keeps Limgrave + Leyndell + Altus + 2 rune bosses (effective 5) and the capital is reachable.
Idempotent.
"""
import os
ROOT = os.path.dirname(os.path.abspath(__file__))
RS = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "region_spine.py")

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

s = load(RS); NL = nl_of(s)
changed = False

# 1) floor += 1 for the mandatory Altus step
s, c = once(s,
    "    return 2 + max(0, int(great_runes_required))",
    "    return 2 + max(0, int(great_runes_required)) + (1 if ALTUS_STEP not in RUNE_STEPS else 0)  # +1: Altus is the only route to Leyndell",
    "num_regions_floor +Altus", "+ (1 if ALTUS_STEP not in RUNE_STEPS else 0)")
changed |= c

# 2) force ALTUS_STEP into picked before the great-rune floor sampling
old = ("    # 1) guarantee the great-rune floor: pick great_runes_required rune-boss steps at random first." + NL +
       "    n_rune = min(int(great_runes_required), len(rune_steps), need_random)" + NL +
       "    picked = list(rng.sample(rune_steps, n_rune)) if n_rune > 0 else []")
new = ("    # 0) Altus is the ONLY route to Leyndell (the capstone has no warp lock), so force it in." + NL +
       "    picked = [ALTUS_STEP] if (ALTUS_STEP in NUM_REGIONS_MIDDLE_STEPS and need_random >= 1) else []" + NL +
       "    # 1) guarantee the great-rune floor: pick great_runes_required rune-boss steps at random." + NL +
       "    _rs = [s for s in rune_steps if s not in picked]" + NL +
       "    n_rune = min(int(great_runes_required), len(_rs), max(0, need_random - len(picked)))" + NL +
       "    picked += list(rng.sample(_rs, n_rune)) if n_rune > 0 else []")
s, c = once(s, old, new, "force Altus into picked", "Altus is the ONLY route to Leyndell (the capstone")
changed |= c

save(RS, s)
print("[OK] num_regions Altus fix applied." if changed else "[OK] already applied -- no changes.")
