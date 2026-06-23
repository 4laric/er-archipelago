#!/usr/bin/env python3
r"""patch_apworld_dlconly_physick_guarantee_20260621.py

FEATURE (Alaric 2026-06-21): put the Progressive Flask of Wondrous Physick on the SAME guaranteed
pipeline as the stone bells + flasks -- with a deliberately LOW count (it's a single ladder).

Physick collapses the flask + low tears into ONE progressive ladder (~5 steps: flask -> restoratives
-> Shrouding -> Sapping(DLC) -> Knots; copies past it -> Lord's Rune, via consumable_grants.py /
physick_tears.py). On a tight dlc_only seed the normal injectable seating is best-effort, so this
adds a count-neutral, filler-funded GUARANTEE like the bells/flasks:

  new option `progressive_physick_count` (Range 0..40, default 0 = off). When >0 on a dlc_only seed,
  seat that many PROG_PHYSICK copies via the same cheapest-filler scrub (crafting mats first, then
  rune drops). ADDITIVE to the normal injectable seating. Keep it LOW -- a single 5-step ladder
  means anything past ~5 is just Lord's Rune overflow.

PREREQ: none hard; sits alongside the bell + flask guarantee patches (all insert before the same
"# Extra filler items" line; order-independent). The Progressive Items group insert anchors on
ProgressiveBellEarlyCount so it is independent of whether the flask patch ran.

TOUCHES (transactional):
  worlds/eldenring/options.py   -- ProgressivePhysickCount + dataclass field + Progressive Items group
  worlds/eldenring/__init__.py  -- the dlc_only physick-guarantee swap (single-name variant)

Idempotent (aborts if MARKER present). CRLF-preserving. Byte-compiles + self-restores on failure.
NOTE: options.py dataclass/group anchors sit past the sandbox read-truncation point but match on the
intact Windows file; the patch aborts cleanly if any anchor moved.

RUN ON WINDOWS from the repo root:
    python patch_apworld_dlconly_physick_guarantee_20260621.py
    .\build.ps1 -Apworld -Generate
"""
import io, os, sys, py_compile, shutil

OPTIONS = os.path.join("Archipelago", "worlds", "eldenring", "options.py")
INIT    = os.path.join("Archipelago", "worlds", "eldenring", "__init__.py")
MARKER  = "progressive_physick_count"


OPT_CLASS = '''

class ProgressivePhysickCount(Range):
    """How many copies of the Progressive Flask of Wondrous Physick to GUARANTEE into a dlc_only
    pool, via the same count-neutral, filler-funded swap the stone bells / flasks use.

    Physick is a SINGLE ladder (~5 steps: flask -> restoratives -> Shrouding -> Sapping(DLC) ->
    Knots), so keep this LOW -- copies past the ladder length just pay out as Lord's Runes. Additive
    to the normal injectable seating. 0 = off. Only matters with progressive_physick on + dlc_only."""
    display_name = "Progressive Physick Pool Count (dlc_only guarantee)"
    range_start = 0
    range_end = 40
    default = 0'''

OPT_EDITS = [
    # 1) new option class, right after ProgressivePhysick.
    (
        '    display_name = "Progressive Flask of Wondrous Physick"',
        '    display_name = "Progressive Flask of Wondrous Physick"' + OPT_CLASS,
    ),
    # 2) dataclass field, right after progressive_physick.
    (
        '    progressive_physick: ProgressivePhysick\n',
        '    progressive_physick: ProgressivePhysick\n'
        '    progressive_physick_count: ProgressivePhysickCount\n',
    ),
    # 3) Progressive Items group -- anchor on ProgressiveBellEarlyCount (independent of flask patch).
    (
        '        ProgressiveBellEarlyCount,\n',
        '        ProgressiveBellEarlyCount,\n        ProgressivePhysickCount,\n',
    ),
]

INIT_EDITS = [
    (
        "        # Extra filler items for locations containing skip items\n"
        "        self.local_itempool.extend(self.create_item(self.get_filler_item_name()) for _ in range(num_required_extra_items))\n",

        "        # progressive physick GUARANTEE (dlc_only, Alaric 2026-06-21): SAME pipeline as the\n"
        "        # bells/flasks, but physick is a SINGLE ladder so keep the count LOW (overflow copies\n"
        "        # -> Lord's Rune). Seats progressive_physick_count copies of PROG_PHYSICK via the\n"
        "        # count-neutral cheapest-filler scrub. Additive to the normal injectable seating. 0 = off.\n"
        "        if (self._progressive_physick_active() and self.options.dlc_only\n"
        "                and getattr(self.options, \"progressive_physick_count\", None)\n"
        "                and self.options.progressive_physick_count.value > 0):\n"
        "            _want = self.options.progressive_physick_count.value\n"
        "            _spared = getattr(self, \"_spared_comedy_junk\", set())\n"
        "            _droppable = [it for it in self.local_itempool\n"
        "                          if it.classification == ItemClassification.filler\n"
        "                          and it.name not in _spared\n"
        "                          and it.name != PROG_PHYSICK]\n"
        "            _droppable.sort(key=lambda it: getattr(it.data, \"runes\", 0) or 0)\n"
        "            _drop_n = min(_want, len(_droppable))\n"
        "            for _it in _droppable[:_drop_n]:\n"
        "                self.local_itempool.remove(_it)\n"
        "            for _ in range(_drop_n):\n"
        "                self.local_itempool.append(self.create_item(PROG_PHYSICK))\n"
        "            if _drop_n < _want:\n"
        "                warning(f\"{self.player_name}: progressive physick -- seated {_drop_n}/{_want} \"\n"
        "                        f\"(filler funding exhausted); lower progressive_physick_count or widen the pool.\")\n"
        "\n"
        "        # Extra filler items for locations containing skip items\n"
        "        self.local_itempool.extend(self.create_item(self.get_filler_item_name()) for _ in range(num_required_extra_items))\n",
    ),
]


def _newline_of(t): return "\r\n" if "\r\n" in t else "\n"


def _apply(path, edits, label):
    raw = io.open(path, "r", encoding="utf-8", newline="").read()
    nl = _newline_of(raw)
    text = raw.replace("\r\n", "\n")
    for anchor, repl in edits:
        a = anchor.replace("\r\n", "\n")
        n = text.count(a)
        if n != 1:
            raise RuntimeError(f"[{label}] anchor not unique (found {n}x):\n----\n{a[:160]}\n----")
        text = text.replace(a, repl.replace("\r\n", "\n"), 1)
    return text.replace("\n", nl)


def main():
    for p in (OPTIONS, INIT):
        if not os.path.isfile(p):
            print(f"ERROR: not found: {p} (run from the repo root).")
            return 2
    with io.open(OPTIONS, "r", encoding="utf-8", newline="") as f:
        if MARKER in f.read():
            print(f"Already applied (marker '{MARKER}' present). No-op.")
            return 0

    targets = [(OPTIONS, OPT_EDITS, "options.py"), (INIT, INIT_EDITS, "__init__.py")]
    new_texts = {}
    try:
        for path, edits, label in targets:
            new_texts[path] = _apply(path, edits, label)
    except Exception as e:
        print(f"ABORT (no files changed): {e}")
        return 1

    backups = {}
    try:
        for path, _, label in targets:
            bak = path + ".bak_physguar"
            shutil.copy2(path, bak)
            backups[path] = bak
            with io.open(path, "w", encoding="utf-8", newline="") as f:
                f.write(new_texts[path])
            py_compile.compile(path, doraise=True)
            print(f"  patched + compiled OK: {label}")
    except Exception as e:
        print(f"FAILED ({e}); restoring backups...")
        for path, bak in backups.items():
            shutil.copy2(bak, path)
        return 1

    pc = os.path.join(os.path.dirname(INIT), "__pycache__")
    if os.path.isdir(pc):
        for fn in os.listdir(pc):
            try:
                os.remove(os.path.join(pc, fn))
            except OSError:
                pass
    print("\nOK. Applied dlc_only progressive-physick guarantee. Backups: *.bak_physguar")
    print("Enable with `progressive_physick_count: 6` (keep it LOW) in the EldenRing yaml.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# =============================================================================================
# GEN-TEST: add `progressive_physick_count: 6` to EldenRing-Alaric.yaml (dlc_only +
# progressive_physick), then .\build.ps1 -Apworld -Generate. PASS =
#   * gen SUCCESS;
#   * spoiler holds ~6 Progressive Flask of Wondrous Physick placed as checks, ~6 cheapest filler
#     gone; progressive_physick_count: 0 reproduces prior behavior.
# In-game: the physick ladder comes online reliably + a couple overflow Lord's Runes.
# =============================================================================================
