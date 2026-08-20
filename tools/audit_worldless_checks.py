#!/usr/bin/env python3
"""audit_worldless_checks.py -- which map-lot checks have NO world reference in any committed corpus?

THE QUESTION (#330's generalization, Alaric 2026-08-19): after the Rada Fruit removal proved that
ItemLotParam rows can be checks without being pickups, how much of the rest of the corpus has the
same shape? Two populations, measured separately because their evidence differs:

  * WORLDLESS SINGLES -- a map-lot check flag with no `item_grace_coords.tsv` row, no
    `msb_flag_region.tsv` row, and no mention in any scripted-award corpus (esd_gifts, esd_flags,
    lot_gates, questline_dag, bell_handins, msb_gated_treasures). Nothing we have places it in the
    world.
  * SAME-WARE COORDINATE STACKS -- several flags of the SAME ware on ONE datamined coordinate:
    vanilla's "ware xN" bundle expressed as N param rows (the Rada shape). Post-#889 the only
    remaining stacks are the m20 Rada bundles, which are KEPT deliberately -- they fire by hand
    (f20017290 / f20017560 in Cokeman5's log).

🛑 A CENSUS COLUMN IS NOT A POPULATION -- this report is a CANDIDATE list, never a cull list.
Both proofs of contamination are on record (2026-08-19):
  * 7 of the then-243 singles fired BY HAND in a live log (400060 / 400190 / 400390 / 530950 /
    65010 / 65020 / 65080) -- NPC handovers and physick tears whose flag_lots type says `map`.
  * Mohgwyn's 34 Golden Rune singles are the rune-farm pickups: MSB enemy-attached treasures
    (`ForceCharacterTreasure`, chr entity == lot id) in maps the census was BLIND to. Run
    `python tools/datamine_msb_item_regions.py --coverage` first; while it reports blind maps,
    absence from the census is a statement about the CENSUS, not the world.

The intended loop: fix the census's blind maps on Windows (re-export MSBs, re-run the datamine and
datamine_item_grace_coords.py, commit), re-run THIS report, and only then judge the survivors --
per cohort, with live-log or in-game evidence, the way #330 was judged.

Usage:
    python tools/audit_worldless_checks.py            # cohort summary
    python tools/audit_worldless_checks.py --list     # every candidate row (flag, region, name)
"""
import argparse
import csv
import importlib.util
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GF = os.path.join(ROOT, "greenfield")

SCRIPTED_CORPORA = ("esd_gifts.tsv", "esd_flags.tsv", "lot_gates.tsv", "questline_dag.tsv",
                    "bell_handins.tsv", "msb_gated_treasures.tsv")


def _load_locations():
    spec = importlib.util.spec_from_file_location("_awc_data", os.path.join(GF, "eldenring", "data.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    out = {}
    for _region, rows in m.LOCATIONS.items():
        for (name, _ap, flag) in rows:
            out.setdefault(str(flag), []).append(name)
    return out


def _flag_lots():
    ware, kind = {}, {}
    with open(os.path.join(GF, "flag_lots.tsv"), encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            ware.setdefault(row["flag"], row.get("name", ""))
            kind.setdefault(row["flag"], row.get("table", ""))
    return ware, kind


def _coords():
    out = defaultdict(list)
    with open(os.path.join(GF, "item_grace_coords.tsv"), encoding="utf-8") as fh:
        for ln in fh:
            p = ln.rstrip("\n").split("\t")
            if p and p[0] == "item" and len(p) >= 6:
                out[p[1]].append(tuple(p[2:6]))
    return out


def _census():
    out = set()
    with open(os.path.join(GF, "msb_flag_region.tsv"), encoding="utf-8") as fh:
        for ln in fh:
            if not ln.startswith(("#", "flag\t")):
                out.add(ln.split("\t", 1)[0])
    return out


def _scripted():
    """Every id-shaped token in the scripted-award corpora. Deliberately COARSE: a flag merely
    MENTIONED near a scripted award is enough to disqualify it from the worldless class, because
    this list exists to avoid false accusations, not to make them."""
    toks = set()
    for name in SCRIPTED_CORPORA:
        p = os.path.join(GF, name)
        if not os.path.isfile(p):
            continue
        with open(p, encoding="utf-8", errors="replace") as fh:
            for ln in fh:
                toks.update(re.findall(r"\b\d{3,10}\b", ln))
    return toks


def _region(name):
    return name.split(" :: ", 1)[0]


def _ware(name):
    return re.split(r" - | \[f", name.split(" :: ", 1)[1], maxsplit=1)[0].strip()


def audit():
    locs = _load_locations()
    _ware_by_flag, kind = _flag_lots()
    coords = _coords()
    census = _census()
    scripted = _scripted()

    singles, soft = [], []
    for fl, names in locs.items():
        if kind.get(fl) != "map" or fl in coords or fl in census:
            continue
        (soft if fl in scripted else singles).append((fl, names[0]))

    spot = defaultdict(list)
    for fl, names in locs.items():
        if kind.get(fl) != "map":
            continue
        for c in coords.get(fl, ()):  # a flag can carry several datamined positions
            spot[(c, _ware(names[0]))].append(fl)
    stacks = {k: v for k, v in spot.items() if len(v) > 1}

    return {"singles": sorted(singles), "scripted_softened": sorted(soft), "stacks": stacks}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--list", action="store_true", help="print every worldless-single row")
    args = ap.parse_args(argv)
    a = audit()
    singles, soft, stacks = a["singles"], a["scripted_softened"], a["stacks"]
    print("worldless singles (no coords, no census, no scripted corpus): %d" % len(singles))
    print("  (+%d more lack coords/census but appear in a scripted corpus -- excluded)" % len(soft))
    print("  by region:", dict(Counter(_region(n) for _, n in singles).most_common(12)))
    print("  top wares:", Counter(_ware(n) for _, n in singles).most_common(10))
    surplus = sum(len(v) - 1 for v in stacks.values())
    print("same-ware coordinate stacks: %d spot(s), %d surplus row(s)" % (len(stacks), surplus))
    for (c, w), fls in sorted(stacks.items(), key=lambda kv: -len(kv[1]))[:10]:
        print("  %2d x %-24s %s" % (len(fls), w, c[0]))
    if args.list:
        print()
        for fl, nm in singles:
            print("%s\t%s" % (fl, nm))
    return 0


if __name__ == "__main__":
    sys.exit(main())
