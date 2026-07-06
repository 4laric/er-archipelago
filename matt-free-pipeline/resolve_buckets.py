#!/usr/bin/env python3
"""Take down the 4 REGION_PENDING buckets (matt-free). Idempotent: re-resolves every
row whose method is NOT treasure/emevd, so it can be re-run after edits."""
import csv, os, re
from collections import Counter, OrderedDict
csv.field_size_limit(10**7)

BASE = "/sessions/sleepy-laughing-mendel/mnt/er-archipelago/elden_ring_artifacts/vanilla_er/vanilla_er"
PIPE = "/sessions/sleepy-laughing-mendel/mnt/er-archipelago/matt-free-pipeline"
OUT  = "/tmp/mfbuckets"
os.makedirs(OUT, exist_ok=True)
FIXED = {"treasure","emevd"}

SHOP_BLOCK = {
 100000:("Limgrave (Church of Elleh)","high"),        # Merchant Kale
 100100:("Roundtable Hold","high"),                   # Twin Maiden Husks
 100200:("Liurnia of the Lakes (Ranni's Rise)","med"),# War Counselor Iji (web-confirmed: Carian Filigreed Crest + Carian sorceries)
 100300:("Liurnia of the Lakes (Seluvis's Rise)","med"),# Preceptor Seluvis (puppets)
 100400:("Limgrave (Waypoint Ruins)","med"),          # Sorceress Sellen
 100500:("Limgrave","med"),                            # Nomadic Merchant (Waypoint Ruins note + Telescope)
 100600:("Weeping Peninsula","med"),                   # Nomadic Merchant (Crimson Amber Medallion, Demi-human note)
 100700:("Liurnia of the Lakes","med"),                # Nomadic Merchant
 100800:("Caelid","med"),                              # Nomadic Merchant (Land of Reeds set, Gravel Stone, Aeonian Butterfly)
 100900:("Siofra River / Nokron","low"),               # Abandoned Merchant (web: Larval Tear + Nascent Butterfly) -- coarse, IN-GAME CHECK
 101500:("Roundtable Hold","high"),                   # Twin Maidens boss armor sets
 101700:("Roundtable Hold","high"),                   # Enia remembrances
 101800:("Roundtable Hold","high"),                   # Twin Maiden Husks base weapon/armor stock (Alaric-confirmed: Scimitar/Battle Axe/Rapier/Heater Shield)
 101900:("Roundtable Hold","high"),                   # Enia remembrance weapons/spells
 102200:("Gravesite Plain (DLC)","med"),               # Moore (web-confirmed: Sanguine Amaryllis, Black Pyrefly)
 102300:("Raya Lucaria Academy","low"),                # sorceries -- IN-GAME CHECK
 102700:("Roundtable Hold","med"),                    # Enia DLC remembrances
 600000:("Unknown (tutorial / cut merchant?)","low"), # Falchion+Lone Wolf Ashes+Imp Shades note -- IN-GAME CHECK
 900000:("Caelid (Cathedral of Dragon Communion)","med"),# dragon incantations
 1600100:("Unknown (merchant TBD)","low"),             # IN-GAME CHECK
 1600400:("Raya Lucaria Academy","low"),               # staves/seals -- IN-GAME CHECK
 9000000:("Unknown (merchant TBD)","low"),             # single item -- IN-GAME CHECK
 9001000:("Unknown (merchant TBD)","low"),             # single item -- IN-GAME CHECK
}

# exact-ID overrides where a hundred-block holds >1 merchant or a non-merchant lineup
# (id_lo, id_hi, region, method, confidence). Checked before the hundred-block table.
SHOP_ID_RULES = [
 (102300,102308,"Cathedral of Manus Metyr (DLC)","shop_merchant","high"),   # Count Ymir sorceries (screenshot-confirmed)
 (102350,102355,"Grand Altar of Dragon Communion (Jagged Peak, DLC)","shop_merchant","high"), # Bayle/Ghostflame: trade dragon hearts
 (600000,600099,"Non-merchant reference (starting gear; items placed in world)","shop_reference","na"),
 (1600100,1600199,"Non-merchant reference (starting gear; items placed in world)","shop_reference","na"),
 (1600400,1600499,"Non-merchant reference (caster kit; items placed in world)","shop_reference","na"),
 (9000000,9001099,"Non-merchant reference (gallery list; reuses key-item flags)","shop_reference","na"),
]
GREAT_RUNE = {
 "Godrick's Great Rune":"Stormveil Castle",
 "Radahn's Great Rune":"Caelid (Redmane Castle)",
 "Morgott's Great Rune":"Leyndell, Royal Capital",
 "Rykard's Great Rune":"Volcano Manor",
 "Mohg's Great Rune":"Mohgwyn Palace",
 "Malenia's Great Rune":"Miquella's Haligtree & Elphael",
 "Great Rune of the Unborn":"Raya Lucaria Academy",
}
REMEMBRANCE = {
 "Remembrance of the Grafted":"Stormveil Castle",
 "Remembrance of the Full Moon Queen":"Raya Lucaria Academy",
 "Remembrance of the Starscourge":"Caelid (Redmane Castle)",
 "Remembrance of the Regal Ancestor":"Nokron / Siofra (Ancestor Spirit)",
 "Remembrance of the Naturalborn":"Lake of Rot (Astel)",
 "Remembrance of the Blasphemous":"Volcano Manor (Rykard)",
 "Remembrance of the Fire Giant":"Mountaintops of the Giants",
 "Remembrance of the Blood Lord":"Mohgwyn Palace",
 "Remembrance of the Rot Goddess":"Miquella's Haligtree & Elphael",
 "Remembrance of the Black Blade":"Crumbling Farum Azula",
 "Remembrance of the Dragonlord":"Crumbling Farum Azula",
 "Remembrance of the Lichdragon":"Deeproot Depths (Lichdragon Fortissax)",
 "Remembrance of the Omen King":"Leyndell, Royal Capital",
 "Remembrance of Hoarah Loux":"Leyndell (Ashen Capital)",
 "Elden Remembrance":"Fractured Marika (final)",
 "Remembrance of the Dancing Lion":"Belurat, Tower Settlement (DLC)",
 "Remembrance of a God and a Lord":"Enir-Ilim (DLC)",
 "Remembrance of the Impaler":"Shadow Keep (DLC)",
 "Remembrance of Putrescence":"Stone Coffin Fissure (DLC)",
 "Remembrance of the Mother of Fingers":"Cathedral of Manus Metyr (DLC)",
 "Remembrance of the Lord of Frenzied Flame":"Midra's Manse (DLC)",
 "Remembrance of the Saint of the Bud":"Church of the Bud (DLC)",
 "Remembrance of the Shadow Sunflower":"Scadu Altus (DLC)",
 "Remembrance of the Wild Boar Rider":"Scadu Altus (DLC)",
 "Remembrance of the Twin Moon Knight":"Castle Ensis (DLC)",
}
AREACODE = {
 "LG":"Limgrave","WP":"Weeping Peninsula","LL":"Liurnia of the Lakes","CL":"Caelid",
 "AL":"Altus Plateau","AP":"Altus Plateau","MT":"Mountaintops of the Giants",
 "CS":"Consecrated Snowfield","MH":"Miquella's Haligtree & Elphael","FA":"Crumbling Farum Azula",
 "RLA":"Raya Lucaria Academy","RH":"Roundtable Hold","SSG":"Subterranean Shunning-Grounds",
 "LAC":"Leyndell, Royal Capital","NS":"Nokstella, Eternal City","MA":"Ainsel River / Lake of Rot",
 "TSC":"Siofra River / Nokron","GP":"Gravesite Plain (DLC)","SA":"Scadu Altus (DLC)","SF":"Consecrated Snowfield",
}

def load_flag2block():
    """f2b: forStock flag -> hundred-block. multi: flags whose equipId is sold across
    >1 block (multi-merchant / scroll-gated -> no single region)."""
    f2b={}; f2sid={}; from collections import defaultdict
    item_blocks=defaultdict(set); item_flags=defaultdict(list)
    with open(os.path.join(BASE,"ShopLineupParam.csv")) as f:
        r=csv.reader(f);h=next(r);iID=h.index("ID");ifl=h.index("eventFlag_forStock");ie=h.index("equipId");iet=h.index("equipType")
        for row in r:
            try: fl=int(row[ifl]); sid=int(row[iID]); item=int(row[ie]); et=int(row[iet])
            except: continue
            if fl<=0: continue
            f2b.setdefault(fl, sid//100*100)
            f2sid.setdefault(fl, sid)
            item_blocks[(et,item)].add(sid//100*100); item_flags[(et,item)].append(fl)
    multi=set()
    for k,blks in item_blocks.items():
        if len(blks)>1:
            multi.update(item_flags[k])
    return f2b, multi, f2sid

def resolve(r, f2b, multi, f2sid):
    src=r['flag_source']; nm=r['item_name']; fl=int(r['flag'])
    if src=='shop':
        sid=f2sid.get(fl)
        if sid is not None:
            for lo,hi,reg,meth,conf in SHOP_ID_RULES:
                if lo<=sid<=hi: return reg,meth,conf
        if fl in multi:
            return "Multiple merchants (various regions)","shop_multi","na"
        blk=f2b.get(fl)
        if blk in SHOP_BLOCK:
            reg,conf=SHOP_BLOCK[blk]; return reg,"shop_merchant",conf
        return "Unknown (merchant TBD)","shop_merchant","low"
    for k,reg in GREAT_RUNE.items():
        if k in nm: return reg,"boss_arena","high"
    for k,reg in REMEMBRANCE.items():
        if k in nm: return reg,"boss_arena","med"
    if src=='synthetic':
        m=re.match(r'^([A-Za-z]+)',nm)
        if m and m.group(1) in AREACODE: return AREACODE[m.group(1)],"synthetic_areacode","med"
        return "Global / Common-event (unplaced)","global","low"
    return "Global / Common-event (unplaced)","global","low"

def main():
    f2b, multi, f2sid=load_flag2block()
    rows=list(csv.DictReader(open(os.path.join(PIPE,"region_map.csv"))))
    touched=[]; mc=Counter(); confc=Counter()
    for r in rows:
        if r['method'] in FIXED: continue
        reg,meth,conf=resolve(r,f2b,multi,f2sid)
        r['region']=reg; r['method']=meth; r['_conf']=conf
        touched.append(dict(r)); mc[meth]+=1; confc[(meth,conf)]+=1
    with open(os.path.join(OUT,"region_map.csv"),"w",newline="") as f:
        w=csv.writer(f); w.writerow(["ap_id","flag","flag_source","item_name","map","region","method"])
        for r in rows: w.writerow([r["ap_id"],r["flag"],r["flag_source"],r["item_name"],r["map"],r["region"],r["method"]])
    with open(os.path.join(OUT,"bucket_resolution_report.csv"),"w",newline="") as f:
        w=csv.writer(f); w.writerow(["flag","flag_source","item_name","region","method","confidence"])
        for r in touched: w.writerow([r["flag"],r["flag_source"],r["item_name"],r["region"],r["method"],r["_conf"]])
    by=OrderedDict()
    for r in sorted(rows,key=lambda x:(x["region"],int(x["flag"]))): by.setdefault(r["region"],[]).append(r)
    def q(s): return '"'+str(s).replace("\\","\\\\").replace('"','\\"')+'"'
    with open(os.path.join(OUT,"locations_generated.py"),"w") as f:
        f.write('"""AUTO-GENERATED matt-free ER locations. Flag-keyed, no matt keys.\n')
        f.write('method col: treasure|emevd (MSB placement) | shop_merchant|boss_arena|synthetic_areacode\n')
        f.write('(item-class resolvers) | global (honestly-unplaced common-event tail)."""\n')
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
                        f'{bool(r["flag_source"]=="synthetic")}))\n')
                n+=1
        f.write(f"\n# {n} locations across {len(by)} regions\n")
    tot=len(rows); glob=sum(1 for r in rows if r['method']=='global'); placed=tot-glob
    print(f"total: {tot} | re-resolved this pass: {len(touched)}")
    print("  by method:", dict(mc))
    for k,v in sorted(confc.items()): print(f"     {k[0]:>18} {k[1]:>5} : {v}")
    print(f"REGION-PLACED (non-global): {placed} ({placed*100//tot}%) | GLOBAL tail: {glob} ({glob*100//tot}%) | regions: {len(by)}")

if __name__=="__main__": main()
