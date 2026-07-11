#!/usr/bin/env python3
"""Merge all game-derived placement sources into final region assignment.

Sources (all matt-free, from game data):
  treasure : MSB Event/Treasure <ItemLotID> -> map/tile   (lot_to_map.tsv)
  emevd    : per-map EMEVD .js references the lot or its flag -> map   (emevd_*.json)
  pending  : awarded by COMMON events / boss death / NPC gift / merchant -> no per-map
             placement exists to parse; needs item-class rules (boss->arena, shop->merchant).
"""
import csv, json, os
csv.field_size_limit(10**7)
OUT="/sessions/vibrant-laughing-franklin/mnt/outputs"
BASE="/sessions/vibrant-laughing-franklin/mnt/er-archipelago/elden_ring_artifacts/vanilla_er/vanilla_er"
INTERIOR={"m10":"Stormveil Castle","m11":"Leyndell / Roundtable / Shunning-Grounds",
 "m12":"Eternal Cities & Underground Rivers","m13":"Crumbling Farum Azula","m14":"Raya Lucaria Academy",
 "m15":"Miquella's Haligtree & Elphael","m16":"Volcano Manor / Mt. Gelmir","m18":"Stormveil (assoc.)",
 "m19":"Chapel of Anticipation","m20":"Mohgwyn / Consecrated-adjacent","m21":"DLC Interior",
 "m30":"Hero's Graves (Catacombs)","m31":"Caves","m32":"Tunnels","m34":"DLC Dungeon","m35":"Divine Tower",
 "m39":"DLC Dungeon","m40":"DLC Dungeon","m41":"DLC Legacy Dungeon","m42":"DLC Legacy Dungeon","m43":"DLC Legacy Dungeon","m45":"DLC Dungeon"}
def friendly(mp):
    if mp.startswith(("m60","m61")): return "Overworld "+mp
    return INTERIOR.get(mp.split("_")[0], mp.split("_")[0])

def main():
    lot2flag={}
    for fn in ("ItemLotParam_map.csv","ItemLotParam_enemy.csv"):
        with open(os.path.join(BASE,fn)) as f:
            r=csv.reader(f);h=next(r);iid=h.index("ID");ifl=h.index("getItemFlagId")
            for row in r:
                try:
                    fl=int(row[ifl])
                    if fl>0: lot2flag[int(row[iid])]=fl
                except: pass
    flag2map={}; method={}
    # treasure
    for line in open(os.path.join(OUT,"lot_to_map.tsv")):
        lot,mp=line.rstrip("\n").split("\t"); fl=lot2flag.get(int(lot))
        if fl and fl not in flag2map: flag2map[fl]=mp; method[fl]="treasure"
    # emevd (lot scan + flag scan)
    for jf in ("/tmp/emevd_lot2map.json","/tmp/emevd_flagscan.json"):
        if not os.path.exists(jf): continue
        d=json.load(open(jf))
        for k,mp in d.items():
            k=int(k)
            fl = lot2flag.get(k, k)   # lot-scan keys are lots; flag-scan keys are flags
            if fl not in flag2map: flag2map[fl]=mp; method[fl]="emevd"
    # persist merged
    with open(os.path.join(OUT,"flag_to_region.csv"),"w",newline="") as f:
        w=csv.writer(f); w.writerow(["flag","map","region","method"])
        for fl,mp in sorted(flag2map.items()):
            w.writerow([fl,mp,friendly(mp),method[fl]])

    rows=list(csv.DictReader(open(os.path.join(OUT,"curated_locations.csv"))))
    out=[]
    from collections import Counter, OrderedDict
    mc=Counter()
    for r in rows:
        fl=int(r["flag"])
        if fl in flag2map:
            out.append(dict(r, map=flag2map[fl], region=friendly(flag2map[fl]), rmethod=method[fl])); mc[method[fl]]+=1
        else:
            out.append(dict(r, map="PENDING", region="REGION_PENDING", rmethod="pending")); mc["pending"]+=1
    with open(os.path.join(OUT,"region_map.csv"),"w",newline="") as f:
        w=csv.writer(f); w.writerow(["ap_id","flag","flag_source","item_name","map","region","method"])
        for r in out: w.writerow([r["ap_id"],r["flag"],r["flag_source"],r["item_name"],r["map"],r["region"],r["rmethod"]])
    # regenerate module
    by=OrderedDict()
    for r in sorted(out,key=lambda x:(x["region"],int(x["flag"]))): by.setdefault(r["region"],[]).append(r)
    def q(s): return '"'+str(s).replace("\\","\\\\").replace('"','\\"')+'"'
    with open(os.path.join(OUT,"locations_generated.py"),"w") as f:
        f.write('"""AUTO-GENERATED matt-free ER locations. Flag-keyed, no matt keys.\n')
        f.write('Region from game placement: MSB Treasure + per-map EMEVD. REGION_PENDING = awarded by\n')
        f.write('common/boss/NPC/shop events (no per-map placement); needs item-class rules."""\n')
        f.write("from dataclasses import dataclass\nfrom typing import Optional, Dict, List\n\n")
        f.write("@dataclass\nclass ERLocationData:\n    name: str\n    default_item_name: Optional[str]\n    flag: int\n")
        f.write("    category: str\n    region: str\n    map_id: str\n    region_method: str\n")
        f.write("    crafting_material: bool=False\n    filler: bool=False\n    synthetic: bool=False\n\n")
        f.write("location_tables: Dict[str, List[ERLocationData]] = {}\n")
        f.write("def _a(rg,L): location_tables.setdefault(rg,[]).append(L)\n\n")
        n=0
        for region,rs in by.items():
            f.write(f"# ---- {region} ({len(rs)}) ----\n")
            for r in rs:
                base=r["item_name"] or (("item#"+r["item_id"]) if r["item_id"] else "check")
                nm=f'{region} :: {base} [f{r["flag"]}]'
                di="None" if not r["item_name"] else q(r["item_name"])
                f.write(f'_a({q(region)}, ERLocationData({q(nm)}, {di}, {r["flag"]}, {q(r["category"])}, '
                        f'{q(region)}, {q(r["map"])}, {q(r["rmethod"])}, {bool(int(r["crafting_material"]))}, '
                        f'{bool(int(r["filler"]))}, {bool(int(r["synthetic"]))}))\n')
                n+=1
        f.write(f"\n# {n} locations across {len(by)} regions\n")
    tot=len(out); resolved=tot-mc["pending"]
    print(f"locations: {tot}")
    print(f"  RESOLVED region: {resolved} ({resolved*100//tot}%)  [treasure={mc['treasure']} emevd={mc['emevd']}]")
    print(f"  REGION_PENDING (common/boss/NPC/shop awards): {mc['pending']} ({mc['pending']*100//tot}%)")
    print(f"  distinct regions: {len(by)}")
    # pending taxonomy
    pend=[r for r in out if r['rmethod']=='pending']
    print("  pending by source:",dict(Counter(r['flag_source'] for r in pend)))

if __name__=="__main__": main()
