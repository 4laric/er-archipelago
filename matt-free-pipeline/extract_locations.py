#!/usr/bin/env python3
"""Matt-free location extractor.

Walks vanilla ER param CSVs (Smithbox dump) and builds a candidate randomizer
location table keyed by the game's own event flags, with NO reference to matt's
static-randomizer keys. Then diffs against the current apworld flag set.

Sources (on disk):
  elden_ring_artifacts/vanilla_er/vanilla_er/ItemLotParam_map.csv
  .../ItemLotParam_enemy.csv
  .../ShopLineupParam.csv
Reference:
  Archipelago/worlds/eldenring/er_static_detection_table.json  (current flags in use)
"""
import csv, json, os, sys

csv.field_size_limit(10**7)
BASE = "/sessions/vibrant-laughing-franklin/mnt/er-archipelago/elden_ring_artifacts/vanilla_er/vanilla_er"
DET  = "/sessions/vibrant-laughing-franklin/mnt/er-archipelago/Archipelago/worlds/eldenring/er_static_detection_table.json"
OUT  = "/sessions/vibrant-laughing-franklin/mnt/outputs/candidate_locations.csv"

# ER ItemLotParam lotItemCategory -> item-family (for names / FullID category nibble)
CATEGORY = {0: "none", 1: "goods", 2: "weapon", 3: "protector", 4: "accessory", 5: "gem", 6: "ashofwar"}

def load_names():
    """id -> display name from Paramdex Names, best-effort (weapon/goods/armor/talisman/gem)."""
    names = {}
    root = "/sessions/vibrant-laughing-franklin/mnt/er-archipelago/Paramdex/ER/Names"
    for fam in ("EquipParamWeapon","EquipParamGoods","EquipParamProtector","EquipParamAccessory","EquipParamGem"):
        p = os.path.join(root, fam + ".txt")
        if os.path.exists(p):
            for line in open(p, encoding="utf-8", errors="replace"):
                line = line.rstrip("\n")
                if not line or " " not in line: continue
                i, nm = line.split(" ", 1)
                try: names[int(i)] = nm
                except ValueError: pass
    return names

def region_hint(flag):
    """Coarse area bucket from flag leading digits (good enough for a name)."""
    s = str(flag)
    if len(s) >= 6:
        return "map" + s[:2]          # e.g. 150xxx -> 'map15'
    return "misc"

def extract():
    cands = []   # (flag, item_id, category, source, param_row_id)
    def do_lot(fn, source):
        path = os.path.join(BASE, fn)
        with open(path) as f:
            r = csv.reader(f); hdr = next(r)
            iID = hdr.index("ID")
            i1  = hdr.index("lotItemId01"); ic = hdr.index("lotItemCategory01")
            ifl = hdr.index("getItemFlagId")
            for row in r:
                try: flag = int(row[ifl])
                except (ValueError, IndexError): continue
                if flag <= 0: continue
                try: item = int(row[i1])
                except (ValueError, IndexError): item = 0
                if item == 0: continue        # curation: lot must award a real item
                try: cat = int(row[ic])
                except (ValueError, IndexError): cat = 0
                cands.append((flag, item, cat, source, row[iID]))
    do_lot("ItemLotParam_map.csv",  "map_lot")
    do_lot("ItemLotParam_enemy.csv","enemy_lot")
    # shops
    with open(os.path.join(BASE, "ShopLineupParam.csv")) as f:
        r = csv.reader(f); hdr = next(r)
        iID = hdr.index("ID"); ie = hdr.index("equipId"); ifl = hdr.index("eventFlag_forStock")
        for row in r:
            try: flag = int(row[ifl])
            except (ValueError, IndexError): continue
            if flag <= 0: continue
            try: item = int(row[ie])
            except (ValueError, IndexError): item = 0
            cands.append((flag, item, -1, "shop", row[iID]))
    return cands

def main():
    names = load_names()
    cands = extract()

    # dedup to one location per (flag) — group shared-flag lots
    by_flag = {}
    for flag, item, cat, source, rid in cands:
        by_flag.setdefault(flag, []).append((item, cat, source, rid))

    # write candidate table
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ap_id","flag","region_hint","source","n_items","first_item_id","category","first_item_name"])
        for i, (flag, members) in enumerate(sorted(by_flag.items())):
            item, cat, source, rid = members[0]
            w.writerow([7000000 + i, flag, region_hint(flag), source, len(members),
                        item, CATEGORY.get(cat, cat), names.get(item, "")])

    # diff vs current apworld flags
    obj = json.JSONDecoder().raw_decode(open(DET).read())[0]
    ap_flags = set(int(v) for v in obj["location_flags"].values())
    cand_flags = set(by_flag)

    covered   = ap_flags & cand_flags
    extra     = cand_flags - ap_flags     # game lots the apworld excluded (curation cut OR missed)
    unresolved= ap_flags - cand_flags     # event-script grants (the ~51)

    print(f"candidate param rows scanned : {len(cands)}")
    print(f"distinct candidate flags     : {len(cand_flags)}")
    print(f"current apworld flags         : {len(ap_flags)}")
    print(f"  covered  (apworld ∩ params): {len(covered)}  ({len(covered)*100//len(ap_flags)}%)")
    print(f"  unresolved(apworld − params): {len(unresolved)}  <- event-script tail")
    print(f"  EXTRA    (params − apworld) : {len(extra)}  <- in-game lots the apworld does NOT use")
    print(f"\nwrote candidate table -> {OUT}  ({len(cand_flags)} locations)")

    # characterize the EXTRA set a little (curation signal)
    from collections import Counter
    src = Counter()
    for flag in extra:
        src[by_flag[flag][0][2]] += 1
    print("EXTRA by source:", dict(src))

if __name__ == "__main__":
    main()
