#!/usr/bin/env python3
"""CENSUS the overworld checks whose region is a GUESS, not an answer.

WHY
---
A check's region and the in-game KICK are decided in two id spaces that are related only by hand
(gen_data.py:381: "THIS BLOCK IS IN THE KICK ID SPACE, AND EVERYTHING ELSE AROUND IT IS NOT"):

  checks : tile -> ANCHOR/ANCHOR61 -> BonfireWarpParam.bonfireSubCategoryId -> REGION_GROUPS
  kick   : the player's PlayRegionParam volume -> ID // 100          -> PLAY_REGION_GROUPS

`_m61_tile_region` falls through curated -> the tile's own grace -> PlayRegionParam's row for the
tile -> **nearest grace tile**. That last step is a guess, and nothing downstream marks it as one, so
a guessed region is indistinguishable from a measured one at every later gate.

bobler, 2026-08-10 (#523): a boss standing on Shadow Keep's measured ground (69300, kick says
unlocked, correctly) handed over 28 checks labelled Scadu Altus -- a region whose Lock he did not
hold. Only 2 of the 28 sat on the trigger's own tile, so the relabel that was planned for four
Hinterland tiles would have moved 2 checks and left 26. The class is what needs fixing, not the tile.

WHAT THIS EMITS
---------------
Every overworld check, bucketed by HOW its region was decided:

  known: tile has its own grace     -- first-hand evidence, the tile's warp bucket
  known: PlayRegionParam row        -- the game's own row for that tile, in the kick's id space
  ambiguous: tile spans >1 kick region  -- a row exists but names two regions
  CONFLICT: grace says X, row says Y    -- both sources speak and disagree
  GUESSED: nearest-neighbour hop    -- neither source knows this tile

`tile_pr`'s own docstring measures the guess: 98.1% agreement on an anchored tile, **84.8% one tile
away** (65 disagreements in 429 checks). This tool names which checks are in that population, so the
triage is over a list rather than over the whole overworld.

🛑 It DERIVES nothing and FIXES nothing. It reads committed tables only -- no MSBs, no EMEVD, no gen
run -- so it can run on any checkout, including CI's artifact-free tier.

Run:  python3 tools/triage_check_region_ambiguity.py            # report
      python3 tools/triage_check_region_ambiguity.py --emit     # + greenfield/check_region_triage.tsv
"""
import argparse
import ast
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GF = os.path.join(ROOT, "greenfield")
OUT = os.path.join(GF, "check_region_triage.tsv")


def _table(src, name):
    """Parse a `NAME = { ... }` literal out of region_groups.py without importing it."""
    i = src.index(name + " = {")
    j = src.index("\n}", i)
    body = re.sub(r"#[^\n]*", "", src[i + len(name) + 3:j + 2]).replace("HUB", '"Roundtable Hold"')
    return ast.literal_eval(body)


def tile_of(flag):
    """Overworld tile from a check's event flag: 10=m60, 20=m61, then XX, YY."""
    s = str(flag)
    if len(s) == 10 and s[:2] in ("10", "20"):
        return "m6%s_%s_%s" % ("0" if s[:2] == "10" else "1", s[2:4], s[4:6])
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit", action="store_true", help="write greenfield/check_region_triage.tsv")
    args = ap.parse_args()

    src = open(os.path.join(GF, "region_groups.py"), encoding="utf-8").read()
    warp_owner = {b: r for r, bs in _table(src, "REGION_GROUPS").items() for b in bs}
    kick_owner = {b: r for r, bs in _table(src, "PLAY_REGION_GROUPS").items() for b in bs}

    grace_tile = defaultdict(set)                     # tile -> {warp bucket}
    for ln in open(os.path.join(GF, "grace_flags.tsv"), encoding="utf-8"):
        p = ln.rstrip("\n").split("\t")
        if p and p[0].isdigit() and len(p) > 2:
            grace_tile[p[1]].add(int(p[2]))

    kick_tile = defaultdict(set)                      # tile -> {PlayRegionParam bucket}
    for ln in open(os.path.join(GF, "play_region_buckets.tsv"), encoding="utf-8"):
        if ln[:1] == "#" or ln.startswith("bucket"):
            continue
        p = ln.rstrip("\n").split("\t")
        if len(p) < 3 or not p[0].isdigit():
            continue
        for t in p[2].split(";"):
            if t.strip():
                kick_tile[t.strip()].add(int(p[0]))

    data = open(os.path.join(GF, "eldenring", "data.py"), encoding="utf-8").read()
    checks = [(m.group(1), int(m.group(2)), int(m.group(3)))
              for m in re.finditer(r"\('([^']*)',\s*(\d+),\s*(\d+)\)", data)]

    cls, rows = Counter(), []
    for label, ap_id, flag in checks:
        t = tile_of(flag)
        if not t:
            continue
        region = label.split(" :: ")[0]
        g = {warp_owner.get(b) for b in grace_tile.get(t, ())} - {None}
        k = {kick_owner.get(b) for b in kick_tile.get(t, ())} - {None}
        if g and k and g != k:
            how = "CONFLICT"
        elif g:
            how = "known-grace"
        elif k and len(k) == 1:
            how = "known-row"
        elif k:
            how = "ambiguous-row"
        else:
            how = "GUESSED"
        cls[how] += 1
        if how != "known-grace" and how != "known-row":
            rows.append((t, region, ap_id, flag, how,
                         ",".join(sorted(g)) or "-", ",".join(sorted(k)) or "-", label))

    total = sum(cls.values())
    print("check region provenance -- %d overworld checks" % total)
    for how, n in cls.most_common():
        print("  %5d  %5.1f%%  %s" % (n, 100.0 * n / total, how))

    tiles = defaultdict(int)
    for r in rows:
        tiles[r[0]] += 1
    print("\nNEEDS TRIAGE: %d checks across %d tiles" % (len(rows), len(tiles)))
    for t, n in sorted(tiles.items(), key=lambda kv: -kv[1])[:15]:
        regs = sorted({r[1] for r in rows if r[0] == t})
        print("  %-12s %3d check(s)   label=%s" % (t, n, ",".join(regs)))

    if args.emit:
        with open(OUT, "w", encoding="utf-8", newline="\n") as f:
            f.write("# checks whose region was NOT decided by first-hand evidence for their tile.\n")
            f.write("# how: GUESSED (nearest-neighbour hop) | ambiguous-row (tile spans 2 kick\n")
            f.write("#      regions) | CONFLICT (grace and PlayRegionParam row disagree)\n")
            f.write("# NOT a defect list -- a TRIAGE list. tools/triage_check_region_ambiguity.py\n")
            f.write("map_tile\tregion\tap_id\tflag\thow\tgrace_says\tkick_row_says\tlabel\n")
            for r in sorted(rows):
                f.write("\t".join(str(x) for x in r) + "\n")
        print("\n-> %s (%d rows)" % (OUT, len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
