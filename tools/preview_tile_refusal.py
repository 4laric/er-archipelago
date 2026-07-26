#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""preview_tile_refusal.py -- what happens if an UNANCHORED tile stops carrying progression.

RUN THIS BEFORE THE REGEN. It needs no game artifacts and no AP install: it reads the committed
tsvs and the generated eldenring/*.py, so it answers "how big is this change" in about a second.

    python tools/preview_tile_refusal.py
    python tools/preview_tile_refusal.py --list        # name every affected check

THE PROBLEM. gen_data.tile_pr(x, y) names an overworld tile's play_region by nearest-neighbour over
ANCHOR, which holds only tiles that CONTAIN A GRACE. It has no failure branch, so a graceless tile
gets a confident answer about ground it has never seen -- and that answer is trusted enough to host
progression. Measured: on an anchored tile it agrees with the independent per-check nearest-grace
oracle 98.1% of the time; ONE TILE AWAY, 84.8%.

WHY NOT JUST REFUSE. Tried, reverted (e14dfa7 -> 8ff2e44): switching the region decision onto
tile_pr_strict DEFAULTED 55 checks to the HUB, three of which test_gf_lod_tile_regions pins BY FLAG
as having a KNOWN real region. Refusing loses answers that were right.

WHAT THIS MEASURES INSTEAD is the third state gen_data's own tile_pr_strict docstring proposes:
KNOWN / GUESSED / UNKNOWN, where a GUESSED check KEEPS its region (so nothing is lost and no pinned
test moves) but is BARRED FROM CARRYING PROGRESSION, exactly like DEFAULTED_REGION_APS. That is a
FILL change and nothing else -- no check moves region, no ap id renumbers.

Read the numbers below and decide whether the progression surface can afford it.
"""
import argparse
import collections
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GF = os.path.join(HERE, "greenfield")
PKG = os.path.join(GF, "eldenring")


def _tsv(name):
    path = os.path.join(GF, name)
    if not os.path.isfile(path):
        sys.exit("FATAL: %s missing -- cannot preview against a partial tree." % name)
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


def _mod(name):
    ns = {}
    path = os.path.join(PKG, name + ".py")
    if not os.path.isfile(path):
        sys.exit("FATAL: %s is not generated yet -- run build.ps1 -Greenfield first." % name)
    exec(compile(open(path, encoding="utf-8").read(), name, "exec"), ns)
    return ns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="print every affected check")
    args = ap.parse_args()

    # ANCHOR, rebuilt exactly as gen_data does: tiles that CONTAIN a grace.
    play = {r["grace_flag"].strip(): r["play_region_id"].strip() for r in _tsv("grace_region_map.tsv")}
    anchor = set()
    for r in _tsv("grace_flags.tsv"):
        m = re.match(r"m60_(\d\d)_(\d\d)", (r.get("mapTile") or "").strip())
        if m and play.get(r["warpUnlockFlag"].strip()):
            anchor.add((int(m.group(1)), int(m.group(2))))

    data = _mod("data")
    tags = _mod("location_tags")
    LOC, HUB = data["LOCATIONS"], data["HUB"]
    already = set(tags.get("DEFAULTED_REGION_APS", ()))
    # THE NUMBER THAT ACTUALLY MATTERS. features/progression_surface.allowed_ap_ids() bars
    # DEFAULTED_REGION_APS "regardless of tags", so barring a check only COSTS something if that
    # check is surface-TAGGED in the first place. An untagged filler check losing progression
    # eligibility costs nothing at all.
    ltags = tags.get("LOCATION_TAGS", {})

    # a check's own tile: its region_map map, else its flag's self-encoded tile
    tile_of = {}
    for r in csv.DictReader(open(os.path.join(GF, "region_map.csv"), encoding="utf-8-sig")):
        f = (r.get("flag") or "").strip()
        m = re.match(r"m60_(\d\d)_(\d\d)", (r.get("map") or ""))
        if f.isdigit() and m:
            tile_of[int(f)] = (int(m.group(1)), int(m.group(2)))
    for r, locs in LOC.items():
        for (_n, _a, f) in locs:
            if f in tile_of:
                continue
            s = str(f)
            if len(s) == 10 and s[0] == "1":
                tile_of[f] = (int(s[2:4]), int(s[4:6]))

    hit, byreg, tiles = [], collections.Counter(), collections.Counter()
    for reg, locs in LOC.items():
        for (name, ap_id, f) in locs:
            t = tile_of.get(f)
            if not t or t in anchor:
                continue
            tiles[t] += 1
            if ap_id in already:
                continue                       # already barred; costs nothing new
            hit.append((reg, name, ap_id, f, t))
            byreg[reg] += 1

    total = sum(len(v) for v in LOC.values())
    print("=" * 78)
    print("TILE REFUSAL PREVIEW -- no check changes region, no ap id renumbers.")
    print("=" * 78)
    print("live checks                                  %d" % total)
    print("anchored m60 tiles (contain a grace)         %d" % len(anchor))
    print("checks on a GRACELESS tile                   %d  over %d tiles" % (sum(tiles.values()), len(tiles)))
    print("already barred (DEFAULTED_REGION_APS)        %d" % len(already))
    print("NEWLY barred from progression                %d   <-- the cost of this change" % len(hit))
    tagged = [h for h in hit if ltags.get(h[2])]
    print("  of which are SURFACE-TAGGED (the real cost)  %d" % len(tagged))
    print("  untagged filler (costs nothing)              %d" % (len(hit) - len(tagged)))
    if tagged:
        bytag = collections.Counter(t for h in tagged for t in ltags.get(h[2], []))
        print("  tag breakdown of the real cost: %s" % dict(bytag.most_common()))
    print("\nnewly barred, by region:")
    for r, n in byreg.most_common():
        print("   %-34s %d" % (r, n))
    print("\nworst graceless tiles:")
    for t, n in tiles.most_common(8):
        print("   m60_%02d_%02d  %d check(s)" % (t[0], t[1], n))
    if args.list:
        print("\nevery newly barred check:")
        for (r, name, a, f, t) in sorted(hit):
            print("   m60_%02d_%02d  ap %-9s f%-11s %s" % (t[0], t[1], a, f, name[:64]))
    print("\nRead this as a FILL change. If the surface can afford it, regen and then run")
    print("gen_sweep.ps1 + run_fill_regression.ps1 -- a shrinking surface is exactly the kind of")
    print("thing that turns into an intermittent FillError two weeks later.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
