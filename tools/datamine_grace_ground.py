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
    Fallback where no volume contains the grace: the PlayRegionParam coordinate row(s) of the
    grace's own tile (the tile DEFAULT). If neither exists the ground is UNDERIVABLE ('-'):
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
    the first. A raw kick-watch line at 72102 (the play_region number) belongs in MEASURED_GROUND as
    engine corroboration; it was observed but not captured, so 72102 currently rests on geometry.

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
AR = os.path.join(REPO, "elden_ring_artifacts")
BWP = os.path.join(AR, "vanilla_er", "vanilla_er", "BonfireWarpParam.csv")
PRP = os.path.join(AR, "vanilla_er", "vanilla_er", "PlayRegionParam.csv")
MAPDIR = os.path.join(AR, "map")
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
}


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
                         "derivation needs them (WitchyBND the .msb.dcx first)." % MAPDIR)
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit", action="store_true", help="write %s" % OUT)
    args = ap.parse_args()
    for p in (BWP, PRP):
        if not os.path.isfile(p):
            raise SystemExit("FATAL: %s missing -- restore elden_ring_artifacts." % p)

    vols = load_volumes()
    print("PlayArea volumes: %d (m60+m61)" % len(vols))

    tile_default = {60: {}, 61: {}}
    interior = {}
    for r in csv.DictReader(open(PRP, newline="", encoding="utf-8-sig")):
        i = int(r["ID"])
        b = i // 100
        a = int(r["areaNo"] or 0)
        if a in (60, 61):
            tile_default[a].setdefault((int(r["gridXNo"]), int(r["gridZNo"])), set()).add(b)
        if b and b < 60000:
            interior.setdefault("m%02d_%02d" % (b // 1000, (b // 10) % 100), set()).add(b)

    rows = []
    for r in csv.DictReader(open(BWP, newline="", encoding="utf-8-sig")):
        try:
            f = int(r["eventflagId"] or 0)
        except ValueError:
            continue
        if not (71000 <= f <= 76999):
            continue
        a = int(r["areaNo"] or 0)
        if a in (60, 61):
            tx, tz = int(r["gridXNo"]), int(r["gridZNo"])
            wx = tx * 256 + float(r["posX"])
            wz = tz * 256 + float(r["posZ"])
            y = float(r["posY"])
            hits = [v for v in vols if v.area == a and v.contains(wx, y, wz)]
            bks = sorted({v.pr // 100 for v in hits})
            if bks:
                src = "volume:" + hits[0].name
            else:
                bks = sorted(tile_default[a].get((tx, tz), set()))
                src = "tile-default" if bks else "none"
            tile = "m%d_%02d_%02d" % (a, tx, tz)
        else:
            ent = str(r["bonfireEntityId"] or "")
            tile = "m%s_%s" % (ent[0:2], ent[2:4]) if len(ent) == 8 else "?"
            bks, src = [], "none"
            # Point-in-volume against the grace's OWN interior MSB first (the foreign-ground catch);
            # its position is local == world for an interior map, so no tile offset.
            try:
                px, py, pz = float(r["posX"]), float(r["posY"]), float(r["posZ"])
            except (TypeError, ValueError):
                px = None
            ivols = load_interior_volumes(tile) if px is not None else []
            if ivols and px is not None:
                hits = [v for v in ivols if v.contains(px, py, pz)]
                if hits:
                    bks = sorted({v.pr // 100 for v in hits})
                    src = "interior-vol:" + hits[0].name
                else:
                    near = _nearest_face(ivols, px, py, pz)   # gate/threshold seam -> nearest face
                    if near and near[0] <= SEAM_SLACK:
                        bks = [near[1].pr // 100]
                        src = "interior-seam:%s@%.1fm" % (near[1].name, near[0])
            if not bks:                                       # inside no volume, near none: fall back
                bks = sorted(interior.get(tile, set()))
                src = "interior-map" if bks else "none"
        if f in MEASURED_GROUND:
            mbks, msrc = MEASURED_GROUND[f]
            if bks and tuple(bks) != tuple(mbks):
                raise SystemExit(
                    "FATAL: derived ground %r for grace %d disagrees with the in-game measurement "
                    "%r (%s) -- the volume transform or the params changed; re-derive, do not "
                    "paper over." % (bks, f, list(mbks), msrc))
            if not bks:
                bks, src = list(mbks), msrc
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
