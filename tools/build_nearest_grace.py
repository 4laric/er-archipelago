#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_nearest_grace.py -- PURE nearest-Site-of-Grace resolver for the location-description
layer 4 (desc_sources.py). Consumes a coordinate dump and writes greenfield/nearest_grace.tsv
(``flag<TAB>grace_name``), which gen_data renders as "near <grace name>".

INPUT: a coords tsv (default greenfield/item_grace_coords.tsv, produced on Windows by
tools/datamine_item_grace_coords.py) with one row per item AND per grace:

    kind<TAB>key<TAB>map_id<TAB>x<TAB>y<TAB>z<TAB>name

  kind  : 'item' or 'grace'
  key   : the check's event flag (item) / the grace's warpUnlockFlag (grace)
  map_id: witchy MSB map (e.g. m20_01_00_00); positions are MAP-LOCAL. Overworld tiles
          (m60_TX_TZ_00 / m61_TX_TZ_00) are merged into one global frame -- see _normalize.
  x/y/z : map-local coordinates (metres)
  name  : the human grace name (grace rows only; blank for items)

For each item we pick the nearest grace IN THE SAME (normalized) map. Interior maps compare
map-local. Overworld tiles are first folded into a single 'm60'/'m61' global frame
(world = tile*256 + local) so a graceless tile can still anchor to a neighbouring tile's grace.

This module is import-safe and side-effect-free (tests call build_map()/nearest() directly).

🛑 THE EMIT INVOCATION, in full -- `--extra-coords` is NOT optional if you intend to reproduce the
committed table. Without it the 24 `via=boss_arena` rows are silently dropped and the run still
prints a cheerful "wrote ... checks matched", which is exactly what happened on 2026-08-04 and was
caught only by a diff. `test_the_committed_table_has_not_shrunk_and_keeps_its_derived_rows` now
catches it:

    python3 tools/build_nearest_grace.py --extra-coords greenfield/boss_reward_coords.tsv

Optional: [coords.tsv] [--out greenfield/nearest_grace.tsv] [--max-dist M]
"""
import argparse
import math
import os
import sys

# `tools/` is not necessarily on sys.path: the test suites load this file BY PATH with importlib,
# which does not add its directory. Without this the sibling import below raises ModuleNotFoundError
# and the whole suite errors at collection.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Overworld maps (m60/m61) are a grid of per-tile MSB frames with MAP-LOCAL coordinates. A graceless
# tile's checks would come up blind even when a neighbouring tile's grace is metres away, so every
# overworld tile is folded into ONE global frame before the join.
#
# 🛑 THE FOLD IS NOT DEFINED HERE. It is tools/overworld_fold.world_xz, shared with the check browser
# and the desc-triage page. This module used to own a second copy that folded at *256 regardless of
# LOD and whose regex required a trailing '_' -- so 725 three-field item rows (m60_34_50) never
# normalised at all while every one of the 225 overworld grace rows did, and the two sides could
# never share a key. MEASURED on 2026-08-04 (issue #338): +421 checks resolve under the shared fold,
# with ZERO existing matches moved, re-graced, or lost, and the 18 that the distance cap was
# catching at 8.7-10.4 km -- the "Altar South spans four regions" phantom -- now land 30-356 m from
# a grace that makes sense.
from overworld_fold import world_xz


def _normalize(map_id, xyz):
    """Overworld tile (map-local) -> ('m60'/'m61', global xyz). Non-overworld passes through."""
    w = world_xz(map_id, xyz[0], xyz[2])
    if w is None:
        return map_id, xyz
    base, gx, gz = w
    return base, (gx, xyz[1], gz)


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_IN = os.path.join(ROOT, "greenfield", "item_grace_coords.tsv")
DEFAULT_OUT = os.path.join(ROOT, "greenfield", "nearest_grace.tsv")


# DEFAULT DISTANCE CAP, in metres. Overworld tiles are folded into one global frame so a graceless
# tile can borrow a neighbour's grace -- necessary, and it is also what let a check anchor to a grace
# on the other side of the continent. Measured over all 3510 matches on 2026-07-25 the distribution
# is sharply bimodal: median 130 m, p90 234 m, p99 433 m, largest plausible match 508.6 m (inside
# Darklight Catacombs) -- and then NOTHING until 8765 m, above which sit 18 checks reaching 8.7-10.4 km.
# There is no continuum between the two populations, so the cap is not a tuning knob; it separates
# real answers from a nearest-neighbour that never fails and therefore answered confidently and
# wrongly (CONTRIBUTING rule 1). 2000 m sits in the middle of an empty 8 km gap: ~4x headroom over the
# largest real match, and it still drops every one of the 18.
#
# Twelve of those 18 landed on ONE grace, Altar South, which is why the grace-straddle screen reported
# it spanning four regions (Liurnia, Altus, Mt. Gelmir, Mountaintops) -- its four genuine checks are
# 59-201 m away and all Liurnia. The regions were right; the GRACE was wrong.
DEFAULT_MAX_DIST = 2000.0


def _dist(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def parse_coords(lines):
    """Iterable of raw tsv lines -> (items, graces_by_map).
    items: list of (flag:int, map_id:str, (x,y,z));
    graces_by_map: {map_id: [((x,y,z), name, key), ...]}.

    `key` is the grace's OWN warpUnlockFlag. It rides along because the display NAME is not unique:
    seven names are shared by two physically distant graces (Artist's Shack, Divine Bridge, East
    Capital Rampart, Elden Throne, Erdtree Sanctuary, Isolated Merchant's Shack, Queen's Bedchamber
    -- the Leyndell/Ashen-Capital map-version pairs, plus two genuinely duplicated shacks). Any
    consumer that GROUPS checks by grace and keys on the name silently merges those pairs and
    manufactures results that look like real findings (the grace-straddle screen counted ~9 such
    phantom minority checks). Names are for humans; group on the key."""
    items = []
    graces_by_map = {}
    for ln in lines:
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        p = ln.rstrip("\n").split("\t")
        if len(p) < 6 or p[0] not in ("item", "grace"):
            continue
        kind, key, map_id = p[0], p[1].strip(), p[2].strip()
        try:
            xyz = (float(p[3]), float(p[4]), float(p[5]))
        except ValueError:
            continue
        name = p[6].strip() if len(p) > 6 else ""
        map_id, xyz = _normalize(map_id, xyz)
        if kind == "grace":
            graces_by_map.setdefault(map_id, []).append((xyz, name, key))
        else:
            if not key.lstrip("-").isdigit():
                continue
            items.append((int(key), map_id, xyz))
    return items, graces_by_map


def nearest(item_xyz, graces, max_dist=None):
    """Return (name, distance) of the nearest named grace, or (None, None). Unnamed graces are
    ignored (a grace with no resolved name is useless as a descriptor).

    Accepts grace tuples of either shape so a caller holding the old ``(xyz, name)`` pairs keeps
    working; see `nearest_keyed` for the identity as well as the label."""
    name, _key, d = nearest_keyed(item_xyz, graces, max_dist=max_dist)
    return name, d


def nearest_keyed(item_xyz, graces, max_dist=None):
    """As `nearest`, but also returns the grace's own key -- (name, key, distance).

    The key is what identifies a grace; the name merely labels it, and seven names are shared by two
    different graces (see `parse_coords`). Grouping consumers must use this.
    """
    best_d, best_name, best_key = math.inf, None, None
    for g in graces:
        gxyz, name = g[0], g[1]
        key = g[2] if len(g) > 2 else None
        if not name:
            continue
        d = _dist(item_xyz, gxyz)
        if d < best_d:
            best_d, best_name, best_key = d, name, key
    if best_name is None or (max_dist is not None and best_d > max_dist):
        return None, None, None
    return best_name, best_key, round(best_d, 1)


def build_map(lines, max_dist=DEFAULT_MAX_DIST):
    """Raw coord lines -> {flag: grace_name}. Same-map nearest only, capped at `max_dist` metres.
    Pass ``max_dist=None`` for the old uncapped behaviour (see DEFAULT_MAX_DIST for why you should
    not)."""
    return {f: nk[0] for f, nk in build_keyed_map(lines, max_dist=max_dist).items()}


def build_keyed_map(lines, max_dist=DEFAULT_MAX_DIST):
    """Raw coord lines -> {flag: (grace_name, grace_key)}. Same-map nearest, capped."""
    return build_keyed_map_reporting(lines, max_dist=max_dist)[0]


def build_keyed_map_reporting(lines, max_dist=DEFAULT_MAX_DIST, with_unmatched=False):
    """As `build_keyed_map`, plus the DROPPED matches: (mapping, [(flag, name, dist), ...]).

    A filter with no tally is a lie (CONTRIBUTING rule 4). The caller prints the drops so a coord
    regen that suddenly strands a hundred checks is visible in the run, not discovered months later
    by a player reading "near <somewhere 10 km away>".

    ⭐ `with_unmatched=True` adds a THIRD element, [(flag, map_id), ...]: the checks whose map holds
    no named grace at all. Those are not distance drops and must not be reported as ones -- but
    until 2026-08-04 they were not reported as ANYTHING, and that is the blind spot that hid issue
    #338 for months. The tally above only fires when a same-map grace exists and is too far; with
    ZERO same-map graces `far_name` is None and nothing was recorded, which is exactly the shape a
    broken join key produces. The default stays a 2-tuple so every existing caller is untouched.
    """
    items, graces_by_map = parse_coords(lines)
    out = {}
    dropped = []
    unmatched = []
    for flag, map_id, xyz in items:
        graces = graces_by_map.get(map_id, ())
        name, key, dist = nearest_keyed(xyz, graces, max_dist=max_dist)
        if name:
            out[flag] = (name, key)
            continue
        # Distinguish "no grace within the cap" from "no named grace in this map at all" -- only the
        # first is a drop, and only the first should be reported as one.
        far_name, _far_key, far_dist = nearest_keyed(xyz, graces, max_dist=None)
        if far_name:
            dropped.append((flag, far_name, far_dist))
        else:
            unmatched.append((flag, map_id))
    # DISTINCT FLAGS, not rows, and only flags that matched NOWHERE. A flag can have several coord
    # rows (map-version duplicates), so a row count here would be a "resolved.len() counted
    # locations, not flags" repeat -- the exact miscount CONTRIBUTING's "the tell" section is about.
    # Measured 2026-08-04: 776 rows collapse to 230 checks, 166 of them m11_10 (the hub) alone.
    unmatched = sorted({(f, m) for f, m in unmatched if f not in out})
    if with_unmatched:
        return out, dropped, unmatched
    return out, dropped


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("coords", nargs="?", default=DEFAULT_IN)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--extra-coords", action="append", default=[],
                    metavar="TSV",
                    help="additional coord file(s) in the item_grace_coords schema, e.g. "
                         "greenfield/boss_reward_coords.tsv. Their flags are marked `via` in the "
                         "output so a DERIVED position is never mistaken for a measured one.")
    ap.add_argument("--max-dist", type=float, default=DEFAULT_MAX_DIST,
                    help=f"drop matches farther than this many metres (default: {DEFAULT_MAX_DIST:.0f}; "
                         "pass 0 to disable the cap -- see DEFAULT_MAX_DIST for why not)")
    args = ap.parse_args(argv)
    if not os.path.isfile(args.coords):
        print(f"coords file not found: {args.coords}\n"
              f"Run tools/datamine_item_grace_coords.py on Windows first. Nothing written.")
        return 1
    cap = args.max_dist if args.max_dist else None
    with open(args.coords, encoding="utf-8-sig", newline="") as fh:
        lines = fh.readlines()
    # EXTRA COORD SOURCES. These carry DERIVED positions (currently boss_reward_coords.tsv: the
    # boss's ARENA, not the item's own spot), so their flags are tracked and marked in the output.
    # They are appended AFTER the primary file and never replace a measured row -- a flag present
    # in both keeps its measured position, because build_keyed_map takes the nearest match and a
    # measured coordinate is strictly better evidence than an inferred one.
    derived_flags = set()
    measured_flags = {int(p[1]) for p in
                      (ln.rstrip("\n").split("\t") for ln in lines)
                      if len(p) > 1 and p[0] == "item" and p[1].strip().lstrip("-").isdigit()}
    for extra in args.extra_coords:
        if not os.path.isfile(extra):
            print(f"  --extra-coords not found, skipping: {extra}")
            continue
        with open(extra, encoding="utf-8-sig", newline="") as fh:
            elines = fh.readlines()
        n = 0
        for ln in elines:
            p = ln.rstrip("\n").split("\t")
            if len(p) > 1 and p[0] == "item" and p[1].strip().lstrip("-").isdigit():
                f = int(p[1])
                if f not in measured_flags:
                    derived_flags.add(f)
                    n += 1
        lines.extend(elines)
        print(f"  +{n} derived position(s) from {os.path.basename(extra)}")
    mapping, dropped, unmatched = build_keyed_map_reporting(lines, max_dist=cap, with_unmatched=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# nearest_grace.tsv -- AUTO-GENERATED by tools/build_nearest_grace.py. DO NOT hand-edit;\n")
        fh.write("# manual fixes go in greenfield/location_descriptions.tsv (layer 1, wins). See\n")
        fh.write("# docs/specs/SPEC-location-descriptions.md.\n")
        fh.write("# grace_key is the grace's own warpUnlockFlag. GROUP ON IT, not on grace_name:\n")
        fh.write("# seven names are shared by two different graces, so name-keyed grouping merges them.\n")
        fh.write("# `via` is EMPTY for a measured position and names the derivation otherwise\n")
        fh.write("# (boss_arena = the position is the BOSS'S ARENA, not the item's own spot -- good\n")
        fh.write("# enough for 'near <grace>', not for a distance). TRAILING column: readers that\n")
        fh.write("# index [0] and [2] are unaffected.\n")
        fh.write("flag\tgrace_name\tgrace_key\tvia\n")
        for flag in sorted(mapping):
            _name, _key = mapping[flag]
            _via = "boss_arena" if flag in derived_flags else ""
            fh.write(f"{flag}\t{_name}\t{_key or ''}\t{_via}\n")
    n_derived = sum(1 for f in mapping if f in derived_flags)
    print(f"wrote {args.out}: {len(mapping)} checks matched to a nearest grace"
          + (f" ({n_derived} via a DERIVED position)" if n_derived else ""))
    if dropped:
        dropped.sort(key=lambda t: -t[2])
        print(f"  DROPPED {len(dropped)} match(es) beyond the {cap:.0f} m cap "
              f"(they fall through to the layer-5 locale description, which is honest; a "
              f"'near <grace>' 9 km away is not):")
        for flag, name, dist in dropped[:25]:
            print(f"    flag={flag} would have said 'near {name}' at {dist:.0f} m")
        if len(dropped) > 25:
            print(f"    ... and {len(dropped) - 25} more")
    # The OTHER half of the tally, and the one whose absence hid #338: a check whose map holds no
    # named grace at all. Not a distance drop -- an unanswerable question -- but it must be a NUMBER
    # in the run, because a broken join key looks exactly like this and looks like nothing else.
    if unmatched:
        by_map = {}
        for _flag, _map in unmatched:
            by_map[_map] = by_map.get(_map, 0) + 1
        print(f"  UNMATCHED {len({f for f, _ in unmatched})} check(s) ({len(unmatched)} coord row(s)) "
              f"across {len(by_map)} map(s) with NO named grace at all (not a distance drop -- there "
              f"was nothing to measure against):")
        for _map, _n in sorted(by_map.items(), key=lambda kv: -kv[1])[:10]:
            print(f"    {_map}: {_n}")
        if len(by_map) > 10:
            print(f"    ... and {len(by_map) - 10} more map(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
