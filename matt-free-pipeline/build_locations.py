#!/usr/bin/env python3
"""matt-free location backbone builder.

One pass: param CSVs -> curated table -> importable locations_generated.py.

Principled tags (all from game data, no matt list):
  crafting_material : EquipParamGoods.goodsType == 2  (the gatherable-flora class;
                      Fulgurbloom/Trina's Lily/Rada Fruit live here). NOT auto-excluded
                      -- matt keeps most; it's just a labeled, toggleable group.
  filler (spam)     : the same vanilla item placed in >= SPAM_THRESHOLD one-time lots
                      (Rada Fruit x183, Golden Rune [1] x106, ...). Count-based, so it
                      catches spam by evidence, not by a hardcoded name blocklist.
  synthetic         : apworld flag with NO source in any param (client sets on pickup).
Respawnables (getItemFlagId == 0) are dropped up front -- unwatchable, by definition.
"""
import csv, json, os, re
csv.field_size_limit(10**7)

BASE  = "/sessions/vibrant-laughing-franklin/mnt/er-archipelago/elden_ring_artifacts/vanilla_er/vanilla_er"
APW   = "/sessions/vibrant-laughing-franklin/mnt/er-archipelago/Archipelago/worlds/eldenring"
NAMES = "/sessions/vibrant-laughing-franklin/mnt/er-archipelago/Paramdex/ER/Names"
OUT_CSV = "/sessions/vibrant-laughing-franklin/mnt/outputs/curated_locations.csv"
OUT_SYN = "/sessions/vibrant-laughing-franklin/mnt/outputs/synthetic_flags.csv"
OUT_PY  = "/sessions/vibrant-laughing-franklin/mnt/outputs/locations_generated.py"
SPAM_THRESHOLD = 40

# lotItemCategory / shop equipType -> Paramdex family
CAT_FAMILY = {2:"EquipParamWeapon", 3:"EquipParamProtector", 4:"EquipParamAccessory",
              1:"EquipParamGoods", 5:"EquipParamGem", 0:"EquipParamGoods"}
CAT_NAME   = {0:"none",1:"goods",2:"weapon",3:"protector",4:"accessory",5:"gem",-1:"shop"}
SHOP_FAMILY= {0:"EquipParamWeapon",1:"EquipParamProtector",2:"EquipParamAccessory",
              3:"EquipParamGoods",4:"EquipParamGem"}

def load_family(fam):
    d={}
    p=os.path.join(NAMES,fam+".txt")
    if os.path.exists(p):
        for l in open(p,encoding="utf-8",errors="replace"):
            l=l.rstrip("\n")
            if " " in l:
                i,n=l.split(" ",1)
                try: d[int(i)]=n
                except ValueError: pass
    return d
FAM = {f:load_family(f) for f in set(CAT_FAMILY.values())|set(SHOP_FAMILY.values())}
def name_of(item, family):
    return FAM.get(family,{}).get(item,"")

def goods_type():
    gt={}
    with open(os.path.join(BASE,"EquipParamGoods.csv")) as f:
        r=csv.reader(f);h=next(r);iid=h.index("ID");ig=h.index("goodsType")
        for row in r:
            try: gt[int(row[iid])]=int(row[ig])
            except (ValueError,IndexError): pass
    return gt
GT = goods_type()

def region_hint(flag):
    s=str(flag); return ("region_"+s[:2]) if len(s)>=6 else "region_misc"

def apcode_names():
    src=open(os.path.join(APW,"locations.py")).read()
    apid=7000000; m={}
    for mt in re.finditer(r'ERLocationData\(\s*"((?:[^"\\]|\\.)*)"\s*,\s*(None\b|")',src):
        if mt.group(2)!="None": m[apid]=mt.group(1); apid+=1
    return m

def main():
    apflags=set(int(v) for v in json.JSONDecoder().raw_decode(open(os.path.join(APW,"er_static_detection_table.json")).read())[0]["location_flags"].values())

    recs={}            # flag -> record
    all_param_flags=set()
    item_lotcount={}   # (item,family) -> count of one-time lots (spam signal)

    def add(flag, item, family, cat_name, source):
        all_param_flags.add(flag)
        if flag in recs: return
        nm=name_of(item, family)
        recs[flag]=dict(flag=flag, item=item, family=family, name=nm, cat=cat_name, source=source,
                        crafting=(cat_name=="goods" and GT.get(item)==2))

    # ---- map + enemy lots (drop respawnables: getItemFlagId==0) ----
    for fn,src in (("ItemLotParam_map.csv","map_lot"),("ItemLotParam_enemy.csv","enemy_lot")):
        with open(os.path.join(BASE,fn)) as f:
            r=csv.reader(f);h=next(r)
            i1=h.index("lotItemId01");ic=h.index("lotItemCategory01");ifl=h.index("getItemFlagId")
            for row in r:
                try: flag=int(row[ifl])
                except: continue
                if flag<=0: continue          # respawnable -> excluded
                try: item=int(row[i1])
                except: item=0
                if item==0: continue
                try: cat=int(row[ic])
                except: cat=0
                fam=CAT_FAMILY.get(cat,"EquipParamGoods")
                item_lotcount[(item,fam)]=item_lotcount.get((item,fam),0)+1
                add(flag,item,fam,CAT_NAME.get(cat,str(cat)),src)
    # ---- shops (drop infinite, dedup equipment/remembrance) ----
    shop=[]
    with open(os.path.join(BASE,"ShopLineupParam.csv")) as f:
        r=csv.reader(f);h=next(r)
        ie=h.index("equipId");ifl=h.index("eventFlag_forStock");isq=h.index("sellQuantity");iet=h.index("equipType")
        for row in r:
            try: flag=int(row[ifl])
            except: continue
            if flag<=0: continue
            try: sq=int(row[isq])
            except: sq=0
            if sq<0: continue
            all_param_flags.add(flag)
            try: item=int(row[ie])
            except: item=0
            try: et=int(row[iet])
            except: et=3
            shop.append((flag,item,et))
    seen={}
    shop.sort(key=lambda t:(t[1], t[0] not in apflags))
    for flag,item,et in shop:
        fam=SHOP_FAMILY.get(et,"EquipParamGoods")
        nm=name_of(item,fam)
        unique = et in (0,1,2) or nm.startswith("Remembrance") or nm=="Elden Remembrance"
        if unique:
            if item in seen: continue
            seen[item]=flag
        add(flag,item,fam,"shop","shop")

    # ---- assemble rows with tags ----
    rows=[]
    for flag,rec in recs.items():
        cnt=item_lotcount.get((rec["item"],rec["family"]),0)
        filler = cnt>=SPAM_THRESHOLD
        rows.append(dict(flag=flag, source=rec["source"], cat=rec["cat"], item=rec["item"],
                         name=rec["name"], region=region_hint(flag),
                         crafting=int(rec["crafting"]), filler=int(filler),
                         synthetic=0, in_matt=int(flag in apflags)))
    # ---- synthetic (flagless) ----
    id2name=apcode_names()
    inv={}
    for aid,fl in json.JSONDecoder().raw_decode(open(os.path.join(APW,"er_static_detection_table.json")).read())[0]["location_flags"].items():
        inv.setdefault(int(fl),int(aid))
    syn=sorted(apflags-all_param_flags)
    for flag in syn:
        rows.append(dict(flag=flag, source="synthetic", cat="synthetic", item="",
                         name=id2name.get(inv.get(flag),"?"), region=region_hint(flag),
                         crafting=0, filler=0, synthetic=1, in_matt=1))
    rows.sort(key=lambda x:x["flag"])

    # ---- write curated CSV ----
    with open(OUT_CSV,"w",newline="") as f:
        w=csv.writer(f); w.writerow(["ap_id","flag","flag_source","category","item_id","item_name",
                                     "region","crafting_material","filler","synthetic","in_matt_set"])
        for i,r in enumerate(rows):
            w.writerow([7000000+i,r["flag"],r["source"],r["cat"],r["item"],r["name"],r["region"],
                        r["crafting"],r["filler"],r["synthetic"],r["in_matt"]])
    with open(OUT_SYN,"w",newline="") as f:
        w=csv.writer(f); w.writerow(["flag","location_name","note"])
        for r in rows:
            if r["synthetic"]:
                w.writerow([r["flag"],r["name"],"client sets on pickup/purchase (flagless in game data)"])

    # ---- emit importable locations_generated.py ----
    from collections import defaultdict, OrderedDict
    by_region=OrderedDict()
    for r in sorted(rows,key=lambda x:(x["region"],x["flag"])):
        by_region.setdefault(r["region"],[]).append(r)
    def pys(s): return '"'+s.replace("\\","\\\\").replace('"','\\"')+'"'
    with open(OUT_PY,"w") as f:
        f.write('"""AUTO-GENERATED matt-free ER location backbone (build_locations.py).\n\n')
        f.write("Locations keyed by the game\'s own event flag (vanilla params), NO matt keys.\n")
        f.write("Names are functional placeholders; regions are provisional flag-prefix buckets.\n")
        f.write("Hand-authored descriptions + real region assignment are the remaining polish.\n\"\"\"\n")
        f.write("from dataclasses import dataclass\n")
        f.write("from typing import Optional, Dict, List\n\n")
        f.write("@dataclass\nclass ERLocationData:\n")
        f.write("    name: str\n    default_item_name: Optional[str]\n    flag: int\n")
        f.write("    category: str\n    region: str\n")
        f.write("    crafting_material: bool = False\n    filler: bool = False\n    synthetic: bool = False\n\n")
        f.write("location_tables: Dict[str, List[ERLocationData]] = {}\n")
        f.write("def _a(r, L): location_tables.setdefault(r, []).append(L)\n\n")
        n=0
        for region,rs in by_region.items():
            f.write(f"# ---- {region} ({len(rs)}) ----\n")
            for r in rs:
                nm=f'{region}: {r["name"] or ("item#"+str(r["item"]) if r["item"] else "check")} [f{r["flag"]}]'
                di="None" if not r["name"] else pys(r["name"])
                f.write(f'_a({pys(region)}, ERLocationData({pys(nm)}, {di}, {r["flag"]}, '
                        f'{pys(r["cat"])}, {pys(region)}, {bool(r["crafting"])}, {bool(r["filler"])}, {bool(r["synthetic"])}))\n')
                n+=1
        f.write(f"\n# total: {n} locations across {len(by_region)} regions\n")

    core=sum(1 for r in rows if not r["filler"])
    print(f"TOTAL locations: {len(rows)}")
    print(f"  crafting_material tagged: {sum(r['crafting'] for r in rows)}")
    print(f"  filler (>= {SPAM_THRESHOLD} placements): {sum(r['filler'] for r in rows)}")
    print(f"  synthetic (flagless): {sum(r['synthetic'] for r in rows)}")
    print(f"  in matt's set: {sum(r['in_matt'] for r in rows)}")
    print(f"  non-filler ('core'): {core}")
    print(f"wrote:\n  {OUT_CSV}\n  {OUT_SYN}\n  {OUT_PY}")

if __name__=="__main__":
    main()
