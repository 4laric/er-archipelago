#!/usr/bin/env python3
"""Map-layer generator for the ER-AP PopTracker pack (M3a: overworld).

Imported by gen_poptracker.py (and runnable standalone). When a coordinate dump is present
(a Windows randomizer-gen artifact, see SPEC-poptracker-map.md) it (re)builds:

    poptracker/maps/lands_between_map.svg     original parchment map (source art)
    poptracker/images/maps/lands_between.png  rasterized map image PopTracker loads (needs cairosvg)
    poptracker/maps/maps.json                 PopTracker map def (Tracker:AddMaps)
    poptracker/maps/map_calibration.json      EXACT world(gx,gz)->image(px,py) transform
    poptracker/maps/region_centroids.json     per-region median gx/gz + check count
    poptracker/maps/region_pins.json          region -> {map,x,y} pixel pins (committed pin source)

It also RETURNS the pins dict to gen_poptracker, which attaches `map_locations` to the region
nodes in locations.json. Pins are sourced from the (committed) region_pins.json when no dump is
present, so locations.json stays reproducible on dump-less machines (no --check staleness trap).

Landmass is a STYLIZED hull drawn from coordinate facts => original art, no game assets. Authored
in gx/gz space, so the transform is exact and pins need no manual calibration. Filters to the base
overworld (tileX<55); DLC/underground maps await the map-id re-dump (SPEC-poptracker-map.md).
"""
from __future__ import annotations
import csv, json, math, os, re, statistics
from collections import defaultdict

TILE_MAX = 55
MAP_NAME = "lands_between"
PNG_REL = "images/maps/lands_between.png"   # what maps.json points at; pixels == SVG viewBox

# greenfield region name -> display label. Only the base-overworld regions (m60 fine grid) get a
# real centroid; DLC (m61) regions belong on dlc_map, interiors/legacy dungeons await interior maps.
LABELS = [("Limgrave","Limgrave"),("Weeping","Weeping Peninsula"),("Liurnia","Liurnia"),
          ("Caelid","Caelid"),("Altus","Altus Plateau"),("Mt. Gelmir","Mt. Gelmir"),
          ("Mountaintops of the Giants","Mountaintops")]
NUDGE = {"Mountaintops of the Giants":(-6,-13,"end"),"Mt. Gelmir":(0,-13,"middle"),
         "Caelid":(0,22,"middle"),"Liurnia":(0,-13,"middle"),"Weeping":(0,22,"middle")}


def load_coords(repo_root):
    """greenfield/item_grace_coords.tsv (map-LOCAL XYZ) -> rows with GLOBAL gx/gz + tileX, keyed by FLAG.
    Transform (validated: base-overworld gx span reproduces the old calibration's 5449 to the digit):
    overworld m60_XX_YY (fine grid XX 33..54) -> gx = XX*256 + localX, gz = YY*256 + localZ. m61 DLC
    tiles go to a private tile band (tileX+100) so the `tileX < TILE_MAX` filter keeps them off the
    Lands Between map (they feed dlc_map). Interiors / underground / m60 mip tiles get a sentinel gx so
    the overworld filter drops them (they await their own interior maps)."""
    p = os.path.join(repo_root, "greenfield", "item_grace_coords.tsv")
    out = []
    if not os.path.isfile(p):
        return out
    for r in csv.reader(open(p, encoding="utf-8"), delimiter="\t"):
        if len(r) < 6 or r[0] not in ("item", "grace"):
            continue
        try:
            lx, lz = float(r[3]), float(r[5])
        except ValueError:
            continue
        m = re.match(r"m6([01])_(\d\d)_(\d\d)", r[2])
        if m and m.group(1) == "0" and 33 <= int(m.group(2)) <= 54:      # base overworld fine grid
            XX, YY = int(m.group(2)), int(m.group(3))
            gx, gz, tileX = XX * 256 + lx, YY * 256 + lz, XX
        elif m and m.group(1) == "1":                                    # DLC overworld -> private band
            XX, YY = int(m.group(2)), int(m.group(3))
            gx, gz, tileX = XX * 256 + lx, YY * 256 + lz, XX + 100
        else:                                                            # interior/underground/mip -> sentinel
            gx, gz, tileX = 1e9, 1e9, 999
        out.append({"type": r[0], "key": r[1], "tileX": tileX, "gx": gx, "gy": r[4], "gz": gz, "mapName": r[2]})
    return out


def key_to_region(apworld_dir):
    """flag(str) -> greenfield region, from eldenring/data.py LOCATIONS (region -> [(name, apid, flag)])."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("_gf_data", os.path.join(apworld_dir, "data.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    kr = {}
    for region, locs in mod.LOCATIONS.items():
        for (_nm, _aid, _flag) in locs:
            kr[str(_flag)] = region
    return kr


def _committed_pins(pack_root):
    """Load region -> {map,x,y} from a previously committed maps/region_pins.json (or {})."""
    p = os.path.join(pack_root, "maps", "region_pins.json")
    if not os.path.exists(p):
        return {}
    doc = json.load(open(p, encoding="utf-8"))
    return {r: {"map": v["map"], "x": v["x"], "y": v["y"]} for r, v in doc.get("pins", {}).items()}


def _hull(points):
    ps = sorted(set(points))
    if len(ps) < 3:
        return ps
    def cr(o, a, b): return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lo = []
    for p in ps:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    up = []
    for p in reversed(ps):
        while len(up) >= 2 and cr(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def _densify(L, step=26):
    o = []
    for i in range(len(L)):
        a, b = L[i], L[(i+1) % len(L)]
        d = math.hypot(b[0]-a[0], b[1]-a[1]); n = max(1, int(d/step))
        for k in range(n):
            o.append((a[0]+(b[0]-a[0])*k/n, a[1]+(b[1]-a[1])*k/n))
    return o


def _chaikin(L, it=3):
    for _ in range(it):
        N = []
        for i in range(len(L)):
            p, q = L[i], L[(i+1) % len(L)]
            N.append((0.75*p[0]+0.25*q[0], 0.75*p[1]+0.25*q[1]))
            N.append((0.25*p[0]+0.75*q[0], 0.25*p[1]+0.75*q[1]))
        L = N
    return L


def _rasterize(svg, pack_root):
    """Best-effort SVG->PNG at native viewBox px (so map_locations pixels align). Needs cairosvg."""
    try:
        import cairosvg
    except Exception:
        return "png skipped (cairosvg not installed; ship images/maps/lands_between.png manually)"
    png = os.path.join(pack_root, PNG_REL)
    os.makedirs(os.path.dirname(png), exist_ok=True)
    # output_width = viewBox width so 1px == 1 map-unit == the x/y we store in region_pins
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=png, output_width=1040)
    return "png ok"


def build(apworld_dir, pack_root, repo_root):
    """Returns (json_targets, text_targets, stats, pins, map_def). pins = {region: {map,x,y}}.
    map_def is this map's PopTracker entry; gen_poptracker.py folds it (plus the DLC map's) into a
    single maps/maps.json. When no dump: emits no map file targets but still returns committed pins
    for locations.json (and the map_def, so the base map variant always loads)."""
    base_map_def = {"name": MAP_NAME, "img": PNG_REL, "location_size": 20,
                    "location_border_thickness": 2, "location_shape": "diamond"}
    rows = load_coords(repo_root)
    if not rows:
        pins = _committed_pins(pack_root)
        return [], [], {"map": "skipped (no item_grace_coords.tsv); committed pins=%d" % len(pins)}, pins, base_map_def

    def ok(r):
        return r["gx"] < 1e8 and r["gz"] < 1e8 and r["tileX"] < TILE_MAX
    pts = [(r["gx"], r["gz"], r["type"]) for r in rows if ok(r)]
    if len(pts) < 50:
        return ([], [], {"map": f"skipped (only {len(pts)} usable points)"},
                _committed_pins(pack_root), base_map_def)
    xs = [p[0] for p in pts]; zs = [p[1] for p in pts]
    x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)

    kr = key_to_region(apworld_dir)
    reg_pts = defaultdict(list)
    for r in rows:
        if r["type"] != "item" or not ok(r):
            continue
        reg = kr.get(r["key"])
        if reg:
            reg_pts[reg].append((float(r["gx"]), float(r["gz"])))
    cent = {reg: {"gx": round(statistics.median(p[0] for p in ps), 1),
                  "gz": round(statistics.median(p[1] for p in ps), 1), "n": len(ps)}
            for reg, ps in reg_pts.items()}

    MARGIN, DRAWW = 70, 900
    DRAWH = DRAWW * ((z1-z0)/(x1-x0)); IMGW = DRAWW+2*MARGIN; IMGH = DRAWH+2*MARGIN
    def w2px(gx, gz):
        return MARGIN+(gx-x0)/(x1-x0)*DRAWW, MARGIN+(1-(gz-z0)/(z1-z0))*DRAWH

    H = _hull([w2px(x, z) for x, z, _ in pts])
    hcx = sum(p[0] for p in H)/len(H); hcy = sum(p[1] for p in H)/len(H)
    H = [(p[0]+(p[0]-hcx)*0.05, p[1]+(p[1]-hcy)*0.05) for p in H]
    coast = _chaikin(_densify(H), 3)
    land_d = "M %.1f %.1f " % coast[0] + " ".join(
        "L %.1f %.1f" % coast[i % len(coast)] for i in range(1, len(coast)+1)) + "Z"

    loc_dots = "".join('<circle cx="%.1f" cy="%.1f" r="1.4"/>' % w2px(x, z) for x, z, t in pts if t == "item")
    grace_dots = "".join('<circle cx="%.1f" cy="%.1f" r="2.3"/>' % w2px(x, z) for x, z, t in pts if t == "grace")

    FS = 15
    def est_w(s): return len(s)*FS*0.52
    pins_svg, labels_svg = "", ""
    pins_doc_pins = {}        # full record for region_pins.json (with n)
    pins_for_locs = {}        # slim {region: {map,x,y}} returned to gen_poptracker
    for reg, c in cent.items():
        px, py = w2px(c["gx"], c["gz"])
        pins_doc_pins[reg] = {"map": MAP_NAME, "x": round(px), "y": round(py), "n": c["n"]}
        pins_for_locs[reg] = {"map": MAP_NAME, "x": round(px), "y": round(py)}
    for reg, disp in LABELS:
        if reg not in cent:
            continue
        px, py = w2px(cent[reg]["gx"], cent[reg]["gz"])
        pins_svg += ('<g transform="translate(%.1f,%.1f)"><circle r="6.5" fill="#7a3b2e" '
                     'stroke="#3d2418" stroke-width="1.4"/><circle r="2.3" fill="#efe2c4"/></g>' % (px, py))
        dx, dy, anchor = NUDGE.get(reg, (0, -13, "middle"))
        lx, ly = px+dx, py+dy
        w = est_w(disp)
        lx = min(max(lx, 34+(0 if anchor == "start" else (w if anchor == "end" else w/2))),
                 IMGW-34-((w if anchor == "start" else (0 if anchor == "end" else w/2))))
        labels_svg += ('<text x="%.1f" y="%.1f" text-anchor="%s" font-size="%d" fill="#3d2418" '
                       'paint-order="stroke" stroke="#efe2c4" stroke-width="3.4" stroke-linejoin="round" '
                       'font-style="italic">%s</text>' % (lx, ly, anchor, FS, disp))

    svg = f'''<svg viewBox="0 0 {IMGW:.0f} {IMGH:.0f}" xmlns="http://www.w3.org/2000/svg" font-family="Georgia, 'Times New Roman', serif">
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
<g>{pins_svg}</g>
<g>{labels_svg}</g>
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

    cal = {"note": "GENERATED by tools/build_map.py. Authored in gx/gz space; transform is EXACT. +Z is North (up).",
           "map_name": MAP_NAME, "source": "greenfield/item_grace_coords.tsv",
           "world_bounds": {"gx_min": x0, "gx_max": x1, "gz_min": z0, "gz_max": z1},
           "image": {"width": round(IMGW), "height": round(IMGH), "margin": MARGIN,
                     "draw_w": DRAWW, "draw_h": round(DRAWH, 2)},
           "transform_px": "px = margin + (gx-gx_min)/(gx_max-gx_min)*draw_w",
           "transform_py": "py = margin + (1 - (gz-gz_min)/(gz_max-gz_min))*draw_h",
           "filter": f"base overworld only: tileX<{TILE_MAX}, sentinels dropped"}
    pins_doc = {"_note": "GENERATED by tools/build_map.py. region -> map pixel pin (M3a overworld).",
                "map": MAP_NAME, "pins": pins_doc_pins}

    raster = _rasterize(svg, pack_root)

    maps = lambda *p: os.path.join(pack_root, "maps", *p)
    # NB: maps.json is written by gen_poptracker (it merges this map_def with the DLC map's).
    json_targets = [(maps("map_calibration.json"), cal),
                    (maps("region_centroids.json"), cent),
                    (maps("region_pins.json"), pins_doc)]
    text_targets = [(maps("lands_between_map.svg"), svg)]
    stats = {"map": MAP_NAME, "map_points": len(pts),
             "map_graces": sum(1 for p in pts if p[2] == "grace"),
             "map_regions_pinned": len(pins_for_locs),
             "map_labeled": sum(1 for r, _ in LABELS if r in cent), "map_raster": raster}
    return json_targets, text_targets, stats, pins_for_locs, base_map_def


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    pack = os.path.dirname(here); repo = os.path.dirname(pack)
    jt, tt, st, pins, mdef = build(os.path.join(repo, "greenfield", "eldenring"), pack, repo)
    for path, data in jt:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write(json.dumps(data, indent=2, ensure_ascii=False)+"\n")
    for path, text in tt:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write(text)
    # NB: standalone runs deliberately do NOT write maps/maps.json -- that file merges the base and
    # DLC map_defs and is owned by gen_poptracker.py. mdef is returned for that merge.
    _ = mdef
    print("map | " + json.dumps(st) + " | pins=%d" % len(pins))
