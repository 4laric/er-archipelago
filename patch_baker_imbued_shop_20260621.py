#!/usr/bin/env python3
# patch_baker_imbued_shop_20260621.py  (run on Windows from repo root)
#
# Baker half of the Imbued Sword Key "Dragon Heart treatment": add one infinite-stock Twin
# Maiden Husks row for the Imbued Sword Key (goods 8186 @ 3000 runes). Reuses the existing
# AddTwinMaidenInfinite helper + soft_consumable_shop block (patch_baker_soft_consumable_shop).
# Idempotent. After running: rebuild SoulsRandomizers (Release) + bake. Price is adjustable.

import os
PW = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                  "SoulsRandomizers", "RandomizerCommon", "PermutationWriter.cs")
MARKER = "AddTwinMaidenInfinite(101884"
ANCHOR = "                    AddTwinMaidenInfinite(101883, 10060, 5000);   // Dragon Heart   @ 5000 runes"

def main():
    with open(PW, "r", encoding="utf-8", newline="") as f:
        s = f.read()
    nl = "\r\n" if "\r\n" in s else "\n"
    body = s.replace("\r\n", "\n")
    if MARKER in body:
        print("ALREADY APPLIED -- no change."); return 0
    if body.count(ANCHOR) != 1:
        print("ERROR: anchor found %d times (expected 1). Aborting." % body.count(ANCHOR)); return 3
    add = ANCHOR + "\n" + "                    AddTwinMaidenInfinite(101884, 8186, 3000);    // Imbued Sword Key @ 3000 runes"
    body = body.replace(ANCHOR, add, 1)
    out = body.replace("\n", nl) if nl == "\r\n" else body
    with open(PW, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    print("APPLIED." if MARKER in out else "WROTE but FAILED verify.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
