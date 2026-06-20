#!/usr/bin/env python3
r"""patch_apworld_dragonbarrow_lock_grace.py

Wire Dragonbarrow as a first-class warp-access region so num_regions_chain (and warp seeds
generally) can reach it on its own Dragonbarrow Lock instead of only geographically via Caelid.

ROOT CAUSE
----------
grace_data.py is AUTO-GENERATED and groups graces by m60 overworld tile. Dragonbarrow shares
Caelid's m60 tiles, so the generator pooled Dragonbarrow's NE-corner graces (m60_50_36 / m60_51_36
= flags 76417, 76419, 76420 -- the Bestial Sanctum cluster outside Gurranq) INTO 'Caelid', and
never gave Dragonbarrow a REGION_LOCK_ITEM entry. Result: the `_region_lock_warp_access` loop
(which iterates REGION_LOCK_ITEM) makes no `Warp To Dragonbarrow`, so under warp access a kept
Dragonbarrow is unreachable unless Caelid is also kept and walked into.

THE FIX (grace_data.py only)
----------------------------
1. REGION_LOCK_ITEM += 'Dragonbarrow': 'Dragonbarrow Lock'  -> warp loop now wires Dragonbarrow,
   and the client lights its graces on Dragonbarrow Lock receipt via the normal
   REGION_GRACE_POINTS -> REGION_LOCK_ITEM path.
2. MOVE the 3 NE-corner graces (76417, 76419, 76420) out of 'Caelid' into a new 'Dragonbarrow'
   REGION_GRACE_POINTS entry. Moving (not copying) is required: if they stayed under Caelid,
   receiving Caelid Lock would light Dragonbarrow's graces and let you warp in without its lock,
   breaking the chain gate.

Net: Dragonbarrow gets its own lock-gated warp + Bestial-Sanctum-area grace bundle; Caelid Lock no
longer opens Dragonbarrow. The Dragonbarrow ENTRANCE RULE (`_add_entrance_rule("Dragonbarrow",
"Dragonbarrow Lock")`) already exists in __init__.py, so gen logic is unchanged.

Run on Windows from repo root (or anywhere the apworld is locatable):
    python patch_apworld_dragonbarrow_lock_grace.py

CRLF-safe byte splice; idempotent. NOTE: grace_data.py is auto-generated -- if it is ever
regenerated from grace_flags.tsv, the generator's tile->region assignment must make the same
Dragonbarrow split or this reverts (same tile->region map Track C needs).
"""
import os, sys

# Locate grace_data.py WITHOUT a bare-CWD fallback (that footgun has written real source before).
HERE = os.path.dirname(os.path.abspath(__file__))
CANDS = [HERE, os.path.join(HERE, "Archipelago", "worlds", "eldenring")]
PKG = next((d for d in CANDS if os.path.exists(os.path.join(d, "grace_data.py"))), None)
if not PKG:
    sys.exit("ERROR: grace_data.py not found (run from repo root or the eldenring apworld dir).")
P = os.path.join(PKG, "grace_data.py")

with open(P, "rb") as f:
    b = f.read()
nl = b"\r\n" if b"\r\n" in b else b"\n"
def conv(s): return s.replace("\n", nl.decode("ascii")).encode("utf-8")

if b"'Dragonbarrow':" in b:
    print("  [skip] grace_data.py already has a Dragonbarrow entry.")
    sys.exit(0)

# 1) REGION_LOCK_ITEM: insert after the Deeproot Depths LOCK line (alpha order; unique anchor --
#    the grace dict's Deeproot line ends in '[[', this one in the lock string).
lock_anchor = conv("    'Deeproot Depths': 'North Underground Lock',\n")
lock_insert = conv("    'Dragonbarrow': 'Dragonbarrow Lock',\n")
if b.count(lock_anchor) != 1:
    sys.exit(f"  [FAIL] REGION_LOCK_ITEM anchor found {b.count(lock_anchor)}x (expected 1); not modified.")
b = b.replace(lock_anchor, lock_anchor + lock_insert, 1)

# 2) Remove the 3 Dragonbarrow graces from the Caelid REGION_GRACE_POINTS line (keep 76416/76418/76450).
moves = [
    "[76417, 12731.7, 9133.2], ",
    "[76419, 13137.6, 9234.9], ",
    "[76420, 13149.1, 9175.8], ",
]
for m in moves:
    mb = conv(m)
    if b.count(mb) != 1:
        sys.exit(f"  [FAIL] Caelid grace fragment {m!r} found {b.count(mb)}x (expected 1); not modified.")
    b = b.replace(mb, b"", 1)

# 3) Insert the new Dragonbarrow REGION_GRACE_POINTS entry before 'Enir Ilim' (alpha order).
grace_anchor = conv("    'Enir Ilim': [[")
grace_insert = conv("    'Dragonbarrow': [[76417, 12731.7, 9133.2], [76419, 13137.6, 9234.9], [76420, 13149.1, 9175.8]],\n")
if b.count(grace_anchor) != 1:
    sys.exit(f"  [FAIL] REGION_GRACE_POINTS 'Enir Ilim' anchor found {b.count(grace_anchor)}x (expected 1); not modified.")
b = b.replace(grace_anchor, grace_insert + grace_anchor, 1)

with open(P, "wb") as f:
    f.write(b)
print("  [ok]   Dragonbarrow added to REGION_LOCK_ITEM + REGION_GRACE_POINTS (3 graces moved from Caelid).")
print("DONE")
