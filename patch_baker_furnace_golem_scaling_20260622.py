#!/usr/bin/env python3
"""
patch_baker_furnace_golem_scaling_20260622.py  --  RUN ON WINDOWS (Alaric), then rebuild
SoulsRandomizers (Release) + rebake.

PROBLEM: Furnace Golems (model c5170) are never touched by completion_scaling, so they keep vanilla
stats in every region -- both incoming HP and OUTGOING damage. Root cause is in
ScalingEffects.InitializeEldenScaling: golems carry NO scaling speffect (NpcParam.spEffectID3 <= 0),
so the FIRST classification pass drops them into the tier-1 fallback
(`if (data.Model != "c0000") ret[entry.Key] = 1;`) and `continue`s -- which preempts the SECOND pass
that would otherwise infer their map's tier. A native tier of 1 means the curve has nothing to reshape
and the scale-only pass skips them (soSrc == soTgt), so they're never assigned a scaling speffect.

FIX: exclude c5170 from that tier-1 fallback. The golem then falls through to the second pass and is
classified by its map's most-common enemy tier (`mapEffects[MainMap]`), so completion_scaling reshapes
it together with the surrounding region (e.g. low tier in early Gravesite, higher in late regions).
Catches ALL Furnace Golems by model -- no entity-id enumeration. Rando exclusion (exclude:unkillable)
is untouched; this only opts them into scaling.

MUST-TEST after baking (none verifiable offline):
  1. Walk up to the Gravesite Plain golem (N of Scorched Ruins) and confirm HP/damage actually dropped
     -- field bosses sometimes IGNORE the scaling speffect (stats come straight from NpcParam). If HP
     is unchanged but damage drops (or vice-versa), that's the speffect-honoring boundary.
  2. Golems on map tiles with no other classified enemies stay unclassified (second pass needs a
     neighbour) -- check each golem actually scaled, not just the Gravesite one.
  3. Golems on tiles that log "Unknown event map target m61_..." get no scaling init applied at all.
  4. Sphere basis: confirm the sphere bridge now includes the golem (it's in ScalingSections now).

Idempotent, CRLF-safe, anchor-verified. Re-run reports IDEMPOTENT.
"""

import os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
CS = os.path.join(ROOT, "SoulsRandomizers", "RandomizerCommon", "ScalingEffects.cs")
results = []

def _read(p):
    with open(p, "r", encoding="utf-8", newline="") as f: return f.read()
def _write(p, t):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(t)
def _eol(t): return "\r\n" if "\r\n" in t else "\n"
def _norm(s, eol): return s.replace("\r\n", "\n").replace("\n", eol)

def edit(tag, path, anchor, replace_with, sentinel):
    try:
        text = _read(path)
    except FileNotFoundError:
        results.append((tag, "FAIL", "file not found: %s" % path)); return
    eol = _eol(text)
    if _norm(sentinel, eol) in text:
        results.append((tag, "IDEMPOTENT", "sentinel present")); return
    a = _norm(anchor, eol)
    n = text.count(a)
    if n == 0:
        results.append((tag, "FAIL", "anchor not found")); return
    if n > 1:
        results.append((tag, "FAIL", "anchor not unique (%d matches)" % n)); return
    _write(path, text.replace(a, _norm(replace_with, eol)))
    ok = _norm(sentinel, eol) in _read(path)
    results.append((tag, "PASS" if ok else "FAIL", "written" if ok else "post-write verify failed"))

edit(
    "Furnace Golem (c5170) opt-in to scaling", CS,
    anchor=(
        '                    // TODO: Is this always correct? bear 60310042 in Dragonbarrow is missing one, for instance\n'
        '                    if (data.Model != "c0000")\n'
        '                    {\n'
        '                        ret[entry.Key] = 1;\n'
        '                    }\n'
    ),
    sentinel='data.Model != "c5170"',
    replace_with=(
        '                    // TODO: Is this always correct? bear 60310042 in Dragonbarrow is missing one, for instance\n'
        '                    // Furnace Golems (c5170) carry NO scaling speffect, so this tier-1 fallback\n'
        '                    // would leave them vanilla in every region (HP AND outgoing damage, in/out).\n'
        '                    // Excluding c5170 lets the SECOND pass infer their map tier so\n'
        '                    // completion_scaling reshapes them with the surrounding region. Rando\n'
        '                    // exclusion (exclude:unkillable) is unaffected. (Alaric 2026-06-22)\n'
        '                    if (data.Model != "c0000" && data.Model != "c5170")\n'
        '                    {\n'
        '                        ret[entry.Key] = 1;\n'
        '                    }\n'
    ),
)

print("")
print("=== patch_baker_furnace_golem_scaling summary ===")
worst = 0
for tag, status, detail in results:
    print("  [%-10s] %s  --  %s" % (status, tag, detail))
    if status == "FAIL": worst = 1
print("=== %s ===" % ("ALL OK (PASS/IDEMPOTENT)" if not worst else "ONE OR MORE FAIL -- review above"))
sys.exit(worst)
