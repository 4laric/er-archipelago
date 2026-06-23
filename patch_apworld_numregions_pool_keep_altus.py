#!/usr/bin/env python3
r"""patch_apworld_numregions_pool_keep_altus.py

FIX for: Fill.FillError "Game appears as unbeatable. Aborting." on a
num_regions Capital run with `num_regions_rune_source: pool`.

ROOT CAUSE
----------
The error is raised by Main.py can_beat_game() -- the goal (Morgott, the
Leyndell mainboss drop) is unreachable even with EVERY item collected. It is a
LOGIC contradiction, not a fill/pool-size shortage.

The goal capstone regions (Capital Outskirts, Leyndell) are always KEPT but have
NO warp lock. Under region_access=warp you can only warp to a region via its
lock, so the capstone is reachable ONLY through the geographic edge
    Liurnia -> Altus -> Capital Outskirts -> Leyndell.
The default `regions` rune-source force-keeps Altus ("the only physical route to
Leyndell") and raises num_regions to its floor for exactly this reason. The
`pool` path (compute_num_regions_scope_pool) DROPS the Altus force-keep on the
premise that "warp ignores adjacency" -- but that premise is false for the
LOCKLESS capstone. If a seed's random roll seals Altus, Leyndell/Morgott is
stranded -> unbeatable.

THE FIX
-------
In compute_num_regions_scope_pool, treat Altus (ALTUS_STEP) as mandatory
capstone-route overhead: add one slot for it (mirrors the regions-mode force-
keep, so we don't displace a rolled content region) and pin it into the roll.
This raises a num_regions:4 roll to 5 kept middles with Altus guaranteed -- the
same shape the `regions` path already produces.

Great runes still ride the pool via the existing __init__.py deficit injector
(unchanged): the kept rune-boss regions and/or injected runes supply Leyndell's
great_runes_required count; this patch only restores the physical route in.

USAGE (Windows, from the er-archipelago repo root):
    python patch_apworld_numregions_pool_keep_altus.py
then gen-test:
    .\build.ps1 -Randomizer -Generate
Idempotent: re-running is a no-op once applied.
"""
import io
import os
import sys
import py_compile

MARKER = "numregions-pool-keep-altus"

ANCHOR = "    picked = list(rng.sample(list(NUM_REGIONS_POOL_STEPS), effective))"

REPLACEMENT_LINES = [
    "    # numregions-pool-keep-altus FIX: Altus is mandatory capstone-route overhead. The lockless",
    "    # Leyndell capstone (Capital Outskirts -> Leyndell) has NO warp lock and is reachable ONLY",
    "    # via the Altus geographic edge, so a sealed Altus strands the goal -> can_beat_game",
    "    # 'unbeatable'. Add one slot for Altus (mirrors the regions-mode force-keep) rather than",
    "    # displacing a rolled content region, then pin Altus into the roll.",
    "    if ALTUS_STEP in NUM_REGIONS_POOL_STEPS:",
    "        effective = min(effective + 1, max_total)",
    "        _rest_pool = [s for s in NUM_REGIONS_POOL_STEPS if s != ALTUS_STEP]",
    "        picked = [ALTUS_STEP] + list(rng.sample(_rest_pool, max(0, effective - 1)))",
    "    else:",
    "        picked = list(rng.sample(list(NUM_REGIONS_POOL_STEPS), effective))",
]


def _find_target():
    """Locate region_spine.py relative to this script / cwd."""
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

    # Read preserving original newline style (apworld files are typically CRLF).
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
                 "  Re-read compute_num_regions_scope_pool and update ANCHOR." % ANCHOR)

    if text.count(ANCHOR) != 1:
        sys.exit("ERROR: anchor is not unique (%d matches); aborting to avoid a "
                 "wrong edit." % text.count(ANCHOR))

    new_block = "\n".join(REPLACEMENT_LINES)
    text = text.replace(ANCHOR, new_block, 1)

    # Restore original newline style and write back.
    out = text.replace("\n", nl)
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(out)

    # Verify on disk: marker present + file still compiles (catches truncation).
    with io.open(path, "r", encoding="utf-8", newline="") as f:
        check = f.read()
    if MARKER not in check:
        sys.exit("ERROR: write did not persist the marker -- check the file on disk.")
    try:
        py_compile.compile(path, doraise=True)
    except py_compile.PyCompileError as e:
        sys.exit("ERROR: region_spine.py failed to compile after patch:\n%s" % e)

    print("[ok] patched + compiles: %s" % path)
    print("     Altus is now force-kept in num_regions_rune_source=pool runs.")
    print("     Next: .\\build.ps1 -Randomizer -Generate  (gen-test before baking)")


if __name__ == "__main__":
    main()
