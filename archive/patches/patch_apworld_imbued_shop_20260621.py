#!/usr/bin/env python3
# patch_apworld_imbued_shop_20260621.py  (run on Windows from repo root)
#
# Give the Imbued Sword Key the "Dragon Heart treatment": sell it infinitely at the Twin
# Maiden Husks under soft_consumable_shop instead of randomizing 4 copies into the pool.
# Apworld half (baker half = patch_baker_imbued_shop_20260621.py).
#   1) add _has_enough_imbued() -> True under soft_consumable_shop (else state.has count).
#   2) route the Four Belfries / Rauh entrance rules through it (the 4x + 3x has() checks).
#   3) pull Imbued Sword Key from the randomized pool when the shop is on.
# Idempotent; aborts if an anchor moved. Repackage the apworld + gen-test afterwards.

import sys, io, os
DEFAULT = os.path.join("Archipelago", "worlds", "eldenring", "__init__.py")
MARKER  = "_has_enough_imbued"

HELPER_ANCHOR = "    def _add_shop_rules(self) -> None:"
HELPER_BLOCK = (
'    def _has_enough_imbued(self, state: CollectionState, req: int) -> bool:\n'
'        """Imbued Sword Keys: the Twin Maiden Husks shop sells them infinitely under\n'
'        soft_consumable_shop (Dragon-Heart treatment), so the requirement is satisfied."""\n'
'        if self.options.soft_consumable_shop.value:\n'
'            return True\n'
'        return state.has("Imbued Sword Key", self.player, req)\n'
'\n'
'    def _add_shop_rules(self) -> None:'
)

POOL_ANCHOR = (
'                    if _vn in item_table: item_table[_vn].skip = True\n'
'        if self.options.derandomize_gurranq.value:'
)
POOL_BLOCK = (
'                    if _vn in item_table: item_table[_vn].skip = True\n'
'            if "Imbued Sword Key" in item_table:  # Twin Maiden Husks sells it infinitely\n'
'                item_table["Imbued Sword Key"].skip = True\n'
'        if self.options.derandomize_gurranq.value:'
)

RULE4_OLD = 'state.has("Imbued Sword Key", self.player, 4)'
RULE4_NEW = 'self._has_enough_imbued(state, 4)'
RULE3_OLD = 'state.has("Imbued Sword Key", self.player, 3)'
RULE3_NEW = 'self._has_enough_imbued(state, 3)'


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    if not os.path.isfile(path):
        print("ERROR: file not found:", path); return 2
    with io.open(path, "r", encoding="utf-8", newline="") as f:
        src = f.read()
    nl = "\r\n" if "\r\n" in src else "\n"
    body = src.replace("\r\n", "\n")
    if MARKER in body:
        print("ALREADY APPLIED (marker present) -- no change."); return 0
    # anchors must be unique
    for tag, anc, n_exp in (("helper", HELPER_ANCHOR, 1), ("pool", POOL_ANCHOR, 1),
                            ("rule4", RULE4_OLD, 4), ("rule3", RULE3_OLD, 3)):
        c = body.count(anc)
        if c != n_exp:
            print("ERROR: anchor %s found %d (expected %d). Aborting." % (tag, c, n_exp)); return 3
    body = body.replace(HELPER_ANCHOR, HELPER_BLOCK, 1)
    body = body.replace(POOL_ANCHOR, POOL_BLOCK, 1)
    body = body.replace(RULE4_OLD, RULE4_NEW)   # all 4
    body = body.replace(RULE3_OLD, RULE3_NEW)   # all 3
    out = body.replace("\n", nl) if nl == "\r\n" else body
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    with io.open(path, "r", encoding="utf-8", newline="") as f:
        chk = f.read().replace("\r\n", "\n")
    ok = (MARKER in chk
          and chk.count(RULE4_OLD) == 0 and chk.count(RULE3_OLD) == 0
          and chk.count("self._has_enough_imbued(state, 4)") == 4
          and chk.count("self._has_enough_imbued(state, 3)") == 3
          and 'item_table["Imbued Sword Key"].skip = True' in chk)
    print("APPLIED." if ok else "WROTE but verification FAILED -- inspect.")
    print("  rules rerouted (4x/3x):", chk.count(RULE4_NEW), "/", chk.count(RULE3_NEW))
    print("  newline:", "CRLF" if nl == "\r\n" else "LF", " bytes:", len(out))
    return 0 if ok else 5

if __name__ == "__main__":
    raise SystemExit(main())
