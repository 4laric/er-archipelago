#!/usr/bin/env python3
"""DERIVE every shop check from ShopLineupParam ground truth. No hand classification.

WHY
---
Shop checks were being taken from `region_map.csv`'s hand-classified `method` column, and that column
gets it wrong in a way that silently loses items.

The tell (Alaric, playtest 2026-07-11): the White Cipher Ring is not randomized in the Twin Maiden
Husks, but the Blue Cipher Ring is. Their rows are identical twins:

    row 101800  equipId=104 (White Cipher Ring)  equipType=3  sellQuantity=1  eventFlag_forStock=60280
    row 101801  equipId=105 (Blue Cipher Ring)   equipType=3  sellQuantity=1  eventFlag_forStock=60290

For a ONE-TIME shop item the stock flag IS the item's "obtained" common-event flag -- the same number
does both jobs. So 60280 got classified `method=global` ("Global / Common-event (unplaced)") instead of
`shop_merchant`, and `global` rows only survive if a map tile can be decoded out of the flag. A 5-digit
flag like 60280 decodes to nothing, so it was dropped: flag 60280 is not a location ANYWHERE. The row is
never rewritten, the shop sells the vanilla ring, and buying it fires nothing. A silently lost check.
Blue survived purely by luck of the classifier.

Sweeping the param instead of the hand column finds 110 such rows:
    76 "class A" -- no location anywhere; the item is simply LOST (White Cipher Ring among them)
    34 "class B" -- the flag IS a location via its world/NPC source, so the check still fires, but the
                   row is never rewritten -> the shop hands you the VANILLA item as well.

THE PREDICATE
-------------
A shop row is a detectable AP check iff

    eventFlag_forStock > 0   AND   sellQuantity >= 1

i.e. it has a flag, and the stock is LIMITED so that flag flips when you buy it. Unlimited rows
(sellQuantity == -1) are excluded on purpose: for those the flag is a stock UNLOCK (the bell-bearing
gate), not a purchase record -- watching it would fire the check when you hand in the bell bearing.
(Of the 1277 rows: 822 carry a flag, but 143 of those are unlimited. 635 distinct flags are sound.)

REGION
------
ShopLineupParam row ids are `shopBlock * 100 + slot`, and a block is ONE MERCHANT. Block 1018 holds the
White Cipher Ring, Blue Cipher Ring, Spirit Calling Bell, Flask of Wondrous Physick, Crafting Kit and
Memory Stone -- that is the Twin Maiden Husks inventory exactly. So a row inherits the region of the
already-classified rows in its own block. That is a structural fact about the param, not a guess.

Blocks with NO known region, or with more than one, are emitted region="" -- gen_data then treats them
as DEFAULTED (hub-quarantined, barred from carrying progression). Refusing to answer beats answering
confidently wrong.

NAMES
-----
FMG, via the witchy'd msg bundle. equipType selects the table:
    0 Weapon -> WeaponName, 1 Protector -> ProtectorName, 2 Accessory -> AccessoryName,
    3 Goods  -> GoodsName,  4 Gem      -> GemName
`equipId` is the RAW row id (no category nibble), so it indexes the FMG directly.

USAGE
    python tools/datamine_shop_rows.py            # -> greenfield/shop_rows.tsv
"""
import argparse
import csv
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AR = os.path.join(ROOT, "elden_ring_artifacts")
PARAMS = os.path.join(AR, "vanilla_er", "vanilla_er")
MSG = os.path.join(AR, "msg")
REGION_MAP = os.path.join(ROOT, "greenfield", "region_map.csv")
OUT = os.path.join(ROOT, "greenfield", "shop_rows.tsv")

# equipType -> FMG basename
FMG_FOR_TYPE = {0: "WeaponName", 1: "ProtectorName", 2: "AccessoryName", 3: "GoodsName", 4: "GemName"}

# region strings in region_map that are PLACEHOLDERS, not places. A block must not inherit these.
_PLACEHOLDER = ("Multiple merchants", "Non-merchant reference", "Global /", "PENDING")


def _int(r, k):
    try:
        return int(r[k])
    except (KeyError, ValueError, TypeError):
        return 0


def load_fmg():
    """(equipType, fmg_id) -> display name, from every item FMG bundle incl. both DLCs.

    Two things that bite:
      * the DLC bundles carry SUFFIXED tables -- WeaponName_dlc01.fmg.xml alongside an (empty base)
        WeaponName.fmg.xml. Opening only `base + '.fmg.xml'` silently misses every DLC name, so glob.
      * FMG ids are not always the equipId. Armor is the one that differs: ShopLineupParam equipId
        3010000 is FMG id 301000 ("Shining Horned Headband") -- i.e. equipId // 10. We index BOTH the
        raw id and the /10 form and let the caller try raw first; a collision would need two different
        items to share a table AND an id, which the param layout precludes.
    """
    import glob as _glob
    names = {}
    bundles = [d for d in os.listdir(MSG) if d.startswith("item") and d.endswith("-msgbnd-dcx")]
    for b in sorted(bundles):
        for etype, base in FMG_FOR_TYPE.items():
            for fp in sorted(_glob.glob(os.path.join(MSG, b, base + "*.fmg.xml"))):
                txt = open(fp, encoding="utf-8-sig", errors="replace").read()
                for m in re.finditer(r'<text id="(\d+)"[^>]*>(.*?)</text>', txt, re.S):
                    nm = m.group(2).strip()
                    if not nm or nm in ("[ERROR]", "%null%"):
                        continue
                    names.setdefault((etype, int(m.group(1))), nm)
    return names


def name_of(names, etype, eid):
    """FMG name for a ShopLineupParam (equipType, equipId). Armor indexes at equipId // 10."""
    for key in ((etype, eid), (etype, eid // 10), (etype, eid // 100)):
        if key in names:
            return names[key]
    return ""


def load_region_by_flag():
    """flag -> region, from the rows region_map ALREADY classifies as a shop (placeholders dropped)."""
    out = {}
    with open(REGION_MAP, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r.get("method", "").startswith("shop"):
                continue
            reg = (r.get("region") or "").strip()
            if not reg or any(reg.startswith(p) for p in _PLACEHOLDER):
                continue
            try:
                out[int(r["flag"])] = reg
            except (ValueError, TypeError):
                pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    with open(os.path.join(PARAMS, "ShopLineupParam.csv"), encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    idk = list(rows[0])[0]

    # THE PREDICATE: has a flag, and limited stock so the flag flips on purchase.
    detect = [r for r in rows
              if _int(r, "eventFlag_forStock") > 0 and _int(r, "sellQuantity") >= 1]

    names = load_fmg()
    reg_by_flag = load_region_by_flag()

    # a shop BLOCK is one merchant -> collect the real regions each block is known to sit in
    block_regions = defaultdict(set)
    for r in detect:
        reg = reg_by_flag.get(_int(r, "eventFlag_forStock"))
        if reg:
            block_regions[_int(r, idk) // 100].add(reg)

    out, unnamed, unregioned = [], 0, 0
    for r in detect:
        rid = _int(r, idk)
        etype, eid = _int(r, "equipType"), _int(r, "equipId")
        flag = _int(r, "eventFlag_forStock")
        block = rid // 100
        nm = name_of(names, etype, eid)
        if not nm:
            unnamed += 1
        known = block_regions.get(block, set())
        if flag in reg_by_flag:
            region, src = reg_by_flag[flag], "row"
        elif len(known) == 1:
            region, src = next(iter(known)), "block"          # same merchant => same place
        else:
            region, src = "", ("block_ambiguous" if len(known) > 1 else "block_unknown")
            unregioned += 1
        out.append((rid, block, etype, eid, nm, flag, _int(r, "sellQuantity"),
                    _int(r, "value"), region, src))

    out.sort()
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("# DERIVED shop checks -- ShopLineupParam ground truth, no hand classification.\n")
        f.write("# predicate: eventFlag_forStock > 0 AND sellQuantity >= 1 (flag flips ON PURCHASE).\n")
        f.write("#   unlimited rows (qty -1) are EXCLUDED: their flag is a bell-bearing stock UNLOCK,\n")
        f.write("#   not a purchase record -- watching it fires on hand-in, not on buying.\n")
        f.write("# region: row ids are shopBlock*100+slot and a BLOCK IS ONE MERCHANT, so a row inherits\n")
        f.write("#   its block's region. Empty region = unknown/ambiguous -> gen_data treats as DEFAULTED\n")
        f.write("#   (hub-quarantined, may not carry progression).\n")
        f.write("# names: FMG (WeaponName/ProtectorName/AccessoryName/GoodsName/GemName), incl. DLC.\n")
        f.write("# value: rune price. value==0 means the row is a TRADE/RETURN, not a purchase -- Enia's\n")
        f.write("#   remembrance shop (65 remembrance RETURNS + 51 trade OUTPUTS). The returns hand back a\n")
        f.write("#   UNIQUE item you already own: minting a location for one puts a SECOND copy of that\n")
        f.write("#   remembrance in the pool and breaks the singleton invariant. So gen_data keeps value==0\n")
        f.write("#   rows in the DETECT table (the trade outputs already have locations and need their shop\n")
        f.write("#   row rewritten) but never mints a NEW location from one.\n")
        f.write("row_id\tshop_block\tequip_type\tequip_id\titem_name\tstock_flag\tsell_qty\tvalue\tregion\tregion_source\n")
        for o in out:
            f.write("\t".join(str(x) for x in o) + "\n")

    print(f"shop_rows: {len(out)} derived shop checks -> {args.out}")
    print(f"  named from FMG      : {len(out) - unnamed}/{len(out)}")
    print(f"  region resolved     : {len(out) - unregioned}/{len(out)}"
          f"   ({sum(1 for o in out if o[8]=='row')} from the row, "
          f"{sum(1 for o in out if o[9]=='block')} inherited from the merchant block)")
    print(f"  region UNKNOWN      : {unregioned}  -> DEFAULTED (barred from progression)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
