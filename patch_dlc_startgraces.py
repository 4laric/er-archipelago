#!/usr/bin/env python3
"""
Emit slot_data "startGraces" so the DLC hub (Gravesite Plain) is warpable from LOAD under dlc_only.

WHY: in dlc_only the Gravesite Lock is precollected, but the client receives precollected locks with
UNRESOLVED names ("Unknown from Server"), so the on-receipt regionGraces/regionOpenFlags/lockRevealFlags
handlers (all keyed by item NAME) miss and the grace flags are never set. The DLC map flags DO get set
(reveal_all_maps, flag-based) -- which is why the map fog appears but there is no Gravesite Plain grace to
warp to. The client ALREADY has a flag-based, name-independent "startGraces" consumer
(ArchipelagoInterface.cpp ~160 -> pendingGraceFlags -> SetEventFlag at load). This patch feeds it the CT
"Unlock DLC Maps" flags (62080-62084) + "Unlock DLC Graces / Gravesite Plain" flags (76800+), so the whole
hub lights up at load. APWORLD-ONLY -- no client rebuild; just regenerate the seed and reconnect.

RUN ON WINDOWS (the sandbox mount phantom-truncates __init__.py; run with real Python):
  cd C:\\Users\\alari\\Documents\\er-archipelago
  python patch_dlc_startgraces.py
  .\\build.ps1 -Generate        # then restart the server on the new zip + reconnect

Safe: backs up the file, asserts both anchors match exactly once, preserves line endings, byte-compiles,
self-restores on failure, refuses to write if already patched.
"""
import os, sys, py_compile, shutil

P = os.path.join("Archipelago", "worlds", "eldenring", "__init__.py")
if not os.path.exists(P):
    print(f"!! {P} not found -- run from the repo root (er-archipelago)."); sys.exit(1)

with open(P, "r", encoding="utf-8", newline="") as f:
    s = f.read()

for sentinel in ('"regionOpenFlags": region_open_flags', "def fill_slot_data", "REGION_GRACE_POINTS"):
    if sentinel not in s:
        print(f"!! integrity check failed ('{sentinel}' missing) -- run this on Windows (real disk)."); sys.exit(2)

if '"startGraces"' in s:
    print("Already patched (startGraces present). Nothing to do."); sys.exit(0)

N = "\r\n" if "\r\n" in s else "\n"
orig = len(s)

def rep(s, old, new, label):
    c = s.count(old)
    if c != 1:
        print(f"!! {label}: expected 1 anchor, found {c}. Aborting (no write)."); sys.exit(3)
    return s.replace(old, new)

# Edit 1: build start_graces just before the slot_data dict literal
anchor1 = ("            lock_notify_items = {_lk: (_c | 0x40000000) for _lk, _c in _tmp.items()}" + N +
           "        slot_data = {" + N)
block1 = ("            lock_notify_items = {_lk: (_c | 0x40000000) for _lk, _c in _tmp.items()}" + N +
          "        # Start graces (load-time, FLAG-based -- not name-keyed): the client sets these at" + N +
          "        # load via its startGraces consumer, independent of item-name resolution. Needed" + N +
          "        # because precollected locks arrive name-UNRESOLVED ('Unknown from Server'), so the" + N +
          "        # on-receipt regionGraces path never fires. Under dlc_only this ports the CT" + N +
          "        # 'Unlock DLC Maps' (62080-62084) + 'Unlock DLC Graces / Gravesite Plain' (76800+)" + N +
          "        # so the Land-of-Shadow hub is warpable from load (no Mohg+Radahn route needed)." + N +
          "        start_graces = []" + N +
          "        if self.options.dlc_only and self.options.world_logic < 3:" + N +
          "            start_graces = [62080, 62081, 62082, 62083, 62084]" + N +
          "            start_graces += [int(_p[0]) for _p in REGION_GRACE_POINTS.get(\"Gravesite Plain\", [])]" + N +
          "            start_graces = sorted(set(int(_f) for _f in start_graces))" + N +
          "        slot_data = {" + N)
s = rep(s, anchor1, block1, "E1 build start_graces")

# Edit 2: add the slot_data key
anchor2 = '            "regionOpenFlags": region_open_flags,' + N
block2 = ('            "regionOpenFlags": region_open_flags,' + N +
          "            # Load-time grace flags (see build above): fixes the precollected-lock name miss;" + N +
          "            # under dlc_only ports the CT DLC map+grace unlock so Gravesite Plain warps from load." + N +
          '            "startGraces": start_graces,' + N)
s = rep(s, anchor2, block2, "E2 slot_data key")

bak = P + ".bak_startgraces"
shutil.copy2(P, bak)
with open(P, "w", encoding="utf-8", newline="") as f:
    f.write(s)

chk = open(P, "r", encoding="utf-8", newline="").read()
if not all(x in chk for x in ('"startGraces": start_graces', "start_graces = []", "def fill_slot_data", "return slot_data")):
    print("!! post-write sanity failed; restoring backup."); shutil.copy2(bak, P); sys.exit(4)
try:
    py_compile.compile(P, doraise=True)
except py_compile.PyCompileError as e:
    print("!! byte-compile FAILED; restoring backup.\n", e); shutil.copy2(bak, P); sys.exit(5)

for root, _d, files in os.walk(os.path.join("Archipelago", "worlds", "eldenring")):
    if os.path.basename(root) == "__pycache__":
        for fn in files:
            try: os.remove(os.path.join(root, fn))
            except OSError: pass

print(f"OK: patched {P} ({orig} -> {len(s)} chars). Backup {bak}. Bytecode purged.")
print("Next: .\\build.ps1 -Generate, restart the server on the new AP_*.zip, reconnect.")
