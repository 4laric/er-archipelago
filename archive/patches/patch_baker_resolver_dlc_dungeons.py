#!/usr/bin/env python3
"""
patch_baker_resolver_dlc_dungeons.py  (RUN ON WINDOWS)

Adds exact-id MSB -> AP region cases for DLC dungeons (m20/m21/m22/m25/m28/
m40/m41/m42/m43) and base minor dungeons (m30 catacombs, m31 caves, m32
tunnels, m34 divine towers, m35 Shunning-Grounds, m39_20 Ruin-Strewn
Precipice, m12_08 Siofra River - Boss, m11_10 Roundtable Hold, m10_01 Chapel
of Anticipation) to the exact-id switch in CompApRegionForMap.

These are FULL MSB ids (mXX_YY_00_00), distinct from the m60/m61 overworld
tile branches, so this won't collide with the overworld resolver patches.

- Binary read/write, CRLF-preserving.
- Idempotent: aborts (no-op) if `case "m20_00_00_00":` already present.
- Anchors on the unique compound:
      return "Nokron, Eternal City Start";\r\n<20sp>default: break;\r\n
  (count==1 guard; aborts otherwise). New cases are inserted immediately
  before that `default: break;`, matching the switch's 20-space indent.

m45 Colosseums (m45_00/01/02) are intentionally OMITTED -- no region_order
entry represents them.
"""

import sys

CS = r"C:\Users\alari\Documents\er-archipelago\SoulsRandomizers\RandomizerCommon\EnemyRandomizer.cs"

IND = " " * 20  # switch-case indentation (verified via file-API Read at line 1171+)
NL = "\r\n"

IDEMPOTENT_MARKER = b'case "m20_00_00_00":'

# Compound anchor: last existing case line + the switch's default.
ANCHOR = (
    IND + 'case "m12_09_00_00": return "Nokron, Eternal City Start";' + NL +
    IND + "default: break;" + NL
).encode("utf-8")

# (msb_id, region_name, comment-group-header-or-None)
NEW_CASES = [
    # --- Base minor dungeons: m30 Catacombs ---
    ("m30_00_00_00", "Tombsward Catacombs", "Base catacombs (m30)"),
    ("m30_01_00_00", "Impaler's Catacombs", None),
    ("m30_02_00_00", "Stormfoot Catacombs", None),
    ("m30_03_00_00", "Road's End Catacombs", None),
    ("m30_04_00_00", "Murkwater Catacombs", None),
    ("m30_05_00_00", "Black Knife Catacombs", None),
    ("m30_06_00_00", "Cliffbottom Catacombs", None),
    ("m30_07_00_00", "Wyndham Catacombs", None),
    ("m30_08_00_00", "Sainted Hero's Grave", None),
    ("m30_09_00_00", "Gelmir Hero's Grave", None),
    ("m30_10_00_00", "Auriza Hero's Grave", None),
    ("m30_11_00_00", "Deathtouched Catacombs", None),
    ("m30_12_00_00", "Unsightly Catacombs", None),
    ("m30_13_00_00", "Auriza Side Tomb", None),
    ("m30_14_00_00", "Minor Erdtree Catacombs", None),
    ("m30_15_00_00", "Caelid Catacombs", None),
    ("m30_16_00_00", "War-Dead Catacombs", None),
    ("m30_17_00_00", "Giant-Conquering Hero's Grave", None),
    ("m30_18_00_00", "Giants' Mountaintop Catacombs", None),
    ("m30_19_00_00", "Consecrated Snowfield Catacombs", None),
    ("m30_20_00_00", "Hidden Path to the Haligtree", None),
    # --- Base minor dungeons: m31 Caves ---
    ("m31_00_00_00", "Murkwater Cave", "Base caves (m31)"),
    ("m31_01_00_00", "Earthbore Cave", None),
    ("m31_02_00_00", "Tombsward Cave", None),
    ("m31_03_00_00", "Groveside Cave", None),
    ("m31_04_00_00", "Stillwater Cave", None),
    ("m31_05_00_00", "Lakeside Crystal Cave", None),
    ("m31_06_00_00", "Academy Crystal Cave", None),
    ("m31_07_00_00", "Seethewater Cave", None),
    ("m31_09_00_00", "Volcano Cave", None),
    ("m31_10_00_00", "Dragonbarrow Cave", None),
    ("m31_11_00_00", "Sellia Hideaway", None),
    ("m31_12_00_00", "Cave of the Forlorn", None),
    ("m31_15_00_00", "Coastal Cave", None),
    ("m31_17_00_00", "Highroad Cave", None),
    ("m31_18_00_00", "Perfumer's Grotto", None),
    ("m31_19_00_00", "Sage's Cave", None),
    ("m31_20_00_00", "Abandoned Cave", None),
    ("m31_21_00_00", "Gaol Cave", None),
    ("m31_22_00_00", "Spiritcaller Cave", None),
    # --- Base minor dungeons: m32 Tunnels ---
    ("m32_00_00_00", "Morne Tunnel", "Base tunnels (m32)"),
    ("m32_01_00_00", "Limgrave Tunnels", None),
    ("m32_02_00_00", "Raya Lucaria Crystal Tunnel", None),
    ("m32_04_00_00", "Old Altus Tunnel", None),
    ("m32_05_00_00", "Altus Tunnel", None),
    ("m32_07_00_00", "Gale Tunnel", None),  # locations.py spells region "Gale Tunnel"
    ("m32_08_00_00", "Sellia Crystal Tunnel", None),
    ("m32_11_00_00", "Yelough Anix Tunnel", None),
    # --- Base minor dungeons: m34 Divine Towers ---
    ("m34_10_00_00", "Divine Tower of Limgrave", "Base divine towers (m34)"),
    ("m34_11_00_00", "Divine Tower of Liurnia", None),
    ("m34_12_00_00", "Divine Tower of West Altus", None),
    ("m34_13_00_00", "Divine Tower of Caelid", None),
    ("m34_14_00_00", "Divine Tower of East Altus", None),
    ("m34_15_00_00", "Isolated Divine Tower", None),
    # --- Base interiors ---
    ("m35_00_00_00", "Subterranean Shunning-Grounds", "Base interiors"),
    ("m39_20_00_00", "Ruin-Strewn Precipice", None),
    ("m12_08_00_00", "Siofra River", None),   # Siofra River - Boss
    ("m11_10_00_00", "Roundtable Hold", None),
    ("m10_01_00_00", "Stormveil Start", None),  # Chapel of Anticipation = Stormveil intro
    # --- DLC: Belurat / Enir-Ilim (m20) ---
    ("m20_00_00_00", "Belurat", "DLC Belurat / Enir-Ilim (m20)"),
    ("m20_01_00_00", "Enir Ilim", None),
    # --- DLC: Shadow Keep (m21) ---
    ("m21_00_00_00", "Shadow Keep", "DLC Shadow Keep (m21)"),
    ("m21_01_00_00", "Shadow Keep Storehouse", None),  # Specimen Storehouse
    ("m21_02_00_00", "Shadow Keep, West Rampart", None),
    # --- DLC: Stone Coffin Fissure (m22) ---
    ("m22_00_00_00", "Stone Coffin Fissure", "DLC Stone Coffin Fissure (m22)"),
    # --- DLC: Finger Birthing Grounds (m25) -> grace region Scadu Altus ---
    ("m25_00_00_00", "Scadu Altus", "DLC Finger Birthing Grounds (m25) -> grace region"),
    # --- DLC: Midra's Manse (m28) ---
    ("m28_00_00_00", "Midra's Manse", "DLC Midra's Manse (m28)"),
    # --- DLC catacombs (m40) ---
    ("m40_00_00_00", "Fog Rift Catacombs", "DLC catacombs (m40)"),
    ("m40_01_00_00", "Scorpion River Catacombs", None),
    ("m40_02_00_00", "Darklight Catacombs", None),
    # --- DLC gaols (m41) ---
    ("m41_00_00_00", "Belurat Gaol", "DLC gaols (m41)"),
    ("m41_01_00_00", "Bonny Gaol", None),
    ("m41_02_00_00", "Lamenter's Gaol (Upper)", None),  # main region of the gaol
    # --- DLC forges (m42) ---
    ("m42_00_00_00", "Gravesite Plain", "DLC forges (m42); Lava Intake -> grace region"),
    ("m42_02_00_00", "Ruined Forge of Starfall Past", None),
    ("m42_03_00_00", "Taylew's Ruined Forge", None),
    # --- DLC caves/pit (m43) ---
    ("m43_00_00_00", "Rivermouth Cave", "DLC caves/pit (m43)"),
    ("m43_01_00_00", "Dragon's Pit", None),
    # m45 Colosseums (m45_00/01/02) OMITTED -- no region_order entry.
]


def build_block():
    out = []
    for msb, region, header in NEW_CASES:
        if header is not None:
            out.append(IND + "// " + header + NL)
        # escape backslashes then double-quotes for a C# string literal
        esc = region.replace("\\", "\\\\").replace('"', '\\"')
        out.append(IND + 'case "' + msb + '": return "' + esc + '";' + NL)
    return ("".join(out)).encode("utf-8")


def main():
    with open(CS, "rb") as f:
        data = f.read()

    if IDEMPOTENT_MARKER in data:
        print("Already patched (found case \"m20_00_00_00\":). No-op.")
        return 0

    n = data.count(ANCHOR)
    if n != 1:
        print("ABORT: compound anchor found {} times (expected 1).".format(n))
        print("Anchor was:")
        sys.stdout.buffer.write(ANCHOR)
        return 1

    block = build_block()
    # Insert new cases between the last existing case line and `default: break;`.
    keep_case = (IND + 'case "m12_09_00_00": return "Nokron, Eternal City Start";' + NL).encode("utf-8")
    default_line = (IND + "default: break;" + NL).encode("utf-8")
    replacement = keep_case + block + default_line

    new_data = data.replace(ANCHOR, replacement, 1)

    if new_data == data:
        print("ABORT: replace produced no change.")
        return 1

    with open(CS, "wb") as f:
        f.write(new_data)

    added = sum(1 for c in NEW_CASES)
    print("Patched OK. Added {} exact-id cases (m45 colosseums omitted).".format(added))
    print("Bytes: {} -> {}".format(len(data), len(new_data)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
