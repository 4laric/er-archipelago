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

The payoff is MAP ATTRIBUTION -- knowing WHERE a check is, one row per position.

🛑 IT DOES NOT FIX `tile_pr()`, AND I CLAIMED IT WOULD. Measured 2026-07-26 before wiring it into
gen_data, which is why it is not wired:

  * gen_data's region waterfall already consumes almost everything here (MSB_TRUTH_MAP,
    MERCHANT_SHOP_REGION, SHOP_ROW_REGION, GLOBAL_RECOVER, _recover_tile). Only **46** checks are
    DEFAULTED_REGION_APS today, and this table places **3** of them -- two of those on more than one
    map, so they would stay HUB anyway.
  * The `tile_pr` exposure is a DIFFERENT QUESTION. Those checks are not missing a map; they are on a
    tile with NO GRACE, so the TILE -> REGION step nearest-neighbours. Of the graceless-tile overworld
    checks, this table names the SAME tile they already have for 301, nothing for 5, and a different
    map for **2**. Knowing the map cannot help when the map is already known and it is the tile's
    REGION that is unanchored.

So wiring this into regioning would move ~1-3 checks on the weakest evidence available, in exchange
for a new consumer in the hot path. Not worth it. What WOULD close the tile exposure is a tile ->
region source: anchor more tiles (more graces in the grace_flags x grace_region_map join), or read
PlayRegionParam directly. See tests/test_gf_tile_anchor_coverage.py, which pins the exposure.

What this table IS for: the one-to-many coordinate/availability model -- which merchant instance sells
a row, on which map, behind which ESD gate -- and as the base layer XYZ hangs off.

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

    # ---- 3. flag-encoded tile: the WEAKEST source, and labelled as such -------------------------
    # An item-lot flag encodes its own map: overworld `1XXYY7NNN` -> m60_XX_YY (`2` -> m61), interior
    # `MMSS7NNN` -> mMM_SS. gen_data already trusts this rule (_recover_tile) and so does
    # test_gf_lot_gates_cross_region's resolver, but it is a derivation FROM THE ID, not an observation
    # of where the thing stands -- so it gets its own source name and a consumer can refuse it.
    #
    # CONTROL, measured against the independent observed maps in msb_flag_region: of 2327 flags that
    # have BOTH, 2281 agree = 98.02%. The 46 that do not split two ways, and neither is random:
    #   * the observed map is a COARSE LOD tile (m60_10_09) while the decode gives the fine tile --
    #     here the decode is the better answer (cf. the LOD tile-snap bug);
    #   * genuinely adjacent tiles (observed m60_35_54 vs decoded m60_36_54) -- an item can sit just
    #     over the boundary from the tile whose flag block owns it; here the observation wins.
    # 🛑 So this is a HINT, not ground truth. It is emitted only where nothing better exists, and it
    # is NOT the tile_pr trap in a new hat: tile_pr was a nearest-neighbour with NO failure branch, so
    # it always answered. This refuses -- 166 flags decode to nothing and are counted, not guessed.
    def _flag_tile(fl):
        t = str(fl)
        if len(t) == 10 and t[0] in "12":
            return "m6%s_%s_%s" % ("0" if t[0] == "1" else "1", t[2:4], t[4:6])
        if len(t) == 8 and t[4] == "7":
            return "m%s_%s" % (t[0:2], t[2:4])
        return None

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
    return out, tally, _flag_tile


def add_flag_tiles(out, tally, flag_tile, wanted):
    """Fill ONLY the flags nothing else placed. `wanted` is the caller's universe of flags (so this
    never invents rows for ids no check uses)."""
    placed = {f for (f, _m, _s, _d, _a, _n) in out}
    for f in sorted(wanted, key=int):
        if f in placed:
            continue
        t = flag_tile(f)
        if not t:
            tally["flag decodes to NO map (refused, not guessed)"] += 1
            continue
        out.append((f, t, "flag_tile", "decoded from the flag id", "", ""))
    return out, tally


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit", action="store_true", help="write greenfield/check_maps.tsv")
    ap.add_argument("--flag-tiles", action="store_true", default=True,
                    help="also emit source=flag_tile for flags nothing else places (default on; "
                         "98.02%% agreement with the observed maps -- see the note in build())")
    ap.add_argument("--no-flag-tiles", dest="flag_tiles", action="store_false")
    args = ap.parse_args()

    out, tally, flag_tile = build()
    if args.flag_tiles:
        # the universe is region_map.csv's flags -- it is comma-separated, so read it directly
        # rather than through the TSV reader.
        universe = set()
        rmp = os.path.join(GF, "region_map.csv")
        if os.path.isfile(rmp):
            import csv as _csv
            with open(rmp, encoding="utf-8-sig", newline="") as fh:
                for r in _csv.DictReader(fh):
                    if (r.get("flag") or "").strip().isdigit():
                        universe.add(r["flag"].strip())
        if not universe:
            sys.exit("FATAL: region_map.csv gave no flags -- refusing to fill tiles into a void.")
        out, tally = add_flag_tiles(out, tally, flag_tile, universe)
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
