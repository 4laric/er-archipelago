#!/usr/bin/env python3
# patch_apworld_numregions_survival_floor_and_dead_access_20260621.py
#
# TWO accessibility-aware fixes for region-sealed (num_regions / spine) seeds.
#
# (#1) SURVIVAL FLOOR. _spine_active seeds demote EVERY Miner's Bell Bearing and
#      Flask of Wondrous Physick to `useful` (lines ~687-692) to dodge a fill
#      overflow ("~15 progression items, no more spots"). But `useful` has NO
#      reachability guarantee, so in a tiny sealed pool they strand in other
#      worlds / sealed regions. Observed live 2026-06-20: a whole run with zero
#      flask upgrades and zero smithing bells. Fix: keep a small FLOOR reachable
#      as progression_skip_balancing (logic-placed, but skipped by the cross-player
#      balancing pass so the tiny pool does not overflow); demote the rest as before.
#
# (#2) DEAD-ACCESS SKIP. Pull region-access items whose gated content is unreachable
#      this seed so they stop occupying pool slots as dead weight:
#        - Pureblood Knight's Medal: promoted to progression ONLY under enable_dlc
#          (its entrance rules are all DLC-gated). With DLC OFF it is a plain warp
#          medal -> skip it from the pool. (With DLC ON it gates Altus/Caelid/Mohgwyn,
#          so it is load-bearing and left untouched.)
#        - Imbued Sword Key: gates only the Four Belfries waygates; skip when every
#          one of those destinations is sealed by the spine.
#
# RUN ON WINDOWS from the repo root:
#   python patch_apworld_numregions_survival_floor_and_dead_access_20260621.py
# Idempotent; aborts if an anchor moved. GEN-TEST a num_regions seed afterwards
# (sandbox can't run gen -- needs Python 3.11+).

import sys, io, os

DEFAULT = os.path.join("Archipelago", "worlds", "eldenring", "__init__.py")
MARKER  = "numregions_survival_floor"

# ---- (#1) survival floor: replace the blanket bell/flask demotion ----------------
ANCHOR_A = (
'            if getattr(self, "_spine_active", False):\n'
'                if self.options.smithing_bell_bearing_option.value == 1:\n'
'                    self.options.smithing_bell_bearing_option.value = 0\n'
'                for _rn in list(item_table):\n'
'                    if ("Miner\'s Bell Bearing" in _rn) or ("Flask of Wondrous Physick" in _rn):\n'
'                        item_table[_rn].classification = ItemClassification.useful'
)
BLOCK_A = (
'            if getattr(self, "_spine_active", False):\n'
'                if self.options.smithing_bell_bearing_option.value == 1:\n'
'                    self.options.smithing_bell_bearing_option.value = 0\n'
'                # accessibility floor (patch numregions_survival_floor): demoting ALL bells +\n'
'                # Flask of Wondrous Physick to useful left them with NO reachability guarantee, so\n'
'                # in a tiny sealed pool they strand in other worlds / sealed regions (observed sync\n'
'                # 2026-06-20: whole run with zero flask upgrades + zero smithing bells). Keep a small\n'
'                # FLOOR reachable as progression_skip_balancing (logic-placed, but skipped by the\n'
'                # cross-player balancing pass so the tiny pool does not overflow); demote the rest.\n'
'                _survival_floor = {\n'
'                    "Smithing-Stone Miner\'s Bell Bearing [1]",\n'
'                    "Smithing-Stone Miner\'s Bell Bearing [2]",\n'
'                    "Somberstone Miner\'s Bell Bearing [1]",\n'
'                    "Flask of Wondrous Physick",\n'
'                }\n'
'                for _rn in list(item_table):\n'
'                    if ("Miner\'s Bell Bearing" in _rn) or ("Flask of Wondrous Physick" in _rn):\n'
'                        if _rn in _survival_floor:\n'
'                            item_table[_rn].classification = ItemClassification.progression_skip_balancing\n'
'                            item_table[_rn].filler = False\n'
'                        else:\n'
'                            item_table[_rn].classification = ItemClassification.useful'
)

# ---- (#2) dead-access skip: insert after the dead-key rune block -----------------
ANCHOR_B = (
'                    item_table[_drn].filler = False\n'
'        if self.options.world_logic == "region_lock" or self.options.world_logic == "region_lock_bosses": # inject keys'
)
BLOCK_B = (
'                    item_table[_drn].filler = False\n'
'        # Accessibility-aware dead-access skip (patch numregions_survival_floor / dead_access):\n'
'        # drop region-access items whose gated content is unreachable this seed so they stop\n'
'        # occupying pool slots. Pureblood Knight\'s Medal is progression ONLY under enable_dlc\n'
'        # (entrance rules all DLC-gated); with DLC off it is a plain warp medal -> skip it. Imbued\n'
'        # Sword Key gates only the Four Belfries waygates; skip when every destination is sealed.\n'
'        _sealed_rr2 = getattr(self, "_spine_sealed_regions", set())\n'
'        if "Pureblood Knight\'s Medal" in item_table and not self.options.enable_dlc:\n'
'            item_table["Pureblood Knight\'s Medal"].skip = True\n'
'        if self.options.enable_dlc and "Imbued Sword Key" in item_table:\n'
'            _belfry_targets = {"The Four Belfries (Chapel of Anticipation)",\n'
'                               "The Four Belfries (Nokron)", "The Four Belfries (Farum Azula)",\n'
'                               "Ancient Ruins of Rauh"}\n'
'            if _belfry_targets <= _sealed_rr2:\n'
'                item_table["Imbued Sword Key"].skip = True\n'
'        if self.options.world_logic == "region_lock" or self.options.world_logic == "region_lock_bosses": # inject keys'
)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    if not os.path.isfile(path):
        print("ERROR: file not found:", path); return 2
    with io.open(path, "r", encoding="utf-8", newline="") as f:
        src = f.read()
    nl = "\r\n" if "\r\n" in src else "\n"
    body = src.replace("\r\n", "\n")
    if MARKER in body:
        print("ALREADY APPLIED (marker present) -- no change made."); return 0
    for tag, anc in (("A", ANCHOR_A), ("B", ANCHOR_B)):
        c = body.count(anc)
        if c != 1:
            print("ERROR: anchor %s found %d time(s) (expected 1). Aborting." % (tag, c)); return 3
    body = body.replace(ANCHOR_A, BLOCK_A, 1)
    body = body.replace(ANCHOR_B, BLOCK_B, 1)
    out = body.replace("\n", nl) if nl == "\r\n" else body
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    with io.open(path, "r", encoding="utf-8", newline="") as f:
        chk = f.read().replace("\r\n", "\n")
    ok = (MARKER in chk
          and "progression_skip_balancing" in chk
          and chk.count('Pureblood Knight\'s Medal"].skip = True') == 1)
    print("APPLIED." if ok else "WROTE FILE but verification FAILED -- inspect manually.")
    print("  marker present :", MARKER in chk)
    print("  newline style  :", "CRLF" if nl == "\r\n" else "LF")
    print("  bytes written  :", len(out))
    return 0 if ok else 5


if __name__ == "__main__":
    raise SystemExit(main())
