#!/usr/bin/env python3
"""build_region_census.py -- the per-region numbers the options wizard shows you WHILE you choose.

WHAT THIS IS. One artifact, `wizard/region-census.json`, holding the two things a player needs to
size a seed before generating it, split by region so the wizard can recompute them live as
`num_regions`, `enable_dlc`, `dlc_only` and `progression_surface` move:

  * how many CHECKS each region contributes, and
  * how many of those checks may actually HOST progression, per progression-surface class.

WHY. Two players asked the same question from opposite ends in two days: bobler asked why
`num_regions: 1` kept four regions, and a Nexus commenter asked what fraction of "2000 checks for 6
areas" is filler before committing his friends to a multiworld. Both answers exist only after you
generate. #409 already added the gen-log line that explains the kept set -- but a log line is read
AFTER the decision it would have informed. This puts the number in front of the choice.

AND THE NUMBER IS A RANGE, WHICH IS THE POINT. `num_regions` is a DRAW SIZE, not a final count
(region_spine.compute_kept: draw + explicit-goal force-keeps + parent closure). At the default 6 the
real check count ranges about 1069..2279 depending purely on WHICH regions the draw takes. A wizard
that printed one number would be lying; the census gives the wizard what it needs to show the spread,
which teaches the draw-size model in one glance.

WHAT IT DOES NOT DO. It does not estimate the filler/useful split. That one genuinely needs a built
world (features/filler_budget + the pool builder reshape the tail), so it belongs in a sampled table,
not here. Deliberately out of scope rather than approximated.

CLASS COMBINATIONS, NOT PER-CLASS COUNTS -- read this before "simplifying" the schema.
Surface classes OVERLAP: one check is routinely `GreatRune` + `MajorBoss` + `Boss` at once. So a
{class: count} table cannot be summed over a player's selection without over-counting exactly the
checks that carry two selected classes. `regions[R]["combos"]` is therefore keyed by the SORTED TUPLE
of vocabulary classes a check carries (joined with "|"), and a consumer computes the surface as

    sum(count for combo, count in combos.items() if selected & set(combo.split("|")))

which is an exact union for any selection. There are 27 distinct combinations, so this costs a few KB
and removes a whole class of wrong answer.

BARS ARE NOT REIMPLEMENTED HERE. `tools/build_surface_confidence.py` already prices every class
against the five bars that stop a check hosting progression (guessed_region, missable, erdtree_burn,
surface_excluded, hub_merchant) and its `ProgressionSurface` docstring says outright: quote that
file, never a number in prose. This tool IMPORTS that one by path and reuses `_load()` and `_bars()`,
adding only the region axis -- so there is exactly one definition of "can host" in the repo.
`test_gf_region_census` pins the union of this table over the default classes to that tool's own
`default_hosting` total, so the two cannot drift apart silently.

THE CHECK-COUNT IDENTITY the wizard evaluates:

    checks = hub + sum(kept regions) + finale

where `finale` is the Ashen Capital's checks and exists iff a base-game region is in play
(features/finale.finale_active -- the Ashen Capital is NEVER rollable, is not in REGIONS, and is not
counted by num_regions; it hangs off the hub behind its own Lock). Verified against real built worlds
at num_regions 0/3/4/6, enable_dlc off, and dlc_only on: zero delta, including dlc_only correctly
dropping the finale.

AP-FREE by construction, like the tool it borrows from: the generated modules are loaded BY PATH,
because importing the `eldenring` package pulls `BaseClasses`. That keeps it runnable in the coverage
half of CI, which has no Archipelago.

Usage:
    python tools/build_region_census.py            # write the JSON and inject it into wizard.html
    python tools/build_region_census.py --check    # exit 1 if either copy is stale (CI drift gate)
    python tools/build_region_census.py --summary  # human table, writes nothing
"""
import hashlib
import importlib.util
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GF = os.path.join(ROOT, "greenfield")
PKG = os.path.join(GF, "eldenring")
OUT = os.path.join(ROOT, "wizard", "region-census.json")
WIZARD_HTML = os.path.join(ROOT, "wizard", "wizard.html")
SCRIPT_ID = "er-region-census"
SIBLING = os.path.join(ROOT, "tools", "build_surface_confidence.py")

SCHEMA = 1


def _sibling():
    """build_surface_confidence, loaded by path. It owns _load() and _bars(); we add the region
    axis and nothing else, so 'can host' has one definition in this repo."""
    if not os.path.isfile(SIBLING):
        raise SystemExit("build_region_census: tools/build_surface_confidence.py is missing -- "
                         "this tool reuses its bar definitions and will not reimplement them.")
    spec = importlib.util.spec_from_file_location("_brc_surface_confidence", SIBLING)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _region_spine(mods):
    """region_spine, loaded under the shim package _load() already installed (its only import is
    `from .data import REGIONS`, which resolves to the already-loaded _sc_gf.data)."""
    path = os.path.join(PKG, "region_spine.py")
    if not os.path.isfile(path):
        raise SystemExit("build_region_census: greenfield/eldenring/region_spine.py is missing.")
    spec = importlib.util.spec_from_file_location("_sc_gf.region_spine", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_sc_gf.region_spine"] = mod
    spec.loader.exec_module(mod)
    return mod


def measure(sc=None):
    """The census dict. Pure over the generated data; no I/O."""
    sc = sc or _sibling()
    mods = sc._load()
    spine = _region_spine(mods)
    data = mods["data"]
    contract = mods["contract"]
    lt = mods["location_tags"].LOCATION_TAGS
    if not lt:
        raise SystemExit("build_region_census: LOCATION_TAGS is EMPTY -- refusing to emit a census "
                         "of zeroes. Regenerate with `python greenfield/gen_data.py`.")

    bars = sc._bars(mods)
    barred = frozenset().union(*bars.values())
    exclude_tags = set(getattr(contract, "SURFACE_EXCLUDE_TAGS", ()) or ())
    vocab = list(contract.IMPORTANT_LOCATION_TYPES)
    vocab_set = set(vocab)
    # ORDER COMES FROM THE VOCABULARY, NEVER FROM THE CONTAINER. SURFACE_DEFAULT_CLASSES is a
    # frozenset, and a Python set of strings has no stable iteration order across processes --
    # emitting list(...) of it made two runs of this tool disagree, and --check caught it before it
    # could land. Same bug class, same fix, as features/progression_surface.selected_surface.
    default_classes = [c for c in vocab if c in set(contract.SURFACE_DEFAULT_CLASSES)]

    rollable = list(spine.REGIONS)
    dlc = set(spine.DLC_REGIONS)
    parent = dict(spine.REGION_PARENT)
    hub = data.HUB
    finale_region = getattr(data, "FINALE_REGION", None)

    regions = {}
    for name in sorted(data.LOCATIONS):
        combos = {}
        for _n, ap, _f in data.LOCATIONS[name]:
            tags = set(lt.get(ap) or ())
            if not tags or (exclude_tags & tags) or ap in barred:
                continue
            key = "|".join(sorted(tags & vocab_set))
            if not key:
                continue
            combos[key] = combos.get(key, 0) + 1
        regions[name] = {
            "checks": len(data.LOCATIONS[name]),
            # rollable = drawn by num_regions. The hub is always present; the finale is conditional
            # but never rolled. Both are false here and handled by their own top-level rules.
            "rollable": name in rollable,
            "dlc": name in dlc,
            "parent": parent.get(name),
            "combos": dict(sorted(combos.items())),
        }

    census = {
        "schema": SCHEMA,
        "source": "greenfield/eldenring {data,location_tags,missable_locations,contract,region_spine}.py",
        "hub_region": hub,
        "finale": {
            "region": finale_region,
            # Stated as a rule rather than a number so a consumer cannot apply it to the wrong seed:
            # features/finale.finale_active -- the finale exists iff the base game is in play.
            "present_when": "any non-DLC region is eligible (i.e. not dlc_only)",
        },
        "classes": vocab,
        "default_classes": default_classes,
        "parent": dict(sorted(parent.items())),
        "regions": regions,
    }
    # Deterministic surface hash (no timestamps) so --check can byte-compare and a diff names itself.
    payload = json.dumps([census["hub_region"], census["classes"], census["default_classes"],
                          census["parent"], census["regions"]], sort_keys=True)
    census["source_sha256"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return census


def surface_union(census, classes, region_names):
    """Exact hosting count for `classes` over `region_names` -- the same union the wizard computes.
    Lives here so the test and the tool agree on the semantics rather than restating them."""
    sel = set(classes)
    total = 0
    for name in region_names:
        r = census["regions"].get(name)
        if not r:
            continue
        for combo, count in r["combos"].items():
            if sel & set(combo.split("|")):
                total += count
    return total


def dumps(census):
    # Deterministic (no timestamps). "</" escaped so the blob is safe to inline in a <script> tag,
    # matching dump_options_metadata.dumps.
    return json.dumps(census, indent=1, ensure_ascii=False, sort_keys=True).replace("</", "<\\/") + "\n"


def inject(text):
    if not os.path.isfile(WIZARD_HTML):
        sys.exit("[FAIL] inject: %s not found" % WIZARD_HTML)
    html = open(WIZARD_HTML, "r", encoding="utf-8", newline="").read()
    blob = ('<script id="%s" type="application/json">\n' % SCRIPT_ID) + text + "</script>"
    pat = re.compile(r'<script id="%s" type="application/json">.*?</script>' % SCRIPT_ID, re.S)
    if not pat.search(html):
        sys.exit("[FAIL] inject: <script id=\"%s\"> block not found in wizard.html -- add the "
                 "placeholder before running this tool." % SCRIPT_ID)
    html = pat.sub(lambda _m: blob, html, count=1)
    with open(WIZARD_HTML, "w", encoding="utf-8", newline="") as f:
        f.write(html)
    print("[ok] injected census into %s" % os.path.relpath(WIZARD_HTML, ROOT))


def summarise(census):
    regs = census["regions"]
    dflt = census["default_classes"]
    w = max(len(n) for n in regs)
    out = ["%-*s %7s %9s  %s" % (w, "region", "checks", "surface", "flags"), ""]
    out[1] = "-" * len(out[0])
    for name in sorted(regs, key=lambda n: -regs[n]["checks"]):
        r = regs[name]
        flags = ",".join([f for f, on in (("dlc", r["dlc"]), ("rollable", r["rollable"])) if on]) or "-"
        out.append("%-*s %7d %9d  %s"
                   % (w, name, r["checks"], surface_union(census, dflt, [name]), flags))
    out.append("")
    out.append("all regions: %d checks | %d hosting on the default surface"
               % (sum(r["checks"] for r in regs.values()),
                  surface_union(census, dflt, list(regs))))
    out.append("num_regions is a DRAW SIZE -- a seed keeps a SUBSET, so these are per-region parts, "
               "not a seed's totals.")
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    census = measure()
    fresh = dumps(census)

    if "--summary" in argv:
        print("\n".join(summarise(census)))
        return 0

    if "--check" in argv:
        stale = []
        if not os.path.isfile(OUT):
            stale.append("wizard/region-census.json missing")
        elif open(OUT, "r", encoding="utf-8", newline="").read().replace("\r\n", "\n") != fresh:
            stale.append("wizard/region-census.json differs from a fresh emit")
        if os.path.isfile(WIZARD_HTML):
            html = open(WIZARD_HTML, "r", encoding="utf-8", newline="").read()
            if fresh.replace("\r\n", "\n") not in html.replace("\r\n", "\n"):
                stale.append("wizard/wizard.html inlined census differs from a fresh emit")
        if stale:
            print("[STALE] " + "; ".join(stale))
            print("        fix: python tools/build_region_census.py")
            return 1
        print("[ok] region census is current (%d regions, %d classes)"
              % (len(census["regions"]), len(census["classes"])))
        return 0

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(fresh)
    print("[ok] wrote %s (%d regions)" % (os.path.relpath(OUT, ROOT), len(census["regions"])))
    # ALWAYS both copies -- a tool whose default leaves the tree half-applied will half-apply it
    # (CONTRIBUTING rule 9; dump_options_metadata's docstring records the four commits that proved it).
    inject(fresh)
    return 0


if __name__ == "__main__":
    sys.exit(main())
