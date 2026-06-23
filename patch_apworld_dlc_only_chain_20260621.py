#!/usr/bin/env python3
r"""patch_apworld_dlc_only_chain_20260621.py

FEATURE (SPEC-dlc-only-chain.md, Phase 1 / Option A): chain the messmer mini-campaign.

`dlc_only` runs region_lock with Gravesite Plain as the free hub and the rest of the DLC gated
by per-region .lock items -- but with warp access every kept region opens from sphere ~1, so the
DLC is FLAT (hints / completion_scaling have no gradient). This patch makes the messmer kept-set
DLC locks form a LINEAR breadcrumb chain off the free Gravesite hub:

    Gravesite (free)  ->  link1  ->  link2  ->  ...  ->  Shadow Keep / Messmer (goal, pinned last)

Each gated link's lock is placed on the PRIOR link's main boss drop (Gravesite hosts link 1), so
you clear one region to open the next -- a 1..N sphere ramp. Reuses the proven base-chain host
selection + reachability filter; only adds a DLC-keyed parent/host map and a topological order.

SCOPE: engages only under `ending_condition: messmer` (which forces dlc_only on) with the new
opt-in `dlc_only_chain` toggle ON. Full-tree dlc_only (all 14 DLC locks) is Phase 2 (needs the
warp-grace coverage audit, SPEC  7.1) and is intentionally NOT engaged here -- a plain dlc_only
seed with dlc_only_chain ON but no messmer goal just warns + no-ops.

TOUCHES THREE FILES (transactional -- validates EVERY anchor before writing any):
  worlds/eldenring/options.py       -- DLCOnlyChain toggle + dataclass field
  worlds/eldenring/region_spine.py  -- DLC_CHAIN_LOCK_PARENT, DLC_CHAIN_HOST_REGIONS,
                                       compute_dlc_mini_chain_order()
  worlds/eldenring/__init__.py      -- chain state init, messmer-block order compute,
                                       inject-pull in the dlc_only block, _dlc_chain_host(),
                                       pre_fill breadcrumb placement

Idempotent (aborts if the MARKER is already present). CRLF-preserving. Byte-compiles each file
and self-restores from .bak on any failure.

RUN ON WINDOWS from the repo root:
    python patch_apworld_dlc_only_chain_20260621.py
    .\build.ps1 -Apworld -Generate     # then gen-test (see footer)
"""
import io, os, sys, py_compile, shutil

REPO_APWORLD = os.path.join("Archipelago", "worlds", "eldenring")
OPTIONS  = os.path.join(REPO_APWORLD, "options.py")
SPINE    = os.path.join(REPO_APWORLD, "region_spine.py")
INIT     = os.path.join(REPO_APWORLD, "__init__.py")
MARKER   = "dlc_only_chain"          # presence in options.py => already applied


# ---------------------------------------------------------------------------------------------
# Each edit is (anchor, replacement). The anchor must appear EXACTLY ONCE. Newlines are written
# with '\n' here and re-encoded to the file's own newline (CRLF/LF) at apply time.
# ---------------------------------------------------------------------------------------------

# ===== options.py ============================================================================
OPT_NEW_CLASS = '''class DLCOnlyChain(Toggle):
    """Chain the DLC-only (Land of Shadow) run into a linear lock breadcrumb so the AP fill
    spheres (and completion scaling) ramp 1..N instead of every kept DLC region opening from
    sphere 1.

    PHASE 1: only acts under the **Messmer** ending condition (which forces dlc_only on). The kept
    DLC slice -- Gravesite (free hub) -> Belurat / Ensis -> Scadu Altus -> Shadow Keep (Messmer) --
    is breadcrumbed: the first gated region's lock is found on a Gravesite boss, and each later
    region's lock is found on the PREVIOUS region's main boss, with Shadow Keep / Messmer pinned
    last. Off = the flat dlc_only roll (all kept regions reachable from sphere 1).

    A plain dlc_only seed (no Messmer goal) with this ON warns and no-ops: the full 14-lock DLC
    tree chain is Phase 2 (it needs the per-region warp-grace audit). See SPEC-dlc-only-chain.md."""
    display_name = "DLC-Only Chain (linear sphere ramp)"


'''

OPT_EDITS = [
    # 1) insert the class right after NumRegionsChain's last line.
    (
        '    display_name = "Num Regions Chain (linear sphere ramp)"\n',
        '    display_name = "Num Regions Chain (linear sphere ramp)"\n\n\n' + OPT_NEW_CLASS,
    ),
    # 2) register the field in the options dataclass, right after num_regions_chain.
    (
        '    num_regions_chain: NumRegionsChain\n',
        '    num_regions_chain: NumRegionsChain\n    dlc_only_chain: DLCOnlyChain\n',
    ),
]

# ===== region_spine.py =======================================================================
SPINE_NEW_BLOCK = '''

# ===== DLC-only chain (SPEC-dlc-only-chain.md) ==========================================
# Linearize the DLC region tree into a breadcrumb chain. The tree (root = the free Gravesite
# hub) is parent->child; a chain needs a single line, so we topologically order the kept locks
# (parent before child) and breadcrumb each onto the previous link's boss. Phase 1 only uses the
# messmer kept-set (Gravesite/Belurat/Ensis/Scadu Altus/Shadow Keep); the full 14-lock maps below
# are populated ready for Phase 2 (the whole dlc_only tree).

# lock -> its tree PARENT lock (None = child of the free Gravesite hub). Drives the topo order:
# a child lock's region only opens once its parent is reachable, so the parent must come first.
DLC_CHAIN_LOCK_PARENT: Dict[str, Optional[str]] = {
    "Belurat Lock":       None,                 # off Gravesite
    "Ellac Lock":         None,
    "Cerulean Lock":      "Ellac Lock",
    "Jagged Peak Lock":   None,                 # via Dragon's Pit (lock-free)
    "Charo's Lock":       "Jagged Peak Lock",
    "Ensis Lock":         None,
    "Scadu Altus Lock":   "Ensis Lock",
    "Rauh Base Lock":     "Scadu Altus Lock",
    "Ancient Ruins Lock": "Rauh Base Lock",
    "Shadow Keep Lock":   "Scadu Altus Lock",
    "Recluses' Lock":     "Shadow Keep Lock",
    "Abyssal Lock":       "Recluses' Lock",
    "Enir Ilim Lock":     "Shadow Keep Lock",   # pinned last under the full-tree (goal)
}

# lock -> the DLC AP region(s) whose boss drop hosts the NEXT link's lock (first = primary).
# "Gravesite Lock" hosts the FIRST gated link (the free root). All names verified present in
# locations.region_order_dlc.
DLC_CHAIN_HOST_REGIONS: Dict[str, List[str]] = {
    "Gravesite Lock":     ["Gravesite Plain", "Belurat Gaol", "Dragon's Pit"],
    "Belurat Lock":       ["Belurat", "Belurat Swamp"],
    "Ellac Lock":         ["Ellac River", "Rivermouth Cave"],
    "Cerulean Lock":      ["Cerulean Coast", "Stone Coffin Fissure"],
    "Jagged Peak Lock":   ["Jagged Peak", "Jagged Peak Foot"],
    "Charo's Lock":       ["Charo's Hidden Grave"],
    "Ensis Lock":         ["Castle Ensis", "Fog Rift Fort"],
    "Scadu Altus Lock":   ["Scadu Altus", "Bonny Gaol"],
    "Rauh Base Lock":     ["Rauh Base", "Scorpion River Catacombs"],
    "Ancient Ruins Lock": ["Ancient Ruins of Rauh"],
    "Shadow Keep Lock":   ["Shadow Keep", "Shadow Keep Storehouse", "Shadow Keep, West Rampart"],
    "Recluses' Lock":     ["Recluses' River", "Darklight Catacombs"],
    "Abyssal Lock":       ["Abyssal Woods", "Midra's Manse"],
    "Enir Ilim Lock":     ["Enir Ilim"],
}

# Locks pinned to the END of the chain (deepest = the goal region's gate).
DLC_CHAIN_PIN_LAST = "Shadow Keep Lock"     # Phase 1 (messmer): Shadow Keep holds Messmer
DLC_CHAIN_FREE_ROOT = "Gravesite Lock"      # always the free precollected hub


def compute_dlc_mini_chain_order(rng, kept_locks: Set[str]) -> List[str]:
    """Topologically order the messmer kept-set DLC locks into a linear breadcrumb chain.

    rng        : world.random (reproducible per seed).
    kept_locks : the kept-lock set from compute_dlc_mini_scope (includes Gravesite Lock).

    Returns the GATED links only (Gravesite Lock -- the free precollected hub -- is excluded):
    [l_1, ..., l_k] where l_1's lock is breadcrumbed onto a Gravesite boss and l_{i+1}'s onto
    l_i's boss. Parent-before-child is enforced via DLC_CHAIN_LOCK_PARENT (a child lock's region
    only opens once its parent is reachable); DLC_CHAIN_PIN_LAST is forced to the END (Messmer =
    the goal, the deepest region). Siblings are shuffled per seed. Mirrors
    compute_num_regions_chain_order but keyed on lock names + the DLC tree parent map."""
    nodes = set(kept_locks) - {DLC_CHAIN_FREE_ROOT}
    parent = {n: DLC_CHAIN_LOCK_PARENT.get(n) for n in nodes}
    pinned_last = DLC_CHAIN_PIN_LAST if DLC_CHAIN_PIN_LAST in nodes else None
    pool = nodes - ({pinned_last} if pinned_last else set())

    placed: List[str] = []
    placed_set: Set[str] = set()

    def _available() -> List[str]:
        out = []
        for n in pool:
            if n in placed_set:
                continue
            p = parent.get(n)
            # parent satisfied if: free root / outside the kept set / already placed.
            if p is None or p == DLC_CHAIN_FREE_ROOT or p not in nodes or p in placed_set:
                out.append(n)
        return sorted(out)   # deterministic base order before the rng pick

    while len(placed) < len(pool):
        avail = _available()
        if not avail:
            # Unsatisfiable parent / cycle (should not happen for the messmer tree); flush the
            # remainder in a stable order so generation never hangs.
            for n in sorted(pool - placed_set):
                placed.append(n)
                placed_set.add(n)
            break
        pick = rng.choice(avail)
        placed.append(pick)
        placed_set.add(pick)

    if pinned_last:
        placed.append(pinned_last)
    return placed
'''

SPINE_EDITS = [
    (
        # end of compute_dlc_mini_scope -> append the new block after it.
        '    kept_locks = set(DLC_MINI_KEPT_LOCKS) & set(all_lock_names)\n'
        '    sealed_locks = (set(dlc_lock_names) & set(all_lock_names)) - kept_locks\n'
        '    return kept_regions, sealed_regions, kept_locks, sealed_locks\n',
        '    kept_locks = set(DLC_MINI_KEPT_LOCKS) & set(all_lock_names)\n'
        '    sealed_locks = (set(dlc_lock_names) & set(all_lock_names)) - kept_locks\n'
        '    return kept_regions, sealed_regions, kept_locks, sealed_locks\n'
        + SPINE_NEW_BLOCK,
    ),
]

# ===== __init__.py ===========================================================================
INIT_CHAIN_STATE_INIT = '''        self._spine_active = False
        self._spine_sealed_regions = set()
        self._spine_sealed_locks = set()
        # dlc_only_chain (SPEC-dlc-only-chain.md) state -- set in the messmer scope block.
        self._dlc_chain = False
        self._dlc_chain_order = []
        self._dlc_chain_managed_locks = set()
'''

INIT_MESSMER_BLOCK = '''                _kept_r, _sealed_r, _kept_l, _sealed_l = region_spine.compute_dlc_mini_scope(
                    _dlc_regions, _all_locks, _dlc_locks,
                )
                self._spine_active = True
                self._spine_sealed_regions = _sealed_r
                self._spine_sealed_locks = _sealed_l
                self._spine_sealed_locations = {
                    loc.name for r in _sealed_r for loc in location_tables.get(r, [])
                }
'''

INIT_MESSMER_BLOCK_NEW = INIT_MESSMER_BLOCK + '''                # dlc_only_chain (SPEC-dlc-only-chain.md, Phase 1 / Option A): breadcrumb the
                # messmer kept-set DLC locks into a linear chain off the free Gravesite hub. We
                # only record the ORDER + managed-lock set here; placement happens in pre_fill
                # (needs created locations) and the inject=False de-pooling happens in the dlc_only
                # lock block below. No-op unless dlc_only_chain is on.
                if getattr(self.options, "dlc_only_chain", None) and self.options.dlc_only_chain.value:
                    self._dlc_chain = True
                    self._dlc_chain_order = region_spine.compute_dlc_mini_chain_order(
                        self.random, set(_kept_l))
                    self._dlc_chain_managed_locks = set(self._dlc_chain_order)
'''

INIT_DLCONLY_PULL = '''                    elif not getattr(item_table[item], "is_dlc", False):
                        # dlc_only: pull BASE-game region locks from the pool (sealed
                        # transit, no findable lock); DLC locks (is_dlc) stay injected.
                        # Count-neutral -- see the L1418 demand-drop comment.
                        item_table[item].inject = False
                # dlc_only: a DLC-only player has already cleared the base game, so DLC
'''

INIT_DLCONLY_PULL_NEW = '''                    elif not getattr(item_table[item], "is_dlc", False):
                        # dlc_only: pull BASE-game region locks from the pool (sealed
                        # transit, no findable lock); DLC locks (is_dlc) stay injected.
                        # Count-neutral -- see the L1418 demand-drop comment.
                        item_table[item].inject = False
                # dlc_only_chain (SPEC-dlc-only-chain.md): the chained kept DLC locks are placed by
                # hand on boss drops in pre_fill, so pull them from the RANDOM injectable pool here
                # (else they'd be randomly placed on top of the fixed breadcrumb). Gravesite is
                # already precollected above. Count-neutral (freed slot -> filler in create_items).
                if getattr(self, "_dlc_chain", False):
                    for _clk in getattr(self, "_dlc_chain_managed_locks", ()):
                        if _clk in item_table:
                            item_table[_clk].inject = False
                # dlc_only: a DLC-only player has already cleared the base game, so DLC
'''

INIT_HOST_METHOD = '''    def _dlc_chain_host(self, host_regions):
        """Pick a stable breadcrumb HOST location inside the given DLC `host_regions`.

        Same preference + reachability logic as _num_regions_chain_host, but parameterized on a
        region-name LIST (DLC chain links are keyed by lock name, not base-SPINE step). Prefers a
        remembrance / 'mainboss drop' boss, then any non-missable boss, then any non-missable
        check; filtered to hosts reachable under the chain placed SO FAR. Returns an ERLocation or
        None. (Consolidate with _num_regions_chain_host later -- SPEC-dlc-only-chain.md  5.2.)"""
        host_regions = list(host_regions or [])
        cands = []
        for _rn in host_regions:
            if _rn not in self.created_regions:
                continue
            try:
                _region = self.get_region(_rn)
            except Exception:
                continue
            cands.extend(_region.locations)
        cands = [l for l in cands if getattr(l, "address", None) is not None
                 and getattr(l, "item", None) is None]
        if not cands:
            return None
        try:
            _cs = CollectionState(self.multiworld)
            _cs.sweep_for_advancements()
            cands = [l for l in cands if l.can_reach(_cs)]
        except Exception as _e:
            warning(f"{self.player_name}: dlc chain-host reach filter skipped ({_e}).")
        if not cands:
            return None

        def _missable(l):
            return bool(getattr(getattr(l, "data", None), "missable", False))

        def _is_boss(l):
            return bool(getattr(getattr(l, "data", None), "boss", False)
                        or getattr(getattr(l, "data", None), "remembrance", False))

        for l in cands:
            d = getattr(l, "data", None)
            if (not _missable(l) and _is_boss(l)
                    and (getattr(d, "remembrance", False) or "mainboss drop" in l.name)):
                return l
        for l in cands:
            if not _missable(l) and _is_boss(l):
                return l
        nonmiss = sorted((l for l in cands if not _missable(l)), key=lambda l: l.name)
        if nonmiss:
            return nonmiss[0]
        return sorted(cands, key=lambda l: l.name)[0]

    def _num_regions_chain_host(self, step: int):
'''

INIT_PREFILL = '''    def pre_fill(self) -> None: #MARK: Pre-fill
        # num_regions_chain (SPEC-num-regions-chain.md, Track A): wire the linear breadcrumb.
'''

INIT_PREFILL_NEW = '''    def pre_fill(self) -> None: #MARK: Pre-fill
        # dlc_only_chain (SPEC-dlc-only-chain.md, Phase 1): breadcrumb the messmer kept-set DLC
        # locks into a linear chain off the free Gravesite hub. Each gated link's lock is placed
        # on the PRIOR link's boss drop (Gravesite hosts link 1). Locks were pulled from the
        # injectable pool in the dlc_only block, so there is no double placement. No-op otherwise.
        if getattr(self, "_dlc_chain", False) and getattr(self, "_dlc_chain_order", None):
            _prev_hosts = region_spine.DLC_CHAIN_HOST_REGIONS.get("Gravesite Lock", [])
            for _clk in self._dlc_chain_order:
                _host = self._dlc_chain_host(_prev_hosts)
                if _host is None or getattr(_host, "item", None) is not None:
                    warning(f"{self.player_name}: dlc_only_chain found no breadcrumb host for "
                            f"{_clk}; precollecting it instead (lost one chain sphere). "
                            f"SPEC-dlc-only-chain  7.")
                    self.multiworld.push_precollected(self.create_item(_clk))
                else:
                    _host.place_locked_item(self.create_item(_clk))
                _prev_hosts = region_spine.DLC_CHAIN_HOST_REGIONS.get(_clk, [])
            self._prune_unreachable_priority()
            return
        # num_regions_chain (SPEC-num-regions-chain.md, Track A): wire the linear breadcrumb.
'''

INIT_STATE_ANCHOR = (
    '        self._spine_active = False\n'
    '        self._spine_sealed_regions = set()\n'
    '        self._spine_sealed_locks = set()\n'
)

INIT_EDITS = [
    (INIT_STATE_ANCHOR, INIT_CHAIN_STATE_INIT),
    (INIT_MESSMER_BLOCK, INIT_MESSMER_BLOCK_NEW),
    (INIT_DLCONLY_PULL, INIT_DLCONLY_PULL_NEW),
    ('    def _num_regions_chain_host(self, step: int):\n', INIT_HOST_METHOD),
    (INIT_PREFILL, INIT_PREFILL_NEW),
]


# ---------------------------------------------------------------------------------------------
def _newline_of(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def _apply(path, edits, label):
    """Validate every anchor (exactly once) then apply. Returns the new text; raises on any miss."""
    with io.open(path, "r", encoding="utf-8", newline="") as f:
        raw = f.read()
    nl = _newline_of(raw)
    # Work in '\n' space, re-encode at the end.
    text = raw.replace("\r\n", "\n")
    for anchor, repl in edits:
        a = anchor.replace("\r\n", "\n")
        n = text.count(a)
        if n != 1:
            raise RuntimeError(f"[{label}] anchor not unique (found {n}x):\n----\n{a[:160]}\n----")
        text = text.replace(a, repl.replace("\r\n", "\n"), 1)
    return text.replace("\n", nl)


def main():
    for p in (OPTIONS, SPINE, INIT):
        if not os.path.isfile(p):
            print(f"ERROR: not found: {p} (run from the repo root).")
            return 2

    with io.open(OPTIONS, "r", encoding="utf-8", newline="") as f:
        if MARKER in f.read():
            print(f"Already applied (marker '{MARKER}' present in options.py). No-op.")
            return 0

    targets = [(OPTIONS, OPT_EDITS, "options.py"),
               (SPINE,   SPINE_EDITS, "region_spine.py"),
               (INIT,    INIT_EDITS, "__init__.py")]

    # 1) validate + compute all new texts BEFORE writing anything.
    new_texts = {}
    try:
        for path, edits, label in targets:
            new_texts[path] = _apply(path, edits, label)
    except Exception as e:
        print(f"ABORT (no files changed): {e}")
        return 1

    # 2) back up, write, byte-compile; restore all on any failure.
    backups = {}
    try:
        for path, _, label in targets:
            bak = path + ".bak_dlcchain"
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

    # 3) purge pycache so the runtime re-imports the patched modules.
    pc = os.path.join(REPO_APWORLD, "__pycache__")
    if os.path.isdir(pc):
        for fn in os.listdir(pc):
            try:
                os.remove(os.path.join(pc, fn))
            except OSError:
                pass
    print("\nOK. Applied dlc_only_chain (Phase 1 / messmer). Backups: *.bak_dlcchain")
    print("Next: .\\build.ps1 -Apworld -Generate  with a messmer + dlc_only_chain yaml (see footer).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# =============================================================================================
# GEN-TEST yaml (Archipelago\Players\ as the only EldenRing yaml), then .\build.ps1 -Generate:
#
#   EldenRing:
#     ending_condition: messmer      # forces dlc_only on, seals Enir Ilim
#     dlc_only_chain: true
#     world_logic: region_lock
#     location_pool: all             # avoid the trimmed-pool lock-spill (er-dlc-only-region-lock)
#     accessibility: minimal
#
# PASS =
#   * gen SUCCESS, no FillError;
#   * `precollected-to-start` lists only Gravesite Lock + the base prereqs (great runes / Crafting
#     Kit / Dragon Hearts) -- NOT Belurat/Ensis/Scadu Altus/Shadow Keep Locks (those are placed on
#     boss drops, not spilled). A "found no breadcrumb host" warning => that one link fell back to
#     precollect (acceptable, but investigate if more than one does);
#   * the spoiler shows the 4 chained locks each sitting on a boss drop in the PREVIOUS link's
#     region (Gravesite boss -> link1 lock, link1 boss -> link2 lock, ...), Shadow Keep last;
#   * ER_SPHERE_TIERS.txt (if completion_scaling on) shows a 1..N DLC gradient, not all sphere 1.
# Add a fill-regression yaml under gen-test/fill-regression-yamls/ once green.
# =============================================================================================
