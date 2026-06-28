#!/usr/bin/env python3
"""HARD-MERGE region_count INTO num_regions (no back-compat alias -- pre-1.0, no users).

Deletes the RegionCount option, adds num_regions_order: {random(default), spine}, and routes
the num_regions branch to either the random roll (compute_num_regions_scope) or the fixed
first-N spine (compute_region_scope -- the old region_count path). spine keeps GEOGRAPHIC
access (contiguous first-N, like region_count); random force-enables warp. pool rune-source is
ignored under spine. region_spine.py is untouched (compute_region_scope stays); the slot_data
"region_count" key (internal wire name) stays.

Migration: yamls that used `region_count: N` now use `num_regions: N` + `num_regions_order: spine`.
er_yaml_lint flags a leftover `region_count` (unknown key).

Conventions: byte-level, CRLF-preserving, idempotent (re-runnable), py_compiles each file before
writing, writes .bak_nrmerge backups. Aborts cleanly (writes nothing) if any anchor drifted.
Run on Windows:  python patch_apworld_numregions_merge.py  then  .\build.ps1 -Apworld  + a gen.
"""
import os, sys, py_compile, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OPTIONS = os.path.join(HERE, "Archipelago", "worlds", "eldenring", "options.py")
INIT = os.path.join(HERE, "Archipelago", "worlds", "eldenring", "__init__.py")

# ---------------- options.py edits ----------------
OPT_A_OLD = '''class RegionCount(Range):
    """Number of regions to include for a short 'reach the capital and kill Morgott' run.

    Only takes effect with the **Capital** ending condition AND region gating (world_logic
    region_lock / region_lock_bosses). Keeps the first N steps of a fixed spine toward Morgott:

      1 Limgrave (free)  2 Weeping  3 Stormveil (Godrick)  4 Liurnia (Rennala)
      5 Caelid (Radahn)  6 Dragonbarrow  7 Altus  8 Mt. Gelmir / Volcano Manor (Rykard)

    Leyndell + Morgott are always the goal (gated by great_runes_required, not by this count).
    Every region NOT kept is sealed: its lock item is removed from the pool (unobtainable) and its
    checks become locked-vanilla events. The count is automatically raised to a floor that keeps
    Morgott reachable -- Altus (7) is the only route to Leyndell, and enough great-rune bosses must
    be in scope for great_runes_required. 0 = disabled (no sealing; the full world stays open)."""
    display_name = "Region Count (Capital run)"
    range_start = 0
    range_end = 8
    default = 0

'''

OPT_B_OLD = '''class NumRegions(Range):
    """Random short 'reach the capital and kill Morgott' run: keep this many overworld majors
    chosen AT RANDOM (instead of region_count's fixed first-N spine), and seal the rest.

    Limgrave (the free start hub) and Leyndell + Morgott (the goal capstone) are ALWAYS kept and
    both count toward this number; the middle majors are rolled per seed. A great-rune floor keeps
    enough great-rune bosses (Godrick / Rennala / Radahn / Rykard) in scope to open Leyndell, so
    the count is automatically raised if it is set too low. Forces region_access=warp -- a random
    non-contiguous set is reached by warping in on each region's own lock, not by walking.

    Only takes effect with the **Capital** ending condition AND region gating (world_logic
    region_lock / region_lock_bosses). 0 = disabled. ~4 gives a short (roughly 3-4 hour) run."""
    display_name = "Num Regions (random Capital run)"
    range_start = 0
    range_end = 9
    default = 0'''

OPT_B_NEW = '''class NumRegions(Range):
    """Short 'reach the capital and kill Morgott' run: keep this many overworld majors and seal
    the rest. num_regions_order chooses HOW the kept set is picked:

      rolled (default) -- N majors rolled at random; reached by warp (forces region_access=warp),
                          since a non-contiguous set has no walking route.
      spine            -- the fixed first-N steps of the spine toward Morgott (1 Limgrave,
                          2 Weeping, 3 Stormveil, 4 Liurnia, 5 Caelid, 6 Dragonbarrow, 7 Altus,
                          8 Volcano), reached geographically. This is the old region_count.

    Limgrave (the free start hub) and Leyndell + Morgott (the goal capstone) are ALWAYS kept and
    both count toward this number. A great-rune floor keeps enough great-rune bosses (Godrick /
    Rennala / Radahn / Rykard) in scope to open Leyndell, so the count is auto-raised if too low.

    Only takes effect with the **Capital** ending condition AND region gating (world_logic
    region_lock / region_lock_bosses). 0 = disabled. ~4 gives a short (roughly 3-4 hour) run."""
    display_name = "Num Regions (Capital run)"
    range_start = 0
    range_end = 9
    default = 0

class NumRegionsOrder(Choice):
    """How num_regions chooses which overworld majors to keep (only matters when num_regions > 0).

    - **rolled** (default): roll N majors at random; reached by warp (forces region_access=warp).
      The original num_regions behavior.
    - **spine**: keep the fixed first-N steps of the spine toward Morgott (Limgrave, Weeping,
      Stormveil, Liurnia, Caelid, Dragonbarrow, Altus, Volcano), reached geographically. This is
      the old region_count option, folded in here.

    Ignored unless num_regions > 0 (and, like num_regions, only under the Capital goal + lock
    logic). num_regions_rune_source: pool is ignored under spine (pool rolls a random set)."""
    display_name = "Num Regions Order"
    option_rolled = 0
    option_spine = 1
    default = 0'''

OPT_C_OLD = '''    region_access: RegionAccessLogic
    region_count: RegionCount
    num_regions: NumRegions
    num_regions_rune_source: NumRegionsRuneSource'''
OPT_C_NEW = '''    region_access: RegionAccessLogic
    num_regions: NumRegions
    num_regions_order: NumRegionsOrder
    num_regions_rune_source: NumRegionsRuneSource'''

OPT_D_OLD = '''    OptionGroup("Short Runs (Capital)", [
        GracesPerRegion,
        RegionCount,
        NumRegions,
        NumRegionsRuneSource,
        NumRegionsChain,
    ]),'''
OPT_D_NEW = '''    OptionGroup("Short Runs (Capital)", [
        GracesPerRegion,
        NumRegions,
        NumRegionsOrder,
        NumRegionsRuneSource,
        NumRegionsChain,
    ]),'''

OPTIONS_EDITS = [
    ("del", OPT_A_OLD, "class RegionCount(Range):"),
    ("sub", OPT_B_OLD, OPT_B_NEW, "class NumRegionsOrder(Choice):"),
    ("sub", OPT_C_OLD, OPT_C_NEW, "num_regions_order: NumRegionsOrder"),
    ("sub", OPT_D_OLD, OPT_D_NEW, "        NumRegionsOrder,"),
]

# ---------------- __init__.py edits ----------------
INIT_E6_OLD = '''        _capital_goal = self.options.ending_condition.value == 4  # option_capital
        _lock_logic = self.options.world_logic.value in (0, 2)    # region_lock / region_lock_bosses
        if self.options.region_count.value > 0:
            if not _capital_goal:
                warning(f"{self.player_name}: region_count is set but ending_condition is not "
                        f"'capital'; ignoring region_count (a smaller world would seal off the goal).")
            elif not _lock_logic:
                warning(f"{self.player_name}: region_count needs world_logic region_lock / "
                        f"region_lock_bosses (it seals regions via their lock items); ignoring it.")
            else:
                _all_regions = set(region_order)
                if self.options.enable_dlc:
                    _all_regions |= set(region_order_dlc)
                _all_locks = {n for n, d in item_table.items() if getattr(d, "lock", False)}
                try:
                    _kept_r, _sealed_r, _kept_l, _sealed_l, _eff = region_spine.compute_region_scope(
                        self.options.region_count.value,
                        self.options.great_runes_required.value,
                        _all_regions, _all_locks,
                    )
                except ValueError as _e:
                    raise OptionError(f"{self.player_name}: {_e}")
                self._spine_active = True
                self._spine_sealed_regions = _sealed_r
                self._spine_sealed_locks = _sealed_l
                self._spine_effective_count = _eff
                # Pre-compute the sealed-check NAME set for _is_location_available (cheap membership).
                self._spine_sealed_locations = {
                    loc.name for r in _sealed_r for loc in location_tables.get(r, [])
                }
                if _eff != self.options.region_count.value:
                    warning(f"{self.player_name}: region_count {self.options.region_count.value} "
                            f"raised to {_eff} so the capital (Morgott) stays reachable.")'''
INIT_E6_NEW = '''        # region_count was MERGED into num_regions (num_regions_order: spine; pre-1.0 hard removal).
        # The fixed first-N spine path now runs in the num_regions branch below, dispatched on
        # num_regions_order and still calling region_spine.compute_region_scope.'''

INIT_7A_OLD = '''            elif getattr(self, "_spine_active", False):
                warning(f"{self.player_name}: num_regions overlaps another region-seal goal "
                        f"(region_count/messmer/godrick); ignoring num_regions.")'''
INIT_7A_NEW = '''            elif getattr(self, "_spine_active", False):
                warning(f"{self.player_name}: num_regions overlaps another region-seal goal "
                        f"(messmer/godrick); ignoring num_regions.")'''

INIT_7B_OLD = '''                try:
                    _active_caves = region_spine.active_cave_steps(self.options.extra_region_locks.value)
                    _kept_r, _sealed_r, _kept_l, _sealed_l, _eff = region_spine.compute_num_regions_scope(
                        self.random,
                        self.options.num_regions.value,
                        self.options.great_runes_required.value,
                        _all_regions, _all_locks,
                        _active_caves,
                    )
                except ValueError as _e:
                    raise OptionError(f"{self.player_name}: {_e}")'''
INIT_7B_NEW = '''                _active_caves = region_spine.active_cave_steps(self.options.extra_region_locks.value)
                _spine_order = self.options.num_regions_order.value == 1  # option_spine (was region_count)
                try:
                    if _spine_order:
                        # spine: fixed first-N steps toward Morgott, reached geographically (the old
                        # region_count). No random roll, no cave-bundle split, no forced warp.
                        _kept_r, _sealed_r, _kept_l, _sealed_l, _eff = region_spine.compute_region_scope(
                            self.options.num_regions.value,
                            self.options.great_runes_required.value,
                            _all_regions, _all_locks,
                        )
                    else:
                        # random: roll N majors; reached by warp (forced below).
                        _kept_r, _sealed_r, _kept_l, _sealed_l, _eff = region_spine.compute_num_regions_scope(
                            self.random,
                            self.options.num_regions.value,
                            self.options.great_runes_required.value,
                            _all_regions, _all_locks,
                            _active_caves,
                        )
                except ValueError as _e:
                    raise OptionError(f"{self.player_name}: {_e}")'''

INIT_7C_OLD = '''                if self.options.region_access.value != 1:
                    self.options.region_access.value = 1
                    warning(f"{self.player_name}: num_regions forces region_access=warp "
                            f"(a random non-contiguous region set needs warp reachability).")'''
INIT_7C_NEW = '''                if not _spine_order and self.options.region_access.value != 1:
                    self.options.region_access.value = 1
                    warning(f"{self.player_name}: num_regions (random order) forces region_access=warp "
                            f"(a random non-contiguous region set needs warp reachability).")'''

INIT_7D_OLD = '''                if self.options.num_regions_rune_source.value == 1:  # option_pool'''
INIT_7D_NEW = '''                _pool_runes = self.options.num_regions_rune_source.value == 1  # option_pool
                if _pool_runes and _spine_order:
                    warning(f"{self.player_name}: num_regions_rune_source=pool is ignored under "
                            f"num_regions_order=spine (pool rolls a random non-contiguous set).")
                    _pool_runes = False
                if _pool_runes:'''

INIT_E8_OLD = '''            if getattr(self, "_spine_active", False):
                warning(f"{self.player_name}: random_start_region is set but a region-seal goal "
                        f"(capital/region_count/messmer/godrick) is active; ignoring it for now.")'''
INIT_E8_NEW = '''            if getattr(self, "_spine_active", False):
                warning(f"{self.player_name}: random_start_region is set but a region-seal goal "
                        f"(capital/num_regions/messmer/godrick) is active; ignoring it for now.")'''

INIT_EDITS = [
    ("sub", INIT_E6_OLD, INIT_E6_NEW, "region_count was MERGED into num_regions"),
    ("sub", INIT_7A_OLD, INIT_7A_NEW, "(messmer/godrick); ignoring num_regions."),
    ("sub", INIT_7B_OLD, INIT_7B_NEW, "_spine_order = self.options.num_regions_order.value == 1"),
    ("sub", INIT_7C_OLD, INIT_7C_NEW, "num_regions (random order) forces region_access=warp"),
    ("sub", INIT_7D_OLD, INIT_7D_NEW, "_pool_runes = self.options.num_regions_rune_source.value == 1"),
    ("sub", INIT_E8_OLD, INIT_E8_NEW, "(capital/num_regions/messmer/godrick) is active"),
]

def apply_edits(text, edits):
    for edit in edits:
        kind = edit[0]
        if kind == "sub":
            _, old, new, marker = edit
            if old in text:
                c = text.count(old)
                if c != 1:
                    raise SystemExit(f"ABORT: anchor appears {c}x (expected 1): {marker!r}")
                text = text.replace(old, new, 1)
            elif marker in text:
                print(f"  [skip] already applied: {marker[:48]!r}")
            else:
                raise SystemExit(f"ABORT: anchor NOT FOUND and not already applied: {marker[:48]!r}")
        elif kind == "del":
            _, old, sig = edit
            if old in text:
                c = text.count(old)
                if c != 1:
                    raise SystemExit(f"ABORT: del-anchor appears {c}x (expected 1): {sig!r}")
                text = text.replace(old, "", 1)
            elif sig in text:
                raise SystemExit(f"ABORT: del-anchor drifted (signature present, block changed): {sig!r}")
            else:
                print(f"  [skip] already removed: {sig!r}")
    return text

def patch_file(path, edits):
    raw = open(path, "rb").read()
    total = raw.count(b"\n"); eol_crlf = raw.count(b"\r\n") == total and total > 0
    text = raw.decode("utf-8")
    work = text.replace("\r\n", "\n") if eol_crlf else text
    new_work = apply_edits(work, edits)
    if new_work == work:
        print(f"  {os.path.basename(path)}: no change (already merged).")
        return
    out = (new_work.replace("\n", "\r\n") if eol_crlf else new_work).encode("utf-8")
    with tempfile.NamedTemporaryFile("wb", suffix=".py", delete=False) as tf:
        tf.write(out); tmp = tf.name
    try:
        py_compile.compile(tmp, doraise=True)
    finally:
        os.remove(tmp)
    open(path + ".bak_nrmerge", "wb").write(raw)
    open(path, "wb").write(out)
    print(f"  {os.path.basename(path)}: patched ({'CRLF' if eol_crlf else 'LF'}); backup -> {os.path.basename(path)}.bak_nrmerge")

def main():
    for p, e in ((OPTIONS, OPTIONS_EDITS), (INIT, INIT_EDITS)):
        if not os.path.isfile(p):
            print("ERROR target not found:", p); return 1
    print("patching options.py ..."); patch_file(OPTIONS, OPTIONS_EDITS)
    print("patching __init__.py ..."); patch_file(INIT, INIT_EDITS)
    print("done.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
