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

This module is import-safe and side-effect-free (tests call build_map()/nearest() directly). Run:
    python3 tools/build_nearest_grace.py [coords.tsv] [--out greenfield/nearest_grace.tsv] [--max-dist M]
"""
import argparse
import math
import os
import re
import sys

# Overworld maps (m60=base Lands Between, m61=DLC Shadow Realm) are stored as a grid of
# per-tile MSB frames: m60_TX_TZ_00, each tile a 256m square with MAP-LOCAL coordinates. A
# graceless tile's checks would come up blind even when a neighbouring tile's grace is metres
# away, because the raw builder only compares WITHIN a map_id. Merge every overworld tile into
# one global frame (world = tile*256 + local) so nearest-grace spans tile borders. This is the
# same transform used by tools/datamine_grace_ground.py. Only x/z are gridded; y is height.
_TILE_M = 256.0
_OVERWORLD_RE = re.compile(r"^(m6[01])_(\d\d)_(\d\d)_")


def _normalize(map_id, xyz):
    """Overworld tile (map-local) -> ('m60'/'m61', global xyz). Non-overworld passes through."""
    m = _OVERWORLD_RE.match(map_id)
    if not m:
        return map_id, xyz
    base, tx, tz = m.group(1), int(m.group(2)), int(m.group(3))
    x, y, z = xyz
    return base, (tx * _TILE_M + x, y, tz * _TILE_M + z)

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


def build_keyed_map_reporting(lines, max_dist=DEFAULT_MAX_DIST):
    """As `build_keyed_map`, plus the DROPPED matches: (mapping, [(flag, name, dist), ...]).

    A filter with no tally is a lie (CONTRIBUTING rule 4). The caller prints the drops so a coord
    regen that suddenly strands a hundred checks is visible in the run, not discovered months later
    by a player reading "near <somewhere 10 km away>".
    """
    items, graces_by_map = parse_coords(lines)
    out = {}
    dropped = []
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
    return out, dropped


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("coords", nargs="?", default=DEFAULT_IN)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--max-dist", type=float, default=DEFAULT_MAX_DIST,
                    help=f"drop matches farther than this many metres (default: {DEFAULT_MAX_DIST:.0f}; "
                         "pass 0 to disable the cap -- see DEFAULT_MAX_DIST for why not)")
    args = ap.parse_args(argv)
    if not os.path.isfile(args.coords):
        print(f"coords file not found: {args.coords}\n"
              f"Run tools/datamine_item_grace_coords.py on Windows first. Nothing written.")
        return 1
    with open(args.coords, encoding="utf-8-sig", newline="") as fh:
        cap = args.max_dist if args.max_dist else None
        mapping, dropped = build_keyed_map_reporting(fh, max_dist=cap)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# nearest_grace.tsv -- AUTO-GENERATED by tools/build_nearest_grace.py. DO NOT hand-edit;\n")
        fh.write("# manual fixes go in greenfield/location_descriptions.tsv (layer 1, wins). See\n")
        fh.write("# docs/specs/SPEC-location-descriptions.md.\n")
        fh.write("# grace_key is the grace's own warpUnlockFlag. GROUP ON IT, not on grace_name:\n")
        fh.write("# seven names are shared by two different graces, so name-keyed grouping merges them.\n")
        fh.write("flag\tgrace_name\tgrace_key\n")
        for flag in sorted(mapping):
            _name, _key = mapping[flag]
            fh.write(f"{flag}\t{_name}\t{_key or ''}\n")
    print(f"wrote {args.out}: {len(mapping)} checks matched to a nearest grace")
    if dropped:
        dropped.sort(key=lambda t: -t[2])
        print(f"  DROPPED {len(dropped)} match(es) beyond the {cap:.0f} m cap "
              f"(they fall through to the layer-5 locale description, which is honest; a "
              f"'near <grace>' 9 km away is not):")
        for flag, name, dist in dropped[:25]:
            print(f"    flag={flag} would have said 'near {name}' at {dist:.0f} m")
        if len(dropped) > 25:
            print(f"    ... and {len(dropped) - 25} more")
    return 0


if __name__ == "__main__":
    sys.exit(main())
