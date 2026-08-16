#!/usr/bin/env python3
"""check_wizard_keymeta_js.py -- differential gate: the wizard's key_meta rendering contract.

`progression_surface` ships PER-KEY presentation into the wizard (`key_meta`: a label and hint for
every class, a family to draw it under, and the subset lattice). Two things about that can be wrong
in ways every existing gate is blind to:

1. THE GRID CAN SILENTLY LOSE A CLASS. The renderer draws keys by walking `key_meta.families` and
   then the keys claimed by each family -- so a class that no family claims, or a family with no
   keys, is simply not drawn. The player then cannot select something the world offers, and the page
   looks complete. `surface_class_meta()` raises on that gap in Python; this gate proves the SHIPPED
   metadata (which is what the page actually reads) has no such gap, and that every drawn key is a
   real `valid_keys` member -- a label for a key AP would reject is a trap, not a hint.

2. THE REDUNDANCY HINT CAN INVERT. `ERW.surfaceCoverage` inverts the containment relation to tell a
   player "you already have these". Get the direction wrong and it confidently says the opposite --
   which is exactly the failure that already happened once, in prose: contract.py carried this
   lattice as a comment and the comment was BACKWARDS for months (it called MajorBoss a subset of
   Remembrance/GreatRune; it is their superset). A comment cannot be executed. This can.

3. THE NUMBER ON THE BOX CAN DRIFT FROM THE NUMBER THE FILL OBEYS. The grid shows what each class
   contributes to the surface (`ERW.surfaceMarginals`), computed in JS from the region census. That
   is the figure a player chooses on. This gate closes the loop on it three ways: JS == an
   independent Python evaluation; single-class totals == the `eligible` column of
   greenfield/surface_confidence.tsv; and the default selection's total == that file's headline
   hosting number. surface_confidence is itself pinned to `features/progression_surface
   .allowed_ap_ids` by test_gf_surface_confidence, so the chain is
   **wizard JS == Python == surface_confidence == allowed_ap_ids**, i.e. the number a player reads is
   the number the fill obeys. Nothing else in the repo executes that JS.

   NOT COVERED HERE, on purpose: whether the census's per-region `dlc` flags are right. The
   cross-check runs DLC-on, so corrupting those flags does not move it -- verified by mutation.
   `test_gf_region_census.test_check_count_identity_against_real_worlds` builds REAL worlds with
   `enable_dlc: False` and `dlc_only: True` among its cases, which pins them harder than anything
   this file could assert about a json blob. Duplicating it here would only add a second thing to
   keep in step.

WHY A DIFFERENTIAL, not an assertion: the Python side below re-derives coverage from `contains`
independently, and the expectation for the load-bearing case is pinned to the LIVE tag data rather
than typed -- `MajorBoss` really does contain `Remembrance`, and the gate asserts the pair from the
shipped lattice, so it cannot be satisfied by two implementations agreeing on a wrong table.

NEEDS NODE. Exits 4 (SKIP) when node is absent, mirroring check_wizard_census_js.py, so a box
without it reports honestly rather than passing vacuously.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIZARD_HTML = os.path.join(ROOT, "wizard", "wizard.html")

# Selections spanning: the shipped default; a lone broad class; broad + its children (the redundancy
# case the hint exists for); two nested shop classes; the empty set (feature off); and every class at
# once, which maximises the number of covered pairs.
CASES = [
    None,                                              # = the option's own default
    ["MajorBoss"],
    ["MajorBoss", "Remembrance", "GreatRune"],
    ["Boss", "MajorBoss", "LegacyBoss", "FieldBoss"],
    ["Shop", "ShopNonSpell", "ShopSlot"],
    [],
    "ALL",
]


def _core(html):
    m = re.search(r'<script id="wizard-core">\n(.*?)</script>', html, re.S)
    if not m:
        sys.exit("[FAIL] wizard.html has no <script id=\"wizard-core\"> block")
    return m.group(1)


def _metadata(html):
    m = re.search(r'<script id="er-options-metadata" type="application/json">\n(.*?)</script>',
                  html, re.S)
    if not m:
        sys.exit("[FAIL] wizard.html has no injected options metadata")
    return json.loads(m.group(1))


def _keymeta_options(meta):
    return [o for o in meta["options"] if o.get("key_meta")]


def _census(html):
    m = re.search(r'<script id="er-region-census" type="application/json">\n(.*?)</script>',
                  html, re.S)
    return json.loads(m.group(1)) if m else None


def _tsv_eligible():
    """{class: eligible} from the committed surface_confidence.tsv, plus its headline hosting total.

    Read from the ARTIFACT rather than recomputed, on purpose: the artifact is what
    test_gf_surface_confidence pins to allowed_ap_ids, so agreeing with it is agreeing with the
    fill. Recomputing here would just be a third implementation to keep in step.
    """
    path = os.path.join(ROOT, "greenfield", "surface_confidence.tsv")
    if not os.path.isfile(path):
        return None, None
    cols, out, hosting = None, {}, None
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith("#"):
            m = re.search(r"hosting (\d+) \|", line)
            if m and hosting is None:
                hosting = int(m.group(1))
            continue
        parts = line.split("\t")
        if cols is None:
            cols = parts
            continue
        row = dict(zip(cols, parts))
        out[row["class"]] = int(row["eligible"])
    return out, hosting


def py_marginals(census, selected, enable_dlc=True, dlc_only=False, rung="bosses"):
    """Reference implementation of ERW.surfaceMarginals. Exact set arithmetic over tag COMBINATIONS,
    plus the DERIVED classes, which are not combinations at all.

    `rung` is dungeon_sweep. SweepSlot contributes one check per sweep the seed RUNS, so its worth
    is 0 / 64 / 138 / 215 corpus-wide across none / minidungeons / all / bosses. Defaulting to
    "bosses" mirrors the JS, which defaults to the shipped `dungeon_sweep`."""
    R = census["regions"]
    in_play = [n for n, r in R.items() if (r["dlc"] if dlc_only else (enable_dlc or not r["dlc"]))]

    def hits(sel):
        sel = set(sel)
        n = 0
        for name in in_play:
            for combo, cnt in R[name]["combos"].items():
                if sel & set(combo.split("|")):
                    n += cnt
            if "SweepSlot" in sel:
                n += (R[name].get("sweep_slots") or {}).get(rung, 0)
        return n

    cur = set(selected or ())
    total = hits(cur)
    marginal = {}
    for cl in census.get("classes", ()):
        probe = set(cur)
        if cl in cur:
            probe.discard(cl)
            marginal[cl] = total - hits(probe)
        else:
            probe.add(cl)
            marginal[cl] = hits(probe) - total
    return {"total": total, "marginal": marginal, "regions": len(in_play)}


def py_coverage(km, selected):
    """Reference implementation: {child: parent} over SELECTED pairs, first parent in key_meta order."""
    contains = km.get("contains") or {}
    sel = set(selected or ())
    out = {}
    for entry in km["keys"]:
        if entry["key"] not in sel:
            continue
        for child in contains.get(entry["key"], ()):
            if child in sel and child not in out:
                out[child] = entry["key"]
    return out


def structural_faults(o):
    """The grid must be able to draw every key exactly once, and only real keys."""
    km = o["key_meta"]
    faults = []
    valid = set(o["valid_keys"] or ())
    drawn = [e["key"] for e in km["keys"]]
    fam_ids = [f["id"] for f in km["families"]]
    if len(set(drawn)) != len(drawn):
        faults.append("a key is drawn twice: %s" % sorted({k for k in drawn if drawn.count(k) > 1}))
    missing = sorted(valid - set(drawn))
    if missing:
        faults.append("valid_keys the grid would NEVER draw (no family claims them): %s" % missing)
    unknown = sorted(set(drawn) - valid)
    if unknown:
        faults.append("labelled keys that are not valid_keys, so AP would reject them: %s" % unknown)
    for e in km["keys"]:
        if e["family"] not in fam_ids:
            faults.append("key %r sits in family %r, which is not in key_meta.families -- it would "
                          "not be drawn" % (e["key"], e["family"]))
        if not (e.get("label") or "").strip():
            faults.append("key %r has an empty label and would render as a bare tag name" % e["key"])
    for f in km["families"]:
        if not any(e["family"] == f["id"] for e in km["keys"]):
            faults.append("family %r claims no keys -- an empty heading" % f["id"])
    # Containment must point at real keys in both directions, or the hint names something invisible.
    for parent, kids in (km.get("contains") or {}).items():
        if parent not in valid:
            faults.append("contains names unknown parent %r" % parent)
        for k in kids:
            if k not in valid:
                faults.append("contains[%r] names unknown child %r" % (parent, k))
        if parent in kids:
            faults.append("contains[%r] contains itself" % parent)
    return faults


def lattice_faults(o):
    """The relation must be a strict partial order: no cycles, nothing containing itself.

    A cycle would make the hint claim two classes each cover the other, and the renderer would
    annotate whichever it saw first -- a coin flip presented as advice.
    """
    contains = {k: set(v) for k, v in (o["key_meta"].get("contains") or {}).items()}
    faults = []
    for a, kids in contains.items():
        for b in kids:
            if a in contains.get(b, ()):
                faults.append("mutual containment %r <-> %r -- not a strict lattice" % (a, b))
    return faults


def _run_node_marginals(core, census, cases):
    harness = (core + "\nconst __census = " + json.dumps(census) + ";\n"
               + "const __cases = " + json.dumps(cases) + ";\n"
               + "console.log(JSON.stringify(__cases.map(c => ERW.surfaceMarginals("
                 "__census, c.selected, {enableDlc: c.enableDlc, dlcOnly: c.dlcOnly}))));\n")
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "marginals.js")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(harness)
        out = subprocess.run(["node", path], capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit("[FAIL] node marginals harness failed:\n" + (out.stderr or "")[-4000:])
    return json.loads(out.stdout.strip().splitlines()[-1])


def _run_node_tree(core, fams):
    """`ERW.surfaceTree` for one family at a time, as the page calls it."""
    harness = (core + "\nconst __f = " + json.dumps(fams) + ";\n"
               + "console.log(JSON.stringify(__f.map(f => "
                 "ERW.surfaceTree(f.keys, f.contains))));\n")
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "tree.js")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(harness)
        out = subprocess.run(["node", path], capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit("[FAIL] node tree harness failed:\n" + (out.stderr or "")[-4000:])
    return json.loads(out.stdout.strip().splitlines()[-1])


def tree_faults(km, fam_id, rows):
    """What the nesting must be true of, whatever the lattice says (#733).

    Deliberately NOT "the bosses family looks like <this picture>": the tree is derived from
    `contains`, so a picture would pin today's data and go red on an unrelated roster change --
    which is exactly how #748's ladder literal broke main hours after it merged. These are the
    properties that make the drawing trustworthy at any shape.
    """
    faults = []
    keys = [k["key"] for k in km["keys"] if k.get("family") == fam_id]
    contains = km.get("contains") or {}
    got = [r["key"] for r in rows]

    # 1. TOTALITY. The renderer draws exactly these rows, so anything missing is a class the player
    #    cannot select, and anything duplicated is a checkbox that fights itself.
    if sorted(got) != sorted(keys):
        faults.append("family %r: the tree is not a permutation of its keys -- drawn %s, family has %s"
                      % (fam_id, got, keys))
        return faults
    if len(set(got)) != len(got):
        faults.append("family %r: a key is drawn twice: %s" % (fam_id, got))

    at = {r["key"]: i for i, r in enumerate(rows)}
    depth = {r["key"]: r["depth"] for r in rows}
    infam = set(keys)

    for r in rows:
        parents = [p for p in keys if p != r["key"] and r["key"] in (contains.get(p) or [])]
        # 2. A CONTAINED CLASS IS DRAWN INSIDE SOMETHING, and after it. Flat-and-covered is the
        #    reading this issue exists to end.
        if parents and depth[r["key"]] == 0:
            faults.append("family %r: %s is contained by %s but is drawn at the top level"
                          % (fam_id, r["key"], parents))
        # 3. NEAREST parent, not any parent. Both Boss and MajorBoss contain Remembrance; hanging it
        #    off Boss is true and useless.
        if parents:
            size = {p: len(set(contains.get(p) or []) & infam) for p in parents}
            nearest = min(parents, key=lambda p: (size[p], keys.index(p)))
            if at[nearest] > at[r["key"]] or depth[r["key"]] != depth[nearest] + 1:
                faults.append("family %r: %s should sit one level inside %s (its nearest container)"
                              % (fam_id, r["key"], nearest))
    return faults


def _run_node(core, cases):
    harness = (core + "\nconst __cases = " + json.dumps(cases) + ";\n"
               + "console.log(JSON.stringify(__cases.map(c => "
                 "ERW.surfaceCoverage(c.km, c.selected))));\n")
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "keymeta.js")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(harness)
        out = subprocess.run(["node", path], capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit("[FAIL] node harness failed:\n" + (out.stderr or "")[-4000:])
    return json.loads(out.stdout.strip().splitlines()[-1])


def main(argv=None):
    # Read-only gate: normalise CRLF so the \n-written patterns below match a Windows checkout.
    html = open(WIZARD_HTML, "r", encoding="utf-8", newline="").read().replace("\r\n", "\n")
    meta = _metadata(html)
    opts = _keymeta_options(meta)
    if not opts:
        sys.exit("[FAIL] no option ships key_meta -- this gate would pass vacuously. If the hook was "
                 "removed on purpose, remove this gate in the same commit.")

    bad = []
    for o in opts:
        for f in structural_faults(o) + lattice_faults(o):
            bad.append("%s: %s" % (o["key"], f))

    # The load-bearing pair, read OUT OF the shipped lattice rather than typed here: whatever the
    # data says contains what, the hint must point from the narrow class to the broad one.
    for o in opts:
        contains = o["key_meta"].get("contains") or {}
        if not contains:
            bad.append("%s: key_meta.contains is EMPTY -- the redundancy hint can never fire, and "
                       "the derivation reads LOCATION_TAGS, so this means the dump ran without "
                       "generated data" % o["key"])

    if not shutil.which("node"):
        print("[SKIP] node not on PATH -- the wizard's coverage inversion is NOT gated on this box.")
        if bad:
            print("[FAIL] " + "\n       ".join(bad))
            return 1
        print("[ok] key_meta structure is sound (%d option(s)); JS half skipped" % len(opts))
        return 4

    cases = []
    for o in opts:
        km = o["key_meta"]
        for c in CASES:
            sel = (o["default"] if c is None
                   else [e["key"] for e in km["keys"]] if c == "ALL" else c)
            sel = [k for k in sel if k in set(o["valid_keys"] or ())]
            cases.append({"key": o["key"], "km": km, "selected": sel})

    js = _run_node(_core(html), cases)
    for case, got in zip(cases, js):
        want = py_coverage(case["km"], case["selected"])
        if got != want:
            bad.append("%s selection %s: JS coverage %s != Python %s"
                       % (case["key"], case["selected"], got, want))

    # THE NESTING (#733). Same shape of check as the coverage half: run the shipped JS, assert the
    # properties rather than a picture of today's lattice.
    fams = []
    for o in opts:
        km = o["key_meta"]
        for fam in (km.get("families") or []):
            keys = [k for k in km["keys"] if k.get("family") == fam["id"]]
            if keys:
                fams.append({"opt": o["key"], "fam": fam["id"], "keys": keys,
                             "contains": km.get("contains") or {}})
    if fams:
        trees = _run_node_tree(_core(html), fams)
        for f, rows in zip(fams, trees):
            km = next(o["key_meta"] for o in opts if o["key"] == f["opt"])
            for fault in tree_faults(km, f["fam"], rows):
                bad.append("%s: %s" % (f["opt"], fault))
        # ...and SOMETHING must actually nest, or the tree is a flat list with extra steps.
        nested = [f["fam"] for f, rows in zip(fams, trees) if any(r["depth"] for r in rows)]
        if not nested:
            bad.append("no family nests at all -- key_meta.contains describes a lattice the page is "
                       "drawing flat, which is the whole of #733")

    # ...and the inversion must actually FIRE somewhere, or agreement is agreement about nothing.
    fired = [c for c, g in zip(cases, js) if g]
    if not fired:
        bad.append("surfaceCoverage returned {} for every case -- the gate is vacuous")

    # ---- the marginal counts: JS == Python == surface_confidence.tsv ----------------------------
    census = _census(html)
    mg_cases = 0
    if census is None:
        bad.append("wizard.html has no injected region census -- the surface grid cannot show what "
                   "any box is worth, and this half of the gate would pass vacuously")
    else:
        classes = list(census.get("classes") or ())
        default = list(census.get("default_classes") or ())
        MG_CASES = [
            {"selected": default, "enableDlc": True, "dlcOnly": False},
            {"selected": default, "enableDlc": False, "dlcOnly": False},
            {"selected": ["Boss"], "enableDlc": True, "dlcOnly": False},
            {"selected": ["Boss", "MajorBoss", "FieldBoss"], "enableDlc": True, "dlcOnly": False},
            {"selected": ["Shop", "ShopSlot"], "enableDlc": True, "dlcOnly": False},
            {"selected": [], "enableDlc": True, "dlcOnly": False},
            {"selected": classes, "enableDlc": True, "dlcOnly": False},
            {"selected": default, "enableDlc": True, "dlcOnly": True},
        ]
        got = _run_node_marginals(_core(html), census, MG_CASES)
        for case, g in zip(MG_CASES, got):
            want = py_marginals(census, case["selected"], case["enableDlc"], case["dlcOnly"])
            if g != want:
                bad.append("surfaceMarginals %s: JS != Python\n         JS     %s\n         Python %s"
                           % (case, g, want))
        mg_cases = len(MG_CASES)

        # 🛑 THE LOAD-BEARING CROSS-CHECK. A single-class selection's total must equal that class's
        # `eligible` count in surface_confidence.tsv, which test_gf_surface_confidence pins to
        # allowed_ap_ids. Two independent computations over two different generated artifacts.
        elig, hosting = _tsv_eligible()
        if not elig:
            bad.append("greenfield/surface_confidence.tsv is missing -- the wizard's numbers would "
                       "be ungated against the fill")
        else:
            singles = _run_node_marginals(
                _core(html), census,
                [{"selected": [c], "enableDlc": True, "dlcOnly": False} for c in classes])
            # 🛑 A DERIVED class is deliberately in the census and deliberately NOT in the tsv: the
            # tsv is a corpus-wide TAG count and SweepSlot has no tag (contract.SURFACE_DERIVED_
            # CLASSES). Skipping it would weaken the chain, so it is cross-checked the other way
            # below -- against the census's own per-rung totals, which is the only other place the
            # number exists.
            derived = set(census.get("derived_classes") or ())
            sweep_total = sum((r.get("sweep_slots") or {}).get("bosses", 0)
                              for r in census["regions"].values())
            for cl, g in zip(classes, singles):
                if cl in derived:
                    if cl in elig:
                        bad.append("%s is DERIVED but surface_confidence.tsv prices it -- one of the "
                                   "two is wrong about what the class is" % cl)
                    elif g["total"] != sweep_total:
                        bad.append("%s alone: the wizard would show %d, the census's own sweep_slots "
                                   "sum to %d" % (cl, g["total"], sweep_total))
                elif cl not in elig:
                    bad.append("%s is in the census but not priced in surface_confidence.tsv" % cl)
                elif g["total"] != elig[cl]:
                    bad.append("%s: the wizard would show %d hosting locations, surface_confidence"
                               ".tsv says %d eligible -- the number a player chooses on has drifted "
                               "from the number the fill obeys" % (cl, g["total"], elig[cl]))
            if hosting is not None:
                dflt = _run_node_marginals(
                    _core(html), census,
                    [{"selected": default, "enableDlc": True, "dlcOnly": False}])[0]
                # The tsv headline prices the TAGGED half of the default surface only (it says so,
                # and test_gf_surface_confidence pins the disclosure). So the identity is not
                # equality any more -- it is equality once the derived half is added, which is a
                # STRONGER statement than the old one: it pins the size of that half too.
                dflt_derived = sweep_total if (set(default) & derived) else 0
                if dflt["total"] != hosting + dflt_derived:
                    bad.append("default surface: wizard %d vs surface_confidence.tsv headline "
                               "hosting %d + %d derived (SweepSlot) = %d"
                               % (dflt["total"], hosting, dflt_derived, hosting + dflt_derived))

    if bad:
        print("[FAIL] " + "\n       ".join(bad))
        return 1
    print("[ok] key_meta: %d option(s), %d coverage case(s), %d with live coverage; "
          "%d marginal case(s) + %d single-class cross-checks vs surface_confidence.tsv; "
          "JS == Python throughout" % (len(opts), len(cases), len(fired), mg_cases,
                                       len(census.get("classes") or ()) if census else 0))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
