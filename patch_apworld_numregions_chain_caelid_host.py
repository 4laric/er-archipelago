#!/usr/bin/env python3
r"""patch_apworld_numregions_chain_caelid_host.py

FIX for: a num_regions_chain SOFTLOCK where the chain breadcrumb places a region
lock (e.g. Altus Lock) on Radahn's drop in Wailing Dunes.

ROOT CAUSE
----------
The chain breadcrumb places link[i]'s lock on link[i-1]'s "boss host", chosen by
_num_regions_chain_host(step) from region_spine.NUM_REGIONS_CHAIN_STEP_HOST_REGIONS.
For Caelid (step 5) that list is ["Caelid", "Wailing Dunes"] and the selector
PREFERS a remembrance/mainboss drop -> it picks Radahn's Remembrance, which lives
in Wailing Dunes. But Wailing Dunes is gated on _can_go_to("Altus Plateau") (the
Radahn-festival trigger). So if the link after Caelid is Altus, the chain does
place_locked_item(Altus Lock) on Radahn's drop:
    reach Wailing Dunes  needs  reach Altus
    reach Altus          needs  Altus Lock
    Altus Lock           is at  Wailing Dunes   <-- circular, hard softlock.
place_locked_item bypasses the reachability check that would otherwise stop fill
from putting a lock there, so this slips through.

THE FIX
-------
Remove "Wailing Dunes" from Caelid's breadcrumb host list, so a chain lock can
only ever land on a normal Caelid location (reachable on the Caelid lock alone),
never on the Altus-gated Radahn drop. The host selector then falls back to any
non-missable Caelid boss/check; if (impossibly) none exists, pre_fill already
precollects the lock instead of softlocking. Radahn's Great Rune itself stays at
Wailing Dunes as a normal check (made reachable by the warp-aware _can_go_to fix,
patch_apworld_cango_warp_aware.py -- apply that too).

USAGE (Windows, from the er-archipelago repo root):
    python patch_apworld_numregions_chain_caelid_host.py
then gen-test:
    .\build.ps1 -Randomizer -Generate
Idempotent: re-running is a no-op once applied.
"""
import io
import os
import sys
import py_compile

MARKER = 'no-wailing-dunes-host'

ANCHOR = '    5: ["Caelid", "Wailing Dunes"],'

REPLACEMENT = ('    5: ["Caelid"],  # ' + MARKER + ': NOT Wailing Dunes -- Radahn\'s drop is '
               'Altus-gated, a breadcrumb lock there deadlocks (Altus Lock <-> Wailing Dunes).')


def _find_target():
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "Archipelago", "worlds", "eldenring", "region_spine.py"),
        os.path.join(os.getcwd(), "Archipelago", "worlds", "eldenring", "region_spine.py"),
        os.path.join(here, "worlds", "eldenring", "region_spine.py"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    sys.exit("ERROR: could not find Archipelago/worlds/eldenring/region_spine.py "
             "(run this from the er-archipelago repo root).")


def main():
    path = _find_target()

    with io.open(path, "r", encoding="utf-8", newline="") as f:
        raw = f.read()
    nl = "\r\n" if "\r\n" in raw else "\n"
    text = raw.replace("\r\n", "\n")

    if MARKER in text:
        print("[skip] already applied (%s marker present): %s" % (MARKER, path))
        return

    if ANCHOR not in text:
        sys.exit("ERROR: anchor line not found -- source may have changed.\n"
                 "  expected: %r\n"
                 "  Re-read NUM_REGIONS_CHAIN_STEP_HOST_REGIONS and update ANCHOR." % ANCHOR)

    if text.count(ANCHOR) != 1:
        sys.exit("ERROR: anchor is not unique (%d matches); aborting." % text.count(ANCHOR))

    text = text.replace(ANCHOR, REPLACEMENT, 1)

    out = text.replace("\n", nl)
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(out)

    with io.open(path, "r", encoding="utf-8", newline="") as f:
        check = f.read()
    if MARKER not in check:
        sys.exit("ERROR: write did not persist the marker -- check the file on disk.")
    try:
        py_compile.compile(path, doraise=True)
    except py_compile.PyCompileError as e:
        sys.exit("ERROR: region_spine.py failed to compile after patch:\n%s" % e)

    print("[ok] patched + compiles: %s" % path)
    print("     Caelid breadcrumb host can no longer land a chain lock on Radahn's drop.")
    print("     Next: .\\build.ps1 -Randomizer -Generate  (gen-test before baking)")


if __name__ == "__main__":
    main()
