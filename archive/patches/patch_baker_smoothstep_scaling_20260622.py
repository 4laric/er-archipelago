#!/usr/bin/env python3
"""
patch_baker_smoothstep_scaling_20260622.py  --  RUN ON WINDOWS, rebuild SoulsRandomizers (Release).

Completeness companion to patch_apworld_smoothstep_scaling_20260622.py: adds smoothstep (mode 4) to the
baker's GEOGRAPHIC-basis compCurve. NOT needed for a sphere-basis run (the baker uses regionSphereTargets
there). Without it, smoothstep under geographic basis would silently fall through to linear.
Idempotent, CRLF-safe, anchor-verified.
"""
import os, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
CS = os.path.join(ROOT, "SoulsRandomizers", "RandomizerCommon", "EnemyRandomizer.cs")
results = []
def _read(p):
    with open(p, "r", encoding="utf-8", newline="") as f: return f.read()
def _write(p, t):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(t)
def _eol(t): return "\r\n" if "\r\n" in t else "\n"
def _norm(s, eol): return s.replace("\r\n", "\n").replace("\n", eol)
text = _read(CS); eol = _eol(text)
sent = _norm("CompletionScaleMode == 4 ?", eol)
anchor = _norm(
    "                    CompletionScaleMode == 2 ? Math.Pow(d, 1.6)\n"
    "                    : CompletionScaleMode == 3 ? Math.Pow(d, 0.55)\n"
    "                    : d;\n", eol)
if sent in text:
    results.append(("baker compCurve mode 4", "IDEMPOTENT", "present"))
elif text.count(anchor) != 1:
    results.append(("baker compCurve mode 4", "FAIL", "anchor count=%d" % text.count(anchor)))
else:
    _write(CS, text.replace(anchor, _norm(
        "                    CompletionScaleMode == 2 ? Math.Pow(d, 1.6)\n"
        "                    : CompletionScaleMode == 3 ? Math.Pow(d, 0.55)\n"
        "                    : CompletionScaleMode == 4 ? d * d * (3.0 - 2.0 * d)\n"
        "                    : d;\n", eol)))
    results.append(("baker compCurve mode 4", "PASS" if sent in _read(CS) else "FAIL", "written"))
print("\n=== patch_baker_smoothstep_scaling summary ===")
worst = 0
for t, s, d in results:
    print("  [%-10s] %s -- %s" % (s, t, d))
    if s == "FAIL": worst = 1
print("=== %s ===" % ("ALL OK" if not worst else "FAIL"))
sys.exit(worst)
