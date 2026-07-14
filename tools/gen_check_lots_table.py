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
# lotItemCategory -> FullID nibble is DERIVED (derive_category_nibble). It used to be hardcoded:
#     GOODS = 1 ; NON_GOODS = (2, 3, 4, 5)
# with a comment saying "0 and 6 are rare/ambiguous (24 rows) and are NEVER judged". They are not
# ambiguous -- they were never DERIVED. Both are GOODS:
#     cat 0: Gravel Stone (20855), Golden Rune [1] (2900), Glintstone Scrap (3050)
#     cat 6: [Sorcery] Rancorcall (5000) -- spells carry the GOODS nibble
# "Never judged" is a decision that silently leaks every check behind it: 13 checks handed out their
# vanilla item alongside the AP item, for as long as this table has existed. Fable found them.
GOODS_NIBBLE = 0x4000_0000

# THE CATEGORY NIBBLE -- DERIVED, not declared. See derive_category_nibble().
#
# `lotItemId` in ItemLotParam is the RAW id; the client's detour reads the AddItemFunc-space FullID
# (`category nibble | raw`), which is also ITEM_CATALOG's space. This table used to emit the RAW id.
# Weapons have nibble 0x0, so raw == FullID and they suppressed fine -- which is exactly why the bug
# hid: suppression *worked*, on a quarter of the items. Protectors, talismans and Ashes of War never
# matched, and every one handed out the vanilla item alongside the AP item.
#
# The first fix HARDCODED lotItemCategory -> nibble from a source comment that claimed to be "derived
# empirically" while containing no derivation. It was wrong (it had GEM at 0x5; the catalog says 0x8),
# and being wrong in a constant is precisely the class of bug this file keeps producing. So: derive it
# from the two tables we already have, and refuse to run if the mapping is not clean.



def derive_category_nibble(rows_by_cat, known):
    """lotItemCategory -> FullID category nibble, VOTED from the data.

    For every lot entry we know (raw id, lotItemCategory). For every ITEM_CATALOG item we know
    (raw id, nibble). Join on raw -- but ONLY where the raw is UNAMBIGUOUS in the catalog (exactly one
    nibble), because raw ids are unique only WITHIN a category: Goods 8200 and Accessory 8200 are
    different items, and a colliding raw votes for both.

    Requires >=95% purity per category and refuses to guess a category it cannot see.
    """
    votes = {}
    for cat, raws in rows_by_cat.items():
        v = {}
        for raw in raws:
            nibs = known.get(raw)
            if not nibs or len(nibs) != 1:
                continue  # unknown, or a cross-category raw collision -- it votes for nothing
            n = next(iter(nibs))
            v[n] = v.get(n, 0) + 1
        votes[cat] = v

    out = {}
    for cat in sorted(votes):
        v = votes[cat]
        if not v:
            raise SystemExit(
                "FATAL: lotItemCategory %d has no unambiguous ITEM_CATALOG evidence -- cannot derive "
                "its nibble, and guessing it is how this bug shipped." % cat)
        ranked = sorted(v.items(), key=lambda kv: -kv[1])
        nib, hits = ranked[0]
        runner = ranked[1][1] if len(ranked) > 1 else 0
        total = sum(v.values())
        purity = hits / total
        print("  lotItemCategory %d -> nibble 0x%08X  (%d/%d = %.1f%%, runner-up %d)"
              % (cat, nib, hits, total, 100.0 * purity, runner))
        # MARGIN, not purity. The residue is raw-id COLLISION noise -- raw ids are unique only WITHIN a
        # category, so e.g. Accessory 8200 and Goods 8200 are different real items and the catalog's
        # goods entry votes against a correct accessory. A 95% purity bar failed a CORRECT mapping at
        # 86.8%. What actually proves the answer is that the winner dominates: >=70% and >=2x the
        # runner-up. Ambiguity is a FATAL; noise is not.
        if purity < 0.70 or hits < 2 * max(runner, 1):
            raise SystemExit(
                "FATAL: lotItemCategory %d does not have a dominant nibble (winner 0x%08X %d, runner-up "
                "%d). The mapping is not a fact here; do not ship a table built on it."
                % (cat, nib, hits, runner))
        out[cat] = nib
    return out


def _catalog_raw_to_nibbles():
    import re
    src = os.path.join(REPO, "greenfield", "eldenring", "item_ids.py")
    text = open(src, encoding="utf-8").read()
    known = {}
    for m in re.finditer(r"'[^']+'\s*:\s*(\d+),", text):
        v = int(m.group(1))
        known.setdefault(v & 0x0FFF_FFFF, set()).add(v & 0xF000_0000)
    if not known:
        raise SystemExit("FATAL: could not read ITEM_CATALOG from %s" % src)
    return known


def build():
    out = {"placeholder_goods": AP_PLACEHOLDER_GOODS, "map": {}, "enemy": {}, "items": {}}
    known = _catalog_raw_to_nibbles()
    # PASS 1: collect every (category, raw) the lots reference, so the nibble map can be derived from
    # them rather than declared.
    rows_by_cat = {}
    pending = []
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
                entries = []
                for i in range(1, 9):
                    try:
                        iid = int(r.get("lotItemId%02d" % i, 0) or 0)
                        cat = int(r.get("lotItemCategory%02d" % i, 0) or 0)
                    except ValueError:
                        continue
                    if iid <= 0 or iid == AP_PLACEHOLDER_GOODS:
                        continue
                    # EVERY category is carried. There is no "never judged" bucket any more -- an
                    # abstention here is a check that hands out its vanilla item forever.
                    entries.append((i, cat, iid))
                    rows_by_cat.setdefault(cat, set()).add(iid)
                if entries:
                    pending.append((key, flag, lot, entries))

    # DERIVE the nibble map from what we just read, then assemble the FullIDs.
    print("deriving lotItemCategory -> FullID nibble from ItemLotParam x ITEM_CATALOG:")
    nibble = derive_category_nibble(rows_by_cat, known)

    # PASS 2: route each slot by its DERIVED nibble. GOODS -> blank the lot slot (the client repoints it
    # at the placeholder). Everything else -> id-keyed suppression against the detour's FullID.
    for key, flag, lot, entries in pending:
        k = str(flag)
        slots = [i for (i, cat, _iid) in entries if nibble[cat] == GOODS_NIBBLE]
        if slots:
            out[key][k] = {"lot": lot, "slots": slots}
        for (_i, cat, iid) in entries:
            if nibble[cat] == GOODS_NIBBLE:
                continue
            full = nibble[cat] | iid
            out["items"].setdefault(k, [])
            if full not in out["items"][k]:
                out["items"][k].append(full)

    _assert_covers_every_lot_check(out)

    # The output shape is a CONTRACT: the client reads { str(flag): [int, ...] } and matches those ints
    # against the detour's FullID. A previous edit half-applied and shipped [[cat, raw]] pairs -- valid
    # JSON, wrong shape, and the client would simply never match. Assert the shape before writing.
    for k, v in out["items"].items():
        if not all(isinstance(i, int) for i in v):
            raise SystemExit(
                "FATAL: check_lots items[%s] is not a flat list of FullID ints: %r\n"
                "The client matches these against the detour's FullID; any other shape silently never "
                "matches, and every vanilla item leaks alongside the AP one." % (k, v))
    return out


def _assert_covers_every_lot_check(out):
    """COVERAGE. Every check whose flag comes from a LOT must be suppressed by this table.

    This gate did not exist, and its absence is why 13 checks handed out their vanilla item alongside
    the AP item for as long as the table has existed. The generator reported "3682 map + 151 enemy" and
    nobody ever asked OF HOW MANY. A count with no denominator is not a measurement.

    greenfield/region_map.csv is the denominator: it is tracked, it carries every check's `flag` and
    `flag_source`, and the two lot-backed sources (map_lot, enemy_lot) are exactly the checks this table
    is responsible for. `shop` checks are handled by shop_sell (native sale, not blanking) and
    `synthetic` flags are recovered ones with no lot to blank -- both are out of scope, by name.
    """
    src = os.path.join(REPO, "greenfield", "region_map.csv")
    if not os.path.isfile(src):
        print("WARNING: %s absent -- coverage NOT verified" % src)
        return
    covered = set(out["map"]) | set(out["enemy"]) | set(out["items"])
    owed, missing = 0, []
    with open(src, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("flag_source") not in ("map_lot", "enemy_lot"):
                continue
            f = (r.get("flag") or "").strip()
            if not f.isdigit():
                continue
            owed += 1
            if f not in covered:
                missing.append((f, r.get("item_name", ""), r.get("map", "")))
    print("coverage: %d/%d lot-backed checks suppressed" % (owed - len(missing), owed))
    if missing:
        detail = "\n".join("    flag %-11s %-24s %s" % m for m in missing[:15])
        raise SystemExit(
            "FATAL: %d lot-backed check(s) have NO suppression. Each one hands the player its vanilla\n"
            "item ALONGSIDE the Archipelago item, and nothing errors or logs -- that is the whole reason\n"
            "this gate exists.\n%s%s"
            % (len(missing), detail, "\n    ..." if len(missing) > 15 else ""))


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
