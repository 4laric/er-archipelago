#!/usr/bin/env python3
"""ORIGINAL data-derived stylized overworld map for the ER-AP PopTracker pack (M3a prototype).

Landmass = rounded convex hull of the real coordinate cloud (original stylization, no game art).
Overlay = real location points (faint) + sites of grace (gold) + LABELED REGION PINS placed at
each region's real coordinate centroid (region = location-key -> region join from locations.py).
Authored in gx/gz space => world->image transform is EXACT (map_calibration.json). +Z = North."""
import csv, json, math, re, statistics
from collections import defaultdict

ROOT = "/sessions/gracious-tender-noether/mnt/er-archipelago"
SRC  = ROOT + "/SoulsRandomizers/ap_location_coords_20260614-212638.txt"
LOCS = ROOT + "/Archipelago/worlds/eldenring/locations.py"
OUT_SVG = "/sessions/gracious-tender-noether/mnt/outputs/lands_between_map.svg"
OUT_CAL = "/sessions/gracious-tender-noether/mnt/outputs/map_calibration.json"
OUT_CEN = "/sessions/gracious-tender-noether/mnt/outputs/region_centroids.json"

# ---- key -> region (from locations.py) -----------------------------------------------
lines = open(LOCS).read().split('\n')
start = next(i for i,l in enumerate(lines) if l.startswith("location_tables"))
hdr = re.compile(r'^    "([^"]+)":\s*\['); kpat = re.compile(r'key="([^"]+)"')
region=None; kr={}
for i in range(start,len(lines)):
    m=hdr.match(lines[i])
    if m: region=m.group(1); continue
    if region:
        km=kpat.search(lines[i])
        if km: kr.setdefault(km.group(1),region)

# ---- coords --------------------------------------------------------------------------
rows=list(csv.DictReader(open(SRC),delimiter='\t'))
def base(r):
    x,z=float(r['gx']),float(r['gz']); return x<1e8 and z<1e8 and int(r['tileX'])<55
pts=[(float(r['gx']),float(r['gz']),r['type']) for r in rows if base(r)]
xs=[p[0] for p in pts]; zs=[p[1] for p in pts]
x0,x1=min(xs),max(xs); z0,z1=min(zs),max(zs)

reg_pts=defaultdict(list)
for r in rows:
    if r['type']!='item' or not base(r): continue
    reg=kr.get(r['key'])
    if reg: reg_pts[reg].append((float(r['gx']),float(r['gz'])))
cent={r:{"gx":round(statistics.median(p[0] for p in ps),1),
         "gz":round(statistics.median(p[1] for p in ps),1),"n":len(ps)} for r,ps in reg_pts.items()}
json.dump(cent, open(OUT_CEN,"w"), indent=1)

# overworld majors to LABEL (undergrounds/minor caves excluded -> separate maps / clutter)
LABELS=[("Limgrave","Limgrave"),("Weeping Peninsula","Weeping Peninsula"),("Stormhill","Stormhill"),
        ("Stormveil Castle","Stormveil"),("Liurnia of The Lakes","Liurnia"),("Caria Manor","Caria Manor"),
        ("Raya Lucaria Academy","Raya Lucaria"),("Caelid","Caelid"),("Dragonbarrow","Dragonbarrow"),
        ("Redmane Castle Post Radahn","Redmane Castle"),("Altus Plateau","Altus Plateau"),
        ("Mt. Gelmir","Mt. Gelmir"),("Volcano Manor","Volcano Manor"),("Leyndell, Royal Capital","Leyndell"),
        ("Capital Outskirts","Capital Outskirts"),("Forbidden Lands","Forbidden Lands"),
        ("Mountaintops of the Giants","Mountaintops"),("Consecrated Snowfield","Consecrated Snowfield"),
        ("Flame Peak","Flame Peak")]

# ---- geometry ------------------------------------------------------------------------
MARGIN=70; DRAWW=900; DRAWH=DRAWW*((z1-z0)/(x1-x0)); IMGW=DRAWW+2*MARGIN; IMGH=DRAWH+2*MARGIN
def world_to_px(gx,gz):
    return MARGIN+(gx-x0)/(x1-x0)*DRAWW, MARGIN+(1-(gz-z0)/(z1-z0))*DRAWH
P=[world_to_px(x,z) for x,z,t in pts]

def hull(points):
    ps=sorted(set(points))
    def cr(o,a,b): return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lo=[]
    for p in ps:
        while len(lo)>=2 and cr(lo[-2],lo[-1],p)<=0: lo.pop()
        lo.append(p)
    up=[]
    for p in reversed(ps):
        while len(up)>=2 and cr(up[-2],up[-1],p)<=0: up.pop()
        up.append(p)
    return lo[:-1]+up[:-1]
H=hull(P); hcx=sum(p[0] for p in H)/len(H); hcy=sum(p[1] for p in H)/len(H)
H=[(p[0]+(p[0]-hcx)*0.05,p[1]+(p[1]-hcy)*0.05) for p in H]
def densify(L,step=26):
    o=[]
    for i in range(len(L)):
        a=L[i]; b=L[(i+1)%len(L)]; d=math.hypot(b[0]-a[0],b[1]-a[1]); n=max(1,int(d/step))
        for k in range(n): o.append((a[0]+(b[0]-a[0])*k/n,a[1]+(b[1]-a[1])*k/n))
    return o
def chaikin(L,it=3):
    for _ in range(it):
        N=[]
        for i in range(len(L)):
            p=L[i]; q=L[(i+1)%len(L)]
            N.append((0.75*p[0]+0.25*q[0],0.75*p[1]+0.25*q[1]))
            N.append((0.25*p[0]+0.75*q[0],0.25*p[1]+0.75*q[1]))
        L=N
    return L
coast=chaikin(densify(H),3)
land_d="M %.1f %.1f "%coast[0]+" ".join("L %.1f %.1f"%coast[i%len(coast)] for i in range(1,len(coast)+1))+"Z"

# ---- overlays ------------------------------------------------------------------------
loc_dots="".join('<circle cx="%.1f" cy="%.1f" r="1.4"/>'%world_to_px(x,z) for x,z,t in pts if t=='item')
grace_dots="".join('<circle cx="%.1f" cy="%.1f" r="2.3"/>'%world_to_px(x,z) for x,z,t in pts if t=='grace')

# per-region label nudges (dx, dy, anchor) to dodge collisions / edges; default = above-centre
NUDGE={
  "Mountaintops of the Giants":(8,-13,"start"),
  "Consecrated Snowfield":(-8,-13,"end"),
  "Flame Peak":(0,20,"middle"),
  "Dragonbarrow":(10,4,"start"),
  "Caelid":(0,22,"middle"),
  "Redmane Castle Post Radahn":(8,4,"start"),
  "Caria Manor":(-6,-13,"end"),
  "Liurnia of The Lakes":(0,24,"middle"),
  "Mt. Gelmir":(-6,-13,"end"),
  "Volcano Manor":(-8,6,"end"),
  "Capital Outskirts":(10,-12,"start"),
  "Stormhill":(0,-14,"middle"),
  "Stormveil Castle":(-7,16,"end"),
}
FS=15
def est_w(s): return len(s)*FS*0.52
pins=""; labels=""
for reg,disp in LABELS:
    if reg not in cent: continue
    px,py=world_to_px(cent[reg]["gx"],cent[reg]["gz"])
    pins+=('<g transform="translate(%.1f,%.1f)">'
           '<circle r="6.5" fill="#7a3b2e" stroke="#3d2418" stroke-width="1.4"/>'
           '<circle r="2.3" fill="#efe2c4"/></g>'%(px,py))
    dx,dy,anchor=NUDGE.get(reg,(0,-13,"middle"))
    lx,ly=px+dx,py+dy
    # keep label box inside the frame
    w=est_w(disp); half={"middle":w/2,"start":0,"end":w}[anchor]
    lx=min(max(lx, 34+ (half if anchor=="start" else (w if anchor=="end" else w/2))),
           IMGW-34-((w if anchor=="start" else (0 if anchor=="end" else w/2))))
    labels+=('<text x="%.1f" y="%.1f" text-anchor="%s" font-size="%d" fill="#3d2418" '
             'paint-order="stroke" stroke="#efe2c4" stroke-width="3.4" stroke-linejoin="round" '
             'font-style="italic">%s</text>'%(lx,ly,anchor,FS,disp))

svg=f'''<svg viewBox="0 0 {IMGW:.0f} {IMGH:.0f}" xmlns="http://www.w3.org/2000/svg" font-family="Georgia, 'Times New Roman', serif">
<defs>
  <radialGradient id="parch" cx="50%" cy="42%" r="78%">
    <stop offset="0%" stop-color="#efe2c4"/><stop offset="60%" stop-color="#e7d6b2"/><stop offset="100%" stop-color="#d6bf8e"/></radialGradient>
  <radialGradient id="landg" cx="44%" cy="36%" r="85%">
    <stop offset="0%" stop-color="#d2bd8c"/><stop offset="70%" stop-color="#c0a468"/><stop offset="100%" stop-color="#ab8d54"/></radialGradient>
  <filter id="rough"><feTurbulence type="fractalNoise" baseFrequency="0.009" numOctaves="3" seed="11" result="n"/>
    <feDisplacementMap in="SourceGraphic" in2="n" scale="22"/></filter>
  <filter id="paper"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="4" result="n"/>
    <feColorMatrix in="n" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.045 0"/>
    <feComposite operator="over" in2="SourceGraphic"/></filter>
  <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="9"/></filter>
</defs>
<rect width="{IMGW:.0f}" height="{IMGH:.0f}" fill="url(#parch)"/>
<rect width="{IMGW:.0f}" height="{IMGH:.0f}" fill="#000" opacity="0.04" filter="url(#paper)"/>
<g filter="url(#rough)">
  <path d="{land_d}" fill="#000" opacity="0.18" filter="url(#shadow)" transform="translate(7,11)"/>
  <path d="{land_d}" fill="url(#landg)" stroke="#5d4a28" stroke-width="2.6" stroke-linejoin="round"/>
  <path d="{land_d}" fill="none" stroke="#efe2c4" stroke-width="1" opacity="0.4" transform="translate(0,2)"/>
</g>
<g fill="#6f5a33" opacity="0.22">{loc_dots}</g>
<g fill="#e3a000" stroke="#7a5b00" stroke-width="0.5" opacity="0.6">{grace_dots}</g>
<g>{pins}</g>
<g>{labels}</g>
<rect x="20" y="20" width="{IMGW-40:.0f}" height="{IMGH-40:.0f}" fill="none" stroke="#6f5a33" stroke-width="2.5"/>
<rect x="27" y="27" width="{IMGW-54:.0f}" height="{IMGH-54:.0f}" fill="none" stroke="#6f5a33" stroke-width="1"/>
<g transform="translate({IMGW-95:.0f},{IMGH-95:.0f})" stroke="#5d4a28" fill="#5d4a28">
  <circle r="34" fill="none" stroke-width="1.5"/>
  <path d="M0,-40 L7,-6 L0,0 L-7,-6 Z" fill="#7a3b2e" stroke="none"/>
  <path d="M0,40 L7,6 L0,0 L-7,6 Z" fill="#5d4a28" stroke="none"/>
  <path d="M40,0 L6,7 L0,0 L6,-7 Z" fill="#5d4a28" stroke="none"/>
  <path d="M-40,0 L-6,7 L0,0 L-6,-7 Z" fill="#5d4a28" stroke="none"/>
  <text x="0" y="-44" text-anchor="middle" font-size="15" stroke="none">N</text></g>
<g transform="translate({IMGW/2:.0f},58)" text-anchor="middle">
  <text y="0" font-size="30" fill="#4a3a1e" letter-spacing="3" font-style="italic">The Lands Between</text>
  <text y="22" font-size="12" fill="#6f5a33" letter-spacing="1.5">Archipelago Tracker Base &#183; region pins placed at real coordinate centroids</text>
</g>
</svg>'''
open(OUT_SVG,"w").write(svg)

cal={"note":"Authored in gx/gz space; transform is EXACT. +Z is North (up). M3a prototype.",
     "world_bounds":{"gx_min":x0,"gx_max":x1,"gz_min":z0,"gz_max":z1},
     "image":{"width":round(IMGW),"height":round(IMGH),"margin":MARGIN,"draw_w":DRAWW,"draw_h":round(DRAWH,2)},
     "transform_px":"px = margin + (gx-gx_min)/(gx_max-gx_min)*draw_w",
     "transform_py":"py = margin + (1 - (gz-gz_min)/(gz_max-gz_min))*draw_h",
     "filter":"base overworld only: tileX<55, sentinels dropped",
     "counts":{"base_points":len(pts),"graces":sum(1 for p in pts if p[2]=='grace'),
               "regions_with_coords":len(cent),"labeled":sum(1 for r,_ in LABELS if r in cent)}}
json.dump(cal, open(OUT_CAL,"w"), indent=2)
print(json.dumps({"img":[round(IMGW),round(IMGH)],"regions":len(cent),
                  "labeled":sum(1 for r,_ in LABELS if r in cent)}))
