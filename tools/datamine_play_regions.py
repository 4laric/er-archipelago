#!/usr/bin/env python3
"""PlayRegionParam -> the play_region BUCKET table. The ground truth for kick-watch geometry.

WHY THIS EXISTS
---------------
`region_groups.py` sourced its buckets from `BonfireWarpParam.bonfireSubCategoryId`, on the written
claim that it "equals the runtime play_region_id (verified against every empirically captured id)".
It does not. It happens to coincide for the base overworld, and it is simply a different number in the
DLC:

    Gravesite:  bonfireSubCategoryId = 6800
                runtime play_region  = 6800000   ->  bucket (pr / 100) = 68000

The client compares `play_region_id / 100` against those buckets, so every DLC bucket missed. Three
things failed at once, none of them loudly: the DLC region KICK never fired (you could walk into a
sealed DLC region and loot it), the Scadutree blessing FLOOR never matched, and DLC enemy scaling sat
at its floor tier. All three are "correct behaviour on absent data".

**`PlayRegionParam` is the authority.** Its row IDs ARE the play_region ids -- that is what the game
puts in `WorldChrMan.main_player.play_region_id`. So:

    bucket = PlayRegionParam.ID // 100

and a bucket belongs to whichever apworld region owns the checks standing on its ground.

ATTRIBUTION -- two geometries, never conflated:

  * OVERWORLD buckets (60000-65999 base m60, 68000-69999 DLC m61): the rows' areaNo/gridXNo/gridZNo
    ARE the tiles the player stands on. Attribute from the apworld checks on those tiles.
  * INTERIOR buckets (everything else): the rows' coordinates are the dungeon's WARP/ENTRY point out
    on the OVERWORLD -- attributing from them names the NEIGHBOUR (it called Leyndell "Altus", Raya
    Lucaria "Liurnia", and the tutorial chapel "Gravesite"). The bucket id itself encodes the map
    exactly (11000 -> m11_00, 30030 -> m30_03), so decode it and join on the map instead.
    An overworld bucket with no usable coordinate rows is reported UNATTRIBUTED -- it must never
    fall through to the interior decode (m6X_YY keys exist as maps, so that fallthrough can invent
    a confident wrong region).

The check-side join keys on the acquisition FLAG, never the ap_id (ap-ids are positional and have
been renumbered; a zero-overlap ap_id join "succeeds" with an empty result). Rows whose map column
is PENDING or a coarse LOD tile still vote: the flag itself encodes the fine tile (same convention
as gen_data._recover_tile), and that decode is re-validated against the real map column on every
run. Rows where the two sources DISAGREE are contested and do not vote at all.

This tool DERIVES and REPORTS; it does not rewrite region_groups.py. `--emit` writes the measured
bucket universe to greenfield/play_region_buckets.tsv -- a TRACKED artifact, so CI (which has no
game data) can assert region_groups.py against the real universe
(greenfield/eldenring/tests/test_gf_play_region_buckets.py).

Usage:
    python tools/datamine_play_regions.py             # report + diff against region_groups.py
    python tools/datamine_play_regions.py --emit      # also write greenfield/play_region_buckets.tsv
    python tools/datamine_play_regions.py --param P   # read PlayRegionParam.csv from P
    (--write stays refused on purpose: a table this load-bearing is edited by a human reading the
     report, not rewritten by the tool that produced it.)
"""
from __future__ import annotations

import argparse
import collections
import csv
import importlib.util
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AR = os.path.join(REPO, "elden_ring_artifacts")
PARAM = os.path.join(AR, "vanilla_er", "vanilla_er", "PlayRegionParam.csv")
ARTIFACT = os.path.join(REPO, "greenfield", "play_region_buckets.tsv")

# PlayRegionParam column names (read by NAME, never by index -- the whole bug upstream of this tool was
# a value read out of the wrong column).
C_ID, C_AREA, C_GX, C_GZ = "ID", "areaNo", "gridXNo", "gridZNo"

# The game defines ~134 buckets. Far fewer means a truncated/filtered CSV, and reporting off one
# would call real buckets phantom -- refuse instead.
MIN_BUCKETS = 100
# Fraction of region_map.csv's flag-carrying rows that must resolve to a data.py region. The ap_id
# renumbering failure mode is ~0%; healthy is ~93%. Below this the join key has drifted again.
MIN_FLAG_MATCH = 0.80
# Absolute floor of rows that actually cast a geometry vote (healthy is ~4000).
MIN_VOTES = 2000
# Flag-decode self-validation: of the rows carrying BOTH a fine map column and a decodable flag,
# this fraction must agree (measured 2026-07-13: 2333/2363 = 98.7%; disagreements are contested
# rows, listed and excluded from voting).
MIN_DECODE_AGREE = 0.95


def fail(msg):
    sys.exit("datamine_play_regions: FATAL: %s" % msg)


def load_module(path, name):
    if not os.path.isfile(path):
        fail("%s not found" % path)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def bucket_kind(b):
    """The two overworld bands are closed intervals of fact, not a prefix heuristic: 66000-67999 is
    NEITHER band, and a bucket there (or anywhere unexpected) is reported unknown-band rather than
    guessed at."""
    if 60000 <= b <= 65999:
        return "overworld-base"      # m60
    if 68000 <= b <= 69999:
        return "overworld-dlc"       # m61
    if 66000 <= b <= 67999:
        return "unknown-band"
    return "interior"


def interior_map(b):
    """An interior bucket encodes its map exactly: 11000 -> m11_00, 30030 -> m30_03, 21020 -> m21_02."""
    return "m%02d_%02d" % (b // 1000, (b % 1000) // 10)


def flag_tile(flag):
    """Acquisition flag -> the tile/map it encodes (same digit conventions as gen_data._recover_tile;
    re-validated against the map column on every run, see load_votes). Overworld -> 3-part tile,
    interior -> 2-part map, None when the flag encodes no tile (6-digit entity flags etc.)."""
    s = str(flag)
    if len(s) == 10 and s[0] == "1" and s[1] in "01":
        return "m" + ("60" if s[1] == "0" else "61") + "_" + s[2:4] + "_" + s[4:6]
    if len(s) == 10 and s[:2] == "20":                    # DLC overworld flag 20AABBLLLL -> m61_AA_BB
        return "m61_" + s[2:4] + "_" + s[4:6]
    if len(s) == 8 and 10 <= int(s[0:2]) < 60:            # interior AABB7LLL -> mAA_BB (never m60/m61)
        return "m" + s[0:2] + "_" + s[2:4]
    return None


def load_play_regions(param):
    """{bucket: set((areaNo, tile3))} from PlayRegionParam. Rows with no coordinates still define a
    bucket. Hard-fails on a missing/renamed column or a degenerate row count -- silence here used to
    read as 'the game has 0 buckets'."""
    if not os.path.isfile(param):
        fail("PlayRegionParam not found: %s\n"
             "This tool needs the game-data artifacts; it cannot run in CI." % param)
    buckets = collections.defaultdict(set)
    seen = bad_id = coord_rows = 0
    with open(param, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        missing_cols = [c for c in (C_ID, C_AREA, C_GX, C_GZ) if c not in (rd.fieldnames or [])]
        if missing_cols:
            fail("PlayRegionParam.csv lacks column(s) %s -- header is %r. A renamed column must "
                 "fail HERE, not read as empty data downstream." % (missing_cols, rd.fieldnames))
        for row in rd:
            try:
                rid = int(row[C_ID])
            except (TypeError, ValueError):
                bad_id += 1
                continue
            seen += 1
            bucket = rid // 100
            try:
                a, x, z = int(row[C_AREA]), int(row[C_GX]), int(row[C_GZ])
            except (TypeError, ValueError):
                a = 0
            if a:
                coord_rows += 1
                buckets[bucket].add((a, "m%02d_%02d_%02d" % (a, x, z)))
            else:
                buckets[bucket]  # bucket exists, no coordinates on this row
    if seen == 0:
        fail("PlayRegionParam.csv parsed to ZERO rows (%d had a non-integer ID)." % bad_id)
    if bad_id:
        print("  (note: %d rows had a non-integer ID and were skipped)" % bad_id)
    if len(buckets) < MIN_BUCKETS:
        fail("only %d buckets parsed; the game defines ~134. Truncated or filtered CSV -- a report "
             "off this would call real buckets phantom." % len(buckets))
    if coord_rows == 0:
        fail("no row carried coordinates: %s/%s/%s parsed but always empty. Overworld attribution "
             "would silently produce nothing." % (C_AREA, C_GX, C_GZ))
    print("PlayRegionParam: %d rows (%d with coordinates) -> %d distinct play_region buckets"
          % (seen, coord_rows, len(buckets)))
    return buckets


def load_votes():
    """Check geometry votes, keyed by the acquisition FLAG (the only join key that survives ap_id
    renumbering). Returns (votes_ow {tile3: Counter(region)}, votes_int {mapAA_BB: Counter(region)},
    data module). Every silent-degradation channel measured here hard-fails below its floor."""
    # data.py is generated and imports nothing: load it BY PATH. Importing the package would pull in
    # Archipelago (eldenring/__init__.py -> core.py -> BaseClasses).
    data = load_module(os.path.join(REPO, "greenfield", "eldenring", "data.py"), "_gf_data")

    flag_region = {}
    for region, locs in data.LOCATIONS.items():
        for entry in locs:
            if len(entry) < 3:
                fail("data.py LOCATIONS entry shape changed (%r) -- flag is expected at index 2."
                     % (entry,))
            flag = entry[2]
            if flag:
                f = int(flag)
                if f in flag_region and flag_region[f] != region:
                    fail("flag %d claimed by two regions (%r, %r) -- the flag key is no longer "
                         "unique and every join on it is suspect." % (f, flag_region[f], region))
                flag_region[f] = region

    votes_ow = collections.defaultdict(collections.Counter)
    votes_int = collections.defaultdict(collections.Counter)
    n_rows = n_matched = n_voted = n_notile = 0
    agree = 0
    contested = []
    with open(os.path.join(REPO, "greenfield", "region_map.csv"), encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            f = (row.get("flag") or "").strip()
            if not f.isdigit():
                continue
            n_rows += 1
            reg = flag_region.get(int(f))
            if not reg:
                continue
            n_matched += 1
            # Map-column tile: only a FINE tile counts (4th segment 00). A coarse LOD index like
            # m60_10_09_02 is a different coordinate space and must never become a tile key.
            m = row.get("map") or ""
            parts = m.split("_")
            fine = None
            if m.startswith("m") and len(parts) >= 4 and parts[3] == "00":
                fine = "_".join(parts[:3])
                if not fine.startswith(("m60_", "m61_")):
                    fine = "_".join(parts[:2])            # interiors key on the map, not the tile
            dec = flag_tile(int(f))
            if fine and dec:
                if fine == dec:
                    agree += 1
                else:
                    contested.append((m, f, dec, reg))    # two sources, two answers: nobody votes
                    continue
            tile = dec or fine
            if not tile:
                n_notile += 1
                continue
            n_voted += 1
            if tile.startswith(("m60_", "m61_")):
                votes_ow[tile][reg] += 1
            else:
                votes_int[tile][reg] += 1

    if n_rows == 0:
        fail("region_map.csv yielded no flag-carrying rows at all.")
    if n_matched / n_rows < MIN_FLAG_MATCH:
        fail("only %d/%d region_map.csv flags resolve to a data.py region (%.0f%%; healthy ~93%%). "
             "The join key has drifted again -- refusing to vote on a sliver and call it geometry."
             % (n_matched, n_rows, 100.0 * n_matched / n_rows))
    both = agree + len(contested)
    if both and agree / both < MIN_DECODE_AGREE:
        fail("flag-tile decode agrees with the map column on only %d/%d rows -- the decode "
             "convention has drifted from gen_data._recover_tile; fix that before trusting any "
             "flag-recovered vote." % (agree, both))
    if n_voted < MIN_VOTES:
        fail("only %d rows cast a geometry vote (healthy ~4000). Too sparse to attribute buckets "
             "honestly." % n_voted)

    print("tile->region: %d/%d rows matched a region; %d voted (%d overworld tiles, %d interior "
          "maps); %d carried no tile; %d contested (map column vs flag decode) and excluded:"
          % (n_matched, n_rows, n_voted, len(votes_ow), len(votes_int), n_notile, len(contested)))
    for m, f, dec, reg in contested[:20]:
        print("    contested: map=%s flag=%s decodes to %s (region %r)" % (m, f, dec, reg))
    if len(contested) > 20:
        print("    ... and %d more" % (len(contested) - 20))
    return votes_ow, votes_int, data


def current_groups():
    """{bucket: region} from THE spine, greenfield/region_groups.py -- imported by path (it imports
    nothing), exactly like tools/datamine_dungeon_regions.py does. The previous regex parser here
    produced two of this tool's five wrong answers (inside-out parse; quote-class truncation of
    "Charo's"); importing the module makes that whole class unrepresentable."""
    rg = load_module(os.path.join(REPO, "greenfield", "region_groups.py"), "_gf_region_groups")
    cur = {}
    for region, pids in rg.REGION_GROUPS.items():
        for p in pids:
            if p in cur and cur[p] != region:
                fail("REGION_GROUPS assigns bucket %d to both %r and %r." % (p, cur[p], region))
            cur[int(p)] = region
    if not cur:
        fail("REGION_GROUPS is empty.")
    return rg, cur


def emit_artifact(path, buckets, seen_note):
    lines = [
        "# AUTO-GENERATED by tools/datamine_play_regions.py --emit -- DO NOT EDIT.",
        "# bucket = PlayRegionParam.ID // 100: the value the client's kick-watch compares",
        "#   play_region_id / 100 against. This is the game's COMPLETE bucket universe.",
        "# TRACKED so CI (which has no game artifacts) can assert greenfield/region_groups.py",
        "#   against it: greenfield/eldenring/tests/test_gf_play_region_buckets.py.",
        "# Regenerate after any game patch, and commit TOGETHER with the region_groups.py changes",
        "#   it implies -- the test fails on any mismatch between the two.",
        "# geometry: interiors = the map the bucket id encodes; overworld = the bucket's own",
        "#   coordinate tiles (an interior row's coordinates are its overworld WARP point -- never",
        "#   emitted, they are the trap this tool exists to avoid).",
        "# source: PlayRegionParam.csv, %s." % seen_note,
        "bucket\tkind\tgeometry",
    ]
    for b in sorted(buckets):
        kind = bucket_kind(b)
        if kind == "interior":
            geo = interior_map(b)
        elif kind == "unknown-band":
            geo = ";".join(sorted(t for (_a, t) in buckets[b])) or "-"
        else:
            want = 60 if kind == "overworld-base" else 61
            own = sorted(t for (a, t) in buckets[b] if a == want)
            geo = ";".join(own) if own else "-"
        lines.append("%d\t%s\t%s" % (b, kind, geo))
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print()
    print("emitted %s (%d buckets)." % (path, len(buckets)))
    print("Commit it TOGETHER with the region_groups.py fix it implies;")
    print("test_gf_play_region_buckets.py fails on any mismatch between the two.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--param", default=PARAM, help="path to PlayRegionParam.csv")
    ap.add_argument("--emit", nargs="?", const=ARTIFACT, default=None, metavar="PATH",
                    help="write the measured bucket universe (default %s)" % ARTIFACT)
    ap.add_argument("--write", action="store_true", help="rewrite region_groups.py (refused)")
    args = ap.parse_args()

    if args.write:
        fail("--write is refused on purpose: this table is edited by a human reading the report "
             "below, not rewritten by the tool that produced it. Run without --write, read the "
             "diff, then edit greenfield/region_groups.py by hand.")

    buckets = load_play_regions(args.param)
    votes_ow, votes_int, data = load_votes()
    rg, cur = current_groups()

    derived = {}                 # bucket -> (region, winner_votes, total_votes)
    lowconf = []
    unattributed = []
    for bucket in sorted(buckets):
        kind = bucket_kind(bucket)
        agg = collections.Counter()
        if kind in ("overworld-base", "overworld-dlc"):
            want = 60 if kind == "overworld-base" else 61
            own = [t for (a, t) in buckets[bucket] if a == want]
            stray = sorted(t for (a, t) in buckets[bucket] if a and a != want)
            if stray:
                print("  NOTE: overworld bucket %d has coordinate rows outside its own map (%s) -- "
                      "ignored, they do not vote." % (bucket, stray))
            for t in own:
                agg += votes_ow.get(t, collections.Counter())
        elif kind == "interior":
            # Raw check counts on the DECODED map -- never the rows' coordinates (those are the
            # warp/entry point out on the overworld and would name the neighbour).
            agg = collections.Counter(votes_int.get(interior_map(bucket), {}))
        # unknown-band: no attribution path; falls through to unattributed.
        if agg:
            (region, n), total = agg.most_common(1)[0], sum(agg.values())
            derived[bucket] = (region, n, total)
            runner = agg.most_common(2)[1][1] if len(agg) > 1 else 0
            if n < 3 or (runner and n < 2 * runner):
                lowconf.append((bucket, region, dict(agg)))
        else:
            unattributed.append((bucket, kind, sorted(t for (_a, t) in buckets[bucket])))

    print()
    print("== BUCKETS THE GAME HAS THAT WE DO NOT (kick never fires here) ==")
    missing = [b for b in derived if b not in cur]
    for b in sorted(missing):
        r, n, tot = derived[b]
        print("   %7d  -> %-30r (%d/%d votes)" % (b, r, n, tot))
    if not missing:
        print("   (none)")

    print()
    print("== BUCKETS WE CLAIM THAT THE GAME DOES NOT HAVE (phantoms, inert) ==")
    phantom = [b for b in cur if b not in buckets]
    for b in sorted(phantom):
        print("   %7d  we say %r" % (b, cur[b]))
    if not phantom:
        print("   (none)")

    print()
    print("== BUCKETS WHERE WE DISAGREE ON THE REGION ==")
    disagree = [b for b in derived if b in cur and cur[b] != derived[b][0]]
    for b in sorted(disagree):
        r, n, tot = derived[b]
        print("   %7d  we say %-24r ->  checks say %r (%d/%d votes)" % (b, cur[b], r, n, tot))
    if not disagree:
        print("   (none)")

    if lowconf:
        print()
        print("== LOW-CONFIDENCE ATTRIBUTIONS (under 3 votes, or margin under 2:1 -- review) ==")
        for b, r, agg in lowconf:
            print("   %7d  -> %-30r votes=%r" % (b, r, agg))

    if unattributed:
        print()
        print("== BUCKETS WITH NO ATTRIBUTABLE CHECK -- NEEDS A HUMAN ==")
        print("   (real buckets the game HAS. Omitting one from REGION_GROUPS means the KICK has no")
        print("    opinion there, i.e. that ground is silently PERMISSIVE. Assign each to a region")
        print("    or to region_groups.UNASSIGNED_BUCKETS with a reason.)")
        for b, kind, ts in unattributed:
            hint = interior_map(b) if kind == "interior" else (";".join(ts) or "(no coordinate rows)")
            was = cur.get(b)
            print("   %7d  %-14s %s%s" % (b, kind, hint,
                                          ("   we currently say %r" % was) if was else ""))

    # A region with NO derived bucket is the Raya-Lucaria failure mode: it simply vanishes from the
    # proposal and nothing looks wrong. Name them, with their own check footprint so a human can
    # match them against the unattributed buckets above.
    derived_regions = {r for (r, _n, _t) in derived.values()}
    all_regions = set(data.REGIONS) | {data.HUB}
    bucketless = sorted(all_regions - derived_regions)
    if bucketless:
        print()
        print("== REGIONS WITH NO DERIVED BUCKET (would be silently unenforceable) ==")
        for r in bucketless:
            ow = sorted(t for t, c in votes_ow.items() if r in c)
            it = sorted(m for m, c in votes_int.items() if r in c)
            print("   %-30r overworld tiles: %s" % (r, ";".join(ow) or "(none)"))
            print("   %30s  interior maps:  %s" % ("", ";".join(it) or "(none)"))

    print()
    print("summary: game has %d buckets; we list %d; %d missing, %d phantom, %d mis-assigned, "
          "%d unattributed, %d regions bucketless"
          % (len(buckets), len(cur), len(missing), len(phantom), len(disagree),
             len(unattributed), len(bucketless)))

    print()
    print("== PROPOSED REGION_GROUPS (measured; review before trusting) ==")
    by_region = collections.defaultdict(list)
    for b, (r, _n, _t) in derived.items():
        by_region[r].append(b)
    for r in sorted(by_region):
        print("    %-30r %s," % (r, tuple(sorted(by_region[r]))))

    if args.emit:
        emit_artifact(args.emit, buckets, "%d buckets" % len(buckets))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
