#!/usr/bin/env python3
"""Hotfix: NumRegionsOrder used `option_random`, which AP reserves (every Choice auto-supports
`random` = pick-a-random-option), tripping AssembleOptions' assertion and breaking the world
import. Rename the value random -> rolled. options.py only; __init__ dispatches by VALUE (==1 for
spine), so it is unaffected. Idempotent, CRLF-safe, py_compiles, backs up .bak_nrorder.

Run on Windows AFTER patch_apworld_numregions_merge.py:
    python patch_apworld_numregions_order_fix.py   then re-gen.
"""
import os, sys, py_compile, tempfile

TARGET = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "Archipelago", "worlds", "eldenring", "options.py")

EDITS = [
    ("    option_random = 0", "    option_rolled = 0"),
    ("    - **random** (default): roll N majors at random; reached by warp (forces region_access=warp).",
     "    - **rolled** (default): roll N majors at random; reached by warp (forces region_access=warp)."),
    ("      random (default) -- N majors rolled at random; reached by warp (forces region_access=warp),",
     "      rolled (default) -- N majors rolled at random; reached by warp (forces region_access=warp),"),
]

def main():
    if not os.path.isfile(TARGET):
        print("ERROR not found:", TARGET); return 1
    raw = open(TARGET, "rb").read()
    total = raw.count(b"\n"); crlf = raw.count(b"\r\n") == total and total > 0
    work = raw.decode("utf-8").replace("\r\n", "\n") if crlf else raw.decode("utf-8")
    if "option_rolled = 0" in work and "option_random = 0" not in work:
        print("already fixed -- no change."); return 0
    changed = False
    for old, new in EDITS:
        if old in work:
            if work.count(old) != 1:
                raise SystemExit(f"ABORT: anchor x{work.count(old)}: {old[:40]!r}")
            work = work.replace(old, new, 1); changed = True
        elif new not in work:
            # the critical first edit MUST be present; the docstring ones are best-effort
            if old.strip().startswith("option_random"):
                raise SystemExit(f"ABORT: critical anchor not found: {old!r}")
    if not changed:
        print("no change."); return 0
    out = (work.replace("\n", "\r\n") if crlf else work).encode("utf-8")
    with tempfile.NamedTemporaryFile("wb", suffix=".py", delete=False) as tf:
        tf.write(out); tmp = tf.name
    try:
        py_compile.compile(tmp, doraise=True)
    finally:
        os.remove(tmp)
    open(TARGET + ".bak_nrorder", "wb").write(raw)
    open(TARGET, "wb").write(out)
    print(f"fixed option_random -> option_rolled ({'CRLF' if crlf else 'LF'}); backup .bak_nrorder")
    return 0

if __name__ == "__main__":
    sys.exit(main())
