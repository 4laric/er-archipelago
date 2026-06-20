#!/usr/bin/env python3
"""
Moore shop-collapse diagnostic.

Run against the apconfig.json produced by ONE FULL (non-dlc_only) seed bake.
Tells you whether the shop AP-location -> event-flag collapse is Moore-specific
or hits every multi-row shop (Kale, nomads, ...). That decides Option B (contained)
vs Option A (scraper rework).

Usage:
    python check_shop_collapse.py path\\to\\apconfig.json

Mechanism being tested: LocationScope forces OnlyShops -> id=0 and keys by base
shop, discarding per-row eventFlag_forStock. If true for all shops, every shop's
rows cluster onto ONE flag in location_flags. (See PATCH-moore-shop-collapse.md.)
"""
import json, sys, collections

# Lead/base row flags per shop, pulled from diste/Base/itemslots.txt.
# A shop is COLLAPSED if its lead flag is mapped by >1 AP location.
SHOPS = {
    "Moore grocery (base 102250)": [320500, 320600, 320610, 320620, 320630, 320640,
                                    320550, 320560, 320570, 320580, 320590, 320650, 320660],
    "Moore poison  (base 102270)": [320700, 320710, 320720, 320730, 320740, 320750,
                                    320770, 320780, 320810, 320760, 320790, 320800],
    "Kale (base 100500)":          [60120, 150100, 150110, 150150, 150160, 150170, 150180,
                                    150050, 150130, 69620, 69720, 67000, 67110, 67610, 66030],
    "Nomad SE-of-CC (base 100575)":[150870, 150860, 150880, 150890, 150920, 150930, 150940,
                                    69630, 69690, 67210, 150950],
}

def main(path):
    d = json.load(open(path))
    lf = d.get("location_flags") or {}
    n = len(lf)
    vals = collections.Counter(lf.values())
    print(f"apconfig: {path}")
    print(f"location_flags entries: {n}")
    print(f"distinct flags: {len(vals)}   flags reused by >1 location: "
          f"{sum(1 for c in vals.values() if c > 1)}\n")

    print("=== per-shop verdict ===")
    for name, flags in SHOPS.items():
        present = [(fl, vals.get(fl, 0)) for fl in flags if vals.get(fl, 0) > 0]
        if not present:
            print(f"  {name:32s}  ABSENT in this seed")
            continue
        lead_mult = max(c for _, c in present)
        distinct = sum(1 for _, c in present if c > 0)
        collapsed = lead_mult > 1
        tag = "COLLAPSED" if collapsed else "ok (distinct rows)"
        print(f"  {name:32s}  {tag:18s}  rows-present={distinct:2d}/{len(flags)}  "
              f"max-flag-multiplicity={lead_mult}")

    print("\n=== top reused flags (any source) ===")
    for fl, c in sorted(((f, c) for f, c in vals.items() if c > 1),
                        key=lambda x: -x[1])[:20]:
        print(f"  flag {fl}: {c} locations")

    print("\nReading: if ONLY the two Moore lines say COLLAPSED -> Option B (contained).")
    print("         if Kale/nomads ALSO say COLLAPSED -> general shop bug -> Option A.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    main(sys.argv[1])
