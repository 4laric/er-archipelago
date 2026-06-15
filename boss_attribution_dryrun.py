#!/usr/bin/env python3
"""Dry-run of boss attribution: how many checks end up under each boss INSTANCE.

Tier 1 uses the AUTHORITATIVE per-check Area from itemslots.txt (no centroid bleed):
  mini  : area tagged minidungeon (catacomb/cave/tunnel/grave/gaol/forge) -> its dungeon boss
  legacy: area name is a legacy dungeon (stormveil/academy/leyndell/volcano/farumazula/
          haligtree/caria/mohgwyn) -> its mainboss (lowest-id Boss in the area's maps)
Open-world checks use world coords:
  Tier 2: nearest field-boss instance in the same OPEN region, within DIST_CAP
  Tier 4: else the region capstone (great-rune / remembrance boss)
Field pool = Miniboss + DragonMiniboss + Evergaol + NightMiniboss. Hauls keyed by boss ID.
Approximate: boss positions from their own drop-check coords, else map-tile centre.
"""
import re, json, math, os, glob, statistics as st
from collections import defaultdict, Counter

BASE = "/sessions/hopeful-fervent-wozniak/mnt/er-archipelago"
DIST = f"{BASE}/SoulsRandomizers/diste/Base"
COORDS = sorted(glob.glob(f"{BASE}/SoulsRandomizers/ap_location_coords_*.txt"))[-1]
DIST_CAP = 800.0
print(f"coords dump: {os.path.basename(COORDS)}   DIST_CAP={DIST_CAP}")

# ---- 1. coords ----
key_coord={}; pts=[]
with open(COORDS, encoding="utf-8", errors="replace") as fh:
    next(fh)
    for line in fh:
        p=line.rstrip("\n").split("\t")
        if len(p)<7 or p[0]!="item": continue
        try: tx,tz=int(p[2]),int(p[3]); gx,gy,gz=float(p[4]),float(p[5]),float(p[6])
        except ValueError: continue
        key_coord[p[1]]=(tx,tz,gx,gy,gz); pts.append((tx,tz,gx,gz))
print(f"checks with coords: {len(key_coord)}")
def fit(xs,ys):
    n=len(xs); sx=sum(xs); sy=sum(ys); sxx=sum(x*x for x in xs); sxy=sum(x*y for x,y in zip(xs,ys))
    a=(n*sxy-sx*sy)/(n*sxx-sx*sx); return a,(sy-a*sx)/n
ax,bx=fit([t[0] for t in pts],[t[2] for t in pts]); az,bz=fit([t[1] for t in pts],[t[3] for t in pts])
tile_centre=lambda tx,tz:(ax*(tx+0.5)+bx, az*(tz+0.5)+bz)

# ---- 2. itemslots: key -> area ; key -> enemy ids ----
key_area={}; key_eids={}; cur=None; buf=[]
def flush(k,dbg):
    if k is not None: key_eids[k]=set(int(m) for m in re.findall(r"id (\d+)",dbg))
with open(f"{DIST}/itemslots.txt", encoding="utf-8", errors="replace") as fh:
    for line in fh:
        m=re.match(r"- Key: '(.+)'",line)
        if m: flush(cur," ".join(buf)); cur=m.group(1); buf=[]; continue
        if cur is None: continue
        a=re.match(r"  Area: (.+)",line)
        if a: key_area[cur]=a.group(1).strip()
        buf.append(line)
flush(cur," ".join(buf))

# ---- 3. annotations: area -> tags, maps ----
area_tags={}; area_maps={}; sec=None; an=None
with open(f"{DIST}/annotations.txt", encoding="utf-8", errors="replace") as fh:
    for line in fh:
        if re.match(r"^[A-Za-z]\w*:",line): sec=line.split(":")[0]
        if sec=="Areas":
            m=re.match(r"- Name: (\S+)",line)
            if m: an=m.group(1)
            elif an:
                mt=re.match(r"  Tags: (.+)",line);  mm=re.match(r"  Maps: (.+)",line)
                if mt: area_tags[an]=mt.group(1).split()
                if mm: area_maps[an]=mm.group(1).split()

LEGACY_PREFIX=("stormveil","academy","leyndell","volcano","farumazula","haligtree","caria","mohgwyn","shunning","subterranean")
def area_kind(area):
    if not area: return "open"
    if "minidungeon" in area_tags.get(area,[]): return "mini"
    if any(area==p or area.startswith(p) for p in LEGACY_PREFIX): return "legacy"
    return "open"

# ---- 4. enemy.txt: boss instances ----
FIELD={"Miniboss","DragonMiniboss","Evergaol","NightMiniboss"}
def best_name(d):
    for k in ("ExtraName","ItemName","PartName","FullName"):
        v=d.get(k)
        if v and "$" not in v: return v
    return str(d.get("ID"))
bosses=[]
for blk in re.split(r"\n(?=- ID:)", open(f"{DIST}/enemy.txt",encoding="utf-8",errors="replace").read()):
    idm=re.match(r"- ID: (\d+)",blk)
    if not idm: continue
    d={"ID":int(idm.group(1))}
    for m in re.finditer(r"  (\w+): (.+)",blk): d.setdefault(m.group(1),m.group(2).strip())
    if d.get("Class") not in (FIELD|{"Boss","MinorBoss"}): continue
    tm=re.match(r"m60_(\d+)_(\d+)",d.get("Map",""))
    bosses.append({"id":d["ID"],"cls":d["Class"],"map":d.get("Map",""),
                   "tile":(int(tm.group(1)),int(tm.group(2))) if tm else None,"name":best_name(d)})
eid_pts=defaultdict(list)
for k,eids in key_eids.items():
    if k in key_coord:
        tx,tz,gx,gy,gz=key_coord[k]
        for e in eids: eid_pts[e].append((tx,tz,gx,gz))
for b in bosses:
    pb=eid_pts.get(b["id"],[])
    if b["tile"]: pb=[p for p in pb if (p[0],p[1])==b["tile"]] or pb
    if pb: b["gx"]=sum(p[2] for p in pb)/len(pb); b["gz"]=sum(p[3] for p in pb)/len(pb)
    elif b["tile"]: b["gx"],b["gz"]=tile_centre(*b["tile"])
    else: b["gx"]=b["gz"]=None
bossname={b["id"]:b["name"] for b in bosses}
byid={b["id"]:b for b in bosses}

# manual overrides for areas with no in-map Boss/MinorBoss (e.g. Patches ambush)
AREA_BOSS_OVERRIDE={"limgrave_murkwatercave":10000850}  # Murkwater Cave -> Margit, the Fell Omen
# area (mini/legacy) -> its boss = lowest-id Boss in the area maps, else lowest-id MinorBoss
def area_boss(area):
    if area in AREA_BOSS_OVERRIDE: return AREA_BOSS_OVERRIDE[area]
    amaps=set(area_maps.get(area,[]))
    cands=[b for b in bosses if b["cls"]=="Boss" and b["map"] in amaps] or \
          [b for b in bosses if b["cls"]=="MinorBoss" and b["map"] in amaps]
    return min(cands,key=lambda b:b["id"])["id"] if cands else None

# ---- 5. open regions from centroids + capstones ----
raw=open(f"{BASE}/poptracker/maps/region_centroids.json").read()
cent={m.group(1):(float(m.group(2)),float(m.group(3)))
      for m in re.finditer(r'"([^"]+)":\s*\{\s*"gx":\s*([\d.\-]+),\s*"gz":\s*([\d.\-]+)',raw)}
DUNG_KW=("Catacomb","Cave","Tunnel","Hero's Grave","Gaol","Grotto","Tomb","Hideaway","Belfries",
         "Divine Tower","Study Hall","Crystal","Manor","Stormveil","Raya Lucaria","Volcano Manor",
         "Leyndell","Farum","Haligtree","Elphael")
open_cent={n:c for n,c in cent.items() if not any(k in n for k in DUNG_KW)}
onames=list(open_cent)
nearest_open=lambda gx,gz:min(onames,key=lambda n:(open_cent[n][0]-gx)**2+(open_cent[n][1]-gz)**2)
print(f"open regions: {len(open_cent)}")

CAPSTONE={
 "Limgrave":"Godrick the Grafted","Stormhill":"Godrick the Grafted","Church of Dragon Communion":"Godrick the Grafted",
 "Stormveil Start":"Godrick the Grafted","Weeping Peninsula":"Leonine Misbegotten",
 "Liurnia of The Lakes":"Rennala","Bellum Highway":"Rennala","Moonlight Altar":"Rennala",
 "Caelid":"Starscourge Radahn","Dragonbarrow":"Starscourge Radahn","Wailing Dunes":"Starscourge Radahn",
 "Altus Plateau":"Tree Sentinel Duo","Capital Outskirts":"Morgott","Frenzied Flame Proscription":"Mohg, the Omen",
 "Subterranean Shunning-Grounds":"Mohg, the Omen","Mt. Gelmir":"Rykard","Mountaintops of the Giants":"Fire Giant",
 "Flame Peak":"Fire Giant","Forbidden Lands":"Fire Giant","Consecrated Snowfield":"Astel",
 "Siofra River":"Regal Ancestor Spirit","Nokron, Eternal City":"Regal Ancestor Spirit",
 "Nokron, Eternal City Start":"Regal Ancestor Spirit","Ainsel River":"Astel","Ainsel River Main":"Astel",
 "Lake of Rot":"Astel","Deeproot Depths":"Lichdragon Fortissax","Deeproot Depths Upper":"Lichdragon Fortissax",
 "Deeproot Depths Boss":"Lichdragon Fortissax","Mohgwyn Palace":"Mohg, Lord of Blood",
 "Scadu Altus":"Messmer","Gravesite Plain":"Messmer",
}
# field bosses -> open region
for b in bosses:
    if b["cls"] in FIELD and b["gx"] is not None: b["region"]=nearest_open(b["gx"],b["gz"])
by_region=defaultdict(list)
for b in bosses:
    if b["cls"] in FIELD and b["gx"] is not None: by_region[b["region"]].append(b)
nfield=sum(1 for b in bosses if b["cls"] in FIELD and b["gx"] is not None)

# ---- 6. assign ----
haul=Counter(); cap_haul=Counter(); tier=Counter(); capped=0; noarea=0
check_out={}  # key -> ("1mini"|"1legacy"|"2field"|"4capstone", region_or_None, field_dist_or_None)
for k,(tx,tz,gx,gy,gz) in key_coord.items():
    area=key_area.get(k)
    if area is None: noarea+=1
    kind=area_kind(area)
    if kind in ("mini","legacy"):
        bid=area_boss(area)
        if bid: haul[bid]+=1
        else: cap_haul[f"[no boss] {area}"]+=1
        tier["1 "+kind]+=1; check_out[k]=("1"+kind,None,None); continue
    reg=nearest_open(gx,gz); best=None; bd=1e18
    for b in by_region.get(reg,[]):
        d=math.hypot(gx-b["gx"],gz-b["gz"])
        if d<bd: bd=d; best=b
    if best and bd<=DIST_CAP: haul[best["id"]]+=1; tier["2 field"]+=1; check_out[k]=("2field",reg,bd)
    else:
        cap_haul[CAPSTONE.get(reg,reg)]+=1; tier["4 capstone"]+=1
        check_out[k]=("4capstone",reg,bd if best else None)
        if best: capped+=1

# ---- 6c. GRACE LAYER (complement trigger; first-of {boss,grace} wins) ----
# graces from the coords dump (type=grace, key=eventflagId)
graces=[]
for line in open(COORDS,encoding="utf-8",errors="replace"):
    p=line.rstrip("\n").split("\t")
    if len(p)>=7 and p[0]=="grace":
        try: graces.append((p[1],int(p[2]),int(p[3]),float(p[4]),float(p[5]),float(p[6])))
        except ValueError: pass
for g in graces:
    pass
grace_xyz=[(g[3],g[4],g[5],g[0]) for g in graces]
# grace flag/rowid -> name (BonfireWarpParam Names table; DLC graces may be absent)
gname={}
import os as _os
_np=f"{BASE}/SoulsRandomizers/diste/Names/BonfireWarpParam.txt"
if _os.path.exists(_np):
    for _l in open(_np,encoding="utf-8",errors="replace"):
        _l=_l.rstrip("\n")
        if " " in _l:
            _i,_n=_l.split(" ",1); gname[_i.strip()]=_n.strip()
def nearest_grace(gx,gy,gz):
    best=None; bd=1e18
    for X,Y,Z,fid in grace_xyz:
        d=(gx-X)**2+(gy-Y)**2+(gz-Z)**2
        if d<bd: bd=d; best=(fid,math.sqrt(d))
    return best
GRACE_CAP=160.0   # a check gets a grace trigger only if a grace is within this (world units)
grace_haul=Counter(); covered=0
complement_capstone=0; complement_farfield=0
cap_total=0; far_total=0
for k,(tx,tz,gx,gy,gz) in key_coord.items():
    out=check_out.get(k)
    fid,gd=nearest_grace(gx,gy,gz)
    has_grace = gd<=GRACE_CAP
    if has_grace: grace_haul[fid]+=1; covered+=1
    if out:
        if out[0]=="4capstone":
            cap_total+=1; complement_capstone+= has_grace
        if out[0]=="2field" and out[2] is not None and out[2]>300:
            far_total+=1; complement_farfield+= has_grace

# ---- 6b. CSV export (every bucket) ----
rows=[]
for bid,c in haul.items():
    b=byid[bid]
    t="Tier1-dungeon" if b["cls"] in ("Boss","MinorBoss") else "Tier2-field"
    rows.append((t,b["cls"],bossname[bid],b.get("region","") if b["cls"] in FIELD else "",c))
for lbl,c in cap_haul.items():
    rows.append(("Tier4-capstone","capstone",lbl,"",c))
rows.sort(key=lambda r:-r[4])
out=f"{BASE}/boss-attribution-dryrun.csv"
with open(out,"w",encoding="utf-8") as f:
    f.write("tier,boss_class,boss,region,checks\n")
    for t,cl,nm,rg,c in rows:
        f.write(f'{t},{cl},"{nm}","{rg}",{c}\n')
print(f"wrote {out}  ({len(rows)} buckets)")

# ---- 7. report ----
tot=sum(tier.values())
print("\n==== TIER BREAKDOWN ====")
for t in sorted(tier): print(f"  {t:12s}: {tier[t]:4d}  ({100*tier[t]/tot:.1f}%)")
print(f"  {'TOTAL':12s}: {tot}   (checks beyond cap -> capstone: {capped}; checks w/o area: {noarea})")
print(f"\n==== FIELD POOL: {nfield}/{sum(1 for b in bosses if b['cls'] in FIELD)} instances positioned ====")
fvals=sorted(haul[b['id']] for b in bosses if b['cls'] in FIELD and haul.get(b['id'],0))
if fvals: print(f"  caught>=1: {len(fvals)}   checks/instance  min {fvals[0]} median {st.median(fvals):.0f} mean {st.mean(fvals):.1f} max {fvals[-1]}")
print("\n==== TOP 30 FIELD-BOSS INSTANCES (Tier 2) ====")
fb=[(bid,c) for bid,c in haul.items() if byid[bid]["cls"] in FIELD]
for bid,c in sorted(fb,key=lambda x:-x[1])[:30]:
    b=byid[bid]; print(f"  {c:4d}  {bossname[bid]:30s} {b['cls']:14s} tile{b['tile']}")
print("\n==== TIER-1 DUNGEON/LEGACY BOSS HAULS (top 25) ====")
d1=[(bid,c) for bid,c in haul.items() if byid[bid]["cls"] in ("Boss","MinorBoss")]
for bid,c in sorted(d1,key=lambda x:-x[1])[:25]: print(f"  {c:4d}  {bossname[bid]}")
print("\n==== TIER-4 CAPSTONE HAULS ====")
for lbl,c in cap_haul.most_common(): print(f"  {c:4d}  {lbl}")
print(f"\n  distinct boss buckets: {len(haul)} bosses + {len(cap_haul)} capstone labels")

print(f"\n==== GRACE LAYER (complement, GRACE_CAP={GRACE_CAP}u) ====")
print(f"  graces in dump: {len(graces)}   graces that catch >=1 check: {len(grace_haul)}")
gv=sorted(grace_haul.values())
if gv: print(f"  checks/grace within cap:  min {gv[0]} median {st.median(gv):.0f} mean {st.mean(gv):.1f} max {gv[-1]}")
print(f"  checks with a grace within {GRACE_CAP}u: {covered}/{len(key_coord)} ({100*covered/len(key_coord):.0f}%)")
print(f"  CAPSTONE checks also covered by a grace: {complement_capstone}/{cap_total} ({100*complement_capstone/max(cap_total,1):.0f}%)  <-- sparse-region rescue")
print(f"  FAR field checks (>300u) also covered by a grace: {complement_farfield}/{far_total} ({100*complement_farfield/max(far_total,1):.0f}%)")

# ---- 8. per-check CLOSEST GRACE export (for hinting) ----
# grace names are a bake-time FMG join; here we emit flag + distance + region.
import csv as _csv
gpath=f"{BASE}/check-nearest-grace.csv"
with open(gpath,"w",newline="",encoding="utf-8") as f:
    w=_csv.writer(f); w.writerow(["check_key","area","region","attributed_boss","nearest_grace_flag","nearest_grace_name","grace_dist_u","within_cap","tier","field_dist_u"])
    for k,(tx,tz,gx,gy,gz) in key_coord.items():
        fid,gd=nearest_grace(gx,gy,gz)
        out=check_out.get(k,("",None,None)); reg=out[1] or ""
        bb=""  # attributed boss display
        # recover attributed boss for context
        ar=key_area.get(k); kind=area_kind(ar)
        if kind in ("mini","legacy"):
            bid=area_boss(ar); bb=bossname.get(bid,f"[{ar}]") if bid else f"[no boss] {ar}"
        elif out[0]=="2field":
            # nearest field boss again (cheap)
            best=None; bd=1e18
            for b in by_region.get(reg,[]):
                d=math.hypot(gx-b["gx"],gz-b["gz"])
                if d<bd: bd=d; best=b
            bb=bossname.get(best["id"],"") if best else ""
        elif out[0]=="4capstone":
            bb="[capstone] "+CAPSTONE.get(reg,reg)
        w.writerow([k,ar or "",reg,bb,fid,gname.get(str(fid),""),f"{gd:.0f}",int(gd<=GRACE_CAP),out[0],("" if out[2] is None else f"{out[2]:.0f}")])
print("\n==== TOP 12 GRACES BY CHECK HAUL ====")
for fid,c in grace_haul.most_common(12):
    print(f"  {c:4d}  [{fid}] {gname.get(str(fid),'?')}")
print(f"\nwrote {gpath}  (per-check nearest grace; {len(key_coord)} rows)")
# end
