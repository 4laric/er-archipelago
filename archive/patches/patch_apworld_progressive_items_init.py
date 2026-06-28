#!/usr/bin/env python3
r"""patch_apworld_progressive_items_init.py

SPEC-options-consolidation.md, Part 3 -- progressive-items merge (__init__ half).
Pairs with patch_apworld_progressive_items_options.py (declares the OptionSet).

Maps the consolidated `progressive_items` OptionSet onto the four legacy boolean options
at the very start of generate_early -- right after the existing `limgrave_caves` alias
normalization, before any region/item/lock logic (or the _progressive_*_active accessors
and slot_data) reads the booleans.

OR-UNION semantics: a boolean is forced on when its key is in the set, but never cleared,
so a legacy yaml that set `progressive_flasks: true` directly is unaffected. Empty set =
no change. Idempotent (re-running re-sets the same values).

ONE insertion into __init__.py:
  after the limgrave alias block (anchor: `        self._inject_reserve_names = frozenset()`)
  -> the progressive_items -> booleans mapping, inserted BEFORE that line.

CRLF/LF agnostic. Backup + post-write verify.

USAGE (Windows, repo root):
    python patch_apworld_progressive_items_options.py
    python patch_apworld_progressive_items_init.py
    .\build.ps1 -Apworld
"""
import os, sys

REPO   = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(REPO, "Archipelago", "worlds", "eldenring", "__init__.py")

# Anchor: the line immediately AFTER the limgrave alias block in generate_early. Insert
# the mapping before it. (Single, newline-free; verified to occur once.)
ANCHOR = b"        self._inject_reserve_names = frozenset()"
# Tail proof: the limgrave normalization just above the anchor -- if we can see it, we read
# through generate_early's head where this belongs.
TAIL_SYMBOL = b'self.options.extra_region_locks.value.add("limgrave_underground")'
ALREADY = b"# progressive_items (OptionSet) -> legacy boolean options"

INSERT_LINES = [
    b"        # progressive_items (OptionSet) -> legacy boolean options. The consolidated",
    b"        # front-end is mapped onto the four booleans here (OR-union: set, never clear),",
    b"        # so all downstream logic + slot_data keep reading the booleans unchanged and a",
    b"        # legacy yaml that set a boolean directly still works. Empty set = no change.",
    b"        _pi = self.options.progressive_items.value",
    b'        if "stone_bells" in _pi:',
    b"            self.options.progressive_stone_bells.value = 1",
    b'        if "glovewort_bells" in _pi:',
    b"            self.options.progressive_glovewort_bells.value = 1",
    b'        if "flasks" in _pi:',
    b"            self.options.progressive_flasks.value = 1",
    b'        if "physick" in _pi:',
    b"            self.options.progressive_physick.value = 1",
]


def _detect_eol(data: bytes) -> bytes:
    crlf = data.count(b"\r\n")
    return b"\r\n" if crlf >= (data.count(b"\n") - crlf) else b"\n"


def main():
    if not os.path.isfile(TARGET):
        sys.exit(f"ERROR: not found: {TARGET}")
    size = os.path.getsize(TARGET)
    with open(TARGET, "rb") as f:
        data = f.read()
    if len(data) != size:
        sys.exit(f"ERROR: short read ({len(data)} != {size}) -- I/O truncation; aborting.")
    if TAIL_SYMBOL not in data:
        sys.exit(f"ERROR: tail symbol {TAIL_SYMBOL!r} missing -- source truncated (mount can "
                 f"truncate this big file; run on Windows). Aborting, no write.")
    if ALREADY in data:
        print("Already patched -- progressive_items mapping present. No change.")
        return
    if data.count(ANCHOR) != 1:
        sys.exit(f"ERROR: anchor {ANCHOR!r} found {data.count(ANCHOR)}x, expected 1. Aborting.")

    eol = _detect_eol(data)
    block = eol.join(INSERT_LINES) + eol
    new = data.replace(ANCHOR, block + ANCHOR, 1)

    expected_len = len(data) + len(block)
    if len(new) != expected_len or new.count(ALREADY) != 1:
        sys.exit("ERROR: post-replace sanity check failed. Aborting (no write).")
    try:
        compile(new.decode("utf-8"), TARGET, "exec")
    except SyntaxError as e:
        sys.exit(f"ERROR: rewritten __init__.py does not compile: {e}. Aborting (no write).")

    bak = TARGET + ".bak_progressiveitems"
    with open(bak, "wb") as f:
        f.write(data)
    with open(TARGET, "wb") as f:
        f.write(new)
    with open(TARGET, "rb") as f:
        chk = f.read()
    if chk != new or ALREADY not in chk:
        sys.exit(f"ERROR: verification AFTER write FAILED. Restore from {bak}")

    eol_name = "CRLF" if eol == b"\r\n" else "LF"
    print("OK: progressive_items -> booleans mapping inserted into generate_early.")
    print(f"  target : {TARGET}")
    print(f"  backup : {bak}")
    print(f"  size   : {size} -> {len(chk)} ({len(chk) - size:+d} bytes); eol {eol_name}")
    print("Next: .\\build.ps1 -Apworld   then gen-test (gen-test/progressive-items-yamls/).")


if __name__ == "__main__":
    main()
