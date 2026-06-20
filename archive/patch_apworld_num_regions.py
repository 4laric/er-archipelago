#!/usr/bin/env python3
r"""patch_apworld_num_regions.py  --  add the `num_regions` option (random short capital run).

Run on Windows from the apworld eldenring dir, e.g.:
    cd <repo>\Archipelago\worlds\eldenring
    python ..\..\..\..\patch_apworld_num_regions.py

What it does (idempotent: re-running is a no-op if already applied):
  1. region_spine.py  -- append compute_num_regions_scope() + helpers (random subset of the
                         capital SPINE, Limgrave hub + Leyndell capstone always kept, great-rune
                         floor; warp reachability assumed -- the caller forces region_access=warp).
  2. options.py       -- add `class NumRegions(Range)` after RegionCount, and the
                         `num_regions: NumRegions` field in the EROptions dataclass.
  3. __init__.py      -- resolve num_regions in generate_early (after the godrick block, before the
                         lock-injection block) into the existing _spine_* seal fields; force
                         region_access=warp; capital goal + lock logic only.

CRLF-safe: each file is read as bytes, the per-file newline is detected, and the inserted text is
normalised to it before a byte-level splice. Nothing is written if an anchor is missing or the
patch is already present (the script reports and skips that file).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
# allow running from anywhere: locate the eldenring package
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
        print(f"  [FAIL] {name}: anchor not found -- NOT modified")
        return False
    cut = idx + len(anchor)
    ins = _conv(insert_text, nl)
    _write(p, b[:cut] + ins + b[cut:])
    print(f"  [ok]   {name}: inserted {marker}")
    return True


# ---------------------------------------------------------------------------
# 1) region_spine.py  -- append the new scope function at end of file.
# ---------------------------------------------------------------------------
REGION_SPINE_ANCHOR = """    sealed_regions = set(all_region_names) - kept_regions
    sealed_locks = set(all_lock_names) - kept_locks
    return kept_regions, sealed_regions, kept_locks, sealed_locks
"""

REGION_SPINE_INSERT = '''

# ===== num_regions (random short capital run) ===========================================
# A short "reach Leyndell and kill Morgott" run like region_count, but the kept overworld majors
# are a RANDOM subset instead of the deterministic first-N spine. Limgrave (the free sphere-1 hub)
# and the Leyndell / Morgott capstone are ALWAYS kept and both count toward num_regions; the middle
# majors (Weeping .. Mt. Gelmir) are rolled. A great-rune floor keeps enough great-rune bosses in
# scope to open Leyndell. Reachability is by WARP (the caller forces region_access=warp), so a
# non-contiguous random subset is still reachable from the Limgrave hub via each region's own lock.
# Everything not kept is sealed exactly like a region_count seal (lock pulled, checks -> events).
# See SPEC-num-regions.md.

# 1-based SPINE indices that are "middle" overworld majors eligible for the random roll
# (step 1 Limgrave is the always-kept free hub; the Leyndell capstone is the always-kept goal).
NUM_REGIONS_MIDDLE_STEPS: List[int] = [2, 3, 4, 5, 6, 7, 8]   # Weeping, Stormveil, Liurnia, Caelid, Dragonbarrow, Altus, Mt. Gelmir


def num_regions_floor(great_runes_required: int) -> int:
    """Lowest num_regions that keeps the capital reachable under WARP access.

    Limgrave + Leyndell (= 2) plus great_runes_required rune-boss majors. Unlike the geographic
    region_count floor there is NO Altus-route requirement (warp travel ignores adjacency).
    """
    if great_runes_required > MAX_PRE_LEYNDELL_RUNES:
        raise ValueError(
            f"num_regions capital goal needs great_runes_required <= {MAX_PRE_LEYNDELL_RUNES} "
            f"(only that many great-rune bosses exist before Leyndell); got {great_runes_required}."
        )
    return 2 + max(0, int(great_runes_required))


def compute_num_regions_scope(
    rng,
    num_regions: int,
    great_runes_required: int,
    all_region_names: Set[str],
    all_lock_names: Set[str],
) -> Tuple[Set[str], Set[str], Set[str], Set[str], int]:
    """Resolve a RANDOM short-capital seal scope.

    rng                  : a seeded RNG (world.random) -- the roll is reproducible per seed.
    num_regions          : option value (>= 1; caller gated on >0 + capital + lock logic).
    great_runes_required : option value, used for the rune-boss floor.
    all_region_names     : every AP region this seed (base [+ DLC]).
    all_lock_names       : every lock item that exists (item_table lock=True).

    Returns (kept_regions, sealed_regions, kept_locks, sealed_locks, effective_count), the same
    shape as compute_region_scope. effective_count is num_regions raised to num_regions_floor()
    (and capped at "all majors") when needed.
    """
    floor = num_regions_floor(great_runes_required)
    max_total = 2 + len(NUM_REGIONS_MIDDLE_STEPS)            # Limgrave + Leyndell + every middle
    effective = max(int(num_regions), floor)
    effective = min(effective, max_total)
    need_random = effective - 2                              # middle steps still to roll

    rune_steps = [s for s in NUM_REGIONS_MIDDLE_STEPS if s in RUNE_STEPS]
    nonrune_steps = [s for s in NUM_REGIONS_MIDDLE_STEPS if s not in RUNE_STEPS]

    # 1) guarantee the great-rune floor: pick great_runes_required rune-boss steps at random first.
    n_rune = min(int(great_runes_required), len(rune_steps), need_random)
    picked = list(rng.sample(rune_steps, n_rune)) if n_rune > 0 else []
    # 2) fill the remaining slots at random from whatever middle steps are left.
    rest_pool = [s for s in (rune_steps + nonrune_steps) if s not in picked]
    n_fill = min(max(0, need_random - len(picked)), len(rest_pool))
    if n_fill > 0:
        picked += list(rng.sample(rest_pool, n_fill))

    kept_steps = [SPINE[0]] + [SPINE[s - 1] for s in picked]   # SPINE[0] = Limgrave (free hub)
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

# ---------------------------------------------------------------------------
# 2a) options.py  -- NumRegions class after RegionCount.
# ---------------------------------------------------------------------------
OPTIONS_CLASS_ANCHOR = '''    display_name = "Region Count (Capital run)"
    range_start = 0
    range_end = 8
    default = 0
'''

OPTIONS_CLASS_INSERT = '''
class NumRegions(Range):
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
    default = 0
'''

# ---------------------------------------------------------------------------
# 2b) options.py  -- dataclass field after region_count.
# ---------------------------------------------------------------------------
OPTIONS_FIELD_ANCHOR = "    region_count: RegionCount\n"
OPTIONS_FIELD_INSERT = "    num_regions: NumRegions\n"

# ---------------------------------------------------------------------------
# 3) __init__.py  -- resolution block after the godrick block, before lock injection.
# ---------------------------------------------------------------------------
INIT_ANCHOR = '''                _kept_r, _sealed_r, _kept_l, _sealed_l = region_spine.compute_godrick_scope(
                    _all_regions, _all_locks,
                )
                self._spine_active = True
                self._spine_sealed_regions = _sealed_r
                self._spine_sealed_locks = _sealed_l
                self._spine_sealed_locations = {
                    loc.name for r in _sealed_r for loc in location_tables.get(r, [])
                }
'''

INIT_INSERT = '''
        # num_regions (SPEC-num-regions.md): a RANDOM short capital run -- keep `num_regions`
        # overworld majors chosen at random (Limgrave hub + Leyndell/Morgott capstone always in,
        # the middle majors rolled with a great-rune floor) and seal the rest. Same _spine_* seal
        # path as region_count; capital goal + lock logic only; forces region_access=warp so the
        # non-contiguous random subset is reachable from the Limgrave hub by each region's lock.
        if self.options.num_regions.value > 0:
            if self.options.ending_condition.value != 4:  # option_capital
                warning(f"{self.player_name}: num_regions needs ending_condition 'capital' "
                        f"(the goal boss must sit inside the kept set); ignoring num_regions.")
            elif self.options.world_logic.value not in (0, 2):
                warning(f"{self.player_name}: num_regions needs world_logic region_lock / "
                        f"region_lock_bosses (it seals regions via their lock items); ignoring it.")
            elif getattr(self, "_spine_active", False):
                warning(f"{self.player_name}: num_regions overlaps another region-seal goal "
                        f"(region_count/messmer/godrick); ignoring num_regions.")
            else:
                _all_regions = set(region_order)
                if self.options.enable_dlc:
                    _all_regions |= set(region_order_dlc)
                _all_locks = {n for n, d in item_table.items() if getattr(d, "lock", False)}
                try:
                    _kept_r, _sealed_r, _kept_l, _sealed_l, _eff = region_spine.compute_num_regions_scope(
                        self.random,
                        self.options.num_regions.value,
                        self.options.great_runes_required.value,
                        _all_regions, _all_locks,
                    )
                except ValueError as _e:
                    raise OptionError(f"{self.player_name}: {_e}")
                self._spine_active = True
                self._spine_sealed_regions = _sealed_r
                self._spine_sealed_locks = _sealed_l
                self._spine_effective_count = _eff
                self._spine_sealed_locations = {
                    loc.name for r in _sealed_r for loc in location_tables.get(r, [])
                }
                if self.options.region_access.value != 1:
                    self.options.region_access.value = 1
                    warning(f"{self.player_name}: num_regions forces region_access=warp "
                            f"(a random non-contiguous region set needs warp reachability).")
                if _eff != self.options.num_regions.value:
                    warning(f"{self.player_name}: num_regions {self.options.num_regions.value} "
                            f"raised to {_eff} so the capital (Morgott) stays reachable.")
'''


def main():
    print(f"Patching apworld in: {PKG}")
    ok = True
    ok &= splice_after("region_spine.py", REGION_SPINE_ANCHOR, REGION_SPINE_INSERT,
                       "compute_num_regions_scope")
    ok &= splice_after("options.py", OPTIONS_CLASS_ANCHOR, OPTIONS_CLASS_INSERT,
                       "class NumRegions")
    ok &= splice_after("options.py", OPTIONS_FIELD_ANCHOR, OPTIONS_FIELD_INSERT,
                       "num_regions: NumRegions")
    ok &= splice_after("__init__.py", INIT_ANCHOR, INIT_INSERT,
                       "SPEC-num-regions.md")
    print("DONE" if ok else "FINISHED WITH ERRORS (see [FAIL] above)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
