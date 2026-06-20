#!/usr/bin/env python3
r"""patch_apworld_num_regions_pool_runes.py  --  decouple the great-rune floor from region
selection in num_regions, and make num_regions use the Roundtable-hub re-root.

WHAT / WHY
==========
The existing `num_regions` option (patch_apworld_num_regions.py) picks a random subset of the
capital SPINE but is forced to keep enough great-rune BOSS regions in scope to open Leyndell
(`great_runes_required` rune-steps) AND to keep Altus (the only physical route). That couples the
"how many regions" knob to "which great runes exist", so a 1-region or 2-region run is impossible.

This patch adds a sub-option `num_regions_rune_source`:

  * regions (0, default) -- UNCHANGED. The rune floor + Altus force live in region selection exactly
                            as today (compute_num_regions_scope). Limgrave is the forced hub.
  * pool    (1)          -- DECOUPLE. Leyndell's gate is a pure ITEM COUNT (_has_enough_great_runes,
                            no region/tower dependency), so the great runes are injected back into
                            the pool as items instead of being kept as boss regions. The content
                            floor drops to just the always-kept set (Roundtable hub + Leyndell): a
                            1-middle-region run becomes legal. Limgrave is NO LONGER force-kept -- it
                            becomes a normal rollable/sealable middle, and the already-built
                            Roundtable-hub re-root makes the non-contiguous random set reachable by
                            warp (each region via its own lock; Limgrave via "Warp To Limgrave").

HOW (count-neutral rune injection)
==================================
Sealing a rune's boss region pulls that rune from the pool. In pool mode we INJECT the deficit back:
deficit = great_runes_required - (rune-steps still kept). For each deficit rune we flip
`item_table[name].inject = True`. The existing create_items demand-drop machinery
(injectable_mandatory_count -> drop a small-rune/filler slot per injectable) then frees one filler
slot per injected rune, so the pool stays COUNT-NEUTRAL with no manual filler bookkeeping here.
Candidate runes are the 4 base-spine great runes whose host region is SEALED, EXCLUDING Morgott's
Great Rune (it is the goal-side Leyndell drop and must stay where the goal logic expects it).

HOW TO RUN (Windows only -- the sandbox must NOT touch the apworld files)
=========================================================================
    cd <repo>\Archipelago\worlds\eldenring
    python ..\..\..\..\patch_apworld_num_regions_pool_runes.py

PRECONDITION: the working tree must contain the INTACT num_regions feature, i.e.
region_spine.compute_num_regions_scope() / NUM_REGIONS_MIDDLE_STEPS / num_regions_floor() and
options.NumRegions must exist (these come from patch_apworld_num_regions.py). If a previous mount
sync truncated region_spine.py / options.py / __init__.py, restore them first:
    git restore worlds/eldenring/region_spine.py worlds/eldenring/options.py worlds/eldenring/__init__.py
then re-apply the num_regions stack, then this patch. The patch reports [FAIL] and writes nothing
for any file whose anchor is missing.

Idempotent: re-running is a no-op (per-insertion marker check). CRLF-safe: each file is read as
bytes, the per-file newline is detected, and inserted text is normalised to it before a byte splice.
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
    # author inserts with '\n'; normalise to the file's newline
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
    if b.find(anchor, idx + 1) >= 0:
        print(f"  [FAIL] {name}: anchor is AMBIGUOUS (>1 match) -- NOT modified ({marker})")
        return False
    cut = idx + len(anchor)
    ins = _conv(insert_text, nl)
    _write(p, b[:cut] + ins + b[cut:])
    print(f"  [ok]   {name}: inserted {marker}")
    return True


# ===========================================================================================
# 1) options.py  --  NumRegionsRuneSource Choice, after the NumRegions class body.
# ===========================================================================================
OPTIONS_CLASS_ANCHOR = '''    display_name = "Num Regions (random Capital run)"
    range_start = 0
    range_end = 9
    default = 0
'''

OPTIONS_CLASS_INSERT = '''
class NumRegionsRuneSource(Choice):
    """Where the great runes that open Leyndell come from, under a num_regions Capital run.

    Leyndell's gate is a pure item count (it needs `great_runes_required` great runes, with NO
    region/tower dependency), so the runes can come from EITHER kept boss regions or the item pool.

    **regions** (default): the runes live on their boss in KEPT regions. num_regions is raised so
        enough rune bosses (and Altus, the only route) stay in scope -- the floor couples the region
        count to great_runes_required, so very small runs are impossible. Limgrave is the forced hub.

    **pool**: the runes are INJECTED into the item pool as items (count-neutral -- one filler slot is
        freed per injected rune) instead of being kept as boss regions. The region floor drops to
        just the always-kept set (Roundtable hub + Leyndell), so a 1-middle-region run is legal, and
        Limgrave is no longer force-kept (it becomes a normal rollable/sealable middle). The random
        non-contiguous set is reached by WARP via the Roundtable hub (each region by its own lock;
        Limgrave by 'Warp To Limgrave'). Only meaningful when num_regions > 0."""
    display_name = "Num Regions Rune Source"
    option_regions = 0
    option_pool = 1
    default = 0
'''

# ===========================================================================================
# 2) options.py  --  dataclass field, after `    num_regions: NumRegions`.
# ===========================================================================================
OPTIONS_FIELD_ANCHOR = "    num_regions: NumRegions\n"
OPTIONS_FIELD_INSERT = "    num_regions_rune_source: NumRegionsRuneSource\n"

# ===========================================================================================
# 3) region_spine.py  --  compute_num_regions_scope_pool(), a sibling of compute_num_regions_scope.
#    Anchored on the (unique) tail of compute_num_regions_scope so the new fn is appended right
#    after it. The existing `regions`-mode function is left completely untouched.
# ===========================================================================================
REGION_SPINE_ANCHOR = '''    kept_steps = [SPINE[0]] + [SPINE[s - 1] for s in picked]   # SPINE[0] = Limgrave (free hub)
    kept_regions: Set[str] = set(ALWAYS_OPEN_REGIONS) | set(GOAL_CAPSTONE_REGIONS)
    kept_locks: Set[str] = set()
    for step in kept_steps:
        kept_regions.update(step["regions"])
        kept_locks.update(step["locks"])

    # Only consider regions/locks that actually exist this seed.
    kept_regions &= (set(all_region_names) | set(ALWAYS_OPEN_REGIONS))
    kept_locks &= set(all_lock_names)

    sealed_regions = set(all_region_names) - kept_regions
    sealed_locks = set(all_lock_names) - kept_locks
    return kept_regions, sealed_regions, kept_locks, sealed_locks, effective
'''

REGION_SPINE_INSERT = '''

# ===== num_regions POOL rune-source (SPEC-num-regions-pool-runes.md) =====================
# Sibling of compute_num_regions_scope for num_regions_rune_source == pool. The great-rune floor
# is DROPPED (the runes are injected into the item pool by __init__.py, not kept as boss regions),
# and Limgrave is NOT force-kept -- ALL eight overworld majors (Limgrave + the seven middles) are a
# single rollable/sealable pool. The only always-kept content is the Roundtable hub + the Leyndell
# capstone, so the content floor is 1 middle region. Reachability is by WARP from the Roundtable hub
# (the caller forces region_access=warp and sets the Roundtable-hub re-root), so a non-contiguous
# random subset -- including a sealed Limgrave / Altus -- is still reachable via each region's lock.

# Every overworld major step (1-based SPINE index) is rollable in pool mode -- including Limgrave (1).
NUM_REGIONS_POOL_STEPS: List[int] = [1] + list(NUM_REGIONS_MIDDLE_STEPS)   # Limgrave + the seven middles


def compute_num_regions_scope_pool(
    rng,
    num_regions: int,
    all_region_names: Set[str],
    all_lock_names: Set[str],
) -> Tuple[Set[str], Set[str], Set[str], Set[str], int]:
    """Resolve a RANDOM short-capital seal scope with the great runes sourced from the POOL.

    rng              : a seeded RNG (world.random) -- the roll is reproducible per seed.
    num_regions      : option value (caller gated on >0 + capital + lock logic). Floored to 1.
    all_region_names : every AP region this seed (base [+ DLC]).
    all_lock_names   : every lock item that exists (item_table lock=True).

    Returns (kept_regions, sealed_regions, kept_locks, sealed_locks, effective_count), the same
    shape as compute_num_regions_scope. effective_count = number of overworld MIDDLE majors kept
    (>= 1), NOT counting the always-kept Roundtable hub or the Leyndell capstone. No great-rune
    floor and no Altus force -- the runes ride the pool and warp ignores adjacency.
    """
    max_total = len(NUM_REGIONS_POOL_STEPS)                  # every overworld major is rollable
    effective = max(int(num_regions), 1)                    # floor of 1 rolled major is fine
    effective = min(effective, max_total)

    picked = list(rng.sample(list(NUM_REGIONS_POOL_STEPS), effective))

    kept_steps = [SPINE[s - 1] for s in picked]             # NO forced SPINE[0]/Limgrave
    kept_regions: Set[str] = set(ALWAYS_OPEN_REGIONS) | set(GOAL_CAPSTONE_REGIONS)
    kept_locks: Set[str] = set()
    for step in kept_steps:
        kept_regions.update(step["regions"])
        kept_locks.update(step["locks"])

    # Only consider regions/locks that actually exist this seed.
    kept_regions &= (set(all_region_names) | set(ALWAYS_OPEN_REGIONS))
    kept_locks &= set(all_lock_names)

    sealed_regions = set(all_region_names) - kept_regions
    sealed_locks = set(all_lock_names) - kept_locks
    return kept_regions, sealed_regions, kept_locks, sealed_locks, effective


# 1-based SPINE step -> the great-rune ITEM whose boss lives in that step's region. Used by
# __init__.py to compute the deficit-rune injection in pool mode. Morgott's Great Rune is NOT here:
# it is the goal-side Leyndell mainboss drop and stays where the goal logic expects it.
NUM_REGIONS_STEP_GREAT_RUNE: Dict[int, str] = {
    3: "Godrick's Great Rune",          # Stormveil (Godrick)
    4: "Great Rune of the Unborn",      # Liurnia / Raya Lucaria (Rennala)
    5: "Radahn's Great Rune",           # Caelid (Radahn)
    8: "Rykard's Great Rune",           # Mt. Gelmir / Volcano Manor (Rykard)
}
'''

# ===========================================================================================
# 4) __init__.py  --  pool-mode resolution inside the num_regions branch. Re-runs the scope with
#    the pool function, decouples the runes, and injects the deficit. Inserted right after the
#    `_eff raised` warning of the existing num_regions block.
# ===========================================================================================
INIT_POOL_ANCHOR = '''                if _eff != self.options.num_regions.value:
                    warning(f"{self.player_name}: num_regions {self.options.num_regions.value} "
                            f"raised to {_eff} so the capital (Morgott) stays reachable.")
'''

INIT_POOL_INSERT = '''
                # num_regions_rune_source == pool (SPEC-num-regions-pool-runes.md): decouple the
                # great-rune floor from region selection. Re-run the scope with the POOL sibling
                # (no rune floor, no Altus force, Limgrave rollable), then inject the deficit great
                # runes back into the item pool so Leyndell's pure item-count gate is still met. The
                # Roundtable-hub re-root (set after the _random_start_region reset below) makes the
                # non-contiguous random set reachable by warp.
                if self.options.num_regions_rune_source.value == 1:  # option_pool
                    _kept_r, _sealed_r, _kept_l, _sealed_l, _eff = \\
                        region_spine.compute_num_regions_scope_pool(
                            self.random,
                            self.options.num_regions.value,
                            _all_regions, _all_locks,
                        )
                    self._spine_sealed_regions = _sealed_r
                    self._spine_sealed_locks = _sealed_l
                    self._spine_effective_count = _eff
                    self._spine_sealed_locations = {
                        loc.name for r in _sealed_r for loc in location_tables.get(r, [])
                    }
                    # Roundtable-hub re-root: arm the flag the existing random_start path keys on.
                    # Actually set self._random_start_region AFTER the unconditional reset below
                    # (it would otherwise be clobbered); record intent here.
                    self._num_regions_pool_reroot = True
                    # Inject the DEFICIT great runes (great_runes_required minus the rune bosses
                    # still in a KEPT region) into the pool. _kept_l holds the kept locks; a rune's
                    # step is kept iff its lock is kept. Candidates = the 4 base-spine runes in a
                    # SEALED step; Morgott's is excluded (goal-side). Flipping inject=True routes
                    # each rune through the create_items demand-drop -> a freed filler slot per
                    # rune keeps the pool count-neutral. Dedup so a rune is never injected twice.
                    _step_lock = region_spine.NUM_REGIONS_CHAIN_STEP_LOCK
                    _step_rune = region_spine.NUM_REGIONS_STEP_GREAT_RUNE
                    _kept_rune_steps = [s for s in _step_rune
                                        if _step_lock.get(s) in _kept_l]
                    _need = max(0, int(self.options.great_runes_required.value)
                                - len(_kept_rune_steps))
                    _sealed_rune_steps = [s for s in sorted(_step_rune)
                                          if s not in _kept_rune_steps]
                    _inject_runes = []
                    for _s in _sealed_rune_steps:
                        if len(_inject_runes) >= _need:
                            break
                        _rn = _step_rune[_s]
                        if _rn in item_table and _rn not in _inject_runes:
                            _inject_runes.append(_rn)
                    for _rn in _inject_runes:
                        item_table[_rn].inject = True
                    self._num_regions_pool_injected_runes = list(_inject_runes)
                    if _need > len(_inject_runes):
                        warning(f"{self.player_name}: num_regions pool rune-source could only "
                                f"source {len(_inject_runes)} of {_need} great runes from sealed "
                                f"base bosses; check great_runes_required vs available runes.")
                    warning(f"{self.player_name}: num_regions rune-source=pool -- kept {_eff} "
                            f"middle region(s), injecting great runes {sorted(_inject_runes)} "
                            f"into the pool (Roundtable hub, Limgrave rollable).")
'''

# ===========================================================================================
# 5) __init__.py  --  Roundtable-hub re-root for pool mode. The unconditional
#    `self._random_start_region = None` reset (just above this anchor) would clobber anything the
#    num_regions block set, so we set the re-root flag HERE, after that reset, gated on the intent
#    flag recorded in (4). The standard random_start_region option block below is skipped for
#    num_regions seeds (its YAML option is 0), so it will not re-clobber.
# ===========================================================================================
INIT_REROOT_ANCHOR = '''        if "Limgrave Lock" in item_table:
            item_table["Limgrave Lock"].inject = False
'''

INIT_REROOT_INSERT = '''        # num_regions pool-mode Roundtable re-root (SPEC-num-regions-pool-runes.md): the line above
        # just reset _random_start_region = None and Limgrave Lock inject = False. When num_regions
        # rune-source == pool we WANT the Roundtable-hub re-root (Limgrave is a normal locked region
        # reached by 'Warp To Limgrave'). Set the flag the re-root keys on (_random_start_region) to
        # the always-open hub region and inject Limgrave Lock. _region_lock_warp_access / create_regions
        # / the start-grace block all treat _random_start_region purely as a truthy re-root flag plus a
        # REGION_GRACE_POINTS lookup that harmlessly returns [] for "Roundtable Hold". The standard
        # random_start_region block below is skipped (its YAML option is 0 on num_regions seeds).
        if getattr(self, "_num_regions_pool_reroot", False):
            self._random_start_region = "Roundtable Hold"
            if "Limgrave Lock" in item_table:
                item_table["Limgrave Lock"].inject = True
'''


def main():
    print(f"Patching apworld in: {PKG}")
    ok = True
    ok &= splice_after("options.py", OPTIONS_CLASS_ANCHOR, OPTIONS_CLASS_INSERT,
                       "class NumRegionsRuneSource")
    ok &= splice_after("options.py", OPTIONS_FIELD_ANCHOR, OPTIONS_FIELD_INSERT,
                       "num_regions_rune_source: NumRegionsRuneSource")
    ok &= splice_after("region_spine.py", REGION_SPINE_ANCHOR, REGION_SPINE_INSERT,
                       "compute_num_regions_scope_pool")
    ok &= splice_after("__init__.py", INIT_POOL_ANCHOR, INIT_POOL_INSERT,
                       "SPEC-num-regions-pool-runes.md")
    ok &= splice_after("__init__.py", INIT_REROOT_ANCHOR, INIT_REROOT_INSERT,
                       "num_regions pool-mode Roundtable re-root")
    print("DONE" if ok else "FINISHED WITH ERRORS (see [FAIL] above)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
