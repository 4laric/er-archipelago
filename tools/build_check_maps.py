#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_check_maps.py -- one row per (check flag, PHYSICAL POSITION), map-granular.

WHY THIS EXISTS, and why it is not item_grace_coords.tsv
-------------------------------------------------------
`item_grace_coords.tsv` carries map-local XYZ, but it can only carry what the witchy'd MSBs name:
treasure parts and enemy parts. 1664 of 4856 live checks (34.3%, measured 2026-07-26) have no row in
it -- and the biggest slice by far is SHOP ROWS, which have no MSB part at all. They are not
non-spatial: **the merchant has a location** (Alaric), and 11 named merchants stand on more than one
map, so a shop check has SEVERAL positions.

The payoff does not need XYZ. What it buys is MAP ATTRIBUTION, which is what kills `tile_pr()` -- a
nearest-neighbour that has no failure branch, so it never refuses and has already put checks in the
wrong region. A check whose map we KNOW never needs to be guessed at.

So this table is deliberately map-granular and derives ONLY from committed tsvs -- it runs in the
agent sandbox with no game artifacts at all. XYZ is a later, orthogonal layer: when a position is
known precisely, item_grace_coords.tsv already holds it, keyed by the same flag.

THE MODEL IS ONE-TO-MANY (Alaric, 2026-07-25: "i don't want to get bit by oversimplifying the game in
modelling again"). One row per (flag, map_id, source). A check on five maps gets five rows. Never
collapse this to one position per check -- that is the arity bug that lost Messmer's Kindling.

INPUTS (all committed, no elden_ring_artifacts needed):
  greenfield/msb_flag_region.tsv   flag -> map_id, source=event|treasure|enemy
  greenfield/shop_rows.tsv         stock_flag -> row_id
  greenfield/merchant_shops.tsv    row_id -> (talk_id, merchant_name, map_id)
  greenfield/esd_gates.tsv         talk_id -> gate_flag/gate_sense over a shop range  (availability)

OUTPUT: greenfield/check_maps.tsv
  flag  map_id  source  detail  avail_flag  avail_sense

  source=msb        detail = the msb_flag_region source (event/treasure/enemy)
  source=merchant   detail = merchant name (or npc:<id>), avail_* = the ESD gate that makes THAT
                    merchant instance live, when one is known.

    python tools/build_check_maps.py --emit
    python tools/build_check_maps.py            # report only, writes nothing
"""
import argparse
import collections
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GF = os.path.join(HERE, "greenfield")
OUT = os.path.join(GF, "check_maps.tsv")


def rows(name, required=True):
    """TSV -> list of dicts. `#` comments are stripped BEFORE the header is read -- csv.DictReader
    takes the first line as the header and these files open with comments, which silently names every
    field wrong and makes every join empty."""
    path = os.path.join(GF, name)
    if not os.path.isfile(path):
        if required:
            sys.exit("FATAL: %s is missing -- refusing to emit a table built on a partial join. "
                     "An empty result is a failure, not a clean run." % name)
        return []
    hdr, out = None, []
    with open(path, encoding="utf-8-sig") as fh:
        for ln in fh:
            if ln.startswith("#"):
                continue
            p = ln.rstrip("\n").split("\t")
            if hdr is None:
                hdr = p
                continue
            out.append(dict(zip(hdr, p)))
    if not out:
        sys.exit("FATAL: %s parsed to ZERO rows." % name)
    return out


def build():
    tally = collections.Counter()
    out = []            # (flag, map_id, source, detail, avail_flag, avail_sense)
    seen = set()

    # ---- 1. MSB-sourced checks: the map is already in the table ---------------------------------
    for r in rows("msb_flag_region.tsv"):
        f, m = r.get("flag", "").strip(), (r.get("map_id") or "").strip()
        if not f.isdigit():
            tally["msb row skipped: flag not numeric"] += 1
            continue
        if not m:
            tally["msb row skipped: no map_id"] += 1
            continue
        key = (f, m, "msb")
        if key in seen:
            tally["msb duplicate (flag,map) collapsed"] += 1
            continue
        seen.add(key)
        out.append((f, m, "msb", (r.get("source") or "?").strip(), "", ""))

    # ---- 2. shop rows: the MERCHANT's map(s), plus the ESD gate that makes that instance live ----
    row_of_flag = collections.defaultdict(set)
    for r in rows("shop_rows.tsv"):
        sf = (r.get("stock_flag") or "").strip()
        if sf.isdigit():
            row_of_flag[sf].add((r.get("row_id") or "").strip())
        else:
            tally["shop row skipped: no stock_flag"] += 1

    merch = collections.defaultdict(list)
    for r in rows("merchant_shops.tsv"):
        rid = (r.get("row_id") or "").strip()
        merch[rid].append(r)

    # talk_id -> [(gate_flag, gate_sense, begin, end)] for availability
    gates = collections.defaultdict(list)
    for r in rows("esd_gates.tsv", required=False):
        t = (r.get("talk_id") or "").strip()
        try:
            gates[t].append((r.get("gate_flag", "").strip(), r.get("gate_sense", "").strip(),
                             int(r.get("shop_begin") or -1), int(r.get("shop_end") or -1)))
        except ValueError:
            tally["esd gate skipped: unparseable range"] += 1
    if not gates:
        tally["NOTE: esd_gates.tsv absent or empty -- availability left blank"] += 1

    for f, rids in row_of_flag.items():
        placed = False
        for rid in rids:
            for inst in merch.get(rid, []):
                m = (inst.get("map_id") or "").strip()
                if not m:
                    continue
                talk = (inst.get("talk_id") or "").strip()
                name = (inst.get("merchant_name") or "").strip() \
                    or ("npc:" + (inst.get("npc_param_id") or "?").strip())
                af, asns = "", ""
                try:
                    rid_i = int(rid)
                except ValueError:
                    rid_i = None
                for (gf, gs, b, e) in gates.get(talk, []):
                    # the gate whose shop RANGE contains this row is the one that makes it live
                    if rid_i is not None and b <= rid_i <= e and gf and gf != "-1":
                        af, asns = gf, gs
                        break
                key = (f, m, "merchant")
                if key in seen:
                    tally["merchant duplicate (flag,map) collapsed"] += 1
                    placed = True
                    continue
                seen.add(key)
                out.append((f, m, "merchant", name, af, asns))
                placed = True
        if not placed:
            tally["shop flag with NO merchant map (unknown position)"] += 1
    return out, tally


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit", action="store_true", help="write greenfield/check_maps.tsv")
    args = ap.parse_args()

    out, tally = build()
    flags = {f for (f, _m, _s, _d, _a, _n) in out}
    per = collections.Counter(f for (f, _m, _s, _d, _a, _n) in out)
    multi = sum(1 for f in per if per[f] > 1)
    bysrc = collections.Counter(s for (_f, _m, s, _d, _a, _n) in out)
    withav = sum(1 for r in out if r[4])

    # An empty or collapsed table must be loud, not quiet.
    if not out or len(flags) < 1000:
        sys.exit("FATAL: only %d (flag,map) pair(s) over %d flag(s) -- a join has collapsed. "
                 "Refusing to emit." % (len(out), len(flags)))

    print("check_maps: %d (flag,map) pair(s) over %d DISTINCT flags  [rows != checks: both printed]"
          % (len(out), len(flags)))
    print("  by source: %s" % dict(bysrc))
    print("  flags with MORE THAN ONE map (the one-to-many the model exists for): %d" % multi)
    print("  merchant pairs carrying an ESD availability gate: %d" % withav)
    for k, v in sorted(tally.items()):
        print("  tally: %-56s %d" % (k, v))

    if args.emit:
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("# AUTO-GENERATED by tools/build_check_maps.py -- DO NOT EDIT.\n")
            fh.write("# One row per (check flag, PHYSICAL POSITION), map-granular. A check on N maps\n")
            fh.write("# gets N rows: the model is one-to-many by design (Alaric 2026-07-25). Derived\n")
            fh.write("# ONLY from committed tsvs -- no elden_ring_artifacts, runs anywhere.\n")
            fh.write("# source=msb -> detail is event|treasure|enemy; source=merchant -> detail is the\n")
            fh.write("# merchant, avail_* the ESD gate that makes THAT instance live (blank = unknown).\n")
            fh.write("flag\tmap_id\tsource\tdetail\tavail_flag\tavail_sense\n")
            for r in sorted(out, key=lambda r: (int(r[0]), r[1], r[2])):
                fh.write("\t".join(r) + "\n")
        print("wrote %s" % os.path.relpath(OUT, HERE))
    else:
        print("(report only; pass --emit to write)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
