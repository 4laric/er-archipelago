#!/usr/bin/env python3
r"""
patch_baker_compspherehits_fix.py  (run on Windows, in the repo root)

Build fix (NOT part of the global-scadu work). The sphere-basis completion-scaling bridge in
EnemyRandomizer.cs increments and prints `compSphereHits` (lines ~1118, ~1138) but its
declaration was dropped in an earlier edit -> CS0103. Re-add the declaration in the same scope,
next to the other comp* locals.

Idempotent, CRLF/LF-safe, makes a .bak.
"""
import os, sys, shutil

REPO = os.path.dirname(os.path.abspath(__file__))
F = os.path.join(REPO, "SoulsRandomizers", "RandomizerCommon", "EnemyRandomizer.cs")

if not os.path.isfile(F):
    sys.exit(f"ERROR: not found: {F}")
with open(F, "r", encoding="utf-8", newline="") as fh:
    text = fh.read()

if "int compSphereHits" in text:
    sys.exit("Already declares compSphereHits; nothing to do.")

nl = "\r\n" if "\r\n" in text else "\n"
anchor = "                int compMaxTier = scalingSpEffects.MaxTier;" + nl
if text.count(anchor) != 1:
    sys.exit(f"ERROR: anchor not unique ({text.count(anchor)}x).")

decl = "                int compSphereHits = 0;   // enemies reshaped by sphere-basis region target (diag)" + nl
text = text.replace(anchor, anchor + decl, 1)

shutil.copy2(F, F + ".bak_globalscadu")
with open(F, "w", encoding="utf-8", newline="") as fh:
    fh.write(text)
with open(F, "r", encoding="utf-8", newline="") as fh:
    if fh.read() != text:
        sys.exit("ERROR: write-back mismatch (truncation?). Restore the .bak.")

print("Patched EnemyRandomizer.cs: declared compSphereHits (.bak_globalscadu written). Re-run build.ps1.")
