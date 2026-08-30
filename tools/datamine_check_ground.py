#!/usr/bin/env python3
r"""datamine_check_ground.py -- derive, per CHECK, the PLAY-REGION GROUND it stands on.

WHY THIS EXISTS (#523, bobler 2026-08-10)
-----------------------------------------
A check's region and the in-game kick are decided in two id spaces joined only by hand
(gen_data.py:381). The check side falls through curated -> the tile's own grace -> PlayRegionParam's
row for the tile -> **nearest grace tile**, and that last step is a guess nothing marks as one.
`tools/triage_check_region_ambiguity.py` measures it on main: of 1452 overworld checks, **431 (29.7%)
are that hop** and 5 are outright conflicts -- 436 across 115 tiles with no first-hand evidence.

A boss standing on Shadow Keep's measured ground (69300 -- the kick said unlocked, correctly) handed
a player 28 checks labelled Scadu Altus, a region whose Lock he did not hold. Only 2 of the 28 sat on
the trigger's own tile, so relabelling tiles fixes the symptom at 7% and leaves the class intact.

THE DERIVATION IS ALREADY BUILT AND CALIBRATED
----------------------------------------------
`datamine_grace_ground.py` point-in-volume tests a GRACE's spawn against every witchy'd MSB
`Region/PlayArea` volume. Those volumes carry `<PlayRegionID>` -- the exact runtime id the client's
kick-watch reads -- and its world transform (world = tile*256 + local, box containment by +yaw) is
calibrated against a real measurement: grace 76841's in-game ground 6840000 from the Charo's kick log
(2026-07-15) reproduces exactly.

`item_grace_coords.tsv` already carries map-local XYZ for **5295 checks** (against 421 graces), and
392 of the 436 triage rows have one. This tool points the same machinery at those rows. It answers in
the KICK's id space, from geometry, instead of hopping to a neighbouring tile's grace.

🛑 WHAT THIS IS NOT. It does not decide a check's REGION and nothing consumes it yet. It emits the
ground and, with --triage, the DISAGREEMENTS against the shipped label. A disagreement is a question
for a human, not a fix: a tile legitimately straddles regions, and `region_overrides.tsv` is where the
human answer belongs (with its reason) so a later regen cannot silently delete it.

FIRST REAL RUN, 2026-08-10 (Alaric, Windows, full artifacts):
    PlayArea volumes: 497 (m60+m61)
    checks: 5295 with coords, 3525 with a derived ground, 1770 underivable
66.6% derived, which is in line with grace_ground's own 293/421 (69.6%) on the same volumes -- the
underivable third is ground the MSBs simply do not carve, not a failure of the join. MIN_DERIVED
below is pinned AT that measured count.

Run:  python3 tools/datamine_check_ground.py                 # report
      python3 tools/datamine_check_ground.py --triage        # + disagreements vs the shipped label
      python3 tools/datamine_check_ground.py --emit          # + greenfield/check_ground.tsv
"""
import argparse
import ast
import csv
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
GF = os.path.join(REPO, "greenfield")
COORDS = os.path.join(GF, "item_grace_coords.tsv")
TRIAGE = os.path.join(GF, "check_region_triage.tsv")
OUT = os.path.join(GF, "check_ground.tsv")
MIN_TRIAGE_ROWS = 456  # measured from the complete tracked table on 2026-08-30 (#531)

sys.path.insert(0, HERE)
from datamine_grace_ground import (                      # noqa: E402  the calibrated machinery
    SEAM_SLACK, PRP, load_volumes, load_interior_volumes, _nearest_face,
)

# COVERAGE FLOOR, same discipline as arena_graces._ARENA_FLOOR and grace_ground.MIN_DERIVED: the
# derivation depends on the unpacked MSBs being PRESENT, so re-running without them must FAIL rather
# than quietly write a thinner table that still looks like an answer. Pinned AT the measured count
# from the 2026-08-10 full-artifact run (3525 of 5295). RAISE, NEVER LOWER -- a drop is a finding.
# If a param or MSB change legitimately drops one, lower it CONSCIOUSLY and say why in the commit.
MIN_DERIVED = 3525


def _play_region_groups():
    """{bucket: region} from region_groups.PLAY_REGION_GROUPS, parsed not imported."""
    src = open(os.path.join(GF, "region_groups.py"), encoding="utf-8").read()
    i = src.index("PLAY_REGION_GROUPS = {")
    j = src.index("\n}", i)
    body = re.sub(r"#[^\n]*", "", src[i + 21:j + 2]).replace("HUB", '"Roundtable Hold"')
    return {b: r for r, bs in ast.literal_eval(body).items() for b in bs}


def _tile_defaults():
    """{(area, tx, tz): {bucket}} and {interior map: {bucket}} from PlayRegionParam."""
    tile, interior = {60: {}, 61: {}}, {}
    for r in csv.DictReader(open(PRP, newline="", encoding="utf-8-sig")):
        i = int(r["ID"])
        b = i // 100
        a = int(r["areaNo"] or 0)
        if a in (60, 61):
            tile[a].setdefault((int(r["gridXNo"]), int(r["gridZNo"])), set()).add(b)
        if b and b < 60000:
            interior.setdefault("m%02d_%02d" % (b // 1000, (b // 10) % 100), set()).add(b)
    return tile, interior


def _check_coords():
    """[(flag, map_id, x, y, z)] for the `item` rows of item_grace_coords.tsv."""
    out = []
    for ln in open(COORDS, encoding="utf-8"):
        if not ln.startswith("item\t"):
            continue
        p = ln.rstrip("\n").split("\t")
        if len(p) < 6 or not p[1].isdigit():
            continue
        try:
            out.append((int(p[1]), p[2], float(p[3]), float(p[4]), float(p[5])))
        except ValueError:
            continue
    return out


def ground_of(flag, map_id, x, y, z, vols, tile_default, interior):
    """-> (sorted buckets, source). Mirrors datamine_grace_ground's two branches exactly."""
    m = re.match(r"m6([01])_(\d\d)_(\d\d)", map_id or "")
    if m:                                                   # OVERWORLD: world = tile*256 + local
        a = 60 + int(m.group(1))
        tx, tz = int(m.group(2)), int(m.group(3))
        wx, wz = tx * 256 + x, tz * 256 + z
        hits = [v for v in vols if v.area == a and v.contains(wx, y, wz)]
        if hits:
            return sorted({v.pr // 100 for v in hits}), "volume:" + hits[0].name
        bks = sorted(tile_default[a].get((tx, tz), set()))
        return bks, ("tile-default" if bks else "none")

    m = re.match(r"m(\d\d)_(\d\d)", map_id or "")           # INTERIOR: local == world
    if not m:
        return [], "none"
    mtile = "m%s_%s" % (m.group(1), m.group(2))
    ivols = load_interior_volumes(mtile)
    if ivols:
        hits = [v for v in ivols if v.contains(x, y, z)]
        if hits:
            return sorted({v.pr // 100 for v in hits}), "interior-vol:" + hits[0].name
        near = _nearest_face(ivols, x, y, z)
        if near and near[0] <= SEAM_SLACK:
            return [near[1].pr // 100], "interior-seam:%s@%.1fm" % (near[1].name, near[0])
    bks = sorted(interior.get(mtile, set()))
    return bks, ("interior-map" if bks else "none")


def _load_triage(path=TRIAGE):
    """Load the shipped-label oracle, refusing absence or silent truncation."""
    if not os.path.isfile(path):
        raise SystemExit("FATAL: %s missing -- --triage cannot answer without it." % path)
    shipped = {}
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader((line for line in fh if not line.startswith("#")), delimiter="\t"):
            shipped[int(r["flag"])] = r["region"]
    if len(shipped) < MIN_TRIAGE_ROWS:
        raise SystemExit(
            "FATAL: %s has only %d checks (floor %d, measured 2026-08-30) -- refusing a "
            "vacuous triage result." % (path, len(shipped), MIN_TRIAGE_ROWS)
        )
    return shipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit", action="store_true", help="write %s" % OUT)
    ap.add_argument("--triage", action="store_true",
                    help="report disagreements against the shipped region label")
    args = ap.parse_args()
    if not os.path.isfile(COORDS):
        raise SystemExit("FATAL: %s missing -- run tools/datamine_item_grace_coords.py (Windows)."
                         % COORDS)

    vols = load_volumes()
    print("PlayArea volumes: %d (m60+m61)" % len(vols))
    tile_default, interior = _tile_defaults()

    raw = []
    for flag, map_id, x, y, z in _check_coords():
        bks, src = ground_of(flag, map_id, x, y, z, vols, tile_default, interior)
        raw.append((flag, ";".join(map(str, bks)) or "-", src, map_id, (x, y, z)))
    raw.sort()

    derived_rows = sum(1 for r in raw if r[1] != "-")
    print("coord rows: %d, %d with a derived ground, %d underivable"
          % (len(raw), derived_rows, len(raw) - derived_rows))
    if derived_rows < MIN_DERIVED:
        raise SystemExit(
            "FATAL: only %d of %d coord rows derived a ground (floor %d, measured 2026-08-10) -- "
            "the MSBs are missing or truncated. Refusing to emit a table that would look like an "
            "answer." % (derived_rows, len(raw), MIN_DERIVED))

    # 🛑 COLLAPSE THE MSB VARIANTS. item_grace_coords carries 5295 rows for 4086 distinct checks:
    # 723 flags appear under both the _00 and _10 MSB variant of the same tile, at IDENTICAL
    # coordinates. Reporting those twice double-counts a single check (the 2026-08-10 run printed
    # 2046467010 twice). Collapse on (flag, tile, position) -- NOT on flag alone, because a check
    # genuinely present at two POSITIONS is a multi-site check (cf. check_maps.tsv) and its sites
    # must stay visible rather than being resolved to whichever sorted first.
    sites = {}
    for flag, bks, src, map_id, pos in raw:
        sites.setdefault((flag, map_id[:9], tuple(round(c, 2) for c in pos)), (bks, src, map_id))
    per_flag = {}
    for (flag, _tile, _pos), (bks, src, map_id) in sorted(sites.items()):
        e = per_flag.setdefault(flag, {"bk": set(), "src": src, "map": map_id, "n": 0})
        e["n"] += 1
        if bks != "-":
            e["bk"] |= set(bks.split(";"))
    rows = [(f, ";".join(sorted(e["bk"], key=int)) or "-", e["src"], e["map"], e["n"])
            for f, e in sorted(per_flag.items())]
    derived = sum(1 for r in rows if r[1] != "-")
    multi = sum(1 for r in rows if r[4] > 1)
    print("checks: %d distinct, %d with a derived ground, %d underivable, %d at >1 site"
          % (len(rows), derived, len(rows) - derived, multi))
    if args.triage:
        owner = _play_region_groups()
        shipped = _load_triage()
        agree = disagree = unknown = 0
        out = []
        for flag, bks, src, map_id, _n in rows:
            if flag not in shipped or bks == "-":
                continue
            regs = {owner.get(int(b)) for b in bks.split(";")} - {None}
            if not regs:
                unknown += 1
            elif regs == {shipped[flag]}:
                agree += 1
            else:
                disagree += 1
                out.append((flag, map_id, shipped[flag], ",".join(sorted(regs)), src))
        print("\nTRIAGE vs the shipped label (%d of the %d ambiguous checks have a ground):"
              % (agree + disagree + unknown, len(shipped)))
        print("  agree %d | DISAGREE %d | ground in an unowned bucket %d" % (agree, disagree, unknown))
        print("\n  flag        map           shipped -> geometry")
        for flag, map_id, was, now, src in sorted(out):
            print("  %-11d %-13s %s -> %s   [%s]" % (flag, map_id, was, now, src[:34]))
        print("\n  A disagreement is a QUESTION, not a fix: tiles straddle regions. Record the human "
              "answer in greenfield/region_overrides.tsv with its reason.")

    if args.emit:
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("# AUTO-GENERATED by tools/datamine_check_ground.py --emit -- DO NOT EDIT.\n")
            fh.write("# Per CHECK: the play_region BUCKET(s) of the ground it stands on (kick-watch id\n")
            fh.write("#   space, PlayRegionParam.ID // 100), by point-in-volume against MSB\n")
            fh.write("#   Region/PlayArea + PlayRegionParam tile defaults. '-' = underivable.\n")
            fh.write("# Same machinery as grace_ground.tsv, calibrated on the Charo's measurement\n")
            fh.write("#   (grace 76841 -> 6840000, in-game 2026-07-15).\n")
            fh.write("# NOT consumed by gen yet -- see #523. It answers 'where does this check STAND',\n")
            fh.write("#   which is a different question from 'which region owns it'.\n")
            fh.write("# one row per CHECK. sites = distinct physical positions (>1 = multi-site);\n")
            fh.write("#   the _00/_10 MSB variants of a tile are the SAME site and are collapsed.\n")
            fh.write("check_flag\tground_buckets\tsource\tmap_id\tsites\n")
            for flag, bks, src, map_id, n in rows:
                fh.write("%d\t%s\t%s\t%s\t%d\n" % (flag, bks, src, map_id, n))
        print("\nemitted %s (%d rows)" % (OUT, len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
