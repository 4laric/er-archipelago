#!/usr/bin/env python3
r"""
patch_apworld_numregions_deadkey_to_rune.py  (run on Windows from repo root)

SUPERSEDES patch_apworld_numregions_rold_to_rune.py (do NOT apply both -- same anchors). Generalises
the Rold swap to every vanilla key item that gates nothing in a num_regions Capital run, swapping each
IN-POOL dead key 1:1 for a free great rune (then filler when runes run out).

Dead keys (gate only sealed / warp-redundant regions):
  * Rold Medallion              -- Mountaintops + Snowfield sealed.
  * Haligtree Secret Medallion (L/R) -- Elphael (Haligtree) sealed.
  * Dectus Medallion (L/R)      -- Altus is KEPT but reached by Altus Lock under warp, so the Dectus
                                   lift is redundant (region_access == warp only).

Free runes (count toward _has_enough_great_runes AND not already in the pool): a rune is free iff its
boss region/step is sealed (post-Leyndell Mohg's/Malenia's via sealed region; spine Godrick's/Radahn's/
Rennala's/Rykard's via sealed step-lock) and it wasn't pool-injected. Determined with the SAME
kept/sealed machinery as the deficit-injector, so a swapped rune can never duplicate a pool rune.

A rune is popped per IN-POOL dead key (in create_items), so runes are never wasted on a dead key whose
half sits in a sealed region, and the swap is count-neutral (the dead key's location stays a check).

Idempotent. Binary I/O preserves CRLF. Anchors on a CLEAN (HEAD) __init__ -- the SAME two anchors the
Rold patch used, so this is a drop-in replacement. git restore __init__.py before re-applying the stack.
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


# 1) generate_early: build the dead-key set + free-rune queue, just before the key-inject loop.
A1 = b'        if self.options.world_logic == "region_lock" or self.options.world_logic == "region_lock_bosses": # inject keys\r\n'
B1 = _crlf('''\
        # Dead/redundant vanilla key items -> free great runes (num_regions). Collect the keys that
        # gate only sealed (or warp-redundant) regions, and the runes that are free to give (boss
        # region/step sealed -> not already in the pool, mirrors the deficit-injector's kept/sealed
        # test so a swap can never duplicate a pool rune). create_items pops one rune per IN-POOL dead
        # key (no waste); leftover dead keys -> filler. Count-neutral; each dead key's location stays a
        # check. No-op when a region is kept (the key is live there).
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

# 2) create_items: swap each in-pool dead key for a free rune (then filler), before the final else.
A2 = (b'            else:\r\n'
      b'                self.local_itempool.append(self.create_item(default_item_name))\r\n')
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
        print("[skip] dead-key swap already applied.")
        return
    if b"self._rold_swap_rune" in data:
        raise SystemExit("[FAIL] patch_apworld_numregions_rold_to_rune.py is applied; this supersedes it. "
                         "git restore __init__.py and re-apply the stack with THIS patch instead. No write.")
    if data.count(A1) != 1:
        raise SystemExit(f"[FAIL] generate_early anchor x{data.count(A1)} (want 1). No write.")
    if data.count(A2) != 1:
        raise SystemExit(f"[FAIL] create_items anchor x{data.count(A2)} (want 1). No write.")
    data = data.replace(A1, B1 + A1, 1).replace(A2, B2, 1)
    _write(INIT, data)
    print("[ok] dead-key (Rold/Haligtree/Dectus) -> free great rune swap wired.")


if __name__ == "__main__":
    main()
