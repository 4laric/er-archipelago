#!/usr/bin/env python3
r"""patch_apworld_numregions_log_kept_regions.py

Record the kept-region NAMES in the num_regions pool resolver log line, so every
generate_*.log says WHICH middle regions a seed kept -- enabling region-frequency
analytics across a gen_sweep. (ER gen does not emit a _Spoiler.txt, and the AP zip
needs the runtime to parse; the resolver log line is the cheap, reliable source.)

CHANGE  (Archipelago/worlds/eldenring/__init__.py, ~L584)
    "... kept {_eff} middle region(s), injecting great runes ..."
  becomes
    "... kept {_eff} middle region(s) {sorted(_kept_r)}, injecting great runes ..."
_kept_r is the final kept-region set in scope there (the pool branch recomputes it).
Single, idempotent, byte-level (CRLF-safe) insert. Refuses to write on a short/
truncated read -- see the bash-read-truncation lesson.

USAGE (Windows, from the repo root):
    python patch_apworld_numregions_log_kept_regions.py
    .\build.ps1 -Apworld        # repackage the apworld so it carries the change
"""
import os, sys

REPO   = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(REPO, "Archipelago", "worlds", "eldenring", "__init__.py")

ANCHOR      = b"middle region(s), injecting great runes"
REPLACE     = b"middle region(s) {sorted(_kept_r)}, injecting great runes"
ALREADY     = REPLACE                       # idempotency marker
TAIL_SYMBOL = b"interpret_slot_data"        # EOF anchor: prove we read the whole file


def main():
    if not os.path.isfile(TARGET):
        sys.exit(f"ERROR: not found: {TARGET}")
    size = os.path.getsize(TARGET)
    with open(TARGET, "rb") as f:
        data = f.read()
    # read-truncation guard (the mount / a short read must NOT be written back)
    if len(data) != size:
        sys.exit(f"ERROR: short read ({len(data)} != {size} bytes) -- I/O truncation; aborting, no write.")
    if TAIL_SYMBOL not in data:
        sys.exit(f"ERROR: tail symbol {TAIL_SYMBOL!r} missing -- source looks truncated; aborting, no write.")

    if ALREADY in data:
        print("Already patched -- kept-region names already in the log line. No change.")
        return

    n = data.count(ANCHOR)
    if n != 1:
        sys.exit(f"ERROR: expected exactly 1 anchor occurrence, found {n}. Aborting (no write).")

    new = data.replace(ANCHOR, REPLACE, 1)
    expected = len(data) + (len(REPLACE) - len(ANCHOR))
    if len(new) != expected or ALREADY not in new or TAIL_SYMBOL not in new:
        sys.exit("ERROR: post-replace sanity check failed. Aborting (no write).")

    bak = TARGET + ".bak_logkeptregions"
    with open(bak, "wb") as f:
        f.write(data)
    with open(TARGET, "wb") as f:
        f.write(new)

    # verify the bytes that actually landed on disk
    with open(TARGET, "rb") as f:
        chk = f.read()
    if ALREADY not in chk or TAIL_SYMBOL not in chk or len(chk) != expected:
        sys.exit(f"ERROR: verification AFTER write FAILED. Restore from {bak}")

    print("OK: kept-region names inserted into the pool resolver log line.")
    print(f"  backup : {bak}")
    print(f"  size   : {size} -> {len(chk)} (+{len(chk) - size} bytes)")
    print("Next: .\\build.ps1 -Apworld  (repackage), then run a fresh gen_sweep -- the")
    print("      log line now reads e.g.  kept 3 middle region(s) ['Altus Plateau', 'Caelid', ...]")


if __name__ == "__main__":
    main()
