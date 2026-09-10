#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_boss_taxonomy.py -- one CLASS per boss, derived from OUR OWN map data.

WHY. `boss_healthbars.py` already carries a coarse geography column (legacy / field / cave /
catacomb / tunnel / dungeon), but it answers a different question: it says which DERIVATION found
the boss, not what KIND of encounter it is. So m61 (the DLC overworld) is filed as `legacy`, every
mini-dungeon family below m34 lands in a bucket called `dungeon`, hero's graves are catacombs, and
an evergaol is indistinguishable from any other field boss. Anything that wants to reason about
boss KIND -- progression surfaces, boss-goal options, the region worksheet, the matt-oracle
histogram (docs/MATT-ORACLE-ROADMAP.md item 7) -- has had to re-derive it inline, differently
each time.

This tool derives it ONCE, and writes `greenfield/eldenring/tables/boss_taxonomy.py`.

INPUTS -- all ours, no third-party table is read or consulted:
  * `boss_healthbars.BOSS_HEALTHBARS`  defeat flag -> (map, tile, coarse class, name)
  * `boss_sweeps.MAJOR_SWEEP_TRIGGERS` the adjudicated major-boss roster (achievement datamine
                                       UNION the MajorBoss tag) -- issue #734
  * `boss_sweeps.SWEEP_ARENA_REGION`   the region the trigger boss is fought in
  * `greenfield/map_names.tsv`         INTERIOR map tile -> dungeon name (BonfireWarpParam ->
                                       PlaceName FMG), which is what separates a hero's grave
                                       from a catacomb inside m30
  * `elden_ring_artifacts/event/*.js`  the EVERGAOL common-event family (below)

THE LADDER. Each boss gets ONE `boss_class`, decided in this order, plus the raw `site_class` so
a consumer that wants pure geography is not forced through the ladder:

  1. remembrance_main  -- flag in MAJOR_SWEEP_TRIGGERS. The game's own roster, already adjudicated.
  2. dragon            -- name matches DRAGON_WORDS (a curated word list, ours; see below).
  3. furnace_golem     -- eight c5170 encounters from the MSB/event census (below).
  4. evergaol          -- trigger flag appears as arg1 of the EVERGAOL_EVENTS common-event family.
  5. site_class        -- from the map prefix (SITE_BY_PREFIX) refined by map_names.tsv.

EVERGAOLS, DERIVED NOT LISTED. An evergaol is an overworld tile with a sealed arena, and the seal
is EMEVD: common events 90005880/81/82/83/85 are initialised only from evergaol tiles and take the
boss's defeat flag as their first argument. Taking the union of those arg1 values is a derivation
over our own decompiled event dump -- no hand-typed roster of twelve names that goes stale on a
patch. It currently yields 10 triggers.

DRAGON IS A WORD LIST, AND SAYS SO. Nothing in the params or the EMEVD marks a boss as a dragon;
NpcParam has no species column and the artifact bundle carries no MSB. So `dragon` is decided on
the boss's own in-game display name (NpcName FMG, via boss_healthbars) against DRAGON_WORDS.
DRAGONKIN_WORDS then subtracts the Dragonkin Soldiers and the Ancient Dragon-Man, which the game
names for dragons but which are not dragon fights. This is the weakest rung on the ladder and it
is deliberately the one with its evidence written next to it.

FURNACE GOLEMS. The independent c5170 MSB census in evidence/furnace_golems
joins eight placed entities to common-event 90005301 death flags and sixteen reward rows.
These encounters have no healthbar. They augment the healthbar roster; acquisition flags
remain check IDs and are never substituted for the separate defeat flags.

Run:
  python tools/gen_boss_taxonomy.py            # emit the module
  python tools/gen_boss_taxonomy.py --list     # print the classification, write nothing
  python tools/gen_boss_taxonomy.py --check    # exit 1 if the committed module is stale
"""
import argparse
import csv
import glob
import importlib.util
import os
import re
import sys
from collections import Counter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLES = os.path.join(REPO, "greenfield", "eldenring", "tables")
EVT = os.path.join(REPO, "elden_ring_artifacts", "event")
MAP_NAMES = os.path.join(REPO, "greenfield", "map_names.tsv")
OUT = os.path.join(TABLES, "boss_taxonomy.py")

# --- the classification vocabulary ------------------------------------------------------------
# Map-id prefix -> site class. The prefixes are the game's own map grouping; the comment on each
# line is why it sits where it does, so a new map family in a DLC gets adjudicated rather than
# silently falling through to 'legacy'.
SITE_BY_PREFIX = {
    "m10": "legacy",        # Stormveil + the Chapel of Anticipation intro
    "m11": "legacy",        # Leyndell / Ashen Capital / Roundtable
    "m12": "legacy",        # the underground rivers -- big, graced, multi-boss: legacy-shaped
    "m13": "legacy",        # Crumbling Farum Azula
    "m14": "legacy",        # Raya Lucaria
    "m15": "legacy",        # Haligtree
    "m16": "legacy",        # Volcano Manor
    "m18": "legacy",        # Stranded Graveyard / Fringefolk Hero's Grave shell
    "m19": "legacy",        # Elden Throne
    "m20": "legacy",        # Belurat / Enir-Ilim
    "m21": "legacy",        # Shadow Keep
    "m22": "legacy",        # Stone Coffin Fissure
    "m25": "legacy",        # Finger Birthing Grounds
    "m28": "legacy",        # Midra's Manse
    "m30": "catacomb",      # base-game catacombs AND hero's graves -- split by map_names below
    "m31": "cave",          # base-game caves / grottoes / hideaways
    "m32": "tunnel",        # base-game mines
    "m34": "legacy",        # Divine Towers -- interior, graced, not a mini-dungeon family
    "m35": "legacy",        # Subterranean Shunning-Grounds (folded into Leyndell)
    "m39": "legacy",        # Ruin-Strewn Precipice
    "m40": "catacomb",      # DLC catacombs
    "m41": "gaol",          # DLC gaols
    "m42": "tunnel",        # DLC ruined forges -- the DLC's mine analogue
    "m43": "cave",          # DLC caves
    "m60": "overworld",     # the Lands Between
    "m61": "overworld",     # the Land of Shadow
}

# map_names.tsv name substring -> the site class it OVERRIDES its prefix with. Only ever used to
# split a prefix that genuinely holds two families (m30 = catacombs + hero's graves).
SITE_BY_NAME = (("Hero's Grave", "heros_grave"),)

# Boss display names that mean "this is a dragon fight". See the DRAGON note in the docstring:
# this is a curated word list over OUR names, not a datamined species column.
DRAGON_WORDS = (
    "Dragon", "Wyrm", "Drake", "Placidusax", "Fortissax", "Lansseax", "Senessax",
    "Greyoll", "Greyll", "Adula", "Smarag", "Agheel", "Theodorix", "Borealis",
)
# ...and the names the game builds out of "Dragon" for things that are NOT dragon fights.
DRAGONKIN_WORDS = ("Dragonkin", "Dragon-Man", "Dragon Communion")

# The EMEVD common-event family that seals an evergaol arena. arg1 is the boss's defeat flag.
EVERGAOL_EVENTS = (90005880, 90005881, 90005882, 90005883, 90005885)

UNDERIVED_CLASSES = {}

# Every class the table can emit, in report order. A class with no members is still listed.
BOSS_CLASSES = (
    "remembrance_main",
    "dragon",
    "furnace_golem",
    "evergaol",
    "overworld_field",
    "legacy_dungeon",
    "catacomb",
    "heros_grave",
    "cave",
    "tunnel",
    "gaol",
)

MIN_BOSSES = 200          # refuse to publish a table built from a half-loaded input
MIN_EVERGAOLS = 8


def _load(name, path=None):
    path = path or os.path.join(TABLES, name + ".py")
    spec = importlib.util.spec_from_file_location("_gen_boss_taxonomy_" + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_map_names():
    """map id (m30_08) -> the tile's PlaceName. Comment lines start with '#'."""
    names = {}
    with open(MAP_NAMES, encoding="utf-8") as fh:
        for row in csv.reader((ln for ln in fh if not ln.startswith("#")), delimiter="\t"):
            if len(row) >= 2 and row[0]:
                names[row[0].strip()] = row[1].strip()
    return names


def evergaol_triggers():
    """Defeat flags sealed by the evergaol common-event family (arg1 of each call site)."""
    if not os.path.isdir(EVT):
        raise SystemExit(
            "FATAL: %s is absent -- run `python tools/gen_inputs.py --ensure "
            "elden_ring_artifacts` first. Refusing to publish an evergaol-less taxonomy." % EVT
        )
    pat = re.compile(
        r"InitializeCommonEvent\(\s*0\s*,\s*(%s)\s*,\s*(\d+)" % "|".join(str(e) for e in EVERGAOL_EVENTS)
    )
    found = set()
    for path in glob.glob(os.path.join(EVT, "*.js")):
        if os.path.basename(path).startswith("common"):
            continue                      # the DEFINITION, not a call site
        with open(path, encoding="utf-8", errors="ignore") as fh:
            for _event, flag in pat.findall(fh.read()):
                found.add(int(flag))
    return found


def _site_class(map_id, place_name):
    site = SITE_BY_PREFIX.get(map_id.split("_", 1)[0])
    if site is None:
        return None
    for needle, override in SITE_BY_NAME:
        if needle in (place_name or ""):
            return override
    return site


def _is_dragon(name):
    if any(w in name for w in DRAGONKIN_WORDS):
        return False
    return any(w in name for w in DRAGON_WORDS)


def classify():
    """defeat flag -> (boss_class, site_class, map_id, region or '', name). Plus the unmapped."""
    hb = _load("boss_healthbars").BOSS_HEALTHBARS
    sweeps = _load("boss_sweeps")
    majors = set(sweeps.MAJOR_SWEEP_TRIGGERS)
    regions = dict(sweeps.SWEEP_ARENA_REGION)
    place = read_map_names()
    gaols = evergaol_triggers()

    if len(hb) < MIN_BOSSES:
        raise SystemExit("FATAL: only %d bosses loaded (minimum %d)." % (len(hb), MIN_BOSSES))
    if len(gaols) < MIN_EVERGAOLS:
        raise SystemExit(
            "FATAL: only %d evergaol trigger(s) derived (minimum %d). The common-event family "
            "moved -- re-audit EVERGAOL_EVENTS before publishing." % (len(gaols), MIN_EVERGAOLS)
        )

    out, unmapped = {}, []
    for flag, (map_id, _tile, _coarse, name) in sorted(hb.items()):
        site = _site_class(map_id, place.get(map_id))
        if site is None:
            unmapped.append((flag, map_id, name))
            continue
        if flag in majors:
            cls = "remembrance_main"
        elif _is_dragon(name):
            cls = "dragon"
        elif flag in gaols:
            cls = "evergaol"
        elif site == "overworld":
            cls = "overworld_field"
        elif site == "legacy":
            cls = "legacy_dungeon"
        else:
            cls = site
        out[flag] = (cls, site, map_id, regions.get(flag, ""), name)
    from furnace_golem_evidence import load
    _rewards, furnaces = load()
    if set(out) & set(furnaces):
        raise ValueError("Furnace roster overlaps healthbars; re-audit taxonomy precedence")
    out.update(furnaces)
    return out, unmapped, gaols


def _write(taxonomy, gaols):
    counts = Counter(v[0] for v in taxonomy.values())
    site_counts = Counter(v[1] for v in taxonomy.values())
    with open(OUT, "w", newline="\n", encoding="utf-8") as f:
        f.write('"""AUTO-GENERATED by tools/gen_boss_taxonomy.py -- DO NOT EDIT (regenerate:\n')
        f.write("python tools/gen_boss_taxonomy.py; it is a step of tools/regen_all.py).\n\n")
        f.write("One CLASS per boss we know, derived from OUR map tiles, OUR major-boss roster and\n")
        f.write("OUR decompiled EMEVD. Matt-free: no third-party table is read, and the oracle uses\n")
        f.write("this only to print a histogram beside his tag counts. See the tool's docstring for\n")
        f.write("the ladder and the independent furnace-golem MSB/event census.\n\n")
        f.write("BOSS_TAXONOMY: defeat flag -> (boss_class, site_class, map_id, arena region, name).\n")
        f.write('An empty region means no boss_area_regions.tsv row -- UNAUDITED, not global."""\n')
        f.write("BOSS_CLASSES = %r\n" % (tuple(BOSS_CLASSES),))
        f.write("\n# class -> why it has no members yet. An empty class here is a KNOWN GAP.\n")
        f.write("UNDERIVED_CLASSES = {\n")
        for cls in sorted(UNDERIVED_CLASSES):
            f.write("    %r: %s,\n" % (cls, ascii(UNDERIVED_CLASSES[cls])))
        f.write("}\n\n")
        f.write("# Defeat flags sealed by the evergaol common-event family (EMEVD-derived).\n")
        f.write("EVERGAOL_TRIGGERS = frozenset({%s})\n\n"
                % ", ".join(str(g) for g in sorted(gaols)))
        f.write("BOSS_TAXONOMY = {\n")
        for flag in sorted(taxonomy):
            cls, site, map_id, region, name = taxonomy[flag]
            f.write("    %d: (%r, %r, %r, %r, %s),\n" % (flag, cls, site, map_id, region, ascii(name)))
        f.write("}\n\n")
        f.write("# Convenience histograms -- the same numbers the oracle report prints.\n")
        f.write("BOSS_CLASS_COUNTS = {\n")
        for cls in BOSS_CLASSES:
            f.write("    %r: %d,\n" % (cls, counts.get(cls, 0)))
        f.write("}\n")
        f.write("SITE_CLASS_COUNTS = {\n")
        for site in sorted(site_counts):
            f.write("    %r: %d,\n" % (site, site_counts[site]))
        f.write("}\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--list", action="store_true", help="print the classification; write nothing")
    ap.add_argument("--check", action="store_true", help="exit 1 if the committed module is stale")
    a = ap.parse_args(argv)

    taxonomy, unmapped, gaols = classify()
    counts = Counter(v[0] for v in taxonomy.values())
    for flag, map_id, name in unmapped:
        print("[boss_taxonomy] UNMAPPED map prefix %s (flag %d, %s) -- add it to SITE_BY_PREFIX"
              % (map_id, flag, name or "?"))
    print("boss_taxonomy: %d bosses, %d evergaol triggers | %s"
          % (len(taxonomy), len(gaols),
             {c: counts.get(c, 0) for c in BOSS_CLASSES}))
    if unmapped:
        raise SystemExit("FATAL: %d boss(es) on an unclassified map prefix." % len(unmapped))

    if a.list:
        for flag in sorted(taxonomy):
            cls, site, map_id, region, name = taxonomy[flag]
            print("  %-11d %-16s %-12s %-9s %-26s %s" % (flag, cls, site, map_id, region, name))
        return 0

    if a.check:
        before = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else None
        _write(taxonomy, gaols)
        after = open(OUT, encoding="utf-8").read()
        if before != after:
            print("STALE: %s regenerated and differs -- commit it." % OUT)
            return 1
        print("fresh:", OUT)
        return 0

    _write(taxonomy, gaols)
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
