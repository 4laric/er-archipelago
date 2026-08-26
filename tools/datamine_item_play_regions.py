#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""datamine_item_play_regions.py -- the EXACT play-region answer for a check, per item coordinate.

WHY THIS EXISTS. 305 checks carry `(region unconfirmed)` because their region came from a
nearest-neighbour tile hop that CANNOT FAIL (CONTRIBUTING rule 1), and the two second opinions we
have -- a public wiki's placement (`tools/audit_region_second_opinion.py`) and the nearest
region-attributed grace (`tools/msb_region_vote.py`, 91.4% on a 2607-check control set) -- are
rankings, not rulings. The instrument that RULES already exists and is already calibrated against
two in-game kick measurements: the point-in-volume test against MSB `Region/PlayArea`, which reads
`<PlayRegionID>` -- the exact id the client's kick-watch reads at runtime. `datamine_grace_ground.py`
points it at the 421 warp graces. This tool points the SAME machinery at ITEM coordinates.

`docs/PLAYAREA-ITEM-SCAN.md` is the runbook; this file is its step 2. It runs on a box with the
extracted MSB corpus (CI has none), takes no network, reads no game install, and is deterministic.

NOTHING GEOMETRIC IS RE-IMPLEMENTED HERE. Everything is imported from its one owner:

    datamine_grace_ground.Vol / Vol.contains / _shape / _load_msb_playareas / load_volumes
                              / load_interior_volumes / _nearest_face / SEAM_SLACK
                              / MEASURED_GROUND / load_play_region_defaults
                              / grace_rows  THE calibration population: the BWP SPAWN position of
                              every warp grace, the point the kick-watch evaluates at warp-in --
                              never the grace asset coordinate in item_grace_coords.tsv
    overworld_fold.world_xz   THE LOD-aware overworld fold (issue #338 -- never a second one),
                              reached THROUGH datamine_grace_ground.derive_ground, which owns the
                              volume -> seam -> tile-default -> none ladder for BOTH tools
    msb_region_vote.load_coords   the item/grace coordinate reader, multi-placement aware

FOLD FIRST, TEST SECOND. `_load_msb_playareas` world-positions volumes as `tile*256 + local` and
is only ever handed fine-grid (`_00`) tiles, but ITEM rows are not all fine-grid: 725 of them are
3-field ids and some are authored on LOD1/LOD2 tiles, where the pitch is `256 << lod` plus a
`(pitch-256)/2` centring term. An unfolded LOD2 item lands hundreds of metres outside its own
volume and reads as a tile-default. `world_xz` is the single shared fold and doing it by hand here
is issue #338 all over again.

THE LABEL TILE IS NOT THE MSB TILE. Three Bestial Sanctum checks are labelled `m60_51_41` and
their coordinates are authored in `m60_51_43`. This scan is driven off `item_grace_coords.tsv`'s
own `map_id`, never off a check's label, so a cross-tile row answers from where it actually is.

THE ANSWER, per placement, in the order it is tried -- and the `source` column says WHICH answered,
because a row that cannot say how it was decided is not falsifiable:

    volume:NAME          a PlayArea volume CONTAINS the point (the ruling)
    interior-vol:NAME    the same, in an interior map's own MSB (world == local, no tile offset)
    seam:NAME@Nm         inside no volume but within SEAM_SLACK m of a volume FACE. The Shadow Keep
    interior-seam:NAME@Nm  Main Gate is why this exists: grace 72102 sits 3.6 m outside the Scadu
                         Altus column, inside no Keep volume, and the in-game kick REFUTES the
                         map default there. A seam is ground, not a miss.
    tile-default         no volume, no seam: the PlayRegionParam coordinate row(s) of the point's
    interior-map         OWN fine tile (recomputed from the FOLDED position, so a LOD row defaults
                         to the tile it really sits on, not the coarse tile it was authored in)
    none ('-')           none of the above. Engine-side tile defaults are not all expressed in
                         params and we refuse to guess. ABSENCE OF AN ANSWER IS NOT AN ANSWER.

OUTPUT: greenfield/item_play_regions.tsv -- `flag  map_id  play_region_ids  buckets  source`, one
row per PLACEMENT (a flag placed in two maps gets two rows; `msb_region_vote.load_coords` keeps
both, and collapsing them here would pick a winner by file order). Bucket = ID // 100, the
kick-watch id space, the space `REGION_PLAY_IDS` is written in.

    python tools/datamine_item_play_regions.py                # report only
    python tools/datamine_item_play_regions.py --emit         # write the tsv
    python tools/datamine_item_play_regions.py --graces       # step 3: the CALIBRATION GATE

--graces runs this exact pipeline over the 421 warp graces out of BonfireWarpParam and DIFFS the
result against the committed `greenfield/grace_ground.tsv`, exiting NON-ZERO on a bucket
mismatch. Run it BEFORE believing a single item answer: a scan that cannot reproduce the table
that is calibrated against the two in-game measurements (76841 -> 6840000, 2026-07-15; 72102 ->
6900000/6900010, 2026-07-21) has not earned an opinion about items.

REFUSALS (both are the same lesson twice paid for: a partial census read as complete is worse than
no census). Neither is bypassable except by `--force`, which exists to say "the shrink is
deliberate" and MUST NOT be used to make a red run green:
  * a DEGENERATE scan -- fewer than VOL_FLOOR PlayArea volumes means a partial witchy export, and
    every item in the unscanned tiles would silently read as a tile-default;
  * a SHRINKING table -- fewer derived rows than the committed tsv (or, before there is one,
    fewer than MIN_DERIVED_ABS).
"""
import argparse
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.dirname(HERE)
sys.path.insert(0, HERE)

import artifacts_root                        # noqa: E402  -- THE --path argument, not a copy
import datamine_grace_ground as gg          # noqa: E402  -- THE volume machinery, not a copy of it
import msb_region_vote as mrv               # noqa: E402  -- THE coordinate reader

OUT = os.path.join(REPO, "greenfield", "item_play_regions.tsv")
GROUND = os.path.join(REPO, "greenfield", "grace_ground.tsv")

# MEASURED, not guessed (the 1000 that stood here was a guess, and it FATAL'd a complete corpus):
# Alaric's box, 2026-08-26 -- a comprehensive witchy export (829 m60 + 386 m61 msb-dcx dirs, 1,346
# total) yields 497 PlayArea volumes. PlayAreas exist where play-region boundaries run, not on
# every tile. A partial export is still the hazard -- missing tiles answer `tile-default`, which is
# a plausible-looking row -- but the real arbiter is `--graces`: a partial volume set cannot
# reproduce grace_ground.tsv. Floor set below the measured full-export count and far above a
# handful of tiles.
VOL_FLOOR = 400

# The floor for the emitted table. `grace_ground.tsv`'s MIN_DERIVED = 200 is a measured pin against
# ITS 421-row population; there is no committed item table to measure against on the FIRST run, so
# the floor is two-part: never fewer than the committed table already has (the ratchet), and on the
# first run never fewer than this absolute minimum. 2000 is deliberately conservative against the
# ~3,966 coord-bearing flags: the overworld is the large majority of them and a full export derives
# most, so a run that derives under 2000 is a broken corpus, not a hard seed. RAISE IT to the
# measured count once the first real run has one -- like MIN_DERIVED next door, raise, never lower.
MIN_DERIVED_ABS = 2000


# THE ladder itself, for the same reason: `datamine_grace_ground.derive_ground` is the one owner
# of volume -> seam -> tile-default -> none, and BOTH tools call it. Aliased (not wrapped) so the
# name `derive` keeps working for this module's callers and tests. Before 2026-08-26 this file held
# its own copy that differed from grace_ground's outdoors -- that delta is what this alias kills.
derive = gg.derive_ground


def load_volumes_or_die(force=False):
    vols = gg.load_volumes()
    print("PlayArea volumes: %d (m60+m61)" % len(vols))
    if len(vols) < VOL_FLOOR and not force:
        raise SystemExit(
            "FATAL: only %d PlayArea volumes (floor %d) -- this is a PARTIAL witchy export and the "
            "scan is worthless: every item on an unscanned tile would answer 'tile-default', which "
            "looks like a result. WitchyBND the rest of map/*.msb.dcx. (--force overrides; do not "
            "use it to make a red run green.)" % (len(vols), VOL_FLOOR))
    return vols


def item_rows(repo, vols, tile_ids, interior_ids):
    """One row per PLACEMENT: (flag, map_id, ids, source). Deterministic ordering."""
    items, _graces = mrv.load_coords(repo)
    rows, seen = [], set()
    for flag, places in items.items():
        for (map_id, x, y, z) in places:
            if (flag, map_id) in seen:
                continue
            seen.add((flag, map_id))
            ids, src = derive(map_id, x, y, z, vols, tile_ids, interior_ids)
            rows.append((int(flag), map_id, ids, src))
    rows.sort(key=lambda r: (r[0], r[1]))
    return rows


def grace_rows(vols, tile_ids, interior_ids):
    """The calibration population -- `datamine_grace_ground.grace_rows`, verbatim.

    NOT a second reader of BonfireWarpParam. The gate's whole claim is that it reproduces
    `grace_ground.tsv`, and that claim is only about the ladder if both sides judge THE SAME
    POINT: the grace's BWP SPAWN position (`posX/posY/posZ`), the point the kick-watch evaluates
    at warp-in -- never the grace ASSET coordinate in `item_grace_coords.tsv`, which is metres
    away at some graces. This file used to hold its own copy of that loop, and the copies had
    already drifted (a grace whose spawn position does not parse was skipped here and emitted next
    door, so the gate never compared it). One generator, so the populations cannot differ.

    Returns (flag, map_id, ids, source): the tile column belongs to grace_ground's tsv, not here.
    """
    rows = [(f, map_id, ids, src)
            for f, map_id, _tile, ids, src in gg.grace_rows(vols, tile_ids, interior_ids)]
    rows.sort(key=lambda r: (r[0], r[1]))
    return rows


def read_ground(path):
    """grace_flag -> (buckets tuple, source) out of a committed grace_ground.tsv."""
    out = {}
    with open(path, encoding="utf-8-sig") as fh:
        body = [ln for ln in fh if not ln.startswith("#") and ln.strip()]
    for row in csv.DictReader(body, delimiter="\t"):
        bks = tuple(int(b) for b in row["ground_buckets"].split(";") if b.strip() and b != "-")
        out[int(row["grace_flag"])] = (bks, row.get("source", ""))
    return out


def run_graces(vols, tile_ids, interior_ids, ground_path):
    """Step 3, the calibration gate. Returns an exit code.

    Exits NON-ZERO on a BUCKET disagreement -- the bucket is the answer, and reproducing it is the
    whole claim. A SOURCE difference is reported but does not fail: this pipeline offers an
    overworld point a seam-snap before the tile default (the runbook's step-2 order) where
    `datamine_grace_ground` goes straight to the default, so a source delta is a finding to read,
    not a broken scan. A bucket delta means the geometry moved.
    """
    if not os.path.isfile(ground_path):
        raise SystemExit("FATAL: %s missing -- there is nothing to calibrate against." % ground_path)
    committed = read_ground(ground_path)
    rows = grace_rows(vols, tile_ids, interior_ids)
    bad, soft, missing = [], [], []
    for f, map_id, ids, src in rows:
        if f not in committed:
            missing.append(f)
            continue
        want_b, want_src = committed[f]
        got_b = tuple(sorted({i // 100 for i in ids}))
        if got_b != want_b:
            bad.append((f, map_id, list(want_b), list(got_b), want_src, src))
        elif src.split("@")[0] != want_src.split("@")[0] and not want_src.startswith("measured:"):
            soft.append((f, want_src, src))
    print("graces: %d derived here, %d in %s"
          % (len(rows), len(committed), os.path.basename(ground_path)))
    for f in missing:
        print("  NOT IN THE COMMITTED TABLE: grace %d" % f)
    for f, want_src, src in soft:
        print("  source delta (buckets AGREE): grace %d committed=%s here=%s" % (f, want_src, src))
    if bad:
        print("BUCKET MISMATCH on %d grace(s) -- this scan does NOT reproduce the calibrated table:"
              % len(bad))
        for f, map_id, want_b, got_b, want_src, src in bad[:40]:
            print("  grace %d (%s): committed %s (%s) vs here %s (%s)"
                  % (f, map_id, want_b, want_src, got_b, src))
        print("REFUSING to bless the item scan: fix the corpus or the transform first "
              "(docs/PLAYAREA-ITEM-SCAN.md step 3).")
        return 1
    if missing:
        print("REFUSING: the grace population moved; re-run tools/datamine_grace_ground.py --emit.")
        return 1
    print("CALIBRATION OK -- every grace reproduces its committed ground bucket. "
          "The item answers can be trusted to the same standard.")
    return 0


def emit(path, rows):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# AUTO-GENERATED by tools/datamine_item_play_regions.py --emit -- DO NOT EDIT.\n")
        fh.write("# Per ITEM PLACEMENT: the play_region id(s) of the ground the pickup stands on,\n")
        fh.write("#   read from MSB Region/PlayArea <PlayRegionID> by point-in-volume test -- the\n")
        fh.write("#   exact id the client's kick-watch reads. buckets = ID // 100.\n")
        fh.write("# One row per placement: a flag placed in two maps has two rows (442 flags are).\n")
        fh.write("# source: volume:/interior-vol: = a volume CONTAINS it (the ruling); seam:/\n")
        fh.write("#   interior-seam: = within %.0f m of a volume face; tile-default/interior-map =\n"
                 % gg.SEAM_SLACK)
        fh.write("#   the PlayRegionParam default for its own tile; '-' = no answer, and absence\n")
        fh.write("#   of an answer is NOT evidence about the region.\n")
        fh.write("# Calibrated by --graces against greenfield/grace_ground.tsv "
                 "(docs/PLAYAREA-ITEM-SCAN.md).\n")
        fh.write("flag\tmap_id\tplay_region_ids\tbuckets\tsource\n")
        for f, map_id, ids, src in rows:
            fh.write("%d\t%s\t%s\t%s\t%s\n"
                     % (f, map_id, ";".join(map(str, ids)) or "-",
                        ";".join(str(i) for i in sorted({j // 100 for j in ids})) or "-", src))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--emit", action="store_true", help="write the tsv (default: report only)")
    ap.add_argument("--out", default=OUT,
                    help="output tsv (default: greenfield/item_play_regions.tsv)")
    artifacts_root.add_path_argument(ap)
    ap.add_argument("--coords-repo", metavar="DIR", default=None,
                    help="read greenfield/item_grace_coords.tsv out of THIS checkout (default: this one)")
    ap.add_argument("--ground", default=GROUND,
                    help="the committed grace_ground.tsv that --graces calibrates against")
    ap.add_argument("--graces", action="store_true",
                    help="RUNBOOK STEP 3: run this pipeline over the warp graces and diff against "
                         "grace_ground.tsv instead of scanning items. Non-zero on a bucket "
                         "mismatch. Run it BEFORE trusting any item answer.")
    ap.add_argument("--force", action="store_true",
                    help="emit even when the scan is DEGENERATE (a partial witchy export) or would "
                         "SHRINK the committed table. This flag exists to say a shrink is "
                         "deliberate -- passing it to turn a red run green destroys the ground "
                         "truth the gate is made of.")
    args = ap.parse_args(argv)

    root = artifacts_root.resolve(args.path)
    if root:
        gg._set_artifacts_root(root)
    if not os.path.isfile(gg.PRP):
        raise SystemExit("FATAL: %s missing -- restore elden_ring_artifacts." % gg.PRP)

    vols = load_volumes_or_die(args.force)
    tile_ids, interior_ids = gg.load_play_region_defaults()

    if args.graces:
        if not os.path.isfile(gg.BWP):
            raise SystemExit("FATAL: %s missing -- restore elden_ring_artifacts." % gg.BWP)
        return run_graces(vols, tile_ids, interior_ids, args.ground)

    rows = item_rows(args.coords_repo or REPO, vols, tile_ids, interior_ids)
    derived = sum(1 for _f, _m, ids, _s in rows if ids)
    by_src = {}
    for _f, _m, _ids, s in rows:
        k = s.split(":")[0]
        by_src[k] = by_src.get(k, 0) + 1
    print("item placements: %d total, %d with a play_region, %d unanswered"
          % (len(rows), derived, len(rows) - derived))
    print("  by source: " + ", ".join("%s=%d" % kv for kv in sorted(by_src.items())))

    floor = MIN_DERIVED_ABS
    if os.path.isfile(args.out):
        with open(args.out, encoding="utf-8") as fh:
            prior = sum(1 for ln in fh
                        if not ln.startswith(("#", "flag\t")) and ln.strip()
                        and ln.split("\t")[2].strip() not in ("", "-"))
        floor = max(floor, prior)
    if derived < floor and not args.force:
        raise SystemExit(
            "FATAL: only %d placements derived a play_region (floor %d -- the committed table's own "
            "count, or %d on a first run). A ground-truth table that SHRINKS and writes anyway is "
            "how a gate goes blind. Fix the corpus (--force only if the shrink is deliberate)."
            % (derived, floor, MIN_DERIVED_ABS))

    if args.emit:
        emit(args.out, rows)
        print("emitted %s (%d rows)." % (args.out, len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
