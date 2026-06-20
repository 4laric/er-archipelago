#!/usr/bin/env python3
r"""
patch_apworld_numregions_deadkey_extend.py  (run on Windows from repo root)

Extends the ALREADY-APPLIED patch_apworld_numregions_rold_to_rune.py from Rold-only to all dead/
redundant vanilla key items (Rold + Haligtree Secret Medallion L/R + Dectus Medallion L/R), each
swapped 1:1 for a free gate-counting great rune (then filler). No git restore needed -- it replaces the
two blocks the Rold patch inserted with the generalized versions, in place. Requires the Rold patch.

Free runes are popped per IN-POOL dead key (in create_items), determined with the same kept/sealed
machinery as the deficit-injector, so no rune is wasted or duplicated. Dectus is included only under
warp access (Altus is kept but reached by its Lock, so the Dectus lift is redundant).

Idempotent. Binary I/O preserves CRLF. Asserts the Rold-patch anchors (no write on mismatch).
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
INIT = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "__init__.py")


def _read(p):
    with open(p, "rb") as f:
        return f.read()


def _write(p, d):
    with open(p, "wb") as f:
        f.write(d)


def _crlf(t):
    return t.replace("\n", "\r\n").encode("utf-8")


# ---- ANCHOR 1: the exact generate_early block the Rold patch inserted (verbatim) ----
A1 = _crlf('''\
        # Rold->rune swap (num_regions): when Mountaintops + Snowfield are sealed (always true in a
        # Capital run) the Rold Medallion gates nothing, yet stays force-placed progression -- dead
        # pool weight. Pick a great rune that DOES count toward the Leyndell gate and whose own boss
        # is sealed (Mohg's/Malenia's), so it isn't already in the pool. Applied 1:1 in create_items.
        self._rold_swap_rune = None
        if self.options.num_regions.value > 0 and getattr(self, "_spine_active", False) \\
                and "Rold Medallion" in item_table:
            _sealed_rr = getattr(self, "_spine_sealed_regions", set())
            if "Mountaintops of the Giants" in _sealed_rr and "Consecrated Snowfield" in _sealed_rr:
                for _cand, _creg in (("Mohg's Great Rune", "Mohgwyn Palace"),
                                     ("Malenia's Great Rune", "Elphael, Brace of the Haligtree")):
                    if (_cand in item_table and _creg in _sealed_rr
                            and _cand not in getattr(self, "_num_regions_pool_injected_runes", [])):
                        self._rold_swap_rune = _cand
                        break
''')
# ---- REPLACEMENT 1: generalized dead-key set + free-rune queue ----
B1 = _crlf('''\
        # Dead/redundant vanilla key items -> free great runes (num_regions). Collect keys that gate
        # only sealed (or warp-redundant) regions, and the runes free to give (boss region/step sealed
        # -> not already in the pool; same kept/sealed test as the deficit-injector, so a swap can
        # never duplicate a pool rune). create_items pops one rune per IN-POOL dead key; leftovers ->
        # filler. Count-neutral; each dead key's location stays a check. No-op when a region is kept.
        self._deadkey_swap_set = frozenset()
        self._deadkey_rune_queue = []
        if self.options.num_regions.value > 0 and getattr(self, "_spine_active", False):
            _sealed_rr = getattr(self, "_spine_sealed_regions", set())
            _sealed_lk = getattr(self, "_spine_sealed_locks", set())
            _injected = getattr(self, "_num_regions_pool_injected_runes", [])
            _dead = []
            if "Mountaintops of the Giants" in _sealed_rr and "Consecrated Snowfield" in _sealed_rr:
                _dead.append("Rold Medallion")
            if "Elphael, Brace of the Haligtree" in _sealed_rr:
                _dead += ["Haligtree Secret Medallion (Left)", "Haligtree Secret Medallion (Right)"]
            if self.options.region_access == "warp":
                _dead += ["Dectus Medallion (Left)", "Dectus Medallion (Right)"]
            self._deadkey_swap_set = frozenset(k for k in _dead if k in item_table)
            _free = []
            for _r, _reg in (("Mohg's Great Rune", "Mohgwyn Palace"),
                             ("Malenia's Great Rune", "Elphael, Brace of the Haligtree")):
                if _reg in _sealed_rr and _r in item_table and _r not in _injected:
                    _free.append(_r)
            _step_lock = region_spine.NUM_REGIONS_CHAIN_STEP_LOCK
            for _s, _r in sorted(region_spine.NUM_REGIONS_STEP_GREAT_RUNE.items()):
                if (_step_lock.get(_s) in _sealed_lk and _r in item_table
                        and _r not in _injected and _r not in _free):
                    _free.append(_r)
            self._deadkey_rune_queue = _free
''')

# ---- ANCHOR 2: the exact create_items elif the Rold patch inserted (elif + else) ----
A2 = (b'            elif default_item_name == "Rold Medallion" and getattr(self, "_rold_swap_rune", None):\r\n'
      b'                # num_regions: Rold gates nothing (Mountaintops/Snowfield sealed) -> swap it 1:1\r\n'
      b'                # for a gate-counting great rune. Count-neutral; the location stays a check.\r\n'
      b'                self.local_itempool.append(self.create_item(self._rold_swap_rune))\r\n'
      b'            else:\r\n'
      b'                self.local_itempool.append(self.create_item(default_item_name))\r\n')
# ---- REPLACEMENT 2: generalized elif (queue pop, then filler) ----
B2 = (b'            elif default_item_name in getattr(self, "_deadkey_swap_set", frozenset()):\r\n'
      b'                # num_regions dead/redundant key -> a free gate-counting great rune (then\r\n'
      b'                # filler). Pop per IN-POOL key so runes are never wasted/duplicated. Count-neutral.\r\n'
      b'                _swap = self._deadkey_rune_queue.pop(0) if self._deadkey_rune_queue else "Golden Rune [13]"\r\n'
      b'                self.local_itempool.append(self.create_item(_swap))\r\n'
      b'            else:\r\n'
      b'                self.local_itempool.append(self.create_item(default_item_name))\r\n')


def main():
    if not os.path.isfile(INIT):
        raise SystemExit(f"[FAIL] not found: {INIT}")
    data = _read(INIT)
    if b"_deadkey_swap_set" in data:
        print("[skip] dead-key extension already applied.")
        return
    if b"self._rold_swap_rune" not in data:
        raise SystemExit("[FAIL] the Rold patch isn't applied; this extension needs it (or use the "
                         "standalone patch_apworld_numregions_deadkey_to_rune.py on a clean tree). No write.")
    if data.count(A1) != 1:
        raise SystemExit(f"[FAIL] generate_early anchor x{data.count(A1)} (want 1). No write.")
    if data.count(A2) != 1:
        raise SystemExit(f"[FAIL] create_items anchor x{data.count(A2)} (want 1). No write.")
    data = data.replace(A1, B1, 1).replace(A2, B2, 1)
    _write(INIT, data)
    print("[ok] extended dead-key swap to Rold + Haligtree + Dectus.")


if __name__ == "__main__":
    main()
