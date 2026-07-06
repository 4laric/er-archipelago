#!/usr/bin/env python3
"""Generate matt_free_locations.py + er_static_detection_table_mattfree.json for the
MVP integration branch. Fully data-derived, matt-free.

Region assignment:
  - Overworld m60 tiles -> play_region via grace/BonfireWarp anchors (nearest-neighbor in tile
    grid), play_region -> apworld region via PLAY2AP.
  - Named/coarse backbone regions -> apworld region via REGION_MAP.
  - shop_multi (multi-merchant) -> Roundtable Hold (always-available hub).
Scoped OUT (per Alaric): method global (quest/NPC), global_filler (spam), shop_reference (phantom).
Item pool: default_item = backbone item_name if registered in items.py, else FILLER fallback.
Client contract: explicit ap_code, synthetic key "mf:<flag>", detection table {ap_code:[flag]}.
"""
import csv, re, os, json, math
from collections import Counter, defaultdict, OrderedDict
csv.field_size_limit(10**7)
REPO="/sessions/sleepy-laughing-mendel/mnt/er-archipelago"
APW=f"{REPO}/Archipelago/worlds/eldenring"
AR=f"{REPO}/elden_ring_artifacts"
PIPE=f"{REPO}/matt-free-pipeline"
OUT="/tmp/mvp"
FILLER="Golden Rune [1]"
SKIP_METHODS={"global","global_filler","shop_reference"}

# ---- apworld region_order + registered items ----
_src=open(f"{APW}/locations.py").read()
def _grab(v):
    m=re.search(v+r"\s*=\s*\[(.*?)\]",_src,re.S); return re.findall(r'"([^"]+)"',m.group(1)) if m else []
REGION_ORDER=_grab("region_order"); REGION_ORDER_DLC=_grab("region_order_dlc")
VALID_REGIONS=set(REGION_ORDER)|set(REGION_ORDER_DLC)
import json as _json
ITEMS=set(_json.load(open(f"{PIPE}/item_table_keys.json")))  # REAL item_table keys (create_items indexes this)

# ---- overworld tile -> play_region (grace anchors) ----
gf={}
for row in csv.DictReader(open(f"{AR}/grace_flags.tsv"),delimiter='\t'): gf[row['warpUnlockFlag']]=row['mapTile']
greg={}
grm=[x for x in os.listdir(AR) if x.startswith('grace_region_map')][0]
for row in csv.DictReader(open(f"{AR}/{grm}"),delimiter='\t'): greg[row['grace_flag']]=row['play_region_id']
_acc=defaultdict(Counter)
for flag,tile in gf.items():
    pr=greg.get(flag); m=re.match(r'm60_(\d\d)_(\d\d)',tile)
    if pr and pr!='0' and m: _acc[(int(m.group(1)),int(m.group(2)))][pr]+=1
ANCHOR={xy:c.most_common(1)[0][0] for xy,c in _acc.items()}
def tile_play_region(x,y):
    if (x,y) in ANCHOR: return ANCHOR[(x,y)]
    best,bd=None,1e18
    for (ax,ay),pr in ANCHOR.items():
        d=(ax-x)**2+(ay-y)**2
        if d<bd: bd,best=d,pr
    return best

PLAY2AP={  # play_region_id -> apworld region (lockable)
 '61000':'Limgrave','61001':'Limgrave','61002':'Weeping Peninsula',
 '62000':'Liurnia of The Lakes','62001':'Liurnia of The Lakes','62002':'Liurnia of The Lakes',
 '63000':'Altus Plateau','63001':'Mt. Gelmir','63002':'Altus Plateau','63003':'Altus Plateau',
 '64000':'Caelid','64001':'Dragonbarrow','64002':'Caelid',
 '65000':'Mountaintops of the Giants','65001':'Mountaintops of the Giants','65002':'Consecrated Snowfield',
}
REGION_MAP={  # backbone named/coarse region -> apworld region
 'Land of Shadow (DLC)':'Gravesite Plain','Eternal Cities & Underground Rivers':'Nokron, Eternal City Start',
 'Mohgwyn / Consecrated-adjacent':'Mohgwyn Palace','Leyndell / Roundtable / Shunning-Grounds':'Leyndell, Royal Capital',
 'DLC Interior':'Shadow Keep','Caves':'Limgrave','Roundtable Hold':'Roundtable Hold',
 'Stormveil Castle':'Stormveil Castle','Stormveil (assoc.)':'Stormveil Castle',
 "Miquella's Haligtree & Elphael":"Miquella's Haligtree",'Hero\'s Graves (Catacombs)':'Limgrave',
 'Crumbling Farum Azula':'Farum Azula','Divine Tower':'Liurnia of The Lakes',
 'Raya Lucaria Academy':'Raya Lucaria Academy','Volcano Manor / Mt. Gelmir':'Mt. Gelmir',
 'Volcano Manor (Rykard)':'Mt. Gelmir','DLC Dungeon':'Gravesite Plain','DLC Legacy Dungeon':'Belurat',
 'Tunnels':'Caelid','Limgrave':'Limgrave','Limgrave (Church of Elleh)':'Limgrave',
 'Limgrave (Waypoint Ruins)':'Limgrave','Liurnia of the Lakes':'Liurnia of The Lakes',
 "Liurnia of the Lakes (Seluvis's Rise)":'Liurnia of The Lakes',"Liurnia of the Lakes (Ranni's Rise)":'Liurnia of The Lakes',
 'Weeping Peninsula':'Weeping Peninsula','Siofra River / Nokron':'Siofra River','Caelid':'Caelid',
 'Caelid (Redmane Castle)':'Caelid','Caelid (Cathedral of Dragon Communion)':'Caelid',
 'Gravesite Plain (DLC)':'Gravesite Plain','Cathedral of Manus Metyr (DLC)':'Cathedral of Manus Metyr',
 'Scadu Altus (DLC)':'Scadu Altus','Consecrated Snowfield':'Consecrated Snowfield','Shadow Keep (DLC)':'Shadow Keep',
 'Altus Plateau':'Altus Plateau','Jagged Peak (DLC)':'Jagged Peak Foot',
 'Grand Altar of Dragon Communion (Jagged Peak, DLC)':'Jagged Peak Foot','Cerulean Coast (DLC)':'Cerulean Coast',
 'Abyssal Woods (DLC)':'Abyssal Woods','Mountaintops of the Giants':'Mountaintops of the Giants',
 'Leyndell, Royal Capital':'Leyndell, Royal Capital','Leyndell (Ashen Capital)':'Leyndell, Ashen Capital',
 'Nokron / Siofra (Ancestor Spirit)':'Nokron, Eternal City Start','Lake of Rot (Astel)':'Lake of Rot',
 'Deeproot Depths (Lichdragon Fortissax)':'Deeproot Depths','Fractured Marika (final)':'Erdtree',
 'Belurat, Tower Settlement (DLC)':'Belurat','Enir-Ilim (DLC)':'Enir Ilim',
 'Stone Coffin Fissure (DLC)':'Stone Coffin Fissure',"Midra's Manse (DLC)":'Abyssal Woods',
 'Church of the Bud (DLC)':'Scadu Altus','Castle Ensis (DLC)':'Castle Ensis',
 'm22':'Ainsel River','m28':'Gravesite Plain',
}
HUB='Roundtable Hold'

def ap_region(r):
    reg=r['region']; meth=r['method']
    if reg.startswith('Overworld m60'):
        m=re.match(r'.*m60_(\d\d)_(\d\d)',reg)
        if m:
            pr=tile_play_region(int(m.group(1)),int(m.group(2)))
            return PLAY2AP.get(pr,HUB)
        return HUB
    if meth=='shop_multi': return HUB
    return REGION_MAP.get(reg,HUB)

def main():
    rows=[r for r in csv.DictReader(open(f"{PIPE}/region_map.csv")) if r['method'] not in SKIP_METHODS]
    by=OrderedDict((rn,[]) for rn in REGION_ORDER+REGION_ORDER_DLC)
    det={}; apid=7000000; seen_names=set(); unmapped=Counter(); fb_items=0; usedhub=0
    for r in rows:
        reg=ap_region(r)
        if reg not in VALID_REGIONS: unmapped[r['region']]+=1; reg=HUB
        if reg==HUB and (r['region'] not in ('Roundtable Hold',) and r['method']!='shop_multi'): usedhub+=1
        flag=int(r['flag']); item=r['item_name']
        default=item if item in ITEMS else FILLER
        if default==FILLER and item not in ITEMS: fb_items+=1
        nm=f"{reg} :: {item or 'check'} [f{flag}]"
        if nm in seen_names: nm=f"{nm}#{apid}"
        seen_names.add(nm)
        by[reg].append((nm,default,apid,flag))
        det[str(apid)]=[flag]; apid+=1
    # keep ALL region keys (empty lists ok) so create_regions[region] never KeyErrors

    # emit module
    def q(s): return '"'+str(s).replace("\\","\\\\").replace('"','\\"')+'"'
    with open(f"{OUT}/matt_free_locations.py","w") as f:
        f.write('"""AUTO-GENERATED matt-free ER location tables for the MVP backbone integration.\n')
        f.write('Data-derived (vanilla params + MSB + grace anchors), NO matt keys/descriptions.\n')
        f.write('Drop-in for the apworld location source: exposes location_tables/location_order/location_dictionary.\n')
        f.write('Quest/NPC + scattered-filler + phantom-shop checks are scoped OUT of this MVP."""\n')
        f.write("from .locations import ERLocationData\n\n")
        f.write("location_tables = {\n")
        for reg,locs in by.items():
            f.write(f"  {q(reg)}: [\n")
            for nm,default,aid,flag in locs:
                di="None" if default is None else q(default)
                f.write(f"    ERLocationData({q(nm)}, {di}, ap_code={aid}, key={q('mf:'+str(flag))}),\n")
            f.write("  ],\n")
        f.write("}\n")
        f.write("location_order = list(location_tables.keys())\n")
        f.write("location_dictionary = {l.name: l for ls in location_tables.values() for l in ls}\n")
    json.dump({"location_flags":det}, open(f"{OUT}/er_static_detection_table_mattfree.json","w"))

    print(f"included checks: {sum(len(v) for v in by.values())} across {len(by)} apworld regions")
    print(f"filler-fallback default items: {fb_items}")
    print(f"routed-to-hub (unclassified): {usedhub}")
    if unmapped:
        print("UNMAPPED backbone regions -> hub (fix REGION_MAP):")
        for k,v in unmapped.most_common(): print(f"   {v:>4} {k}")
    else:
        print("all backbone regions mapped to a valid apworld region")
    # top regions
    print("\ntop apworld regions by check count:")
    for reg,locs in sorted(by.items(),key=lambda kv:-len(kv[1]))[:15]: print(f"  {len(locs):>4} {reg}")

if __name__=="__main__": main()
