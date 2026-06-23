#!/usr/bin/env python3
r"""patch_apworld_dlc_only_rune_catchup_options.py

Add the `dlc_only_rune_catchup` Toggle option (default OFF) to options.py, wired
exactly like the sibling dlc_only Toggle `quick_start`:
  1. a new `DLCOnlyRuneCatchup(Toggle)` class (inserted right before `EnableDLC`),
  2. its membership in the `EROptions` dataclass (after `quick_start: QuickStart`),
  3. its entry in the "DLC" option_group (after `QuickStart,`),
so it resolves and shows in gendiag resolved options like every other option.

WHAT THE FEATURE DOES (the behaviour lives in the __init__.py patch; this only
declares the knob): when ON *and* dlc_only is ON, every rune-CURRENCY filler item
in the item pool (Golden Rune [1..13], Numen's Rune, Hero's Rune [1..5], Lord's
Rune, plus the DLC rune drops -- anything with a `runes=` value in items.py) is
swapped IN PLACE for a Lord's Rune (50,000 runes, goods 2919), to help a DLC-only
start catch up to the DLC's enemy scaling. Count-neutral. Great Runes (no `runes=`
kwarg -> excluded) and Rune Arc (a buff, no `runes=` -> excluded) are untouched.

THREE INSERTIONS (each anchor VERIFIED to occur exactly once on the live Windows
disk; all anchors are newline-free so this is CRLF/LF agnostic -- source is CRLF on
Windows, some mounts serve LF):

  (A) before  `class EnableDLC(Toggle):`            -> the new option class
  (B) after   `    quick_start: QuickStart`          -> the dataclass member
  (C) after   `        QuickStart,`                   -> the option_group entry

USAGE (Windows, from the repo root):
    python patch_apworld_dlc_only_rune_catchup_options.py
    python patch_apworld_dlc_only_rune_catchup_init.py
    .\build.ps1 -Apworld
"""
import os, sys

REPO   = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(REPO, "Archipelago", "worlds", "eldenring", "options.py")

# EOF anchor: prove we read the whole file (near the end of option_groups, L1118).
TAIL_SYMBOL = b"ImpoliteEnemies,"

# Idempotency / verify marker: the distinctive new class name.
ALREADY = b"class DLCOnlyRuneCatchup(Toggle):"

# ---- (A) the new option class, inserted before EnableDLC -------------------
ANCHOR_A = b"class EnableDLC(Toggle):"
# Body (no line endings here; _emit inserts the file's own EOL between lines).
CLASS_LINES = [
    b"class DLCOnlyRuneCatchup(Toggle):",
    b'    """Rune Catch-up (dlc_only): turn every rune-currency drop in the pool into a',
    b"    Lord's Rune (50,000 runes each) so a DLC-only start can rocket up to the DLC's",
    b"    enemy scaling. A DLC-only run skips the base game's whole rune-earning curve;",
    b"    this makes the rune drops you DO find pay out at the maximum rate. Every Golden",
    b"    Rune / Hero's Rune / Numen's Rune / smaller rune (base and DLC) becomes a Lord's",
    b"    Rune in place -- same number of items, just each worth 50,000. Great Runes and",
    b"    Rune Arcs are NOT runes-currency and are left untouched. Only takes effect when",
    b'    dlc_only is on (inert otherwise)."""',
    b'    display_name = "Rune Catch-up (Lord\'s Runes, dlc_only)"',
    b"",
]

# ---- (B) the dataclass member, after quick_start: QuickStart ---------------
ANCHOR_B = b"    quick_start: QuickStart"
MEMBER_LINE = b"    dlc_only_rune_catchup: DLCOnlyRuneCatchup"

# ---- (C) the option_group entry, after QuickStart, ------------------------
ANCHOR_C = b"        QuickStart,"
GROUP_LINE = b"        DLCOnlyRuneCatchup,"


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

    # read-truncation guard (a short / stale mount read must NOT be written back)
    if len(data) != size:
        sys.exit(f"ERROR: short read ({len(data)} != {size} bytes) -- I/O truncation; aborting, no write.")
    if TAIL_SYMBOL not in data:
        sys.exit(f"ERROR: tail symbol {TAIL_SYMBOL!r} missing -- source looks truncated; aborting, no write.")

    if ALREADY in data:
        print("Already patched -- dlc_only_rune_catchup option already declared. No change.")
        return

    for label, anc in (("A class", ANCHOR_A), ("B member", ANCHOR_B), ("C group", ANCHOR_C)):
        n = data.count(anc)
        if n != 1:
            sys.exit(f"ERROR: anchor {label} ({anc!r}) found {n} times, expected 1. Aborting (no write).")

    eol = _detect_eol(data)

    # (A) class block: emitted lines joined by EOL, then a trailing EOL before the anchor.
    class_block = eol.join(CLASS_LINES) + eol
    new = data.replace(ANCHOR_A, class_block + ANCHOR_A, 1)
    # (B) dataclass member: anchor line stays, append a new line after it.
    new = new.replace(ANCHOR_B, ANCHOR_B + eol + MEMBER_LINE, 1)
    # (C) option_group entry: anchor line stays, append a new line after it.
    new = new.replace(ANCHOR_C, ANCHOR_C + eol + GROUP_LINE, 1)

    expected = (len(data)
                + len(class_block)
                + len(eol) + len(MEMBER_LINE)
                + len(eol) + len(GROUP_LINE))
    if (len(new) != expected
            or ALREADY not in new
            or TAIL_SYMBOL not in new
            or new.count(ALREADY) != 1
            or new.count(MEMBER_LINE) != 1
            or new.count(GROUP_LINE) != 1):
        sys.exit("ERROR: post-replace sanity check failed. Aborting (no write).")

    bak = TARGET + ".bak_dlconlyrunecatchup"
    with open(bak, "wb") as f:
        f.write(data)
    with open(TARGET, "wb") as f:
        f.write(new)

    # verify the bytes that actually landed on disk
    with open(TARGET, "rb") as f:
        chk = f.read()
    if (ALREADY not in chk or TAIL_SYMBOL not in chk or len(chk) != expected
            or chk.count(MEMBER_LINE) != 1 or chk.count(GROUP_LINE) != 1):
        sys.exit(f"ERROR: verification AFTER write FAILED. Restore from {bak}")

    print("OK: dlc_only_rune_catchup Toggle declared, added to EROptions + DLC option_group.")
    print(f"  target : {TARGET}")
    print(f"  backup : {bak}")
    print(f"  size   : {size} -> {len(chk)} (+{len(chk) - size} bytes)")
    _eol_name = "CRLF" if eol == b"\r\n" else "LF"
    print(f"  eol    : {_eol_name}")
    print("Next: python patch_apworld_dlc_only_rune_catchup_init.py  then  .\\build.ps1 -Apworld")


if __name__ == "__main__":
    main()
