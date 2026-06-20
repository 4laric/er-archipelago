#!/usr/bin/env python3
r"""patch_apworld_spine_seal_bypass_keys.py

Drop redundant VANILLA BYPASS KEYS from the pool in num_regions / spine-seal seeds so they stop
force-overflowing the fill.

WHY
---
Keys like the Dectus Medallion gate a GEOGRAPHIC path to a region (Grand Lift of Dectus -> Altus),
but under region_access=warp that region also has a lock-warp entrance (Altus Lock), so the key is
disjunctively redundant -- you reach the region on the lock alone. For SEALED regions the key is
moot entirely. Yet the key stays PROGRESSION-classified, so the priority/progression fill force-
places it into the ~5-region kept pool and contributes to:
    Fill.FillError: No more spots to place N items.

FIX (spine-seal seeds only)
---
In the region_lock lock-injection block (self._spine_active live), drop (inject=False, like a sealed
lock -> create_items backfills the slot with filler) each bypass key whose EVERY gated region is:
  - sealed by the cut (_spine_sealed_regions), OR
  - warp-superseded (region_access=warp AND the region has its own lock in REGION_LOCK_ITEM).

NOT included: Academy Glintstone Key. Raya Lucaria has no warp, so the key genuinely gates Rennala /
Great Rune of the Unborn when Liurnia is a kept rune region -- dropping it would break that seed.

Pairs with patch_apworld_spine_seal_bell_relief.py (same block; order-independent). Inert on non-
seal seeds. Run on Windows from repo root:  python patch_apworld_spine_seal_bypass_keys.py
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

MARKER = "spine seal: VANILLA BYPASS KEYS"
if MARKER.encode("utf-8") in b:
    print("  [skip] spine-seal bypass-key drop already present.")
    sys.exit(0)

ANCHOR = conv("            # dlc_only + region_lock: Gravesite Plain is the DLC's free hub (you START there --\n")
if b.count(ANCHOR) != 1:
    sys.exit("  [FAIL] lock-injection anchor found %d times (expected 1); not modified." % b.count(ANCHOR))

INSERT = conv(
    "            # num_regions / spine seal: VANILLA BYPASS KEYS are disjunctive with region locks under\n"
    "            # warp (you reach Altus on Altus Lock, not the Dectus lift) and moot for SEALED regions,\n"
    "            # yet stay PROGRESSION-classified so the fill force-places them into the scarce kept pool.\n"
    "            # Drop a bypass key when EVERY region it gates is sealed OR warp-superseded (kept + has a\n"
    "            # region lock under warp). Academy Glintstone Key is excluded: Raya Lucaria has no warp,\n"
    "            # so it genuinely gates Rennala when Liurnia is kept. (patch_apworld_spine_seal_bypass_keys.py)\n"
    "            if getattr(self, \"_spine_active\", False):\n"
    "                _bk_sealed = getattr(self, \"_spine_sealed_regions\", set())\n"
    "                _bk_warp = self.options.region_access == \"warp\"\n"
    "                _BYPASS_KEYS = {\n"
    "                    \"Dectus Medallion (Left)\": [\"Altus Plateau\"],\n"
    "                    \"Dectus Medallion (Right)\": [\"Altus Plateau\"],\n"
    "                    \"Rold Medallion\": [\"Mountaintops of the Giants\", \"Consecrated Snowfield\"],\n"
    "                    \"Haligtree Secret Medallion (Left)\": [\"Hidden Path to the Haligtree\"],\n"
    "                    \"Haligtree Secret Medallion (Right)\": [\"Hidden Path to the Haligtree\"],\n"
    "                    \"Imbued Sword Key\": [\"The Four Belfries (Chapel of Anticipation)\",\n"
    "                                         \"The Four Belfries (Nokron)\", \"The Four Belfries (Farum Azula)\"],\n"
    "                }\n"
    "                for _bk, _brs in _BYPASS_KEYS.items():\n"
    "                    if _bk not in item_table:\n"
    "                        continue\n"
    "                    if all((_r in _bk_sealed) or (_bk_warp and _r in REGION_LOCK_ITEM and _r not in _bk_sealed)\n"
    "                           for _r in _brs):\n"
    "                        item_table[_bk].inject = False\n"
)
b = b.replace(ANCHOR, INSERT + ANCHOR, 1)
with open(P, "wb") as f:
    f.write(b)
print("  [ok]   spine-seal bypass-key drop added (Dectus/Rold/Haligtree/Imbued when sealed or warp-superseded).")
print("DONE")
