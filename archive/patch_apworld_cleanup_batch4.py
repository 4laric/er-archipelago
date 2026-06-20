#!/usr/bin/env python3
r"""
patch_apworld_cleanup_batch4.py  (run after the earlier questline + tidy patches)

Unplaced-audit follow-ups:
  - QUESTLINE_DERANDO += "Law of Regression" (refs=0) and "Chrysalids' Memento" (gates only a
    Roderika Golden Seed; locking it vanilla keeps that Seedtree check reachable). Both unique.
  - tidy_fun_consumables += "Shabriri Grape" (3 locs, gates the frenzied check at count 3 -- same
    consumable pattern as Starlight Shards: skip from pool + precollect 3).
Drawing-Room Key is intentionally NOT cut -- it gates the Volcano Manor region entrance.
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

# curation.py -- extend QUESTLINE_DERANDO
c = load(CUR); NL = nl_of(c)
add = NL.join([
    '    "Secret Rite Scroll",',
    '    # extras v4 (unplaced-audit 2026-06-19): Law of Regression (refs=0), Chrysalids\' Memento',
    '    # (gates only a Roderika Golden Seed -- Seedtree check stays reachable when locked).',
    '    "Law of Regression", "Chrysalids\' Memento",',
])
c, ch = once(c, '    "Secret Rite Scroll",', add, "curation: extend QUESTLINE_DERANDO v4",
             "extras v4 (unplaced-audit"); changed |= ch
save(CUR, c)

# __init__.py -- add Shabriri Grape to tidy skip + precollect
i = load(INIT); NL = nl_of(i)
i, ch = once(i,
    '                        "Festering Bloody Finger x10", "Starlight Shards", "Seedbed Curse"):',
    '                        "Festering Bloody Finger x10", "Starlight Shards", "Seedbed Curse", "Shabriri Grape"):',
    "init: add Shabriri to tidy skip", '"Seedbed Curse", "Shabriri Grape"):'); changed |= ch
i, ch = once(i,
    '            for _ in range(5):' + NL + '                self.multiworld.push_precollected(self.create_item("Seedbed Curse"))',
    '            for _ in range(5):' + NL + '                self.multiworld.push_precollected(self.create_item("Seedbed Curse"))' + NL +
    '            for _ in range(3):' + NL + '                self.multiworld.push_precollected(self.create_item("Shabriri Grape"))',
    "init: add Shabriri precollect", 'self.create_item("Shabriri Grape")'); changed |= ch
save(INIT, i)

print("[OK] cleanup-batch4 applied." if changed else "[OK] already applied -- no changes.")
