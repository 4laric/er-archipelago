# -*- coding: utf-8 -*-
"""Dry-run report for the check-trim pass (SPEC-check-trim.md). Standalone: parses
locations.py / items.py / item_tiers.tsv by regex so it runs without the AP framework.
Mirrors EldenRing._is_bad_and_remote / _remoteness, INCLUDING the Phase-2 grace-distance
term when worlds/eldenring/location_remoteness.py exists. Use it to tune thresholds.
    python3 tools/trim_report.py [remote_threshold]   (default 3)
"""
import re, csv, collections, sys, os, importlib.util
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
base=os.path.join(ROOT,"Archipelago","worlds","eldenring")
loc=open(os.path.join(base,"locations.py"),encoding="utf-8",errors="replace").read()
itm=open(os.path.join(base,"items.py"),encoding="utf-8",errors="replace").read()
tiers={r["item_name"]:r["tier"] for r in csv.DictReader(open(os.path.join(ROOT,"item_tiers.tsv"),encoding="utf-8"),delimiter="\t")}
THR=int(sys.argv[1]) if len(sys.argv)>1 else 3
BAD={"C","D","F"}; KEEP=("Malenia's","Snow Witch")
DUNG=("caveboss","tunnelboss","catacombboss","graveboss","minidungeonboss","crawl")
GRACE_MED_M, GRACE_FAR_M = 70.0, 140.0
# optional Phase-2 grace distances
LGD={}
lrp=os.path.join(base,"location_remoteness.py")
if os.path.exists(lrp):
    spec=importlib.util.spec_from_file_location("location_remoteness",lrp)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    LGD=getattr(m,"LOC_GRACE_DIST",{})
JUNK=set()
jp=os.path.join(base,"junk_goods.py")
if os.path.exists(jp):
    spec2=importlib.util.spec_from_file_location("junk_goods",jp)
    m2=importlib.util.module_from_spec(spec2); spec2.loader.exec_module(m2)
    JUNK=set(getattr(m2,"JUNK_GOODS",()))
cat={}; prog=set()
for m in re.finditer(r'ERItemData\(\s*"((?:[^"\\]|\\.)*)"(.*)', itm):
    rest=m.group(2)
    cm=re.search(r'ERItemCategory\.(\w+)',rest)
    if cm: cat[m.group(1)]=cm.group(1)
    if "ItemClassification.progression" in rest: prog.add(m.group(1))
def grab(var):
    j=loc.find("[",loc.find(var+" =")); depth=0; k=j
    while k<len(loc):
        if loc[k]=="[":depth+=1
        elif loc[k]=="]":
            depth-=1
            if depth==0:break
        k+=1
    return re.findall(r'"((?:[^"\\]|\\.)*)"',loc[j:k+1])
idx={r:i for i,r in enumerate(grab("region_order")+grab("region_order_dlc"))}
MAXI=max(len(idx)-1,1)
cur=None; locs=[]
for line in loc[loc.find("location_tables"):].splitlines():
    h=re.match(r'\s+"([^"]+)":\s*\[',line)
    if h: cur=h.group(1); continue
    m=re.search(r'ERLocationData\(\s*"((?:[^"\\]|\\.)*)"\s*,\s*("(?:[^"\\]|\\.)*"|None)(.*)',line)
    if m:
        item=None if m.group(2)=="None" else m.group(2)[1:-1]
        rest=m.group(3)
        km=re.search(r'key\s*=\s*"((?:[^"\\]|\\.)*)"',rest)
        key=km.group(1) if km else None
        flags={f for f in ("outoftheway","hidden","deadend","chest")+DUNG if f+"=True" in rest}
        locs.append((cur,m.group(1),item,flags,key))
def rem(flags,region,key):
    s=0
    if "outoftheway" in flags:s+=3
    if "hidden" in flags:s+=1
    if "deadend" in flags:s+=1
    if any(t in flags for t in DUNG):s+=2
    i=idx.get(region)
    if i is not None and i>=0.6*MAXI:s+=1
    if key and key in LGD:
        d=LGD[key]
        if d>=GRACE_FAR_M:s+=3
        elif d>=GRACE_MED_M:s+=1
    return s
dropped=[]
junk_drop=[]
somber_drop=[]  # moderate somber cut: far (>=GRACE_FAR_M) Somber Smithing Stone checks, all levels
for region,lname,item,flags,key in locs:
    if not item: continue
    if item in JUNK and "graveyard" not in lname.lower():
        junk_drop.append((region,lname,item)); continue
    if item.startswith("Somber Smithing Stone") and key:
        d=LGD.get(key)
        if d is not None and d>=GRACE_FAR_M:
            somber_drop.append((region,lname,item)); continue
    c=cat.get(item)
    if c not in ("WEAPON","ARMOR"): continue
    if item in prog or any(item.startswith(p) for p in KEEP): continue
    if "chest" in flags and c=="WEAPON": continue
    if tiers.get(item) not in BAD: continue
    if rem(flags,region,key)>=THR: dropped.append((region,lname,item,c,tiers.get(item)))
assert all(d[2] not in prog for d in dropped), "PROGRESSION ITEM DROPPED"
print(f"grace-distance data: {'LOADED '+str(len(LGD))+' checks' if LGD else 'NOT PRESENT (Phase-1 tags+region only)'}")
print(f"threshold>={THR}  dropped {len(dropped)} checks  (no progression dropped: OK)")
print(f"junk GOODS dropped (cookbooks/greases/materials): {len(junk_drop)}")
print(f"remote somber stones dropped (far >= {GRACE_FAR_M:.0f}m, all levels): {len(somber_drop)}")
print(f"COMBINED Trimmed drops (gear + junk GOODS + remote somber): {len(dropped)+len(junk_drop)+len(somber_drop)}")
print("by region:")
for r,n in collections.Counter(d[0] for d in dropped).most_common():
    print(f"  {n:3d}  {r}")
print("drops:")
for d in sorted(dropped):
    print(f"  [{d[4]}] {d[3]:6} {d[2]:30} @ {d[0]}  ({d[1]})")
