#!/usr/bin/env python3
r"""
patch_apworld_fold_volcano_into_gelmir.py  (run on Windows from repo root)  -- v2, EOL-agnostic

Folds "Volcano Lock" into "Mt. Gelmir Lock" (Volcano Manor becomes part of the Mt. Gelmir region-lock).
Volcano Lock was never physically enforced, so it only added a redundant logical gate + a dead pool
item. Mt. Gelmir Lock already blooms Volcano Manor's graces (natural_key_triggers clause), so coverage
is unchanged. Three edits across three files:
  1. __init__.py     -- gate Volcano Manor Entrance/Dungeon on Mt. Gelmir Lock (was Volcano Lock).
  2. region_spine.py -- drop Volcano Lock from SPINE step 8's lock set.
  3. items.py        -- Volcano Lock lock=True -> lock=False (no longer injected).

v2: matches LINE CONTENT (no trailing newline), so it works whether a file is CRLF or LF -- region_spine.py
is LF while __init__.py/items.py are CRLF. Idempotent; asserts each anchor; no write on mismatch.
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
EL = os.path.join(ROOT, "Archipelago", "worlds", "eldenring")
INIT = os.path.join(EL, "__init__.py")
ITEMS = os.path.join(EL, "items.py")
SPINE = os.path.join(EL, "region_spine.py")


def _read(p):
    with open(p, "rb") as f:
        return f.read()


def _write(p, d):
    with open(p, "wb") as f:
        f.write(d)


def _one(path, old, new, label, done_marker):
    """Replace exactly one occurrence of byte-string `old` (line content, no EOL) with `new`."""
    if not os.path.isfile(path):
        raise SystemExit(f"[FAIL] not found: {path}")
    data = _read(path)
    if done_marker in data:
        print(f"[skip] {label}: already folded.")
        return
    n = data.count(old)
    if n != 1:
        raise SystemExit(f"[FAIL] {label}: anchor x{n} (want 1). No write.")
    _write(path, data.replace(old, new, 1))
    print(f"[ok] {label}.")


def main():
    _one(INIT,
         b'self._add_entrance_rule("Volcano Manor Entrance", "Volcano Lock")',
         b'self._add_entrance_rule("Volcano Manor Entrance", "Mt. Gelmir Lock")  # folded: Volcano Manor is part of Mt. Gelmir',
         "__init__ Volcano Manor Entrance rule",
         b'"Volcano Manor Entrance", "Mt. Gelmir Lock"')
    _one(INIT,
         b'self._add_entrance_rule("Volcano Manor Dungeon", "Volcano Lock")',
         b'self._add_entrance_rule("Volcano Manor Dungeon", "Mt. Gelmir Lock")  # folded: Volcano Manor is part of Mt. Gelmir',
         "__init__ Volcano Manor Dungeon rule",
         b'"Volcano Manor Dungeon", "Mt. Gelmir Lock"')
    _one(SPINE,
         b'"locks": {"Mt. Gelmir Lock", "Volcano Lock"},',
         b'"locks": {"Mt. Gelmir Lock"},  # Volcano Lock folded into Mt. Gelmir Lock',
         "region_spine step-8 locks",
         b'# Volcano Lock folded into Mt. Gelmir Lock')
    _one(ITEMS,
         b'ERItemData("Volcano Lock", 99999, ERItemCategory.GOODS, classification=ItemClassification.progression, lock=True),',
         b'ERItemData("Volcano Lock", 99999, ERItemCategory.GOODS, classification=ItemClassification.progression, lock=False),  # folded into Mt. Gelmir Lock',
         "items.py Volcano Lock lock=False",
         b'lock=False),  # folded into Mt. Gelmir Lock')


if __name__ == "__main__":
    main()
