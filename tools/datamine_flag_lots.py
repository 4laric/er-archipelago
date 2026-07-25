#!/usr/bin/env python3
r"""datamine_flag_lots.py -- the FAITHFUL flag->lots capture (SPEC-flag-lot-item-model).

The game's ItemLotParam is one-to-MANY: a single acquisition event flag (`getItemFlagId`) can be
shared by SEVERAL lots, each granting an item. Messmer's death (flag 510460) drives lot 10460
(Remembrance of the Impaler) AND lot 10461 (Messmer's Kindling). The old scan collapsed each flag to
one row (lowest lot wins), silently dropping the siblings; ROW_ITEM_NAME_FIX then hand-corrected the
mis-picks. This tool captures the WHOLE structure instead -- one row per (flag, table, lot, slot) --
so the downstream projection (each awarded lot -> its own co-firing check) is data-driven, not a pin.

Emits `greenfield/flag_lots.tsv` (tab-separated, utf-8, \n, sorted by flag,table,lot,slot):

    flag  table  lot  slot  category  item_id  num  goods_type  name

  * flag       = getItemFlagId (the acquisition flag the client polls; SHARED across sibling lots)
  * table      = "map" | "enemy" (which ItemLotParam)
  * lot        = the ItemLotParam row id
  * slot       = 1..8 (lotItemId0N)
  * category   = lotItemCategory0N (0/1/6 = goods families, others = weapon/armor/accessory/gem)
  * item_id    = lotItemId0N (RAW id; goods FullID = item_id | 0x40000000)
  * num        = lotItemNum0N (quantity)
  * goods_type = EquipParamGoods.goodsType for a goods item (1 = KEY ITEM, 3 = remembrance, ...), else ""
  * name       = best-effort display name (ITEM_CATALOG reverse where the item is pooled), else ""

The one goods row the client suppresses unconditionally (AP_PLACEHOLDER_GOODS = 8852) is skipped, as
are unflagged/farmable lots (flag<=0) -- consistent with gen_check_lots_table.py.

    python tools/datamine_flag_lots.py            # regenerate greenfield/flag_lots.tsv
    python tools/datamine_flag_lots.py --check     # CI drift gate (exit 1 if stale)
    python tools/datamine_flag_lots.py --report    # co-check candidate report: every SHARED flag +
                                                   #   each sibling's category/goods_type/meaningful
                                                   #   verdict. Reads the COMMITTED tsv -- no
                                                   #   artifacts needed, runs anywhere.

Artifacts: reads `elden_ring_artifacts/vanilla_er/vanilla_er/` under the repo (same as
gen_check_lots_table.py). Override with env ER_ARTIFACTS_VV (used in the Linux sandbox where only the
param CSVs are staged). Windows/regen runs it with the full artifacts in place.
"""
import argparse
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.dirname(HERE)
VV = os.environ.get("ER_ARTIFACTS_VV") or os.path.join(
    REPO, "elden_ring_artifacts", "vanilla_er", "vanilla_er")
OUT = os.path.join(REPO, "greenfield", "flag_lots.tsv")

AP_PLACEHOLDER_GOODS = 8852   # must match gen_data.AP_PLACEHOLDER_GOODS / gen_check_lots_table
GOODS_NIBBLE = 0x4000_0000


def _goods_types():
    """goods raw id -> goodsType (EquipParamGoods). 1 = KEY ITEM, 3 = remembrance, etc."""
    p = os.path.join(VV, "EquipParamGoods.csv")
    if not os.path.isfile(p):
        raise SystemExit("FATAL: %s missing -- EquipParamGoods required" % p)
    out = {}
    with open(p, newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            try:
                out[int(r["ID"])] = int(r.get("goodsType", -1))
            except (ValueError, KeyError, TypeError):
                continue
    return out


def _catalog_names():
    """FullID -> display name, from the committed greenfield catalog (item_ids.py). Best-effort: only
    pooled items are here, so a ride-along item absent from the pool gets an empty name (the Windows
    regen resolves the rest via FMG; the name column is legibility, not load-bearing)."""
    src = os.path.join(REPO, "greenfield", "eldenring", "item_ids.py")
    if not os.path.isfile(src):
        return {}
    text = open(src, encoding="utf-8").read()
    out = {}
    for m in re.finditer(r"'([^']+)'\s*:\s*(\d+),", text):
        out.setdefault(int(m.group(2)), m.group(1))
    return out


def build_rows():
    goods_type = _goods_types()
    names = _catalog_names()
    rows = []
    for fn, table in (("ItemLotParam_map.csv", "map"), ("ItemLotParam_enemy.csv", "enemy")):
        p = os.path.join(VV, fn)
        if not os.path.isfile(p):
            raise SystemExit("FATAL: %s missing -- elden_ring_artifacts required" % p)
        with open(p, newline="", encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                try:
                    lot = int(list(r.values())[0])            # ID = first column
                    flag = int(r.get("getItemFlagId", 0) or 0)
                except (ValueError, IndexError):
                    continue
                if lot <= 0 or flag <= 0:                      # unflagged/farmable -> not a check
                    continue
                for i in range(1, 9):
                    try:
                        iid = int(r.get("lotItemId%02d" % i, 0) or 0)
                        cat = int(r.get("lotItemCategory%02d" % i, 0) or 0)
                        num = int(r.get("lotItemNum%02d" % i, 0) or 0)
                    except (ValueError, TypeError):
                        continue
                    if iid <= 0 or iid == AP_PLACEHOLDER_GOODS:
                        continue
                    gt = goods_type.get(iid, "")
                    # name: try the goods FullID first (goods are the common key-item case), then the
                    # raw id under any known nibble in the catalog.
                    nm = names.get(iid | GOODS_NIBBLE) or names.get(iid) or ""
                    rows.append((flag, table, lot, i, cat, iid, num,
                                 "" if gt == "" else str(gt), nm))
    rows.sort(key=lambda t: (t[0], t[1], t[2], t[3]))
    return rows


HEADER = "flag\ttable\tlot\tslot\tcategory\titem_id\tnum\tgoods_type\tname"

# ---- co-check candidate POLICY (SPEC-flag-lot-item-model §2.1 first cut) ---------------------------
# "Meaningful" sibling = worth being its own co-firing check when the allowlist widens beyond the
# hand-verified four. This is the ONE place the policy lives; flipping gen_data from
# CO_CHECK_FLAGS-allowlist to "all meaningful siblings" is a one-line change that imports these.
#   * goods_type: 1 = KEY ITEM, 3 = remembrance, 15 = great rune; 5/16/17/18 = sorcery/incantation
#     families (verified against the tsv: Rancorcall=5, Aspects of the Crucible=16, Frozen
#     Armament=17, Flame Protect Me=18).
#   * category: 2 weapon / 3 protector / 4 accessory / 5 gem(Ash of War) / 6 spell -- non-goods gear.
# Deliberately JUNK (not meaningful): goods_type 0/2/9-12 (consumables, materials, notes, pots),
# 7/8 (spirit ashes -- the Ogha/Oleg class, "not a check anywhere"), 14 (reinforcement materials --
# NB this bucket contains BOTH somber smithing stones (junk) AND Golden Seed / Scadutree Fragment
# (meaningful): the two meaningful gt-14 cases ride the ALLOWLIST (520160, 510440), never the policy.
MEANINGFUL_GOODS_TYPES = frozenset({1, 3, 15, 5, 16, 17, 18})
MEANINGFUL_CATEGORIES = frozenset({2, 3, 4, 5, 6})


def sibling_meaningful(category, goods_type):
    """Would this (category, goods_type) sibling qualify under the widen-the-allowlist policy?"""
    try:
        if goods_type != "" and int(goods_type) in MEANINGFUL_GOODS_TYPES:
            return True
    except (TypeError, ValueError):
        pass
    try:
        return int(category) in MEANINGFUL_CATEGORIES
    except (TypeError, ValueError):
        return False


def report():
    """Print every SHARED flag (>1 lot) from the COMMITTED tsv, one line per lot, with the policy
    verdict per sibling -- the review sheet for widening CO_CHECK_FLAGS beyond the seeded four."""
    if not os.path.isfile(OUT):
        raise SystemExit("FATAL: %s missing -- run the datamine first" % OUT)
    from collections import defaultdict
    by_flag = defaultdict(list)
    with open(OUT, encoding="utf-8") as fh:
        rd = csv.DictReader(fh, delimiter="\t")
        for r in rd:
            by_flag[int(r["flag"])].append(r)
    shared = {f: v for f, v in by_flag.items() if len({(x["table"], x["lot"]) for x in v}) > 1}
    n_meaningful_flags = 0
    for f in sorted(shared):
        fam = sorted(shared[f], key=lambda x: (x["table"], int(x["lot"]), int(x["slot"])))
        lots = sorted({(x["table"], int(x["lot"])) for x in fam})
        primary = lots[0]                      # the lot the region_map row was named after (lowest)
        any_meaningful = False
        lines = []
        for x in fam:
            is_primary = (x["table"], int(x["lot"])) == primary
            mn = sibling_meaningful(x["category"], x["goods_type"])
            if mn and not is_primary:
                any_meaningful = True
            lines.append("    %-5s lot %-10s slot %s  cat %-2s gt %-3s %-9s %s"
                         % (x["table"], x["lot"], x["slot"], x["category"],
                            x["goods_type"] or "-",
                            "PRIMARY" if is_primary else
                            ("MEANINGFUL" if mn else "junk"),
                            x["name"] or "(name resolves at regen)"))
        if any_meaningful:
            n_meaningful_flags += 1
        print("flag %d  (%d lots%s)" % (f, len(lots),
                                        "; has MEANINGFUL sibling" if any_meaningful else ""))
        for ln in lines:
            print(ln)
    print("\n%d shared flags total; %d with at least one MEANINGFUL (policy) sibling; "
          "allowlist today: see gen_data.CO_CHECK_FLAGS" % (len(shared), n_meaningful_flags))


def render(rows):
    out = [HEADER]
    for (flag, table, lot, slot, cat, iid, num, gt, nm) in rows:
        out.append("\t".join(str(x) for x in (flag, table, lot, slot, cat, iid, num, gt, nm)))
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="drift gate: exit 1 if flag_lots.tsv is stale")
    ap.add_argument("--report", action="store_true",
                    help="co-check candidate report from the COMMITTED tsv (no artifacts needed)")
    args = ap.parse_args()
    if args.report:
        report()
        return
    rows = build_rows()
    text = render(rows)
    # summary: how many flags, how many are SHARED (>1 awarded lot) -> the co-check candidates.
    from collections import defaultdict
    lots_per_flag = defaultdict(set)
    for (flag, table, lot, *_rest) in rows:
        lots_per_flag[flag].add((table, lot))
    shared = {f: v for f, v in lots_per_flag.items() if len(v) > 1}
    if args.check:
        cur = open(OUT, encoding="utf-8").read() if os.path.isfile(OUT) else ""
        if cur != text:
            print("STALE: flag_lots.tsv differs from a fresh datamine. Run: python tools/datamine_flag_lots.py",
                  file=sys.stderr)
            sys.exit(1)
        print("flag_lots.tsv up to date (%d rows, %d flags, %d SHARED-flag co-check candidates)"
              % (len(rows), len(lots_per_flag), len(shared)))
        return
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("wrote %s: %d rows, %d flags, %d SHARED-flag co-check candidates"
          % (OUT, len(rows), len(lots_per_flag), len(shared)))


if __name__ == "__main__":
    main()
