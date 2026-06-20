#!/usr/bin/env python3
r"""patch_baker_sphere_unmapped_diag.py

Adds a CAPTURE DIAGNOSTIC to the sphere-basis reshape loop in EnemyRandomizer.cs. When
completion_scaling_basis = sphere, every enemy whose MSB map does NOT resolve to an AP region
via CompApRegionForMap (so it falls back to geographic tiering) is recorded by map id with a
count. After the reshape, the bake log prints the distinct unmapped maps sorted by enemy count.

WHY: there is no complete public m61 (DLC Land of Shadow overworld) tile->region table -- the
DLC overworld is one contiguous map and references only list scattered dungeon-connection tiles.
Instead of guessing, run ONE dlc_only enemy-OFF bake with this diag and the log will list the
exact m61_XX_YY_00 tiles the DLC enemies live on, with weights. That ground-truth list is what
we build the m61 branch of CompApRegionForMap from (same recipe as the m60 fill). It also audits
the m60 table just added (any base tile still printing here is a hole to plug).

This is READ-ONLY logging -- it changes no tiers, only reports. Safe to ship alongside the real
scaling.

Three surgical inserts (idempotent marker: "compUnmapped"):
  1. declare  var compUnmapped  next to compSphereHits
  2. else-branch in the loop: compRegion==null with a non-empty Map -> count it
  3. after the sphere-basis summary line: dump sorted unmapped maps

Run on Windows from repo root:
    python patch_baker_sphere_unmapped_diag.py
CRLF-preserving; exact-match byte replace; idempotent. Uses System.Linq (already imported in
EnemyRandomizer.cs). PREREQ: the sphere bridge is applied (compSphereHits present).
"""
import os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
ER = os.path.join(ROOT, "SoulsRandomizers", "RandomizerCommon", "EnemyRandomizer.cs")
if not os.path.exists(ER):
    sys.exit("ERROR: EnemyRandomizer.cs not found under SoulsRandomizers/RandomizerCommon (run from repo root).")


def crlf(s):
    # normalize any bare \n in our literals to \r\n to match the (CRLF) source file
    return s.replace("\r\n", "\n").replace("\n", "\r\n")


# --- 1. declare the collector ---------------------------------------------------------------
A_ANCHOR = crlf(
    '                int compSphereHits = 0;   // enemies whose tier came from a region sphere target\n'
)
A_INSERT = crlf(
    '                var compUnmapped = new Dictionary<string, int>();   // [unmapped diag] MSB map id -> enemy count (basis=sphere, no AP region)\n'
)

# --- 2. count unmapped enemies in the loop --------------------------------------------------
B_ANCHOR = crlf(
    '                            compSphereHits++;\n'
    '                        }\n'
)
B_INSERT = crlf(
    '                            compSphereHits++;\n'
    '                        }\n'
    '                        else if (compRegion == null && compInfo != null && !string.IsNullOrEmpty(compInfo.Map))\n'
    '                        {\n'
    '                            compUnmapped.TryGetValue(compInfo.Map, out int compUmN);\n'
    '                            compUnmapped[compInfo.Map] = compUmN + 1;\n'
    '                        }\n'
)

# --- 3. dump after the existing sphere-basis summary ----------------------------------------
C_ANCHOR = crlf(
    '                if (CompletionScaleBasis == 1)\n'
    '                    Console.WriteLine($"CompletionScaling sphere basis: reshaped {compSphereHits} enemies by region target "\n'
    '                        + $"(targets={(RegionSphereTargets?.Count ?? 0)}); remainder on geographic fallback.");\n'
)
C_INSERT = C_ANCHOR + crlf(
    '                if (CompletionScaleBasis == 1 && compUnmapped.Count > 0)\n'
    '                {\n'
    '                    var compUmSorted = compUnmapped.OrderByDescending(kv => kv.Value).ToList();\n'
    '                    int compUmTotal = compUmSorted.Sum(kv => kv.Value);\n'
    '                    Console.WriteLine($"CompletionScaling UNMAPPED maps (basis=sphere): {compUmSorted.Count} distinct, {compUmTotal} enemies on geographic fallback -- fill CompApRegionForMap:");\n'
    '                    foreach (var compUm in compUmSorted)\n'
    '                        Console.WriteLine($"  {compUm.Key}  x{compUm.Value}");\n'
    '                }\n'
)


def apply(txt, anchor, insert, label):
    n = txt.count(anchor)
    if n != 1:
        sys.exit("  [FAIL] %s: anchor found %d times (expected 1); not modified." % (label, n))
    return txt.replace(anchor, insert, 1)


with open(ER, "rb") as f:
    txt = f.read().decode("utf-8")

if "compUnmapped" in txt:
    print("  [skip] unmapped diag already present (compUnmapped found).")
    sys.exit(0)

txt = apply(txt, A_ANCHOR, A_INSERT, "declare collector")
txt = apply(txt, B_ANCHOR, B_INSERT, "loop else-branch")
txt = apply(txt, C_ANCHOR, C_INSERT, "summary dump")

with open(ER, "wb") as f:
    f.write(txt.encode("utf-8"))

print("  [ok]   sphere unmapped-map diagnostic added.")
print("DONE -- rebuild SoulsRandomizers, then a dlc_only enemy-OFF bake with completion_scaling + "
      "completion_scaling_basis: sphere. In the bake log, copy the 'UNMAPPED maps' block "
      "(m61_XX_YY_00 x N lines) and send it back to build the DLC m61 resolver table.")
