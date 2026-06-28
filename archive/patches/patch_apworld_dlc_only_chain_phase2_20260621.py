#!/usr/bin/env python3
r"""patch_apworld_dlc_only_chain_phase2_20260621.py

FEATURE (SPEC-dlc-only-chain.md, Phase 2 / Option B): full-tree dlc_only chain.

Phase 1 chained only the messmer kept-set. Phase 2 makes `dlc_only_chain` work for a PLAIN
dlc_only run (no messmer goal): breadcrumb EVERY warp-chainable DLC lock into a single linear
chain off the free Gravesite hub, so all ~13 gated DLC regions open one-per-sphere (1..N) with
Enir Ilim / Messmer's Kindling pinned last.

GRACE AUDIT (done 2026-06-21): of the 15 DLC region locks, 14 have a warp-grace-bearing region in
grace_data.py and are chainable. The ONE exception is **Ellac Lock** (Ellac River) -- no entry in
grace_data OR the source grace_flags.tsv (shared m61 overworld tile). It is left a NORMAL
region_lock pool item: Ellac River hangs directly off the free Gravesite hub
(create_connection("Gravesite Plain","Ellac River")), so it is reached ON FOOT once the lock is
found -- no warp grace needed, minimal-accessibility-safe. Stone Coffin Lock (omitted from the
Phase 1 maps because messmer seals it) is added here.

PREREQ: patch_apworld_dlc_only_chain_20260621.py (Phase 1) must already be applied
(DLCOnlyChain + compute_dlc_mini_chain_order + _dlc_chain_host + pre_fill breadcrumb). This patch
reuses that machinery unchanged; it only adds the full-tree order + the plain-dlc_only engage path.

TOUCHES (transactional -- validates EVERY anchor before writing any):
  worlds/eldenring/region_spine.py  -- Stone Coffin Lock into the parent + host maps;
                                       DLC_CHAIN_GRACELESS_LOCKS; compute_dlc_full_chain_order()
  worlds/eldenring/__init__.py      -- engage the full-tree chain in the dlc_only block when
                                       dlc_only_chain is on and messmer did not already engage it

Idempotent (aborts if MARKER present). CRLF-preserving. Byte-compiles + self-restores on failure.

RUN ON WINDOWS from the repo root:
    python patch_apworld_dlc_only_chain_phase2_20260621.py
    .\build.ps1 -Apworld -Generate     # gen-test: dlc_only + dlc_only_chain, NO messmer (footer)
"""
import io, os, sys, py_compile, shutil

REPO_APWORLD = os.path.join("Archipelago", "worlds", "eldenring")
SPINE = os.path.join(REPO_APWORLD, "region_spine.py")
INIT  = os.path.join(REPO_APWORLD, "__init__.py")
MARKER = "compute_dlc_full_chain_order"


# ===== region_spine.py =======================================================================
SPINE_EDITS = [
    # 1) Stone Coffin Lock -> parent map (child of Cerulean in the DLC tree).
    (
        '    "Cerulean Lock":      "Ellac Lock",\n',
        '    "Cerulean Lock":      "Ellac Lock",\n'
        '    "Stone Coffin Lock":  "Cerulean Lock",\n',
    ),
    # 2) Stone Coffin Lock -> host map; drop Stone Coffin Fissure from Cerulean's hosts (it now
    #    has its own lock and is only reachable once that lock is collected).
    (
        '    "Cerulean Lock":      ["Cerulean Coast", "Stone Coffin Fissure"],\n',
        '    "Cerulean Lock":      ["Cerulean Coast"],\n'
        '    "Stone Coffin Lock":  ["Stone Coffin Fissure"],\n',
    ),
    # 3) graceless set + full-tree order fn, appended after compute_dlc_mini_chain_order.
    (
        '    if pinned_last:\n'
        '        placed.append(pinned_last)\n'
        '    return placed\n',
        '    if pinned_last:\n'
        '        placed.append(pinned_last)\n'
        '    return placed\n'
        '\n\n'
        '# Locks that gate a DLC region with NO warp grace in grace_data (shared m61 tile, absent\n'
        '# from the source grace_flags.tsv) -> cannot be a warp-reachable chain LINK. Left as normal\n'
        '# region_lock pool items, reached on foot (Ellac River hangs directly off the free Gravesite\n'
        '# hub). See SPEC-dlc-only-chain.md  7.1.\n'
        'DLC_CHAIN_GRACELESS_LOCKS: Set[str] = {"Ellac Lock"}\n'
        '\n'
        '# The full-tree chain\'s final goal link (deepest), pinned last.\n'
        'DLC_CHAIN_FULL_PIN_LAST = "Enir Ilim Lock"\n'
        '\n\n'
        'def compute_dlc_full_chain_order(rng, all_dlc_lock_names: Set[str]) -> List[str]:\n'
        '    """Topologically order EVERY warp-chainable DLC lock into a linear breadcrumb chain for\n'
        '    a PLAIN dlc_only run (Phase 2 / Option B). Excludes the free Gravesite hub and the\n'
        '    graceless locks (DLC_CHAIN_GRACELESS_LOCKS -- no warp grace, cannot be a warp link).\n'
        '    Enir Ilim Lock is pinned LAST (final goal). Parent-before-child via DLC_CHAIN_LOCK_PARENT\n'
        '    (a parent that is graceless / outside the set counts as satisfied, since warp reaches each\n'
        '    link by its own lock). Returns the gated link order [l_1..l_k]; l_1 is breadcrumbed onto a\n'
        '    Gravesite boss, l_{i+1} onto l_i\'s boss. Mirrors compute_dlc_mini_chain_order."""\n'
        '    nodes = (set(all_dlc_lock_names) & set(DLC_CHAIN_LOCK_PARENT)) - DLC_CHAIN_GRACELESS_LOCKS\n'
        '    nodes -= {DLC_CHAIN_FREE_ROOT}\n'
        '    parent = {n: DLC_CHAIN_LOCK_PARENT.get(n) for n in nodes}\n'
        '    pinned_last = DLC_CHAIN_FULL_PIN_LAST if DLC_CHAIN_FULL_PIN_LAST in nodes else None\n'
        '    pool = nodes - ({pinned_last} if pinned_last else set())\n'
        '    placed: List[str] = []\n'
        '    placed_set: Set[str] = set()\n'
        '\n'
        '    def _available() -> List[str]:\n'
        '        out = []\n'
        '        for n in pool:\n'
        '            if n in placed_set:\n'
        '                continue\n'
        '            p = parent.get(n)\n'
        '            if p is None or p == DLC_CHAIN_FREE_ROOT or p not in nodes or p in placed_set:\n'
        '                out.append(n)\n'
        '        return sorted(out)\n'
        '\n'
        '    while len(placed) < len(pool):\n'
        '        avail = _available()\n'
        '        if not avail:\n'
        '            for n in sorted(pool - placed_set):\n'
        '                placed.append(n)\n'
        '                placed_set.add(n)\n'
        '            break\n'
        '        pick = rng.choice(avail)\n'
        '        placed.append(pick)\n'
        '        placed_set.add(pick)\n'
        '\n'
        '    if pinned_last:\n'
        '        placed.append(pinned_last)\n'
        '    return placed\n',
    ),
]

# ===== __init__.py ===========================================================================
INIT_EDITS = [
    (
        '            if self.options.dlc_only:\n'
        '                for item in item_table:\n'
        '                    if not item_table[item].lock:\n'
        '                        continue\n',
        '            if self.options.dlc_only:\n'
        '                # dlc_only_chain full-tree (SPEC-dlc-only-chain.md, Phase 2 / Option B): if\n'
        '                # the chain is on but the messmer scope block did not already engage it\n'
        '                # (plain dlc_only, no messmer goal), breadcrumb EVERY warp-chainable DLC lock\n'
        '                # into one linear chain off the free Gravesite hub. Graceless locks (Ellac)\n'
        '                # stay normal pool items, reached on foot. Placement happens in pre_fill; the\n'
        '                # managed locks are pulled from inject in the Phase 1 block just below.\n'
        '                if (getattr(self.options, "dlc_only_chain", None)\n'
        '                        and self.options.dlc_only_chain.value\n'
        '                        and not getattr(self, "_dlc_chain", False)):\n'
        '                    _dlc_lock_names = {n for n, d in item_table.items()\n'
        '                                       if getattr(d, "lock", False)\n'
        '                                       and getattr(d, "is_dlc", False)}\n'
        '                    _full_order = region_spine.compute_dlc_full_chain_order(\n'
        '                        self.random, _dlc_lock_names)\n'
        '                    if _full_order:\n'
        '                        self._dlc_chain = True\n'
        '                        self._dlc_chain_order = _full_order\n'
        '                        self._dlc_chain_managed_locks = set(_full_order)\n'
        '                for item in item_table:\n'
        '                    if not item_table[item].lock:\n'
        '                        continue\n',
    ),
]


# ---------------------------------------------------------------------------------------------
def _newline_of(text): return "\r\n" if "\r\n" in text else "\n"


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
    for p in (SPINE, INIT):
        if not os.path.isfile(p):
            print(f"ERROR: not found: {p} (run from the repo root).")
            return 2

    with io.open(SPINE, "r", encoding="utf-8", newline="") as f:
        spine_src = f.read()
    if MARKER in spine_src:
        print(f"Already applied (marker '{MARKER}' present). No-op.")
        return 0
    if "compute_dlc_mini_chain_order" not in spine_src:
        print("ERROR: Phase 1 (patch_apworld_dlc_only_chain_20260621.py) is not applied. "
              "Apply it first.")
        return 2

    targets = [(SPINE, SPINE_EDITS, "region_spine.py"),
               (INIT, INIT_EDITS, "__init__.py")]

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
            bak = path + ".bak_dlcchainp2"
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

    pc = os.path.join(REPO_APWORLD, "__pycache__")
    if os.path.isdir(pc):
        for fn in os.listdir(pc):
            try:
                os.remove(os.path.join(pc, fn))
            except OSError:
                pass
    print("\nOK. Applied dlc_only_chain Phase 2 (full DLC tree). Backups: *.bak_dlcchainp2")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# =============================================================================================
# GEN-TEST yaml (Archipelago\Players\ as the only EldenRing yaml), then .\build.ps1 -Generate:
#
#   EldenRing:
#     dlc_only: true
#     dlc_only_chain: true
#     world_logic: region_lock
#     region_access: warp
#     graces_per_region: 0
#     location_pool: all
#     accessibility: minimal
#     # NOTE: no ending_condition (or a non-messmer one) -> exercises the Phase 2 full-tree path,
#     # NOT the Phase 1 messmer slice.
#
# PASS =
#   * gen SUCCESS, no FillError;
#   * `precollected-to-start` lists only Gravesite Lock + base prereqs -- NOT the 13 chained DLC
#     locks (each placed on a boss drop). Ellac Lock should appear as a normal pool placement
#     (in the spoiler), NOT precollected and NOT on a breadcrumb;
#   * the spoiler shows the chained locks each on a boss drop in the PREVIOUS link's region,
#     Enir Ilim Lock last;
#   * at most one "found no breadcrumb host" warning (investigate if more);
#   * ER_SPHERE_TIERS.txt (if completion_scaling+enemy_rando on) shows a 1..N DLC gradient.
# Add a fill-regression yaml under gen-test/fill-regression-yamls/ once green.
# =============================================================================================
