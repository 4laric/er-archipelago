#!/usr/bin/env python3
"""Map-layer generator for the DLC overworld (M3c: Land of Shadow).

Sibling of build_map.py. Same stylized-hull engine, but it selects the DLC overworld points
instead of the base Lands Between and emits a second PopTracker map named "land_of_shadow".
gen_poptracker.py calls build_dlc() right after build_map.build() and merges the two pin dicts
(disjoint by region: base regions pin on lands_between, DLC regions on land_of_shadow) and the two
map defs into a single maps/maps.json.

DLC point selection (SPEC-poptracker-map.md) -- in priority order:
  1. If the dump carries a map-id column ("mapName"/"map"/"mapId"), keep rows whose id starts with
     the DLC overworld prefix (m61). This is the clean, complete filter the re-dump enables.
  2. Otherwise, the AUTHORITATIVE fallback is the key->region join: an item row is DLC iff its key
     belongs to a DLC region (per locations.py). This is correct (no reliance on tile heuristics);
     it is just limited to item rows, since graces carry no region key.

Today's dumps have essentially no captured DLC overworld coordinates (the join yields < MIN_POINTS),
so build_dlc emits a parchment PLACEHOLDER image and committed pins -- the dlc_only variant still
loads. After a DLC re-dump (ideally with a mapName column) re-running gen_poptracker.py draws the
real map and pins automatically.

Rasterization: build_map relies on cairosvg (a manual Windows step). Here the PNG is rendered
directly with PIL from the same pixel-space geometry, so the map is loadable with no extra tooling
and the pins align with the image. The .svg is still emitted as source art (re-raster with
resvg.exe on Windows for a higher-fidelity image if desired).
"""
from __future__ import annotations
import csv, json, os, statistics
from collections import defaultdict

import build_map  # shared helpers: find_dump, key_to_region, _hull, _densify, _chaikin

DLC_MAP_PREFIX = "m61"  # Land of Shadow overworld map id (used when the dump has a map-id column)
MIN_POINTS = 20         # below this the cloud is too sparse for a real hull -> placeholder canvas
MAP_NAME = "land_of_shadow"
PNG_REL = "images/maps/land_of_shadow.png"

# region -> short display label for the headline regions (others get an unlabeled pin)
LABELS = [
    ("Gravesite Plain", "Gravesite Plain"), ("Belurat", "Belurat"),
    ("Castle Ensis", "Castle Ensis"), ("Charo's Hidden Grave", "Charo's Grave"),
    ("Scadu Altus", "Scadu Altus"), ("Shadow Keep", "Shadow Keep"),
    ("Scaduview", "Scaduview"), ("Enir Ilim", "Enir Ilim"),
    ("Cerulean Coast", "Cerulean Coast"), ("Stone Coffin Fissure", "Stone Coffin Fissure"),
    ("Jagged Peak", "Jagged Peak"), ("Rauh Base", "Rauh Base"),
    ("Ancient Ruins of Rauh", "Ancient Ruins of Rauh"), ("Abyssal Woods", "Abyssal Woods"),
    ("Hinterland", "Hinterland"), ("Recluses' River", "Recluses' River"),
    ("Finger Ruins of Rhia", "Finger Ruins of Rhia"),
    ("Finger Ruins of Dheo", "Finger Ruins of Dheo"),
    ("Finger Ruins of Miyr", "Finger Ruins of Miyr"),
]

_MAPID_COLS = ("mapName", "mapname", "map", "mapId", "mapid", "MapName")


def _mapid_col(rows):
    if not rows:
        return None
    for c in _MAPID_COLS:
        if c in rows[0]:
            return c
    return None


def _finite(r):
    try:
        return abs(float(r["gx"])) < 1e8 and abs(float(r["gz"])) < 1e8
    except (KeyError, ValueError):
        return False


def _committed_pins(pack_root):
    p = os.path.join(pack_root, "maps", "region_pins_dlc.json")
    if not os.path.exists(p):
        return {}
    doc = json.load(open(p, encoding="utf-8"))
    return {r: {"map": v["map"], "x": v["x"], "y": v["y"]} for r, v in doc.get("pins", {}).items()}


def _dlc_regions_from_locations(apworld_dir):
    import ast
    tree = ast.parse(open(os.path.join(apworld_dir, "locations.py"), encoding="utf-8").read())
    for n in tree.body:
        if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "region_order_dlc"
                                             for t in n.targets):
            return {e.value for e in n.value.elts if hasattr(e, "value")}
    return set()


def _font(size):
    from PIL import ImageFont
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:  # noqa: BLE001
                pass
    return ImageFont.load_default()


def _render_png(pack_root, imgw, imgh, coast_px, loc_px, grace_px, pins, labels_px, title, subtitle):
    """Render the map PNG directly with PIL (no cairosvg needed); pixels match the stored pins."""
    from PIL import Image, ImageDraw
    png = os.path.join(pack_root, PNG_REL)
    os.makedirs(os.path.dirname(png), exist_ok=True)
    img = Image.new("RGB", (int(imgw), int(imgh)), (231, 214, 178))
    d = ImageDraw.Draw(img, "RGBA")
    if len(coast_px) >= 3:
        shadow = [(x + 7, y + 11) for x, y in coast_px]
        d.polygon(shadow, fill=(0, 0, 0, 40))
        d.polygon(coast_px, fill=(192, 164, 104), outline=(93, 74, 40))
    for x, y in loc_px:
        d.ellipse((x - 1.4, y - 1.4, x + 1.4, y + 1.4), fill=(111, 90, 51, 70))
    for x, y in grace_px:
        d.ellipse((x - 2.3, y - 2.3, x + 2.3, y + 2.3), fill=(227, 160, 0, 150))
    for x, y in pins:
        d.polygon([(x, y - 6), (x + 6, y), (x, y + 6), (x - 6, y)],
                  fill=(122, 59, 46), outline=(61, 36, 24))
        d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(239, 226, 196))
    flabel = _font(15)
    for x, y, text in labels_px:
        d.text((x, y), text, font=flabel, fill=(61, 36, 24),
               stroke_width=3, stroke_fill=(239, 226, 196), anchor="ms")
    d.rectangle((20, 20, imgw - 20, imgh - 20), outline=(111, 90, 51), width=3)
    d.rectangle((27, 27, imgw - 27, imgh - 27), outline=(111, 90, 51), width=1)
    d.text((imgw / 2, 40), title, font=_font(30), fill=(74, 58, 30),
           stroke_width=2, stroke_fill=(231, 214, 178), anchor="ms")
    d.text((imgw / 2, 60), subtitle, font=_font(12), fill=(111, 90, 51), anchor="ms")
    img.save(png)
    return "png ok (PIL)"


def _placeholder(pack_root, n_pts, mapcol, why):
    _render_png(pack_root, 1040, 1040, [], [], [], [], [], "The Land of Shadow", why)
    return {"dlc_map": f"placeholder ({n_pts} usable DLC points; need >= {MIN_POINTS})",
            "dlc_map_filter": f"mapcol={mapcol or 'key-join'}"}


def build_dlc(apworld_dir, pack_root, repo_root, dlc_regions=None):
    """Returns (json_targets, text_targets, stats, pins, map_def).

    map_def is the PopTracker map entry gen_poptracker folds into the combined maps.json. Always
    returns a map_def + a PNG (placeholder when DLC coords are too sparse) so the dlc_only variant
    can load; it auto-upgrades when a fuller dump is present."""
    map_def = {"name": MAP_NAME, "img": PNG_REL, "location_size": 20,
               "location_border_thickness": 2, "location_shape": "diamond"}
    if dlc_regions is None:
        dlc_regions = _dlc_regions_from_locations(apworld_dir)
    dump = build_map.find_dump(repo_root)
    rows = list(csv.DictReader(open(dump), delimiter="\t")) if dump else []
    mapcol = _mapid_col(rows)
    kr = build_map.key_to_region(apworld_dir)

    def is_dlc_pt(r):
        if not _finite(r):
            return False
        if mapcol:
            mid = str(r.get(mapcol, "")).strip().lower()
            if mid:
                return mid.startswith(DLC_MAP_PREFIX)
        # authoritative fallback: key joins to a DLC region (item rows only -- graces lack keys)
        return r["type"] == "item" and kr.get(r["key"]) in dlc_regions

    pts = [(float(r["gx"]), float(r["gz"]), r["type"]) for r in rows if is_dlc_pt(r)]

    if len(pts) < MIN_POINTS:
        stats = _placeholder(pack_root, len(pts), mapcol,
                             "awaiting a DLC coordinate dump - run gen_poptracker.py after re-dumping")
        return [], [], stats, _committed_pins(pack_root), map_def

    xs = [p[0] for p in pts]; zs = [p[1] for p in pts]
    x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
    span_x = max(x1 - x0, 1.0); span_z = max(z1 - z0, 1.0)

    reg_pts = defaultdict(list)
    for r in rows:
        if r["type"] != "item" or not is_dlc_pt(r):
            continue
        reg = kr.get(r["key"])
        if reg in dlc_regions:
            reg_pts[reg].append((float(r["gx"]), float(r["gz"])))
    cent = {reg: {"gx": round(statistics.median(p[0] for p in ps), 1),
                  "gz": round(statistics.median(p[1] for p in ps), 1), "n": len(ps)}
            for reg, ps in reg_pts.items()}

    MARGIN, DRAWW = 70, 900
    DRAWH = DRAWW * (span_z / span_x); IMGW = DRAWW + 2 * MARGIN; IMGH = DRAWH + 2 * MARGIN

    def w2px(gx, gz):
        return (MARGIN + (gx - x0) / span_x * DRAWW,
                MARGIN + (1 - (gz - z0) / span_z) * DRAWH)

    H = build_map._hull([w2px(x, z) for x, z, _ in pts])
    if len(H) >= 3:
        hcx = sum(p[0] for p in H) / len(H); hcy = sum(p[1] for p in H) / len(H)
        H = [(p[0] + (p[0] - hcx) * 0.05, p[1] + (p[1] - hcy) * 0.05) for p in H]
        coast = build_map._chaikin(build_map._densify(H), 3)
    else:
        coast = H
    coast_px = [(round(x, 1), round(y, 1)) for x, y in coast]

    loc_px = [w2px(x, z) for x, z, t in pts if t == "item"]
    grace_px = [w2px(x, z) for x, z, t in pts if t == "grace"]

    pins_doc_pins, pins_for_locs, pins_px, labels_px = {}, {}, [], []
    for reg, c in cent.items():
        px, py = w2px(c["gx"], c["gz"])
        pins_doc_pins[reg] = {"map": MAP_NAME, "x": round(px), "y": round(py), "n": c["n"]}
        pins_for_locs[reg] = {"map": MAP_NAME, "x": round(px), "y": round(py)}
        pins_px.append((px, py))
    for reg, disp in LABELS:
        if reg in cent:
            px, py = w2px(cent[reg]["gx"], cent[reg]["gz"])
            labels_px.append((px, py - 11, disp))

    def _poly_d(poly):
        if not poly:
            return ""
        return "M %.1f %.1f " % poly[0] + " ".join(
            "L %.1f %.1f" % poly[i % len(poly)] for i in range(1, len(poly) + 1)) + "Z"
    land_d = _poly_d(coast_px)
    loc_dots = "".join('<circle cx="%.1f" cy="%.1f" r="1.4"/>' % p for p in loc_px)
    grace_dots = "".join('<circle cx="%.1f" cy="%.1f" r="2.3"/>' % p for p in grace_px)
    pins_svg = "".join(
        '<g transform="translate(%.1f,%.1f)"><circle r="6.5" fill="#7a3b2e" stroke="#3d2418" '
        'stroke-width="1.4"/><circle r="2.3" fill="#efe2c4"/></g>' % p for p in pins_px)
    labels_svg = "".join(
        '<text x="%.1f" y="%.1f" text-anchor="middle" font-size="15" fill="#3d2418" '
        'paint-order="stroke" stroke="#efe2c4" stroke-width="3.4" stroke-linejoin="round" '
        'font-style="italic">%s</text>' % (x, y, t) for x, y, t in labels_px)
    svg = f'''<svg viewBox="0 0 {IMGW:.0f} {IMGH:.0f}" xmlns="http://www.w3.org/2000/svg" font-family="Georgia, 'Times New Roman', serif">
<defs>
  <radialGradient id="parch" cx="50%" cy="42%" r="78%">
    <stop offset="0%" stop-color="#efe2c4"/><stop offset="60%" stop-color="#e7d6b2"/><stop offset="100%" stop-color="#d6bf8e"/></radialGradient>
  <radialGradient id="landg" cx="44%" cy="36%" r="85%">
    <stop offset="0%" stop-color="#cdb487"/><stop offset="70%" stop-color="#b59a64"/><stop offset="100%" stop-color="#9c8050"/></radialGradient>
</defs>
<rect width="{IMGW:.0f}" height="{IMGH:.0f}" fill="url(#parch)"/>
<path d="{land_d}" fill="url(#landg)" stroke="#5d4a28" stroke-width="2.6" stroke-linejoin="round"/>
<g fill="#6f5a33" opacity="0.22">{loc_dots}</g>
<g fill="#e3a000" stroke="#7a5b00" stroke-width="0.5" opacity="0.6">{grace_dots}</g>
<g>{pins_svg}</g>
<g>{labels_svg}</g>
<rect x="20" y="20" width="{IMGW-40:.0f}" height="{IMGH-40:.0f}" fill="none" stroke="#6f5a33" stroke-width="2.5"/>
<g transform="translate({IMGW/2:.0f},48)" text-anchor="middle">
  <text y="0" font-size="30" fill="#4a3a1e" letter-spacing="3" font-style="italic">The Land of Shadow</text>
  <text y="20" font-size="12" fill="#6f5a33" letter-spacing="1.5">Archipelago Tracker DLC &#183; region pins at real coordinate centroids</text>
</g>
</svg>'''

    raster = _render_png(pack_root, IMGW, IMGH, coast_px, loc_px, grace_px, pins_px, labels_px,
                         "The Land of Shadow",
                         "Archipelago Tracker DLC - region pins at real coordinate centroids")

    cal = {"note": "GENERATED by tools/dlc_map.py. Authored in gx/gz space; transform is EXACT. +Z is North (up).",
           "map_name": MAP_NAME, "source_dump": os.path.basename(dump),
           "world_bounds": {"gx_min": x0, "gx_max": x1, "gz_min": z0, "gz_max": z1},
           "image": {"width": round(IMGW), "height": round(IMGH), "margin": MARGIN,
                     "draw_w": DRAWW, "draw_h": round(DRAWH, 2)},
           "transform_px": "px = margin + (gx-gx_min)/(gx_max-gx_min)*draw_w",
           "transform_py": "py = margin + (1 - (gz-gz_min)/(gz_max-gz_min))*draw_h",
           "filter": (f"DLC overworld via map-id col '{mapcol}' prefix '{DLC_MAP_PREFIX}'"
                      if mapcol else "DLC overworld via key->region join (items only)")}
    pins_doc = {"_note": "GENERATED by tools/dlc_map.py. region -> map pixel pin (M3c DLC overworld).",
                "map": MAP_NAME, "pins": pins_doc_pins}

    maps = lambda *p: os.path.join(pack_root, "maps", *p)
    json_targets = [(maps("map_calibration_dlc.json"), cal),
                    (maps("region_centroids_dlc.json"), cent),
                    (maps("region_pins_dlc.json"), pins_doc)]
    text_targets = [(maps("land_of_shadow_map.svg"), svg)]
    stats = {"dlc_map": MAP_NAME, "dlc_map_points": len(pts),
             "dlc_map_graces": sum(1 for p in pts if p[2] == "grace"),
             "dlc_map_regions_pinned": len(pins_for_locs),
             "dlc_map_labeled": sum(1 for r, _ in LABELS if r in cent),
             "dlc_map_filter": f"mapcol={mapcol or 'key-join'}", "dlc_map_raster": raster}
    return json_targets, text_targets, stats, pins_for_locs, map_def


if __name__ == "__main__":
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    pack = os.path.dirname(here); repo = os.path.dirname(pack)
    apw = os.path.join(repo, "Archipelago", "worlds", "eldenring")
    jt, tt, st, pins, mdef = build_dlc(apw, pack, repo)
    for path, data in jt:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    for path, text in tt:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write(text)
    print("dlc_map | " + json.dumps(st) + " | pins=%d" % len(pins))
