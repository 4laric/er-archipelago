"""Does a check STAND where its region says it does? -- the PlayRegion ground audit (issue #445).

WHY THIS EXISTS. A check's region decides two different things that nobody had ever made agree:

  1. whether the seed CREATES it -- `core._add_locations` walks `[HUB] + kept`, so a check in a kept
     region becomes an AP location and lands in `locationFlags`;
  2. whether the player can REACH it -- `er_logic::region_lock::kick_decision` compares the
     play_region bucket THE PLAYER IS STANDING IN against `areaLockFlags`, and ejects them from any
     bucket whose region is not kept.

(1) is derived from the check's flag / map / MSB attribution. (2) is derived from its POSITION. Where
those two disagree, a seed can ship a location it also forbids you to walk to: created, flag-polled,
counted on the tracker, and unreachable.

This is the same shape as the Golden Hippopotamus in #445 -- reward scripted in m21_00 (Shadow Keep),
fight standing on bucket 69000 (Scadu Altus) -- one level down, on ordinary checks instead of on a
sweep trigger. It was found while verifying that issue: 8 members of the Gravesite sweep turned out
to sit on Rauh Base ground.

THE JOIN, all four inputs committed (so this runs in the sandbox and in CI):

    data.LOCATIONS            check -> assigned region, check -> flag
    item_grace_coords.tsv     flag  -> map_id (the datamined position's map/tile)
    play_region_buckets.tsv   tile  -> play_region bucket(s)      [the game's own bucket universe]
    region_groups.py          bucket-> region                     [PLAY_REGION_GROUPS]

🛑 IT IS A LOWER BOUND, LOUDLY. Of 4916 checks, 3928 have a datamined coordinate at all and only
2451 land on a tile `play_region_buckets.tsv` has a row for. The remaining 2465 are NOT clean --
they are unmeasured, and `report()` prints that split every run rather than quoting a pass rate over
the subset it happened to resolve.

🛑 AND IT REFUSES TO GUESS. Bucket volumes are 3-D and this join is TILE-level, so a tile claimed by
two buckets in different regions is reported AMBIGUOUS, never resolved to the nearer/first/likelier
one. `tile_pr()` is the cautionary tale in CONTRIBUTING: a nearest-neighbour that never fails put
six checks in the wrong region and one of them cost a playtest.

Usage:  python3 tools/check_ground_regions.py [--repo PATH]
"""
import argparse
import csv
import importlib.util
import os
import sys
from collections import defaultdict

# Ground regions that are reachable WITHOUT being drawn by the region roll, so a check standing on
# them is not at risk. Each entry names its mechanism -- a benign class with no stated reason is how
# a real defect gets filed as noise.
BENIGN_GROUNDS = {
    "Roundtable Hold":
        "the HUB is in scope in EVERY seed (core walks [HUB] + kept), so its ground is never "
        "locked; these are the Twin Maiden Husks / Gostoc shop rows, bought in the Hold",
    "Ashen Capital":
        "m11_05 is the ASHEN twin of the m11_00 Royal Capital. These checks ARE Leyndell checks "
        "(their flags are f1100xxxx); the coordinate datamine resolved the m11_05 copy of the same "
        "spot. The Ashen Capital is never rolled (#436) and is entered behind the Ashen Capital "
        "Lock, not the region draw -- so this pairing is an artefact of the COORDINATE source, not "
        "a region defect",
}


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def _tile_of(map_id):
    """The key `play_region_buckets.tsv` geometry is written in: `m60_48_51` / `m61_46_45` for the
    overworlds (tile-level), `m21_00` for an interior."""
    if map_id.startswith("m6"):
        return "_".join(map_id.split("_")[:3])
    return map_id[:6]


def load_tables(repo):
    gf = os.path.join(repo, "greenfield")
    data = _load(os.path.join(gf, "eldenring", "data.py"), "_cgr_data")
    groups = _load(os.path.join(gf, "region_groups.py"), "_cgr_groups")

    bucket_region = {}
    for region, buckets in groups.PLAY_REGION_GROUPS.items():
        for b in buckets:
            bucket_region[int(b)] = region

    tile_buckets = defaultdict(set)
    with open(os.path.join(gf, "play_region_buckets.tsv"), encoding="utf-8") as fh:
        for line in fh:
            if line[:1] == "#" or line.startswith("bucket"):
                continue
            bucket, kind, geometry = line.rstrip("\n").split("\t")
            tiles = [geometry] if kind == "interior" else geometry.split(";")
            for t in tiles:
                if t and t != "-":
                    tile_buckets[t].add(int(bucket))

    coords = {}
    with open(os.path.join(gf, "item_grace_coords.tsv"), encoding="utf-8") as fh:
        rows = csv.DictReader([l for l in fh if l[:1] != "#"], delimiter="\t")
        for r in rows:
            key = (r.get("key") or "").strip()
            if r.get("kind") == "item" and key.isdigit():
                coords[int(key)] = r["map_id"]
    return data, bucket_region, tile_buckets, coords


def audit(repo):
    """Every check, classified. Returns a dict of lists -- one bucket per VERDICT, so a caller can
    never read a total as if it were the resolved count.

    Records are keyed on the check's EVENT FLAG, not its ap-id. ap-ids are positional and renumber
    wholesale whenever the corpus grows -- a regen on 2026-08-07 shifted every id above 7774000 by
    adding 16 checks -- so a pin keyed on them silently comes to name different checks. The flag is
    game data and does not move."""
    data, bucket_region, tile_buckets, coords = load_tables(repo)
    out = {"agree": [], "benign": [], "mismatch": [], "ambiguous": [],
           "no_coord": [], "no_bucket_row": []}
    for region, rows in sorted(data.LOCATIONS.items()):
        for (name, ap, flag) in rows:
            map_id = coords.get(int(flag))
            if map_id is None:
                out["no_coord"].append((int(flag), region, name))
                continue
            tile = _tile_of(map_id)
            buckets = tile_buckets.get(tile)
            if not buckets:
                out["no_bucket_row"].append((int(flag), region, name, tile))
                continue
            grounds = {bucket_region.get(b) for b in buckets}
            rec = (int(flag), region, sorted(grounds, key=str), tile, name)
            if region in grounds:
                out["agree"].append(rec)
            elif len(grounds) > 1:
                # Two buckets, two regions, one tile. The volumes are 3-D and this join is not.
                out["ambiguous"].append(rec)
            elif grounds <= set(BENIGN_GROUNDS):
                out["benign"].append(rec)
            else:
                out["mismatch"].append(rec)
    return out


def report(repo, stream=sys.stdout):
    a = audit(repo)
    total = sum(len(v) for v in a.values())
    resolved = len(a["agree"]) + len(a["benign"]) + len(a["mismatch"]) + len(a["ambiguous"])
    w = stream.write
    w("check ground-region audit (issue #445)\n")
    w("  %d checks total\n" % total)
    w("  %d RESOLVED (coordinate + a play_region bucket row for its tile)\n" % resolved)
    w("  %d unmeasured: %d have no datamined coordinate, %d sit on a tile with no bucket row\n"
      % (len(a["no_coord"]) + len(a["no_bucket_row"]), len(a["no_coord"]), len(a["no_bucket_row"])))
    w("     ^ these are UNMEASURED, not clean. Any rate below is over the resolved subset only.\n")
    w("  %d agree | %d benign | %d AMBIGUOUS | %d MISMATCH\n"
      % (len(a["agree"]), len(a["benign"]), len(a["ambiguous"]), len(a["mismatch"])))
    for label, key in (("BENIGN", "benign"), ("AMBIGUOUS (tile spans two regions -- unresolved)",
                                              "ambiguous"), ("MISMATCH", "mismatch")):
        if not a[key]:
            continue
        w("\n  --- %s ---\n" % label)
        for (flag, region, grounds, tile, name) in sorted(a[key], key=lambda r: (r[1], str(r[2]))):
            w("    f%-10d %-22s ground=%-28s tile=%-12s %s\n"
              % (flag, region, "/".join(str(g) for g in grounds), tile, name[:72]))
    if a["benign"]:
        w("\n  benign classes:\n")
        for g in sorted({str(x) for (_a, _r, gs, _t, _n) in a["benign"] for x in gs}):
            w("    %s -- %s\n" % (g, BENIGN_GROUNDS.get(g, "NO REASON RECORDED")))
    return a


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--repo", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    args = p.parse_args(argv)
    a = report(args.repo)
    return 1 if a["mismatch"] else 0


if __name__ == "__main__":
    sys.exit(main())
