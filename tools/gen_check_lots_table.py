#!/usr/bin/env python3
r"""gen_check_lots_table.py -- the VANILLA-SUPPRESSION table, for ANY apworld.

THE PROBLEM (measured in-game, 2026-07-13, first Bedrock playtest):

    vanilla suppressor INERT: checkItemFlags empty/absent in slot_data

Our client blanks a check's vanilla ware AT THE SOURCE -- it rewrites the check's own
ItemLotParam row so the game never hands the item over. But it learns WHICH lots to blank from
`checkLotBlankMap` / `checkLotBlankEnemy` in slot_data, and only OUR apworld emits those. Drive a
foreign apworld (Bedrock's) and the tables are empty: every check pays out the VANILLA item AND the
AP item. Playable, wrong.

THE INSIGHT -- and it is the same one that made shoplineup_flags.json work:

    the blank-list is derived from ItemLotParam: flag -> lot -> which slots hold a GOODS ware.
    That is GAME data. It is not seed data. It is identical for every seed and every apworld.

So SHIP IT STATIC. The client already knows the seed's check FLAGS (from `locationFlags`, or derived
from Bedrock's matt slot keys by key_resolver). Intersect those flags with this table and you have
the blank-list -- for ANY apworld, with zero changes on its side.

Emits greenfield/eldenring/check_lots_table.json:

    {"placeholder_goods": 8852,
     "map":   {"<flag>": {"lot": <lot>, "slots": [1..8]}, ...},   # GOODS slots -> blank at the lot
     "enemy": {"<flag>": {"lot": <lot>, "slots": [1..8]}, ...},
     "items": {"<flag>": [<ER item id>, ...]}}                     # WEAPON/ARMOR wares -> suppress by id

TWO MECHANISMS, because the game gives us two problems:

  * GOODS wares are blanked AT THE LOT (`map`/`enemy`): point the check's goods slot at the
    placeholder row, and the game hands over nothing. Suppressing goods BY ID would be a disaster --
    Golden Rune [1] backs 46 checks, so every Golden Rune you ever picked up would be eaten.
  * WEAPON / ARMOR wares are suppressed BY ITEM ID (`items` -> the client's `checkItemFlags`). That
    is sound for them and only for them: a weapon is essentially never farmable, so it lives in the
    check-only set and cannot eat a legitimate source.

Both halves derive from the same ItemLotParam rows, so both ship here. Without the `items` half a
foreign seed still double-dips on every weapon/armor check (517 of Bedrock's 3022, measured).

NOT filtered to our check flags. The whole point is that a foreign apworld's flag set is different
from ours -- filtering to `_CHECK_FLAGS_ALL` (which gen_data does, correctly, for our own seeds)
would silently drop exactly the rows a foreign world needs.

    python tools/gen_check_lots_table.py            # regenerate
    python tools/gen_check_lots_table.py --check    # CI drift gate (exit 1 if stale)
"""
import argparse
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.dirname(HERE)
VV = os.path.join(REPO, "elden_ring_artifacts", "vanilla_er", "vanilla_er")
OUT = os.path.join(REPO, "greenfield", "eldenring", "check_lots_table.json")

# The one goods row the client suppresses unconditionally. It EXISTS (so the game can grant it), has
# no GoodsName entry, and is referenced by no lot / shop / recipe -- so it can never eat a real item.
# Must match gen_data.AP_PLACEHOLDER_GOODS.
AP_PLACEHOLDER_GOODS = 8852
GOODS = 1
# lotItemCategory, derived empirically over every lot row: 2=Weapon 3=Protector 4=Accessory 5=Gem.
# 0 and 6 are rare/ambiguous (24 rows) and are NEVER judged -- see the item-existence guard.
NON_GOODS = (2, 3, 4, 5)

# THE CATEGORY NIBBLE. `lotItemId` in ItemLotParam is the RAW id; the client's detour reads the
# AddItemFunc-space **FullID** (`category nibble | raw`), which is also the id space ITEM_CATALOG uses.
# This table used to emit the RAW id. Weapons have nibble 0x0, so raw == FullID and they suppressed
# fine -- which is exactly why the bug hid: suppression *worked*, on a quarter of the items. Protectors,
# talismans and GEMS (Ashes of War) never matched, so every one of them handed out the vanilla item
# alongside the AP item. Alaric caught it on an Ash of War.
#
# Nibbles measured against ITEM_CATALOG, not assumed -- note GEM is 0x8, NOT 0x5 as the lotItemCategory
# number would suggest:
#   0x00000000 Weapon (344)   0x10000000 Protector (344)   0x20000000 Accessory (115)
#   0x40000000 Goods  (697)   0x80000000 Gem/AoW    (88)
CATEGORY_NIBBLE = {
    2: 0x00000000,   # Weapon
    3: 0x10000000,   # Protector
    4: 0x20000000,   # Accessory
    5: 0x80000000,   # Gem -- Ash of War
}


def build():
    out = {"placeholder_goods": AP_PLACEHOLDER_GOODS, "map": {}, "enemy": {}, "items": {}}
    for fn, key in (("ItemLotParam_map.csv", "map"), ("ItemLotParam_enemy.csv", "enemy")):
        p = os.path.join(VV, fn)
        if not os.path.isfile(p):
            raise SystemExit("FATAL: %s missing -- elden_ring_artifacts required" % p)
        with open(p, newline="", encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                try:
                    lot = int(list(r.values())[0])
                    flag = int(r.get("getItemFlagId", 0) or 0)
                except (ValueError, IndexError):
                    continue
                # No flag => farmable/unflagged => NOT a check under anyone's model. Leave it alone;
                # blanking it would eat a legitimate drop source.
                if lot <= 0 or flag <= 0:
                    continue
                slots, ids = [], []
                for i in range(1, 9):
                    try:
                        iid = int(r.get("lotItemId%02d" % i, 0) or 0)
                        cat = int(r.get("lotItemCategory%02d" % i, 0) or 0)
                    except ValueError:
                        continue
                    if iid <= 0 or iid == AP_PLACEHOLDER_GOODS:
                        continue
                    if cat == GOODS:
                        slots.append(i)
                    elif cat in NON_GOODS:
                        # weapon/armor/talisman/AoW -> id-keyed suppression (checkItemFlags), keyed by
                        # the FullID the detour actually sees. See CATEGORY_NIBBLE.
                        ids.append(CATEGORY_NIBBLE[cat] | iid)
                if slots:
                    out[key][str(flag)] = {"lot": lot, "slots": slots}
                if ids:
                    out["items"].setdefault(str(flag), [])
                    for i in ids:
                        if i not in out["items"][str(flag)]:
                            out["items"][str(flag)].append(i)
    _assert_ids_are_real_items(out)
    return out


def _assert_ids_are_real_items(out):
    """Every id-keyed suppression entry must be an item the game actually HAS.

    This is the guard that would have caught the raw-vs-FullID bug the day it shipped. The client
    suppresses a pickup by matching the detour's FullID against these keys; an id in the wrong encoding
    simply never matches, and a suppressor that never fires looks EXACTLY like a suppressor with nothing
    to do. It logged "ARMED for 865 check item ids" while quietly leaking every Ash of War.

    ITEM_CATALOG is generated, tracked, and in the FullID space -- so it is the oracle. If most of what
    we emit is not in it, we are emitting nonsense; fail rather than ship a table that silently no-ops.
    """
    import re

    src = os.path.join(REPO, "greenfield", "eldenring", "item_ids.py")
    text = open(src, encoding="utf-8").read()
    known = {int(m.group(1)) for m in re.finditer(r"'[^']+'\s*:\s*(\d+),", text)}
    if not known:
        raise SystemExit("FATAL: could not read ITEM_CATALOG from %s -- cannot validate the encoding" % src)

    emitted = {i for ids in out["items"].values() for i in ids}
    if not emitted:
        return
    hits = len(emitted & known)
    frac = hits / len(emitted)
    print("id-encoding check: %d/%d (%.1f%%) of the id-keyed suppressions are real ITEM_CATALOG items"
          % (hits, len(emitted), 100.0 * frac))
    if frac < 0.80:
        raise SystemExit(
            "FATAL: only %.1f%% of the emitted suppression ids exist in ITEM_CATALOG. They are almost\n"
            "certainly in the wrong id space -- lotItemId is RAW, the client's detour reads the FullID\n"
            "(category nibble | raw). A table in the wrong space does not error, it just never matches,\n"
            "and every vanilla item leaks alongside the AP one. See CATEGORY_NIBBLE." % (100.0 * frac))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="CI drift gate: fail if committed output is stale")
    a = ap.parse_args()
    tbl = build()
    txt = json.dumps(tbl, indent=1, sort_keys=True) + "\n"
    n_map, n_ene, n_it = len(tbl["map"]), len(tbl["enemy"]), len(tbl["items"])
    both = set(tbl["map"]) & set(tbl["enemy"])
    print("check_lots_table: %d map flag(s), %d enemy flag(s), %d in BOTH; %d flag(s) with "
          "weapon/armor wares (id-keyed)" % (n_map, n_ene, len(both), n_it))
    if a.check:
        if not os.path.isfile(OUT):
            print("STALE: %s missing -- run tools/gen_check_lots_table.py" % OUT)
            sys.exit(1)
        if open(OUT, encoding="utf-8").read() != txt:
            print("STALE: %s does not match a fresh derivation -- regenerate and commit" % OUT)
            sys.exit(1)
        print("OK: up to date (%d map + %d enemy + %d id-keyed)" % (n_map, n_ene, n_it))
        return
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(txt)
    print("wrote %s (%d bytes)" % (OUT, len(txt)))


if __name__ == "__main__":
    main()
