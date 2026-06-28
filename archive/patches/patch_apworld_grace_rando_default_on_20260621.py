#!/usr/bin/env python3
"""
patch_apworld_grace_rando_default_on_20260621.py  --  RUN ON WINDOWS.
Flip grace_rando to ON by default under region gating: GraceRando(Toggle) -> GraceRando(DefaultOnToggle).
Set grace_rando: false in a yaml for the old graces_per_region bundle behavior. Idempotent, CRLF-safe.
"""
import os, sys
OPTIONS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "Archipelago", "worlds", "eldenring", "options.py")

def _read(p):
    with open(p, "r", encoding="utf-8", newline="") as f: return f.read()
def _write(p, t):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(t)
def _eol(t): return "\r\n" if "\r\n" in t else "\n"
def _norm(s, e): return s.replace("\r\n", "\n").replace("\n", e)

def repl(tag, text, eol, old, new, sentinel, results):
    if _norm(sentinel, eol) in text:
        results.append((tag, "IDEMPOTENT")); return text
    o = _norm(old, eol)
    n = text.count(o)
    if n != 1:
        results.append((tag, "FAIL (%d matches)" % n)); return text
    results.append((tag, "PASS"))
    return text.replace(o, _norm(new, eol))

results = []
text = _read(OPTIONS); eol = _eol(text)
text = repl("base class -> DefaultOnToggle", text, eol,
            "class GraceRando(Toggle):",
            "class GraceRando(DefaultOnToggle):",
            "class GraceRando(DefaultOnToggle):", results)
text = repl("docstring default-on note", text, eol,
            '    grows the pool. No effect unless world_logic is a region-gating mode."""',
            '    grows the pool. ON BY DEFAULT under region gating; set false for the old bundle\n'
            '    (graces_per_region) behavior. No effect outside a region-gating world_logic."""',
            "ON BY DEFAULT under region gating", results)
_write(OPTIONS, text)
chk = _read(OPTIONS)
ok = ("class GraceRando(DefaultOnToggle):" in chk) and ("ON BY DEFAULT under region gating" in chk)
print("=== grace_rando default-on flip ===")
for t, s in results: print("  [%s] %s" % (s, t))
print("=== %s ===" % ("VERIFIED ON DISK" if ok else "VERIFY FAILED -- review"))
sys.exit(0 if ok else 1)
