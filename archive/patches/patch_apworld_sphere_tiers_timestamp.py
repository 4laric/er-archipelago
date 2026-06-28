#!/usr/bin/env python3
r"""patch_apworld_sphere_tiers_timestamp.py

Makes the apworld's sphere-scaling inspection dump TIMESTAMPED:
  ER_SPHERE_TIERS.txt  ->  ER_SPHERE_TIERS_<YYYYMMDD-HHMMSS>.txt   (+ a header line with the stamp)

WHY: the un-timestamped ER_SPHERE_TIERS.txt silently went stale (a 2026-06-19 file survived a
2026-06-20 gen), which masked that the GENERATOR was loading a stale packaged eldenring.apworld
(no sphere emission -> AP zip slot_data missing completionScalingBasis/regionSphereTargets ->
baker fell back to geographic basis). A stamped filename (matching the gendiag_<stamp>.txt
convention) makes a no-rewrite immediately obvious: if no fresh ER_SPHERE_TIERS_<today>.txt
appears after a gen, the emission code didn't run.

NOTE: this edits the loose source only. It has NO effect until the apworld is REPACKAGED/redeployed
(build.ps1 -Apworld) so the generator actually loads it -- which is the real fix for the current bug.

Edits Archipelago/worlds/eldenring/__init__.py: the single `with open(... "ER_SPHERE_TIERS.txt" ...)`
line inside the sphere-emission block. Inserts a local time import + stamp + header, and stamps the
filename. Anchor is a unique single line (no newline dependence). Idempotent (skips if _cs_stamp present).

Run on Windows from repo root:
    python patch_apworld_sphere_tiers_timestamp.py
Preserves the file's existing newline style (CRLF or LF). Exact byte replace.
"""
import os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
INIT = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "__init__.py")
if not os.path.exists(INIT):
    sys.exit("ERROR: __init__.py not found at Archipelago/worlds/eldenring (run from repo root).")

with open(INIT, "rb") as f:
    data = f.read()

if b"_cs_stamp" in data:
    print("  [skip] timestamped sphere dump already present (_cs_stamp found).")
    sys.exit(0)

nl = b"\r\n" if b"\r\n" in data else b"\n"
IND = b" " * 16  # the with-statement's indentation inside the try block

OLD = b'with open(_csos.path.join(_csos.path.dirname(__file__), "ER_SPHERE_TIERS.txt"), "w") as _df:'
if data.count(OLD) != 1:
    sys.exit("  [FAIL] ER_SPHERE_TIERS open-line found %d times (expected 1); not modified. "
             "Is patch_apworld_sphere_scaling.py applied to __init__.py?" % data.count(OLD))

NEW = nl.join([
    b'import time as _cstime',
    IND + b'_cs_stamp = _cstime.strftime("%Y%m%d-%H%M%S")',
    IND + b'_lines.insert(0, "# ER_SPHERE_TIERS stamp=" + _cs_stamp + " maxsphere=" + str(_maxsph) + " regions=" + str(len(_region_sphere)))',
    IND + b'with open(_csos.path.join(_csos.path.dirname(__file__), "ER_SPHERE_TIERS_" + _cs_stamp + ".txt"), "w") as _df:',
])

data = data.replace(OLD, NEW, 1)
with open(INIT, "wb") as f:
    f.write(data)

print("  [ok]   sphere dump is now ER_SPHERE_TIERS_<stamp>.txt with a header line.")
print("DONE -- REPACKAGE the apworld (build.ps1 -Apworld) so gen uses it, then regenerate. "
      "Confirm a fresh ER_SPHERE_TIERS_<today-stamp>.txt appears. You can delete the stale "
      "Archipelago/worlds/eldenring/ER_SPHERE_TIERS.txt.")
