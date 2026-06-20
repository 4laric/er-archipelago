#!/usr/bin/env python3
r"""patch_baker_resolver_fill_missing_tiles.py

Fills the COVERAGE GAP in CompApRegionForMap (EnemyRandomizer.cs) for the sphere-scaling
bridge. The exact-tile switch shipped by patch_baker_resolver_exact_tiles.py covered only the
region-LOCK overworld regions (Weeping/Liurnia/Caelid/Dragonbarrow/Altus/Mt.Gelmir) because it
was derived from grace_data.py REGION_GRACE_POINTS, which only contains lock regions. The
non-lock / natural-key overworld regions -- Limgrave, Stormhill, Capital Outskirts, Forbidden
Lands, Mountaintops of the Giants, Consecrated Snowfield -- had NO grace entries, so their m60
tiles fell through to `default: return null` => v1 geographic fallback (sphere scaling never bit
on them, including LIMGRAVE, the common random-start region).

This patch adds those tiles, read directly off thefifthmatt's small-tile m60 map
(https://gist.github.com/gracenotes/9c3f7979b061ec7dbff09a3bf148abdf -- the same author the
rando derives from). Each tile's gist place-name prefix maps 1:1 onto an AP region_order name
(verified against Archipelago/worlds/eldenring/locations.py region_order). Tile id parse matches
the resolver: m60_XX_YY_00 -> compTile "XX_YY".

INSERTION: new `case` lines are spliced into the EXISTING switch, just before `default: return
null;`, so no existing case is touched and there are no duplicate labels. Tiles already present
in the switch (e.g. 46_39 = shared Limgrave/Caelid, already Caelid) are intentionally OMITTED
here to avoid a duplicate-case compile error -- they keep their current assignment.

SHARED / AMBIGUOUS TILES (flagged -- override if a playtest says otherwise):
  47_51  Leyndell DT-of-East-Altus + "Mountaintops - Forbidden Lands Start"  -> Forbidden Lands
  48_51  "Mountaintops - Forbidden Lands Midway"                             -> Forbidden Lands
  50_56  "Mountaintops - Shack of the Lofty" + "Snowfield - Albinauric Rise" -> Mountaintops (1st label)
  50_57  "Mountaintops - West of Castle Sol" + "Snowfield - N of Minor Erd"  -> Mountaintops (1st label)
(47_51/48_51: gist files them under the Mountaintops prefix but AP splits "Forbidden Lands" out
as its own region, so they go to Forbidden Lands.)

NOT handled here: DLC overworld (map m61 -- the resolver only parses m60_; needs a separate m61
branch + tile grid). Base-game overworld is now fully covered.

Run on Windows from repo root:
    python patch_baker_resolver_fill_missing_tiles.py
CRLF-preserving (file is CRLF); exact-match byte replace; idempotent (skips if 42_36 present).
"""
import os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
ER = os.path.join(ROOT, "SoulsRandomizers", "RandomizerCommon", "EnemyRandomizer.cs")
if not os.path.exists(ER):
    sys.exit("ERROR: EnemyRandomizer.cs not found under SoulsRandomizers/RandomizerCommon (run from repo root).")

# AP region (region_order name) -> list of m60 small tiles "XX_YY" to assign to it.
# Source: thefifthmatt gist small-tile map. Tiles already in the existing switch are excluded.
REGION_TILES = {
    "Limgrave": [
        "41_35", "42_35", "43_35", "41_36", "41_37", "42_36", "42_37", "43_36", "43_37",
        "43_38", "44_35", "45_35", "44_36", "44_37", "45_36", "45_37", "44_38", "44_39",
        "45_38", "45_39", "46_36", "46_37", "46_38", "45_40",
    ],
    "Stormhill": [
        "40_38", "40_39", "41_38", "41_39", "42_38", "42_39", "43_39", "42_40", "43_40",
    ],
    "Capital Outskirts": [
        "42_50", "42_51", "43_50", "43_51", "45_51", "44_52", "44_53", "45_52", "45_53",
        "42_52", "42_53", "43_52", "43_53",
    ],
    "Forbidden Lands": [
        "47_51", "48_51",  # shared w/ Leyndell / labeled under Mountaintops in gist -- see header
    ],
    "Mountaintops of the Giants": [
        "49_52", "49_53", "50_53", "51_52", "51_53", "50_54", "51_54", "51_55", "51_56",
        "51_57", "51_58", "52_52", "52_53", "53_52", "53_53", "52_54", "52_55", "53_54",
        "53_55", "54_53", "54_55", "52_56", "52_57", "53_56", "53_57", "52_58", "53_58",
        "54_56", "54_57",
        "50_56", "50_57",  # shared w/ Snowfield -- 1st gist label wins -- see header
    ],
    "Consecrated Snowfield": [
        "46_55", "47_55", "46_57", "47_56", "47_57", "47_58", "48_54", "48_55", "49_54",
        "49_55", "50_55", "48_56", "48_57", "49_56", "49_57", "48_58",
    ],
}

# Guard: no tile assigned to two regions in this patch.
_seen = {}
for _region, _tiles in REGION_TILES.items():
    for _t in _tiles:
        if _t in _seen:
            sys.exit("  [FAIL] internal: tile %s assigned to both %r and %r." % (_t, _seen[_t], _region))
        _seen[_t] = _region

# Build the C# case block (28-space case lines, 32-space return), matching existing indentation.
CASE_I = " " * 28
RET_I = " " * 32
blocks = []
for region, tiles in REGION_TILES.items():
    lines = "".join("%scase \"%s\":\r\n" % (CASE_I, t) for t in tiles)
    blocks.append("%s// %s (gist small-tile map; fill_missing_tiles patch)\r\n%s%sreturn \"%s\";\r\n"
                  % (CASE_I, region, lines, RET_I, region))
NEW_CASES = "".join(blocks)

# Splice in before `default: return null;`, right after the Mt. Gelmir return that ends the
# existing switch body.
ANCHOR = RET_I + 'return "Mt. Gelmir";\r\n' + CASE_I + "default: return null;\r\n"
REPLACEMENT = RET_I + 'return "Mt. Gelmir";\r\n' + NEW_CASES + CASE_I + "default: return null;\r\n"

with open(ER, "rb") as f:
    b = f.read()
txt = b.decode("utf-8")

if 'case "42_36":' in txt:
    print("  [skip] resolver already has the missing-tile cases (42_36 present).")
    sys.exit(0)

n = txt.count(ANCHOR)
if n != 1:
    sys.exit("  [FAIL] Mt.Gelmir/default anchor found %d times (expected 1); not modified. "
             "Is patch_baker_resolver_exact_tiles.py applied?" % n)
txt = txt.replace(ANCHOR, REPLACEMENT, 1)

with open(ER, "wb") as f:
    f.write(txt.encode("utf-8"))

_total = sum(len(v) for v in REGION_TILES.values())
print("  [ok]   added %d tiles across %d regions: %s"
      % (_total, len(REGION_TILES), ", ".join(REGION_TILES)))
print("DONE -- rebuild SoulsRandomizers, then enemy-OFF bake with completion_scaling + "
      "completion_scaling_basis: sphere. Watch the bake log 'CompletionScaling sphere basis: "
      "reshaped N enemies' -- N should jump now that Limgrave/Mountaintops/Snowfield resolve.")
