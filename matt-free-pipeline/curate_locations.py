#!/usr/bin/env python3
"""Curation pass: turn the raw param candidates into a drop-in location set.

Builds on extract_locations.py findings. Key realization from profiling the 878
"extra" lots: they are NOT junk. They are real placed items matt excluded as
low-value filler (179 Rada Fruit, 106 Golden Rune [1], harvest mats) or duplicate
shop rows (each Remembrance sold 3x, bell-bearing dup inventories, talisman +N
variants). So curation is a design dial + a dedup, not a correctness fix.

Rules applied (all mechanical, over game facts — none copy matt's list):
  R1  shops: drop infinite-stock rows (sellQuantity < 0)          -> merchant spam
  R2  shops: dedup EQUIPMENT/remembrance by item id               -> collapses the 3x rows
  R3  goods: tier='filler' for a small harvest/low-value blocklist -> Rada Fruit etc.
  R4  everything else -> tier='core'
  +   the 49 flagless checks kept as synthetic-flag locations (client sets on pickup)

Output: curated_locations.csv  with columns
  ap_id, flag, flag_source, tier, category, item_id, item_name, region_hint, in_matt_set
"""
import csv, json, os, re
csv.field_size_limit(10**7)

BASE  = "/sessions/vibrant-laughing-franklin/mnt/er-archipelago/elden_ring_artifacts/vanilla_er/vanilla_er"
APW   = "/sessions/vibrant-laughing-franklin/mnt/er-archipelago/Archipelago/worlds/eldenring"
NAMES = "/sessions/vibrant-laughing-franklin/mnt/er-archipelago/Paramdex/ER/Names"
OUT   = "/sessions/vibrant-laughing-franklin/mnt/outputs/curated_locations.csv"
SYN   = "/sessions/vibrant-laughing-franklin/mnt/outputs/synthetic_flags.csv"

CATEGORY = {0:"none",1:"goods",2:"weapon",3:"protector",4:"accessory",5:"gem",6:"ashofwar",-1:"shop"}
# R3 harvest / trivial-filler goods (name-based, explicit + auditable)
FILLER = {"Rada Fruit","Golden Rune [1]","Glowstone","Rimed Rowa","Miquella's Lily",
          "Golden Rune [2]","Smithing Stone [1]"}

def load_names():
    out={}
    for fam in ("EquipParamWeapon","EquipParamGoods","EquipParamProtector",
                "EquipParamAccessory","EquipParamGem"):
        p=os.path.join(NAMES,fam+".txt")
        if os.path.exists(p):
            for l in open(p,encoding="utf-8",errors="replace"):
                l=l.rstrip("\n")
                if " " in l:
                    i,n=l.split(" ",1)
                    try: out[int(i)]=(n,fam)
                    except ValueError: pass
    return out

def region_hint(flag):
    s=str(flag)
    return ("map"+s[:2]) if len(s)>=6 else "misc"

def apcode_names():
    """ap_id -> location name, by replaying the ERLocationData counter."""
    src=open(os.path.join(APW,"locations.py")).read()
    apid=7000000; m={}
    for mt in re.finditer(r'ERLocationData\(\s*"((?:[^"\\]|\\.)*)"\s*,\s*(None\b|")',src):
        if mt.group(2)!="None":
            m[apid]=mt.group(1); apid+=1
    return m

def main():
    names=load_names()
    apflags=set(int(v) for v in json.JSONDecoder().raw_decode(open(os.path.join(APW,"er_static_detection_table.json")).read())[0]["location_flags"].values())

    by_flag={}   # flag -> dict(record)
    all_param_flags=set()   # every flag present in params, pre-curation (for true synthetic calc)
    def add(flag,item,cat,source,extra=None):
        all_param_flags.add(flag)
        if flag in by_flag:
            by_flag[flag]["n"]+=1; return
        nm,fam=names.get(item,("",""))
        by_flag[flag]=dict(flag=flag,item=item,cat=cat,source=source,name=nm,fam=fam,n=1,extra=extra or {})

    # --- map + enemy lots ---
    for fn,src in (("ItemLotParam_map.csv","map_lot"),("ItemLotParam_enemy.csv","enemy_lot")):
        with open(os.path.join(BASE,fn)) as f:
            r=csv.reader(f);h=next(r)
            i1=h.index("lotItemId01");ic=h.index("lotItemCategory01");ifl=h.index("getItemFlagId")
            for row in r:
                try: flag=int(row[ifl])
                except: continue
                if flag<=0: continue
                try: item=int(row[i1])
                except: item=0
                if item==0: continue
                try: cat=int(row[ic])
                except: cat=0
                add(flag,item,cat,src)
    # --- shops (R1 drop infinite, capture equipType for R2) ---
    shop_rows=[]
    with open(os.path.join(BASE,"ShopLineupParam.csv")) as f:
        r=csv.reader(f);h=next(r)
        ie=h.index("equipId");ifl=h.index("eventFlag_forStock");isq=h.index("sellQuantity")
        iet=h.index("equipType");im=h.index("mtrlId")
        for row in r:
            try: flag=int(row[ifl])
            except: continue
            if flag<=0: continue
            try: sq=int(row[isq])
            except: sq=0
            if sq<0: continue                       # R1
            all_param_flags.add(flag)
            try: item=int(row[ie])
            except: item=0
            try: et=int(row[iet])
            except: et=3
            shop_rows.append((flag,item,et))
    # R2: dedup equipment/remembrance shop items by item id (keep flag already in matt set if any)
    seen_equip={}
    def is_unique(item,et):
        nm=names.get(item,("",""))[0]
        return et in (0,1,2) or nm.startswith("Remembrance") or nm=="Elden Remembrance"
    # first pass: prefer matt-set flag as the survivor
    shop_rows.sort(key=lambda t:(t[1], t[0] not in apflags))
    for flag,item,et in shop_rows:
        if is_unique(item,et):
            if item in seen_equip:  # duplicate equipment row -> skip
                continue
            seen_equip[item]=flag
        add(flag,item,-1,"shop")

    # --- assign tier + write ---
    id2name=apcode_names()
    inv={}
    for aid,fl in json.JSONDecoder().raw_decode(open(os.path.join(APW,"er_static_detection_table.json")).read())[0]["location_flags"].items():
        inv.setdefault(int(fl),int(aid))
    core=filler=0
    rows=[]
    for flag,rec in sorted(by_flag.items()):
        tier="filler" if rec["name"] in FILLER else "core"
        core+= tier=="core"; filler+= tier=="filler"
        rows.append((flag,rec["source"],tier,CATEGORY.get(rec["cat"],rec["cat"]),
                     rec["item"],rec["name"],region_hint(flag), int(flag in apflags)))

    # --- the 49 synthetic (apflags with no param source) ---
    syn=sorted(apflags - all_param_flags)   # true flagless checks (independent of curation)
    syn_rows=[]
    for flag in syn:
        aid=inv.get(flag); nm=id2name.get(aid,"?")
        syn_rows.append((flag,"synthetic","core","synthetic","", nm, region_hint(flag), 1))

    allrows=rows+syn_rows
    allrows.sort(key=lambda x:x[0])
    with open(OUT,"w",newline="") as f:
        w=csv.writer(f); w.writerow(["ap_id","flag","flag_source","tier","category","item_id","item_name","region_hint","in_matt_set"])
        for i,(flag,src,tier,cat,item,nm,reg,inm) in enumerate(allrows):
            w.writerow([7000000+i,flag,src,tier,cat,item,nm,reg,inm])
    with open(SYN,"w",newline="") as f:
        w=csv.writer(f); w.writerow(["flag","location_name","note"])
        for flag,_,_,_,_,nm,_,_ in syn_rows:
            w.writerow([flag,nm,"client sets on pickup/purchase (flagless in game data)"])

    total=len(allrows)
    print(f"CURATED SET: {total} locations")
    print(f"  core (param natural flag): {core}")
    print(f"  filler (harvest/low-value, toggle-off): {filler}")
    print(f"  synthetic-flag checks     : {len(syn_rows)}")
    print(f"  core+synthetic (default on): {core+len(syn_rows)}")
    print("\nfor reference, matt/current set: 4150 keyed locations / 4493 flags")
    print("wrote", OUT)
    print("wrote", SYN, "(", len(syn_rows), "synthetic flags )")

if __name__=="__main__":
    main()
