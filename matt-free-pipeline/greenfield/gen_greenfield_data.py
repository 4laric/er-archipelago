#!/usr/bin/env python3
"""Generate the greenfield matt-free world's data.py from matt_free_locations.py.
Reuses the region assignment already computed there (clean apworld region names + flags).
Emits: HUB, REGIONS (locked spokes), LOCATIONS {region:[(name,ap_id,flag)]}, LOCK_FLAG (region->region-open flag placeholder)."""
import re, os, importlib.util
APW="/sessions/sleepy-laughing-mendel/mnt/er-archipelago/Archipelago/worlds/eldenring"
OUT="/tmp/gf/eldenring_mf/data.py"
HUB="Roundtable Hold"

class ERLocationData:  # stub matching the constructor used in matt_free_locations.py
    def __init__(self,name,default,ap_code=None,key=None):
        self.name=name; self.default_item_name=default; self.ap_code=ap_code; self.key=key
src=open(os.path.join(APW,"matt_free_locations.py")).read().replace("from .locations import ERLocationData","")
g={"ERLocationData":ERLocationData}; exec(src,g)
LT=g["location_tables"]

def flag_of(k):
    m=re.match(r"mf:(\d+)",k or ""); return int(m.group(1)) if m else None

regions=[r for r in LT if LT[r] and r!=HUB]
data_locs={}
for r,locs in LT.items():
    if not locs: continue
    data_locs[r]=[(l.name, l.ap_code, flag_of(l.key)) for l in locs]

with open(OUT,"w") as f:
    f.write('"""AUTO-GENERATED greenfield matt-free ER data (gen_greenfield_data.py). No matt keys."""\n')
    f.write(f'HUB = {HUB!r}\n')
    f.write('# locked spokes (each gated by "<region> Lock"); HUB is free.\n')
    f.write("REGIONS = [\n")
    for r in sorted(regions): f.write(f"    {r!r},\n")
    f.write("]\n\n")
    f.write("# region -> list of (location_name, ap_id, game_event_flag)\n")
    f.write("LOCATIONS = {\n")
    for r in sorted(data_locs):
        f.write(f"    {r!r}: [\n")
        for nm,aid,flag in data_locs[r]:
            f.write(f"        ({nm!r}, {aid}, {flag}),\n")
        f.write("    ],\n")
    f.write("}\n")

tot=sum(len(v) for v in data_locs.values())
print(f"regions(spokes)={len(regions)} hub_locs={len(data_locs.get(HUB,[]))} total_locations={tot}")
print("wrote",OUT)
