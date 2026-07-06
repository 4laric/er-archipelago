#!/usr/bin/env python3
"""Generate eldenring_gf/data.py (regions + flag-keyed locations) for the Greenfield ER apworld.
Self-contained + data-derived: reads region_map.csv (this dir) + grace/BonfireWarp anchors from
elden_ring_artifacts. No dependency on any externally-named file. See LESSONS-LEARNED.md."""
import csv, re, os, math
from collections import Counter, defaultdict, OrderedDict
csv.field_size_limit(10**7)
HERE=os.path.dirname(os.path.abspath(__file__))
REPO=os.path.abspath(os.path.join(HERE,".."))
AR=os.path.join(REPO,"elden_ring_artifacts")
OUT=os.path.join(HERE,"eldenring_gf","data.py")
HUB="Roundtable Hold"
SKIP={"global","global_filler","shop_reference"}
BASE_AP=7770000  # greenfield location id space

# ---- overworld tile -> play_region via grace anchors + nearest-neighbor ----
gf={}
for row in csv.DictReader(open(os.path.join(AR,"grace_flags.tsv")),delimiter="\t"): gf[row["warpUnlockFlag"]]=row["mapTile"]
greg={}
grm=[x for x in os.listdir(AR) if x.startswith("grace_region_map")][0]
for row in csv.DictReader(open(os.path.join(AR,grm)),delimiter="\t"): greg[row["grace_flag"]]=row["play_region_id"]
_acc=defaultdict(Counter)
for flag,tile in gf.items():
    pr=greg.get(flag); m=re.match(r"m60_(\d\d)_(\d\d)",tile)
    if pr and pr!="0" and m: _acc[(int(m.group(1)),int(m.group(2)))][pr]+=1
ANCHOR={xy:c.most_common(1)[0][0] for xy,c in _acc.items()}
def tile_pr(x,y):
    if (x,y) in ANCHOR: return ANCHOR[(x,y)]
    best,bd=None,1e18
    for (ax,ay),pr in ANCHOR.items():
        d=(ax-x)**2+(ay-y)**2
        if d<bd: bd,best=d,pr
    return best
PLAY2AP={'61000':'Limgrave','61001':'Limgrave','61002':'Weeping Peninsula','62000':'Liurnia of the Lakes',
 '62001':'Liurnia of the Lakes','62002':'Liurnia of the Lakes','63000':'Altus Plateau','63001':'Mt. Gelmir',
 '63002':'Altus Plateau','63003':'Altus Plateau','64000':'Caelid','64001':'Dragonbarrow','64002':'Caelid',
 '65000':'Mountaintops of the Giants','65001':'Mountaintops of the Giants','65002':'Consecrated Snowfield'}
REGION_MAP={'Land of Shadow (DLC)':'Land of Shadow','Eternal Cities & Underground Rivers':'Eternal Cities',
 'Mohgwyn / Consecrated-adjacent':'Mohgwyn Palace','Leyndell / Roundtable / Shunning-Grounds':'Leyndell',
 'DLC Interior':'Shadow Keep','Caves':'Limgrave',"Roundtable Hold":'Roundtable Hold','Stormveil Castle':'Stormveil Castle',
 'Stormveil (assoc.)':'Stormveil Castle',"Miquella's Haligtree & Elphael":"Miquella's Haligtree",
 "Hero's Graves (Catacombs)":'Limgrave','Crumbling Farum Azula':'Farum Azula','Divine Tower':'Liurnia of the Lakes',
 'Raya Lucaria Academy':'Raya Lucaria Academy','Volcano Manor / Mt. Gelmir':'Mt. Gelmir','Volcano Manor (Rykard)':'Mt. Gelmir',
 'DLC Dungeon':'Land of Shadow','DLC Legacy Dungeon':'Belurat','Tunnels':'Caelid','Limgrave':'Limgrave',
 'Limgrave (Church of Elleh)':'Limgrave','Limgrave (Waypoint Ruins)':'Limgrave','Liurnia of the Lakes':'Liurnia of the Lakes',
 "Liurnia of the Lakes (Seluvis's Rise)":'Liurnia of the Lakes',"Liurnia of the Lakes (Ranni's Rise)":'Liurnia of the Lakes',
 'Weeping Peninsula':'Weeping Peninsula','Siofra River / Nokron':'Eternal Cities','Caelid':'Caelid',
 'Caelid (Redmane Castle)':'Caelid','Caelid (Cathedral of Dragon Communion)':'Caelid','Gravesite Plain (DLC)':'Land of Shadow',
 'Cathedral of Manus Metyr (DLC)':'Scadu Altus','Scadu Altus (DLC)':'Scadu Altus','Consecrated Snowfield':'Consecrated Snowfield',
 'Shadow Keep (DLC)':'Shadow Keep','Altus Plateau':'Altus Plateau','Jagged Peak (DLC)':'Jagged Peak',
 'Grand Altar of Dragon Communion (Jagged Peak, DLC)':'Jagged Peak','Cerulean Coast (DLC)':'Land of Shadow',
 'Abyssal Woods (DLC)':'Abyssal Woods','Mountaintops of the Giants':'Mountaintops of the Giants',
 'Leyndell, Royal Capital':'Leyndell','Leyndell (Ashen Capital)':'Leyndell','Nokron / Siofra (Ancestor Spirit)':'Eternal Cities',
 'Lake of Rot (Astel)':'Eternal Cities','Deeproot Depths (Lichdragon Fortissax)':'Eternal Cities','Fractured Marika (final)':'Leyndell',
 'Belurat, Tower Settlement (DLC)':'Belurat','Enir-Ilim (DLC)':'Land of Shadow','Stone Coffin Fissure (DLC)':'Land of Shadow',
 "Midra's Manse (DLC)":'Abyssal Woods','Church of the Bud (DLC)':'Scadu Altus','Castle Ensis (DLC)':'Belurat',
 'm22':'Eternal Cities','m28':'Land of Shadow'}

def region_of(r):
    reg=r['region']; meth=r['method']
    if reg.startswith('Overworld m60'):
        m=re.match(r'.*m60_(\d\d)_(\d\d)',reg)
        return PLAY2AP.get(tile_pr(int(m.group(1)),int(m.group(2))),HUB) if m else HUB
    if meth=='shop_multi': return HUB
    return REGION_MAP.get(reg,HUB)

rows=[r for r in csv.DictReader(open(os.path.join(HERE,"region_map.csv"))) if r['method'] not in SKIP]
buckets=OrderedDict()
apid=BASE_AP; names=set()
for r in rows:
    reg=region_of(r); flag=int(r['flag']); item=r['item_name'] or 'check'
    nm=f"{reg} :: {item} [f{flag}]"
    if nm in names: nm=f"{nm}#{apid}"
    names.add(nm)
    buckets.setdefault(reg,[]).append((nm,apid,flag)); apid+=1

spokes=sorted(k for k in buckets if k!=HUB)
with open(OUT, "w", newline="\n") as f:
    f.write('"""AUTO-GENERATED Greenfield ER data (gen_data.py). Data-derived, no external naming."""\n')
    f.write(f"HUB = {HUB!r}\n")
    f.write("REGIONS = [\n")
    for r in spokes: f.write(f"    {r!r},\n")
    f.write("]\n\nLOCATIONS = {\n")
    for r in [HUB]+spokes:
        f.write(f"    {r!r}: [\n")
        for nm,aid,flag in buckets.get(r,[]): f.write(f"        ({nm!r}, {aid}, {flag}),\n")
        f.write("    ],\n")
    f.write("}\n")
print(f"spokes={len(spokes)} hub_locs={len(buckets.get(HUB,[]))} total={sum(len(v) for v in buckets.values())}")

# ---- Phase 0 boot contract: one warp-grace open flag per major region (matt-free) -----------
# Derived from the SAME grace anchors used above. On lock receipt the client sets this flag
# (region.rs region_open_flags), lighting the region's front-door grace so the player can warp in.
# DLC sub-areas whose locations are all boss-arena (map=PENDING) don't resolve to a grace here ->
# left PENDING; the client treats an absent open flag as "unlocked" (SPEC-PARITY.md 14.4).
def _map_pref(m):
    if not m or m == "PENDING": return None
    p = m.split("_")
    return "_".join(p[:3]) if m.startswith("m60") and len(p) >= 3 else "_".join(p[:2])
_pref2maj = defaultdict(Counter)
for _r in rows:
    _mj = region_of(_r); _pf = _map_pref(_r["map"])
    if _pf and _mj: _pref2maj[_pf][_mj] += 1
_pref2maj = {p: c.most_common(1)[0][0] for p, c in _pref2maj.items()}
_open_cand = defaultdict(list)
for _fl, _tile in gf.items():          # gf = {warpUnlockFlag(str): mapTile}, built at top
    _mj = None
    _m = re.match(r"m60_(\d\d)_(\d\d)", _tile)
    if _m: _mj = PLAY2AP.get(tile_pr(int(_m.group(1)), int(_m.group(2))))
    if not _mj: _mj = _pref2maj.get(_map_pref(_tile))
    if _mj and _mj != HUB: _open_cand[_mj].append(int(_fl))
REGION_OPEN_FLAGS = {r: min(_open_cand[r]) for r in spokes if _open_cand.get(r)}
REGION_OPEN_PENDING = [r for r in spokes if r not in REGION_OPEN_FLAGS]
OUT_OPEN = os.path.join(HERE, "eldenring_gf", "region_open_flags.py")
with open(OUT_OPEN, "w", newline="\n") as _f:
    _f.write('"""AUTO-GENERATED (gen_data.py). Per-region warp-grace open flags for the Phase 0 boot\n')
    _f.write('contract; derived from grace anchors (matt-free). PENDING = DLC sub-area to resolve in\n')
    _f.write('the region audit (SPEC-PARITY.md 14.4); client treats an absent open flag as unlocked."""\n')
    _f.write("REGION_OPEN_FLAGS = {\n")
    for _r in spokes:
        if _r in REGION_OPEN_FLAGS: _f.write(f"    {_r!r}: {REGION_OPEN_FLAGS[_r]},\n")
    _f.write("}\n\nREGION_OPEN_PENDING = [\n")
    for _r in REGION_OPEN_PENDING: _f.write(f"    {_r!r},\n")
    _f.write("]\n")
print(f"region_open_flags: {len(REGION_OPEN_FLAGS)} resolved, {len(REGION_OPEN_PENDING)} pending -> {REGION_OPEN_PENDING}")
