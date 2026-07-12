#!/usr/bin/env python3
r"""regen_grace_tables.py -- rebuild elden_ring_artifacts/grace_flags.tsv and
grace_region_map_<stamp>.tsv from BonfireWarpParam.csv.

WHY: both are DERIVED tables that live in the gitignored elden_ring_artifacts/, so a
`git clean -xdf` deletes them and there is no copy in git. gen_data.py cannot run without
them (they supply ANCHOR: the overworld tile -> play_region join). Everything they contain
comes from BonfireWarpParam, so losing them is annoying, not fatal.

  grace_flags.tsv          warpUnlockFlag <- eventflagId
                           mapTile        <- bonfireEntityId, decoded
  grace_region_map_*.tsv   grace_flag     <- eventflagId
                           play_region_id <- bonfireSubCategoryId   (the KICK area id)

bonfireEntityId decodes to a map tile the same way an item-lot flag does:
  10 digits, leading 1  ->  m60_XX_YY / m61_XX_YY   (overworld tile; s[1] picks base/DLC)
   8 digits             ->  mAA_BB                  (interior map)

ACCEPTANCE TEST (do not skip): after rebuilding, run gen_data.py and diff the generated
modules against git. If the rebuild is faithful they are BYTE-IDENTICAL. If they are not,
this script is wrong -- do not "fix" gen_data to match it.

    python tools/regen_grace_tables.py
    python greenfield/gen_data.py && git diff --stat greenfield/eldenring/
"""
import csv, os, argparse, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.dirname(HERE)
AR   = os.path.join(REPO, "elden_ring_artifacts")
BWP  = os.path.join(AR, "vanilla_er", "vanilla_er", "BonfireWarpParam.csv")


def decode_tile(entity_id, area_no, grid_x, grid_z):
    """-> map tile, or None.

    OVERWORLD (areaNo 60/61): use areaNo/gridXNo/gridZNo -- they ARE the tile, authoritatively.
    Decoding the entity id also works but has two encodings (base `1 0 AA BB ....`, DLC
    `2 0 AA BB ....`), and an earlier version of this script knew only the first, silently dropping
    all 60 DLC graces. The grid columns cannot drift like that.

    INTERIOR: no grid columns, so decode the 8-digit entity id -> mAA_BB.
    """
    if area_no in (60, 61):
        return "m%d_%02d_%02d" % (area_no, grid_x, grid_z)
    s = str(entity_id)
    if len(s) == 8:
        return "m%s_%s" % (s[0:2], s[2:4])
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="print counts, write nothing")
    a = ap.parse_args()
    if not os.path.isfile(BWP):
        raise SystemExit("FATAL: %s missing -- restore elden_ring_artifacts from your ER install" % BWP)

    graces, regions = [], []
    with open(BWP, newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            try:
                flag = int(r["eventflagId"] or 0)
                ent  = int(r["bonfireEntityId"] or 0)
                pr   = int(r["bonfireSubCategoryId"] or 0)
                area = int(r["areaNo"] or 0)
                gx   = int(r["gridXNo"] or 0)
                gz   = int(r["gridZNo"] or 0)
            except (KeyError, ValueError):
                continue
            if flag <= 0 or ent <= 0:
                continue
            tile = decode_tile(ent, area, gx, gz)
            if tile:
                graces.append((flag, tile))
            regions.append((flag, pr))

    # gen_data rejects anything outside the 71000-76999 region/grace group at ingest; keep the
    # table faithful (emit everything) and let it do its own filtering, as it did before.
    print("BonfireWarpParam rows -> %d grace flags with a decodable tile, %d play_region rows"
          % (len(graces), len(regions)))
    print("  in the real-grace group (71000-76999): %d" % sum(1 for f, _t in graces if 71000 <= f <= 76999))
    if a.dry:
        return

    gp = os.path.join(AR, "grace_flags.tsv")
    with open(gp, "w", encoding="utf-8", newline="\n") as f:
        f.write("warpUnlockFlag\tmapTile\n")
        for flag, tile in sorted(graces):
            f.write("%d\t%s\n" % (flag, tile))
    print("wrote %s (%d rows)" % (gp, len(graces)))

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    rp = os.path.join(AR, "grace_region_map_%s.tsv" % stamp)
    with open(rp, "w", encoding="utf-8", newline="\n") as f:
        f.write("grace_flag\tplay_region_id\n")
        for flag, pr in sorted(regions):
            f.write("%d\t%d\n" % (flag, pr))
    print("wrote %s (%d rows)" % (rp, len(regions)))
    print("\nNOW VERIFY:  python greenfield/gen_data.py && git diff --stat greenfield/eldenring/")
    print("Faithful rebuild == generated modules byte-identical (stamp lines aside).")


if __name__ == "__main__":
    main()
