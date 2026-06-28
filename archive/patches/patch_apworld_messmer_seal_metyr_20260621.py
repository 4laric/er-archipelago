#!/usr/bin/env python3
r"""patch_apworld_messmer_seal_metyr_20260621.py

FIX (Alaric 2026-06-21, option 2 / lean): SEAL the Metyr side-area in the messmer mini-campaign.

The messmer kept-set kept Cathedral of Manus Metyr + Finger Ruins of Miyr (the Metyr boss =
"FRM: Remembrance of the Mother of Fingers") + Finger Ruins of Dheo, but they are UNREACHABLE in
messmer: the Cathedral entrance rule is the vanilla 3-bell questline
    Hole-Laden Necklace AND can_go_to(Finger Ruins of Rhia) AND can_go_to(Finger Ruins of Dheo)
and Finger Ruins of Rhia hangs off Cerulean Coast, which the messmer scope SEALS. So can_go_to(Rhia)
is never true, the Cathedral never opens, and ~10 checks (Metyr's remembrance, Cherishing Fingers,
etc.) sat in the played pool but unreachable (dead checks that could swallow items; tolerated only
because dlc_only forces accessibility: minimal).

Lean fix: drop those three regions from DLC_MINI_KEPT_REGIONS so compute_dlc_mini_scope SEALS them
(lock-free sub-regions -> their checks become locked-vanilla events), reclaiming the dead checks.
Metyr is simply out of scope for the messmer run (goal is Messmer at Shadow Keep). To instead make
Metyr reachable, the opposite change (add Ellac/Cerulean Lock + Ellac River/Cerulean Coast/Finger
Ruins of Rhia to the kept set) would be needed -- NOT done here.

TOUCHES worlds/eldenring/region_spine.py only (DLC_MINI_KEPT_REGIONS).
Idempotent (aborts if MARKER present). LF file. Byte-compiles + self-restores on failure.

RUN ON WINDOWS from the repo root:
    python patch_apworld_messmer_seal_metyr_20260621.py
    .\build.ps1 -Apworld -Generate
"""
import io, os, sys, py_compile, shutil

SPINE = os.path.join("Archipelago", "worlds", "eldenring", "region_spine.py")
MARKER = "messmer option 2"

EDITS = [
    (
        '    "Cathedral of Manus Metyr", "Finger Ruins of Miyr",\n',
        '    # SEALED in messmer (option 2, 2026-06-21): Cathedral of Manus Metyr / Finger Ruins of\n'
        '    # Miyr (Metyr) / Finger Ruins of Dheo are unreachable here -- the Cathedral 3-bell\n'
        '    # questline needs Finger Ruins of Rhia, which is on the sealed Cerulean branch. Dropped\n'
        '    # from the kept set so they seal cleanly instead of being dead checks.\n',
    ),
    (
        '    "Shadow Keep Storehouse Back", "Scaduview", "Hinterland", "Finger Ruins of Dheo",\n',
        '    "Shadow Keep Storehouse Back", "Scaduview", "Hinterland",\n',
    ),
]


def main():
    if not os.path.isfile(SPINE):
        print(f"ERROR: not found: {SPINE} (run from the repo root).")
        return 2
    raw = io.open(SPINE, "r", encoding="utf-8", newline="").read()
    if MARKER in raw:
        print(f"Already applied (marker '{MARKER}' present). No-op.")
        return 0
    nl = "\r\n" if "\r\n" in raw else "\n"
    text = raw.replace("\r\n", "\n")
    for anchor, repl in EDITS:
        a = anchor.replace("\r\n", "\n")
        n = text.count(a)
        if n != 1:
            print(f"ABORT (no change): anchor not unique (found {n}x):\n----\n{a[:120]}\n----")
            return 1
        text = text.replace(a, repl.replace("\r\n", "\n"), 1)
    out = text.replace("\n", nl)

    bak = SPINE + ".bak_sealmetyr"
    shutil.copy2(SPINE, bak)
    try:
        with io.open(SPINE, "w", encoding="utf-8", newline="") as f:
            f.write(out)
        py_compile.compile(SPINE, doraise=True)
    except Exception as e:
        print(f"FAILED ({e}); restoring backup.")
        shutil.copy2(bak, SPINE)
        return 1

    pc = os.path.join(os.path.dirname(SPINE), "__pycache__")
    if os.path.isdir(pc):
        for fn in os.listdir(pc):
            try:
                os.remove(os.path.join(pc, fn))
            except OSError:
                pass
    print("OK. Sealed Cathedral/Metyr/Finger Ruins of Dheo in messmer. Backup: " + bak)
    return 0


if __name__ == "__main__":
    sys.exit(main())

# =============================================================================================
# GEN-TEST: ending_condition: messmer (dlc_only) -> .\build.ps1 -Apworld -Generate. PASS =
#   * gen SUCCESS;
#   * spoiler no longer lists CMM/FRM/FRD as randomized checks (they're locked-vanilla events);
#   * "FRM: Remembrance of the Mother of Fingers" holds its vanilla item, not an AP item;
#   * goal (Messmer / Shadow Keep) still reachable; played-pool check count drops by ~10.
# =============================================================================================
