#!/usr/bin/env python3
r"""patch_apworld_exclude_locations_groups.py

SPEC-options-consolidation.md, Part 1 (bug 1.2) -- the FUNCTIONAL half of the
exclude_locations cleanup. Pairs with patch_apworld_options_cleanup.py (the text half).

PROBLEM
  ERExcludeLocations exposes keys `dlc` / `hidden` / `blizzard`, but none of them
  resolve: there is no `dlc` or `blizzard` location group, and the existing group is
  `"Hidden"` (capitalized) which the lowercase key never matched -- so using any of the
  three raised "... is not a valid location name from 'EldenRing'". (Hence the
  `# still errors` note.) The author left a commented-out DLC-group experiment at EOF.

FIX (additive; locations.py)
  At module load, after location_name_groups is fully populated, wire the three keys
  to real location sets, replacing the dead commented experiment at EOF:
    location_name_groups["hidden"]   = the existing "Hidden" group (lowercase alias)
    location_name_groups["dlc"]      = union of every region in region_order_dlc
    location_name_groups["blizzard"] = every non-event location tagged blizzard=True
  The world already registers `location_name_groups = location_name_groups`
  (__init__.py L138), so these become valid excludable group names. Because the option
  DEFAULT is the empty set, existing seeds are completely unaffected -- this only makes
  the three keys work when a user actually lists them.

  Validated logic (synthetic): hidden -> the Hidden set; dlc -> union of DLC regions
  (region_order_dlc is the full DLC region list, incl. catacombs/gaols); blizzard ->
  the blizzard-tagged Consecrated Snowfield checks.

The dead block (the only thing between the anchor and EOF) is REPLACED by the wiring.
CRLF/LF agnostic. Backup + post-write verify + full-file compile.

USAGE (Windows, repo root):
    python patch_apworld_options_cleanup.py
    python patch_apworld_exclude_locations_groups.py
    .\build.ps1 -Apworld
"""
import os, sys

REPO   = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(REPO, "Archipelago", "worlds", "eldenring", "locations.py")

# Anchor: first line of the dead commented experiment at EOF (must occur exactly once).
ANCHOR = b"# temp = location_name_groups['Gravesite Plain'] # might work shrug"
# Tail proof: the last line of the file (the end of the dead block).
TAIL_SYMBOL = b'# location_name_groups["DLC"] = temp'
# Idempotency / verify marker.
MARKER = b"# --- exclude_locations group wiring (ERExcludeLocations keys: dlc / hidden / blizzard) ---"

WIRING_LINES = [
    b"# --- exclude_locations group wiring (ERExcludeLocations keys: dlc / hidden / blizzard) ---",
    b"# Make the three documented exclude_locations keys resolve to real location sets so the",
    b'# option actually works (previously unwired -> "not a valid location name"). Additive;',
    b"# the option default is empty, so existing seeds are unaffected. Supersedes the commented",
    b"# experiment that used to live here. See patch_apworld_exclude_locations_groups.py.",
    b'location_name_groups["hidden"] = set(location_name_groups.get("Hidden", set()))',
    b'location_name_groups["dlc"] = set().union(',
    b"    *(location_name_groups.get(_dlc_region, set()) for _dlc_region in region_order_dlc)",
    b")",
    b'location_name_groups["blizzard"] = set(',
    b"    _ld.name",
    b"    for _bz_table in location_tables.values()",
    b"    for _ld in _bz_table",
    b'    if getattr(_ld, "blizzard", False) and not _ld.is_event',
    b")",
    b"",  # trailing newline at EOF
]


def _detect_eol(data: bytes) -> bytes:
    crlf = data.count(b"\r\n")
    lf_only = data.count(b"\n") - crlf
    return b"\r\n" if crlf >= lf_only else b"\n"


def main():
    if not os.path.isfile(TARGET):
        sys.exit(f"ERROR: not found: {TARGET}")
    size = os.path.getsize(TARGET)
    with open(TARGET, "rb") as f:
        data = f.read()

    if len(data) != size:
        sys.exit(f"ERROR: short read ({len(data)} != {size}) -- I/O truncation; aborting, no write.")
    # Marker check FIRST: this patch REMOVES the dead block that holds TAIL_SYMBOL, so on a
    # re-run the tail is legitimately gone -- the marker is the real already-applied signal.
    if MARKER in data:
        print("Already patched -- exclude_locations groups already wired. No change.")
        return
    if TAIL_SYMBOL not in data:
        sys.exit(f"ERROR: tail symbol {TAIL_SYMBOL!r} missing -- source looks truncated (the mount "
                 f"truncates this big file in some sandboxes; run on Windows). Aborting, no write.")

    n = data.count(ANCHOR)
    if n != 1:
        sys.exit(f"ERROR: anchor {ANCHOR!r} found {n} times, expected 1. Aborting (no write).")
    # the anchor must be the start of the dead block at EOF (only the block follows it)
    idx = data.index(ANCHOR)
    if data.index(TAIL_SYMBOL) < idx:
        sys.exit("ERROR: tail symbol precedes anchor -- unexpected file shape. Aborting (no write).")

    eol = _detect_eol(data)
    head = data[:idx]
    payload = eol.join(WIRING_LINES)  # WIRING_LINES are bytes; joined with the file's EOL
    new = head + payload

    try:
        compile(new.decode("utf-8"), TARGET, "exec")
    except SyntaxError as e:
        sys.exit(f"ERROR: rewritten locations.py does not compile: {e}. Aborting (no write).")

    bak = TARGET + ".bak_excludelocgroups"
    with open(bak, "wb") as f:
        f.write(data)
    with open(TARGET, "wb") as f:
        f.write(new)

    with open(TARGET, "rb") as f:
        chk = f.read()
    if chk != new or MARKER not in chk:
        sys.exit(f"ERROR: verification AFTER write FAILED. Restore from {bak}")
    for key in (b'location_name_groups["hidden"]', b'location_name_groups["dlc"]', b'location_name_groups["blizzard"]'):
        if chk.count(key) != 1:
            sys.exit(f"ERROR: {key!r} appears {chk.count(key)}x after write (want 1). Restore from {bak}")

    eol_name = "CRLF" if eol == b"\r\n" else "LF"
    print("OK: exclude_locations groups wired (dlc / hidden / blizzard).")
    print(f"  target : {TARGET}")
    print(f"  backup : {bak}")
    print(f"  size   : {size} -> {len(chk)} ({len(chk) - size:+d} bytes); eol {eol_name}")
    print("Next: .\\build.ps1 -Apworld   then gen-test with an exclude_locations yaml.")


if __name__ == "__main__":
    main()
