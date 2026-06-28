#!/usr/bin/env python3
r"""patch_apworld_dead_natural_keys.py

Demote DEAD vanilla "natural-key" candidates (starting with Rusty Key) under a spine seal, so
they stop overflowing the tiny kept fill -- WITHOUT breaking the natural-locks feature.

WHY
---
A class of vanilla key items (Rusty Key, Irina's Letter, Academy Glintstone Key, the medallions,
Sewer-Gaol / Imbued Sword Keys, ...) are classification=progression and gate specific content via
entrance rules that are only added under certain options. When those conditions are off (or the
gated region is sealed by num_regions), the key gates nothing yet stays progression -> dead weight
that demands a reachable kept home and contributes to:
    Fill.FillError: No more spots to place N items.

Rusty Key specifically only gates Liurnia/Caelid entrance under early_legacy_dungeons (the vanilla
Stormveil-shortcut rule is commented out). With early_legacy_dungeons OFF it is pure dead progression.

CROSS-FEATURE SAFETY (natural-locks)
------------------------------------
The natural-locks feature (SPEC-natural-locks.md) re-purposes some of these very keys AS region
locks (e.g. Rusty Key -> Stormveil Lock). When that lands, the key becomes real, critical-path
progression and must NEVER be demoted. So the demotion is GUARDED on the item's `.lock` flag: if a
key is acting as a lock it is skipped, and this patch auto-disables for it the moment natural-locks
wires it up. Demotion keys on lock-status, never on the item name alone.

FIX
---
In the spine-seal demotion block (where Miner's Bell Bearings + Wondrous Physick are already demoted
under self._spine_active), demote Rusty Key to useful iff: not a lock, AND early_legacy_dungeons is
off, AND it is currently progression. Inert on non-spine seeds. Extend the guarded block with the
sibling natural-key candidates as each is confirmed dead + lock-guarded.

Run on Windows from repo root (or the eldenring apworld dir), AFTER the prior two patches:
    python patch_apworld_dead_natural_keys.py
CRLF-safe byte splice; idempotent; anchor is count-guarded.
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

MARKER = "patch_apworld_dead_natural_keys"
if MARKER.encode("utf-8") in b:
    print("  [skip] dead natural-key demotion already present.")
    sys.exit(0)

OLD = conv(
    "                    if (\"Miner's Bell Bearing\" in _rn) or (\"Flask of Wondrous Physick\" in _rn):\n"
    "                        item_table[_rn].classification = ItemClassification.useful\n"
)
NEW = conv(
    "                    if (\"Miner's Bell Bearing\" in _rn) or (\"Flask of Wondrous Physick\" in _rn):\n"
    "                        item_table[_rn].classification = ItemClassification.useful\n"
    "                # patch_apworld_dead_natural_keys: vanilla \"natural-key\" candidates that gate\n"
    "                # nothing in this config are dead progression -> they overflow the tiny kept fill.\n"
    "                # Demote to useful, but GUARD on .lock so this auto-disables the moment natural-locks\n"
    "                # wires the key AS a region lock (then it's real progression, never demote). Rusty Key\n"
    "                # only gates Liurnia/Caelid entrance under early_legacy_dungeons; dead when that's off.\n"
    "                # First of the class -- Irina's Letter, Academy Glintstone Key, the medallions,\n"
    "                # Sewer-Gaol / Imbued Sword Keys are siblings; add each once confirmed dead + guarded.\n"
    "                _rk = item_table.get(\"Rusty Key\")\n"
    "                if (_rk is not None and not getattr(_rk, \"lock\", False)\n"
    "                        and not self.options.early_legacy_dungeons\n"
    "                        and _rk.classification == ItemClassification.progression):\n"
    "                    _rk.classification = ItemClassification.useful\n"
    "                    _rk.filler = False\n"
)
n = b.count(OLD)
if n != 1:
    sys.exit("  [FAIL] spine-seal demotion anchor found %d times (expected 1); not modified." % n)
b = b.replace(OLD, NEW)

with open(P, "wb") as f:
    f.write(b)
print("  [ok] dead natural-key demotion (Rusty Key, lock-guarded) applied to %s" % P)
