#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""derive_boss_reward_coords.py -- position boss REWARDS at their boss's arena.

Emits greenfield/boss_reward_coords.tsv. AP-free, MSB-free: reads only the committed
game_areas.tsv, msb_flag_region.tsv, item_grace_coords.tsv and the bundled EMEVD.

WHY THIS EXISTS. SPEC-msb-spatial-walk.md was CLOSED 2026-07-26 at 3912/4856 positioned checks,
with `event`-source measured DEAD: 20 of 517 resolve (3.9%), because a boss reward is awarded by
EMEVD and has no MSB placement to read a position from. §0 records what would reopen it -- "a new
INPUT, not more effort. Specifically (a) whatever actually positions an event-source award."

`GameAreaParam` is that input. It arrived 2026-07-27 with the params glob and carries 216 boss
arenas WITH positions and no MSB dependency (tools/datamine_game_areas.py -> game_areas.tsv), and
event-source awards are explicitly "BOSS drops (remembrances, great runes, boss rewards)".

THE JOIN. For an unpositioned event-source check, find the `$Event(...)` block in that map's EMEVD
that references the check's flag. If that same block references a GameAreaParam DEFEAT flag, the
event that awards the lot is the event that waits on that boss dying -- so the reward is AT that
boss, and the arena position is a sound anchor for it.

🛑 TWO REFUSALS, AND THEY ARE MOST OF THE STORY. The headline number fell by more than half once
each was applied, and both were found by cross-checking rather than by the join itself:

    60 blocks matched
   -31  AMBIGUOUS: the block names TWO arenas. m10_00's names both 10000800 (Godrick) and
        10000850 (Margit), so "take the first" -- which my first pass did, reporting 59 -- is a
        coin flip presented as a datum.
   - 2  GATE, NOT AWARD SITE: a block can reference a defeat flag because the item is GATED
        behind that boss ("available once X is dead"), which says nothing about WHERE it is.
        lot_gates.tsv already knows this; f400666 and f16007690 are gated BY the very arena we
        anchored them to. (22 of 29 appear in lot_gates at all, but only these 2 are gated by
        their own anchor -- so this refuses exactly the provably-wrong ones.)
    =27 EMITTED

Both refusal lists are written into the tsv header so the counts can never be read as zero.

Honest yield: 27 checks. 4086 -> 4113 of 4875 (83.8% -> 84.4%).

🛑 THE POSITION IS THE ARENA, NOT THE ITEM. It is DERIVED, not measured, which is why it lands in
its own file with a `via` column rather than being merged into item_grace_coords.tsv. A consumer
that wants "near <grace>" is well served by it; a consumer computing a distance to something else
is not. Do not let these rows become indistinguishable from an MSB-measured position -- that is the
whole reason they are kept separate.

Run:  python tools/gen_inputs.py --extract <dir> && python tools/derive_boss_reward_coords.py
"""
import argparse
import glob
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_check_browser import read_tsv, load_module_consts  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# `$Event(<id>, ...)` up to the next one. Crude but sufficient: we only ask "do these two ids
# co-occur inside one event body", never anything about the body's structure.
BLOCK_RE = re.compile(r"\$Event\((\d+),.*?\n(.*?)(?=\n\$Event\(|\Z)", re.S)
ID_RE = re.compile(r"\b(\d{4,10})\b")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--inputs", default=os.path.join(os.path.dirname(REPO), "inputs"))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    gf = os.path.join(args.repo, "greenfield")
    ev_dir = os.path.join(args.inputs, "event")
    if not os.path.isdir(ev_dir):
        sys.exit(f"FATAL: {ev_dir} not found. Run tools/gen_inputs.py --extract first.")

    ga_path = os.path.join(gf, "game_areas.tsv")
    if not os.path.exists(ga_path):
        sys.exit("FATAL: greenfield/game_areas.tsv missing -- run tools/datamine_game_areas.py.")

    arenas = {}
    for r in read_tsv(ga_path):
        if r.get("defeat_flag", "").isdigit() and int(r["defeat_flag"]) and r.get("boss_map"):
            arenas[int(r["defeat_flag"])] = r

    positioned = {int(r["key"]) for r in read_tsv(os.path.join(gf, "item_grace_coords.tsv"))
                  if r.get("kind") == "item" and r.get("key", "").isdigit()}
    LOC = load_module_consts(os.path.join(gf, "eldenring", "data.py"), {"LOCATIONS"})["LOCATIONS"]
    checks = {f for v in LOC.values() for (_n, _a, f) in v}

    targets = {}
    for r in read_tsv(os.path.join(gf, "msb_flag_region.tsv")):
        if not r.get("flag", "").isdigit():
            continue
        f = int(r["flag"])
        if r.get("source") == "event" and f in checks and f not in positioned:
            targets.setdefault(f, r["map_id"])

    by_map = defaultdict(list)
    for f, mp in targets.items():
        by_map[mp].append(f)

    found = defaultdict(set)          # check flag -> {arena defeat flag}
    for mp, flags in sorted(by_map.items()):
        cands = sorted(glob.glob(os.path.join(ev_dir, f"{mp}_*.emevd.dcx.js"))) or \
                sorted(glob.glob(os.path.join(ev_dir, f"{mp}.emevd.dcx.js")))
        if not cands:
            continue
        with open(cands[0], encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        want = set(flags)
        for m in BLOCK_RE.finditer(text):
            ids = {int(x) for x in ID_RE.findall(m.group(2))}
            hit = want & ids
            if not hit:
                continue
            bosses = sorted(b for b in ids if b in arenas)
            if not bosses:
                continue
            # An arena in THIS map is the better candidate when the block names several.
            same = [b for b in bosses if arenas[b]["boss_map"].startswith(mp)]
            for f in hit:
                found[f].update(same or bosses)

    # 🛑 GATE, NOT AWARD SITE. A block can reference a defeat flag because the item is GATED
    # behind that boss ("available once X is dead"), which says nothing about WHERE the item is.
    # lot_gates.tsv already knows which flags gate which checks, so if the arena flag we picked is
    # this check's own gate flag, the reference is a gate and the anchor is unsupported. Measured:
    # 22 of 29 emitted checks appear in lot_gates at all, but only 2 are gated BY the arena flag --
    # so this refuses exactly the 2 that are provably wrong and leaves the rest.
    gated_by = defaultdict(set)
    lg = os.path.join(gf, "lot_gates.tsv")
    if os.path.exists(lg):
        for r in read_tsv(lg):
            if r.get("check_flag", "").isdigit() and r.get("gate_flag", "").isdigit():
                gated_by[int(r["check_flag"])].add(int(r["gate_flag"]))

    emitted, refused, gate_refused = [], [], []
    for f in sorted(found):
        bs = sorted(found[f])
        if len(bs) == 1 and bs[0] in gated_by.get(f, ()):
            gate_refused.append((f, bs[0]))
            continue
        if len(bs) == 1:
            a = arenas[bs[0]]
            emitted.append({
                "flag": f, "map_id": a["boss_map"], "x": a["local_x"], "y": a["local_y"],
                "z": a["local_z"], "via": "boss_arena", "arena_defeat_flag": bs[0],
                "evidence": f"awarding EMEVD block in {targets[f]} references defeat flag {bs[0]}",
            })
        else:
            refused.append((f, bs))

    out_path = args.out or os.path.join(gf, "boss_reward_coords.tsv")
    hdr = ["flag", "map_id", "x", "y", "z", "via", "arena_defeat_flag", "evidence"]
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# AUTO-GENERATED by tools/derive_boss_reward_coords.py -- DO NOT EDIT, re-emit.\n")
        fh.write("# DERIVED positions for boss REWARDS: the arena of the boss whose defeat flag the\n")
        fh.write("# awarding EMEVD block waits on. See SPEC-msb-spatial-walk.md §0 (2026-07-27).\n")
        fh.write("# 🛑 This is the ARENA, not the item's own spot, and it is DERIVED not measured --\n")
        fh.write("#    which is why it lives here and NOT in item_grace_coords.tsv. Keep the `via`\n")
        fh.write("#    column with the row; a consumer must be able to tell these apart.\n")
        fh.write(f"# EMITTED {len(emitted)} unambiguous.\n")
        fh.write(f"# REFUSED {len(refused)} AMBIGUOUS (block named >1 arena -- guessing would be a\n")
        fh.write("#    coin flip presented as a datum). Listed so the count is never read as zero:\n")
        for f, bs in refused:
            fh.write(f"#    refused flag {f}: candidates {','.join(str(b) for b in bs)}\n")
        fh.write(f"# REFUSED {len(gate_refused)} where the arena flag is the check's OWN GATE flag\n")
        fh.write("#    (the block references the boss to GATE the item, not to award it there):\n")
        for f, b in gate_refused:
            fh.write(f"#    refused flag {f}: arena {b} is its gate_flag in lot_gates.tsv\n")
        fh.write("\t".join(hdr) + "\n")
        for r in emitted:
            fh.write("\t".join(str(r[h]) for h in hdr) + "\n")

    print(f"wrote {out_path}")
    print(f"  event-source checks with no position : {len(targets)}")
    print(f"  blocks matched                       : {len(found)}")
    print(f"  EMITTED (unambiguous)                : {len(emitted)}")
    print(f"  REFUSED (ambiguous, >1 arena)        : {len(refused)}")
    print(f"  REFUSED (arena flag GATES the check) : {len(gate_refused)}  {gate_refused or ''}")
    print(f"  coverage {len(positioned)} -> {len(positioned) + len(emitted)} of {len(checks)}"
          f"  ({100*len(positioned)/len(checks):.1f}% -> "
          f"{100*(len(positioned)+len(emitted))/len(checks):.1f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
