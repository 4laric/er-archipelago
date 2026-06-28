#!/usr/bin/env python3
"""Part 2 (true deletion): remove pool_builder_dlc_gear + great_runes_present.

Both are narrow, FILL-TIME-ONLY options (NOT in slot_data, so baker/client-safe to remove):
  pool_builder_dlc_gear -- overlapped dlc_gear_curation + a DLC-dep footgun; removing it reverts
                           pool_builder to base-game-juice-only (_allow_dlc_juice = False).
  great_runes_present   -- only fired in num_regions rune_source=pool; removing it makes the
                           deficit great-rune injection always target exactly great_runes_required.

Deletes the two option classes + dataclass fields + their entries in the Advanced & Experimental
group, and rewires the two logic sites. Idempotent, CRLF-safe, py_compiles, .bak_part2 backups.
Run on Windows: python patch_apworld_part2_delete_narrow.py  then  .\build.ps1 -Apworld + re-gen.
"""
import os, sys, py_compile, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OPTIONS = os.path.join(HERE, "Archipelago", "worlds", "eldenring", "options.py")
INIT = os.path.join(HERE, "Archipelago", "worlds", "eldenring", "__init__.py")

POOL_CLS = '''class PoolBuilderDLCGear(Toggle):
    """When pool_builder is on, also pull DLC S/A items into the all-game ladder -- S-tier DLC
    weapons/armor/spells/Ashes of War (via the PvE tier list) plus the curated best-DLC-gear set
    dlc_gear_curation uses. Off = the ladder injects base-game juice only. Ungated from
    enable_dlc (DLC item ids are always registered), but granting DLC items still needs the DLC
    installed in-game -- so enabling this on a base-game run reintroduces a DLC dependency.
    Only matters when pool_builder is on. See SPEC-pool-builder.md."""
    display_name = "Pool Builder: include DLC S/A gear"'''

GRP_CLS = '''class GreatRunesPresent(Range):
    """How many Great Runes to force into the pool in a num_regions run, even beyond the
    Leyndell / final-boss requirement -- the Great-Rune analogue of Messmer Kindle Shards Max
    vs Required. Only the DEFICIT (this minus the great runes already on kept rune-bosses) is
    injected, capped by the great runes whose bosses are sealed (<= 7 total). Clamped UP to at
    least great_runes_required. 0 = inject exactly as many as required (default; no change).
    Ignored outside a num_regions rune_source=pool run (a full run already has all 7)."""
    display_name = "Great Runes Present"
    range_start = 0
    range_end = 7
    default = 0'''

OPTIONS_EDITS = [
    ("del", POOL_CLS, "class PoolBuilderDLCGear(Toggle):"),
    ("del", GRP_CLS, "class GreatRunesPresent(Range):"),
    ("del", "\n    great_runes_present: GreatRunesPresent", "    great_runes_present: GreatRunesPresent"),
    ("del", "\n    pool_builder_dlc_gear: PoolBuilderDLCGear", "    pool_builder_dlc_gear: PoolBuilderDLCGear"),
    ("del", "\n        GreatRunesPresent,\n        PoolBuilderDLCGear,", "        GreatRunesPresent,"),
]

INIT_E_OLD = '''        # pool_builder_dlc_gear: pull DLC S/A items into the ladder too (mirror of
        # dlc_gear_curation; ungated from enable_dlc -- DLC item ids are always registered).
        _allow_dlc_juice = bool(self.options.pool_builder_dlc_gear.value)'''
INIT_E_NEW = '''        # pool_builder_dlc_gear was removed (Part 2): the all-game ladder injects base juice only
        # (use dlc_gear_curation for DLC gear).
        _allow_dlc_juice = False'''

INIT_F_OLD = '''                    # great_runes_present (>= required) forces EXTRA great runes into the pool
                    # beyond the Leyndell gate -- the Great-Rune mirror of MessmerKindleMax vs
                    # Required. 0 = match great_runes_required (default; no behaviour change).
                    _gr_target = max(int(self.options.great_runes_required.value),
                                     int(self.options.great_runes_present.value))'''
INIT_F_NEW = '''                    # great_runes_present was removed (Part 2): the deficit injection now always
                    # targets exactly great_runes_required.
                    _gr_target = int(self.options.great_runes_required.value)'''

INIT_EDITS = [
    ("sub", INIT_E_OLD, INIT_E_NEW, "the all-game ladder injects base juice only"),
    ("sub", INIT_F_OLD, INIT_F_NEW, "great_runes_present was removed (Part 2)"),
]

def apply_edits(text, edits):
    for edit in edits:
        kind = edit[0]
        if kind == "sub":
            _, old, new, marker = edit
            if old in text:
                if text.count(old) != 1:
                    raise SystemExit(f"ABORT: anchor x{text.count(old)}: {marker!r}")
                text = text.replace(old, new, 1)
            elif marker in text:
                print(f"  [skip] applied: {marker[:46]!r}")
            else:
                raise SystemExit(f"ABORT: anchor not found / not applied: {marker[:46]!r}")
        elif kind == "del":
            _, old, sig = edit
            if old in text:
                if text.count(old) != 1:
                    raise SystemExit(f"ABORT: del-anchor x{text.count(old)}: {sig!r}")
                text = text.replace(old, "", 1)
            elif sig in text:
                raise SystemExit(f"ABORT: del-anchor drifted: {sig!r}")
            else:
                print(f"  [skip] removed: {sig!r}")
    return text

def patch_file(path, edits):
    raw = open(path, "rb").read()
    total = raw.count(b"\n"); crlf = raw.count(b"\r\n") == total and total > 0
    work = raw.decode("utf-8").replace("\r\n", "\n") if crlf else raw.decode("utf-8")
    nw = apply_edits(work, edits)
    if nw == work:
        print(f"  {os.path.basename(path)}: no change."); return
    out = (nw.replace("\n", "\r\n") if crlf else nw).encode("utf-8")
    with tempfile.NamedTemporaryFile("wb", suffix=".py", delete=False) as tf:
        tf.write(out); tmp = tf.name
    try:
        py_compile.compile(tmp, doraise=True)
    finally:
        os.remove(tmp)
    open(path + ".bak_part2", "wb").write(raw)
    open(path, "wb").write(out)
    print(f"  {os.path.basename(path)}: patched ({'CRLF' if crlf else 'LF'}); backup .bak_part2")

def main():
    for p in (OPTIONS, INIT):
        if not os.path.isfile(p):
            print("ERROR not found:", p); return 1
    print("patching options.py ..."); patch_file(OPTIONS, OPTIONS_EDITS)
    print("patching __init__.py ..."); patch_file(INIT, INIT_EDITS)
    print("done.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
