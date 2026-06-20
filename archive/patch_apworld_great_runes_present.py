#!/usr/bin/env python3
"""
patch_apworld_great_runes_present.py -- add a `great_runes_present` arg that forces EXTRA great runes
into the pool in num_regions runs, beyond the Leyndell gate. The Great-Rune analogue of Messmer Kindle
Shards Max vs Required.

CONTEXT: In a num_regions run with num_regions_rune_source=pool, the deficit injector (__init__.py ~L514)
places exactly `great_runes_required` great runes:
    _need = max(0, great_runes_required - len(kept_rune_steps))
i.e. just enough kept-boss runes + injected sealed-boss runes to satisfy the Leyndell gate. There was no
way to seed MORE than the minimum (the kindling feature has MessmerKindleMax > MessmerKindleRequired for
exactly this; great runes had only the "required" side).

THIS PATCH adds GreatRunesPresent (Range 0..7, default 0) and drives `_need` off it:
    _gr_target = max(great_runes_required, great_runes_present)   # present clamps UP to required
    _need = max(0, _gr_target - len(kept_rune_steps))
- present == 0  -> _gr_target == required -> IDENTICAL to today (safe default; no behaviour change).
- present  > required -> injects extra sealed-boss great runes (capped by the candidate loop at <= the
  great runes whose bosses are sealed, and by 7 total). Extra runes all count toward the gate, so they
  add redundancy / multiple satisfy-paths, never break logic.
Each injected rune is count-neutral (demand-drops a filler slot in create_items), and the existing
"could only source N of M" warning still fires if there aren't enough sealed rune bosses.

SCOPE: only the num_regions rune_source=pool injection path. A full open-world run already has all 7 great
runes present, so the knob is moot there (documented in the option help).

Targets (both CRLF): Archipelago/worlds/eldenring/options.py + __init__.py. Byte-level replace to preserve
CRLF (the Edit tool truncates CRLF source). Idempotent; verifies on disk. Run on Windows, then re-gen.
No client/baker build needed (pure fill-logic option).
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
ED = os.path.join(ROOT, "Archipelago", "worlds", "eldenring")
OPTIONS = os.path.join(ED, "options.py")
INIT = os.path.join(ED, "__init__.py")

# ---- options.py: new option class (insert after GreatRunesMountaintops, before DeathlessRouting) ----
OPT_CLS_OLD = b"    range_end = 7\r\n    default = 0\r\n\r\nclass DeathlessRouting(Toggle):"
GR_CLASS = (
    "class GreatRunesPresent(Range):\r\n"
    "    \"\"\"How many Great Runes to force into the pool in a num_regions run, even beyond the\r\n"
    "    Leyndell / final-boss requirement -- the Great-Rune analogue of Messmer Kindle Shards Max\r\n"
    "    vs Required. Only the DEFICIT (this minus the great runes already on kept rune-bosses) is\r\n"
    "    injected, capped by the great runes whose bosses are sealed (<= 7 total). Clamped UP to at\r\n"
    "    least great_runes_required. 0 = inject exactly as many as required (default; no change).\r\n"
    "    Ignored outside a num_regions rune_source=pool run (a full run already has all 7).\"\"\"\r\n"
    "    display_name = \"Great Runes Present\"\r\n"
    "    range_start = 0\r\n"
    "    range_end = 7\r\n"
    "    default = 0\r\n"
)
OPT_CLS_NEW = (b"    range_end = 7\r\n    default = 0\r\n\r\n"
               + GR_CLASS.encode("utf-8")
               + b"\r\nclass DeathlessRouting(Toggle):")

# ---- options.py: register in the options dataclass ----
OPT_DC_OLD = b"    great_runes_mountaintops: GreatRunesMountaintops\r\n"
OPT_DC_NEW = (b"    great_runes_mountaintops: GreatRunesMountaintops\r\n"
              b"    great_runes_present: GreatRunesPresent\r\n")

# ---- __init__.py: drive _need off great_runes_present ----
INIT_OLD = (b"                    _need = max(0, int(self.options.great_runes_required.value)\r\n"
            b"                                - len(_kept_rune_steps))")
INIT_NEW = (b"                    # great_runes_present (>= required) forces EXTRA great runes into the pool\r\n"
            b"                    # beyond the Leyndell gate -- the Great-Rune mirror of MessmerKindleMax vs\r\n"
            b"                    # Required. 0 = match great_runes_required (default; no behaviour change).\r\n"
            b"                    _gr_target = max(int(self.options.great_runes_required.value),\r\n"
            b"                                     int(self.options.great_runes_present.value))\r\n"
            b"                    _need = max(0, _gr_target - len(_kept_rune_steps))")


def _patch(path, edits, done_marker):
    with open(path, "rb") as f:
        data = f.read()
    if done_marker in data:
        print("  [skip] %s already patched." % os.path.basename(path))
        return
    for label, old, new in edits:
        n = data.count(old)
        if n != 1:
            sys.exit("ERROR: %s anchor '%s' found %d times (expected 1). Aborting; no write."
                     % (os.path.basename(path), label, n))
        before = len(data)
        data = data.replace(old, new, 1)
        if len(data) != before - len(old) + len(new):
            sys.exit("ERROR: %s unexpected length after '%s'. Aborting; no write."
                     % (os.path.basename(path), label))
    with open(path, "wb") as f:
        f.write(data)
    with open(path, "rb") as f:
        chk = f.read()
    assert done_marker in chk, "VERIFY FAILED: %s" % path
    print("  [ok]   %s patched + verified." % os.path.basename(path))


def main():
    for p in (OPTIONS, INIT):
        if not os.path.isfile(p):
            sys.exit("ERROR: not found: %s" % p)
    _patch(OPTIONS, [
        ("option class", OPT_CLS_OLD, OPT_CLS_NEW),
        ("dataclass field", OPT_DC_OLD, OPT_DC_NEW),
    ], done_marker=b"class GreatRunesPresent(Range):")
    _patch(INIT, [
        ("deficit _need", INIT_OLD, INIT_NEW),
    ], done_marker=b"_gr_target = max(int(self.options.great_runes_required.value),")
    print("Done. Add `great_runes_present: <N>` to the yaml (0..7; >great_runes_required to seed extras).")
    print("Next: re-gen (+ gen-test). No client/baker build needed.")


if __name__ == "__main__":
    main()
