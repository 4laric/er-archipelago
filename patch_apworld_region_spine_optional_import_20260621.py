#!/usr/bin/env python3
r"""patch_apworld_region_spine_optional_import_20260621.py

HOTFIX for patch_apworld_dlc_only_chain_20260621.py: region_spine.py uses `Optional` in the
DLC_CHAIN_LOCK_PARENT annotation (Dict[str, Optional[str]]) but only imports Dict/List/Set/Tuple,
so importing the module raises `NameError: name 'Optional' is not defined` -> the whole EldenRing
world fails to load -> gen reports the player yaml as invalid. Add Optional to the typing import.

RUN ON WINDOWS from the repo root:
    python patch_apworld_region_spine_optional_import_20260621.py
    .\build.ps1 -Apworld -Generate
"""
import io, os, sys, py_compile, shutil

PATH   = os.path.join("Archipelago", "worlds", "eldenring", "region_spine.py")
ANCHOR = "from typing import Dict, List, Set, Tuple"
REPL   = "from typing import Dict, List, Optional, Set, Tuple"


def main():
    if not os.path.isfile(PATH):
        print(f"ERROR: not found: {PATH} (run from the repo root).")
        return 2
    raw = io.open(PATH, "r", encoding="utf-8", newline="").read()
    if "Optional" in raw.split("\n", 30)[0:30] and "Optional, Set" in raw:
        print("Already imports Optional. No-op.")
        return 0
    nl = "\r\n" if "\r\n" in raw else "\n"
    text = raw.replace("\r\n", "\n")
    n = text.count(ANCHOR)
    if n != 1:
        print(f"ABORT: anchor not unique (found {n}x): {ANCHOR!r}")
        return 1
    text = text.replace(ANCHOR, REPL, 1).replace("\n", nl)

    bak = PATH + ".bak_optionalimport"
    shutil.copy2(PATH, bak)
    try:
        with io.open(PATH, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        py_compile.compile(PATH, doraise=True)
    except Exception as e:
        print(f"FAILED ({e}); restoring backup.")
        shutil.copy2(bak, PATH)
        return 1

    pc = os.path.join(os.path.dirname(PATH), "__pycache__")
    if os.path.isdir(pc):
        for fn in os.listdir(pc):
            try:
                os.remove(os.path.join(pc, fn))
            except OSError:
                pass
    print("OK. Added Optional to region_spine.py typing import. Backup: " + bak)
    return 0


if __name__ == "__main__":
    sys.exit(main())
