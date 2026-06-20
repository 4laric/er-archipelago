#!/usr/bin/env python3
r"""patch_apworld_spine_seal_bell_relief.py

Stop the fabricated smithing-bell gate from overflowing fill in num_regions / spine-seal seeds.

WHY
---
`smithing_bell_bearing_option == progression_randomize` adds entrance rules gating Altus / Capital
Outskirts / Flame Peak / Farum on Miner's Bell Bearings. That has NO basis in vanilla ER (bell
bearings are Twin-Maiden shop turn-ins, they never gate area access). The gate promotes the bell
bearings (incl. ~15 Progressive copies) to PROGRESSION; under a num_regions seal the kept pool is
~5 regions, and force-placing those bells (+ Progressive Physick) blows the fill:
    Fill.FillError: No more spots to place N items. Remaining locations are invalid.

FIX (spine-seal seeds only -- region_count / num_regions / messmer / godrick)
---
In the region_lock lock-injection block (where self._spine_active is live), when a seal is active:
- turn smithing_bell_bearing_option OFF (value 0) so the fabricated entrance rules never fire at
  set_rules time, and
- demote every "Miner's Bell Bearing" (discrete + Progressive) and "Flask of Wondrous Physick"
  item back to `useful`, so they stop competing for the scarce kept-region progression spots.

Safe: with the gate off, no logic references the bells, so can_beat_game doesn't need them (this is
the same reasoning as patch_apworld_softprog_bellgate_fix.py). Inert on non-seal seeds
(_spine_active is False). Glovewort Picker's bells are untouched ("Picker's", not "Miner's").

Run on Windows from repo root (or the eldenring apworld dir):
    python patch_apworld_spine_seal_bell_relief.py
CRLF-safe byte splice; idempotent.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CANDS = [HERE, os.path.join(HERE, "Archipelago", "worlds", "eldenring")]
PKG = next((d for d in CANDS if os.path.exists(os.path.join(d, "__init__.py"))
            and os.path.exists(os.path.join(d, "grace_data.py"))), None)
if not PKG:
    sys.exit("ERROR: eldenring apworld dir not found (run from repo root or the apworld dir).")
P = os.path.join(PKG, "__init__.py")

with open(P, "rb") as f:
    b = f.read()
nl = b"\r\n" if b"\r\n" in b else b"\n"
def conv(s): return s.replace("\n", nl.decode("ascii")).encode("utf-8")

MARKER = "spine seal: the smithing-bell entrance gate"
if MARKER.encode("utf-8") in b:
    print("  [skip] spine-seal bell relief already present.")
    sys.exit(0)

ANCHOR = conv("            # dlc_only + region_lock: Gravesite Plain is the DLC's free hub (you START there --\n")
if b.count(ANCHOR) != 1:
    sys.exit("  [FAIL] lock-injection anchor found %d times (expected 1); not modified." % b.count(ANCHOR))

INSERT = conv(
    "            # num_regions / spine seal: the smithing-bell entrance gate (Altus / Capital Outskirts /\n"
    "            # Flame Peak / Farum requiring Miner's Bell Bearings) is fabricated -- vanilla ER never\n"
    "            # gates area access on bell bearings -- and in a tiny sealed pool it force-places ~15\n"
    "            # progressive bells (+ progressive physick) as PROGRESSION, overflowing the fill\n"
    "            # (\"No more spots to place ...\"). For spine-seal seeds turn the smithing-bell option OFF\n"
    "            # (entrance rules won't fire) and demote the bells + Wondrous Physick back to useful.\n"
    "            # (patch_apworld_spine_seal_bell_relief.py)\n"
    "            if getattr(self, \"_spine_active\", False):\n"
    "                if self.options.smithing_bell_bearing_option.value == 1:\n"
    "                    self.options.smithing_bell_bearing_option.value = 0\n"
    "                for _rn in list(item_table):\n"
    "                    if (\"Miner's Bell Bearing\" in _rn) or (\"Flask of Wondrous Physick\" in _rn):\n"
    "                        item_table[_rn].classification = ItemClassification.useful\n"
)
b = b.replace(ANCHOR, INSERT + ANCHOR, 1)
with open(P, "wb") as f:
    f.write(b)
print("  [ok]   spine-seal bell relief added (gate off + bells/physick -> useful).")
print("DONE")
