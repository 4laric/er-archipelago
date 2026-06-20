#!/usr/bin/env python3
"""
patch_apworld_debate_parlor_boss_exclude.py -- exclude the Debate Parlor grace (Red Wolf of Radagon
arena) from the region-lock grace bundle so warping in doesn't drop the player behind the boss fog.

WHY: Debate Parlor's warp-unlock flag is 71401 (grace_flags.tsv rowId 140001; the Red Wolf of Radagon
Memory Stone drop flag 60440 maps to nearest-grace placeName 140001 = Debate Parlor). Warping onto it
lands the player behind the fog in the Red Wolf arena -- the boss never aggros (skip/soft-lock). It's
the Raya Lucaria equivalent of the existing _BOSS_GRACE_FLAGS exclusions (Astel, Radahn, Nox Duo, ...).

GOTCHA: the Raya Lucaria Academy graces are injected via the natural-key apparatus list
_NK2_GRACES["Raya Lucaria Lock"] = [71400, 71401, 71402, 71403] (__init__.py ~L4662), which -- unlike
the geographic REGION_GRACE_POINTS bundling -- is NOT filtered through _SKIP_GRACE_FLAGS. So adding
71401 to _BOSS_GRACE_FLAGS alone would NOT drop it. This patch does BOTH:
  1. Add 71401 to _BOSS_GRACE_FLAGS  (authoritative intent + covers the geographic path).
  2. Remove 71401 from _NK2_GRACES["Raya Lucaria Lock"]  (the path that actually grants it).

Player still reaches Debate Parlor on foot from Church of the Cuckoo after killing Red Wolf; it just
no longer gets a fast-travel warp-unlock on Raya Lucaria Lock receipt.

Target: Archipelago/worlds/eldenring/__init__.py (CRLF). Byte-level replace to preserve CRLF (the Edit
tool truncates CRLF source). Idempotent; verifies on disk. Run on Windows, then re-gen + re-bake.
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "__init__.py")

EDITS = [
    (
        "add 71401 to _BOSS_GRACE_FLAGS",
        "            _BOSS_GRACE_FLAGS = frozenset({71240, 76415, 76422, 76508, 76509, 76852, 76853, 76930, 76931})  # 76415=Nox Duo arena (Sellia, Town of Sorcery; 'chair crypt')",
        "            _BOSS_GRACE_FLAGS = frozenset({71240, 71401, 76415, 76422, 76508, 76509, 76852, 76853, 76930, 76931})  # 76415=Nox Duo arena (Sellia, Town of Sorcery; 'chair crypt'); 71401=Debate Parlor (Red Wolf of Radagon arena)",
    ),
    (
        "drop 71401 from Raya Lucaria natural-key grace list",
        '                "Raya Lucaria Lock": [71400, 71401, 71402, 71403],',
        '                "Raya Lucaria Lock": [71400, 71402, 71403],  # 71401 Debate Parlor EXCLUDED: Red Wolf of Radagon arena (warp drops you behind the fog)',
    ),
]

SENTINEL = b"71401=Debate Parlor (Red Wolf of Radagon arena)"


def main():
    if not os.path.isfile(TARGET):
        sys.exit("ERROR: not found: %s" % TARGET)

    with open(TARGET, "rb") as f:
        data = f.read()

    if SENTINEL in data:
        print("Already patched (Debate Parlor boss-exclude); nothing to do.")
        return

    for desc, old, new in EDITS:
        old_b = old.encode("utf-8")
        new_b = new.encode("utf-8")
        n = data.count(old_b)
        if n != 1:
            sys.exit("ERROR: anchor for '%s' found %d times (expected 1). Aborting; no write." % (desc, n))
        before = len(data)
        data = data.replace(old_b, new_b, 1)
        if len(data) != before - len(old_b) + len(new_b):
            sys.exit("ERROR: unexpected length after '%s'. Aborting; no write." % desc)
        print("  [ok] %s" % desc)

    with open(TARGET, "wb") as f:
        f.write(data)

    # Verify on disk.
    with open(TARGET, "rb") as f:
        chk = f.read()
    assert SENTINEL in chk, "VERIFY FAILED: sentinel missing"
    assert b'"Raya Lucaria Lock": [71400, 71402, 71403]' in chk, "VERIFY FAILED: Raya list not updated"
    assert b"{71240, 71401, 76415" in chk, "VERIFY FAILED: _BOSS_GRACE_FLAGS not updated"
    print("Patched + verified on disk: %s" % TARGET)
    print("Next: re-gen + re-bake (apworld logic change). No client build needed.")


if __name__ == "__main__":
    main()
