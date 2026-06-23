#!/usr/bin/env python3
"""
patch_apworld_smoothstep_scaling_20260622.py  --  RUN ON WINDOWS (Alaric), then REGEN.

Adds `smoothstep` as completion_scaling option 4. Smoothstep S(d)=3d^2-2d^3 (= d*d*(3-2d)): zero slope
at both ends, steepest in the middle -> gentle early on-ramp, fast mid-game ramp, plateau into the cap.

Two edits, both in worlds/eldenring:
  A. options.py -- doc line + `option_smoothstep = 4` in CompletionScaling.
  B. __init__.py -- `_cs_curve` (the SPHERE-basis curve emitted as regionSphereTargets) gets mode 4.

For a SPHERE-basis run this is all that's needed: the baker applies regionSphereTargets directly (it
only checks completion_scaling > 0, which mode 4 satisfies), so NO baker rebuild -- just regen. For
GEOGRAPHIC basis, also run patch_baker_smoothstep_scaling_20260622.py (baker compCurve) + rebuild.

Idempotent, CRLF-safe, anchor-verified.
"""
import os, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(ROOT, "Archipelago", "worlds", "eldenring")
OPTIONS = os.path.join(PKG, "options.py")
INIT = os.path.join(PKG, "__init__.py")
results = []
def _read(p):
    with open(p, "r", encoding="utf-8", newline="") as f: return f.read()
def _write(p, t):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(t)
def _eol(t): return "\r\n" if "\r\n" in t else "\n"
def _norm(s, eol): return s.replace("\r\n", "\n").replace("\n", eol)
def edit(tag, path, anchor, replace_with, sentinel):
    try: text = _read(path)
    except FileNotFoundError:
        results.append((tag, "FAIL", "not found")); return
    eol = _eol(text)
    if _norm(sentinel, eol) in text:
        results.append((tag, "IDEMPOTENT", "sentinel present")); return
    a = _norm(anchor, eol); n = text.count(a)
    if n != 1:
        results.append((tag, "FAIL", "anchor count=%d" % n)); return
    _write(path, text.replace(a, _norm(replace_with, eol)))
    results.append((tag, "PASS" if _norm(sentinel, eol) in _read(path) else "FAIL", "written"))

# A1 docstring
edit("A1 options doc line", OPTIONS,
    anchor='    - steep:  concave -- difficulty climbs fast, mid-game already punishing."""\n',
    sentinel="smoothstep: S-curve",
    replace_with=(
        '    - steep:  concave -- difficulty climbs fast, mid-game already punishing.\n'
        '    - smoothstep: S-curve -- gentle early on-ramp, steep mid-game, plateau into the cap."""\n'
    ))
# A2 enum
edit("A2 options enum", OPTIONS,
    anchor="    option_steep = 3\n    default = 0\n",
    sentinel="option_smoothstep = 4",
    replace_with="    option_steep = 3\n    option_smoothstep = 4\n    default = 0\n")
# B _cs_curve
edit("B _cs_curve mode 4", INIT,
    anchor="                if _cs_mode == 3:\n                    return d ** 0.55\n",
    sentinel="d * d * (3 - 2 * d)",
    replace_with=(
        "                if _cs_mode == 3:\n"
        "                    return d ** 0.55\n"
        "                if _cs_mode == 4:\n"
        "                    return d * d * (3 - 2 * d)  # smoothstep: 3d^2-2d^3\n"
    ))

print("\n=== patch_apworld_smoothstep_scaling summary ===")
worst = 0
for t, s, d in results:
    print("  [%-10s] %s -- %s" % (s, t, d))
    if s == "FAIL": worst = 1
print("=== %s ===" % ("ALL OK" if not worst else "FAIL"))
sys.exit(worst)
