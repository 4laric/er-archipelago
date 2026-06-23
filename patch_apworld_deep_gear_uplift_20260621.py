#!/usr/bin/env python3
r"""patch_apworld_deep_gear_uplift_20260621.py

FEATURE (Alaric 2026-06-21): opt-in `deep_gear_uplift` -- deepen the curation inject ladder to
include A- and B-tier base-game gear, not just S-tier.

The pool_builder / relevance_uplift (dlc_only) swaps inject ranked base-game juice into the slots
freed by scrubbing bottom-tier junk. Today the ITEM_TIERS gear pull is **S-tier only**
(_uplift_inject_names), so once the handful of S items run out the ladder falls back to
runes/seeds. With deep_gear_uplift ON the pull also draws A- and B-tier base gear (PvE tier list)
-- a much larger pool of solid, thematic equipment -- so scrubbed junk is replaced with usable kit
instead of more runes. Count-neutral (rides the existing injected<=scrubbed swap). DEFAULT OFF.

TOUCHES (transactional -- validates EVERY anchor before writing any):
  worlds/eldenring/options.py   -- DeepGearUplift toggle + dataclass field + Pool & Curation group
  worlds/eldenring/__init__.py  -- _uplift_inject_names: S -> {S,A,B} base gear when the toggle is on

Idempotent (aborts if MARKER present). CRLF-preserving. Byte-compiles + self-restores on failure.
NOTE: the options.py dataclass/option_groups anchors sit past the sandbox read-truncation point but
are matched on Windows where the file is intact; if any anchor moved the patch aborts cleanly.

RUN ON WINDOWS from the repo root:
    python patch_apworld_deep_gear_uplift_20260621.py
    .\build.ps1 -Apworld -Generate
"""
import io, os, sys, py_compile, shutil

OPTIONS = os.path.join("Archipelago", "worlds", "eldenring", "options.py")
INIT    = os.path.join("Archipelago", "worlds", "eldenring", "__init__.py")
MARKER  = "deep_gear_uplift"


OPT_CLASS = '''

class DeepGearUplift(Toggle):
    """Deepen the curation inject ladder to include A- and B-tier base-game gear.

    The pool_builder / relevance_uplift (dlc_only) swaps normally inject only S-tier base
    weapons/armor/spells/Ashes of War from the PvE tier list into the slots freed by scrubbing
    bottom-tier junk. With this ON the ladder also draws A- and B-tier base gear -- a much larger
    pool of solid, thematic equipment -- so the scrubbed junk is replaced with usable kit instead
    of falling back to runes/seeds. Only meaningful with pool_builder or a dlc_only relevance_uplift
    run; inert otherwise. DLC gear is governed separately by pool_builder_dlc_gear / dlc_gear_curation."""
    display_name = "Deep Gear Uplift (inject A/B-tier base gear)"'''

OPT_EDITS = [
    # 1) new option class, right after PoolBuilderDLCGear.
    (
        '    display_name = "Pool Builder: include DLC S/A gear"',
        '    display_name = "Pool Builder: include DLC S/A gear"' + OPT_CLASS,
    ),
    # 2) dataclass field, right after pool_builder_dlc_gear (the last field).
    (
        '    pool_builder_dlc_gear: PoolBuilderDLCGear\n',
        '    pool_builder_dlc_gear: PoolBuilderDLCGear\n    deep_gear_uplift: DeepGearUplift\n',
    ),
    # 3) add to the "Pool & Curation" option group (closes on RandomizeEnia).
    (
        '        RandomizeEnia,\n    ]),',
        '        RandomizeEnia,\n        DeepGearUplift,\n    ]),',
    ),
]

INIT_EDITS = [
    (
        '        uniques += [n for n, t in ITEM_TIERS.items()\n'
        '                    if t == "S" and n in item_table and (_allow_dlc_juice or not item_table[n].is_dlc)]\n',

        '        # deep_gear_uplift: widen the base-gear pull from S-tier to S+A+B when opted in.\n'
        '        _gear_tiers = {"S"}\n'
        '        if getattr(self.options, "deep_gear_uplift", None) and self.options.deep_gear_uplift.value:\n'
        '            _gear_tiers |= {"A", "B"}\n'
        '        uniques += [n for n, t in ITEM_TIERS.items()\n'
        '                    if t in _gear_tiers and n in item_table and (_allow_dlc_juice or not item_table[n].is_dlc)]\n',
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
            bak = path + ".bak_deepgear"
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
    print("\nOK. Applied deep_gear_uplift (default OFF). Backups: *.bak_deepgear")
    print("Enable with `deep_gear_uplift: true` in the EldenRing yaml.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# =============================================================================================
# GEN-TEST: add `deep_gear_uplift: true` to EldenRing-Alaric.yaml (dlc_only + pool_builder), then
# .\build.ps1 -Apworld -Generate. PASS =
#   * gen SUCCESS;
#   * spoiler shows a clear jump in A/B-tier base weapons/armor/spells placed as checks (vs the
#     S-only ladder), filling slots that previously held Golden Runes / seeds;
#   * toggling it OFF reproduces the prior S-only mix (regression check).
# =============================================================================================
