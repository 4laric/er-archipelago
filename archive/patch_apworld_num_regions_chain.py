#!/usr/bin/env python3
r"""patch_apworld_num_regions_chain.py  --  add the `num_regions_chain` mode (Track A).

Forces the kept `num_regions` regions into a LINEAR lock-breadcrumb CHAIN so the AP fill
spheres become 1..N instead of all sphere-1. Opt-in; only meaningful with
`num_regions > 0` + `ending_condition: capital` + region_lock world_logic.

Run on Windows from the apworld eldenring dir (or repo root), e.g.:
    cd <repo>\Archipelago\worlds\eldenring
    python ..\..\..\..\patch_apworld_num_regions_chain.py

Mechanism (SPEC-num-regions-chain.md  3 / 5 / 6 Track A):
  * Order the kept regions: Limgrave is link 0 (free sphere-1 hub). The rolled middle
    majors form links 1..m, shuffled by the world rng, with Altus PINNED LAST among the
    middles (capstone tail: Altus -> Capital Outskirts -> Leyndell, Leyndell is great-rune
    gated, no lock). Leyndell is the terminus.
  * Breadcrumb each link's lock into its PREDECESSOR: the first middle's lock is precollected
    (free), and for every other middle M_{i+1} its region lock is PLACED on the prior link
    M_i's prominent boss-drop location (place_locked_item). So M_{i+1} only opens after you
    clear M_i  ->  sphere i+1.
  * Breadcrumbed + precollected locks LEAVE the random injectable pool (inject=False), so they
    are never randomly placed nor spilled to the start inventory. The freed pool slots take
    filler (count-neutral, handled by the existing create_items accounting).
  * Track A emits NO slot_data (Track B owns the four contract keys). Output guarantee:
    post-fill get_spheres() is a linear 1..N region ladder.

CRLF-safe / idempotent: each file is read as bytes, its own newline is detected, inserts are
normalised to it, and a unique marker guards re-application. Nothing is written if an anchor is
missing or the marker is already present (that file is reported and skipped).

Anchors used (all DISJOINT from Track B's `fill_slot_data` region):
  * region_spine.py : after compute_num_regions_scope()'s `return ... effective`  (end of fn)
  * options.py      : after the NumRegions class body  (the `default = 0` of NumRegions)
                      + after the `num_regions: NumRegions` dataclass field
  * __init__.py     : (a) after the num_regions scope-resolution block's last warning
                          (sets up self._num_regions_chain_* state in generate_early)
                      (b) after the spine-sealed-locks inject=False loop in the lock-injection
                          block (so kept breadcrumbed locks are de-injected AFTER inject=True)
                      (c) a brand-new pre_fill() method appended in the class (places the
                          breadcrumb locks once the regions/locations exist)
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CANDIDATES = [
    HERE,
    os.path.join(HERE, "Archipelago", "worlds", "eldenring"),
    os.getcwd(),
]
PKG = next((d for d in CANDIDATES if os.path.exists(os.path.join(d, "region_spine.py"))), None)
if not PKG:
    sys.exit("ERROR: could not find region_spine.py -- run from the eldenring apworld dir.")


def _nl(b: bytes) -> bytes:
    return b"\r\n" if b"\r\n" in b else b"\n"


def _read(name):
    p = os.path.join(PKG, name)
    with open(p, "rb") as f:
        return p, f.read()


def _write(p, data):
    with open(p, "wb") as f:
        f.write(data)


def _conv(text: str, nl: bytes) -> bytes:
    return text.replace("\n", nl.decode("ascii")).encode("utf-8")


def splice_after(name, anchor_text, insert_text, marker):
    """Insert insert_text immediately AFTER the first occurrence of anchor_text."""
    p, b = _read(name)
    nl = _nl(b)
    if marker.encode("utf-8") in b:
        print(f"  [skip] {name}: already patched ({marker})")
        return True
    anchor = _conv(anchor_text, nl)
    idx = b.find(anchor)
    if idx < 0:
        print(f"  [FAIL] {name}: anchor not found -- NOT modified ({marker})")
        return False
    cut = idx + len(anchor)
    ins = _conv(insert_text, nl)
    _write(p, b[:cut] + ins + b[cut:])
    print(f"  [ok]   {name}: inserted {marker}")
    return True


# ===========================================================================
# 1) region_spine.py  --  chain-order helper (appended after compute_num_regions_scope).
# ===========================================================================
# Anchor = the closing return of compute_num_regions_scope (unique in the file).
REGION_SPINE_ANCHOR = """    sealed_regions = set(all_region_names) - kept_regions
    sealed_locks = set(all_lock_names) - kept_locks
    return kept_regions, sealed_regions, kept_locks, sealed_locks, effective
"""

REGION_SPINE_INSERT = '''

# ===== num_regions CHAIN order (SPEC-num-regions-chain.md  3 / 5) ========================
# Track A: turn the kept num_regions middles into a linear lock-breadcrumb CHAIN so the AP
# fill spheres become 1..N. Limgrave is the free sphere-1 hub (link 0). The rolled middle
# majors are shuffled by the world rng, with Altus PINNED LAST among the middles (capstone
# tail: Altus -> Capital Outskirts -> Leyndell; Leyndell is great-rune gated, has no lock and
# is the terminus). __init__.py consumes this order: it precollects the first middle's lock and
# breadcrumbs every later middle's lock onto the PRIOR middle's prominent boss drop.

# Per (1-based) middle SPINE step: the region whose boss hosts the NEXT link's lock, and the
# lock item this step contributes to the chain (the one gating its overworld region under
# region_lock / REGION_LOCK_ITEM). The host REGION is resolved dynamically in __init__.py from
# this region's actual locations (prefer a remembrance/prominent boss drop, then any
# non-missable boss drop, then any non-missable check), so a region without a great-rune
# remembrance (Weeping / Dragonbarrow / Altus) still gets a stable host. Only the LOCK NAME and
# the candidate host-region NAMES are fixed here.
NUM_REGIONS_CHAIN_STEP_LOCK: Dict[int, str] = {
    2: "Weeping Lock",
    3: "Stormveil Lock",
    4: "Liurnia Lock",
    5: "Caelid Lock",
    6: "Dragonbarrow Lock",
    7: "Altus Lock",
    8: "Mt. Gelmir Lock",
}

# The overworld AP region(s) whose checks/bosses belong to each middle step, used by __init__.py
# to find a breadcrumb HOST location. First name is the primary (where the prominent boss lives);
# the rest are fallbacks searched in order if the primary has no usable host.
NUM_REGIONS_CHAIN_STEP_HOST_REGIONS: Dict[int, List[str]] = {
    2: ["Weeping Peninsula"],
    3: ["Stormveil Throne", "Stormveil Castle", "Stormveil Start"],
    4: ["Raya Lucaria Academy Library", "Raya Lucaria Academy", "Liurnia of The Lakes"],
    5: ["Caelid", "Wailing Dunes"],
    6: ["Dragonbarrow"],
    7: ["Altus Plateau"],
    8: ["Volcano Manor", "Mt. Gelmir"],
}


def _kept_middle_steps(kept_locks: Set[str]) -> List[int]:
    """Which 1-based middle SPINE steps are kept, derived from the kept-lock set.

    A middle step is 'kept' iff its chain lock is in kept_locks (compute_num_regions_scope put
    every kept step's locks into kept_locks). Returns them in ascending SPINE order.
    """
    return [s for s in sorted(NUM_REGIONS_CHAIN_STEP_LOCK)
            if NUM_REGIONS_CHAIN_STEP_LOCK[s] in kept_locks]


def compute_num_regions_chain_order(rng, kept_locks: Set[str]) -> List[int]:
    """Order the kept MIDDLE steps into the chain sequence (1-based SPINE indices).

    rng        : world.random (reproducible per seed).
    kept_locks : the kept-lock set returned by compute_num_regions_scope.

    Returns [m_1, m_2, ..., m_k] where the regions open in that order off the Limgrave hub:
    m_1's lock is free (precollected), m_{i+1}'s lock is breadcrumbed onto m_i's boss. Altus
    (step 7) is forced to the END (capstone tail). Dragonbarrow (step 6) is kept ADJACENT to and
    IMMEDIATELY AFTER Caelid (step 5) when both are kept -- Dragonbarrow has no own hub warp
    (absent from REGION_LOCK_ITEM); it is reached by warping to Caelid then walking in with the
    Dragonbarrow Lock, so it must sit right behind Caelid in the chain to stay reachable. The
    remaining middles are shuffled. (If Dragonbarrow is kept WITHOUT Caelid -- possible because
    compute_num_regions_scope does not couple them -- it is ordered normally and flagged by the
    caller; that combo needs a gen-test, see SPEC  9.)
    """
    middles = _kept_middle_steps(kept_locks)
    altus = ALTUS_STEP if ALTUS_STEP in middles else None
    rest = [s for s in middles if s != altus]
    rng.shuffle(rest)
    # Keep Dragonbarrow (6) directly after Caelid (5) when both present.
    if 6 in rest and 5 in rest:
        rest = [s for s in rest if s != 6]
        ci = rest.index(5)
        rest.insert(ci + 1, 6)
    order = rest + ([altus] if altus is not None else [])
    return order
'''

# ===========================================================================
# 2a) options.py  --  NumRegionsChain toggle class (after the NumRegions class body).
# ===========================================================================
OPTIONS_CLASS_ANCHOR = '''    display_name = "Num Regions (random Capital run)"
    range_start = 0
    range_end = 9
    default = 0
'''

OPTIONS_CLASS_INSERT = '''
class NumRegionsChain(Toggle):
    """Chain the random num_regions Capital run into a linear lock breadcrumb so the difficulty
    (and AP fill spheres) ramp 1..N instead of every region opening from sphere 1.

    With this ON, the kept regions form a single line off the Limgrave hub: the first region's
    lock is free, and every later region's lock is found on the PREVIOUS region's main boss --
    so you clear region 1 to open region 2, clear region 2 to open region 3, and so on, up to
    Altus -> Leyndell -> Morgott. Altus is always the last link before the capital. Sphere-ordered
    completion scaling can then tier each region by its depth in the chain.

    Only meaningful with `num_regions > 0`, the **Capital** ending condition, and region gating
    (world_logic region_lock / region_lock_bosses); ignored otherwise. Off = the flat num_regions
    roll (all kept regions reachable from sphere 1)."""
    display_name = "Num Regions Chain (linear sphere ramp)"
'''

# ===========================================================================
# 2b) options.py  --  dataclass field after num_regions.
# ===========================================================================
OPTIONS_FIELD_ANCHOR = "    num_regions: NumRegions\n"
OPTIONS_FIELD_INSERT = "    num_regions_chain: NumRegionsChain\n"

# ===========================================================================
# 3a) __init__.py  --  resolve the chain order at the END of the num_regions scope block.
#     Anchor = that block's final raised-count warning (unique to the num_regions block).
# ===========================================================================
INIT_RESOLVE_ANCHOR = '''                if _eff != self.options.num_regions.value:
                    warning(f"{self.player_name}: num_regions {self.options.num_regions.value} "
                            f"raised to {_eff} so the capital (Morgott) stays reachable.")
'''

INIT_RESOLVE_INSERT = '''
                # num_regions_chain (SPEC-num-regions-chain.md, Track A): force the kept middles
                # into a linear lock-breadcrumb chain so the fill spheres ramp 1..N. We only record
                # the ORDER + the chain locks here; the actual placement happens in pre_fill (after
                # locations exist) and the inject=False de-pooling happens in the lock-injection
                # block below. _spine_active is already True (this is inside the num_regions branch).
                self._num_regions_chain = bool(self.options.num_regions_chain.value)
                if self._num_regions_chain:
                    _chain_order = region_spine.compute_num_regions_chain_order(self.random, _kept_l)
                    self._num_regions_chain_order = _chain_order
                    # The chain locks = every kept middle's chain lock. The FIRST link's lock is
                    # free (precollected); the rest are breadcrumbed onto the prior link's boss.
                    _chain_locks = [region_spine.NUM_REGIONS_CHAIN_STEP_LOCK[s] for s in _chain_order]
                    self._num_regions_chain_free_lock = _chain_locks[0] if _chain_locks else None
                    self._num_regions_chain_breadcrumb_locks = set(_chain_locks[1:])
                    # Breadcrumb host map filled in pre_fill (needs created locations); for the
                    # inject pass we only need the set of locks that LEAVE the random pool.
                    self._num_regions_chain_managed_locks = set(_chain_locks)
                    if 6 in _chain_order and 5 not in _chain_order:
                        warning(f"{self.player_name}: num_regions_chain kept Dragonbarrow without "
                                f"Caelid; Dragonbarrow has no hub warp, so it may be unreachable "
                                f"under warp access -- gen-test this seed (SPEC-num-regions-chain  9).")
'''

# ===========================================================================
# 3b) __init__.py  --  de-pool the chain locks in the lock-injection block.
#     Anchor = the spine-sealed-locks inject=False loop (runs AFTER inject=True for all locks).
# ===========================================================================
INIT_INJECT_ANCHOR = '''            if self._spine_active:
                for _lk in self._spine_sealed_locks:
                    if _lk in item_table:
                        item_table[_lk].inject = False
'''

INIT_INJECT_INSERT = '''            # num_regions_chain (Track A): the breadcrumbed + precollected chain locks are
            # placed by hand (pre_fill / push_precollected), so pull them from the RANDOM injectable
            # pool -- otherwise they would be randomly placed (or spilled to start) on TOP of the
            # fixed placement. create_items keeps the pool count-neutral (the freed slot -> filler).
            if getattr(self, "_num_regions_chain", False):
                for _lk in getattr(self, "_num_regions_chain_managed_locks", ()):  # free + breadcrumb
                    if _lk in item_table:
                        item_table[_lk].inject = False
'''

# ===========================================================================
# 3c) __init__.py  --  initialise chain state in generate_early (before any block reads it),
#     anchored on the existing _spine_* init line so it sits beside the other spine defaults.
# ===========================================================================
INIT_DEFAULTS_ANCHOR = "        self._spine_effective_count = 0\n"
INIT_DEFAULTS_INSERT = '''        # num_regions_chain (SPEC-num-regions-chain.md, Track A) -- inert unless engaged below.
        self._num_regions_chain = False
        self._num_regions_chain_order = []
        self._num_regions_chain_free_lock = None
        self._num_regions_chain_breadcrumb_locks = set()
        self._num_regions_chain_managed_locks = set()
'''

# ===========================================================================
# 3d) __init__.py  --  new pre_fill() that precollects link-1's lock and breadcrumbs the rest
#     onto each prior link's boss drop. Inserted at the end of _filler_replacement_name (the
#     method just before set_rules), so set_rules stays intact -- anchoring AFTER the def line
#     of set_rules would split set_rules from its body.
# ===========================================================================
INIT_PREFILL_ANCHOR = "        return self.random.choices(names, weights=weights, k=1)[0]\n"
INIT_PREFILL_INSERT = '''
    def _num_regions_chain_host(self, step: int):
        """Pick a stable breadcrumb HOST location inside a chain middle `step`.

        Prefers, among that step's host regions (region_spine.NUM_REGIONS_CHAIN_STEP_HOST_REGIONS):
          1. a prominent remembrance / 'mainboss drop' boss location,
          2. any non-missable boss drop,
          3. any non-missable real (addressed) check.
        Returns an ERLocation, or None if the step has no usable host this seed.
        """
        host_regions = region_spine.NUM_REGIONS_CHAIN_STEP_HOST_REGIONS.get(step, [])
        # Gather this step's actual locations from the created regions.
        cands = []
        for _rn in host_regions:
            if _rn not in self.created_regions:
                continue
            try:
                _region = self.get_region(_rn)
            except Exception:
                continue
            cands.extend(_region.locations)
        cands = [l for l in cands if getattr(l, "address", None) is not None]
        if not cands:
            return None

        def _missable(l):
            return bool(getattr(getattr(l, "data", None), "missable", False))

        def _is_boss(l):
            return bool(getattr(getattr(l, "data", None), "boss", False)
                        or getattr(getattr(l, "data", None), "remembrance", False))

        # 1) prominent remembrance / mainboss-drop boss.
        for l in cands:
            d = getattr(l, "data", None)
            if (not _missable(l) and _is_boss(l)
                    and (getattr(d, "remembrance", False) or "mainboss drop" in l.name)):
                return l
        # 2) any non-missable boss drop.
        for l in cands:
            if not _missable(l) and _is_boss(l):
                return l
        # 3) any non-missable real check (stable, deterministic by name).
        nonmiss = sorted((l for l in cands if not _missable(l)), key=lambda l: l.name)
        if nonmiss:
            return nonmiss[0]
        # 4) last resort: any real check.
        return sorted(cands, key=lambda l: l.name)[0]

    def pre_fill(self) -> None: #MARK: Pre-fill
        # num_regions_chain (SPEC-num-regions-chain.md, Track A): wire the linear breadcrumb.
        # The first chain link's lock is precollected (free -> that region is sphere 1 off the
        # hub); every later link's lock is PLACED on the prior link's boss drop, so the chain
        # opens one region per sphere. These locks were pulled from the random injectable pool in
        # the lock-injection block, so there is no double placement. NO-OP unless chain is engaged.
        if not getattr(self, "_num_regions_chain", False):
            return
        _order = getattr(self, "_num_regions_chain_order", [])
        if not _order:
            return
        # link 1 lock: free.
        _free = getattr(self, "_num_regions_chain_free_lock", None)
        if _free and _free in item_table:
            self.multiworld.push_precollected(self.create_item(_free))
        # links 2..k: breadcrumb each onto the PRIOR link's boss drop.
        for _i in range(1, len(_order)):
            _prev_step = _order[_i - 1]
            _lock_name = region_spine.NUM_REGIONS_CHAIN_STEP_LOCK.get(_order[_i])
            if not _lock_name or _lock_name not in item_table:
                continue
            _host = self._num_regions_chain_host(_prev_step)
            if _host is None:
                # No usable host in the predecessor: precollect the lock so the chain does not
                # softlock (it just loses one sphere of ramp). Flagged for gen-test.
                warning(f"{self.player_name}: num_regions_chain found no breadcrumb host in spine "
                        f"step {_prev_step}; precollecting {_lock_name} instead (lost one chain "
                        f"sphere). SPEC-num-regions-chain  9.")
                self.multiworld.push_precollected(self.create_item(_lock_name))
                continue
            _host.place_locked_item(self.create_item(_lock_name))

'''


def main():
    print(f"Patching apworld in: {PKG}")
    ok = True
    ok &= splice_after("region_spine.py", REGION_SPINE_ANCHOR, REGION_SPINE_INSERT,
                       "compute_num_regions_chain_order")
    ok &= splice_after("options.py", OPTIONS_CLASS_ANCHOR, OPTIONS_CLASS_INSERT,
                       "class NumRegionsChain")
    ok &= splice_after("options.py", OPTIONS_FIELD_ANCHOR, OPTIONS_FIELD_INSERT,
                       "num_regions_chain: NumRegionsChain")
    ok &= splice_after("__init__.py", INIT_DEFAULTS_ANCHOR, INIT_DEFAULTS_INSERT,
                       "_num_regions_chain_managed_locks = set()")
    ok &= splice_after("__init__.py", INIT_RESOLVE_ANCHOR, INIT_RESOLVE_INSERT,
                       "SPEC-num-regions-chain.md, Track A): force the kept middles")
    ok &= splice_after("__init__.py", INIT_INJECT_ANCHOR, INIT_INJECT_INSERT,
                       "_num_regions_chain_managed_locks\", ()):  # free + breadcrumb")
    ok &= splice_after("__init__.py", INIT_PREFILL_ANCHOR, INIT_PREFILL_INSERT,
                       "def pre_fill(self) -> None: #MARK: Pre-fill")
    print("DONE" if ok else "FINISHED WITH ERRORS (see [FAIL] above)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
