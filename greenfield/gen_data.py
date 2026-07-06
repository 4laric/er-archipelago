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
# Map-fragment pickups are granted via the RE'd map-reveal FLAG path (the client's reveal_all_maps
# sets these exact flags), so they must NOT also be AP checks -- otherwise revealing the map trips
# all of them at once (start-of-run map-piece flood). Exclude any location whose acquisition flag is
# a map-reveal flag. Mirrors startgrants.rs MAP_REVEAL_FLAGS_BASE + MAP_REVEAL_FLAGS_DLC.
MAP_REVEAL_FLAGS=frozenset({62010,62011,62012,62020,62021,62022,62030,62031,62032,62040,62041,
                            62050,62051,62052,62060,62061,62062,62063,62064,
                            62080,62081,62082,62083,62084})
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
 'Mohgwyn / Consecrated-adjacent':'Mohgwyn Palace','Mohgwyn Palace':'Mohgwyn Palace','Leyndell / Roundtable / Shunning-Grounds':'Leyndell',
 'DLC Interior':'Shadow Keep','Caves':'Limgrave',"Roundtable Hold":'Roundtable Hold','Stormveil Castle':'Stormveil Castle',
 'Stormveil (assoc.)':'Stormveil Castle',"Miquella's Haligtree & Elphael":"Miquella's Haligtree",
 "Hero's Graves (Catacombs)":'Limgrave','Crumbling Farum Azula':'Farum Azula','Divine Tower':'Liurnia of the Lakes',
 'Raya Lucaria Academy':'Raya Lucaria Academy','Volcano Manor / Mt. Gelmir':'Mt. Gelmir','Volcano Manor (Rykard)':'Mt. Gelmir','Volcano Manor':'Mt. Gelmir',
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

# ---- important_locations tags (matt-free): classify each check by TYPE from item_name + method,
# NOT names. Used by features/important_locations.py to force those checks to hold non-filler items.
# Remembrance/Seedtree/Church/Basin exclude shop rows (buying a duplicate is not the meaningful check).
def _loc_tags(r):
    nm = (r['item_name'] or '').lower(); meth = r['method']; shop = meth.startswith('shop')
    t = []
    if meth == 'boss_arena': t.append('Boss')
    if 'remembrance' in nm and not shop: t.append('Remembrance')
    if 'golden seed' in nm and not shop: t.append('Seedtree')
    if 'sacred tear' in nm and not shop: t.append('Church')
    if 'scadutree fragment' in nm: t.append('Fragment')
    if 'revered spirit ash' in nm: t.append('Revered')
    if 'crystal tear' in nm and not shop: t.append('Basin')
    if shop: t.append('Shop')
    return t

rows=[r for r in csv.DictReader(open(os.path.join(HERE,"region_map.csv")))
      if r['method'] not in SKIP and int(r['flag']) not in MAP_REVEAL_FLAGS]
buckets=OrderedDict()
loc_tags={}
apid=BASE_AP; names=set()
for r in rows:
    reg=region_of(r); flag=int(r['flag']); item=r['item_name'] or 'check'
    nm=f"{reg} :: {item} [f{flag}]"
    if nm in names: nm=f"{nm}#{apid}"
    names.add(nm)
    _t=_loc_tags(r)
    if _t: loc_tags[apid]=_t
    buckets.setdefault(reg,[]).append((nm,apid,flag)); apid+=1

spokes=sorted(k for k in buckets if k!=HUB)
with open(OUT,"w",encoding="utf-8") as f:
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

# ---- location_tags.py: {ap_id: [type,...]} + TAG_COUNTS (important_locations source, matt-free) ----
OUT_TAGS = os.path.join(HERE, "eldenring_gf", "location_tags.py")
import collections as _c
_tagcount = _c.Counter(tg for tags in loc_tags.values() for tg in tags)
with open(OUT_TAGS, "w", newline="\n", encoding="utf-8") as f:
    f.write('"""AUTO-GENERATED (gen_data.py). Location TYPE tags for important_locations, derived\n')
    f.write('matt-free from item_name + method (see _loc_tags). LOCATION_TAGS = {ap_id: [type,...]}."""\n')
    f.write('LOCATION_TAGS = {\n')
    for _aid in sorted(loc_tags):
        f.write(f'    {_aid}: {loc_tags[_aid]!r},\n')
    f.write('}\n\nTAG_COUNTS = ' + repr(dict(sorted(_tagcount.items()))) + '\n')
print(f'location_tags: {len(loc_tags)} tagged locations; counts ' + repr(dict(sorted(_tagcount.items()))))

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
_open_cand_ow = defaultdict(list)   # overworld-only (m60/m61) graces: visible + warpable front doors
for _fl, _tile in gf.items():          # gf = {warpUnlockFlag(str): mapTile}, built at top
    _mj = None
    _m = re.match(r"m60_(\d\d)_(\d\d)", _tile)
    if _m: _mj = PLAY2AP.get(tile_pr(int(_m.group(1)), int(_m.group(2))))
    if not _mj: _mj = _pref2maj.get(_map_pref(_tile))
    if _mj and _mj != HUB:
        _open_cand[_mj].append(int(_fl))
        if _tile[:3] in ("m60", "m61"): _open_cand_ow[_mj].append(int(_fl))
# Front-door grace = an ACCESSIBLE OVERWORLD grace (m60/m61), NOT the numerically-lowest flag, which
# is often a catacomb/cave INTERIOR grace the player can never see (e.g. Limgrave min was 73000 =
# m30_00_00 catacomb -> "no graces in-game"). Serves as the region-open flag AND the start/front-door
# grace. Fall back to any grace only for a pure-dungeon bucket with no overworld grace at all.
def _front_door(r):
    return min(_open_cand_ow[r]) if _open_cand_ow.get(r) else min(_open_cand[r])
REGION_OPEN_FLAGS = {r: _front_door(r) for r in spokes if _open_cand.get(r)}
# DLC sub-areas whose locations are all boss-arena/PENDING never resolve to a grace above (their
# m61 tiles collapse into Land of Shadow's coarse bucket). Hand-verified front-door warp graces
# from grace_flags.tsv (grace_name-labeled) give them their own open flag:
#   Abyssal Woods -> 76860 'Abyssal Woods' (m61_50_42); Jagged Peak -> 76850 'Foot of the Jagged
#   Peak' (m61_52_40); Scadu Altus -> 76900 'Highroad Cross' (m61_48_45).
_DLC_OPEN_FALLBACK = {'Abyssal Woods': 76860, 'Jagged Peak': 76850, 'Scadu Altus': 76900}
for _dr, _df in _DLC_OPEN_FALLBACK.items():
    if _dr in spokes and _dr not in REGION_OPEN_FLAGS:
        REGION_OPEN_FLAGS[_dr] = _df
REGION_OPEN_PENDING = [r for r in spokes if r not in REGION_OPEN_FLAGS]
OUT_OPEN = os.path.join(HERE, "eldenring_gf", "region_open_flags.py")
with open(OUT_OPEN, "w", encoding="utf-8") as _f:
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


# ---- Phase 3 region bosses: the 25 major bosses (method=boss_arena), joined to greenfield ap-ids
# by FLAG (matt-free). Members-per-dungeon sweeps need a boss-kill-flag enrichment the backbone
# lacks (SPEC-PARITY.md P3), so only the labeled region bosses are emitted here.
_flag2apid = {int(r["flag"]): BASE_AP + i for i, r in enumerate(rows)}
_region_bosses = defaultdict(list)
for r in rows:
    if r["method"] == "boss_arena":
        reg = region_of(r); fl = int(r["flag"])
        _region_bosses[reg].append((_flag2apid[fl], fl, r["item_name"] or "boss"))
OUT_BOSS = os.path.join(HERE, "eldenring_gf", "boss_data.py")
with open(OUT_BOSS, "w", newline="\n", encoding="utf-8") as f:
    f.write('"""AUTO-GENERATED (gen_data.py). Region bosses (method=boss_arena) -> greenfield ap-ids,\n')
    f.write('joined by event flag. Matt-free. Dungeon-sweep triggers need EMEVD enrichment (SPEC P3)."""\n')
    f.write("REGION_BOSSES = {\n")
    for reg in sorted(_region_bosses):
        f.write(f"    {reg!r}: [\n")
        for aid, fl, nm in _region_bosses[reg]:
            f.write(f"        ({aid}, {fl}, {nm!r}),\n")
        f.write("    ],\n")
    f.write("}\n")
print(f"boss_data: {sum(len(v) for v in _region_bosses.values())} region bosses across {len(_region_bosses)} regions -> {sorted(_region_bosses)}")


# ---- Phase 6 grace rando: ALL warp graces per major region (matt-free; reuses _open_cand from the
# region-open-flags block above -- same grace_flags.tsv source). Bundle mode lights these on lock
# receipt; freebie+scatter is a v2 enhancement.
def _graces_frontdoor_first(r):
    _fs = sorted(_open_cand[r]); _fd = _front_door(r)
    return [_fd] + [f for f in _fs if f != _fd]
REGION_GRACE_POINTS = {r: _graces_frontdoor_first(r) for r in spokes if _open_cand.get(r)}
OUT_GRACES = os.path.join(HERE, "eldenring_gf", "region_graces.py")
with open(OUT_GRACES, "w", newline="\n", encoding="utf-8") as f:
    f.write('"""AUTO-GENERATED (gen_data.py). All warp graces per major region (grace_flags.tsv). Matt-free."""\n')
    f.write("REGION_GRACE_POINTS = {\n")
    for r in spokes:
        if REGION_GRACE_POINTS.get(r):
            f.write(f"    {r!r}: {REGION_GRACE_POINTS[r]},\n")
    f.write("}\n")
print(f"region_graces: {sum(len(v) for v in REGION_GRACE_POINTS.values())} graces across {len(REGION_GRACE_POINTS)} regions")


# ---- Phase 3b dungeon sweeps: boss-defeat flag per dungeon (DarkScript EMEVD) -> member checks.
# Matt-free: HandleBossDefeatAndDisplayBanner(<flag>) in the decompiled event scripts is the boss
# trigger; members are that dungeon map's greenfield checks. FLAG-KEYED (a small client handler to
# watch the boss-defeat flag activates these in-game -- P3b-client). Skipped if event/ is absent.
import re as _re2
_EVDIR = os.path.join(AR, "event")
_map_boss = defaultdict(list)
if os.path.isdir(_EVDIR):
    for _fn in os.listdir(_EVDIR):
        _mm = _re2.match(r"(m\d\d_\d\d)_\d\d_\d\d\.emevd\.dcx\.js$", _fn)
        if not _mm:
            continue
        _txt = open(os.path.join(_EVDIR, _fn), encoding="utf-8", errors="replace").read()
        for _fl in _re2.findall(r"HandleBossDefeatAndDisplayBanner\((\d+),", _txt):
            _map_boss[_mm.group(1)].append(int(_fl))
def _mp2(m):
    if not m or m == "PENDING":
        return None
    q = m.split("_"); return "_".join(q[:2])
_mem = defaultdict(list); _mreg = {}
for _i, _r in enumerate(rows):
    _mp = _mp2(_r["map"])
    if _mp and _r["method"] in ("treasure", "emevd"):
        _mem[_mp].append(BASE_AP + _i)
        _mreg.setdefault(_mp, region_of(_r))
DUNGEON_SWEEPS = {}; SWEEP_REGION = {}
for _mp, _flags in _map_boss.items():
    _members = _mem.get(_mp)
    if not _members:
        continue
    for _fl in _flags:
        DUNGEON_SWEEPS[_fl] = sorted(_members)
        SWEEP_REGION[_fl] = _mreg.get(_mp, HUB)
OUT_SWEEP = os.path.join(HERE, "eldenring_gf", "boss_sweeps.py")
with open(OUT_SWEEP, "w", newline="\n", encoding="utf-8") as f:
    f.write('"""AUTO-GENERATED (gen_data.py). Dungeon sweeps: boss-defeat flag (DarkScript EMEVD) ->\n')
    f.write('member check ap-ids + region. Matt-free. Needs a client flag-watch handler to fire in-game."""\n')
    f.write("DUNGEON_SWEEPS = {\n")
    for _fl in sorted(DUNGEON_SWEEPS):
        f.write(f"    {_fl}: {DUNGEON_SWEEPS[_fl]},\n")
    f.write("}\n\nSWEEP_REGION = {\n")
    for _fl in sorted(SWEEP_REGION):
        f.write(f"    {_fl}: {SWEEP_REGION[_fl]!r},\n")
    f.write("}\n")
print(f"boss_sweeps: {len(DUNGEON_SWEEPS)} dungeon triggers, {sum(len(v) for v in DUNGEON_SWEEPS.values())} member links across {len(set(SWEEP_REGION.values()))} regions")


# ---- Phase 4 shops: shop-purchase checks keyed by greenfield ap-id -> ShopLineupParam stock flag.
# Matt-free: region_map rows with method in {shop_merchant, shop_multi} carry flag_source=="shop",
# and for those rows region_map's `flag` IS ShopLineupParam.eventFlag_forStock (verified 505/505 on
# disk). cookbook rows are map_lot/enemy_lot pickups (not shop purchases) so they're NOT shop checks.
# SHOP_ROW_FLAGS {str(ap_id): stock_flag} is the client purchase-detect table; SHOP_LOC_REGION lets
# the feature scope to kept regions; SHOP_PREVIEW_GOODS {str(ap_id): vanilla equipId} (single-good
# rows only) is the vanilla preview. Degrades to empty if ShopLineupParam is absent.
_SLP_DIR = os.path.join(AR, "vanilla_er", "vanilla_er")
_SLP = os.path.join(_SLP_DIR, "ShopLineupParam.csv")
_REC = os.path.join(_SLP_DIR, "ShopLineupParam_Recipe.csv")
_flag2goods = defaultdict(list)   # stock_flag -> [(equipId, equipType)]
_flag2rows = defaultdict(list)    # stock_flag -> [ShopLineupParam row ID] (client shopRowFlags key)
_CAT_NIB = {0:0x00000000,1:0x10000000,2:0x20000000,3:0x40000000,4:0x80000000}
_slp_present = os.path.isfile(_SLP)
if _slp_present:
    for _src in [_SLP] + ([_REC] if os.path.isfile(_REC) else []):
        for _sr in csv.DictReader(open(_src)):
            try:
                _fl = int(_sr["eventFlag_forStock"])
            except (KeyError, ValueError):
                continue
            if _fl <= 0:
                continue
            try:
                _flag2rows[_fl].append(int(_sr["ID"]))
            except (KeyError, ValueError):
                pass
            try:
                _flag2goods[_fl].append((int(_sr["equipId"]), int(_sr.get("equipType", 3))))
            except (KeyError, ValueError):
                pass
_SHOP_METHODS = {"shop_merchant", "shop_multi"}
SHOP_ROW_FLAGS = {}
SHOP_ROW_IDS = {}
SHOP_LOC_REGION = {}
SHOP_PREVIEW_GOODS = {}
for _i, _r in enumerate(rows):
    if _r["method"] not in _SHOP_METHODS or _r.get("flag_source") != "shop":
        continue
    try:
        _fl = int(_r["flag"])
    except (KeyError, ValueError):
        continue
    _aid = BASE_AP + _i
    SHOP_ROW_FLAGS[str(_aid)] = _fl
    # ShopLineupParam row ids whose eventFlag_forStock == this flag (client writes this flag
    # onto those rows). Usually one; a flag shared across rows lists them all (all get asserted).
    SHOP_ROW_IDS[str(_aid)] = sorted(set(_flag2rows.get(_fl, [])))
    SHOP_LOC_REGION[_aid] = region_of(_r)
    _goods = _flag2goods.get(_fl)
    if _goods and len({_e for _e, _t in _goods}) == 1:
        _eid, _et = _goods[0]
        SHOP_PREVIEW_GOODS[str(_aid)] = _eid | _CAT_NIB.get(_et, 0x40000000)
OUT_SHOP = os.path.join(HERE, "eldenring_gf", "shop_data.py")
with open(OUT_SHOP, "w", newline="\n", encoding="utf-8") as f:
    f.write('"""AUTO-GENERATED (gen_data.py). Shop-purchase checks: greenfield ap-id -> ShopLineupParam\n')
    f.write('eventFlag_forStock (region_map shop rows, flag_source=="shop"). Matt-free; preview goods are\n')
    f.write('vanilla equipIds. Empty if ShopLineupParam is absent (SPEC-PARITY.md 14.3)."""\n')
    f.write("SHOP_ROW_FLAGS = {\n")
    for _aid in sorted(SHOP_ROW_FLAGS, key=int):
        f.write(f"    {_aid!r}: {SHOP_ROW_FLAGS[_aid]},\n")
    f.write("}\n\nSHOP_ROW_IDS = {\n")
    for _aid in sorted(SHOP_ROW_IDS, key=int):
        f.write(f"    {_aid!r}: {SHOP_ROW_IDS[_aid]!r},\n")
    f.write("}\n\nSHOP_LOC_REGION = {\n")
    for _aid in sorted(SHOP_LOC_REGION):
        f.write(f"    {_aid}: {SHOP_LOC_REGION[_aid]!r},\n")
    f.write("}\n\nSHOP_PREVIEW_GOODS = {\n")
    for _aid in sorted(SHOP_PREVIEW_GOODS, key=int):
        f.write(f"    {_aid!r}: {SHOP_PREVIEW_GOODS[_aid]},\n")
    f.write("}\n")
print(f"shop_data: {len(SHOP_ROW_FLAGS)} shop checks, {len(SHOP_PREVIEW_GOODS)} with preview goods across {len(set(SHOP_LOC_REGION.values()))} regions (param_present={_slp_present})")


# ---- Real-item-pool foundation: each location's vanilla item -> its ER FullID (matt-free).
# Names come from the WitchyBND FMG exports (msg/item-msgbnd-dcx + the item_dlc0{1,2}-msgbnd-dcx
# DLC name tables, *Name.fmg.xml); id == EquipParam/Goods/Gem id (verified Golden Rune [1]=2900 ->
# 0x40000B54, Golden Rune [12]=2911 -> 0x40000B5F). name -> FullID = id | category nibble, priority
# weapon>armor>accessory>goods>gem on cross-category name clashes. NOTE (measured on disk): spells
# already live in GoodsName (e.g. Glintstone Pebble = Goods id 4000 -> 0x40000FA0) and Ashes of War
# in GemName (e.g. Ash of War: Barbaric Roar = Gem id 0x13068 -> 0x80013068); the MagicName/ArtsName
# tables are empty stubs / redundant with GemName here and add no coverage, so they are omitted.
# Coverage beyond a direct hit is lifted by (a) the DLC name tables and (b) mechanically stripping the
# location bread-crumbs region_map decorates vanilla names with -- a leading "LG/(CE): " area code, a
# trailing " - <where>", a trailing " x<N>" count, and a "[Sorcery]/[Incantation]/[Ash of War]/[Skill]"
# prefix -- to re-match the BASE item, then falling back to a whitespace-normalized + diacritic-folded
# (accent/case-insensitive) match (0 fold collisions on this data). All matt-free: pure FMG/param joins
# plus mechanical string trims, no curation, no guessed ids. Emits item_ids.py:
#   ITEM_CATALOG {item_name: FullID}   -- distinct resolved BASE items (the AP item catalog)
#   LOCATION_ITEM {ap_id: item_name}   -- the BASE vanilla item that sits at each resolved location
#     (annotated location strings resolve to the base catalog name, so the same location grants base).
# Unresolved names (empty item_name, quest "Note:" text, source typos, items in no FMG) are omitted ->
# core falls back to Rune filler. Guard-to-empty if the FMG name dirs are absent.
import xml.etree.ElementTree as _ET
import unicodedata as _UD
_MSG    = os.path.join(AR, "msg", "item-msgbnd-dcx")
_MSG_D1 = os.path.join(AR, "msg", "item_dlc01-msgbnd-dcx")
_MSG_D2 = os.path.join(AR, "msg", "item_dlc02-msgbnd-dcx")
# (filename, category nibble, dir). base tables first so base ids win over DLC on any name clash.
_NAME_FMGS = [
    ("WeaponName.fmg.xml",    0x00000000, _MSG), ("ProtectorName.fmg.xml", 0x10000000, _MSG),
    ("AccessoryName.fmg.xml", 0x20000000, _MSG), ("GoodsName.fmg.xml",      0x40000000, _MSG),
    ("GemName.fmg.xml",       0x80000000, _MSG),
    ("WeaponName_dlc01.fmg.xml",    0x00000000, _MSG_D1), ("ProtectorName_dlc01.fmg.xml", 0x10000000, _MSG_D1),
    ("AccessoryName_dlc01.fmg.xml", 0x20000000, _MSG_D1), ("GoodsName_dlc01.fmg.xml",      0x40000000, _MSG_D1),
    ("GemName_dlc01.fmg.xml",       0x80000000, _MSG_D1),
    ("WeaponName_dlc02.fmg.xml",    0x00000000, _MSG_D2), ("ProtectorName_dlc02.fmg.xml", 0x10000000, _MSG_D2),
    ("AccessoryName_dlc02.fmg.xml", 0x20000000, _MSG_D2), ("GoodsName_dlc02.fmg.xml",      0x40000000, _MSG_D2),
    ("GemName_dlc02.fmg.xml",       0x80000000, _MSG_D2),
]
def _norm(_s):                                   # collapse internal whitespace
    return re.sub(r"\s+", " ", _s).strip()
def _fold(_s):                                   # accent-insensitive, case-insensitive key
    _s = _UD.normalize("NFKD", _norm(_s))
    return "".join(_c for _c in _s if not _UD.combining(_c)).casefold()
_name2full = {}        # exact display name -> FullID (first/higher-priority category wins)
_norm2full = {}; _norm2name = {}    # normalized name -> FullID / canonical display name
_fold2full = {}; _fold2name = {}    # folded name     -> FullID / canonical display name
for _fn, _nib, _dir in _NAME_FMGS:
    _p = os.path.join(_dir, _fn)
    if not os.path.exists(_p):
        continue
    for _t in _ET.parse(_p).getroot().iter("text"):
        _nm = (_t.text or "").strip(); _iid = _t.get("id")
        if not _nm or _nm in ("[ERROR]", "%null%") or not _iid:
            continue
        _full = int(_iid) | _nib
        if _nm not in _name2full:
            _name2full[_nm] = _full
        _nn = _norm(_nm)
        if _nn not in _norm2full:
            _norm2full[_nn] = _full; _norm2name[_nn] = _nm
        _ff = _fold(_nm)
        if _ff not in _fold2full:
            _fold2full[_ff] = _full; _fold2name[_ff] = _nm
# annotation strippers (region_map decorates vanilla names with location bread-crumbs)
_LEAD_RE   = re.compile(r"^[A-Z][A-Za-z0-9/()]*\s*:\s*")           # "LG/(CE): " / "RH: " / "MA/(LER): "
_ANNOT_RE  = re.compile(r"\s+-\s+.*$")                              # " - to SW up right stairs outside"
_COUNT_RE  = re.compile(r"\s*[x×]\s*\d+\s*$", re.I)        # trailing " x3" / " ×3"
_PREFIX_RE = re.compile(r"^\[(?:Sorcery|Incantation|Ash of War|Skill)\]\s*", re.I)
def _resolve_item(_raw):
    """(FullID, canonical_base_name) or (None, None). Matt-free mechanical strips + accent fold only."""
    _raw = (_raw or "").strip()
    if not _raw:
        return (None, None)
    _tries = []
    def _add(_s):
        _s = _norm(_s)
        if _s and _s not in _tries:
            _tries.append(_s)
    _add(_raw)
    _lead = _LEAD_RE.sub("", _raw); _add(_lead); _add(_ANNOT_RE.sub("", _lead))
    _core = _COUNT_RE.sub("", _ANNOT_RE.sub("", _lead)); _add(_core); _add(_PREFIX_RE.sub("", _core))
    for _t in _tries:                            # exact normalized hit -> canonical display name
        if _t in _norm2full:
            return (_norm2full[_t], _norm2name[_t])
    for _t in _tries:                            # accent/case-folded fallback -> canonical name
        _ff = _fold(_t)
        if _ff in _fold2full:
            return (_fold2full[_ff], _fold2name[_ff])
    return (None, None)
ITEM_CATALOG = {}; LOCATION_ITEM = {}
for _i, _r in enumerate(rows):
    _full, _base = _resolve_item(_r.get("item_name"))
    if _full is None:
        continue
    ITEM_CATALOG[_base] = _full                  # catalog keyed by canonical base name
    LOCATION_ITEM[BASE_AP + _i] = _base          # annotated locations -> base catalog name
OUT_ITEMS = os.path.join(HERE, "eldenring_gf", "item_ids.py")
with open(OUT_ITEMS, "w", newline="\n", encoding="utf-8") as f:
    f.write('"""AUTO-GENERATED (gen_data.py). Real-item-pool: vanilla item_name -> ER FullID, from the\n')
    f.write('FMG name exports (base + DLC, matt-free). ITEM_CATALOG = distinct {name: FullID}; LOCATION_ITEM =\n')
    f.write('{ap_id: base name}. Unresolved locations fall back to Rune filler. core ItemShuffle consumes this."""\n')
    f.write("ITEM_CATALOG = {\n")
    for _nm in sorted(ITEM_CATALOG):
        f.write(f"    {ascii(_nm)}: {ITEM_CATALOG[_nm]},\n")
    f.write("}\n\nLOCATION_ITEM = {\n")
    for _aid in sorted(LOCATION_ITEM):
        f.write(f"    {_aid}: {ascii(LOCATION_ITEM[_aid])},\n")
    f.write("}\n")
_cov = 100.0 * len(LOCATION_ITEM) / max(len(rows), 1)
print(f"item_ids: {len(ITEM_CATALOG)} distinct items, {len(LOCATION_ITEM)} locations resolved ({_cov:.1f}%)")


# ---- Phase 5 pool-builder tiers: vanilla item quality from the ER param `rarity` column
# (matt-free -- param-derived, no curation). Joins each ITEM_CATALOG FullID back to its EquipParam
# row (weapon/protector/accessory) and reads `rarity` (0=trivial/ammo, 1=common, 2=rare,
# 3=legendary). Goods (0x40000000) and gems/ashes (0x80000000) are not equippable "juice" and are
# omitted -> they stay filler. Emits item_tiers.py:  ITEM_TIERS {item_name: rarity 0..3}.
# Degrades to an empty map if the vanilla_er param CSVs are absent (feature then no-ops).
_TIER_PARAMS = [(0x00000000, "EquipParamWeapon.csv"),      # weapons/staves/shields/bows (nibble 0x0)
                (0x10000000, "EquipParamProtector.csv"),   # armor                        (nibble 0x1)
                (0x20000000, "EquipParamAccessory.csv")]   # talismans                    (nibble 0x2)
_rarity_by_full = {}   # FullID (id | category nibble) -> rarity int
for _nib, _csv in _TIER_PARAMS:
    _p = os.path.join(_SLP_DIR, _csv)
    if not os.path.isfile(_p):
        continue
    for _row in csv.DictReader(open(_p, newline="", encoding="utf-8", errors="replace")):
        try:
            _rarity_by_full[(int(_row["ID"]) | _nib)] = int(_row["rarity"])
        except (KeyError, ValueError):
            continue
ITEM_TIERS = {}
for _nm, _full in ITEM_CATALOG.items():
    _r = _rarity_by_full.get(_full)
    if _r is not None:
        ITEM_TIERS[_nm] = _r
OUT_TIERS = os.path.join(HERE, "eldenring_gf", "item_tiers.py")
with open(OUT_TIERS, "w", newline="\n", encoding="utf-8") as f:
    f.write('"""AUTO-GENERATED (gen_data.py). Phase 5 pool-builder: vanilla item_name -> quality tier\n')
    f.write('from the ER param `rarity` column (0=trivial,1=common,2=rare,3=legendary), joined by\n')
    f.write('FullID to EquipParamWeapon/Protector/Accessory. Matt-free (param-derived, no curation).\n')
    f.write('Equippables only; goods/gems omitted (stay filler). features/pool_builder.py consumes this."""\n')
    f.write("ITEM_TIERS = {\n")
    for _nm in sorted(ITEM_TIERS):
        f.write(f"    {_nm!r}: {ITEM_TIERS[_nm]},\n")
    f.write("}\n")
from collections import Counter as _Cnt
_td = _Cnt(ITEM_TIERS.values())
print(f"item_tiers: {len(ITEM_TIERS)} equippables tiered "
      f"(legendary={_td.get(3,0)}, rare={_td.get(2,0)}, common={_td.get(1,0)}, trivial={_td.get(0,0)})")
