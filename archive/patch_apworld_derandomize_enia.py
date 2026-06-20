#!/usr/bin/env python3
r"""patch_apworld_derandomize_enia.py

Give the Enia remembrance shop the "Gurranq treatment": when it's derandomized, drop the Remembrance
items from the pool (they gate nothing, so they were dead progression clogging the fill). Plus a
companion drop of Rusty Key when it gates nothing.

WHY
---
Remembrance items (Remembrance of the Grafted / Starscourge / ... / Elden Remembrance) are NOT
referenced by any `state.has(...)` rule -- the Enia turn-in CHECKS are gated on reaching the boss
drop + great runes, not on holding the remembrance. So the remembrances are progression-CLASSIFIED
but redundant, and in a num_regions seal the priority/progression fill force-places them into the
scarce kept pool -> "No more spots to place N items". When the Enia shop is derandomized
(randomize_enia off) its turn-in slots are already non-checks (see _in_location_pool), so the
remembrances have no reason to exist in the pool either. Mirror derandomize_gurranq's Deathroot skip.

Rusty Key gates Liurnia / Caelid / Stormveil ONLY under early_legacy_dungeons; with that option off
it is referenced by no rule -> the same dead-progression clog. Drop it too.

FIX
---
- not randomize_enia        -> item_table["<every Remembrance>"].skip = True
- not early_legacy_dungeons -> item_table["Rusty Key"].skip = True

Inserted right after the derandomize_gurranq Deathroot skip. Both are plain option toggles (general,
not seal-gated) -- skipping a dead item is always safe since nothing requires it.

REMEMBER to set `randomize_enia: false` in the yaml to engage the remembrance drop.

Run on Windows from repo root:  python patch_apworld_derandomize_enia.py
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

MARKER = "Enia \"Gurranq treatment\""
if MARKER.encode("utf-8") in b:
    print("  [skip] derandomize-enia remembrance drop already present.")
    sys.exit(0)

ANCHOR = conv('            if "Deathroot" in item_table: item_table["Deathroot"].skip = True\n')
if b.count(ANCHOR) != 1:
    sys.exit("  [FAIL] derandomize_gurranq anchor found %d times (expected 1); not modified." % b.count(ANCHOR))

INSERT = conv(
    "        # Enia \"Gurranq treatment\" (Alaric): Remembrance items are referenced by NO state.has rule\n"
    "        # -- the Enia turn-in checks gate on reaching the boss drop + great runes, not on holding the\n"
    "        # remembrance -- so they're progression-classified but redundant and force-fill a scarce kept\n"
    "        # pool. When the Enia shop is derandomized its turn-in slots are already non-checks, so drop\n"
    "        # the remembrances from the pool too (mirrors the Deathroot skip above).\n"
    "        if not self.options.randomize_enia:\n"
    "            for _rememb in list(item_table):\n"
    "                if \"Remembrance\" in _rememb:\n"
    "                    item_table[_rememb].skip = True\n"
    "        # Rusty Key gates Liurnia/Caelid/Stormveil ONLY under early_legacy_dungeons; with that off it\n"
    "        # references no rule -> dead progression. Drop it so it doesn't clog the fill.\n"
    "        if not self.options.early_legacy_dungeons and \"Rusty Key\" in item_table:\n"
    "            item_table[\"Rusty Key\"].skip = True\n"
)
b = b.replace(ANCHOR, ANCHOR + INSERT, 1)
with open(P, "wb") as f:
    f.write(b)
print("  [ok]   remembrances dropped when randomize_enia off; Rusty Key dropped when early_legacy off.")
print("DONE")
