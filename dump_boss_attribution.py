#!/usr/bin/env python3
"""
dump_boss_attribution.py -- capture the VANILLA boss attribution as a committed static JSON the apworld
reads at generation time (so hints can name the boss whose location holds each check).

WHY: the boss attribution {check -> nearest field/dungeon/capstone boss} is purely geometric (check &
boss positions, region centroids) -- a pure function of one bake's coords, independent of the AP fill.
So it can be captured ONCE and reused for every seed. The C# baker already emits it into apconfig.json
as sweep_flags { defeatFlag : [apLocId,...] }; this tool inverts that into { apLocId : [defeatFlag,
bossName] } and names each flag from enemy.txt. Phrased as the VANILLA boss' location, the hint stays
useful even under enemy_rando (it's a landmark: "the check where Night's Cavalry stands in vanilla").

INPUT:
  argv[1] (optional) = path to a FULL-CONTENT apconfig.json (DLC on, no region sealing, enemy_rando off)
                       so the dump covers every check. Default: ./apconfig.json.
  enemy.txt          = SoulsRandomizers/diste/Base/enemy.txt (DefeatFlag -> ExtraName/Name).
OUTPUT:
  Archipelago/worlds/eldenring/boss_attribution.json = { "apLocId": [defeatFlag, "Boss Name"], ... }
  Only BOSS flags (>= 1_000_000); grace lit-flags (small) are ignored. A check under several boss flags
  takes the lowest-distance one the baker already chose (sweep_flags lists each apLocId once per flag;
  we keep the first boss flag seen).

Run on Windows after a full bake, then commit boss_attribution.json. Re-run only when content/version
changes. Pure stdlib.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
APCONFIG = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "apconfig.json")
ENEMY = os.path.join(ROOT, "SoulsRandomizers", "diste", "Base", "enemy.txt")
OUT = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "boss_attribution.json")
BOSS_FLAG_MIN = 1_000_000  # boss DefeatFlags are >= 1e6; grace lit-flags are small (apconfig convention)


def parse_enemy_names(path):
    """flag -> human name (ExtraName preferred, else the most recent Name: cXXXX id)."""
    flag2name = {}
    last_name = None
    pending = None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = re.match(r"\s*Name:\s*(\S+)", line)
            if m:
                last_name = m.group(1)
                continue
            m = re.match(r"\s*DefeatFlag:\s*(\d+)", line)
            if m:
                pending = int(m.group(1))
                flag2name.setdefault(pending, last_name or str(pending))  # fallback until ExtraName
                continue
            m = re.match(r"\s*ExtraName:\s*(.+?)\s*$", line)
            if m and pending is not None:
                flag2name[pending] = m.group(1)
                pending = None
    return flag2name


def main():
    for p in (APCONFIG, ENEMY):
        if not os.path.isfile(p):
            sys.exit("ERROR: not found: %s" % p)
    cfg = json.load(open(APCONFIG, encoding="utf-8"))
    sweep = cfg.get("sweep_flags")
    if not sweep:
        sys.exit("ERROR: %s has no sweep_flags (bake with dungeon_sweep=bosses). Aborting." % APCONFIG)
    flag2name = parse_enemy_names(ENEMY)

    attribution = {}      # apLocId(str) -> [flag, name]
    missing_names = set()
    for flag_s, loc_ids in sweep.items():
        flag = int(flag_s)
        if flag < BOSS_FLAG_MIN:
            continue       # grace lit-flag, not a boss
        name = flag2name.get(flag)
        if name is None:
            missing_names.add(flag)
            name = "boss %d" % flag
        for lid in loc_ids:
            attribution.setdefault(str(lid), [flag, name])  # first boss flag wins

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(attribution, f, ensure_ascii=False, sort_keys=True, indent=0)

    n_bosses = len({v[0] for v in attribution.values()})
    print("Wrote %s: %d checks attributed across %d bosses (source %s)."
          % (OUT, len(attribution), n_bosses, os.path.basename(APCONFIG)))
    if missing_names:
        print("  NOTE: %d boss flag(s) had no enemy.txt name (DLC/edge): %s"
              % (len(missing_names), sorted(missing_names)[:8]))
    print("  Commit boss_attribution.json. (Coverage = whatever checks were in this bake;"
          " use a FULL-content bake for all regions.)")


if __name__ == "__main__":
    main()
