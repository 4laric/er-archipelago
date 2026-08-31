#!/usr/bin/env python3
"""Emit boss-gated graces from EMEVD common event 9005810 (#358)."""
import csv
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ART = os.path.join(REPO, "elden_ring_artifacts")
EVENT = os.path.join(ART, "event")
BONFIRE = os.path.join(ART, "vanilla_er", "vanilla_er", "BonfireWarpParam.csv")
OUT = os.path.join(REPO, "greenfield", "boss_gated_graces.tsv")
MIN_ROWS = 49  # complete 1.17 corpus, measured 2026-08-04
INIT = re.compile(
    r"InitializeCommonEvent\(\s*\d+\s*,\s*9005810\s*,\s*(\d+)\s*,\s*\d+\s*,\s*\d+\s*,\s*(\d+)\s*,"
)


def derive():
    entity_to_flag = {}
    with open(BONFIRE, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                entity_to_flag.setdefault(row["bonfireEntityId"], int(row["eventflagId"]))
            except (KeyError, ValueError):
                continue
    rows = {}
    unresolved = []
    for path in sorted(glob.glob(os.path.join(EVENT, "m*.emevd.dcx.js"))):
        map_tile = os.path.basename(path).split(".emevd", 1)[0]
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                match = INIT.search(line)
                if not match:
                    continue
                gate_flag, asset = map(int, match.groups())
                grace_flag = entity_to_flag.get(str(asset))
                if grace_flag is None:
                    unresolved.append((map_tile, gate_flag, asset))
                    continue
                rows.setdefault(grace_flag, (map_tile, asset, gate_flag))
    if unresolved:
        raise SystemExit("FATAL: unresolved 9005810 grace assets: %r" % unresolved[:8])
    if len(rows) < MIN_ROWS:
        raise SystemExit("FATAL: derived %d boss-gated graces; floor is %d" % (len(rows), MIN_ROWS))
    return rows


def main():
    rows = derive()
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("grace_flag\tmap_tile\tasset_entity\tgate_flag\tgate_source\n")
        for grace_flag, (map_tile, asset, gate_flag) in sorted(rows.items()):
            fh.write(f"{grace_flag}\t{map_tile}\t{asset}\t{gate_flag}\temevd:9005810\n")
    print("boss_gated_graces: %d rows -> %s" % (len(rows), OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
