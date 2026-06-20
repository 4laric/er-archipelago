#!/usr/bin/env python3
r"""
patch_apworld_numregions_rold_to_rune.py  (run on Windows from repo root)

In a num_regions Capital run the Mountaintops of the Giants + Consecrated Snowfield (and the whole
post-Leyndell cluster: Mohgwyn, Haligtree) are sealed, so the Rold Medallion gates nothing -- yet it
stays in the pool as force-placed progression (a dead item, and one of the overflow culprits). This
swaps it 1:1 for a GREAT RUNE that actually counts toward the Leyndell gate.

Swap target = Mohg's (or Malenia's) Great Rune: _has_enough_great_runes counts both, and their bosses
are sealed in a Capital run, so the rune is NOT already in the pool (no duplicate) and the pool-mode
deficit-injector never touches them. Count-neutral: the Rold location stays a check, its pool slot now
holds the rune.

Guards (no-op unless all hold): num_regions > 0; spine active; Mountaintops + Snowfield sealed; the
chosen rune's own boss region sealed (so swapping can't duplicate a pool rune); rune not already
injected. If Mountaintops is KEPT (Rold is live), nothing changes.

Idempotent. Binary I/O preserves CRLF. Asserts anchors (no write on mismatch). Independent of the
random-start patches.
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


# 1) generate_early: choose the swap rune, just before the region_lock key-inject loop (so
#    _spine_sealed_regions / _num_regions_pool_injected_runes are already finalized).
A1 = b'        if self.options.world_logic == "region_lock" or self.options.world_logic == "region_lock_bosses": # inject keys\r\n'
B1 = _crlf('''\
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

# 2) create_items: swap Rold's pool slot for the chosen rune (1:1), just before the final else.
A2 = (b'            else:\r\n'
      b'                self.local_itempool.append(self.create_item(default_item_name))\r\n')
B2 = (b'            elif default_item_name == "Rold Medallion" and getattr(self, "_rold_swap_rune", None):\r\n'
      b'                # num_regions: Rold gates nothing (Mountaintops/Snowfield sealed) -> swap it 1:1\r\n'
      b'                # for a gate-counting great rune. Count-neutral; the location stays a check.\r\n'
      b'                self.local_itempool.append(self.create_item(self._rold_swap_rune))\r\n'
      b'            else:\r\n'
      b'                self.local_itempool.append(self.create_item(default_item_name))\r\n')


def main():
    if not os.path.isfile(INIT):
        raise SystemExit(f"[FAIL] not found: {INIT}")
    data = _read(INIT)
    if b"self._rold_swap_rune" in data:
        print("[skip] Rold->rune swap already applied.")
        return
    if data.count(A1) != 1:
        raise SystemExit(f"[FAIL] generate_early anchor x{data.count(A1)} (want 1). No write.")
    if data.count(A2) != 1:
        raise SystemExit(f"[FAIL] create_items anchor x{data.count(A2)} (want 1). No write.")
    data = data.replace(A1, B1 + A1, 1).replace(A2, B2, 1)
    _write(INIT, data)
    print("[ok] Rold Medallion -> great rune swap wired (num_regions, Mountaintops/Snowfield sealed).")


if __name__ == "__main__":
    main()
