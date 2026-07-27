#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_msb_event_coords.py -- WINDOWS-ONLY. Does an MSB Event record carry a position?

Answers the one question SPEC-msb-event-coords.md cannot answer from the bundle, and answers it
in about a minute. Run it BEFORE building anything.

THE QUESTION. 505 live checks are seen by `msb_flag_region` (so their MSB record IS parsed and
DOES identify a map) but have no coordinate in `item_grace_coords.tsv`. 537 of the 546 missing
rows are `source=event` with `treasure_name=common90005300` -- awarded by a shared common event
rather than by a positioned Treasure part. Whether that Event record carries, or points at,
a usable XYZ is UNCONFIRMED.

  * If it does  -> extend datamine_item_grace_coords per the spec; ~505 checks gain a position.
  * If it does not -> the spec is DEAD. Delete it and record the finding, the way the place-name
    route was measured and killed (AGENTS.md, DESC-TRIAGE).

This prints the raw record. It does not decide -- a probe that draws a conclusion is a
derivation, and this one is meant to inform a human.

Run on the box with elden_ring_artifacts/:
    python tools/probe_msb_event_coords.py
    python tools/probe_msb_event_coords.py --flag 10007085 --map m10_00
"""
import argparse
import glob
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Sampled from greenfield/msb_flag_region.tsv where source=event and the flag has no coords.
# Spread across an interior and two overworld tiles on purpose: if only one shape resolves,
# that is itself the finding.
DEFAULT_CASES = [
    ("10007085", "m10_00", "10001085"),          # Stormveil interior
    ("1033417400", "m60_33_41", "1033410400"),   # overworld, fine tile
    ("1034427400", "m60_34_42", "1034420400"),   # overworld, fine tile
]


def find_msb(artifacts, map_prefix):
    """The witchy'd MSB xml for a map prefix, whatever layout the box uses."""
    pats = [
        os.path.join(artifacts, "**", f"{map_prefix}_*.msb.xml"),
        os.path.join(artifacts, "**", f"{map_prefix}_*.msb.json"),
        os.path.join(artifacts, "**", f"{map_prefix}*.msb.xml"),
    ]
    for p in pats:
        hits = sorted(glob.glob(p, recursive=True))
        if hits:
            return hits[0]
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--artifacts", default=os.path.join(REPO, "elden_ring_artifacts"))
    ap.add_argument("--flag")
    ap.add_argument("--map")
    ap.add_argument("--lot")
    ap.add_argument("--context", type=int, default=40,
                    help="lines of surrounding record to print")
    args = ap.parse_args()

    if not os.path.isdir(args.artifacts):
        sys.exit(f"FATAL: {args.artifacts} not found. This probe is Windows-only -- it needs the "
                 f"MSBs, which are deliberately not in gen_inputs.db.")

    cases = ([(args.flag, args.map, args.lot or args.flag)] if args.flag and args.map
             else DEFAULT_CASES)

    for flag, mp, lot in cases:
        print("=" * 78)
        print(f"flag {flag}   map {mp}   item_lot {lot}")
        path = find_msb(args.artifacts, mp)
        if not path:
            print(f"  no MSB found for {mp} under {args.artifacts} -- check the layout/extension")
            continue
        print(f"  {path}")
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                lines = fh.read().splitlines()
        except OSError as e:
            print(f"  cannot read: {e}")
            continue

        # Look for the LOT id first: an Event that awards it must reference it somewhere.
        hits = [i for i, ln in enumerate(lines) if lot in ln] or \
               [i for i, ln in enumerate(lines) if flag in ln]
        if not hits:
            print(f"  ⚠ neither lot {lot} nor flag {flag} appears in this MSB at all.")
            print("    That is a finding: msb_flag_region attributed the map some OTHER way.")
            continue
        print(f"  {len(hits)} mention(s); showing the first with +/-{args.context} lines.\n")
        i = hits[0]
        for j in range(max(0, i - args.context), min(len(lines), i + args.context)):
            mark = ">>" if j == i else "  "
            print(f"   {mark} {lines[j].rstrip()[:150]}")
        print()

    print("=" * 78)
    print("WHAT TO LOOK FOR, in order:")
    print("  1. a Position / Translate / posX,posY,posZ on THIS record  -> emit it directly")
    print("  2. an entity/part reference (PartName, entityId, attachPart) -> resolve THAT part's")
    print("     position; that is the corpse or asset the player interacts with")
    print("  3. neither, on any of the three cases -> the spec is DEAD; delete it and record")
    print("     the finding in AGENTS.md so nobody has the idea again")
    print("\nPaste the output back and I will write the extraction against what is actually there,")
    print("rather than against what I assume is there.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
