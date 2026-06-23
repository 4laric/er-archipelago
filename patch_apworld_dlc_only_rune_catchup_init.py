#!/usr/bin/env python3
r"""patch_apworld_dlc_only_rune_catchup_init.py

Implement the `dlc_only_rune_catchup` behaviour in create_items: when dlc_only AND
dlc_only_rune_catchup are both ON, swap every rune-CURRENCY filler item in the pool
IN PLACE for a Lord's Rune (goods 2919, 50,000 runes) so a DLC-only start can catch
up to the DLC's enemy scaling.

WHY THIS POINT / HOW IT MIRRORS filler_replacement
--------------------------------------------------
The existing `filler_replacement` block (__init__.py ~L1538-1557) is the established
mechanism for an in-place, COUNT-NEUTRAL pool rewrite: it runs AFTER _fill_local_items()
(so locally placed named items are already pulled), walks `self.local_itempool`, and
rebuilds chosen entries with `self.create_item(...)` while forcing the new item's
.classification back to ItemClassification.filler (because filler == 0 is falsy and the
ERItem ctor would otherwise re-promote stones/high runes to useful). We insert OUR pass
immediately AFTER that block and BEFORE `self.multiworld.itempool += self.local_itempool`
(anchor: the unique 8-space `# Add items to itempool`). Running last means we also
catch any Golden Runes that filler_replacement itself just produced, so the result is
"every rune drop is a Lord's Rune" regardless of the other option.

WHICH ITEMS QUALIFY (rune-currency, NOT Great Runes / Rune Arc)
---------------------------------------------------------------
items.py gives every rune-currency consumable a `runes=<int>` value on its ERItemData
(class field `runes: Optional[int] = None`, items.py:40):
  Golden Rune [1..13] (2900-2912), Numen's Rune (2913), Hero's Rune [1..5] (2914-2918),
  Lord's Rune (2919), and the DLC rune drops (Leda's/Broken/Shadow Realm [1..7]/Rune of
  an Unsung Hero/Marika's Rune, 2002950+). All carry `runes=`.
The Great Runes (Godrick's..Malenia's 8148-8153, Great Rune of the Unborn 10080,
Miquella's 2008000) and Rune Arc (190) have NO `runes=` kwarg -> runes is None ->
EXCLUDED. So the predicate `getattr(item_table[name], "runes", None) is not None`
selects exactly the rune currency and nothing progression. We additionally require the
pool entry to be NON-progression / non-useful / non-trap (it's a filler drop), mirroring
filler_replacement, so an item that some other option promoted to progression is spared.
A Lord's Rune already in the pool maps to a Lord's Rune (no-op, harmless).

COUNT-NEUTRAL: each qualifying entry is replaced 1:1; pool size and filler class are
unchanged, so AP fill / progression balancing are unaffected.

DEFENSIVE: reads the option via getattr(..., None) and no-ops if the option class isn't
present, so this patch is safe even if the options.py patch hasn't been applied yet.

CHANGE (anchor VERIFIED unique on the live Windows disk; newline-free => CRLF/LF safe;
source is CRLF on Windows, some mounts serve LF):
    insert a new block BEFORE  `        # Add items to itempool`

USAGE (Windows, from the repo root):
    python patch_apworld_dlc_only_rune_catchup_options.py
    python patch_apworld_dlc_only_rune_catchup_init.py
    .\build.ps1 -Apworld
"""
import os, sys

REPO   = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(REPO, "Archipelago", "worlds", "eldenring", "__init__.py")

TAIL_SYMBOL = b"interpret_slot_data"   # EOF anchor: prove we read the whole file

# Unique 8-space-indented anchor that closes create_items' pool-build (verified count==1).
ANCHOR  = b"        # Add items to itempool"
# Idempotency / verify marker: the distinctive comment of the new block.
ALREADY = b"# dlc_only_rune_catchup:"


def _detect_eol(data: bytes) -> bytes:
    crlf = data.count(b"\r\n")
    lf_only = data.count(b"\n") - crlf
    return b"\r\n" if crlf >= lf_only else b"\n"


def _block(eol: bytes) -> bytes:
    # 8-space-indented block body, matching the surrounding create_items method.
    lines = [
        b"        # dlc_only_rune_catchup: under dlc_only, turn every rune-currency filler",
        b"        # drop into a Lord's Rune (goods 2919, 50,000 runes) so a DLC-only start",
        b"        # catches up to DLC scaling. In-place + count-neutral, mirroring the",
        b"        # filler_replacement pass above; runs LAST so it also upgrades any Golden",
        b"        # Runes that pass produced. Rune-currency == an item_table entry with a",
        b"        # `runes` value (Golden/Hero's/Numen's/Lord's + DLC runes); Great Runes and",
        b"        # Rune Arc have no `runes` value and are left untouched.",
        b'        if self.options.dlc_only and getattr(self.options, "dlc_only_rune_catchup", None) \\',
        b'                is not None and self.options.dlc_only_rune_catchup.value != 0:',
        b'            for _idx in range(len(self.local_itempool)):',
        b'                _it = self.local_itempool[_idx]',
        b'                _data = item_table.get(_it.name)',
        b'                if _data is None or getattr(_data, "runes", None) is None:',
        b'                    continue  # not a rune-currency item (Great Runes/Rune Arc excluded)',
        b'                _c = _it.classification',
        b'                if (_c & ItemClassification.progression',
        b'                        or _c & ItemClassification.useful',
        b'                        or _c & ItemClassification.trap):',
        b'                    continue  # spare anything promoted to progression/useful/trap',
        b'                if _it.name == "Lord\'s Rune":',
        b'                    continue  # already the catch-up item',
        b'                _new = self.create_item("Lord\'s Rune")',
        b'                _new.classification = ItemClassification.filler',
        b'                self.local_itempool[_idx] = _new',
        b"",
    ]
    return eol.join(lines) + eol


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
        print("Already patched -- dlc_only_rune_catchup swap already present in create_items. No change.")
        return

    n = data.count(ANCHOR)
    if n != 1:
        sys.exit(f"ERROR: expected exactly 1 anchor occurrence, found {n}. Aborting (no write). "
                 f"(Anchor = the 8-space-indented `# Add items to itempool`.)")

    eol = _detect_eol(data)
    block = _block(eol)
    new = data.replace(ANCHOR, block + ANCHOR, 1)
    expected = len(data) + len(block)
    if (len(new) != expected
            or ALREADY not in new
            or TAIL_SYMBOL not in new
            or new.count(ANCHOR) != 1
            or new.count(ALREADY) != 1):
        sys.exit("ERROR: post-replace sanity check failed. Aborting (no write).")

    bak = TARGET + ".bak_dlconlyrunecatchup"
    with open(bak, "wb") as f:
        f.write(data)
    with open(TARGET, "wb") as f:
        f.write(new)

    # verify the bytes that actually landed on disk
    with open(TARGET, "rb") as f:
        chk = f.read()
    if ALREADY not in chk or TAIL_SYMBOL not in chk or len(chk) != expected or chk.count(ALREADY) != 1:
        sys.exit(f"ERROR: verification AFTER write FAILED. Restore from {bak}")

    print("OK: dlc_only_rune_catchup swap inserted into create_items.")
    print(f"  target : {TARGET}")
    print(f"  backup : {bak}")
    print(f"  size   : {size} -> {len(chk)} (+{len(chk) - size} bytes)")
    _eol_name = "CRLF" if eol == b"\r\n" else "LF"
    print(f"  eol    : {_eol_name}")
    print("Next: .\\build.ps1 -Apworld  (repackage), then gen a dlc_only seed with")
    print("      dlc_only_rune_catchup: true and confirm every rune drop is a Lord's Rune.")


if __name__ == "__main__":
    main()
