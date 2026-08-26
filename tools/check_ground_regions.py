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


# Sweep triggers whose members' cross-region assignment is a RULING, not an accident. The verdict
# below applies ONLY to these -- a trigger enters this table WITH its ruling written out, or its
# members stay MISMATCH. The scope exists so that "it happens to sit inside a same-region sweep"
# can never quietly excuse a possibly-wrong assignment: until 2026-08-26 it held one trigger, and
# 400175/400036/400401 stayed accusable precisely because nobody had ruled on them.
#
# 2026-08-26: Mohg is the second entry, and the ground under that scope moved first. #1059 made
# member/arena co-region a GATE (test_gf_sweep_region_containment) and made SWEEP_ARENA_REGION
# read the MEASURED bucket instead of a snapshot, so "the trigger's arena is the member's region"
# is now an enforced invariant rather than a coincidence this table has to guard against.
RULED_SWEEP_ANCHORS = {
    21000850: "#885 (Alaric 2026-08-19): the Golden Hippopotamus presents as Scadu Altus "
              "EVERYWHERE -- reward, trigger, and every granted member. m21_00 is curated to "
              "Scadu Altus in gen_data.DUNGEON_REGION_CURATED; the arena is bucket 69000.",
    12050800: "#445 (2026-08-26): MOHG, LORD OF BLOOD. His arena is MOHGWYN -- SWEEP_ARENA_REGION "
              "reads it from the MEASURED PlayRegionParam bucket since #1059, which hard-errors "
              "rather than falling back -- and every one of his 60 members is filed Mohgwyn, which "
              "#1059's containment gate (test_gf_sweep_region_containment) now ENFORCES for every "
              "trigger. One member, f400036 (Festering Bloody Finger), is accused by this audit: "
              "its award site is Mohg's own m12_05 EMEVD grant, which has no MSB coordinate for "
              "the join to see, so the only coordinates it has are two placements of the shared "
              "lot 110301 on Bloody-Finger invader NPCs standing in m60_35_44 and m60_42_36. "
              "Killing Mohg grants it, so Mohgwyn alone always suffices; and the assignment cannot "
              "move to the accusing ground without VIOLATING the containment gate. Same caveat as "
              "the Hippo: walking to the invader from a Mohgwyn-only seed still kicks, the sweep "
              "is the guaranteed route.",
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
    sweeps = _load(os.path.join(gf, "eldenring", "boss_sweeps.py"), "_cgr_sweeps")

    # ap -> (trigger, arena_region) for every member of a RULED trigger (RULED_SWEEP_ANCHORS) that
    # has an AUDITED arena region. Used by the SWEEP-ANCHORED verdict; an unruled or unmeasured
    # trigger contributes nothing (neither may excuse anything).
    sweep_anchor = {}
    for trig, members in sweeps.DUNGEON_SWEEPS.items():
        if trig not in RULED_SWEEP_ANCHORS:
            continue
        arena = sweeps.SWEEP_ARENA_REGION.get(trig)
        if not arena:
            continue
        for ap in members:
            sweep_anchor[ap] = (trig, arena)

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

    # ---- PLAYAREA-RULED: checks whose region was SET by the point-in-volume scan (#1059) --------
    # `tile_buckets` above is the PlayRegionParam DEFAULT for a whole map tile -- the coarse
    # instrument. `docs/PLAYAREA-ITEM-SCAN.md` is explicit that the point-in-volume scan's answers
    # REPLACE it rather than average with it: the scan reads the exact runtime PlayRegionID the
    # kick-watch reads, at the pickup's own coordinates, and a tile default cannot see a volume
    # reaching across a tile boundary. Without this branch the audit accuses precisely the checks
    # the scan just corrected -- the finer instrument blamed for disagreeing with the coarser one.
    #
    # 🛑 IT IS NOT APPLIED TO EVERY FLAG THE SCAN CAN ANSWER, and that restraint is the whole
    # design. A scan row is exact about a POINT; it is evidence about a CHECK only when the check
    # IS that point. Applied wholesale it drags in the NPC-relocation families #1054 excludes by
    # name -- the Roundtable and Limgrave Ash-of-War rows answering Mt. Gelmir because Patches and
    # Bernahl stand at Volcano Manor, the "from Moore" rows answering Scadu Altus -- and the
    # mismatch list goes from 3 to over 100 accusations that are all the instrument being right
    # about the wrong question. So the branch fires ONLY for a flag that carries a reasoned
    # region_overrides.tsv row: the set a human adjudicated, one at a time, with the reason written
    # down. An unadjudicated flag keeps the tile default and stays accusable.
    _EXACT = ("volume:", "interior-vol:", "seam:", "interior-seam:")
    _ruled_flags = set()
    _ov = os.path.join(gf, "region_overrides.tsv")
    if os.path.isfile(_ov):
        with open(_ov, encoding="utf-8") as fh:
            for line in fh:
                parts = line.rstrip("\n").split("\t")
                if len(parts) >= 4 and parts[0] == "flag" and parts[1].isdigit():
                    _ruled_flags.add(int(parts[1]))
    exact_buckets = defaultdict(set)
    _ipr = os.path.join(gf, "item_play_regions.tsv")
    if os.path.isfile(_ipr):
        with open(_ipr, encoding="utf-8") as fh:
            for line in fh:
                if line[:1] == "#" or line.startswith("flag\t"):
                    continue
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 5 or not parts[0].isdigit():
                    continue
                if int(parts[0]) not in _ruled_flags or not parts[4].startswith(_EXACT):
                    continue
                for b in parts[3].split(";"):
                    if b.strip().isdigit():
                        exact_buckets[int(parts[0])].add(int(b))

    coords = {}
    with open(os.path.join(gf, "item_grace_coords.tsv"), encoding="utf-8") as fh:
        rows = csv.DictReader([l for l in fh if l[:1] != "#"], delimiter="\t")
        for r in rows:
            key = (r.get("key") or "").strip()
            if r.get("kind") == "item" and key.isdigit():
                # ALL maps, not last-write-wins (2026-08-19, the full-census regen). A flag can be
                # datamined at SEVERAL positions -- shop_multi rows carry one row per physical
                # merchant (Kale AND the region's own vendor), quest items one per NPC station.
                # Keeping one arbitrary map turned 26 multi-merchant rows into false MISMATCHes:
                # standing-ground for a disjunct-site check is a DISJUNCTION, and the audit agrees
                # if ANY site's ground matches the assigned region.
                coords.setdefault(int(key), []).append(r["map_id"])
    return data, bucket_region, tile_buckets, coords, sweep_anchor, exact_buckets


def audit(repo):
    """Every check, classified. Returns a dict of lists -- one bucket per VERDICT, so a caller can
    never read a total as if it were the resolved count.

    Records are keyed on the check's EVENT FLAG, not its ap-id. ap-ids are positional and renumber
    wholesale whenever the corpus grows -- a regen on 2026-08-07 shifted every id above 7774000 by
    adding 16 checks -- so a pin keyed on them silently comes to name different checks. The flag is
    game data and does not move."""
    data, bucket_region, tile_buckets, coords, sweep_anchor, exact_buckets = load_tables(repo)
    out = {"agree": [], "benign": [], "sweep_anchored": [], "playarea_ruled": [],
           "mismatch": [], "ambiguous": [], "sites_elsewhere": [], "no_coord": [],
           "no_bucket_row": []}
    for region, rows in sorted(data.LOCATIONS.items()):
        for (name, ap, flag) in rows:
            map_ids = coords.get(int(flag))
            if not map_ids:
                out["no_coord"].append((int(flag), region, name))
                continue
            exact = exact_buckets.get(int(flag))
            if exact:
                here = {bucket_region.get(b) for b in exact} - {None}
                if here:
                    # Its own verdict bucket, not "agree": these are EXCUSED by a ruling, and a
                    # ruling that hides inside the agreement count cannot be reviewed.
                    rec = (int(flag), region, sorted(here, key=str), "playarea-scan", name)
                    out["playarea_ruled" if region in here else "mismatch"].append(rec)
                    continue
            grounds = set()
            per_tile = {}
            for map_id in map_ids:
                tile = _tile_of(map_id)
                buckets = tile_buckets.get(tile)
                if not buckets:
                    continue
                per_tile[tile] = {bucket_region.get(b) for b in buckets}
                grounds |= per_tile[tile]
            if not per_tile:
                out["no_bucket_row"].append((int(flag), region, name, _tile_of(map_ids[0])))
                continue
            tile = "/".join(sorted(per_tile))
            rec = (int(flag), region, sorted(grounds, key=str), tile, name)
            if region in grounds:
                out["agree"].append(rec)          # ANY site suffices: disjunct-site semantics
            elif len(per_tile) > 1:
                # SEVERAL sites, none in the assigned region. Not a tile ambiguity and not (yet) a
                # mismatch: every observed case is a RELOCATING MERCHANT (Bernahl, Sellen -- shop
                # rows assigned to the FIRST station by the ESD ground truth) whose first-station
                # position the coordinate datamine has not attributed. The assignment is unwitnessed
                # rather than contradicted; the missing datum is the first station's coordinates.
                out["sites_elsewhere"].append(rec)
            elif any(len(g) > 1 for g in per_tile.values()):
                # Two buckets, two regions, one tile. The volumes are 3-D and this join is not.
                out["ambiguous"].append(rec)
            elif grounds <= set(BENIGN_GROUNDS):
                out["benign"].append(rec)
            elif sweep_anchor.get(ap, (None, None))[1] == region:
                # SWEEP-ANCHORED (#885): the check stands on foreign ground, but it is a MEMBER of a
                # sweep whose trigger is fought standing IN the assigned region -- so any seed that
                # keeps the assigned region can obtain it by killing that boss, and the assignment is
                # a deliberate ruling, not a mis-attribution. The archetype is the Golden
                # Hippopotamus: its 100+ m21_00 members stand on Shadow Keep ground (bucket 21000)
                # and present as Scadu Altus, the arena bucket 69000 the fight is actually fought
                # from (Alaric 2026-08-19). Caveat stated out loud: walking to the pickup from a seed
                # that lacks the GROUND region still kicks; the sweep is the guaranteed route.
                out["sweep_anchored"].append(rec + (sweep_anchor[ap][0],))
            else:
                out["mismatch"].append(rec)
    return out


def report(repo, stream=sys.stdout):
    a = audit(repo)
    total = sum(len(v) for v in a.values())
    resolved = (len(a["agree"]) + len(a["benign"]) + len(a["sweep_anchored"])
                + len(a["playarea_ruled"])
                + len(a["mismatch"]) + len(a["ambiguous"]) + len(a["sites_elsewhere"]))
    w = stream.write
    w("check ground-region audit (issue #445)\n")
    w("  %d checks total\n" % total)
    w("  %d RESOLVED (coordinate + a play_region bucket row for its tile)\n" % resolved)
    w("  %d unmeasured: %d have no datamined coordinate, %d sit on a tile with no bucket row\n"
      % (len(a["no_coord"]) + len(a["no_bucket_row"]), len(a["no_coord"]), len(a["no_bucket_row"])))
    w("     ^ these are UNMEASURED, not clean. Any rate below is over the resolved subset only.\n")
    w("  %d agree | %d benign | %d sweep-anchored | %d playarea-ruled | %d sites-elsewhere | "
      "%d AMBIGUOUS | %d MISMATCH\n"
      % (len(a["agree"]), len(a["benign"]), len(a["sweep_anchored"]), len(a["playarea_ruled"]),
         len(a["sites_elsewhere"]), len(a["ambiguous"]), len(a["mismatch"])))
    for label, key in (("BENIGN", "benign"),
                       ("SWEEP-ANCHORED (member of a sweep fought from the assigned region, #885)",
                        "sweep_anchored"),
                       ("PLAYAREA-RULED (region set by the point-in-volume scan + a reasoned "
                        "region_overrides row, which outranks the tile default -- #1059)",
                        "playarea_ruled"),
                       ("SITES-ELSEWHERE (multi-site, first station unwitnessed -- relocating merchants)",
                        "sites_elsewhere"),
                       ("AMBIGUOUS (tile spans two regions -- unresolved)", "ambiguous"),
                       ("MISMATCH", "mismatch")):
        if not a[key]:
            continue
        w("\n  --- %s ---\n" % label)
        for rec in sorted(a[key], key=lambda r: (r[1], str(r[2]))):
            (flag, region, grounds, tile, name) = rec[:5]
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
