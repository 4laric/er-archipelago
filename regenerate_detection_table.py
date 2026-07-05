#!/usr/bin/env python3
"""regenerate_detection_table.py -- close the er_static_detection_table.json coverage gap.

The vanilla-suppress detection table maps AP location id -> acquisition flag. ~127 non-event,
non-shop locations were missing from it (so their vanilla ware couldn't be suppressed -> leaks, e.g.
Winged Scythe, Weeping Peninsula map). Their flag is DERIVABLE: for 4286/4295 already-covered
locations the flag equals int(key.field1) -- the segment between the first two colons of the location
key (e.g. "604330,0:0000510800::" -> 510800), across ALL length classes incl. 10-digit map-lot ids.

This script ADDITIVELY augments the table: it PRESERVES every existing (validated) entry untouched and
adds `ap_code -> int(key.field1)` for each non-event, non-shop location not already present. It rebuilds
`flag_to_locations` (the inverse map) and updates `_meta`; `sweep_flags` is left untouched. Output is a
NEW timestamped file next to the original -- it never overwrites the live table.

MUST run on Windows inside the Archipelago repo (needs the world importable). Then:
  1. diff the new file against er_static_detection_table.json (should be +127 location_flags),
  2. PROBE-VALIDATE a sample of the added flags in-game (set flag -> readback; invented ids silently
     no-op -- see the event-flag-validity note), esp. the 10-digit map-lots and any surprises,
  3. only then swap it in as er_static_detection_table.json (me3/ + dist copies too).

Usage:
    python regenerate_detection_table.py            # writes ..._augmented_<ts>.json + a report
"""
import os
import sys
import json
import glob
import collections
import datetime


def find_world_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    for c in (os.path.join(here, "Archipelago", "worlds", "eldenring"),
              os.path.join(here, "worlds", "eldenring"), here):
        if os.path.isfile(os.path.join(c, "locations.py")):
            return c
    hits = glob.glob(os.path.join(here, "**", "worlds", "eldenring", "locations.py"),
                     recursive=True)
    if hits:
        return os.path.dirname(hits[0])
    raise SystemExit("could not locate worlds/eldenring")


def load_location_dictionary(world_dir):
    """Import the world's location_dictionary via the Archipelago package (reliable on Windows,
    where every relative submodule + BaseClasses is present)."""
    # worlds/eldenring -> the Archipelago root is two levels up.
    ap_root = os.path.dirname(os.path.dirname(world_dir))
    if ap_root not in sys.path:
        sys.path.insert(0, ap_root)
    try:
        from worlds.eldenring.locations import location_dictionary  # type: ignore
        return location_dictionary
    except Exception as e:
        raise SystemExit(
            "Could not import worlds.eldenring.locations (%s).\n"
            "Run this from the Archipelago repo on Windows where the world imports cleanly." % e)


def field1(key):
    parts = (key or "").split(":")
    return parts[1] if len(parts) > 1 else ""


def main():
    world = find_world_dir()
    table_path = os.path.join(world, "er_static_detection_table.json")
    if not os.path.isfile(table_path):
        raise SystemExit("er_static_detection_table.json not found in %s" % world)

    with open(table_path, encoding="utf-8") as fh:
        full = json.load(fh)
    lf = full["location_flags"]
    orig_n = len(lf)

    loc_dict = load_location_dictionary(world)

    added = []
    skipped_shop = skipped_nokey = 0
    for name, data in loc_dict.items():
        if getattr(data, "is_event", False):
            continue
        ap = getattr(data, "ap_code", None)
        if ap is None:
            continue
        if str(ap) in lf:
            continue  # preserve validated entries -- additive only
        if getattr(data, "shop", False) or getattr(data, "raceshop", False):
            skipped_shop += 1
            continue  # shop slots use the separate shopRowFlags detection path
        v = field1(getattr(data, "key", "") or "")
        if not (v.isdigit() and v.strip("0")):
            skipped_nokey += 1
            continue
        lf[str(ap)] = int(v)
        added.append((ap, int(v), getattr(data, "default_item_name", ""), name))

    # rebuild inverse map + _meta consistently; leave sweep_flags untouched
    ftl = collections.OrderedDict()
    for loc, flag in lf.items():
        ftl.setdefault(str(flag), []).append(int(loc))
    for k in ftl:
        ftl[k].sort()
    full["flag_to_locations"] = ftl
    meta = full.setdefault("_meta", {})
    meta["location_count"] = len(lf)
    meta["distinct_flags"] = len(ftl)
    meta["shared_flag_groups"] = sum(1 for vs in ftl.values() if len(vs) > 1)
    meta["source"] = str(meta.get("source", "")) + \
        " + regen %s (+%d derivable non-shop locs, flag=key.field1; PROBE-VALIDATE)" % (
            datetime.date.today().isoformat(), len(added))

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = os.path.join(world, "er_static_detection_table_augmented_%s.json" % ts)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(full, fh, separators=(",", ":"))
    rep = os.path.join(world, "detection_table_added_%s.txt" % ts)
    with open(rep, "w", encoding="utf-8") as fh:
        fh.write("# ADDED (additive; flag = int(key.field1)). location_count %d -> %d, +%d\n"
                 % (orig_n, len(lf), len(added)))
        fh.write("# PROBE-VALIDATE a sample in-game before swapping this in.\n")
        fh.write("# ap_code\tflag\tdigits\titem\tname\n")
        for ap, flag, item, name in sorted(added):
            fh.write("%d\t%d\t%d\t%s\t%s\n" % (ap, flag, len(str(flag)), item, name))

    print("location_flags: %d -> %d (+%d) | skipped shop %d, no-key %d"
          % (orig_n, len(lf), len(added), skipped_shop, skipped_nokey))
    print("wrote %s" % out)
    print("wrote %s" % rep)
    print("Next: diff vs er_static_detection_table.json, probe-validate a sample, then swap in "
          "(+ me3/ and dist copies).")


if __name__ == "__main__":
    main()
