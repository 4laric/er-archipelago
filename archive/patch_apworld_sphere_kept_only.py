#!/usr/bin/env python3
r"""patch_apworld_sphere_kept_only.py

Fix sphere-ordered completion scaling to ignore SEALED regions when tiering.

BUG (observed in ER_SPHERE_TIERS.txt for a num_regions seed): the sphere computation in
fill_slot_data (added by patch_apworld_sphere_scaling.py) walks self.multiworld.get_spheres(),
which under minimal accessibility sweeps the SEALED (num_regions/region_count/etc.) regions late
as one big terminal sphere. So ~75 unreachable/unplayed regions land at the max sphere (target 1.0)
AND inflate maxSphere -- compressing the actually-played chain (Limgrave..Leyndell) into the bottom
~quarter of the tier range (0.0..0.23) while content you never see is maxed. Backwards.

FIX: exclude self._spine_sealed_regions from the table, and normalize maxSphere over the KEPT
regions only, so the played chain spans the full 0..1 range. Inert on non-seal seeds
(_spine_sealed_regions is empty there).

This patches the ALREADY-APPLIED block in __init__.py (re-running patch_apworld_sphere_scaling.py
skips on its marker). The sphere patch itself is also updated, so a FRESH apply is correct too.

Run on Windows from repo root (or the eldenring apworld dir):
    python patch_apworld_sphere_kept_only.py
CRLF-safe; idempotent.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CANDS = [HERE, os.path.join(HERE, "Archipelago", "worlds", "eldenring")]
PKG = next((d for d in CANDS if os.path.exists(os.path.join(d, "__init__.py"))
            and os.path.exists(os.path.join(d, "grace_data.py"))), None)
if not PKG:
    sys.exit("ERROR: eldenring apworld dir not found (run from repo root or the apworld dir).")
P = os.path.join(PKG, "__init__.py")

with open(P, "rb") as f:
    b = f.read()
nl = b"\r\n" if b"\r\n" in b else b"\n"
def conv(s): return s.replace("\n", nl.decode("ascii")).encode("utf-8")

if conv('_spine_sealed_regions", set())\n').replace(nl, nl) in b and b.count(conv('_sealed = getattr(self, "_spine_sealed_regions", set())\n')) >= 1:
    print("  [skip] sphere computation already excludes sealed regions.")
    sys.exit(0)

REPL = [
    ("            _maxsph = max(1, len(_spheres) - 1)\n",
     '            _sealed = getattr(self, "_spine_sealed_regions", set())\n'),
    ("                    if _rn and _rn not in _region_sphere:\n",
     "                    if _rn and _rn not in _sealed and _rn not in _region_sphere:\n"),
    ("            for _rn, _sph in _region_sphere.items():\n",
     "            _maxsph = max(1, max(_region_sphere.values(), default=1))\n"
     "            for _rn, _sph in _region_sphere.items():\n"),
]
for old, new in REPL:
    ob = conv(old)
    if b.count(ob) != 1:
        sys.exit("  [FAIL] anchor %r found %d times (expected 1); not modified. "
                 "Is patch_apworld_sphere_scaling.py applied unmodified?" % (old.strip(), b.count(ob)))
    b = b.replace(ob, conv(new), 1)

with open(P, "wb") as f:
    f.write(b)
print("  [ok]   sphere targets now computed over KEPT regions only (sealed excluded; maxSphere = kept max).")
print("DONE")
