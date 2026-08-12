#!/usr/bin/env python3
r"""build_region_dispute_worksheet.py -- checks whose TILE holds more than one region.

WHY (er-archipelago#598)
-----------------------
bobler could not find a Scadutree Fragment. Its hint read `Cerulean :: ... southwest of Cliffroad
Terminus [f2044417995]` -- Cliffroad Terminus is Gravesite Plain, and its tile-mate `f2044417000`
came out Gravesite in the SAME seed. One tile, two regions, one generation.

A tile is the smallest loadable unit of a map, so on the OVERWORLD two checks on one tile disagreeing
is a derivation artifact, not geography. `region_of`'s ladder is walked per CHECK, so two checks can
exit at different branches; the last resort in `_m61_tile_region` / `_m60_tile_region` is an
unconditional nearest-neighbour hop that returns a confident region with no marker saying it guessed.

🛑 INTERIORS ARE DIFFERENT AND ARE NOT DEFECTS. A legacy dungeon is one map id covering an enormous
space, and it may legitimately own checks in two AP regions -- `m21_00` (Shadow Keep) holds the
Golden Hippopotamus arena, which `region_of`'s boss-arena branch DELIBERATELY re-homes to Scadu Altus
(and `region_overrides.tsv` records it). Those rows are emitted with `tile_kind=interior` so they can
be dismissed on sight rather than re-litigated.

WHAT THIS IS
------------
A WORKSHEET, in the shape of `boss_region_worksheet.tsv`: hand-fill `verdict` and `reason`, and the
answer goes into `region_overrides.tsv`, which `region_of` already honours FIRST
(`FLAG_REGION_OVERRIDE`). Nothing in gen reads this file.

ORDERING IS THE PRIORITISATION (Alaric, 2026-08-12: "starting with the progression_surface
candidates"). Rows sort by:
  1. surface_default -- the check carries one of `contract.SURFACE_DEFAULT_CLASSES`, so a default
     seed can hang progression on it. A mis-regioned surface check is the expensive kind: it is what
     `region_locks` gate on, and a wrong region there can strand a key item.
  2. how == GUESSED -- `check_region_triage.tsv` already says this region was a nearest-neighbour
     hop rather than first-hand evidence, so it is the likelier half of a disagreement.
  3. tile, then flag, for a stable diff.

INPUTS ARE ALL COMMITTED -- data.py, check_maps.tsv, check_region_triage.tsv, location_tags.py,
contract.py. No `elden_ring_artifacts`, no MSBs, so this runs in the sandbox and in CI.

    python tools/build_region_dispute_worksheet.py            # report to stdout
    python tools/build_region_dispute_worksheet.py --emit     # + greenfield/region_dispute_worksheet.tsv
"""
import argparse
import ast
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GF = os.path.join(ROOT, "greenfield")
OUT = os.path.join(GF, "region_dispute_worksheet.tsv")
HUB = "Roundtable Hold"


def _literal(path, name):
    """Read one module-level literal WITHOUT importing the package.

    🛑 `from eldenring import contract` pulls `eldenring/__init__.py`, which imports Archipelago's
    `BaseClasses`. That would make this tool need the AP env for two constants and break the
    "runs anywhere" promise in the docstring. Parse instead.
    """
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == name:
                    v = node.value
                    if isinstance(v, ast.Call):          # frozenset({...})
                        v = v.args[0]
                    return ast.literal_eval(v)
    raise SystemExit("%s not found in %s" % (name, path))


def _flag_region():
    """flag -> AP region, from the committed data.py LOCATIONS table."""
    src = open(os.path.join(GF, "eldenring", "data.py"), encoding="utf-8").read()
    out, cur = {}, None
    for ln in src.splitlines():
        m = re.match(r"""\s*['"]([^'"]+)['"]: \[$""", ln)
        if m:
            cur = m.group(1)
            continue
        m2 = re.search(r",\s*(\d+),\s*(\d+)\)", ln)
        if cur and m2:
            out[int(m2.group(2))] = (cur, int(m2.group(1)))
    return out


def _tsv(name, want_prefix=None):
    rows = []
    for ln in open(os.path.join(GF, name), encoding="utf-8"):
        if ln.startswith("#"):
            continue
        p = ln.rstrip("\n").split("\t")
        if p and p[0].isdigit():
            rows.append(p)
        elif want_prefix and len(p) > 1 and p[0].startswith(want_prefix):
            rows.append(p)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit", action="store_true", help="write %s" % OUT)
    args = ap.parse_args()

    surface = frozenset(_literal(os.path.join(GF, "eldenring", "contract.py"),
                                 "SURFACE_DEFAULT_CLASSES"))
    LOCATION_TAGS = _literal(os.path.join(GF, "eldenring", "location_tags.py"), "LOCATION_TAGS")

    flag_region = _flag_region()
    tile = {int(p[0]): p[1] for p in _tsv("check_maps.tsv") if len(p) > 1 and p[1].startswith("m")}
    how = {}
    for p in _tsv("check_region_triage.tsv", want_prefix="m"):
        # map_tile region ap_id flag how ...
        if len(p) > 4 and p[3].isdigit():
            how[int(p[3])] = p[4]
    desc = {int(p[0]): p[1] for p in _tsv("location_descriptions.tsv") if len(p) > 1}

    by = {}
    for flag, t in tile.items():
        hit = flag_region.get(flag)
        if hit:
            by.setdefault(t, set()).add(hit[0])

    disputed = {}
    for t, regions in by.items():
        real = {r for r in regions if r != HUB}
        if len(real) > 1:
            disputed[t] = sorted(regions)

    rows = []
    for flag, t in tile.items():
        if t not in disputed:
            continue
        hit = flag_region.get(flag)
        if not hit:
            continue
        region, ap_id = hit
        tags = LOCATION_TAGS.get(ap_id, [])
        rows.append({
            "tile": t,
            "tile_kind": "overworld" if re.match(r"m6[01]_", t) else "interior",
            "flag": flag,
            "ap_id": ap_id,
            "derived_region": region,
            "regions_on_tile": "|".join(disputed[t]),
            "surface_default": "yes" if (set(tags) & surface) else "no",
            "how": how.get(flag, "-"),
            "tags": ",".join(tags) or "-",
            "label": desc.get(flag, "-"),
        })

    rows.sort(key=lambda r: (r["surface_default"] != "yes", r["how"] != "GUESSED",
                             r["tile_kind"] != "overworld", r["tile"], r["flag"]))

    ow = sorted({r["tile"] for r in rows if r["tile_kind"] == "overworld"})
    inr = sorted({r["tile"] for r in rows if r["tile_kind"] == "interior"})
    surf = sum(1 for r in rows if r["surface_default"] == "yes")
    print("disputed tiles      : %d (%d overworld, %d interior)" % (len(disputed), len(ow), len(inr)))
    print("checks on them      : %d" % len(rows))
    print("progression-surface : %d  <-- work these first" % surf)
    print("overworld tiles     : %s" % ", ".join(ow))

    if not args.emit:
        return
    cols = ["tile", "tile_kind", "flag", "ap_id", "derived_region", "regions_on_tile",
            "surface_default", "how", "tags", "label", "verdict", "reason"]
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("# WORKSHEET (er-archipelago#598) -- hand-fill `verdict` and `reason`, then move the\n")
        f.write("#   answer into region_overrides.tsv, which region_of honours FIRST. Nothing in gen\n")
        f.write("#   reads THIS file. Regenerate: tools/build_region_dispute_worksheet.py --emit\n")
        f.write("# Every row's TILE holds checks in more than one AP region.\n")
        f.write("# tile_kind=interior -- a legacy dungeon is one map id over a huge space and MAY own\n")
        f.write("#   two regions legitimately (m21_00's Hippopotamus arena is Scadu Altus by design,\n")
        f.write("#   see region_overrides.tsv). Dismiss those unless something else looks wrong.\n")
        f.write("# tile_kind=overworld -- a tile is the smallest loadable unit, so a split here is a\n")
        f.write("#   derivation artifact. These are the real subject.\n")
        f.write("# how=GUESSED -- check_region_triage says this region was a nearest-neighbour hop,\n")
        f.write("#   not first-hand evidence. surface_default=yes -- a default seed can hang\n")
        f.write("#   progression on it, so a wrong region here is the expensive kind.\n")
        f.write("# ORDER IS THE PRIORITY: surface_default, then GUESSED, then overworld, then tile.\n")
        f.write("\t".join(cols) + "\n")
        for r in rows:
            f.write("\t".join(str(r.get(c, "")) for c in cols) + "\n")
    print("wrote %s" % OUT)


if __name__ == "__main__":
    main()
