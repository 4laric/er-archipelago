#!/usr/bin/env python3
r"""patch_apworld_options_cleanup.py

SPEC-options-consolidation.md, Part 1 -- options.py text cleanups (no behaviour change).
Pairs with patch_apworld_exclude_locations_groups.py (the functional half).

Five single-line, exactly-once text edits in
  Archipelago/worlds/eldenring/options.py :

  1. ExtraRegionLocks docstring: mark `limgrave_caves` as an ALIAS of
     `limgrave_underground` (it is auto-normalized to that key in __init__.py /
     region_spine.py -- it is NOT a duplicate bug, and the Alaric yaml relies on it,
     so it must stay; only the misleading docstring is fixed).
  2. + 3. Strip the leftover dev-uncertainty comments from MessmerKindle /
     MessmerKindleRequired.
  4. ERExcludeLocations `default = frozenset({}) # still errors` -> `frozenset()` with
     an accurate note (the keys are wired by the companion patch).
  5. Replace the stale captured-Exception comment with a pointer to the wiring.

Nothing structural changes -- no option class, dataclass, default value or logic is
altered (frozenset({}) and frozenset() are both the empty set), so generation is
identical. CRLF/LF agnostic. Backup + post-write verify + full-file compile.

USAGE (Windows, repo root):
    python patch_apworld_options_cleanup.py
    python patch_apworld_exclude_locations_groups.py
    .\build.ps1 -Apworld
"""
import os, sys

REPO   = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(REPO, "Archipelago", "worlds", "eldenring", "options.py")

TAIL_SYMBOL = b"ImpoliteEnemies,"   # prove a full read (near EOF)

# (old, new) -- each `old` must occur exactly once; each is newline-free (single line).
EDITS = [
    (b"      limgrave_caves -- gate Limgrave's 10 underground regions (Fringefolk Hero's Grave, Coastal",
     b"      limgrave_caves -- ALIAS of limgrave_underground (auto-normalized in code); the same 10 underground regions (Fringefolk Hero's Grave, Coastal"),

    (b"class MessmerKindle(Toggle): # another toggle to make them only spawn in dlc?",
     b"class MessmerKindle(Toggle):"),

    (b"class MessmerKindleRequired(Range): # i just picked these numbers idk how many would be good",
     b"class MessmerKindleRequired(Range):"),

    (b"    default = frozenset({}) # still errors",
     b"    default = frozenset()  # keys (dlc/hidden/blizzard) wired to location groups in locations.py"),

    (b"    # Exception: Location 'hidden' from option 'ERExcludeLocations(hidden)' is not a valid location name from 'EldenRing'. Did you mean 'RH: Mace - Twin maiden shop' (18% sure)",
     b"    # dlc / hidden / blizzard resolve via location_name_groups (see patch_apworld_exclude_locations_groups.py)."),
]


def main():
    if not os.path.isfile(TARGET):
        sys.exit(f"ERROR: not found: {TARGET}")
    size = os.path.getsize(TARGET)
    with open(TARGET, "rb") as f:
        data = f.read()

    if len(data) != size:
        sys.exit(f"ERROR: short read ({len(data)} != {size}) -- I/O truncation; aborting, no write.")
    if TAIL_SYMBOL not in data:
        sys.exit(f"ERROR: tail symbol {TAIL_SYMBOL!r} missing -- source looks truncated; aborting.")

    new = data
    applied, skipped = 0, 0
    for i, (old, repl) in enumerate(EDITS, 1):
        if old in new:
            if new.count(old) != 1:
                sys.exit(f"ERROR: edit {i} anchor found {new.count(old)}x, expected 1. Aborting (no write).")
            new = new.replace(old, repl, 1)
            applied += 1
        elif repl in new:
            skipped += 1  # already applied
        else:
            sys.exit(f"ERROR: edit {i} -- neither old anchor nor new text present. "
                     f"Anchor drift? Aborting (no write).\n  anchor: {old[:60]!r}...")

    if applied == 0:
        print(f"Already cleaned -- all {skipped} edits already present. No change.")
        return

    try:
        compile(new.decode("utf-8"), TARGET, "exec")
    except SyntaxError as e:
        sys.exit(f"ERROR: rewritten options.py does not compile: {e}. Aborting (no write).")

    bak = TARGET + ".bak_optionscleanup"
    with open(bak, "wb") as f:
        f.write(data)
    with open(TARGET, "wb") as f:
        f.write(new)

    with open(TARGET, "rb") as f:
        chk = f.read()
    if chk != new or TAIL_SYMBOL not in chk:
        sys.exit(f"ERROR: verification AFTER write FAILED. Restore from {bak}")
    for _, repl in EDITS:
        if repl not in chk:
            sys.exit(f"ERROR: expected text missing after write: {repl[:50]!r}. Restore from {bak}")

    print(f"OK: options.py cleaned ({applied} applied, {skipped} already present).")
    print(f"  target : {TARGET}")
    print(f"  backup : {bak}")
    print(f"  size   : {size} -> {len(chk)} ({len(chk) - size:+d} bytes)")
    print("Next: python patch_apworld_exclude_locations_groups.py  then  .\\build.ps1 -Apworld")


if __name__ == "__main__":
    main()
