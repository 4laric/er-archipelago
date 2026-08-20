#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_surface_confidence.py -- how SURE are we where each surface class lives?

WHAT THIS IS. One table, `greenfield/surface_confidence.tsv`: for every class in the
progression-surface vocabulary (`contract.SURFACE_CLASSES`), how many checks carry the tag
and how many of those may actually HOST progression once the bars are applied.

    class  total  guessed_region  missable  erdtree_burn  surface_excluded  release_gated
    hub_merchant  eligible

WHY. The rule for opening the surface vocabulary up to players is: *before we add something to the
possible progression surface we have to be absolutely sure where it is.* That rule is only
enforceable if the cost is measured per class and sits in front of the reviewer. A class is not
"safe" because its items were audited to exist -- Golden Seeds are 43/43 audited for EXISTENCE and
11 of 43 still have a GUESSED region, which is a different claim and the one the surface depends on.

TAGS ARE NOT HOSTING. This is the failure this tool exists to make unrepeatable. A count of tagged
checks is a claim about tags; the surface is a claim about which checks can hold an item. The
`ProgressionSurface` docstring said "193 locations" while the number of checks that can actually host
was 163 (156 with the missable guard armed) -- 193 belongs to the un-barred family (the raw tag union
measures 197). features/progression_surface.missable_barred_aps documents the same class of error
being fixed for the missable set on 2026-07-28. Every number this tool prints is a HOSTING number,
and the un-barred union is printed beside it so the two can never be confused again.

AND THE NUMBERS MOVE. Between `461e709` and `3adad2f` -- one playtest-corrections commit, hours apart
-- re-anchoring two Liurnia Golden Seeds took `Seedtree` from 29 eligible to 31 and the default
surface from 154 to 156. That is the case for a gated artifact rather than a figure in a docstring:
a hand-recorded confidence number is stale the next time anyone confirms a region in game.

THE BARS, and why each one disqualifies a check from hosting progression:

  guessed_region    DEFAULTED_REGION_APS -- the region was defaulted to the hub or tile-guessed. AP
                    believes the check is reachable at spawn; the item spawns where it really lives.
                    This is the softlock that put a Stormveil Lock on a Golden Seed (gen_data
                    _region_is_derived). THE bar this tool exists to price.
  missable          MISSABLE_LOCATIONS -- can be lost permanently, so it cannot be required. Counted
                    while `protect_missable_locations` bars progression (the default does).
  erdtree_burn      ERDTREE_BURN_APS -- m11_00 is destroyed when Maliketh dies. Barred unless the
                    capital reconciler is armed, so this tool reports it as a SEPARATE column rather
                    than folding it in: it is conditional, the others are not.
  surface_excluded  SURFACE_EXCLUDE_APS -- hand-excluded surface-tagged checks (Alaric's call).
  hub_merchant      Roundtable-Hold MERCHANT rows -- reachable at spawn, so progression is trivial.

🛑 THIS TOOL SETS NO POLICY. It does not decide that a class is too uncertain to offer; it prints the
number a human decides on. `--check` asserts only that the committed table matches a fresh emit, so a
regen that shifts a class's confidence CANNOT land silently. Wiring a threshold ("no class above N%
guessed enters the offered vocabulary") is a deliberate follow-up, not this tool's call.

AP-FREE by construction: it loads the generated modules by path, because importing the `eldenring`
package pulls `BaseClasses`. That keeps it runnable in the coverage half of CI, which has no AP.
The price is that the bar stack is re-implemented here rather than imported from
features/progression_surface.allowed_ap_ids (which needs `Options`), so it can drift from the real
one. tests/test_gf_surface_confidence.py pins the two together on the AP side; that test is what
makes this file trustworthy, and it must not be skipped.

Run:
    python tools/build_surface_confidence.py            # emit greenfield/surface_confidence.tsv
    python tools/build_surface_confidence.py --probe    # print the tallies, write nothing
    python tools/build_surface_confidence.py --check    # re-emit to memory, diff; exit 1 on drift
"""
import argparse
import importlib.util
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GF = os.path.join(ROOT, "greenfield")
PKG = os.path.join(GF, "eldenring")
OUT = os.path.join(GF, "surface_confidence.tsv")

# The generated modules this reads. Loaded BY PATH under a throwaway package name: importing
# `eldenring` executes __init__ -> core.py -> `from BaseClasses import ...`, which is AP.
# boss_sweeps + boss_healthbars are here for build_region_census (it shares this loader): the
# SweepSlot box is priced from them. Neither is needed by this tool's own table.
_MODULES = ("data", "location_tags", "missable_locations", "contract",
            "boss_sweeps", "boss_healthbars")


def _load():
    """Load the generated modules AP-free. Raises SystemExit with a usable message if one is absent
    (an un-generated tree is a real state -- run gen_data.py -- not an internal error)."""
    shim = types.ModuleType("_sc_gf")
    shim.__path__ = [PKG]
    sys.modules["_sc_gf"] = shim
    out = {}
    for name in _MODULES:
        path = os.path.join(PKG, name + ".py")
        if not os.path.isfile(path):
            raise SystemExit(
                "build_surface_confidence: %s is missing. The generated data is not present in this "
                "tree -- run `python greenfield/gen_data.py` first." % os.path.relpath(path, ROOT))
        spec = importlib.util.spec_from_file_location("_sc_gf." + name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["_sc_gf." + name] = mod
        spec.loader.exec_module(mod)
        out[name] = mod
    return out


def _bars(mods):
    """The per-check bar sets, by name. Mirrors features/progression_surface.allowed_ap_ids +
    _world_barred_aps; test_gf_surface_confidence pins the union to the real function."""
    tags = mods["location_tags"]
    data = mods["data"]
    lt = tags.LOCATION_TAGS
    # 🛑 `Shop`, NOT `ShopSlot` -- this is #707, and it was wrong HERE too. Both this
    # re-implementation and the feature filtered on a tag no hub row carries, so the
    # `hub_merchant` column read 0 for three weeks and agreed with the feature's 0. Two
    # identical wrong answers pin as cleanly as two right ones, which is why
    # test_eligible_matches_allowed_ap_ids did not catch it. Keep this in step with
    # features/progression_surface._HUB_MERCHANT_TAGS.
    hub_merchant = frozenset(
        ap for (_n, ap, _f) in data.LOCATIONS.get(data.HUB, ())
        if "Shop" in (lt.get(ap) or ()))
    return {
        "guessed_region": frozenset(getattr(tags, "DEFAULTED_REGION_APS", ())),
        "missable": frozenset(mods["missable_locations"].MISSABLE_LOCATIONS),
        "erdtree_burn": frozenset(getattr(tags, "ERDTREE_BURN_APS", ())),
        "surface_excluded": frozenset(getattr(tags, "SURFACE_EXCLUDE_APS", ())),
        "release_gated": frozenset(getattr(tags, "SHOP_RELEASE_GATED_APS", ())),
        "hub_merchant": hub_merchant,
    }


BAR_ORDER = ("guessed_region", "missable", "erdtree_burn", "surface_excluded",
             "release_gated", "hub_merchant")


def measure(mods=None):
    """(rows, totals). Pure over the generated data; no I/O."""
    mods = mods or _load()
    contract = mods["contract"]
    lt = mods["location_tags"].LOCATION_TAGS
    if not lt:
        raise SystemExit("build_surface_confidence: LOCATION_TAGS is EMPTY -- refusing to emit a "
                         "table of zeroes. Regenerate with `python greenfield/gen_data.py`.")
    bars = _bars(mods)
    barred_all = frozenset().union(*bars.values())
    exclude_tags = set(getattr(contract, "SURFACE_EXCLUDE_TAGS", ()) or ())
    # 🛑 DERIVED classes are NOT priced here, and a zero row would be a lie rather than an omission.
    # Every column in this table is a corpus-wide TAG count; SweepSlot carries no tag, because which
    # check it names is decided per seed from that seed's enabled sweeps (progression_surface.
    # sweep_slot_aps). Emitting it would read "0 tagged, 0 can host" -- indistinguishable from a
    # class no location can carry, which is the exact misreading this artifact exists to prevent.
    # Its size IS knowable, just not from here: one per enabled sweep trigger.
    _derived = set(getattr(contract, "SURFACE_DERIVED_CLASSES", ()) or ())
    vocab = [c for c in contract.SURFACE_CLASSES if c not in _derived]
    # 🛑 The default now CONTAINS a derived class (SweepSlot). Its tag union is therefore not the
    # whole default surface, and saying so is the point of this artifact: the number below prices
    # what tags can host, and one member per enabled sweep is added to it per seed on top.
    default_derived = set(contract.SURFACE_DEFAULT_CLASSES) & _derived
    default = set(contract.SURFACE_DEFAULT_CLASSES) - _derived

    def tagged(classes):
        """ap-ids carrying any of `classes` and none of SURFACE_EXCLUDE_TAGS -- contract.has_class,
        re-expressed so this stays AP-free."""
        sel = set(classes)
        return {ap for ap, ts in lt.items()
                if (sel & set(ts or ())) and not (exclude_tags & set(ts or ()))}

    def raw_tagged(classes):
        """ap-ids carrying any of `classes`, WITHOUT the SURFACE_EXCLUDE_TAGS filter.

        Only used to price the `tag_excluded` column. `total` deliberately stays the has_class
        count -- see the emit() header for why this column exists at all."""
        sel = set(classes)
        return {ap for ap, ts in lt.items() if sel & set(ts or ())}

    rows = []
    for cls in vocab:
        aps = tagged([cls])
        row = {"class": cls, "total": len(aps),
               "tag_excluded": len(raw_tagged([cls])) - len(aps),
               "eligible": len(aps - barred_all),
               "in_default": "yes" if cls in default else ""}
        for b in BAR_ORDER:
            row[b] = len(aps & bars[b])
        rows.append(row)

    dflt = tagged(default)
    # erdtree_burn is CONDITIONAL (capital reconciler armed -> not barred), so the headline hosting
    # number is reported both ways rather than picking one and hiding the other.
    hosting_bars = (bars["guessed_region"] | bars["surface_excluded"]
                    | bars["release_gated"] | bars["hub_merchant"])
    totals = {
        "vocabulary": len(vocab),
        "default_classes": len(default),
        "default_derived": sorted(default_derived),
        "default_tag_union": len(dflt),
        "default_hosting_reconciler_on": len(dflt - hosting_bars - bars["missable"]),
        "default_hosting": len(dflt - hosting_bars - bars["erdtree_burn"] - bars["missable"]),
        "default_hosting_missable_off": len(dflt - hosting_bars - bars["erdtree_burn"]),
        "checks_total": sum(len(v) for v in mods["data"].LOCATIONS.values()),
        "checks_tagged": len(lt),
    }
    return rows, totals


_COLS = ("class", "total", "tag_excluded") + BAR_ORDER + ("eligible", "eligible_pct", "in_default")


def emit(rows, totals):
    """The .tsv text. Deterministic: vocabulary order, LF endings, ASCII."""
    L = []
    a = L.append
    a("# AUTO-GENERATED by tools/build_surface_confidence.py -- DO NOT EDIT, re-emit.")
    a("# How sure we are WHERE each progression-surface class lives.")
    a("#")
    a("# 'eligible' = checks that may actually HOST progression: tagged, minus every bar below.")
    a("# A TAG COUNT IS NOT A HOSTING COUNT. Both are printed; quote the second one.")
    a("#")
    a("# 'total' IS ALREADY FILTERED, AND THAT USED TO BE INVISIBLE. It is contract.has_class:")
    a("# checks carrying the tag MINUS checks carrying a SURFACE_EXCLUDE_TAG (EniaShop -- Enia's")
    a("# buy-only remembrance store). The 'checks N carry any tag' line below is RAW. So the two")
    a("# numbers on this page legitimately disagree, and nothing said so.")
    a("#   raw tag count for a class  ==  total + tag_excluded")
    a("# MOTIVATING CASE (rule 11): on 2026-08-08 an agent read `Shop 500` here, measured 527 raw")
    a("# tags in location_tags.py, and reported the committed table as STALE in a design review.")
    a("# It was not stale -- test_gf_surface_confidence::test_artifact_is_current diffs a fresh")
    a("# emit on every CI run and was green. Two measures, one label, a fabricated defect. The")
    a("# column makes the filter visible instead of leaving it in prose.")
    a("#   tag_excluded      carries the tag but also a SURFACE_EXCLUDE_TAG -> never on the surface")
    a("#   guessed_region    region defaulted/tile-guessed -> AP thinks it is reachable at spawn")
    a("#   missable          can be lost permanently -> cannot be required")
    a("#   erdtree_burn      m11_00 destroyed when Maliketh dies (CONDITIONAL: not barred when the")
    a("#                     capital reconciler is armed -- see the two default_hosting_* lines)")
    a("#   surface_excluded  hand-excluded surface-tagged checks (gen_data _SURFACE_EXCLUDE_FLAGS)")
    a("#   release_gated     merchant row absent until its own shop-release event fires")
    a("#   hub_merchant      Roundtable-Hold MERCHANT rows -- reachable at spawn, so trivial")
    a("# Bar columns OVERLAP (one check can be both guessed and missable), so they do not sum to")
    a("# total - eligible. 'eligible' is computed from the UNION, never by subtracting the columns.")
    a("#")
    a("# 🛑 This table sets NO policy. It prices each class; a human decides what is offerable.")
    a("# 🛑 A class is not safe because its items were audited to EXIST. Golden Seeds are 43/43")
    a("#    audited for existence and several still have a GUESSED region -- a different claim,")
    a("#    and the one the surface depends on. See the Seedtree row.")
    a("#")
    a("# MEASURED THIS RUN (recomputed on every emit):")
    a("#   vocabulary %d class(es) | default surface %d TAGGED class(es)"
      % (totals["vocabulary"], totals["default_classes"]))
    if totals["default_derived"]:
        # Not a footnote: without this line the reader takes the hosting number below for the whole
        # default surface, and it is short by one check per enabled sweep -- which on a default seed
        # is more than the tag union itself.
        a("#   PLUS %s -- DERIVED, not priced here: one check per enabled dungeon sweep, decided per"
          % ", ".join(totals["default_derived"]))
        a("#   seed (55 on a 4-region seed, ~170 on the full map). So the DEFAULT SURFACE hosting")
        a("#   number below is the TAGGED half only.")
    a("#   checks %d total, %d carry any tag" % (totals["checks_total"], totals["checks_tagged"]))
    a("#   DEFAULT SURFACE: tag union %d | hosting %d | hosting w/ reconciler armed %d "
      "| hosting if missable guard OFF %d"
      % (totals["default_tag_union"], totals["default_hosting"],
         totals["default_hosting_reconciler_on"], totals["default_hosting_missable_off"]))
    a("#")
    a("\t".join(_COLS))
    for r in rows:
        pct = (100.0 * r["eligible"] / r["total"]) if r["total"] else 0.0
        # `in_default` is deliberately blank for most classes. Do not serialize that final blank as
        # trailing whitespace: integrity hooks correctly reject generated whitespace too.
        a("\t".join([r["class"], str(r["total"]), str(r["tag_excluded"])]
                    + [str(r[b]) for b in BAR_ORDER]
                    + [str(r["eligible"]), "%.0f" % pct, r["in_default"]]).rstrip())
    return "\n".join(L) + "\n"


def summarise(rows, totals):
    w = max(len(r["class"]) for r in rows)
    head = ("%-*s %6s %6s %7s %7s %6s %6s %7s %6s %9s %5s  %s"
            % (w, "class", "total", "tagxc", "guessed", "missbl", "burn", "sxcl", "release",
               "hub", "ELIGIBLE", "%", "default"))
    out = [head, "-" * len(head)]
    for r in rows:
        pct = (100.0 * r["eligible"] / r["total"]) if r["total"] else 0.0
        out.append("%-*s %6d %6d %7d %7d %6d %6d %7d %6d %9d %4.0f%%  %s"
                   % (w, r["class"], r["total"], r["tag_excluded"],
                      r["guessed_region"], r["missable"],
                      r["erdtree_burn"], r["surface_excluded"], r["release_gated"],
                      r["hub_merchant"],
                      r["eligible"], pct, r["in_default"]))
    out.append("")
    if totals["default_derived"]:
        out.append("DEFAULT SURFACE also includes %s (DERIVED: one check per enabled sweep, per "
                   "seed) -- not in the numbers below." % ", ".join(totals["default_derived"]))
    out.append("DEFAULT SURFACE  tag union %d  ->  HOSTING %d  (reconciler armed %d; missable guard off %d)"
               % (totals["default_tag_union"], totals["default_hosting"],
                  totals["default_hosting_reconciler_on"], totals["default_hosting_missable_off"]))
    out.append("A tag count is not a hosting count. Quote the hosting number.")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--probe", action="store_true", help="print the tallies, write nothing")
    ap.add_argument("--check", action="store_true",
                    help="re-emit to memory and diff against the committed file; exit 1 on drift")
    args = ap.parse_args(argv)

    rows, totals = measure()
    for line in summarise(rows, totals):
        print(line)

    if args.probe:
        print("--probe: nothing written")
        return 0

    text = emit(rows, totals)
    if args.check:
        if not os.path.isfile(OUT):
            print("DRIFT: %s does not exist. Run the tool." % os.path.relpath(OUT, ROOT),
                  file=sys.stderr)
            return 1
        current = open(OUT, encoding="utf-8", newline="").read()
        if current != text:
            print("DRIFT: greenfield/surface_confidence.tsv is stale. Re-emit with "
                  "`python tools/build_surface_confidence.py`.", file=sys.stderr)
            return 1
        print("--check: committed table matches a fresh emit")
        return 0

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("wrote %s (%d classes)" % (os.path.relpath(OUT, ROOT), len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
