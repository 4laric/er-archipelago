#!/usr/bin/env python3
# patch_apworld_filldiag_fix_20260621.py  (run on Windows from repo root)
#
# Fix for patch_apworld_filldiag_20260621.py: the diag block called io.open() but `io` is not
# imported in __init__.py -> NameError, swallowed by the except -> no file written. Switch to the
# builtin open(), and ALSO print the key metrics to stdout so they land in generate_*.log even if
# the file path is ever odd. Idempotent (marker = the new stdout line). Apply, then re-run the sweep.

import sys, io, os
DEFAULT = os.path.join("Archipelago", "worlds", "eldenring", "__init__.py")
MARKER  = "ER_DUMP_FILL adv_by_category"

FN_ANCHOR = '            _fn = _os.path.join("output", "ER_FILLDIAG_%s_%s_%s.txt" % (self.player, _seed, _ts))'
FN_BLOCK = (
'            print("ER_DUMP_FILL seed=%s locs=%d pool=%d adv=%d prio=%d slack=%d"\n'
'                  % (_seed, len(_locs), len(_pool), len(_adv), len(self.all_priority_locations), len(_locs) - len(_adv)))\n'
'            print("ER_DUMP_FILL adv_by_category=%s" % dict(_advcat))\n'
'            _fn = _os.path.join("output", "ER_FILLDIAG_%s_%s_%s.txt" % (self.player, _seed, _ts))'
)
IO_OLD = '                with io.open(_fn, "w", encoding="utf-8") as _f:'
IO_NEW = '                with open(_fn, "w", encoding="utf-8") as _f:'


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    if not os.path.isfile(path):
        print("ERROR: file not found:", path); return 2
    with io.open(path, "r", encoding="utf-8", newline="") as f:
        src = f.read()
    nl = "\r\n" if "\r\n" in src else "\n"
    body = src.replace("\r\n", "\n")
    if MARKER in body:
        print("ALREADY FIXED -- no change."); return 0
    if "ER_DUMP_FILL" not in body:
        print("ERROR: diag block not present -- run patch_apworld_filldiag_20260621.py first."); return 4
    for tag, anc in (("fn", FN_ANCHOR), ("io", IO_OLD)):
        if body.count(anc) != 1:
            print("ERROR: anchor %s found %d (expected 1)." % (tag, body.count(anc))); return 3
    body = body.replace(FN_ANCHOR, FN_BLOCK, 1)
    body = body.replace(IO_OLD, IO_NEW, 1)
    out = body.replace("\n", nl) if nl == "\r\n" else body
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    chk = out.replace("\r\n", "\n")
    ok = MARKER in chk and "io.open(_fn" not in chk
    print("APPLIED." if ok else "WROTE but verify FAILED -- inspect.")
    return 0 if ok else 5

if __name__ == "__main__":
    raise SystemExit(main())
