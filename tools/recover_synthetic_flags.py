#!/usr/bin/env python3
"""Recover the REAL acquisition flag for every phantom (synthetic) check in region_map.csv.

Background
----------
`greenfield/region_map.csv` contains rows with `flag_source=synthetic`,
`method=synthetic_areacode`, `map=PENDING`.  Their `flag` is an INVENTED id that
exists nowhere in the shipped game data (not in ItemLotParam_map /
ItemLotParam_enemy `getItemFlagId*`, not in ShopLineupParam `eventFlag_forStock`,
not referenced by any EMEVD).  Elden Ring event flags are group-allocated: an
unallocated id is a no-op, so the client can never observe such a flag flip and
the check can never be sent.

This tool tries to recover the real flag for each phantom, purely from data:

  * SHOP purchases  -> ShopLineupParam row for (item, merchant-block); its
                       `eventFlag_forStock` is the real flag.
  * WORLD pickups   -> msb_flag_region.tsv (flag -> map, item_lot_id) joined to
                       ItemLotParam_map, scoped to the maps that belong to the
                       region the phantom is assigned to.
  * ENEMY drops     -> same, source=enemy / ItemLotParam_enemy.

Evidence standard (deliberately strict; prefer AMBIGUOUS over a guess)
----------------------------------------------------------------------
A candidate must match on ITEM **and** PLACEMENT.  Item alone is never enough:
a naive item-name -> ShopLineupParam match "recovers" a *world* pickup of
Smithing Stone [8] to some merchant's stock flag, which is simply wrong.
  - shop candidates are only generated for phantoms whose annotation says the
    check IS a shop purchase, and are scoped to that merchant's ShopLineupParam
    100-block (inferred from the group of phantoms naming the same merchant at
    the same map-code).
  - world/enemy candidates are only generated from lots the MSB actually places
    in a map that belongs to the phantom's region.

Verdicts
--------
  RECOVERED     exactly one real flag, and that flag is NOT already used by
                another AP location -> safe to rebind the phantom to it.
  DUPLICATE     exactly one real flag, but it is ALREADY claimed by another AP
                location -> the phantom row duplicates an existing check; the
                fix is to DELETE the row, not rebind it (rebinding would put two
                AP locations on one flag).
  AMBIGUOUS     more than one defensible candidate.
  UNRECOVERABLE no candidate survives the evidence standard.

Writes: greenfield/synthetic_flag_recovery.tsv   (read-only w.r.t. everything else)
Run:    python3 tools/recover_synthetic_flags.py
"""
from __future__ import annotations

import collections
import csv
import importlib.util
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARAMS = os.path.join(ROOT, "elden_ring_artifacts", "vanilla_er", "vanilla_er")
GF = os.path.join(ROOT, "greenfield")
OUT = os.path.join(GF, "synthetic_flag_recovery.tsv")

# ItemLotParam lotItemCategory -> FullID top nibble.  Verified empirically against
# the ~4k already-bound map_lot rows in region_map.csv: cat1=Goods(4),
# cat2=Weapon(0), cat3=Protector(1), cat4=Accessory(2), cat5=Gem/Ash-of-War(8);
# cat0 slots resolve as Goods.
LOT_CAT = {"0": 4, "1": 4, "2": 0, "3": 1, "4": 2, "5": 8}
# ShopLineupParam equipType -> FullID top nibble (4 = Gem / Ash of War).
SHOP_ET = {"0": 0, "1": 1, "2": 2, "3": 4, "4": 8}


def load_rows(path):
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        return list(csv.DictReader(fh))


def load_item_catalog():
    spec = importlib.util.spec_from_file_location(
        "gf_item_ids", os.path.join(GF, "eldenring_gf", "item_ids.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.ITEM_CATALOG


def parse_annotation(item_name):
    """'LG/(CE): Telescope - Kale Shop' -> (mapcode, item, hint)."""
    mapcode, rest = "", item_name
    if ": " in item_name:
        mapcode, rest = item_name.split(": ", 1)
    if " - " in rest:
        item, hint = rest.split(" - ", 1)
    else:
        item, hint = rest, ""
    item = re.sub(r"\s+x\d+$", "", item.strip())
    return mapcode.strip(), item.strip(), hint.strip()


def classify(hint, item):
    h = hint.lower()
    if ("shop" in h or "merchant" in h or "kalé" in h or "twin maiden" in h
            or "enia" in h or "pidia" in h):
        return "shop"
    if "boss drop" in h:
        return "boss"
    if "enemy drop" in h or "scarab" in h:
        return "enemy"
    if "given by" in h:
        return "npc"
    return "world"


def merchant_key(mapcode, hint):
    """Locality-scoped merchant identity, e.g. ('LG/(CE)', 'kale')."""
    h = hint.lower()
    for name, key in (("kalé", "kale"), ("twin maiden", "twinmaiden"),
                      ("enia", "enia"), ("pidia", "pidia"),
                      ("nomadic merchant", "nomadic"), ("merchant", "merchant")):
        if name in h:
            return (mapcode, key)
    return (mapcode, "shop")


def main():
    catalog = load_item_catalog()
    region_map = load_rows(os.path.join(GF, "region_map.csv"))
    lots_map = load_rows(os.path.join(PARAMS, "ItemLotParam_map.csv"))
    lots_enemy = load_rows(os.path.join(PARAMS, "ItemLotParam_enemy.csv"))
    shop = load_rows(os.path.join(PARAMS, "ShopLineupParam.csv"))

    msb = []
    with open(os.path.join(GF, "msb_flag_region.tsv"), encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            p = line.rstrip("\n").split("\t")
            if len(p) < 5 or p[0] == "flag":
                continue
            msb.append({"flag": p[0], "map_id": p[1], "lot": p[2],
                        "name": p[3], "source": p[4]})

    # ---- real-flag universe -------------------------------------------------
    lot_flag_index = collections.defaultdict(list)
    for table, rows in (("map", lots_map), ("enemy", lots_enemy)):
        for r in rows:
            for c in [("getItemFlagId%02d" % i) for i in range(1, 9)] + ["getItemFlagId"]:
                v = r.get(c, "0")
                if v and v not in ("0", "-1"):
                    lot_flag_index[v].append((table, r["ID"]))
    shop_flags = set()
    for r in shop:
        for c in ("eventFlag_forStock", "eventFlag_forRelease"):
            v = r.get(c, "0")
            if v and v not in ("0", "-1"):
                shop_flags.add(v)
    real_flags = set(lot_flag_index) | shop_flags | {r["flag"] for r in msb}

    lot_by_id = {"map": {r["ID"]: r for r in lots_map},
                 "enemy": {r["ID"]: r for r in lots_enemy}}

    def lot_slots(table, lot_id):
        """[(FullID, slot_flag_or_None)] for every real item slot of a lot."""
        r = lot_by_id[table].get(lot_id)
        if not r:
            return []
        out = []
        for i in range(1, 9):
            iid = r.get("lotItemId%02d" % i, "0")
            cat = r.get("lotItemCategory%02d" % i, "0")
            if not iid or iid in ("0", "-1"):
                continue
            top = LOT_CAT.get(cat)
            if top is None:
                continue
            sf = r.get("getItemFlagId%02d" % i, "0")
            if not sf or sf in ("0", "-1"):
                sf = r.get("getItemFlagId", "0")
            out.append(((top << 28) + int(iid), sf if sf and sf not in ("0", "-1") else None))
        return out

    # ---- claimed flags ------------------------------------------------------
    claimed = {r["flag"]: r for r in region_map if r["flag_source"] != "synthetic"}

    # ---- map_id for ANY lot -------------------------------------------------
    # ER item-lot IDs encode their map: 8-digit AABBnnnn -> mAA_BB;
    # 10-digit 10XXYYnnnn -> m60_XX_YY; 20XXYYnnnn -> m61_XX_YY.
    # Validated against msb_flag_region.tsv: 2290/2308 exact, 18 neighbour-tile
    # disagreements, 318 short (event) lot ids that carry no map -> those fall
    # back to the MSB's own map_id.
    def lot_map(lot_id):
        s_ = lot_id
        if len(s_) == 8 and s_[0] != '0':
            return "m%s_%s" % (s_[0:2], s_[2:4])
        if len(s_) == 10 and s_[0] in '12' and s_[1] == '0':
            return "m6%s_%s_%s" % ('0' if s_[0] == '1' else '1', s_[2:4], s_[4:6])
        return None

    msb_map_by_lot = {}
    for r in msb:
        msb_map_by_lot.setdefault(r["lot"], r["map_id"])

    def map_of(table, lot_id):
        if table == "enemy":
            return msb_map_by_lot.get(lot_id)          # enemy lots: only the MSB knows
        return msb_map_by_lot.get(lot_id) or lot_map(lot_id)

    # ---- AP region of every already-bound flag, from the generated data.py ----
    spec = importlib.util.spec_from_file_location(
        "gf_data", os.path.join(GF, "eldenring_gf", "data.py"))
    dmod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dmod)
    ap_region_of_flag = {}
    for reg, locs in dmod.LOCATIONS.items():
        for _name, _ap, flag in locs:
            ap_region_of_flag[str(flag)] = reg

    # map_id -> AP region, by plurality vote over every already-bound (non-phantom)
    # flag whose lot we can place on the map.
    votes = collections.defaultdict(collections.Counter)
    for flag, places in lot_flag_index.items():
        reg = ap_region_of_flag.get(flag)
        if not reg or flag not in claimed:
            continue
        for table, lot_id in places:
            mid = map_of(table, lot_id)
            if mid:
                votes[mid][reg] += 1
    map_region = {mid: c.most_common(1)[0][0] for mid, c in votes.items()}

    # Overworld tiles with no bound item at all get no vote.  Fill them in from
    # their 8-neighbourhood (m60_XX_YY / m61_XX_YY are a grid), 2 rounds.
    def tile(mid):
        p_ = mid.split("_")
        if len(p_) == 3 and p_[0] in ("m60", "m61"):
            return p_[0], int(p_[1]), int(p_[2])
        return None
    every_map = {r["map_id"] for r in msb} | set(map_region)
    for r in lots_map:                       # every tile any item lot lives in
        m_ = lot_map(r["ID"])
        if m_:
            every_map.add(m_)
    all_tiles = {t for t in (tile(m) for m in every_map) if t}
    filled = {}
    for _round in range(2):
        for grid, x, y in all_tiles:
            mid = "%s_%02d_%02d" % (grid, x, y)
            if mid in map_region:
                continue
            nb = collections.Counter()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    n = map_region.get("%s_%02d_%02d" % (grid, x + dx, y + dy))
                    if n:
                        nb[n] += 1
            if nb:
                filled[mid] = nb.most_common(1)[0][0]
        map_region.update(filled)

    region_to_maps = collections.defaultdict(set)
    for mid, reg in map_region.items():
        region_to_maps[reg].add(mid)
    neighbour_filled = set(filled)

    # every (item -> lots that grant it), over both lot tables
    lots_by_item = collections.defaultdict(list)
    for table, rows in (("map", lots_map), ("enemy", lots_enemy)):
        for r in rows:
            for full_id, sf in lot_slots(table, r["ID"]):
                lots_by_item[full_id].append((table, r["ID"], sf))

    # ---- shop index ---------------------------------------------------------
    shop_by_item = collections.defaultdict(list)
    for r in shop:
        top = SHOP_ET.get(r["equipType"])
        if top is None:
            continue
        try:
            shop_by_item[(top << 28) + int(r["equipId"])].append(r)
        except ValueError:
            pass

    # ---- phantoms -----------------------------------------------------------
    phantoms = [r for r in region_map
                if r["flag_source"] == "synthetic" and r["flag"] not in real_flags]
    real_synth = [r for r in region_map
                  if r["flag_source"] == "synthetic" and r["flag"] in real_flags]

    # merchant-block inference: group phantoms by (mapcode, merchant); score each
    # ShopLineupParam 100-block by how many of the group's items it stocks.
    groups = collections.defaultdict(list)
    for r in phantoms:
        mc, item, hint = parse_annotation(r["item_name"])
        if classify(hint, item) == "shop":
            groups[merchant_key(mc, hint)].append(item)

    merchant_block, why = {}, {}
    for key, items in groups.items():
        score = collections.Counter()
        for item in items:
            full = catalog.get(item)
            if full is None:
                continue
            for sr in shop_by_item[full]:
                score[int(sr["ID"]) // 100] += 1
        if not score:
            continue
        best, n = score.most_common(1)[0]
        ties = [b for b, v in score.items() if v == n]
        if len(ties) == 1 and (n >= 2 or len(items) == 1):
            merchant_block[key] = best
            why[key] = ("merchant block %d00-%d99 stocks %d/%d of this merchant's phantom items"
                        % (best, best, n, len(items)))

    rows_out, stats = [], collections.Counter()

    for r in sorted(phantoms, key=lambda x: int(x["flag"])):
        syn, region = r["flag"], r["region"]
        mc, item, hint = parse_annotation(r["item_name"])
        kind = classify(hint, item)
        full = catalog.get(item)
        cands = {}
        unscoped = False

        if full is None:
            rows_out.append((syn, item, r["item_name"], "UNRECOVERABLE", "",
                             "item name %r not resolvable via ITEM_CATALOG" % item))
            stats["UNRECOVERABLE"] += 1
            continue

        if kind == "shop":
            key = merchant_key(mc, hint)
            blk = merchant_block.get(key)
            for sr in shop_by_item[full]:
                fs = sr["eventFlag_forStock"]
                if not fs or fs in ("0", "-1"):
                    continue
                if blk is not None and int(sr["ID"]) // 100 != blk:
                    continue
                cands.setdefault(fs, "ShopLineupParam ID=%s equipId=%s equipType=%s "
                                     "eventFlag_forStock=%s; %s"
                                 % (sr["ID"], sr["equipId"], sr["equipType"], fs,
                                    why.get(key, "merchant block NOT inferred - searched all shops")))
        else:
            ap_reg = ap_region_of_flag.get(syn, "")
            scope = region_to_maps.get(ap_reg, set())
            for table, lot_id, sf in lots_by_item.get(full, []):
                mid = map_of(table, lot_id)
                flag = sf
                if not flag:
                    continue
                if not scope or not mid or mid not in scope:
                    continue
                cands.setdefault(flag,
                    "ItemLotParam_%s ID=%s grants %r, slot getItemFlagId=%s; lot is placed in map %s "
                    "(%s) which belongs to AP region %r%s [%s]"
                    % (table, lot_id, item, flag, mid,
                       "msb_flag_region" if lot_id in msb_map_by_lot else "lot-id map convention",
                       ap_reg,
                       " (tile region inferred from neighbouring tiles)" if mid in neighbour_filled else "",
                       "annotation says: %s" % (hint or kind)))
            unscoped = not scope

            if not cands:
                # Pass 3 - global uniqueness.  If the ENTIRE game grants this item
                # from exactly one item lot, placement is determined by item identity
                # alone and no region scope is needed.  (This rescues phantoms whose
                # AP region disagrees with the region gen_data gave the real check,
                # e.g. the known Liurnia/Altus boundary mis-tag.)
                all_lots = lots_by_item.get(full, [])
                flags_all = {sf for _t, _l, sf in all_lots if sf}
                if len(all_lots) == 1 and len(flags_all) == 1:
                    table, lot_id, sf = all_lots[0]
                    mid = map_of(table, lot_id)
                    cands[sf] = (
                        "ItemLotParam_%s ID=%s is the ONLY lot in the entire game that grants %r "
                        "(slot getItemFlagId=%s, map=%s) -> placement proven by global uniqueness; "
                        "note the phantom is filed under AP region %r while the real check's map "
                        "resolves to %r"
                        % (table, lot_id, item, sf, mid or "unbound(event/enemy lot)", ap_reg,
                           map_region.get(mid or "", "unknown")))
                    unscoped = False

        if kind != "shop" and unscoped:
            rows_out.append((syn, item, r["item_name"], "UNRECOVERABLE", "",
                             "AP region %r has no known map scope - refusing to guess a placement"
                             % ap_region_of_flag.get(syn, "?")))
            stats["UNRECOVERABLE"] += 1
            continue

        if not cands:
            verdict, real = "UNRECOVERABLE", ""
            ev = ("no %s grants %r inside AP region %r"
                  % ("ShopLineupParam row" if kind == "shop" else "item lot", item,
                     region if kind == "shop" else ap_region_of_flag.get(syn, "?")))
            if kind != "shop":
                ev += " (maps searched: %s)" % ",".join(
                    sorted(region_to_maps.get(ap_region_of_flag.get(syn, ""), set())))
            elsewhere = collections.Counter()
            n_unplaced = 0
            for table, lot_id, sf in lots_by_item.get(full, []):
                mid = map_of(table, lot_id)
                if mid:
                    elsewhere[mid] += 1
                else:
                    n_unplaced += 1
            if kind != "shop":
                ev += (" || the item IS granted by %d lot(s) elsewhere: maps=[%s]; %d lot(s) have no "
                       "MSB map binding at all (enemy/event lots) so they cannot be map-scoped"
                       % (len(lots_by_item.get(full, [])),
                          ",".join("%s x%d" % (m, n) for m, n in elsewhere.most_common(8)),
                          n_unplaced))
            same = [f for f, c in claimed.items()
                    if c["item_name"] == item
                    and ap_region_of_flag.get(f) == ap_region_of_flag.get(syn)]
            ev += " || context: %d existing AP location(s) already grant %r in this region%s" % (
                len(same), item, (" (flags %s)" % ",".join(sorted(same)[:6])) if same else "")
        elif len(cands) == 1:
            real, ev = next(iter(cands.items()))
            c = claimed.get(real)
            if c:
                verdict = "DUPLICATE"
                ev += (" || flag ALREADY CLAIMED by ap_id=%s (%s, method=%s) -> phantom row "
                       "duplicates an existing AP location; fix = DELETE the phantom row"
                       % (c["ap_id"], c["item_name"], c["method"]))
            else:
                verdict = "RECOVERED"
                ev += " || flag not claimed by any other AP location -> safe to rebind"
        else:
            verdict = "AMBIGUOUS"
            unclaimed = sorted(f for f in cands if f not in claimed)
            real = unclaimed[0] if len(unclaimed) == 1 else ""
            ev = "%d candidates [%s]; unclaimed=[%s]. %s" % (
                len(cands), ",".join(sorted(cands)), ",".join(unclaimed) or "none",
                " ;; ".join("%s: %s" % (f, cands[f]) for f in sorted(cands)))
            if not unclaimed:
                stats["AMBIGUOUS_ALL_CLAIMED"] += 1
                ev = ("EVERY candidate real flag is ALREADY claimed by another AP location, so "
                      "whichever one this phantom means, the check already exists -> the phantom "
                      "row is redundant and DELETE is safe even though the exact counterpart is "
                      "not pinned. ") + ev
            elif real:
                ev = ("only 1 of %d candidates is unclaimed (%s) - plausible but NOT proven; "
                      "needs placement disambiguation. " % (len(cands), real)) + ev

        rows_out.append((syn, item, r["item_name"], verdict, real, ev))
        stats[verdict] += 1

    # flag-collision note: two phantoms resolving to the same real flag
    by_real = collections.Counter(r[4] for r in rows_out if r[4])
    rows_out = [
        (a, b, c, d, e, f + ("" if by_real[e] < 2 else
         " || NOTE: phantom(s) %s resolve to this same real flag (one game flag cannot back two AP locations)"
         % ",".join(x[0] for x in rows_out if x[4] == e and x[0] != a)))
        for (a, b, c, d, e, f) in rows_out]

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["synthetic_flag", "item", "annotation", "verdict", "real_flag", "evidence"])
        w.writerows(rows_out)

    in_ap = [r for r in phantoms if r["flag"] in ap_region_of_flag]
    not_ap = [r["flag"] for r in phantoms if r["flag"] not in ap_region_of_flag]
    print("synthetic rows in region_map.csv                  : %d"
          % (len(phantoms) + len(real_synth)))
    print("  PHANTOM (flag absent from ALL game data)        : %d" % len(phantoms))
    print("  synthetic-tagged but flag DOES exist in data    : %d  (%s)"
          % (len(real_synth), ",".join(r["flag"] for r in real_synth)))
    print("  PHANTOMS that reach data.py as AP LOCATIONS     : %d  <-- these are the live bug"
          % len(in_ap))
    print("  phantoms dropped before data.py (not AP locs)   : %d  (%s)"
          % (len(not_ap), ",".join(not_ap)))
    print()
    for v in ("RECOVERED", "DUPLICATE", "AMBIGUOUS", "UNRECOVERABLE"):
        print("  %-14s %d" % (v, stats[v]))
    print("    (of the AMBIGUOUS, %d have ZERO unclaimed candidates -> the real check already"
          % stats["AMBIGUOUS_ALL_CLAIMED"])
    print("     exists as an AP location no matter which candidate is meant)")
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    sys.exit(main())
