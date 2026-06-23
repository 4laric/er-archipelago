#!/usr/bin/env python3
r"""patch_apworld_dlc_only_pull_base_locks.py

Pull BASE-game region locks from the item pool under dlc_only, so they stop being
placed as findable progression items in a DLC-only seed.

ROOT CAUSE (Archipelago/worlds/eldenring/__init__.py, set_rules / region-lock block ~L703-709)
-----------------------------------------------------------------------------------------------
The dlc_only region-lock block frees ONLY Gravesite Lock and -- per its own comment --
"leave[s] every other region lock in the pool, gated by region_lock". The loop is:

    if self.options.dlc_only:
        for item in item_table:
            if not item_table[item].lock:
                continue
            if _DLC_ONLY_FREE_ALL_LOCKS or item == "Gravesite Lock":
                item_table[item].inject = False
                self.multiworld.push_precollected(self.create_item(item))

It never distinguishes DLC locks from BASE-game locks. Every BASE lock
(Liurnia / Caelid / Altus / Stormveil / Haligtree / Farum Azula / ...) therefore stays
inject=True and gets PLACED as a findable progression item -- even though in dlc_only
those base regions are SEALED transit (their checks become locked-vanilla events; see
create_regions ~L1292-1296). A user found a placed "Liurnia Lock" in-game on a dlc_only
seed. Those placements are dead garbage that eat fill slots.

BASE vs DLC is already cleanly separable in the data (items.py):
  * Base locks (Limgrave/Liurnia/Caelid/Altus/Stormveil/...) live in _vanilla_items
    -> is_dlc = False  (Liurnia Lock items.py:2159; Snowfield Lock appended as base 2857).
  * DLC locks (Gravesite/Belurat/Scadu Altus/Shadow Keep/Enir Ilim/...) live in
    _dlc_items (items.py:2829+) -> is_dlc = True (set by the loop items.py:2851-2852).
The same getattr(d, "is_dlc", False) handle is already used to build _dlc_locks
(__init__.py:446) and to size the dlc_only demand-drop (__init__.py:737, 1422).

THE FIX (minimal, count-neutral, mirrors the Limgrave pool fix)
--------------------------------------------------------------
Add an elif branch: a lock that is NOT Gravesite and is NOT a DLC lock
(is_dlc == False) gets inject=False -- REMOVED from the pool, NOT precollected. DLC
locks (is_dlc=True) stay in the pool exactly as today. inject=False removes the item
from create_items; the dlc_only create_items demand-drop (sized to DLC injectables only,
__init__.py:1418-1424) already treats base locks as "free transit" that "may spill to
the start inventory harmlessly", so removing them is strictly count-neutral -- one fewer
injectable means one fewer filler is sacrificed, that filler simply stays in the pool.

WHY THIS CANNOT STRAND ANYTHING / BREAK BEATABILITY (verified)
-------------------------------------------------------------
  1. Sealed-region enforcement is FLAG-based, not pool-based. areaLockFlags /
     regionGraces / regionOpenFlags are built from REGION_LOCK_ITEM/_rli and the static
     item_table .lock field (__init__.py:4754-4795), independent of .inject. A removed
     base lock leaves its region sealed (KICK active, lock simply unobtainable) -- the
     correct state for a sealed region, identical to a sealed Limgrave.
  2. The warp loop (_region_lock_warp_access, __init__.py:2563-2569) gates a warp on
     state.has(lock); a removed base lock just never grants a warp -- and a sealed base
     region in dlc_only has no checks, so no warp into it is wanted.
  3. The (1,2) demand-reserve block (__init__.py:734-738) reserves slots only for
     is_dlc DLC locks, so it cannot re-seat a base lock.
  4. No DLC region gates on a base region lock: the DLC's base prerequisites are
     precollected as great runes / Crafting Kit / Dragon Hearts (__init__.py:717-727),
     not via base region locks. Removing base locks cannot make the DLC graph
     unbeatable.

CHANGE
------
Anchor on the unique 24-space-indented precollect line (the inner-most line of this
block; the L1661 twin is at 16-space indent, so the 24-space form is unique). Append an
elif branch immediately after it. The file's own line ending is detected from the bytes
(CRLF on Windows; some mounts serve LF), so the inserted lines match it exactly -- the
anchor itself contains no newline and is line-ending agnostic.

    ... if _DLC_ONLY_FREE_ALL_LOCKS or item == "Gravesite Lock":
            item_table[item].inject = False
            self.multiworld.push_precollected(self.create_item(item))
+   elif not getattr(item_table[item], "is_dlc", False):
+       # dlc_only: pull BASE-game region locks from the pool (sealed transit, no
+       # findable lock); DLC locks stay injected. Count-neutral (see L1418 comment).
+       item_table[item].inject = False

USAGE (Windows, from the repo root):
    python patch_apworld_dlc_only_pull_base_locks.py
    .\build.ps1 -Apworld        # repackage the apworld so it carries the change
"""
import os, sys

REPO   = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(REPO, "Archipelago", "worlds", "eldenring", "__init__.py")

# 24-space-indented precollect line -- unique to the dlc_only Gravesite free block
# (the other push_precollected(self.create_item(item)) at ~L1661 is 16-space). No
# newline in the anchor => CRLF/LF agnostic.
ANCHOR  = b'                        self.multiworld.push_precollected(self.create_item(item))'
# Idempotency / verify marker: the distinctive body of the new elif branch.
ALREADY = b'elif not getattr(item_table[item], "is_dlc", False):'
TAIL_SYMBOL = b"interpret_slot_data"   # EOF anchor: prove we read the whole file


def _detect_eol(data: bytes) -> bytes:
    # Use the file's dominant line ending so the inserted lines match the source.
    return b"\r\n" if data.count(b"\r\n") >= data.count(b"\n") - data.count(b"\r\n") else b"\n"


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
        print("Already patched -- base region locks already pulled from the dlc_only pool. No change.")
        return

    n = data.count(ANCHOR)
    if n != 1:
        sys.exit(f"ERROR: expected exactly 1 anchor occurrence, found {n}. Aborting (no write). "
                 f"(Anchor = the 24-space-indented dlc_only `push_precollected(self.create_item(item))`.)")

    eol = _detect_eol(data)
    # The elif sits at the same 20-space indent as the original `if`; its body at 24.
    addition = (
        eol
        + b'                    elif not getattr(item_table[item], "is_dlc", False):'
        + eol
        + b'                        # dlc_only: pull BASE-game region locks from the pool (sealed'
        + eol
        + b'                        # transit, no findable lock); DLC locks (is_dlc) stay injected.'
        + eol
        + b'                        # Count-neutral -- see the L1418 demand-drop comment.'
        + eol
        + b'                        item_table[item].inject = False'
    )
    new = data.replace(ANCHOR, ANCHOR + addition, 1)
    expected = len(data) + len(addition)
    if (len(new) != expected or ALREADY not in new or TAIL_SYMBOL not in new
            or new.count(ANCHOR) != 1 or new.count(ALREADY) != 1):
        sys.exit("ERROR: post-replace sanity check failed. Aborting (no write).")

    bak = TARGET + ".bak_dlconlypullbaselocks"
    with open(bak, "wb") as f:
        f.write(data)
    with open(TARGET, "wb") as f:
        f.write(new)

    # verify the bytes that actually landed on disk
    with open(TARGET, "rb") as f:
        chk = f.read()
    if ALREADY not in chk or TAIL_SYMBOL not in chk or len(chk) != expected or chk.count(ALREADY) != 1:
        sys.exit(f"ERROR: verification AFTER write FAILED. Restore from {bak}")

    print("OK: base-game region locks are now pulled from the pool under dlc_only.")
    print(f"  target : {TARGET}")
    print(f"  backup : {bak}")
    print(f"  size   : {size} -> {len(chk)} (+{len(chk) - size} bytes)")
    _eol_name = "CRLF" if eol == b"\r\n" else "LF"
    print(f"  eol    : {_eol_name}")
    print("Next: .\\build.ps1 -Apworld  (repackage), then gen a dlc_only seed and confirm")
    print("      NO base '* Lock' items remain in the pool (DLC locks still present).")


if __name__ == "__main__":
    main()
