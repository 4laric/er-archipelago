#!/usr/bin/env python3
r"""patch_apworld_dump_sphere_counts.py

Dump TOTAL-REACHABLE-CHECKS-per-sphere for a seed, computed from the same
multiworld.get_spheres() AP already runs for the playthrough. Writes
    Archipelago/output/ER_SPHERES_<seed>.txt
with a line per sphere (sphere 0 = the OPENING reachable set = your "sphere 1"),
plus the total reachable check count. Gen-time, gated by the env var
ER_DUMP_SPHERES so normal sweeps pay nothing.

Inserts a guarded block at the TOP of EldenRing.fill_slot_data (after fill, where
get_spheres() is valid). Counts only real checks (item.code is not None), so
events / sealed-region locations are excluded; permanently-unreachable locations
never appear in get_spheres, so the total is genuinely reachable checks.

USAGE (Windows, repo root):
    python patch_apworld_dump_sphere_counts.py
    # reproduce one seed with the dump on (PowerShell):
    $env:ER_DUMP_SPHERES = "1"
    cd Archipelago ; python Generate.py --seed 555768038979539724 ; cd ..
    Remove-Item Env:\ER_DUMP_SPHERES
    # read: Archipelago\output\ER_SPHERES_555768038979539724.txt
(-Generate reads the worlds\eldenring SOURCE, so no apworld rebuild is needed
 for a source-tree re-gen; rebuild only if you sweep the packaged apworld.)
"""
import os, sys

REPO   = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(REPO, "Archipelago", "worlds", "eldenring", "__init__.py")

ANCHOR_LINE = b"        slot_data: Dict[str, object] = {}"
MARKER      = b"ER_DUMP_SPHERES"          # idempotency marker
TAIL_SYMBOL = b"interpret_slot_data"

BLOCK_LINES = [
    "        # --- ER sphere-count dump (gated by env ER_DUMP_SPHERES; reachability analytics) ---",
    "        import os as _ersp_os",
    "        if _ersp_os.environ.get(\"ER_DUMP_SPHERES\") and self.player == 1:",
    "            try:",
    "                _ersp_counts = []",
    "                for _ersp_s in self.multiworld.get_spheres():",
    "                    _ersp_n = sum(1 for _l in _ersp_s if _l.player == self.player and _l.item is not None and _l.item.code is not None)",
    "                    _ersp_counts.append(_ersp_n)",
    "                _ersp_seed = getattr(self.multiworld, \"seed\", \"x\")",
    "                _ersp_dir = _ersp_os.path.join(_ersp_os.getcwd(), \"output\")",
    "                if not _ersp_os.path.isdir(_ersp_dir):",
    "                    _ersp_dir = _ersp_os.getcwd()",
    "                _ersp_path = _ersp_os.path.join(_ersp_dir, f\"ER_SPHERES_{_ersp_seed}.txt\")",
    "                with open(_ersp_path, \"w\", encoding=\"utf-8\") as _ersp_f:",
    "                    _ersp_f.write(f\"seed {_ersp_seed}  total_reachable_checks {sum(_ersp_counts)}  spheres {len(_ersp_counts)}\\n\")",
    "                    for _ersp_i, _ersp_c in enumerate(_ersp_counts):",
    "                        _ersp_f.write(f\"sphere {_ersp_i}: {_ersp_c} checks\\n\")",
    "            except Exception as _ersp_e:",
    "                print(f\"ER_DUMP_SPHERES dump failed: {_ersp_e}\")",
]


def main():
    if not os.path.isfile(TARGET):
        sys.exit(f"ERROR: not found: {TARGET}")
    size = os.path.getsize(TARGET)
    with open(TARGET, "rb") as f:
        data = f.read()
    if len(data) != size:
        sys.exit(f"ERROR: short read ({len(data)} != {size}) -- I/O truncation; aborting, no write.")
    if TAIL_SYMBOL not in data:
        sys.exit(f"ERROR: tail symbol {TAIL_SYMBOL!r} missing -- source looks truncated; aborting, no write.")
    if MARKER in data:
        print("Already patched -- ER_DUMP_SPHERES block present. No change.")
        return

    nl = b"\r\n" if b"\r\n" in data else b"\n"
    anchor = ANCHOR_LINE + nl
    n = data.count(anchor)
    if n != 1:
        sys.exit(f"ERROR: expected exactly 1 anchor ({ANCHOR_LINE!r}+newline), found {n}. Aborting.")

    block = nl.join(line.encode("utf-8") for line in BLOCK_LINES) + nl
    replace = anchor + block
    new = data.replace(anchor, replace, 1)
    if MARKER not in new or TAIL_SYMBOL not in new or len(new) != len(data) + len(block):
        sys.exit("ERROR: post-replace sanity check failed. Aborting (no write).")

    bak = TARGET + ".bak_dumpspheres"
    with open(bak, "wb") as f:
        f.write(data)
    with open(TARGET, "wb") as f:
        f.write(new)
    with open(TARGET, "rb") as f:
        chk = f.read()
    if MARKER not in chk or TAIL_SYMBOL not in chk or len(chk) != len(data) + len(block):
        sys.exit(f"ERROR: verification AFTER write FAILED. Restore from {bak}")

    print("OK: sphere-count dump inserted into fill_slot_data (gated by ER_DUMP_SPHERES).")
    print(f"  backup : {bak}")
    print(f"  size   : {size} -> {len(chk)} (+{len(chk) - size} bytes)")
    print("Run a gen with $env:ER_DUMP_SPHERES=1 to write Archipelago\\output\\ER_SPHERES_<seed>.txt")


if __name__ == "__main__":
    main()
