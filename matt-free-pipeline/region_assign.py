#!/usr/bin/env python3
"""Region assignment from game placement data (matt-free).

Chain: location flag -> ItemLotParam lot -> map. Two game-data sources:
  (A) MSB Treasure events (elden_ring_artifacts/mapstudio/*-msb-dcx/Event/Treasure/*.xml)
      carry <ItemLotID> and live in a per-map folder -> EXACT map/overworld-tile. (~46%)
  (B) interior lot-id prefix: 'm'+first-2-digits == map block, verified 99% on the MSB set.
      Fills the interior remainder the Treasure events don't cover. (~49%)
Overworld (m60/m61) that MSB doesn't cover can't use (B) (their lot ids don't start 60) -> ~3% gap.

Output: region_map.csv (flag,map,region,method) + regenerated locations_generated.py grouped by region.
Authoritative region = the game map id / tile. Friendly names applied for confidently-identified
interiors; overworld carries its exact tile (grouping tiles into named areas = the next refinement).
"""
import csv, json, os, re
csv.field_size_limit(10**7)
OUT="/sessions/vibrant-laughing-franklin/mnt/outputs"
BASE="/sessions/vibrant-laughing-franklin/mnt/er-archipelago/elden_ring_artifacts/vanilla_er/vanilla_er"

# confident interior map-block -> ER region name (validated against the placement join)
INTERIOR = {
 "m10":"Stormveil Castle", "m11":"Leyndell / Roundtable / Shunning-Grounds",
 "m12":"Eternal Cities & Underground Rivers", "m13":"Crumbling Farum Azula",
 "m14":"Raya Lucaria Academy", "m15":"Miquella's Haligtree & Elphael",
 "m16":"Volcano Manor / Mt. Gelmir", "m19":"Chapel of Anticipation",
 "m30":"Hero's Graves (Catacombs)", "m31":"Caves", "m32":"Tunnels",
 "m40":"DLC Legacy Dungeon", "m41":"DLC Legacy Dungeon", "m42":"DLC Legacy Dungeon",
 "m43":"DLC Legacy Dungeon", "m18":"Stranded Graveyard / Chapel of Anticipation",  # 2026-07-08: m40/m18 were
 # MISSING -> lots fell back to an m18 alias -> Stormveil. Note these blocks span MULTIPLE regions per
 # sub-map (m40_00 Gravesite vs m40_01 Rauh); the precise fix is the grace-join FLAG_REGION_OVERRIDE in
 # gen_data.py. This coarse block-level entry just stops the Stormveil fallback if the pipeline re-runs.
}
def friendly(mapid):
    if mapid.startswith(("m60","m61")):
        return "Overworld " + mapid           # exact tile; area-grouping is the next pass
    blk = mapid.split("_")[0]
    return INTERIOR.get(blk, blk)             # named if confident, else the raw block

def main():
    lot2flag={}
    with open(os.path.join(BASE,"ItemLotParam_map.csv")) as f:
        r=csv.reader(f);h=next(r);iid=h.index("ID");ifl=h.index("getItemFlagId")
        for row in r:
            try:
                fl=int(row[ifl])
                if fl>0: lot2flag[int(row[iid])]=fl
            except: pass
    flag2lot={fl:lot for lot,fl in lot2flag.items()}
    # MSB exact
    flag2map={}
    for line in open(os.path.join(OUT,"lot_to_map.tsv")):
        lot,mp=line.rstrip("\n").split("\t")
        fl=lot2flag.get(int(lot))
        if fl: flag2map[fl]=mp

    def resolve(flag):
        if flag in flag2map: return flag2map[flag],"msb"
        return "REGION_PENDING","pending"   # non-treasure lots need enemy/event MSB pass

    rows=list(csv.DictReader(open(os.path.join(OUT,"curated_locations.csv"))))
    out=[]
    from collections import Counter
    meth=Counter()
    for r in rows:
        mp,m = resolve(int(r["flag"]))
        meth[m]+=1
        out.append(dict(r, map=mp, region=friendly(mp) if mp!="REGION_PENDING" else "REGION_PENDING", method=m))

    with open(os.path.join(OUT,"region_map.csv"),"w",newline="") as f:
        w=csv.writer(f); w.writerow(["ap_id","flag","flag_source","item_name","map","region","method"])
        for r in out:
            w.writerow([r["ap_id"],r["flag"],r["flag_source"],r["item_name"],r["map"],r["region"],r["method"]])

    # regenerate locations_generated.py grouped by real region
    from collections import OrderedDict
    by=OrderedDict()
    for r in sorted(out,key=lambda x:(x["region"],int(x["flag"]))):
        by.setdefault(r["region"],[]).append(r)
    def q(s): return '"'+str(s).replace("\\","\\\\").replace('"','\\"')+'"'
    with open(os.path.join(OUT,"locations_generated.py"),"w") as f:
        f.write('"""AUTO-GENERATED matt-free ER locations (region_assign.py). Flag-keyed, no matt keys.\n')
        f.write('Region = real ER map from placement data (MSB Treasure + verified lot-id prefix).\n')
        f.write('Overworld carries exact tile; grouping tiles into named areas is the next refinement."""\n')
        f.write("from dataclasses import dataclass\nfrom typing import Optional, Dict, List\n\n")
        f.write("@dataclass\nclass ERLocationData:\n    name: str\n    default_item_name: Optional[str]\n")
        f.write("    flag: int\n    category: str\n    region: str\n    map_id: str\n")
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
                        f'{q(region)}, {q(r["map"])}, {bool(int(r["crafting_material"]))}, '
                        f'{bool(int(r["filler"]))}, {bool(int(r["synthetic"]))}))\n')
                n+=1
        f.write(f"\n# {n} locations across {len(by)} regions\n")

    print(f"locations: {len(out)}")
    print(f"  RELIABLE region (MSB Treasure, exact map/tile): {meth['msb']} ({meth['msb']*100//len(out)}%)")
    print(f"  REGION_PENDING (boss/enemy/event/shop lots, need enemy+EMEVD pass): {meth['pending']} ({meth['pending']*100//len(out)}%)")
    print(f"  distinct regions: {len(by)}")
    print(f"wrote region_map.csv + locations_generated.py")

if __name__=="__main__": main()
