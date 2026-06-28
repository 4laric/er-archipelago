#!/usr/bin/env python3
r"""patch_apworld_cango_warp_aware.py

FIX for: Fill.FillError "Could not access required locations for accessibility
check" with a single missing location like
    CL/(WD): Radahn's Great Rune - mainboss drop
on a num_regions + region_access:warp Capital run.

ROOT CAUSE
----------
_can_go_to(state, region) is implemented as
    state.can_reach_entrance(f"Go To {region}", player)
i.e. it tests the GEOGRAPHIC 'Go To <region>' entrance, not whether the region
is reachable. Wailing Dunes (Radahn, who drops Radahn's Great Rune) is gated on
_can_go_to("Altus Plateau") -- the vanilla Radahn-festival trigger. The
'Go To Altus Plateau' entrance's parent region is Liurnia. Under num_regions a
seed can SEAL Liurnia while KEEPING Caelid, so 'Go To Altus Plateau' is dead
even though Altus is reachable by its own 'Warp To Altus Plateau' lock. Result:
Wailing Dunes is falsely unreachable and Radahn's pinned Great Rune fails the
accessibility check. (Altus stays warp-reachable, so the goal still works and
can_beat_game passes -- hence an accessibility error, not 'unbeatable'.)

THE FIX
-------
Make _can_go_to region-aware under warp: keep the existing geographic-entrance
test, and additionally accept region reachability when region_access == warp.
This matches the method docstring ("can access the given region name") AND the
indirect conditions, which are already registered on the REGION (e.g.
register_indirect_condition(get_region("Altus Plateau"),
get_entrance("Go To Wailing Dunes"))), not on the 'Go To' entrance.

In-game this is sound (NOT a logic-only softlock): the Radahn festival arms on
reaching Altus (touching an Altus grace / the Altus map-region flag), which a
warp into Altus satisfies -- so the routing "find Altus Lock -> warp to Altus ->
festival arms -> return to Caelid -> fight Radahn" actually works.

Non-warp seeds are unchanged (the new branch is gated on region_access==warp).

USAGE (Windows, from the er-archipelago repo root):
    python patch_apworld_cango_warp_aware.py
then gen-test:
    .\build.ps1 -Randomizer -Generate
Idempotent: re-running is a no-op once applied.

NOTE: a SEPARATE, seed-dependent risk remains -- the num_regions_chain breadcrumb
host for Caelid (region_spine.NUM_REGIONS_CHAIN_STEP_HOST_REGIONS[5] =
["Caelid", "Wailing Dunes"]) can place a chain lock on Radahn's Altus-gated drop,
which would deadlock. If a future seed fails on Wailing Dunes/Radahn with Altus
itself unreachable, drop "Wailing Dunes" from that host list too.
"""
import io
import os
import sys
import py_compile

MARKER = "cango-warp-aware"

ANCHOR = "        return state.can_reach_entrance(f\"Go To {region}\", self.player)"

REPLACEMENT_LINES = [
    "        # cango-warp-aware FIX: under region_access=warp a region is reached by its own",
    "        # 'Warp To <region>' lock, so its geographic 'Go To <region>' entrance can be dead when",
    "        # a predecessor region is num_regions-sealed (e.g. Liurnia sealed -> 'Go To Altus Plateau'",
    "        # unreachable -> Wailing Dunes/Radahn falsely unreachable, even though Altus is warp-",
    "        # reachable). Region-reachability matches the docstring + the indirect conditions (which",
    "        # are registered on regions, not the 'Go To' entrance). Sound in-game: the Radahn festival",
    "        # arms on reaching Altus (grace/map flag), which a warp into Altus satisfies.",
    "        if state.can_reach_entrance(f\"Go To {region}\", self.player):",
    "            return True",
    "        if self.options.region_access == \"warp\":",
    "            return state.can_reach_region(region, self.player)",
    "        return False",
]


def _find_target():
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "Archipelago", "worlds", "eldenring", "__init__.py"),
        os.path.join(os.getcwd(), "Archipelago", "worlds", "eldenring", "__init__.py"),
        os.path.join(here, "worlds", "eldenring", "__init__.py"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    sys.exit("ERROR: could not find Archipelago/worlds/eldenring/__init__.py "
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
                 "  Re-read _can_go_to and update ANCHOR." % ANCHOR)

    if text.count(ANCHOR) != 1:
        sys.exit("ERROR: anchor is not unique (%d matches); aborting." % text.count(ANCHOR))

    new_block = "\n".join(REPLACEMENT_LINES)
    text = text.replace(ANCHOR, new_block, 1)

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
        sys.exit("ERROR: __init__.py failed to compile after patch:\n%s" % e)

    print("[ok] patched + compiles: %s" % path)
    print("     _can_go_to is now warp-aware (region-reach under region_access=warp).")
    print("     Next: .\\build.ps1 -Randomizer -Generate  (gen-test before baking)")


if __name__ == "__main__":
    main()
