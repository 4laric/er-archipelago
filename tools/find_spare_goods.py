#!/usr/bin/env python3
"""Find a SPARE EquipParamGoods row -- a second AP placeholder, on the 8852 pattern.

WHY
---
`apPlaceholderGoods` (8852) is "a spare EquipParamGoods row: exists so the game can grant it, no FMG
name, referenced by no lot/shop/recipe" (contract.py). One is not enough: the lot-side suppressor
(`check_lots::is_placeholder`) nulls placeholder bag-adds UNCONDITIONALLY and cannot tell a shop row
from a lot row, so a shop row cannot be repointed at 8852 without re-arming the retired crash path.
A SECOND, shop-only spare row is the unlock -- it makes shop slots markable without hijacking a real
good's shared FMG entry (see shop_preview.rs's `real.contains(&gid)` guard, which is why a slot shows
"Armorer's Cookbook [2]" while paying out an Ash of War).

This runs on the WINDOWS box: it reads the Smithbox param CSV dump, which is licensing-restricted and
never leaves it. The only thing that comes back to the repo is ONE INTEGER.

THE DATUM, NOT THE ABSENCE (corrected 2026-07-25)
------------------------------------------------
The first version of this tool ranked rows by "referenced by nothing I scanned" and reported 1137 of
2326 goods rows as spare -- half the table, with row id 0 at the top. That predicate was wrong in
principle: absence of a reference is invisible evidence (a row can be granted by EMEVD or an NPC's
ESD without appearing in any param), and CONTRIBUTING is explicit that absence is what you go looking
for, not what you conclude from.

The game ships the answer. `disableParam_NT = 1` is FromSoft's own marker for a row disabled in the
shipping build, and 8852 -- the placeholder already proven in-game -- carries it, together with an
empty Name, `sortId 999999` + `sortGroupId 255` (hidden from the menu sort) and `goodsType 1`. So we
select on the datum and match 8852's SHAPE, and the reference scan is demoted to a CONFIRMATION that
prints when a datum-selected row turns out to be referenced anyway (which would mean the marker and
the tables disagree -- worth seeing, not worth hiding).

Still cannot prove "no FMG name": names live in the msgbnd, not the params. The shape filter makes it
very likely and the confirmation is one in-game grant.

USAGE (PowerShell)
------------------
    python tools\\find_spare_goods.py <csv-dir>
    python tools\\find_spare_goods.py <csv-dir> --exclude 8852 --top 25
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

GOODS_LOT_CATEGORIES = {"0", "1", "6"}   # gen_data.py _LOT_CAT_GOODS: these lot categories hold goods
SHOP_EQUIPTYPE_GOODS = "3"               # ShopLineupParam.equipType 3 = Goods


def read(path: Path):
    """Yield dict rows. Smithbox writes ';'-delimited with a BOM; sniffed, never assumed."""
    if not path.is_file():
        print(f"  [skip] {path.name} not found -- its references CANNOT be ruled out", file=sys.stderr)
        return
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        head = fh.readline()
        if not head.strip():
            return
        delim = max((";", ",", "\t"), key=head.count)
        fh.seek(0)
        yield from csv.DictReader(fh, delimiter=delim)


def main() -> int:
    ap = argparse.ArgumentParser(description="Find spare (unreferenced) EquipParamGoods rows.")
    ap.add_argument("csv_dir", type=Path)
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--exclude", type=int, nargs="*", default=[8852], help="already-claimed rows")
    ap.add_argument("--goods-type", type=int, default=1, help="match 8852's goodsType (default 1)")
    args = ap.parse_args()

    d = args.csv_dir
    if not d.is_dir():
        sys.exit(f"{d}: not a directory")

    goods, rows = {}, {}
    for r in read(d / "EquipParamGoods.csv"):
        rid = (r.get("ID") or r.get("Row ID") or "").strip()
        if rid.isdigit():
            goods[int(rid)] = (r.get("Name") or "").strip()
            rows[int(rid)] = r
    if not goods:
        sys.exit("EquipParamGoods.csv yielded ZERO rows -- an empty input is a FAILURE, not a clean run")

    referenced: dict[int, set[str]] = {}

    def mark(rid, why):
        if rid in goods:
            referenced.setdefault(rid, set()).add(why)

    for name in ("ItemLotParam_map.csv", "ItemLotParam_enemy.csv"):
        for r in read(d / name):
            for i in range(1, 9):
                cat = (r.get(f"lotItemCategory{i:02d}") or "").strip()
                iid = (r.get(f"lotItemId{i:02d}") or "").strip()
                if cat in GOODS_LOT_CATEGORIES and iid.isdigit() and int(iid) > 0:
                    mark(int(iid), "lot")

    for name in ("ShopLineupParam.csv", "ShopLineupParam_Recipe.csv"):
        for r in read(d / name):
            eid = (r.get("equipId") or "").strip()
            et = (r.get("equipType") or "").strip()
            if eid.isdigit() and int(eid) > 0 and (et == SHOP_EQUIPTYPE_GOODS or "Recipe" in name):
                mark(int(eid), "recipe" if "Recipe" in name else "shop")
            for k in ("mtrlId", "materialId"):
                v = (r.get(k) or "").strip()
                if v.isdigit() and int(v) > 0:
                    mark(int(v), "recipe-mtrl")

    for r in read(d / "EquipMtrlSetParam.csv"):
        for k, v in r.items():
            if k and k.startswith("materialId") and (v or "").strip().isdigit() and int(v) > 0:
                mark(int(v), "craft-material")

    excl = set(args.exclude)
    # THE DATUM: the game's own "this row is disabled in the shipping build" marker, plus 8852's shape.
    ref_name = {"8852": "the proven placeholder"}
    spare = []
    contradicted = []
    for rid, row in sorted(rows.items()):
        if rid in excl:
            continue
        if (row.get("disableParam_NT") or "").strip() != "1":
            continue
        if (row.get("Name") or "").strip():
            continue                                    # a named row is somebody's item
        if (row.get("sortId") or "").strip() != "999999":
            continue                                    # not hidden from the menu sort
        if (row.get("goodsType") or "").strip() != str(args.goods_type):
            continue                                    # must be grantable/holdable like 8852
        if rid in referenced:
            contradicted.append((rid, sorted(referenced[rid])))
            continue
        spare.append((rid, row))

    print(f"[goods] rows {len(goods)} | param-referenced {len(referenced)} | "
          f"excluded {len(excl)} | SPARE candidates {len(spare)}")
    if contradicted:
        # The marker and the tables disagree. Loud, not filtered away.
        detail = ", ".join("%d(%s)" % (r, "/".join(w)) for r, w in contradicted[:6])
        print("[goods] %d row(s) are marked disabled BUT referenced -- marker and tables "
              "disagree, do not use these: %s" % (len(contradicted), detail))
    if not spare:
        sys.exit("no spare row found -- that is a real answer, not an error, but check the [skip] "
                 "lines above: a param file that failed to load cannot rule anything out")
    print("\nMarked disabled by the game + 8852's shape (NOT proven nameless -- grant one in-game):")
    print(f"  {'id':<9} {'iconId':<8} {'maxNum':<7} {'rarity':<7} {'sortGroupId'}")
    for rid, row in spare[:args.top]:
        print(f"  {rid:<9} {(row.get('iconId') or '?'):<8} {(row.get('maxNum') or '?'):<7} "
              f"{(row.get('rarity') or '?'):<7} {row.get('sortGroupId') or '?'}")
    print(f"\nPick one, confirm it has no FMG name, then wire it as the SHOP placeholder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
