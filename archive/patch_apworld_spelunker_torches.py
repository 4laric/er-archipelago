#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
patch_apworld_spelunker_torches.py

Reskin each opt-in caves/underground BUNDLE region-lock item into a usable TORCH
weapon. The lock's AP item NAME is the cross-file key (items.py / grace_data.py /
map_region_data.py / __init__.py all reference the literal string), so renaming a lock
means rewriting EVERY occurrence of that string. We also flip the item's ERItemData from
GOODS er_code 99999 (sentinel) to WEAPON er_code = the torch's EquipParamWeapon id, so the
existing grant path hands the player a real torch while the (renamed) name still keys the
bundle unlock.

GRANT MECHANISM (verified in __init__.py fill_slot_data):
    category_nibbles = {GOODS: 0x40000000, WEAPON: 0x00000000, ARMOR: 0x10000000, ...}
    ap_ids_to_er_ids[ap_code] = er_code | category_nibbles[item.category]
  A WEAPON item with er_code 24000000 packs to FullID 24000000 (weapon nibble = 0), i.e.
  the raw EquipParamWeapon id, which the client's GrantFullID grants as that weapon. So a
  WEAPON-category er_code equal to the EquipParamWeapon id IS the correct weapon FullID form.
  (The line `if item.er_code:` keeps the item in the map -- 24xxxxxx is truthy.)

CONVENTIONS: CRLF-safe (read/write bytes, newline-preserving), backs up to <file>.bak_<tag>,
asserts anchors present, idempotent via an applied-marker probe, raises on missing anchor.

Run on Windows:  python patch_apworld_spelunker_torches.py
"""

import os
import sys

TAG = "spelunkertorch"
APWORLD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "Archipelago", "worlds", "eldenring")

# lock item NAME -> (new torch name, EquipParamWeapon id).
# Confirmed locks present in live source: Limgrave Underground / Liurnia Caves / Altus Caves /
# Mountaintops Caves / Shadow Catacombs (the DLC catacombs bundle, key dlc_catacombs).
TORCHES = {
    "Limgrave Underground Lock": ("Spelunker's Torch",                 24000000),
    "Liurnia Caves Lock":        ("Spelunker's Ghostflame Torch",      24050000),
    "Altus Caves Lock":          ("Spelunker's Steel-Wire Torch",      24020000),
    "Mountaintops Caves Lock":   ("Spelunker's Beast-Repellent Torch", 24060000),
    "Shadow Catacombs Lock":     ("Spelunker's Messmerflame Torch",    24500000),
}

# Files in which the lock NAME literal can appear (cross-file rename targets).
NAME_FILES = ["items.py", "grace_data.py", "map_region_data.py", "__init__.py"]


def _read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def _write_bytes(path, data):
    with open(path, "wb") as f:
        f.write(data)


def _backup(path):
    bak = path + ".bak_" + TAG
    if not os.path.exists(bak):
        _write_bytes(bak, _read_bytes(path))
        print("  backup -> %s" % os.path.basename(bak))


def main():
    if not os.path.isdir(APWORLD):
        print("ERROR: apworld dir not found: %s" % APWORLD)
        sys.exit(1)

    items_path = os.path.join(APWORLD, "items.py")
    items_src = _read_bytes(items_path).decode("utf-8")

    # ---- idempotency probe: if any new torch name is already present in items.py, bail. ----
    already = [n for (n, _c) in TORCHES.values() if n in items_src]
    if already:
        print("already applied (found torch name(s) in items.py): %s" % ", ".join(already))
        return

    # ---- discover which locks are actually present (by their ERItemData line in items.py) ----
    # The defining line is GOODS + 99999 + lock=True; that's the anchor we rewrite per-item.
    def items_anchor(lock_name):
        return ('ERItemData("%s", 99999, ERItemCategory.GOODS, '
                'classification=ItemClassification.progression, lock=True)' % lock_name)

    present = []
    missing = []
    for lock in TORCHES:
        if items_anchor(lock) in items_src:
            present.append(lock)
        else:
            missing.append(lock)
    if missing:
        print("NOTE: lock(s) not found in items.py (skipped, not renamed): %s"
              % ", ".join(missing))
    if not present:
        print("ERROR: no target lock items found in items.py; nothing to do.")
        sys.exit(1)

    counts = {}  # (file, lock) -> name-occurrence count

    # ---- pass 1: items.py -- rewrite the defining ERItemData line (category+er_code) ----
    new_items_src = items_src
    for lock in present:
        new_name, weapon_id = TORCHES[lock]
        old_line = items_anchor(lock)
        new_line = ('ERItemData("%s", %d, ERItemCategory.WEAPON, '
                    'classification=ItemClassification.progression, lock=True)'
                    % (new_name, weapon_id))
        if old_line not in new_items_src:
            raise RuntimeError("items.py anchor vanished mid-pass for %r" % lock)
        # exactly one defining line expected
        n = new_items_src.count(old_line)
        if n != 1:
            raise RuntimeError("items.py defining line for %r found %d times (expected 1)"
                               % (lock, n))
        new_items_src = new_items_src.replace(old_line, new_line)

    # ---- pass 2 (items.py): rename any *remaining* literal occurrences of the lock NAME ----
    # (e.g. references elsewhere in items.py). The defining line already carries the new name,
    # so this only touches leftover "<lock name>" literals.
    for lock in present:
        new_name, _ = TORCHES[lock]
        lit = '"%s"' % lock
        c = new_items_src.count(lit)
        counts[("items.py", lock)] = c
        if c:
            new_items_src = new_items_src.replace(lit, '"%s"' % new_name)

    _backup(items_path)
    _write_bytes(items_path, new_items_src.encode("utf-8"))
    print("patched items.py")

    # ---- pass 3: the other files -- pure NAME-literal replacement ----
    for fname in NAME_FILES:
        if fname == "items.py":
            continue
        path = os.path.join(APWORLD, fname)
        if not os.path.exists(path):
            print("  NOTE: %s not present, skipped" % fname)
            continue
        src = _read_bytes(path).decode("utf-8")
        new_src = src
        touched = False
        for lock in present:
            new_name, _ = TORCHES[lock]
            lit = '"%s"' % lock
            c = new_src.count(lit)
            counts[(fname, lock)] = c
            if c:
                new_src = new_src.replace(lit, '"%s"' % new_name)
                touched = True
        if touched:
            _backup(path)
            _write_bytes(path, new_src.encode("utf-8"))
            print("patched %s" % fname)
        else:
            print("  no name literals in %s (nothing to do)" % fname)

    # ---- report ----
    print("\n=== rename occurrence counts (name-literal replacements) ===")
    for fname in NAME_FILES:
        for lock in present:
            key = (fname, lock)
            if key in counts:
                print("  %-18s | %-26s | %d" % (fname, lock, counts[key]))
    print("\n=== items.py defining lines rewritten -> WEAPON ===")
    for lock in present:
        nm, wid = TORCHES[lock]
        print("  %-26s -> %-34s (EquipParamWeapon %d, FullID %d)"
              % (lock, nm, wid, wid))
    print("\nDONE. Re-bake/regen on Windows to pick up the new pool.")


if __name__ == "__main__":
    main()
