#!/usr/bin/env python3
r"""datamine_grace_ground.py -- derive, per warp grace, the PLAY-REGION GROUND it stands on.

WHY THIS EXISTS (the Charo's kick, 2026-07-15). A region lock force-lights every grace in the
region's bundle so the player can warp in. The kick-watch then checks the play_region bucket of
the ground the player is STANDING on -- which is a different fact from the warp-menu group the
grace is listed under. When they disagree, the player warps to a grace their own lock just lit
and is immediately kicked for trespassing on a SIBLING region's ground:

    kick-watch: play_region 6840000 (sub 68400); range [68400,68400] flag 76831 = false
    -> kick = true; SEALED REGION -- Returning to Roundtable        (Charo's, in-game log)

Grace 76841 ("Charo's Hidden Grave", warp group 6840 = Charo's) stands on bucket 68400, which
region_groups.py had assigned to Cerulean. This tool derives that fact FROM THE GAME DATA so the
mismatch is caught at gen time, not by a playtester.

DERIVATION
  * OVERWORLD graces (BonfireWarpParam areaNo 60/61): point-in-volume test of the grace's spawn
    position against every witchy'd MSB `Region/PlayArea` volume (Box/Cylinder/Sphere/Composite,
    m60_*/m61_* tiles, elden_ring_artifacts/map/). PlayArea regions carry <PlayRegionID> -- the
    exact runtime id the client's kick-watch reads. World transform: world = tile*256 + local;
    box containment rotates the delta by +yaw (standard 2D rotation on (x,z)).
    CALIBRATION: grace 76841's in-game measured ground (6840000, client log 2026-07-15) is
    reproduced by this transform -- it falls inside the tile-48/39 "dragon-mountain west" box.
    Where no volume contains the grace but a volume FACE is within SEAM_SLACK m, it SNAPS to that
    face's bucket -- the SAME seam step the interiors have always had, and the same one
    datamine_item_play_regions has always applied outdoors. Until 2026-08-26 this tool skipped it
    on the overworld and fell straight to the default, which made three graces sitting 0.9-3.6 m
    from a PlayArea face answer 'none' where the item pass answered the face (76214/76453/76500).
    Fallback where neither holds: the PlayRegionParam coordinate row(s) of the tile the folded
    point STANDS on (the tile DEFAULT). If neither exists the ground is UNDERIVABLE ('-'):
    engine-side tile defaults are not all expressed in params, and we refuse to guess.
  * MEASURED grounds (the Scaduview kick, 2026-07-15): an in-game kick-watch line is the ENGINE
    itself reporting the play_region at a grace -- stronger than any of the above. MEASURED_GROUND
    records such data points; they fill rows the derivation cannot reach and must AGREE with the
    derivation where both exist (a disagreement means the transform broke -- fatal, not a shrug).
    We do NOT generalize them into a legacy-map-overlay rule: WorldMapLegacyConvParam maps every
    legacy/interior map onto overworld tiles, but for teleport-linked maps (Farum Azula, Haligtree,
    the underground) and under-surface dungeons those dst tiles are WORLD-MAP DISPLAY anchoring,
    not physical ground -- a blanket rule mis-files Bestial Sanctum on Farum Azula's 13000 and the
    Altus Plateau grace on the Precipice's 39200 (tried and reverted, 2026-07-15).
  * INTERIOR graces (BonfireWarpParam areaNo NOT 60/61): the SAME point-in-volume test, now run
    against the PlayArea volumes of the grace's OWN interior MSB (mAA_BB; world == local, no tile
    offset). A volume that CONTAINS the grace gives its exact PlayRegionID bucket -- this is what
    catches a FOREIGN region's ground poking into an interior map. Where the grace is inside NO
    volume but within SEAM_SLACK m of a volume FACE (a gate/threshold seam) it SNAPS to that nearest
    volume's bucket. Only inside-no-volume-and-near-none falls back to the map-prefix bucket(s)
    (m41_02 -> 41020). The Shadow Keep Main Gate is why: grace 72102 sits in a seam 3.6 m outside the
    Scadu Altus 6900000 approach column and is inside no Shadow Keep 21000 volume in the m21_00 MSB,
    yet the old map-prefix path emitted 21000 (Shadow Keep) and warped Keep-holders into a kick.
    IMPORTANT -- the map-prefix default is NOT a safe fallback at a seam: the 76935 note below says a
    point inside no volume reads the map default (here 21000), but the in-game kick at 72102 (Alaric
    2026-07-21) REFUTES that for this point -- a Keep-holder standing on 21000 is never kicked, so the
    engine reads a non-21000 play_region at the gate, and the only play-region volume near it is
    Scadu Altus's. The seam-snap makes the derivation agree with the engine. (The 3.6 m gap between
    the grace and the authored volume face is closed engine-side by the arrival point and/or the
    engine's own containment tolerance; SEAM_SLACK models that.) The seam emits ONE bucket -- the
    nearest, 69000 -- not {69000,21000}: the kick has already refuted 21000, and a two-bucket row
    would read as non-foreign and silently NOT fix the bug. Map-prefix is now the LAST resort, not
    the first. The 72102 kick is now ENGINE-MEASURED: warping to the grace read raw play_region
    6900000/6900010 (bucket 69000, kick 3x, client log 2026-07-21) -- pinned in MEASURED_GROUND, which
    asserts the seam derivation against it and holds 69000 even on a regen with no interior MSB.

OUTPUT: greenfield/grace_ground.tsv (TRACKED -- CI has no artifacts). gen_data.py consumes it:
a bundle grace whose derived ground is owned by a foreign region is NOT force-lit, and a region
whose FRONT-DOOR grace stands on foreign ground kills the gen (fix region_groups.py, like 68400).

    python tools/datamine_grace_ground.py            # report only
    python tools/datamine_grace_ground.py --emit     # write greenfield/grace_ground.tsv

Y-SLACK: containment allows +/-8 m vertically (grace assets sit slightly above the volume floor).
SEAM_SLACK (interior only): the planar mirror of that tolerance -- an interior grace inside no
volume but within SEAM_SLACK m of a volume face stands on that volume's ground. It only ever
differs from the map-prefix fallback when the nearest face belongs to a FOREIGN-bucket volume
(the seam case); a same-bucket nearest face snaps to the same answer the fallback would give.
"""
import argparse
import csv
import glob
import math
import os
import re
import sys
import xml.etree.ElementTree as ET

XSI = "{http://www.w3.org/2001/XMLSchema-instance}type"
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.dirname(HERE)
sys.path.insert(0, HERE)

import artifacts_root                          # noqa: E402  -- THE --path argument, not a copy
from overworld_fold import fine_tile, world_xz  # noqa: E402  -- THE fold + tile attribution (#338)

AR = artifacts_root.default_root(REPO)
BWP = os.path.join(AR, "vanilla_er", "vanilla_er", "BonfireWarpParam.csv")
PRP = os.path.join(AR, "vanilla_er", "vanilla_er", "PlayRegionParam.csv")
MAPDIR = artifacts_root.msb_dir(AR) or os.path.join(AR, "map")
OUT = os.path.join(REPO, "greenfield", "grace_ground.tsv")

# Refuse to emit a table that would silently shrink the derived set: like arena_graces.tsv, the
# derivation depends on the unpacked MSBs being PRESENT -- rerunning without them must fail, not
# quietly write an all-underivable table that turns the gen gate off.
MIN_DERIVED = 200   # measured 2026-07-15: 293/421 graces derive a ground. Raise, never lower.

# Planar tolerance for the INTERIOR seam-snap (see the docstring's INTERIOR bullet for the full
# justification). Numerically the planar twin of the +/-8 m vertical yslack, and it covers the one
# case that motivates it -- the Main Gate 72102 sits 3.6 m outside the Scadu Altus 6900000 approach
# column. It is NOT merely a geometric fudge: at 72102 the in-game kick REFUTES the map-prefix
# fallback (a Keep-holder on 21000 is never kicked), so the snap is what makes the derivation agree
# with the engine. It changes the answer from the fallback only when the nearest face is a
# foreign-bucket volume (a same-bucket nearest face snaps to the fallback's own answer).
SEAM_SLACK = 8.0

# In-game ENGINE measurements: grace flag -> (ground buckets, provenance). Each entry is a client
# kick-watch/log line read at that grace -- the same instrument the enforcement itself uses. They
# override 'none' rows and are ASSERTED against the derivation where both exist.
#   76935 "Hinterland" (front door of region Scaduview, m61_50_48): warping there read raw
#   play_region 2100010 -> bucket 21000 = Shadow Keep (client log 2026-07-15, the Scaduview kick).
#   Corroboration: m21_00 overlays that tile (WorldMapLegacyConvParam row 1105), its MSB defines
#   override volumes for subs 2100001/11/12/13/15 and NONE for 2100010 -- 2100010 is m21_00's
#   default ground, which is what the plateau outside Scaduview's own 6930000 volumes reads.
MEASURED_GROUND = {
    76935: ((21000,), "measured:2100010 client kick line 2026-07-15"),
    #   72102 "Shadow Keep Main Gate" (entity 21001952): warping to the grace read raw play_region
    #   6900000 / 6900010 -> bucket 69000 = Scadu Altus, kick=true 3x while holding ONLY the Keep lock
    #   (Alaric, archipelago client log 2026-07-21, 12:12:19 / 12:14:27 / 12:15:21). AGREES with the
    #   interior-seam derivation (72102 sits 3.6 m from the m21_00 Scadu Altus 6900000 approach column),
    #   and hard-pins 69000 even if a regen ever runs without the interior MSB (the fallback would give
    #   the map-prefix 21000 -- the exact stale value that caused the kick). NOTE the ARENA grace 72101
    #   "Main Gate Plaza" is a DIFFERENT point (~29 m inside, boss-lit) and stays 21000 -- the Golden
    #   Hippopotamus fight/loot is Keep ground; only this approach grace is on the Scadu Altus seam.
    72102: ((69000,), "measured:6900000/6900010 client kick lines 2026-07-21 (warp to grace 21001952, 3x)"),
}


def _set_artifacts_root(path):
    """Point every input at a DIFFERENT artifacts tree -- what `--path` (alias `--artifacts`)
    calls, the one flag shared by every corpus-reading tool (tools/artifacts_root.py). Exists so the derivation can be exercised against a
    synthetic MSB fixture -- the machinery below is otherwise only reachable on a box with the
    extracted corpus, which is how it stayed untested for a month."""
    global AR, BWP, PRP, MAPDIR
    AR = os.path.abspath(path)
    BWP = os.path.join(AR, "vanilla_er", "vanilla_er", "BonfireWarpParam.csv")
    PRP = os.path.join(AR, "vanilla_er", "vanilla_er", "PlayRegionParam.csv")
    # DISCOVERY, not a hardcoded subdir: `map/`, `mapstudio/`, `map/mapstudio/`, then the root
    # itself (tools/artifacts_root.py). A witchy export that landed FLAT under `mapstudio/` used
    # to make this tool alone say "no witchy'd m60/m61 MSBs" while three sibling tools read the
    # same corpus fine. Falls back to `map/` so the FATAL below still names a path when the
    # corpus is absent entirely (CI has none).
    MAPDIR = artifacts_root.msb_dir(AR) or os.path.join(AR, "map")
    _INTERIOR_VOLS.clear()


def load_play_region_defaults(prp=None):
    """(tile_ids, interior_ids) out of PlayRegionParam.csv -- the LAST-RESORT answers.

    tile_ids:     (gridXNo, gridZNo) -> {PlayRegionID}  for the overworld areas 60/61.
    interior_ids: 'mAA_BB'           -> {PlayRegionID}  for the interior maps the id space encodes.
    Full ids, not buckets: a caller that wants the kick-watch bucket divides by 100 itself, and a
    caller that wants to PRINT the id (item_play_regions.tsv does) still can.
    """
    tile_ids = {60: {}, 61: {}}
    interior_ids = {}
    for r in csv.DictReader(open(prp or PRP, newline="", encoding="utf-8-sig")):
        i = int(r["ID"])
        a = int(r["areaNo"] or 0)
        if a in (60, 61):
            tile_ids[a].setdefault((int(r["gridXNo"]), int(r["gridZNo"])), set()).add(i)
        if i // 100 and i // 100 < 60000:
            interior_ids.setdefault("m%02d_%02d" % (i // 100000, (i // 1000) % 100), set()).add(i)
    return tile_ids, interior_ids


class Vol:
    __slots__ = ("pr", "area", "name", "kind", "cx", "cy", "cz", "yaw", "a", "b", "h")

    def __init__(s, pr, area, name, kind, cx, cy, cz, yaw, a, b, h):
        s.pr, s.area, s.name, s.kind = pr, area, name, kind
        s.cx, s.cy, s.cz, s.yaw = cx, cy, cz, yaw
        s.a, s.b, s.h = a, b, h

    def contains(s, x, y, z, yslack=8.0):
        dx, dz = x - s.cx, z - s.cz
        if not (s.cy - yslack <= y <= s.cy + (s.h or 1e18) + yslack):
            return False
        if s.kind == "Box":
            r = math.radians(s.yaw)
            c, sn = math.cos(r), math.sin(r)
            return abs(dx * c - dz * sn) <= s.a / 2 and abs(dx * sn + dz * c) <= s.b / 2
        if s.kind == "Cylinder":
            return dx * dx + dz * dz <= s.a * s.a
        if s.kind == "Sphere":
            dy = y - s.cy
            return dx * dx + dz * dz + dy * dy <= s.a * s.a
        return False


def _shape(el):
    sh = el.find("Shape")
    k = sh.get(XSI)
    if k == "Box":
        return k, float(sh.findtext("Width")), float(sh.findtext("Depth")), float(sh.findtext("Height"))
    if k == "Cylinder":
        return k, float(sh.findtext("Radius")), 0.0, float(sh.findtext("Height"))
    if k == "Sphere":
        return k, float(sh.findtext("Radius")), 0.0, 0.0
    if k == "Composite":
        return k, [c.findtext("RegionName") for c in sh.iter("Child") if c.findtext("RegionName")], 0.0, 0.0
    return k, 0.0, 0.0, 0.0


def _load_msb_playareas(d, area, tx, tz):
    """Every PlayArea volume in ONE witchy'd MSB dir, world-positioned (world = tile*256 + local;
    pass tx=tz=0 for an interior map, where local coords ARE world). Composite shapes are resolved
    to their named child regions within the same MSB."""
    out = []
    pa = os.path.join(d, "Region", "PlayArea")
    if not os.path.isdir(pa):
        return out
    pend = []
    for f in glob.glob(os.path.join(pa, "*.xml")):
        el = ET.parse(f).getroot()
        pend.append((int(el.findtext("PlayRegionID")), el))
    need = set()
    for pr, el in pend:
        k, a, _b, _h = _shape(el)
        if k == "Composite":
            need.update(a)
    byname = {}
    if need:
        # composite children live in Region/Other (occasionally another category); search the
        # shallow categories rather than the whole tree -- the mount is slow on deep globs.
        _cand = glob.glob(os.path.join(d, "Region", "Other", "*.xml"))
        _cand += [f for f in glob.glob(os.path.join(d, "Region", "*", "*.xml"))
                  if os.sep + "Other" + os.sep not in f]
        for f in _cand:
            try:
                el = ET.parse(f).getroot()
            except ET.ParseError:
                continue
            nm = el.findtext("Name")
            if nm in need:
                byname[nm] = el
    for pr, el in pend:
        stack, seen = [el], set()
        while stack:
            e = stack.pop()
            nm = e.findtext("Name")
            if nm in seen:
                continue
            seen.add(nm)
            k, a, b, h = _shape(e)
            if k == "Composite":
                stack.extend(byname[cn] for cn in a if cn in byname)
                continue
            pos, rot = e.find("Position"), e.find("Rotation")
            x, y, z = (float(pos.findtext(c)) for c in "XYZ")
            out.append(Vol(pr, area, nm, k, tx * 256 + x, y, tz * 256 + z,
                           float(rot.findtext("Y")), a, b, h))
    return out


def load_volumes():
    """Every PlayArea volume on the witchy'd m60/m61 overworld tiles, world-positioned."""
    vols = []
    tile_dirs = sorted(set(glob.glob(os.path.join(MAPDIR, "m6[01]_*_00-msb-dcx"))))
    if not tile_dirs:
        raise SystemExit("FATAL: no witchy'd m60/m61 MSBs under %s -- the overworld ground "
                         "derivation needs them (WitchyBND the .msb.dcx first). Searched under "
                         "the artifacts root %s: %s."
                         % (MAPDIR, AR, artifacts_root.msb_search_report(AR)))
    for d in tile_dirs:
        bn = os.path.basename(d)
        area, tx, tz = int(bn[1:3]), int(bn[4:6]), int(bn[7:9])
        vols.extend(_load_msb_playareas(d, area, tx, tz))
    # dedupe (_00/_10 MSB variants carry identical copies)
    uniq = {}
    for v in vols:
        uniq[(v.area, v.pr, round(v.cx, 2), round(v.cz, 2), v.kind, round(v.a, 2))] = v
    return list(uniq.values())


_INTERIOR_VOLS = {}


def load_interior_volumes(mtile):
    """PlayArea volumes for ONE interior map (mAA_BB), world == local. Cached per map. Returns []
    if that MSB is absent -- interior volume derivation is best-effort, and an absent MSB simply
    falls the grace back to the map-prefix default (the pre-2026-07-21 behaviour)."""
    if mtile in _INTERIOR_VOLS:
        return _INTERIOR_VOLS[mtile]
    vols = []
    m = re.match(r"m(\d\d)_(\d\d)$", mtile or "")
    if m:
        aa, bb = m.group(1), m.group(2)
        for d in sorted(glob.glob(os.path.join(MAPDIR, "m%s_%s_00_00-msb-dcx" % (aa, bb)))):
            vols.extend(_load_msb_playareas(d, int(aa), 0, 0))
    _INTERIOR_VOLS[mtile] = vols
    return vols


def _nearest_face(vols, x, y, z):
    """(planar face-distance, vol) for the nearest volume whose y-range (+/-yslack) holds y, else
    None. Face-distance = how far (x,z) lies OUTSIDE the volume footprint (0 if inside it in plane).
    Handles all three shapes so a grace can't snap PAST a nearer same-bucket cylinder/sphere onto a
    farther foreign box. y-gated so a grace never snaps to a volume far above/below it."""
    best = None
    for v in vols:
        dx, dz = x - v.cx, z - v.cz
        if v.kind == "Box":
            if not (v.cy - 8.0 <= y <= v.cy + (v.h or 1e18) + 8.0):
                continue
            r = math.radians(v.yaw)
            c, sn = math.cos(r), math.sin(r)
            du = abs(dx * c - dz * sn) - v.a / 2
            dv = abs(dx * sn + dz * c) - v.b / 2
            d = math.hypot(max(0.0, du), max(0.0, dv))
        elif v.kind == "Cylinder":
            if not (v.cy - 8.0 <= y <= v.cy + (v.h or 1e18) + 8.0):
                continue
            d = max(0.0, math.hypot(dx, dz) - v.a)   # a = radius
        elif v.kind == "Sphere":
            dy = max(0.0, abs(y - v.cy) - 8.0)        # sphere has no separate height; use 3-D gap
            d = max(0.0, math.sqrt(dx * dx + dz * dz + dy * dy) - v.a)
        else:
            continue
        if best is None or d < best[0]:
            best = (d, v)
    return best


def _srcname(v):
    """A volume's name, safe to put in a TAB-separated `source` column.

    MSB region names are free text and at least one of them contains a literal TAB: the m60_39_54
    volume `プレイ領域 6300030<TAB>高山_地図断片８_閉込ボス領域１` (grace 76322). The committed
    grace_ground.tsv row for that grace is CORRUPT because of it -- the tab split the source column
    in two and pushed the tile column off the end, so the row's `tile` reads the second half of a
    volume name instead of m60_39_54, and `--graces` reported a phantom "source delta" because the
    reader had truncated the committed source at the tab. Collapse any run of whitespace to one
    space at the point the name becomes a source string; do NOT normalise Vol.name itself, which is
    what Composite children are looked up by.
    """
    return " ".join((v.name or "").split())


def derive_ground(map_id, x, y, z, vols, tile_ids, interior_ids):
    """THE ladder, for ONE placement -> (sorted play_region ids, source string).

    This is the single owner of the volume -> seam -> default -> none ordering, for BOTH the
    overworld and the interiors, and BOTH of its callers go through it:
    `datamine_grace_ground.main` (the grace_ground.tsv derivation) and
    `datamine_item_play_regions.derive` (the item scan and its --graces calibration gate). They
    used to be two ladders that agreed on interiors and DIFFERED outdoors -- the item pass offered
    an overworld point a seam-snap before the tile default, this tool went straight to the default
    -- so a grace 1.7 m outside a PlayArea face answered `seam:` over there and `none` here (graces
    76214 / 76453 / 76500, Alaric's box, 2026-08-26). `none` is the less correct answer: the seam
    tolerance is the same engine containment slack indoors and out, and the face is right there.
    One function, so a third divergence cannot be written.

    Ids are RAW PlayRegionParam ids; the bucket is id // 100 and the caller does that division.
    """
    got = world_xz(map_id, x, z)
    if got is not None:                                          # OVERWORLD: world = tile*256+local
        area = int(got[0][1:])                                   # 'm60' -> 60
        gx, gz = got[1], got[2]
        mine = [v for v in vols if v.area == area]
        hits = [v for v in mine if v.contains(gx, y, gz)]
        if hits:
            return sorted({v.pr for v in hits}), "volume:" + _srcname(hits[0])
        near = _nearest_face(mine, gx, y, gz)                    # gate/threshold seam
        if near and near[0] <= SEAM_SLACK:
            return [near[1].pr], "seam:%s@%.1fm" % (_srcname(near[1]), near[0])
        # NOT the AUTHORED tile: the tile the folded point actually STANDS on (fine_tile rounds --
        # the overworld frame is centre-origin). For 214 of 225 graces that IS the authored tile.
        ids = sorted(tile_ids.get(area, {}).get(fine_tile(gx, gz), ()))
        return (ids, "tile-default") if ids else ([], "none")

    mkey = "_".join((map_id or "").split("_")[:2])               # 'm10_00_00_00' -> 'm10_00'
    ivols = load_interior_volumes(mkey)
    if ivols:
        hits = [v for v in ivols if v.contains(x, y, z)]         # interior: world == local
        if hits:
            return sorted({v.pr for v in hits}), "interior-vol:" + _srcname(hits[0])
        near = _nearest_face(ivols, x, y, z)
        if near and near[0] <= SEAM_SLACK:
            return [near[1].pr], "interior-seam:%s@%.1fm" % (_srcname(near[1]), near[0])
    ids = sorted(interior_ids.get(mkey, ()))
    return (ids, "interior-map") if ids else ([], "none")


def grace_rows(vols, tile_ids, interior_ids, bwp=None):
    """THE warp-grace population, for BOTH consumers -- yields (flag, map_id, tile, ids, source).

    ONE OWNER OF THE POINT, not just of the ladder. `derive_ground` above made the two tools agree
    about how a placement is judged; this generator makes them agree about WHICH PLACEMENT IS
    JUDGED. Every grace answer -- this tool's emitted `grace_ground.tsv` and
    `datamine_item_play_regions --graces`, the gate that diffs against it -- is derived from the
    BonfireWarpParam SPAWN POSITION (`posX/posY/posZ`) of the grace's own row: the point the
    player materialises at, which is the point the client's kick-watch evaluates play_region at on
    warp-in. It is NOT the grace ASSET coordinate that `greenfield/item_grace_coords.tsv` carries
    for the same flag; the two are metres apart at some graces, and a gate that compared a
    spawn-derived table against asset-derived answers would report seam/none deltas that are
    artifacts of comparing two different points.

    Until 2026-08-26 the loop below was written TWICE -- here and in the gate -- and the copies had
    already drifted: a row whose spawn position does not parse got a fallback row here and was
    silently SKIPPED there, so the gate simply never compared it. A grace the gate does not compare
    is not a grace the gate blessed.

    Yields the raw PlayRegionParam ids (bucket = id // 100, the caller divides) plus the AUTHORED
    tile, which only this tool's tsv column wants. MEASURED_GROUND is applied here, once: an
    in-game kick line is the ENGINE reporting the play_region and outranks the derivation, and a
    derivation that DISAGREES with one is fatal, not a shrug.
    """
    for r in csv.DictReader(open(bwp or BWP, newline="", encoding="utf-8-sig")):
        try:
            f = int(r["eventflagId"] or 0)
        except ValueError:
            continue
        if not (71000 <= f <= 76999):
            continue
        a = int(r["areaNo"] or 0)
        try:
            px, py, pz = float(r["posX"]), float(r["posY"]), float(r["posZ"])
        except (TypeError, ValueError):
            px = None                                # unparseable spawn: no geometry, fallback only
        if a in (60, 61):
            tx, tz = int(r["gridXNo"]), int(r["gridZNo"])
            map_id = "m%d_%02d_%02d_00" % (a, tx, tz)
            tile = "m%d_%02d_%02d" % (a, tx, tz)     # the AUTHORED tile: the grace's own map id,
            #                                          not the ruling (the ruling may fold next door)
        else:
            ent = str(r["bonfireEntityId"] or "")
            map_id = tile = "m%s_%s" % (ent[0:2], ent[2:4]) if len(ent) == 8 else "?"
        if px is None:
            ids = [] if a in (60, 61) else sorted(interior_ids.get(tile, ()))
            src = "interior-map" if ids else "none"
        else:
            ids, src = derive_ground(map_id, px, py, pz, vols, tile_ids, interior_ids)
        if f in MEASURED_GROUND:
            mbks, msrc = MEASURED_GROUND[f]
            bks = sorted({i // 100 for i in ids})
            if bks and tuple(bks) != tuple(mbks):
                raise SystemExit(
                    "FATAL: derived ground %r for grace %d disagrees with the in-game measurement "
                    "%r (%s) -- the volume transform or the params changed; re-derive, do not "
                    "paper over." % (bks, f, list(mbks), msrc))
            if not bks:
                ids, src = [b * 100 for b in mbks], msrc
        yield f, map_id, tile, ids, src


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit", action="store_true", help="write %s" % OUT)
    artifacts_root.add_path_argument(ap)
    args = ap.parse_args(argv)          # argv is a PARAMETER so the suite can drive it
    root = artifacts_root.resolve(args.path)
    if root:
        _set_artifacts_root(root)
    for p in (BWP, PRP):
        if not os.path.isfile(p):
            raise SystemExit("FATAL: %s missing -- restore elden_ring_artifacts." % p)

    vols = load_volumes()
    print("PlayArea volumes: %d (m60+m61)" % len(vols))

    tile_ids, interior_ids = load_play_region_defaults()

    rows = []
    for f, _map_id, tile, ids, src in grace_rows(vols, tile_ids, interior_ids):
        bks = sorted({i // 100 for i in ids})
        rows.append((f, ";".join(map(str, bks)) or "-", src, tile))

    rows.sort()
    derived = sum(1 for _f, b, _s, _t in rows if b != "-")
    print("graces: %d total, %d with a derived ground, %d underivable"
          % (len(rows), derived, len(rows) - derived))
    if derived < MIN_DERIVED:
        raise SystemExit("FATAL: only %d graces derived a ground (floor %d) -- the MSBs are "
                         "missing or truncated; refusing to emit a gate-blinding table."
                         % (derived, MIN_DERIVED))
    if args.emit:
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("# AUTO-GENERATED by tools/datamine_grace_ground.py --emit -- DO NOT EDIT.\n")
            fh.write("# Per warp grace: the play_region BUCKET(s) of the ground it stands on (kick-watch\n")
            fh.write("#   id space, PlayRegionParam.ID // 100), derived from MSB Region/PlayArea volumes +\n")
            fh.write("#   PlayRegionParam tile defaults. '-' = underivable (no volume, no tile row).\n")
            fh.write("# Consumed by greenfield/gen_data.py: a grace force-lit by a region lock must stand\n")
            fh.write("#   on ground THAT region (or an ancestor) owns, or the player warps into a kick.\n")
            fh.write("# Calibrated against the in-game Charo's measurement (76841 -> 6840000, 2026-07-15).\n")
            fh.write("grace_flag\tground_buckets\tsource\ttile\n")
            for f, b, s, t in rows:
                fh.write("%d\t%s\t%s\t%s\n" % (f, b, s, t))
        print("emitted %s (%d rows). Commit it TOGETHER with any region_groups.py fix it implies."
              % (OUT, len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
