#!/usr/bin/env python3
"""
patch_apworld_random_start_roundtable_hub.py -- re-root the warp graph onto Roundtable Hold under
random_start_region, demoting Limgrave to a normal locked region. SPEC-random-start-roundtable-hub.md.

GATED ENTIRELY on self._random_start_region (set by patch_apworld_random_start.py). Normal seeds and
non-random-start region_lock seeds are byte-for-byte unaffected (all new branches are inert).

items.py:
  + "Limgrave Lock" region-lock item (like Caelid Lock).
__init__.py:
  A) generate_early random-start block: default Limgrave Lock inject=False (so it's NOT a dead
     progression item on ordinary seeds)...
  B) ...and inject=True once a start region is actually rolled (Limgrave joins the pool like any region).
  C) create_regions: New Game roots at Roundtable Hold (not Limgrave) under random_start.
  D) _region_lock_warp_access: warp hub = Roundtable (not Limgrave); + a hub->Limgrave warp gated on
     Limgrave Lock (Limgrave isn't in REGION_LOCK_ITEM, so the main loop skips it).

v1 = LOGIC-ONLY (no areaLockFlags entry for Limgrave -> no physical kick yet; needs the Limgrave
area-id capture to go hard). region_count combo is already skipped by the random-start block
(_spine_active guard), so the spine's "Limgrave = step 1" assumption is untouched.

GEN-TEST (the point of this draft): assert solvable for each overworld start; assert Limgrave Lock in
pool; assert hub=Roundtable; watch for any region reachable ONLY via a geographic edge from Limgrave
with no warp entrance (would now be stranded behind Limgrave Lock) -- the one real risk.

Run on Windows. Idempotent. Binary I/O preserves CRLF (both files are CRLF).
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
ITEMS = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "items.py")
INIT = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "__init__.py")


def _read(p):
    with open(p, "rb") as f:
        return f.read()


def _write(p, d):
    with open(p, "wb") as f:
        f.write(d)


def _crlf(t):
    return t.replace("\n", "\r\n").encode("utf-8")


def _after(data, anchor, ins, label):
    if data.count(anchor) != 1:
        raise SystemExit(f"[FAIL] {label}: anchor x{data.count(anchor)} (want 1). No write.")
    return data.replace(anchor, anchor + ins, 1)


def _replace(data, anchor, repl, label):
    if data.count(anchor) != 1:
        raise SystemExit(f"[FAIL] {label}: anchor x{data.count(anchor)} (want 1). No write.")
    return data.replace(anchor, repl, 1)


# ---------------- items.py ----------------
ITEMS_ANCHOR = _crlf('    ERItemData("Weeping Lock", 99999, ERItemCategory.GOODS, classification=ItemClassification.progression, lock=True),\n')
ITEMS_INS = _crlf('    ERItemData("Limgrave Lock", 99999, ERItemCategory.GOODS, classification=ItemClassification.progression, lock=True),  # random_start_region: demotes Limgrave to a normal locked region (Roundtable is the hub). SPEC-random-start-roundtable-hub.md\n')

# ---------------- __init__.py: A) default Limgrave Lock OFF ----------------
A_ANCHOR = _crlf("        self._random_start_region = None\n")
A_INS = _crlf('''\
        # Roundtable-hub re-root (SPEC-random-start-roundtable-hub.md): Limgrave Lock is a real region
        # lock but only LIVE under random_start -- default it out of the pool so ordinary region_lock
        # seeds don't carry a progression item that gates nothing. Re-enabled below when a start rolls.
        if "Limgrave Lock" in item_table:
            item_table["Limgrave Lock"].inject = False
''')

# ---------------- __init__.py: B) re-enable Limgrave Lock when a start is rolled ----------------
B_ANCHOR = _crlf("                    self._random_start_region = _choice\n")
B_INS = _crlf('''\
                    # Roundtable-hub re-root: Limgrave is no longer the free hub -- inject its lock so
                    # it joins the pool like any region (hub moves to Roundtable in create_regions /
                    # _region_lock_warp_access). SPEC-random-start-roundtable-hub.md.
                    if "Limgrave Lock" in item_table:
                        item_table["Limgrave Lock"].inject = True
''')

# ---------------- __init__.py: C) New Game roots at Roundtable ----------------
C_OLD = _crlf('        self.multiworld.get_entrance("New Game", self.player).connect(regions["Limgrave"])\n')
C_NEW = _crlf('''\
        # Roundtable-hub re-root (SPEC-random-start-roundtable-hub.md): under random_start the
        # hub/logic-root is Roundtable Hold (always-open interior), not Limgrave; Limgrave is reached
        # via a lock-gated Warp To Limgrave (see _region_lock_warp_access). Normal seeds: unchanged.
        _ng_root = "Roundtable Hold" if getattr(self, "_random_start_region", None) else "Limgrave"
        self.multiworld.get_entrance("New Game", self.player).connect(regions[_ng_root])
''')

# ---------------- __init__.py: D1) warp hub = Roundtable ----------------
D1_OLD = _crlf('        limgrave = self.get_region("Limgrave")\n')
D1_NEW = _crlf('''\
        # Roundtable-hub re-root: under random_start the warp hub is Roundtable (Limgrave is now a
        # locked region, reached via its own Warp To Limgrave added below). Variable kept named
        # `limgrave` so the rest of this method is untouched. SPEC-random-start-roundtable-hub.md.
        _hub = "Roundtable Hold" if getattr(self, "_random_start_region", None) else "Limgrave"
        limgrave = self.get_region(_hub)
''')

# ---------------- __init__.py: D2) add hub->Limgrave warp gated on Limgrave Lock ----------------
D2_ANCHOR = _crlf("        # REGION_LOCK_ITEM, so the loop above skips them. Under warp access, receiving the bundle lock\n")
D2_INS_BEFORE = _crlf('''\
        # Roundtable-hub re-root (SPEC-random-start-roundtable-hub.md): Limgrave isn't in
        # REGION_LOCK_ITEM (it was the free hub), so the loop above gives it no warp. Under
        # random_start add a direct hub -> Limgrave warp gated on Limgrave Lock, so Limgrave behaves
        # like any locked region. Inert on every other seed.
        if getattr(self, "_random_start_region", None) and "Limgrave" in self.created_regions:
            _lwarp = Entrance(self.player, "Warp To Limgrave", limgrave)
            limgrave.exits.append(_lwarp)
            _lwarp.connect(self.get_region("Limgrave"))
            add_rule(_lwarp, lambda state: state.has("Limgrave Lock", self.player))
''')


def patch_items(data):
    if b'"Limgrave Lock"' in data:
        print("[skip] items.py already has Limgrave Lock.")
        return data, False
    return _after(data, ITEMS_ANCHOR, ITEMS_INS, "items.py Limgrave Lock"), True


def patch_init(data):
    if b"Roundtable-hub re-root" in data:
        print("[skip] __init__.py already re-rooted.")
        return data, False
    data = _after(data, A_ANCHOR, A_INS, "A default-off")
    data = _after(data, B_ANCHOR, B_INS, "B re-enable")
    data = _replace(data, C_OLD, C_NEW, "C New Game root")
    data = _replace(data, D1_OLD, D1_NEW, "D1 warp hub")
    data = data.replace(D2_ANCHOR, D2_INS_BEFORE + D2_ANCHOR, 1)
    return data, True


def main():
    for p in (ITEMS, INIT):
        if not os.path.isfile(p):
            raise SystemExit(f"[FAIL] not found: {p}")
    it = _read(ITEMS)
    it2, ic = patch_items(it)
    ini = _read(INIT)
    # D2 anchor uniqueness guard (count before the combined patch_init replace)
    if b"Roundtable-hub re-root" not in ini and ini.count(D2_ANCHOR) != 1:
        raise SystemExit(f"[FAIL] D2 anchor x{ini.count(D2_ANCHOR)} (want 1). No write.")
    ini2, nc = patch_init(ini)
    if ic:
        _write(ITEMS, it2)
        print("[ok] patched items.py (+ Limgrave Lock)")
    if nc:
        _write(INIT, ini2)
        print("[ok] patched __init__.py (Roundtable hub re-root)")
    if not (ic or nc):
        print("[done] nothing to do.")
    else:
        print("[done] Roundtable-hub re-root applied. Rebuild apworld; GEN-TEST each overworld start "
              "(solvable? Limgrave Lock in pool? no geographic-only orphan behind Limgrave Lock?).")


if __name__ == "__main__":
    main()
