#!/usr/bin/env python3
r"""datamine_flagless_enemy_drops.py -- size the SUPPRESSION BLIND SPOT: enemy drops with no flag.

WHY (SPEC-flagless-enemy-drops.md). Every layer of check suppression is FLAG-KEYED, and the corpus
that feeds it drops unflagged rows on purpose -- `datamine_flag_lots.py`:

    if lot <= 0 or flag <= 0:          # unflagged/farmable -> not a check
        continue

Correct for building the CHECK list (no flag, nothing for the poll to observe), but flag_lots.tsv is
also the input to check_lots_table.json, which is the input to the client's blank pass. So an
unflagged enemy lot is invisible three layers deep and nothing downstream can name it, let alone
blank it.

MOTIVATING CASE (rule 11): boblerrr, 2026-08-07, live 0.3.7 -- killed the enemy occupying Ancient
Dragon Senessax's arena and got Ancient Dragon Smithing Stone + Somber Ancient Dragon Smithing Stone
as real items, while the arena's own reward lot (f2053397000 -> lot 2054390000) WAS correctly blanked
and re-armed two minutes before the kill.

THIS TOOL MEASURES. It does not suppress and must not: an unflagged lot is unflagged BECAUSE it is
repeatable, so blanking one eats every copy the player would legitimately farm -- the same reason
features/check_item_flags.py declines id-keyed suppression for farmables. Sizing the population is
what makes that ruling possible.

Run:
    python tools/datamine_flagless_enemy_drops.py           # report only
    python tools/datamine_flagless_enemy_drops.py --emit    # + write greenfield/flagless_enemy_drops.tsv
"""
import argparse
import collections
import csv
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.dirname(HERE)
VV = os.environ.get("ER_ARTIFACTS_VV") or os.path.join(
    REPO, "elden_ring_artifacts", "vanilla_er", "vanilla_er")
MSG = os.path.join(REPO, "elden_ring_artifacts", "msg")
OUT = os.path.join(REPO, "greenfield", "flagless_enemy_drops.tsv")

# lotItemCategory -> the FMG family that NAMES the id. Same table gen_data derived empirically
# (gen_data.py:583); restated here rather than imported because gen_data needs Archipelago.
_LOT_CAT_FMG = {0: "goods", 1: "goods", 2: "weapon", 3: "protector", 4: "accessory",
                5: "goods", 6: "goods"}
_FMG_GLOB = {"weapon": "WeaponName", "protector": "ProtectorName",
             "accessory": "AccessoryName", "goods": "GoodsName"}


def _rows(fn):
    p = os.path.join(VV, fn)
    if not os.path.isfile(p):
        raise SystemExit("FATAL: %s missing -- run tools/gen_inputs.py --ensure elden_ring_artifacts" % p)
    with open(p, newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            yield r


def _names():
    """(family, raw id) -> display name, from the base + both DLC msgbnds."""
    out = {}
    for fam, stem in _FMG_GLOB.items():
        for d in ("item-msgbnd-dcx", "item_dlc01-msgbnd-dcx", "item_dlc02-msgbnd-dcx"):
            for p in glob.glob(os.path.join(MSG, d, "*%s*.fmg.xml" % stem)):
                try:
                    txt = open(p, encoding="utf-8", errors="replace").read()
                except OSError:
                    continue
                for m in re.finditer(r'<text id="(\d+)"[^>]*>(.*?)</text>', txt, re.S):
                    nm = m.group(2).strip()
                    if nm and nm not in ("%null%", "[ERROR]"):
                        out.setdefault((fam, int(m.group(1))), nm)
    return out


def _goods_ids():
    return {int(r["ID"]) for r in _rows("EquipParamGoods.csv") if (r.get("ID") or "").strip().isdigit()}


def collect():
    names, goods = _names(), _goods_ids()
    # NpcParam.itemLotId_enemy -> which NPCs own a lot (one lot is shared by many)
    owners = collections.defaultdict(set)
    for r in _rows("NpcParam.csv"):
        try:
            lot, npc = int(r.get("itemLotId_enemy", 0) or 0), int(r["ID"])
        except (ValueError, KeyError, TypeError):
            continue
        if lot > 0:
            owners[lot].add(npc)

    flag_cols = None
    out, tally = [], collections.Counter()
    for r in _rows("ItemLotParam_enemy.csv"):
        if flag_cols is None:
            flag_cols = [c for c in r if c and c.startswith("getItemFlagId")]
        try:
            lot = int(list(r.values())[0])
        except (ValueError, IndexError):
            continue
        if lot <= 0:
            continue
        flagged = any(int(r.get(c, 0) or 0) > 0 for c in flag_cols)
        tally["enemy lots"] += 1
        if flagged:
            tally["  flagged (already a check candidate)"] += 1
            continue
        tally["  FLAGLESS"] += 1
        if lot not in owners:
            tally["    ...but no NpcParam references it -- unreachable, ignored"] += 1
            continue
        for i in range(1, 9):
            try:
                iid = int(r.get("lotItemId%02d" % i, 0) or 0)
                cat = int(r.get("lotItemCategory%02d" % i, 0) or 0)
                pts = int(r.get("lotItemBasePoint%02d" % i, 0) or 0)
                num = int(r.get("lotItemNum%02d" % i, 0) or 0)
            except (ValueError, TypeError):
                continue
            if iid <= 0:
                continue
            nm = names.get((_LOT_CAT_FMG.get(cat, "goods"), iid), "")
            if not nm:
                tally["    slot: unnamed id (cut content) -- skipped"] += 1
                continue
            tally["    slot: NAMED award"] += 1
            if iid in goods:
                tally["      ...of which GOODS"] += 1
            out.append((lot, i, iid, cat, pts, num, "goods" if iid in goods else "",
                        nm, ";".join(str(n) for n in sorted(owners[lot]))))
    return out, tally


HEADER = "lot\tslot\titem_id\tcategory\tbase_point\tnum\tis_goods\tname\tnpc_param_ids"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--emit", action="store_true")
    args = ap.parse_args(argv)
    rows, tally = collect()
    for k, v in tally.items():
        print(f"{k:<58} {v}")

    UPGRADE = re.compile(r"smithing stone|somber", re.I)
    hundred = [r for r in rows if r[4] >= 100]
    upg = [r for r in rows if UPGRADE.search(r[7])]
    print(f"\nnamed flagless award slots               {len(rows)}")
    print(f"  base_point >= 100 (guaranteed)         {len(hundred)}")
    print(f"  upgrade materials (smithing/somber)    {len(upg)}")
    print(f"  distinct lots                          {len({r[0] for r in rows})}")
    print(f"  distinct NPCs referencing them         {len({n for r in rows for n in r[8].split(';') if n})}")
    top = collections.Counter(r[7] for r in rows).most_common(12)
    print("\n  most common awards:")
    for nm, c in top:
        print(f"    {c:>5}  {nm}")
    if upg:
        print("\n  UPGRADE MATERIAL rows (the ones that distort a run):")
        for r in sorted(upg, key=lambda x: -x[4])[:15]:
            print(f"    lot {r[0]:>10} slot {r[1]} pts {r[4]:>4} x{r[5]}  {r[7]}  npcs={r[8][:40]}")
    if args.emit:
        with open(OUT, "w", encoding="utf-8", newline="") as fh:
            fh.write("# AUTO-GENERATED by tools/datamine_flagless_enemy_drops.py -- DO NOT EDIT.\n")
            fh.write("# ItemLotParam_enemy rows with NO getItemFlagId* that award a NAMED item, joined\n")
            fh.write("# to the NpcParam rows that reference them. MEASUREMENT ONLY -- see\n")
            fh.write("# SPEC-flagless-enemy-drops.md; suppression policy is a separate ruling.\n")
            fh.write(HEADER + "\n")
            for r in sorted(rows):
                fh.write("\t".join(str(x) for x in r) + "\n")
        print(f"\nwrote {len(rows)} row(s) -> {os.path.relpath(OUT, REPO)}")
    else:
        print("\n(report only -- pass --emit to write the tsv)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
