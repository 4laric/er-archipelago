#!/usr/bin/env python3
"""grace_rando: light only the ROLLED start region's ONE freebie grace (not its full bundle).

Under a random/pool start the spawn region's graces were lit in FULL at load (_rs_pts), ignoring
grace_rando -- so "one grace per region" didn't hold for the start region (e.g. Caelid lit up). With
grace_rando on, light only that region's grace_rando freebie (the same single grace every other region
gets) and spawn the player AT it; with grace_rando off, keep the full-bundle behavior (warp = centroid).

The freebie (from _grace_rando_freebie_by_region, set in pre_fill) is chosen from the region's
non-skip graces -- grace_rando's skip set is a SUPERSET of the warp skip set, so the freebie is always
a valid (non boss-arena / non-border) warp target. __init__.py only. Idempotent, CRLF-safe, py_compiles,
.bak_grstart. Order-independent of the sealed-Limgrave patch (touches different lines).
"""
import os, sys, py_compile, tempfile

INIT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "Archipelago", "worlds", "eldenring", "__init__.py")

F1_OLD = '''            _rs_pts = [p for p in REGION_GRACE_POINTS.get(_rsr, []) if p[0] not in _RS_SKIP]
            _rs_g = [int(p[0]) for p in _rs_pts]'''
F1_NEW = '''            _rs_pts = [p for p in REGION_GRACE_POINTS.get(_rsr, []) if p[0] not in _RS_SKIP]
            # grace_rando: light only this region's ONE freebie grace (like every other region) and
            # spawn at it; otherwise light the full start-region bundle (warp = centroid, below).
            _rsr_gr_on = bool(getattr(self.options, "grace_rando", None) and self.options.grace_rando.value)
            _rsr_fb = getattr(self, "_grace_rando_freebie_by_region", {}).get(_rsr, [])
            if _rsr_gr_on and _rsr_fb:
                _rs_g = [int(_rsr_fb[0])]
            else:
                _rs_g = [int(p[0]) for p in _rs_pts]'''

F2_OLD = '''            if _rs_pts:
                _cx = sum(p[1] for p in _rs_pts) / len(_rs_pts)
                _cz = sum(p[2] for p in _rs_pts) / len(_rs_pts)
                _rsr_warp_grace = int(min(_rs_pts, key=lambda p: (p[1] - _cx) ** 2 + (p[2] - _cz) ** 2)[0])'''
F2_NEW = '''            if _rsr_gr_on and _rsr_fb:
                _rsr_warp_grace = int(_rsr_fb[0])   # spawn at the lit freebie grace
            elif _rs_pts:
                _cx = sum(p[1] for p in _rs_pts) / len(_rs_pts)
                _cz = sum(p[2] for p in _rs_pts) / len(_rs_pts)
                _rsr_warp_grace = int(min(_rs_pts, key=lambda p: (p[1] - _cx) ** 2 + (p[2] - _cz) ** 2)[0])'''

EDITS = [
    ("sub", F1_OLD, F1_NEW, '_rsr_gr_on = bool(getattr(self.options, "grace_rando", None)'),
    ("sub", F2_OLD, F2_NEW, '_rsr_warp_grace = int(_rsr_fb[0])   # spawn at the lit freebie grace'),
]

def apply_edits(text, edits):
    for kind, old, new, marker in edits:
        if marker in text:
            print(f"  [skip] applied: {marker[:46]!r}")
        elif old in text:
            if text.count(old) != 1:
                raise SystemExit(f"ABORT: anchor x{text.count(old)}: {marker!r}")
            text = text.replace(old, new, 1)
        else:
            raise SystemExit(f"ABORT: anchor not found / not applied: {marker[:46]!r}")
    return text

def main():
    if not os.path.isfile(INIT):
        print("ERROR not found:", INIT); return 1
    raw = open(INIT, "rb").read()
    total = raw.count(b"\n"); crlf = raw.count(b"\r\n") == total and total > 0
    work = raw.decode("utf-8").replace("\r\n", "\n") if crlf else raw.decode("utf-8")
    nw = apply_edits(work, EDITS)
    if nw == work:
        print("__init__.py: no change."); return 0
    out = (nw.replace("\n", "\r\n") if crlf else nw).encode("utf-8")
    with tempfile.NamedTemporaryFile("wb", suffix=".py", delete=False) as tf:
        tf.write(out); tmp = tf.name
    try:
        py_compile.compile(tmp, doraise=True)
    finally:
        os.remove(tmp)
    open(INIT + ".bak_grstart", "wb").write(raw)
    open(INIT, "wb").write(out)
    print(f"__init__.py: patched ({'CRLF' if crlf else 'LF'}); backup .bak_grstart")
    return 0

if __name__ == "__main__":
    sys.exit(main())
