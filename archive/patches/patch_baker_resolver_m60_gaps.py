#!/usr/bin/env python3
# patch_baker_resolver_m60_gaps.py
#
# Adds 104 previously-unmapped base-game m60 overworld tiles (small _00 tiles
# plus the big _02 region tiles) to the C# resolver `CompApRegionForMap` in
# SoulsRandomizers\RandomizerCommon\EnemyRandomizer.cs.
#
# Source of truth for tile -> place: thefifthmatt "Elden Ring map names" gist.
# Region names match Archipelago\worlds\eldenring\locations.py region_order
# byte-for-byte (note: "Liurnia of The Lakes" with capital T).
#
# RUN ON WINDOWS:  py patch_baker_resolver_m60_gaps.py
#
# - CRLF-preserving binary IO.
# - Idempotent: aborts cleanly if the new cases are already present
#   (distinctive marker: case "33_40":).
# - Inserts the new case blocks IMMEDIATELY BEFORE the m60 switch's
#   `default: return null;`, anchored on the LAST existing region block
#   (Consecrated Snowfield) that precedes that default.
# - Indentation: 28 spaces for `case`, 32 spaces for `return`.

import sys
import os

CS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "SoulsRandomizers", "RandomizerCommon", "EnemyRandomizer.cs",
)

CRLF = b"\r\n"
CASE_INDENT = b" " * 28
RET_INDENT = b" " * 32

# Idempotency marker: one of the new tiles. If already present, do nothing.
MARKER = b'case "33_40":'

# Anchor: the last region block before `default: return null;` in the m60
# switch is Consecrated Snowfield. We insert our new blocks between that
# block's return and the default line.
ANCHOR = (
    RET_INDENT + b'return "Consecrated Snowfield";' + CRLF
    + CASE_INDENT + b"default: return null;" + CRLF
)

# Each entry: (region_name, comment, [list of "XX_YY" compTile labels])
# compTile = msbMap.Substring(4,2) + "_" + msbMap.Substring(7,2)
#   e.g. m60_33_40_00 -> "33_40";  m60_08_10_02 -> "08_10"
GROUPS = [
    ("Liurnia of The Lakes", "Liurnia of The Lakes (m60 gap fill; big _02 + small _00)", [
        # big _02 region tiles
        "08_10",  # Southwest Liurnia
        "08_11",  # West Liurnia
        "09_11",  # East Liurnia
        "09_12",  # Liurnia to Atlus Plateau (primary "Liurnia"; SHARED w/ Altus label)
        # small _00 tiles
        "33_43", "33_45",
        "34_42",  # SHARED: Village of the Albinaurics; Moonlight Altar - Moonfolk Ruins
        "34_45", "34_50", "34_51",
        "35_44", "35_45", "35_46", "35_48", "35_49", "35_51",
        "36_42", "36_44", "36_46",
        "36_47",  # SHARED: ...; Bellum Highway - South of East Raya Lucaria Gate
        "36_49",  # SHARED: ...; Bellum Highway - Bellum Church
        "36_50",
        "37_41", "37_43", "37_45",
        "37_50",  # SHARED: Liurnia of the Lake - Northeast Ravine; Bellum Highway
        "38_39", "38_42", "38_44",
        "39_39", "39_43", "39_45", "39_46",
        "40_40",
    ]),
    ("Moonlight Altar", "Moonlight Altar (m60 gap fill; small _00)", [
        "33_40", "33_41", "33_42",
        "34_41",
        "35_41", "35_42",
    ]),
    ("Bellum Highway", "Bellum Highway (m60 gap fill; small _00)", [
        "36_48",
        "37_49",
        "38_49",
        "39_48",  # SHARED: Bellum Highway primary; Liurnia - Black Knife Catacombs
        "39_49",
    ]),
    ("Mt. Gelmir", "Mt. Gelmir (m60 gap fill; small _00)", [
        "35_52", "35_54",
        "37_54", "37_55",
    ]),
    ("Altus Plateau", "Altus Plateau (m60 gap fill; big _02 + small _00)", [
        # big _02
        "10_13",  # North Atlus Plateau
        # small _00
        "36_51",
        "38_52",
        "39_50", "39_52",
        "40_50", "40_51", "40_55",
        "41_50", "41_51", "41_53", "41_55",
        "42_54",
        "43_54",
    ]),
    ("Weeping Peninsula", "Weeping Peninsula (m60 gap fill; big _02 + small _00)", [
        # big _02
        "10_08",  # West Weeping Peninsula
        "11_07",  # Southeast Weeping Peninsula Coast
        # small _00
        "41_34",
        "42_32", "42_34",
        "43_30", "43_32", "43_33",
        "44_31", "44_32",
        "45_32", "45_34",
    ]),
    ("Limgrave", "Limgrave (m60 gap fill; big _02)", [
        "10_09",  # West Limgrave
        "11_09",  # East Limgrave
    ]),
    ("Caelid", "Caelid (m60 gap fill; big _02 + small _00)", [
        # big _02
        "13_09",  # Southeast Caelid
        # small _00
        "47_37", "47_38", "47_41", "47_42",
        "49_36",
        "50_37", "50_39",
        "51_35",
        "52_38",
    ]),
    ("Dragonbarrow", "Dragonbarrow (m60 gap fill; small _00)", [
        "48_41",
        "49_40", "49_41",
        "50_40",
        "51_39", "51_40", "51_41", "51_42", "51_43",
        "52_41", "52_42", "52_43",
    ]),
    ("Mountaintops of the Giants", "Mountaintops of the Giants (m60 gap fill; big _02)", [
        "12_13",  # Southwest Mountaintops
        "12_14",  # Northwest Mountaintops
        "13_13",  # Southeast Mountaintops
        "13_14",  # Northeast Mountaintops
    ]),
    ("Consecrated Snowfield", "Consecrated Snowfield (m60 gap fill; big _02)", [
        "11_14",  # West Consecrated Snowfield
    ]),
]


def build_block():
    out = bytearray()
    for region, comment, tiles in GROUPS:
        out += CASE_INDENT + b"// " + comment.encode("ascii") + CRLF
        for t in tiles:
            out += CASE_INDENT + b'case "' + t.encode("ascii") + b'":' + CRLF
        out += RET_INDENT + b'return "' + region.encode("utf-8") + b'";' + CRLF
    return bytes(out)


def main():
    if not os.path.isfile(CS_PATH):
        print("ERROR: not found: %s" % CS_PATH)
        sys.exit(1)

    with open(CS_PATH, "rb") as f:
        data = f.read()

    if MARKER in data:
        print("Already patched (marker %r present). No changes." % MARKER.decode())
        sys.exit(0)

    n = data.count(ANCHOR)
    if n != 1:
        print("ERROR: anchor found %d times (expected exactly 1). Aborting." % n)
        print("Anchor was:\n%r" % ANCHOR)
        sys.exit(2)

    # Sanity: every tile distinct, none duplicated within our own block.
    seen = set()
    dupes = []
    for _, _, tiles in GROUPS:
        for t in tiles:
            if t in seen:
                dupes.append(t)
            seen.add(t)
    if dupes:
        print("ERROR: duplicate tiles within patch: %s" % dupes)
        sys.exit(3)

    new_block = build_block()

    # Insert new_block between the Consecrated Snowfield return and the default.
    replacement = (
        RET_INDENT + b'return "Consecrated Snowfield";' + CRLF
        + new_block
        + CASE_INDENT + b"default: return null;" + CRLF
    )
    patched = data.replace(ANCHOR, replacement, 1)

    if patched == data:
        print("ERROR: replacement made no change. Aborting.")
        sys.exit(4)

    with open(CS_PATH, "wb") as f:
        f.write(patched)

    added = sum(len(tiles) for _, _, tiles in GROUPS)
    print("OK: inserted %d new m60 tile cases across %d region groups."
          % (added, len(GROUPS)))
    print("File: %s" % CS_PATH)


if __name__ == "__main__":
    main()
