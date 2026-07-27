#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""datamine_game_areas.py -- boss arenas from GameAreaParam: defeat flag, position, rune reward.

Emits greenfield/game_areas.tsv. GameAreaParam is the game's own boss-arena table and arrived
2026-07-27 with the params glob; nothing in this repo consumed it before.

WHAT IT GIVES US THAT WE DID NOT HAVE
  * defeat flag per arena, straight from the param -- an INDEPENDENT oracle for the boss
    corpora we derive from EMEVD (boss_area_regions.tsv, boss_sweeps, the healthbar sweep).
    Two derivations that disagree is a finding; one derivation is a hope.
  * ARENA POSITION WITHOUT MSBs. bossPosX/Y/Z + bossMapAreaNo/BlockNo/MapNo put a boss at a
    world coordinate using only params. The MSBs are the input we still cannot bundle, so a
    spatial oracle that does not need them is worth a lot -- it bears directly on the open
    Stormhill/Stormveil boundary defect, where the question is literally "which side of a line
    is Margit's arena on".
  * bonusSoul -- FromSoft's own difficulty ordering, a DERIVED input for boss scaling tiers
    instead of a hand-assigned one (CONTRIBUTING: derive the datum).

🛑 THIS IS A PARTITION, NOT THE UNIVERSE. 216 rows is the rune-award arena set, not every boss:
the healthbar sweep finds 249. Rows here that are missing from the sweep, and sweep bosses
missing here, are both interesting -- and neither is automatically a bug. The tool reports the
overlap both ways and refuses to call either side authoritative.

🛑 OVERWORLD ARENA COORDS ARE TILE-LOCAL and need the same fold as everything else
(build_check_browser.world_xz). They are emitted BOTH ways -- raw local and folded global -- with
the folded columns blank for interiors, so no consumer has to guess which frame it is holding.

Run:  python tools/gen_inputs.py --extract <dir> && python tools/datamine_game_areas.py --inputs <dir>
"""
import argparse
import csv
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_check_browser import read_tsv, world_xz  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _int(v, default=0):
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return default


def _float(v):
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return 0.0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--inputs", default=os.path.join(os.path.dirname(REPO), "inputs"))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    gf = os.path.join(args.repo, "greenfield")
    src = os.path.join(args.inputs, "vanilla_er", "vanilla_er", "GameAreaParam.csv")
    if not os.path.exists(src):
        sys.exit(f"FATAL: {src} not found. Run tools/gen_inputs.py --extract first.")

    with open(src, encoding="utf-8", errors="replace") as fh:
        rows = [r for r in csv.DictReader(fh) if r.get("ID", "").strip().isdigit()]

    out = []
    for r in rows:
        rid = _int(r["ID"])
        defeat = _int(r.get("defeatBossFlagId"))
        a, b, m = (_int(r.get("bossMapAreaNo")), _int(r.get("bossMapBlockNo")),
                   _int(r.get("bossMapNo")))
        # mapAreaNo/BlockNo/MapNo -> the map id the rest of the repo speaks
        map_id = f"m{a:02d}_{b:02d}_{m:02d}_00" if a else ""
        px, py, pz = (_float(r.get("bossPosX")), _float(r.get("bossPosY")),
                      _float(r.get("bossPosZ")))
        w = world_xz(map_id[:-3], px, pz) if map_id.startswith("m6") else None
        out.append({
            "area_id": rid,
            "defeat_flag": defeat,
            "flag_equals_id": "yes" if defeat == rid else ("no" if defeat else "-"),
            "found_flag": _int(r.get("foundBossFlagId")),
            "challenge_flag": _int(r.get("bossChallengeFlagId")),
            "bonus_soul": _int(r.get("bonusSoul_single") or r.get("bonusSoul")),
            "boss_map": map_id,
            "local_x": round(px, 2), "local_y": round(py, 2), "local_z": round(pz, 2),
            # folded ONLY for the overworld; blank means "interior, local frame, do not fold"
            "world_gx": round(w[1], 1) if w else "",
            "world_gz": round(w[2], 1) if w else "",
        })
    out.sort(key=lambda x: x["area_id"])

    # --- cross-check against what we already derive ----------------------------------
    ours = set()
    p = os.path.join(gf, "boss_area_regions.tsv")
    if os.path.exists(p):
        for r in read_tsv(p):
            for k in ("flag", "boss_flag", "defeat_flag"):
                if r.get(k, "").isdigit():
                    ours.add(int(r[k]))
                    break
    theirs = {r["defeat_flag"] for r in out if r["defeat_flag"]}
    both, only_ours, only_theirs = ours & theirs, ours - theirs, theirs - ours

    out_path = args.out or os.path.join(gf, "game_areas.tsv")
    hdr = list(out[0].keys())
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# AUTO-GENERATED by tools/datamine_game_areas.py -- DO NOT EDIT, re-emit.\n")
        fh.write("# GameAreaParam: one row per boss ARENA (rune-award set, 216 rows).\n")
        fh.write("# 🛑 A PARTITION, not every boss -- the healthbar sweep finds 249. Rows here\n")
        fh.write("#    absent from that sweep, and sweep bosses absent here, are both worth a\n")
        fh.write("#    look; neither table is authoritative over the other.\n")
        fh.write("# 🛑 local_* is MAP-LOCAL. world_gx/gz are folded (tile*256+local) and are\n")
        fh.write("#    populated ONLY for m60/m61 overworld arenas; blank = interior, do not fold.\n")
        fh.write("\t".join(hdr) + "\n")
        for r in out:
            fh.write("\t".join(str(r[h]) for h in hdr) + "\n")

    print(f"wrote {out_path}  ({len(out)} arenas)")
    print(f"  with a defeat flag        : {sum(1 for r in out if r['defeat_flag'])}")
    print(f"  defeat flag == row id     : {sum(1 for r in out if r['flag_equals_id'] == 'yes')}")
    print(f"  with an overworld position: {sum(1 for r in out if r['world_gx'] != '')}")
    print(f"  with any position         : {sum(1 for r in out if r['boss_map'])}")
    print(f"  bonusSoul range           : {min(r['bonus_soul'] for r in out)}"
          f" .. {max(r['bonus_soul'] for r in out)}")
    print(f"\n  vs boss_area_regions.tsv ({len(ours)} flags):")
    print(f"    in BOTH                 : {len(both)}")
    print(f"    only in boss_area_regions: {len(only_ours)}   <- EMEVD-derived, no arena row")
    print(f"    only in GameAreaParam    : {len(only_theirs)}   <- arenas our derivation misses")
    print(f"\n  map spread: {dict(Counter(r['boss_map'][:3] for r in out if r['boss_map']).most_common(6))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
