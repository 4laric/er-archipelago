#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""datamine_spare_goods.py -- enumerate every SPARE EquipParamGoods row usable as a shop-preview slot.

Emits greenfield/spare_goods.tsv (one goods id per line), the full pool that
features/shops._LOCK_PREVIEW_SPARE_GOODS should draw from. The client re-icons a preview good's shared
FMG + icon GLOBALLY, so a region-lock / foreign-item shop slot must point at a good that is safe to
clobber: one that EXISTS (so the game can grant/preview it), has NO real name (nothing to overwrite),
and is referenced by NOTHING (so re-iconing it touches no legitimate item). That is the identical
criterion as gen_data.AP_PLACEHOLDER_GOODS (8852) -- this tool just enumerates ALL of them instead of
picking one, so the 64-row hand-list in shops.py can widen toward the full ~332-row pool and give every
foreign shop item its OWN distinct flowered name (today they SHARE once the 64 spares are exhausted --
shops.py logs the overflow warning).

Criterion (matt-free), mirroring gen_data.REPEATABLE_GOODS + AP_PLACEHOLDER_GOODS:
  * EXISTS   -- id is a row in EquipParamGoods.csv,
  * NO NAME  -- id has no GoodsName.fmg entry (base + item_dlc0*; %null%/<?null?>/x/'' all count as no
                name, so the in-game '[ERROR]' rows qualify),
  * UNREFERENCED -- id appears in NO ItemLotParam_map/_enemy goods slot (lotItemCategory==1) and NO
                ShopLineupParam / ShopLineupParam_Recipe goods row (equipType==3). (A crafting recipe's
                output is a named good, so the name test already excludes craftables; the shop-recipe
                table is scanned anyway to match the '/ recipe' half of the criterion verbatim.)
  * >= MIN_ID and != 8852 -- skip the low/system band and the reserved placeholder. 8852 is documented
                as "the lowest one clear of the low/system band", so MIN_ID = 8852 reproduces that band.

Reads elden_ring_artifacts (vanilla_params CSVs + unpacked witchy GoodsName FMG xml). Pure Python:
    python tools/datamine_spare_goods.py
"""
import csv
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AR = os.path.join(ROOT, "elden_ring_artifacts")
OUT = os.path.join(ROOT, "greenfield", "spare_goods.tsv")

# 8852 is the reserved AP_PLACEHOLDER_GOODS and is documented as the lowest row clear of the low/system
# band; use it as the inclusive floor and exclude the placeholder itself.
MIN_ID = 8852
PLACEHOLDER = 8852

_TEXT_RE = re.compile(r'<text id="(\d+)"[^>]*>(.*?)</text>', re.S)
_NULLS = ("%null%", "&lt;?null?&gt;", "x", "")


def _fmg_ids(paths):
    """Set of goods ids that have a REAL (non-null) GoodsName entry across the given FMG xml paths."""
    named = set()
    for path in paths:
        if not os.path.isfile(path):
            continue
        for m in _TEXT_RE.finditer(open(path, encoding="utf-8", errors="replace").read()):
            if m.group(2).strip() not in _NULLS:
                named.add(int(m.group(1)))
    return named


def _params_dir():
    for cand in (os.path.join(AR, "vanilla_er", "vanilla_er"),
                 os.path.join(AR, "vanilla_params")):
        if os.path.isdir(cand):
            return cand
    return None


def _referenced(pdir):
    """Every goods id referenced by a lot slot (category 1) or a shop/recipe row (equipType 3)."""
    ref = set()
    for fn in ("ItemLotParam_map.csv", "ItemLotParam_enemy.csv"):
        p = os.path.join(pdir, fn)
        if not os.path.isfile(p):
            print(f"WARNING: {fn} missing under {pdir} -- lot references not counted.", file=sys.stderr)
            continue
        with open(p, newline="", encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                for i in range(1, 9):
                    try:
                        iid = int(r.get("lotItemId%02d" % i, 0) or 0)
                        cat = int(r.get("lotItemCategory%02d" % i, 0) or 0)
                    except ValueError:
                        continue
                    if iid > 0 and cat == 1:            # 1 == Goods
                        ref.add(iid)
    for fn in ("ShopLineupParam.csv", "ShopLineupParam_Recipe.csv"):
        p = os.path.join(pdir, fn)
        if not os.path.isfile(p):
            print(f"WARNING: {fn} missing under {pdir} -- shop references not counted.", file=sys.stderr)
            continue
        with open(p, newline="", encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                try:
                    if int(r.get("equipType", 3) or 3) != 3:   # goods only
                        continue
                    eid = int(r.get("equipId", 0) or 0)
                except ValueError:
                    continue
                if eid > 0:
                    ref.add(eid)
    return ref


def main():
    pdir = _params_dir()
    if not pdir:
        print(f"no vanilla params dir under {AR} -- nothing written.", file=sys.stderr)
        return 1
    epg = os.path.join(pdir, "EquipParamGoods.csv")
    if not os.path.isfile(epg):
        print(f"missing {epg} -- nothing written.", file=sys.stderr)
        return 1

    exists = set()
    with open(epg, newline="", encoding="utf-8-sig") as fh:
        rdr = csv.DictReader(fh)
        id_col = rdr.fieldnames[0]                      # first column is the row ID
        for r in rdr:
            try:
                exists.add(int(r[id_col]))
            except (ValueError, KeyError, TypeError):
                continue

    named = _fmg_ids([os.path.join(AR, "msg", "item-msgbnd-dcx", "GoodsName.fmg.xml")] +
                     glob.glob(os.path.join(AR, "msg", "item_dlc0*-msgbnd-dcx", "GoodsName*.fmg.xml")))
    if not named:
        print("no GoodsName FMG entries found -- refusing to emit (every row would look nameless).",
              file=sys.stderr)
        return 1

    referenced = _referenced(pdir)

    spares = sorted(g for g in exists
                    if g >= MIN_ID and g != PLACEHOLDER and g not in named and g not in referenced)

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("# AUTO-GENERATED by tools/datamine_spare_goods.py -- EquipParamGoods rows that EXIST,\n")
        f.write("# have NO GoodsName, and are referenced by NO lot/shop/recipe. The safe-to-clobber pool\n")
        f.write("# for features/shops._LOCK_PREVIEW_SPARE_GOODS (region-lock + foreign-item previews).\n")
        f.write(f"# floor id={MIN_ID}, excludes reserved placeholder {PLACEHOLDER}.\n")
        f.write("goods_id\n")
        for g in spares:
            f.write(f"{g}\n")
    print(f"wrote {OUT}: {len(spares)} spare goods rows "
          f"(exists={len(exists)} named={len(named)} referenced={len(referenced)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
