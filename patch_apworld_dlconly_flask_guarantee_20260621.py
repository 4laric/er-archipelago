#!/usr/bin/env python3
r"""patch_apworld_dlconly_flask_guarantee_20260621.py

FEATURE (Alaric 2026-06-21): put progressive Golden Seeds + Sacred Tears on the SAME guaranteed
pipeline as the stone bells.

progressive_flasks swaps each discrete Golden Seed / Sacred Tear 1:1 to its progressive item -- but
in dlc_only the vanilla seed/tear locations aren't checks, so that swap barely fires and the player
gets almost no flask ramp. consumable_grants.py already gives the progressive flasks the SAME client
overflow path as the bells (copies past the 30-seed / 12-tear cap -> Lord's Rune), so the only thing
missing is the count-based, filler-funded seat. This adds it:

  new option `progressive_flask_count` (Range 0..40, default 0 = off). When >0 on a dlc_only seed,
  seat that many copies of EACH progressive flask via the same COUNT-NEUTRAL swap the bells use --
  drop the cheapest filler (low-tier crafting mats first, then base rune drops) and add the flasks.
  Guarantees the flask charge/potency ramp + a wave of overflow Lord's Runes. The 1:1 swap is left
  intact (the few DLC seed/tear checks still convert), so this is purely additive.

PREREQ: none hard, but designed to sit alongside patch_apworld_dlconly_bell_guarantee_20260621.py
(both insert before the same "# Extra filler items" line; order-independent).

TOUCHES (transactional):
  worlds/eldenring/options.py   -- ProgressiveFlaskCount + dataclass field + Progressive Items group
  worlds/eldenring/__init__.py  -- the dlc_only flask-guarantee swap (mirror of the bell swap)

Idempotent (aborts if MARKER present). CRLF-preserving. Byte-compiles + self-restores on failure.
NOTE: options.py dataclass/group anchors sit past the sandbox read-truncation point but match on the
intact Windows file; the patch aborts cleanly if any anchor moved.

RUN ON WINDOWS from the repo root:
    python patch_apworld_dlconly_flask_guarantee_20260621.py
    .\build.ps1 -Apworld -Generate
"""
import io, os, sys, py_compile, shutil

OPTIONS = os.path.join("Archipelago", "worlds", "eldenring", "options.py")
INIT    = os.path.join("Archipelago", "worlds", "eldenring", "__init__.py")
MARKER  = "progressive_flask_count"


OPT_CLASS = '''

class ProgressiveFlaskCount(Range):
    """How many copies of EACH progressive flask item (Progressive Golden Seed = charges,
    Progressive Sacred Tear = potency) to GUARANTEE into a dlc_only pool -- via the same
    count-neutral, filler-funded swap the stone bells use (cheapest junk dropped to fund them).

    dlc_only has few vanilla Golden Seed / Sacred Tear checks, so the normal 1:1 progressive_flasks
    swap barely fires there; this seats a tunable number regardless, and copies past the vanilla cap
    (30 seeds / 12 tears) pay out as Lord's Runes -- the flask analogue of progressive_bell_count.
    0 = off (1:1 swap only). Only matters with progressive_flasks on + dlc_only."""
    display_name = "Progressive Flask Pool Count (dlc_only guarantee)"
    range_start = 0
    range_end = 40
    default = 0'''

OPT_EDITS = [
    # 1) new option class, right after ProgressiveFlasks.
    (
        '    display_name = "Progressive Flask Upgrades"',
        '    display_name = "Progressive Flask Upgrades"' + OPT_CLASS,
    ),
    # 2) dataclass field, right after progressive_flask_early_count.
    (
        '    progressive_flask_early_count: ProgressiveFlaskEarlyCount\n',
        '    progressive_flask_early_count: ProgressiveFlaskEarlyCount\n'
        '    progressive_flask_count: ProgressiveFlaskCount\n',
    ),
    # 3) add to the "Progressive Items" option group (closes on ProgressiveFlaskEarlyCount).
    (
        '        ProgressiveFlaskEarlyCount,\n    ]),',
        '        ProgressiveFlaskEarlyCount,\n        ProgressiveFlaskCount,\n    ]),',
    ),
]

INIT_EDITS = [
    (
        "        # Extra filler items for locations containing skip items\n"
        "        self.local_itempool.extend(self.create_item(self.get_filler_item_name()) for _ in range(num_required_extra_items))\n",

        "        # progressive flask GUARANTEE (dlc_only, Alaric 2026-06-21): SAME pipeline as the\n"
        "        # stone bells -- seat the FULL progressive_flask_count copies of EACH progressive flask\n"
        "        # (Golden Seed = charges, Sacred Tear = potency), funded by the count-neutral cheapest-\n"
        "        # filler scrub (crafting mats first, then rune drops). dlc_only's 1:1 seed/tear swap\n"
        "        # underdelivers (few DLC seed/tear checks); this guarantees the flask ramp + the overflow\n"
        "        # Lord's Runes past the 30-seed / 12-tear cap (same client overflow path as bells).\n"
        "        # 0 = off. See consumable_grants.py / er-progressive-stone-bells.\n"
        "        if (self._progressive_flasks_active() and self.options.dlc_only\n"
        "                and getattr(self.options, \"progressive_flask_count\", None)\n"
        "                and self.options.progressive_flask_count.value > 0):\n"
        "            _flask_names = list(FLASK_PROGRESSIVE_NAMES)\n"
        "            _per = self.options.progressive_flask_count.value\n"
        "            _want = _per * len(_flask_names)\n"
        "            _spared = getattr(self, \"_spared_comedy_junk\", set())\n"
        "            _droppable = [it for it in self.local_itempool\n"
        "                          if it.classification == ItemClassification.filler\n"
        "                          and it.name not in _spared\n"
        "                          and it.name not in _flask_names]\n"
        "            _droppable.sort(key=lambda it: getattr(it.data, \"runes\", 0) or 0)\n"
        "            _drop_n = min(_want, len(_droppable))\n"
        "            for _it in _droppable[:_drop_n]:\n"
        "                self.local_itempool.remove(_it)\n"
        "            _counts = {n: 0 for n in _flask_names}\n"
        "            _seated = 0\n"
        "            _fi = 0\n"
        "            while _seated < _drop_n and not all(_counts[n] >= _per for n in _flask_names):\n"
        "                _n = _flask_names[_fi % len(_flask_names)]\n"
        "                if _counts[_n] < _per:\n"
        "                    self.local_itempool.append(self.create_item(_n))\n"
        "                    _counts[_n] += 1\n"
        "                    _seated += 1\n"
        "                _fi += 1\n"
        "            if _seated < _want:\n"
        "                warning(f\"{self.player_name}: progressive flasks -- seated {_seated}/{_want} \"\n"
        "                        f\"(filler funding exhausted); lower progressive_flask_count or widen the pool.\")\n"
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
            bak = path + ".bak_flaskguar"
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
    print("\nOK. Applied dlc_only progressive-flask guarantee. Backups: *.bak_flaskguar")
    print("Enable with `progressive_flask_count: 25` (or similar) in the EldenRing yaml.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# =============================================================================================
# GEN-TEST: add `progressive_flask_count: 25` to EldenRing-Alaric.yaml (dlc_only + progressive_flasks),
# then .\build.ps1 -Apworld -Generate. PASS =
#   * gen SUCCESS;
#   * spoiler holds ~25 Progressive Golden Seed + ~25 Progressive Sacred Tear placed as checks
#     (was a handful from the DLC-only 1:1 swap), with ~50 of the cheapest filler gone;
#   * progressive_flask_count: 0 reproduces the prior behavior (regression check).
# In-game: flask charges/potency ramp quickly + overflow Lord's Runes past the 30/12 cap.
# =============================================================================================
