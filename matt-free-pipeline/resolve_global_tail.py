#!/usr/bin/env python3
"""Refine the 'global' tail using data-clean signals only. Runs AFTER resolve_buckets.py.

Levers (in priority order), applied ONLY to method=='global' rows:
  1. map_name    : item name starts 'Map:' -> region is literally in the name (high).
  2. flag_prefix : learn prefix->region from the 2,791 ground-truth (treasure/emevd) rows;
                   apply the longest prefix with support>=3 and purity>=0.85. Ambiguous
                   prefixes (Stormveil m10 vs Limgrave overworld m60) fail the purity test
                   and are left global -- so no fabrication. conf med if purity>=0.95 else low.
  3. filler rows : spam items (>=40 lots) are scattered by design -> region
                   'Global / Filler (scattered by design)', method 'global_filler'. Honest,
                   distinct from truly-unknown.
  Everything else stays 'Global / Common-event (unplaced)' / method 'global'.
"""
import csv, os
from collections import Counter, defaultdict, OrderedDict
csv.field_size_limit(10**7)
PIPE="/sessions/sleepy-laughing-mendel/mnt/er-archipelago/matt-free-pipeline"
OUT="/tmp/mftail"; os.makedirs(OUT,exist_ok=True)
GT={"treasure","emevd"}

COOKBOOK = {
 "Ancient Dragon Apostle's Cookbook [1]":"Altus Plateau",
 "Ancient Dragon Knight's Cookbook [1]":"Scadu Altus (DLC)",
 "Ancient Dragon Knight's Cookbook [2]":"Scadu Altus (DLC)",
 "Antiquity Scholar's Cookbook [1]":"Scadu Altus (DLC)",
 "Antiquity Scholar's Cookbook [2]":"Land of Shadow (DLC)",
 "Battlefield Priest's Cookbook [1]":"Shadow Keep (DLC)",
 "Battlefield Priest's Cookbook [4]":"Shadow Keep (DLC)",
 "Fevor's Cookbook [1]":"Limgrave",
 "Finger-Weaver's Cookbook [2]":"Land of Shadow (DLC)",
 "Fire Knight's Cookbook [1]":"Gravesite Plain (DLC)",
 "Fire Knight's Cookbook [2]":"Land of Shadow (DLC)",
 "Forager Brood Cookbook [1]":"Gravesite Plain (DLC)",
 "Forager Brood Cookbook [2]":"Land of Shadow (DLC)",
 "Forager Brood Cookbook [3]":"Cerulean Coast (DLC)",
 "Forager Brood Cookbook [4]":"Land of Shadow (DLC)",
 "Forager Brood Cookbook [5]":"Land of Shadow (DLC)",
 "Forager Brood Cookbook [6]":"Shadow Keep (DLC)",
 "Forager Brood Cookbook [7]":"Land of Shadow (DLC)",
 "Glintstone Craftsman's Cookbook [4]":"Liurnia of the Lakes",
 "Glintstone Craftsman's Cookbook [6]":"Liurnia of the Lakes",
 "Glintstone Craftsman's Cookbook [8]":"Consecrated Snowfield",
 "Greater Potentate's Cookbook [1]":"Land of Shadow (DLC)",
 "Greater Potentate's Cookbook [2]":"Land of Shadow (DLC)",
 "Greater Potentate's Cookbook [3]":"Scadu Altus (DLC)",
 "Greater Potentate's Cookbook [4]":"Land of Shadow (DLC)",
 "Greater Potentate's Cookbook [5]":"Land of Shadow (DLC)",
 "Greater Potentate's Cookbook [6]":"Jagged Peak (DLC)",
 "Greater Potentate's Cookbook [10]":"Land of Shadow (DLC)",
 "Greater Potentate's Cookbook [11]":"Land of Shadow (DLC)",
 "Greater Potentate's Cookbook [12]":"Land of Shadow (DLC)",
 "Greater Potentate's Cookbook [13]":"Land of Shadow (DLC)",
 "Igon's Cookbook [1]":"Jagged Peak (DLC)",
 "Igon's Cookbook [2]":"Jagged Peak (DLC)",
 "Loyal Knight's Cookbook":"Land of Shadow (DLC)",
 "Mad Craftsman's Cookbook [1]":"Abyssal Woods (DLC)",
 "Mad Craftsman's Cookbook [3]":"Abyssal Woods (DLC)",
 "Nomadic Warrior's Cookbook [4]":"Limgrave",
 "Nomadic Warrior's Cookbook [11]":"Liurnia of the Lakes",
 "Perfumer's Cookbook [1]":"Altus Plateau",
 "Perfumer's Cookbook [2]":"Altus Plateau",
 "St. Trina Disciple's Cookbook [3]":"Land of Shadow (DLC)",
 "Tibia's Cookbook":"Land of Shadow (DLC)",
}


def main():
    cur={int(r['flag']):r for r in csv.DictReader(open(os.path.join(PIPE,"curated_locations.csv")))}
    rows=list(csv.DictReader(open(os.path.join(PIPE,"region_map.csv"))))
    # learn prefix -> region from ground truth
    dist={N:defaultdict(Counter) for N in (5,4,3)}
    for r in rows:
        if r['method'] in GT and len(str(r['flag']))>=6:
            for N in (5,4,3): dist[N][str(r['flag'])[:N]][r['region']]+=1
    pure={}
    for N in (5,4,3):
        for p,c in dist[N].items():
            tot=sum(c.values()); reg,top=c.most_common(1)[0]
            if tot>=3 and top/tot>=0.85: pure[(N,p)]=(reg, top/tot)

    def infer(fl):
        s=str(fl)
        if len(s)<6: return None
        for N in (5,4,3):
            hit=pure.get((N,s[:N]))
            if hit: return hit  # (region, purity)
        return None

    touched=[]; mc=Counter()
    for r in rows:
        if r['method']!='global': continue
        nm=r['item_name']; fl=int(r['flag'])
        if nm.startswith("Map:"):
            reg=nm[4:].split(",")[0].strip()
            r['region']=reg; r['method']="map_name"; r['_conf']="high"
        elif nm in COOKBOOK:
            r['region']=COOKBOOK[nm]; r['method']="cookbook"; r['_conf']="med"
        else:
            inf=infer(fl)
            isfill = cur.get(fl,{}).get('filler')=='1'
            if inf and not isfill:
                reg,pur=inf
                r['region']=reg; r['method']="flag_prefix"; r['_conf']="med" if pur>=0.95 else "low"
            elif isfill:
                r['region']="Global / Filler (scattered by design)"; r['method']="global_filler"; r['_conf']="na"
            elif any(k in nm.lower() for k in ("smithing stone","glovewort","golden rune")):
                r['region']="Global / Filler (scattered by design)"; r['method']="global_filler"; r['_conf']="na"
            else:
                r['_conf']="na"; continue  # stays global
        mc[r['method']]+=1; touched.append(dict(r))

    # normalize: m61 overworld tiles are DLC (Land of Shadow), not Lands Between
    for r in rows:
        if r['region'].startswith("Overworld m61"):
            r['region']="Land of Shadow (DLC)"
    # rewrite region_map.csv
    with open(os.path.join(OUT,"region_map.csv"),"w",newline="") as f:
        w=csv.writer(f); w.writerow(["ap_id","flag","flag_source","item_name","map","region","method"])
        for r in rows: w.writerow([r["ap_id"],r["flag"],r["flag_source"],r["item_name"],r["map"],r["region"],r["method"]])
    # append to bucket report
    with open(os.path.join(OUT,"tail_resolution_report.csv"),"w",newline="") as f:
        w=csv.writer(f); w.writerow(["flag","flag_source","item_name","region","method","confidence"])
        for r in touched: w.writerow([r["flag"],r["flag_source"],r["item_name"],r["region"],r["method"],r["_conf"]])
    # regenerate module
    by=OrderedDict()
    for r in sorted(rows,key=lambda x:(x["region"],int(x["flag"]))): by.setdefault(r["region"],[]).append(r)
    def q(s): return '"'+str(s).replace("\\","\\\\").replace('"','\\"')+'"'
    with open(os.path.join(OUT,"locations_generated.py"),"w") as f:
        f.write('"""AUTO-GENERATED matt-free ER locations. Flag-keyed, no matt keys.\n')
        f.write('method: treasure|emevd (MSB) | shop_merchant|boss_arena|synthetic_areacode|map_name|\n')
        f.write('flag_prefix (item-class/data resolvers) | global_filler (spam, scattered) | global (unplaced)."""\n')
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
                base=r["item_name"] or "check"
                nm=f'{region} :: {base} [f{r["flag"]}]'
                di="None" if not r["item_name"] else q(r["item_name"])
                f.write(f'_a({q(region)}, ERLocationData({q(nm)}, {di}, {r["flag"]}, {q(r["flag_source"])}, '
                        f'{q(region)}, {q(r["map"])}, {q(r["method"])}, False, False, '
                        f'{bool(r["flag_source"]=="synthetic")}))\n'); n+=1
        f.write(f"\n# {n} locations across {len(by)} regions\n")

    tot=len(rows)
    glob=sum(1 for r in rows if r['method']=='global')
    placed=sum(1 for r in rows if r['method'] not in ('global','global_filler'))
    print(f"pure prefixes learned: {len(pure)}")
    print(f"tail refined this pass: {sum(mc.values())} -> {dict(mc)}")
    print(f"REGION-PLACED (real region): {placed} ({placed*100//tot}%)")
    print(f"global_filler (scattered): {sum(1 for r in rows if r['method']=='global_filler')}")
    print(f"still global (unplaced): {glob} ({glob*100//tot}%)")
    print(f"regions: {len(by)}")

if __name__=="__main__": main()
