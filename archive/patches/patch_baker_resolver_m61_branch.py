#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_baker_resolver_m61_branch.py

Adds a NEW m61 (Shadow of the Erdtree, "Land of Shadow") overworld-tile branch
to CompApRegionForMap in SoulsRandomizers/RandomizerCommon/EnemyRandomizer.cs.

RUN ON WINDOWS. The Linux mount serves stale copies; this script edits the real
CRLF file in place. It is idempotent (skips if an m61_ branch is already present)
and CRLF-preserving (binary read/write).

Anchor: inserts the new m61 block IMMEDIATELY BEFORE the existing m60 handling,
which begins with the comment line:
    // Overworld tiles m60_XX_YY_00: classify by the FogMod-style XX/YY band. These
A count==1 guard protects the anchor. The m61 block is a DISTINCT switch from the
m60 switch, so it will not collide with a parallel m60-gaps patch.

ATTRIBUTION NOTE (best-effort): m61 has NO complete public tile->region table.
HIGH-confidence tiles are anchored on the soulsmodding map list (a DLC legacy
dungeon "Connects to m61_XX_YY_00" + its grace region). MED tiles are geographic
interpolation between anchors. LOW tiles are guesses (flagged). YY rises north,
XX rises east (derived from the anchors). Unattributable tiles fall through to
`default: return null;` (graceful v1 fallback) -- they are listed in the report.
"""

import io
import sys

CS_PATH = r"C:\Users\alari\Documents\er-archipelago\SoulsRandomizers\RandomizerCommon\EnemyRandomizer.cs"

# Anchor: the m60 block's leading comment line (matched as a substring, CRLF-agnostic).
ANCHOR = b"// Overworld tiles m60_XX_YY_00: classify by the FogMod-style XX/YY band. These"

# Already-applied marker.
IDEMPOTENCY_MARKER = b'StartsWith("m61_")'

# 16-space indentation matching the body of CompApRegionForMap (same as the m60 block).
IND = "                "

# The m61 block to insert. Built as text, then encoded with CRLF line endings.
# Cases are grouped by AP region (names verified byte-for-byte against
# Archipelago/worlds/eldenring/locations.py region_order_dlc).
M61_BLOCK_LINES = [
    "// Overworld tiles m61_XX_YY_00: Land of Shadow (SotE DLC). BEST-EFFORT band",
    "// attribution -- no complete public m61 tile->region table exists. HIGH = anchored",
    "// on a DLC legacy-dungeon 'Connects to m61_XX_YY' + its grace region (soulsmodding",
    "// map list); MED = geographic interpolation between anchors; LOW = guess. YY rises",
    "// north, XX rises east. Parse mirrors the m60 block. Unmatched -> null (v1 fallback).",
    'if (msbMap.StartsWith("m61_") && msbMap.Length >= 9)',
    "{",
    "    int compTx, compTy;",
    "    if (int.TryParse(msbMap.Substring(4, 2), out compTx)",
    "        && int.TryParse(msbMap.Substring(7, 2), out compTy))",
    "    {",
    '        string compTile = compTx.ToString("D2") + "_" + compTy.ToString("D2");',
    "        switch (compTile)",
    "        {",
    # ---------------- Cerulean Coast ----------------
    "            // Cerulean Coast (m61 DLC; HIGH anchor 47_35/47_36 = Stone Coffin Fissure;",
    "            // far-south coast band YY<=39, rest MED interpolation)",
    '            case "46_38":',
    '            case "46_39":',
    '            case "47_35":',
    '            case "47_36":',
    '            case "47_37":',
    '            case "47_38":',
    '            case "47_39":',
    '            case "48_37":',
    '            case "48_38":',
    '            case "48_39":',
    '            case "49_38":',
    '            case "49_39":',
    '            case "50_37":',
    '            case "50_38":',
    '            case "50_39":',
    '            case "51_39":',
    '            case "53_39":',
    '            case "54_39":',
    '            case "54_40":',
    '            case "55_39":',
    '                return "Cerulean Coast";',
    # ---------------- Charo's Hidden Grave ----------------
    "            // Charo's Hidden Grave (m61 DLC; HIGH anchor 46_40 = Lamenter's Gaol;",
    "            // SW band just N of the coast, rest MED)",
    '            case "44_41":',
    '            case "45_41":',
    '            case "45_42":',
    '            case "46_40":',
    '            case "46_41":',
    '            case "46_42":',
    '            case "47_40":',
    '            case "47_41":',
    '            case "47_42":',
    '                return "Charo\'s Hidden Grave";',
    # ---------------- Gravesite Plain ----------------
    "            // Gravesite Plain (m61 DLC; HIGH anchors 44_43=Belurat, 45_44=Belurat Gaol,",
    "            // 46_44=Rivermouth Cave, 47_46=Fog Rift Catacombs, 48_41=Dragon's Pit,",
    "            // 48_42=Ruined Forge Lava Intake; central-west plain, rest MED)",
    '            case "44_43":',
    '            case "44_45":',  # also covers m61_44_45_10 (parse -> 44_45)
    '            case "45_43":',
    '            case "45_44":',
    '            case "46_43":',
    '            case "46_44":',
    '            case "46_45":',
    '            case "47_43":',
    '            case "47_44":',
    '            case "47_45":',
    '            case "47_46":',
    '            case "48_41":',
    '            case "48_42":',
    '            case "48_43":',
    '                return "Gravesite Plain";',
    # ---------------- Scadu Altus ----------------
    "            // Scadu Altus (m61 DLC; HIGH anchors 48_40/48_41/49_40/49_41=Midra's Manse,",
    "            // 48_44=Ruined Forge of Starfall Past, 48_47/49_47/50_48/51_47=Shadow Keep,",
    "            // 47_47=West Rampart, 49_48=Specimen Storehouse, 50_43=Bonny Gaol,",
    "            // 51_43/52_43=Darklight Catacombs, 51_46=Finger Birthing Grounds;",
    "            // central highlands N of the plain, rest MED)",
    '            case "44_47":',
    '            case "44_48":',
    '            case "45_45":',
    '            case "45_46":',
    '            case "45_47":',
    '            case "46_46":',
    '            case "46_47":',
    '            case "47_47":',
    '            case "47_48":',
    '            case "48_40":',
    '            case "48_44":',
    '            case "48_45":',
    '            case "48_46":',
    '            case "48_47":',
    '            case "48_49":',
    '            case "49_40":',
    '            case "49_41":',
    '            case "49_42":',
    '            case "49_43":',
    '            case "49_44":',
    '            case "49_45":',
    '            case "49_46":',
    '            case "49_47":',
    '            case "49_48":',
    '            case "49_49":',
    '            case "50_40":',
    '            case "50_41":',
    '            case "50_42":',
    '            case "50_43":',
    '            case "50_44":',
    '            case "50_45":',
    '            case "50_46":',
    '            case "50_47":',
    '            case "50_48":',
    '            case "51_40":',
    '            case "51_41":',
    '            case "51_42":',
    '            case "51_43":',
    '            case "51_44":',
    '            case "51_45":',
    '            case "51_46":',
    '            case "51_47":',
    '            case "51_48":',
    '            case "51_49":',
    '            case "52_40":',
    '            case "52_41":',
    '            case "52_42":',
    '            case "52_43":',
    '            case "52_45":',
    '            case "52_46":',
    '            case "53_41":',
    '            case "53_45":',
    '                return "Scadu Altus";',
    # ---------------- Rauh Base ----------------
    "            // Rauh Base (m61 DLC; HIGH anchors 44_46=Scorpion River Catacombs,",
    "            // 48_48=Taylew's Ruined Forge; NE forest/ruins band high XX & YY, rest MED)",
    '            case "44_46":',
    '            case "45_48":',
    '            case "46_48":',
    '            case "48_48":',
    '            case "52_47":',
    '            case "52_48":',
    '            case "52_49":',
    '            case "53_46":',
    '            case "53_47":',
    '            case "53_48":',
    '            case "54_46":',
    '            case "54_47":',
    '            case "54_48":',
    '                return "Rauh Base";',
    # ---------------- Enir Ilim (LOW; off-grid secondary layer) ----------------
    "            // Enir Ilim (m61 DLC; LOW -- the four big _02 tiles 11_09/11_11/12_11/13_12",
    "            // sit far off the overworld band (XX 44-55 / YY 35-49); treated as the",
    "            // far-west endgame ascent layer. GUESS -- verify in-game.)",
    '            case "11_09":',
    '            case "11_11":',
    '            case "12_11":',
    '            case "13_12":',
    '                return "Enir Ilim";',
    "            default: return null;",
    "        }",
    "    }",
    "    return null;",
    "}",
]


def main():
    with io.open(CS_PATH, "rb") as f:
        data = f.read()

    if IDEMPOTENCY_MARKER in data:
        print("[skip] m61 branch already present (found StartsWith(\"m61_\")). No change.")
        return 0

    count = data.count(ANCHOR)
    if count != 1:
        print("[ERROR] expected exactly 1 anchor occurrence, found %d. Aborting." % count)
        print("        anchor = %r" % ANCHOR)
        return 1

    # Build the insert text with CRLF, each line prefixed by the 16-space indent.
    block_text = "".join(IND + line + "\r\n" for line in M61_BLOCK_LINES)
    block_bytes = block_text.encode("utf-8")

    # Insert immediately before the anchor line. The anchor begins a line that is
    # itself indented with IND; we splice in front of that indentation by finding
    # the start of the anchor's indented line.
    idx = data.find(ANCHOR)
    # Walk back over the leading indentation (spaces) so our block lands on its own
    # full lines and the anchor line keeps its original indent.
    line_start = idx
    while line_start > 0 and data[line_start - 1:line_start] in (b" ",):
        line_start -= 1

    new_data = data[:line_start] + block_bytes + data[line_start:]

    with io.open(CS_PATH, "wb") as f:
        f.write(new_data)

    print("[ok] inserted m61 branch (%d source lines) before the m60 block." % len(M61_BLOCK_LINES))
    print("[ok] file grew by %d bytes." % (len(new_data) - len(data)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
