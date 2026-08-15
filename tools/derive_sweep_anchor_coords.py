#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""derive_sweep_anchor_coords.py -- anchor a coordinate-less check at its SWEEP BOSS's arena.

Emits greenfield/sweep_anchor_coords.tsv. AP-free, MSB-free: reads only the committed
game_areas.tsv, item_grace_coords.tsv and greenfield/eldenring/boss_sweeps.py.

WHY THIS EXISTS, AND WHY IT IS NOT derive_boss_reward_coords.py
--------------------------------------------------------------
derive_boss_reward_coords.py asks a hard question -- WHICH ARENA does the EMEVD block that AWARDS
this check wait on -- and refuses 66 of 90 candidates because the block names two arenas, the NPC
relocates, or the flag is a gate rather than an award site. Those refusals are correct and must
stay: that is the HIGH-CONFIDENCE table and this one must never be merged into it.

This asks a weaker question with a much wider answer: which boss's sweep does this check belong to,
and where is that boss fought? DUNGEON_SWEEPS already groups 4045 member checks under 218 trigger
flags, and GameAreaParam (game_areas.tsv) carries 216 arenas WITH map-local positions. The join
needs no EMEVD block at all.

THE CLAIM IS WEAKER AND MUST STAY LABELLED AS SUCH. A sweep MEMBER sits BEHIND its trigger boss,
not AT it -- boss_sweeps' own docstring scopes members by class (legacy = region-divvy,
catacomb/cave/tunnel = map-local, field = nearest-boss Chebyshev<=2 neighbourhood), and #445
records that a trigger can sit in a region its members are not in. So this is "somewhere in that
boss's area", never a measured position. Every row carries anchor=sweep_arena, and NOTHING
downstream may present it with the wording used for a real item_grace_coords position.

FOUR REFUSALS, written into the emitted header with their candidates so no count hides a guess:
  * ALREADY POSITIONED -- the check has a real item_grace_coords row. Never overwritten.
  * NO ARENA           -- the trigger flag has no GameAreaParam row, or no position in it.
  * AMBIGUOUS SWEEP    -- the check is a member of >1 sweep whose arenas DISAGREE. Picking the
                          first would be a coin flip presented as a datum -- the thing the sibling
                          tool refuses to do.
                          🛑 THIS GUARD HAS NEVER FIRED, AND SAYING SO IS THE POINT. Measured
                          2026-08-15: DUNGEON_SWEEPS holds 4045 member slots across 218 triggers
                          and 4045 DISTINCT members -- it is a PARTITION, so no check can be
                          claimed twice on current data. It is kept as a REGRESSION RATCHET, not
                          a live filter: #363 (multi-boss dungeon sweeps duplicate) is exactly the
                          defect that would break the partition, and if it returns this refusal
                          starts counting instead of the tool silently anchoring a check at the
                          wrong boss. An unfired guard is UNTESTED -- test_gf_sweep_anchor_coords
                          drives it with a synthetic double-claim rather than trusting the zero.
  * ARENA AT ORIGIN    -- local_x/y/z all 0.0. game_areas.tsv's row 0 is literally that; a 0,0,0
                          anchor is an unset field, not a place.
"""
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GF = os.path.join(ROOT, "greenfield")
OUT = os.path.join(GF, "sweep_anchor_coords.tsv")


def load_arenas():
    """defeat_flag -> (boss_map, x, y, z). Skips rows with no usable position."""
    arenas, at_origin = {}, set()
    with open(os.path.join(GF, "game_areas.tsv"), encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            p = line.rstrip("\n").split("\t")
            if len(p) < 10 or not p[1].isdigit():
                continue
            try:
                x, y, z = float(p[7]), float(p[8]), float(p[9])
            except ValueError:
                continue
            if x == 0.0 and y == 0.0 and z == 0.0:
                at_origin.add(p[1])
                continue
            arenas[p[1]] = (p[6], x, y, z)
    return arenas, at_origin


def load_positioned():
    have = set()
    with open(os.path.join(GF, "item_grace_coords.tsv"), encoding="utf-8") as fh:
        for line in fh:
            p = line.split("\t")
            if len(p) >= 2 and p[0] == "item":
                have.add(p[1])
    return have


def load_sweeps():
    """trigger flag -> [ap location ids], read TEXTUALLY. Importing boss_sweeps would drag in the
    package __init__ -> core -> BaseClasses, and this tool is deliberately AP-free."""
    src = open(os.path.join(GF, "eldenring", "boss_sweeps.py"), encoding="utf-8").read()
    body = src.split("DUNGEON_SWEEPS = {", 1)[1]
    sweeps = {}
    for flag, members in re.findall(r"^\s*(\d+): \[([\d, ]*)\],", body, re.M):
        sweeps[flag] = [m.strip() for m in members.split(",") if m.strip()]
    return sweeps


def load_loc_flags():
    src = open(os.path.join(GF, "eldenring", "data.py"), encoding="utf-8").read()
    return {lid: flag for _d, lid, flag in
            re.findall(r"\(['\"](.+?)['\"], (\d+), (\d+)\)", src)}


def main():
    arenas, at_origin = load_arenas()
    positioned = load_positioned()
    sweeps = load_sweeps()
    loc_flag = load_loc_flags()

    claims = defaultdict(set)
    for trigger, members in sweeps.items():
        if trigger in arenas:
            for lid in members:
                claims[lid].add((arenas[trigger], trigger))

    rows, refused = [], defaultdict(list)
    for trigger, members in sorted(sweeps.items(), key=lambda kv: int(kv[0])):
        for lid in members:
            flag = loc_flag.get(lid)
            if flag and flag in positioned:
                refused["ALREADY POSITIONED"].append(lid)
                continue
            if trigger not in arenas:
                refused["ARENA AT ORIGIN" if trigger in at_origin else "NO ARENA"].append(
                    "%s (trigger %s)" % (lid, trigger))
                continue
            if len({c[0] for c in claims[lid]}) > 1:
                refused["AMBIGUOUS SWEEP"].append(
                    "%s: triggers %s" % (lid, ",".join(sorted(t for _a, t in claims[lid]))))
                continue
            bmap, x, y, z = arenas[trigger]
            rows.append((lid, flag or "", trigger, bmap, x, y, z))

    seen, uniq = set(), []
    for r in rows:
        if r[0] not in seen:
            seen.add(r[0])
            uniq.append(r)

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# AUTO-GENERATED by tools/derive_sweep_anchor_coords.py -- DO NOT EDIT, re-emit.\n")
        fh.write("# WEAK ANCHOR, NOT A MEASUREMENT. Each row says: this check is a MEMBER of the\n")
        fh.write("# sweep triggered by <trigger_defeat_flag>, and that boss is fought at <x,y,z>.\n")
        fh.write("# A member sits BEHIND its trigger, not AT it (boss_sweeps scopes members by\n")
        fh.write("# class, and #445 records triggers outside their members' region). Present it as\n")
        fh.write("# an AREA, never with the wording used for an item_grace_coords position.\n")
        fh.write("# Positions are MAP-LOCAL, the same space as item_grace_coords.\n#\n")
        fh.write("# EMITTED %d.\n" % len(uniq))
        for kind in ("AMBIGUOUS SWEEP", "NO ARENA", "ARENA AT ORIGIN", "ALREADY POSITIONED"):
            got = refused.get(kind, [])
            fh.write("# REFUSED %d %s%s\n" % (len(got), kind, ":" if got else ""))
            for item in got[:40]:
                fh.write("#    %s\n" % item)
            if len(got) > 40:
                fh.write("#    ... %d more\n" % (len(got) - 40))
        fh.write("ap_location_id\tcheck_flag\ttrigger_defeat_flag\tboss_map\tlocal_x\tlocal_y\tlocal_z\tanchor\n")
        for lid, flag, trigger, bmap, x, y, z in sorted(uniq, key=lambda r: int(r[0])):
            fh.write("%s\t%s\t%s\t%s\t%s\t%s\t%s\tsweep_arena\n" % (lid, flag, trigger, bmap, x, y, z))

    print("wrote %s" % os.path.relpath(OUT, ROOT))
    print("  emitted %d check(s) anchored at a sweep arena" % len(uniq))
    for kind in ("AMBIGUOUS SWEEP", "NO ARENA", "ARENA AT ORIGIN", "ALREADY POSITIONED"):
        print("  refused %6d  %s" % (len(refused.get(kind, [])), kind))
    if not uniq:
        sys.exit("FATAL: emitted nothing. An empty result is a failure, not a clean run.")


if __name__ == "__main__":
    main()
