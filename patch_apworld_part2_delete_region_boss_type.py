#!/usr/bin/env python3
"""Part 2 (true deletion): remove region_boss_type.

It only fed the `if ... and False:` (disabled, unfinished) region_bosses rules block, so it does
nothing today. Confirmed NOT read by the C# randomizer / C++ client (grep of the repo: only yamls/
docs reference it), so dropping its slot_data key is bake-safe.

Deletes the option class + dataclass field + Advanced-group entry, neutralizes the two dead
`if self.options.region_boss_type:` branches to `if False:` (the block is already disabled), and
removes the slot_data key. Idempotent, CRLF-safe, py_compiles, .bak_rbt backups.
"""
import os, sys, py_compile, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OPTIONS = os.path.join(HERE, "Archipelago", "worlds", "eldenring", "options.py")
INIT = os.path.join(HERE, "Archipelago", "worlds", "eldenring", "__init__.py")

RBT_CLS = '''class RegionBossType(Toggle):
    """Remove cave and catacombs type bosses from region bosses."""
    display_name = "Region Boss Type"'''

OPTIONS_EDITS = [
    ("del", RBT_CLS, "class RegionBossType(Toggle):"),
    ("del", "\n    region_boss_type: RegionBossType", "    region_boss_type: RegionBossType"),
    ("del", "\n        RegionBossType,", "        RegionBossType,"),
]

INIT_EDITS = [
    ("sub",
     "\n            if self.options.region_boss_type: # only bosses in both sets are used",
     "\n            if False:  # region_boss_type removed (Part 2); region_bosses rules block is disabled",
     "region_bosses rules block is disabled"),
    ("sub",
     "\n                if self.options.region_boss_type: # only bosses in both sets are used",
     "\n                if False:  # region_boss_type removed (Part 2), DLC bosses",
     "region_boss_type removed (Part 2), DLC bosses"),
    ("del",
     '\n                "region_boss_type": self.options.region_boss_type.value,',
     '"region_boss_type": self.options.region_boss_type.value,'),
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
    open(path + ".bak_rbt", "wb").write(raw)
    open(path, "wb").write(out)
    print(f"  {os.path.basename(path)}: patched ({'CRLF' if crlf else 'LF'}); backup .bak_rbt")

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
