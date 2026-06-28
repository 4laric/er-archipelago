#!/usr/bin/env python3
"""patch_apworld_caves_chainable.py

FEATURE: make the four cave bundles behave like Stormveil -- a sub-region that is its OWN
selectable + chainable num_regions step. When a bundle's extra_region_locks key is active:
  * its minor dungeons SPLIT OUT of their parent overworld spine step into a standalone step
    (synthetic indices 9-12, past len(SPINE)=8);
  * that step COMPETES with the overworld majors for the num_regions slots (compete model);
  * with num_regions_chain it can be ANY link in the chain, reached by WARP (its torch lights
    the cluster's entrance graces; grace_data.BUNDLE_LOCK_GRACES + _BUNDLE_WARP), so a route
    like  Liurnia -> <a caves link> -> ... -> Altus  is expressible.

Bundles handled (the four existing ones; Caelid caves / Snowfield split are a separate TODO):
  limgrave_underground (Spelunker's Torch)            parent SPINE 1 (Limgrave hub)
  liurnia_caves        (Spelunker's Ghostflame Torch) parent SPINE 4 (Liurnia)
  altus_caves          (Spelunker's Steel-Wire Torch) parent SPINE 7 (Altus)
  mountaintops_caves   (Spelunker's Beast-Repellent Torch) no SPINE parent (always sealed before)

Touches: worlds/eldenring/region_spine.py and worlds/eldenring/__init__.py
Transactional: validates EVERY anchor before writing either file. Idempotent.

RUN ON WINDOWS (repo root), AFTER patch_apworld_limgrave_caves_alias.py:
    python patch_apworld_caves_chainable.py
    .\build.ps1 -Randomizer -Generate     # gen-test before baking
Expect (num_regions seed with e.g. extra_region_locks: [liurnia_caves, altus_caves]):
  the cave torches appear as progression chain links competing for the N slots, the chosen
  cave dungeons are reachable (warp), unchosen ones seal cleanly, no FillError.
"""
import io, os, sys

SPINE_PY = os.path.join("Archipelago", "worlds", "eldenring", "region_spine.py")
INIT_PY  = os.path.join("Archipelago", "worlds", "eldenring", "__init__.py")


def _read(path):
    if not os.path.isfile(path):
        sys.exit(f"ERROR: {path} not found. Run from the repo root (where Archipelago\\ lives).")
    with io.open(path, "r", encoding="utf-8") as f:
        return f.read()


def repl(src, old, new, label, marker):
    """Exact single replacement. If marker already present -> treat as applied (no-op)."""
    if marker in src:
        print(f"  [skip] {label} (already applied)")
        return src, False
    n = src.count(old)
    if n != 1:
        sys.exit(f"ERROR: anchor for '{label}' found {n} times (expected 1). Source drifted; "
                 f"aborting with NO files written.")
    return src.replace(old, new, 1), True


# ============================ region_spine.py ============================
spine = _read(SPINE_PY)
changed_spine = False

# --- R1: append cave-bundle data + helper (resolved at call time, so end-of-file is fine) ---
APPEND_MARK = "CAVE_BUNDLE_STEPS: Dict[int, Dict]"
APPEND_BLOCK = '''

# ===== Cave-bundle steps (chainable minor-dungeon clusters) ==============================
# When a cave bundle's extra_region_locks key is active under num_regions, the cluster SPLITS
# OUT of its parent overworld spine step into its own selectable + chainable step (synthetic
# 1-based indices past len(SPINE)=8). It then COMPETES with the overworld majors for the
# num_regions slots and, with num_regions_chain, can be any link in the chain -- reached by warp
# (its torch lights the cluster's entrance graces; see grace_data.BUNDLE_LOCK_GRACES and the
# _BUNDLE_WARP block in __init__). parent = the SPINE index whose regions list holds these
# dungeons (None = not in SPINE, e.g. Mountaintops/Snowfield, so nothing to split out).
CAVE_BUNDLE_STEPS: Dict[int, Dict] = {
    9: {
        "key": "limgrave_underground", "name": "Limgrave Underground",
        "lock": "Spelunker's Torch", "parent": 1,
        "regions": ["Fringefolk Hero's Grave", "Coastal Cave", "Church of Dragon Communion",
                    "Groveside Cave", "Stormfoot Catacombs", "Limgrave Tunnels", "Murkwater Cave",
                    "Murkwater Catacombs", "Highroad Cave", "Deathtouched Catacombs"],
    },
    10: {
        "key": "liurnia_caves", "name": "Liurnia Caves",
        "lock": "Spelunker's Ghostflame Torch", "parent": 4,
        "regions": ["Stillwater Cave", "Lakeside Crystal Cave", "Academy Crystal Cave",
                    "Road's End Catacombs", "Black Knife Catacombs", "Cliffbottom Catacombs",
                    "Raya Lucaria Crystal Tunnel", "Ruin-Strewn Precipice"],
    },
    11: {
        "key": "altus_caves", "name": "Altus Caves",
        "lock": "Spelunker's Steel-Wire Torch", "parent": 7,
        "regions": ["Sainted Hero's Grave", "Unsightly Catacombs", "Perfumer's Grotto",
                    "Sage's Cave", "Old Altus Tunnel", "Altus Tunnel"],
    },
    12: {
        "key": "mountaintops_caves", "name": "Mountaintops Caves",
        "lock": "Spelunker's Beast-Repellent Torch", "parent": None,
        "regions": ["Giant-Conquering Hero's Grave", "Giants' Mountaintop Catacombs",
                    "Spiritcaller Cave", "Consecrated Snowfield Catacombs", "Cave of the Forlorn",
                    "Yelough Anix Tunnel"],
    },
}


def active_cave_steps(extra_region_locks) -> Set[int]:
    """Map active extra_region_locks keys -> the cave-bundle step indices they enable.

    Accepts the option value (an iterable of key strings). `limgrave_caves` is honored as the
    documented synonym of `limgrave_underground` in case the alias normalization did not run.
    """
    keys = set(extra_region_locks)
    if "limgrave_caves" in keys:
        keys.add("limgrave_underground")
    return {idx for idx, d in CAVE_BUNDLE_STEPS.items() if d["key"] in keys}
'''
if APPEND_MARK in spine:
    print("  [skip] R1 append CAVE_BUNDLE_STEPS (already present)")
else:
    spine = spine + APPEND_BLOCK
    changed_spine = True
    print("  [ok]   R1 append CAVE_BUNDLE_STEPS + active_cave_steps()")

# --- R2: extend NUM_REGIONS_CHAIN_STEP_LOCK ---
spine, c = repl(
    spine,
    '    7: "Altus Lock",\n    8: "Mt. Gelmir Lock",\n}',
    '    7: "Altus Lock",\n    8: "Mt. Gelmir Lock",\n'
    '    9: "Spelunker\'s Torch",                   # Limgrave Underground (limgrave_underground)\n'
    '    10: "Spelunker\'s Ghostflame Torch",       # Liurnia Caves (liurnia_caves)\n'
    '    11: "Spelunker\'s Steel-Wire Torch",       # Altus Caves (altus_caves)\n'
    '    12: "Spelunker\'s Beast-Repellent Torch",  # Mountaintops Caves (mountaintops_caves)\n}',
    "R2 extend NUM_REGIONS_CHAIN_STEP_LOCK",
    '9: "Spelunker\'s Torch",',
)
changed_spine = changed_spine or c

# --- R3: extend NUM_REGIONS_CHAIN_STEP_HOST_REGIONS ---
spine, c = repl(
    spine,
    '    7: ["Altus Plateau"],\n    8: ["Volcano Manor", "Mt. Gelmir"],\n}',
    '    7: ["Altus Plateau"],\n    8: ["Volcano Manor", "Mt. Gelmir"],\n'
    '    9: ["Stormfoot Catacombs", "Limgrave Tunnels", "Murkwater Catacombs", "Deathtouched Catacombs",\n'
    '        "Fringefolk Hero\'s Grave", "Coastal Cave", "Groveside Cave", "Murkwater Cave",\n'
    '        "Highroad Cave", "Church of Dragon Communion"],\n'
    '    10: ["Black Knife Catacombs", "Road\'s End Catacombs", "Cliffbottom Catacombs", "Stillwater Cave",\n'
    '         "Lakeside Crystal Cave", "Academy Crystal Cave", "Raya Lucaria Crystal Tunnel",\n'
    '         "Ruin-Strewn Precipice"],\n'
    '    11: ["Sainted Hero\'s Grave", "Unsightly Catacombs", "Perfumer\'s Grotto", "Sage\'s Cave",\n'
    '         "Old Altus Tunnel", "Altus Tunnel"],\n'
    '    12: ["Giants\' Mountaintop Catacombs", "Giant-Conquering Hero\'s Grave", "Spiritcaller Cave",\n'
    '         "Consecrated Snowfield Catacombs", "Cave of the Forlorn", "Yelough Anix Tunnel"],\n}',
    "R3 extend NUM_REGIONS_CHAIN_STEP_HOST_REGIONS",
    '9: ["Stormfoot Catacombs"',
)
changed_spine = changed_spine or c

# --- R4: compute_num_regions_scope signature (+ active_cave_steps param) ---
spine, c = repl(
    spine,
    "def compute_num_regions_scope(\n"
    "    rng,\n"
    "    num_regions: int,\n"
    "    great_runes_required: int,\n"
    "    all_region_names: Set[str],\n"
    "    all_lock_names: Set[str],\n"
    ") -> Tuple[Set[str], Set[str], Set[str], Set[str], int]:",
    "def compute_num_regions_scope(\n"
    "    rng,\n"
    "    num_regions: int,\n"
    "    great_runes_required: int,\n"
    "    all_region_names: Set[str],\n"
    "    all_lock_names: Set[str],\n"
    "    active_cave_steps: Set[int] = frozenset(),\n"
    ") -> Tuple[Set[str], Set[str], Set[str], Set[str], int]:",
    "R4 compute_num_regions_scope signature",
    "    all_lock_names: Set[str],\n    active_cave_steps: Set[int] = frozenset(),\n) -> Tuple[Set[str], Set[str], Set[str], Set[str], int]:\n    \"\"\"Resolve a RANDOM short-capital seal scope.",
)
changed_spine = changed_spine or c

# --- R5: regions-mode max_total + cave precompute ---
spine, c = repl(
    spine,
    "    floor = num_regions_floor(great_runes_required)\n"
    "    max_total = 2 + len(NUM_REGIONS_MIDDLE_STEPS)            # Limgrave + Leyndell + every middle",
    "    floor = num_regions_floor(great_runes_required)\n"
    "    _caves = [s for s in sorted(active_cave_steps) if s in CAVE_BUNDLE_STEPS]\n"
    "    _active_cave_dungeons = set()\n"
    "    for _cs in _caves:\n"
    "        _active_cave_dungeons |= set(CAVE_BUNDLE_STEPS[_cs][\"regions\"])\n"
    "    max_total = 2 + len(NUM_REGIONS_MIDDLE_STEPS) + len(_caves)   # Limgrave + Leyndell + middles + active caves",
    "R5 regions max_total + cave precompute",
    "    _caves = [s for s in sorted(active_cave_steps) if s in CAVE_BUNDLE_STEPS]\n    _active_cave_dungeons = set()\n    for _cs in _caves:\n        _active_cave_dungeons |= set(CAVE_BUNDLE_STEPS[_cs][\"regions\"])\n    max_total = 2 + len(NUM_REGIONS_MIDDLE_STEPS) + len(_caves)",
)
changed_spine = changed_spine or c

# --- R6: regions-mode fill pool includes caves ---
spine, c = repl(
    spine,
    "    rest_pool = [s for s in (rune_steps + nonrune_steps) if s not in picked]",
    "    rest_pool = [s for s in (rune_steps + nonrune_steps + _caves) if s not in picked]  # caves COMPETE for fill slots",
    "R6 regions fill pool includes caves",
    "(rune_steps + nonrune_steps + _caves)",
)
changed_spine = changed_spine or c

# --- R7: regions-mode kept_steps cave-aware + split ---
spine, c = repl(
    spine,
    "    kept_steps = [SPINE[0]] + [SPINE[s - 1] for s in picked]   # SPINE[0] = Limgrave (free hub)\n"
    "    kept_regions: Set[str] = set(ALWAYS_OPEN_REGIONS) | set(GOAL_CAPSTONE_REGIONS)\n"
    "    kept_locks: Set[str] = set()\n"
    "    for step in kept_steps:\n"
    "        kept_regions.update(step[\"regions\"])\n"
    "        kept_locks.update(step[\"locks\"])",
    "    kept_steps = [SPINE[0]] + [\n"
    "        ({\"regions\": CAVE_BUNDLE_STEPS[s][\"regions\"], \"locks\": {CAVE_BUNDLE_STEPS[s][\"lock\"]}}\n"
    "         if s in CAVE_BUNDLE_STEPS else SPINE[s - 1])\n"
    "        for s in picked\n"
    "    ]   # SPINE[0] = Limgrave (free hub); cave steps split out of their parent\n"
    "    _picked_cave_dungeons = {r for s in picked if s in CAVE_BUNDLE_STEPS\n"
    "                             for r in CAVE_BUNDLE_STEPS[s][\"regions\"]}\n"
    "    kept_regions: Set[str] = set(ALWAYS_OPEN_REGIONS) | set(GOAL_CAPSTONE_REGIONS)\n"
    "    kept_locks: Set[str] = set()\n"
    "    for step in kept_steps:\n"
    "        kept_regions.update(step[\"regions\"])\n"
    "        kept_locks.update(step[\"locks\"])\n"
    "    # Active cave dungeons are governed ONLY by their own cave step: drop any pulled in via a\n"
    "    # kept parent overworld step unless that cave step was itself picked.\n"
    "    kept_regions -= (_active_cave_dungeons - _picked_cave_dungeons)",
    "R7 regions kept_steps cave-aware",
    "if s in CAVE_BUNDLE_STEPS else SPINE[s - 1])\n        for s in picked\n    ]   # SPINE[0] = Limgrave",
)
changed_spine = changed_spine or c

# --- R8: pool signature (+ active_cave_steps param) ---
spine, c = repl(
    spine,
    "def compute_num_regions_scope_pool(\n"
    "    rng,\n"
    "    num_regions: int,\n"
    "    all_region_names: Set[str],\n"
    "    all_lock_names: Set[str],\n"
    ") -> Tuple[Set[str], Set[str], Set[str], Set[str], int]:",
    "def compute_num_regions_scope_pool(\n"
    "    rng,\n"
    "    num_regions: int,\n"
    "    all_region_names: Set[str],\n"
    "    all_lock_names: Set[str],\n"
    "    active_cave_steps: Set[int] = frozenset(),\n"
    ") -> Tuple[Set[str], Set[str], Set[str], Set[str], int]:",
    "R8 compute_num_regions_scope_pool signature",
    "    all_lock_names: Set[str],\n    active_cave_steps: Set[int] = frozenset(),\n) -> Tuple[Set[str], Set[str], Set[str], Set[str], int]:\n    \"\"\"Resolve a RANDOM short-capital seal scope with the great runes sourced from the POOL.",
)
changed_spine = changed_spine or c

# --- R9: pool body cave-aware (max_total, roll pools, kept_steps + split) ---
spine, c = repl(
    spine,
    "    max_total = len(NUM_REGIONS_POOL_STEPS)                  # every overworld major is rollable\n"
    "    effective = max(int(num_regions), 1)                    # floor of 1 rolled major is fine\n"
    "    effective = min(effective, max_total)\n"
    "\n"
    "    # numregions-pool-keep-altus FIX: Altus is mandatory capstone-route overhead. The lockless\n"
    "    # Leyndell capstone (Capital Outskirts -> Leyndell) has NO warp lock and is reachable ONLY\n"
    "    # via the Altus geographic edge, so a sealed Altus strands the goal -> can_beat_game\n"
    "    # 'unbeatable'. Add one slot for Altus (mirrors the regions-mode force-keep) rather than\n"
    "    # displacing a rolled content region, then pin Altus into the roll.\n"
    "    if ALTUS_STEP in NUM_REGIONS_POOL_STEPS:\n"
    "        effective = min(effective + 1, max_total)\n"
    "        _rest_pool = [s for s in NUM_REGIONS_POOL_STEPS if s != ALTUS_STEP]\n"
    "        picked = [ALTUS_STEP] + list(rng.sample(_rest_pool, max(0, effective - 1)))\n"
    "    else:\n"
    "        picked = list(rng.sample(list(NUM_REGIONS_POOL_STEPS), effective))\n"
    "\n"
    "    kept_steps = [SPINE[s - 1] for s in picked]             # NO forced SPINE[0]/Limgrave\n"
    "    kept_regions: Set[str] = set(ALWAYS_OPEN_REGIONS) | set(GOAL_CAPSTONE_REGIONS)\n"
    "    kept_locks: Set[str] = set()\n"
    "    for step in kept_steps:\n"
    "        kept_regions.update(step[\"regions\"])\n"
    "        kept_locks.update(step[\"locks\"])",
    "    _caves = [s for s in sorted(active_cave_steps) if s in CAVE_BUNDLE_STEPS]\n"
    "    _active_cave_dungeons = set()\n"
    "    for _cs in _caves:\n"
    "        _active_cave_dungeons |= set(CAVE_BUNDLE_STEPS[_cs][\"regions\"])\n"
    "    max_total = len(NUM_REGIONS_POOL_STEPS) + len(_caves)    # overworld majors + active caves\n"
    "    effective = max(int(num_regions), 1)                    # floor of 1 rolled major is fine\n"
    "    effective = min(effective, max_total)\n"
    "\n"
    "    # numregions-pool-keep-altus FIX: Altus is mandatory capstone-route overhead. The lockless\n"
    "    # Leyndell capstone (Capital Outskirts -> Leyndell) has NO warp lock and is reachable ONLY\n"
    "    # via the Altus geographic edge, so a sealed Altus strands the goal -> can_beat_game\n"
    "    # 'unbeatable'. Add one slot for Altus (mirrors the regions-mode force-keep) rather than\n"
    "    # displacing a rolled content region, then pin Altus into the roll. Cave steps COMPETE for\n"
    "    # the remaining slots alongside the overworld majors.\n"
    "    if ALTUS_STEP in NUM_REGIONS_POOL_STEPS:\n"
    "        effective = min(effective + 1, max_total)\n"
    "        _rest_pool = [s for s in NUM_REGIONS_POOL_STEPS if s != ALTUS_STEP] + _caves\n"
    "        picked = [ALTUS_STEP] + list(rng.sample(_rest_pool, max(0, effective - 1)))\n"
    "    else:\n"
    "        picked = list(rng.sample(list(NUM_REGIONS_POOL_STEPS) + _caves, effective))\n"
    "\n"
    "    kept_steps = [\n"
    "        ({\"regions\": CAVE_BUNDLE_STEPS[s][\"regions\"], \"locks\": {CAVE_BUNDLE_STEPS[s][\"lock\"]}}\n"
    "         if s in CAVE_BUNDLE_STEPS else SPINE[s - 1])\n"
    "        for s in picked\n"
    "    ]             # NO forced SPINE[0]/Limgrave; cave steps split out of their parent\n"
    "    _picked_cave_dungeons = {r for s in picked if s in CAVE_BUNDLE_STEPS\n"
    "                             for r in CAVE_BUNDLE_STEPS[s][\"regions\"]}\n"
    "    kept_regions: Set[str] = set(ALWAYS_OPEN_REGIONS) | set(GOAL_CAPSTONE_REGIONS)\n"
    "    kept_locks: Set[str] = set()\n"
    "    for step in kept_steps:\n"
    "        kept_regions.update(step[\"regions\"])\n"
    "        kept_locks.update(step[\"locks\"])\n"
    "    # Active cave dungeons are governed ONLY by their own cave step: drop any pulled in via a\n"
    "    # kept parent overworld step unless that cave step was itself picked.\n"
    "    kept_regions -= (_active_cave_dungeons - _picked_cave_dungeons)",
    "R9 pool body cave-aware",
    "list(rng.sample(list(NUM_REGIONS_POOL_STEPS) + _caves, effective))",
)
changed_spine = changed_spine or c


# ============================ __init__.py ============================
init = _read(INIT_PY)
changed_init = False

# --- I1: regions scope call -- compute + pass active_cave_steps ---
init, c = repl(
    init,
    "                    _kept_r, _sealed_r, _kept_l, _sealed_l, _eff = region_spine.compute_num_regions_scope(\n"
    "                        self.random,\n"
    "                        self.options.num_regions.value,\n"
    "                        self.options.great_runes_required.value,\n"
    "                        _all_regions, _all_locks,\n"
    "                    )",
    "                    _active_caves = region_spine.active_cave_steps(self.options.extra_region_locks.value)\n"
    "                    _kept_r, _sealed_r, _kept_l, _sealed_l, _eff = region_spine.compute_num_regions_scope(\n"
    "                        self.random,\n"
    "                        self.options.num_regions.value,\n"
    "                        self.options.great_runes_required.value,\n"
    "                        _all_regions, _all_locks,\n"
    "                        _active_caves,\n"
    "                    )",
    "I1 regions scope call passes active caves",
    "_active_caves = region_spine.active_cave_steps(self.options.extra_region_locks.value)",
)
changed_init = changed_init or c

# --- I2: pool scope call -- pass active_cave_steps (reuses _active_caves from I1) ---
init, c = repl(
    init,
    "                    _kept_r, _sealed_r, _kept_l, _sealed_l, _eff = \\\n"
    "                        region_spine.compute_num_regions_scope_pool(\n"
    "                            self.random,\n"
    "                            self.options.num_regions.value,\n"
    "                            _all_regions, _all_locks,\n"
    "                        )",
    "                    _kept_r, _sealed_r, _kept_l, _sealed_l, _eff = \\\n"
    "                        region_spine.compute_num_regions_scope_pool(\n"
    "                            self.random,\n"
    "                            self.options.num_regions.value,\n"
    "                            _all_regions, _all_locks,\n"
    "                            _active_caves,\n"
    "                        )",
    "I2 pool scope call passes active caves",
    "                            _all_regions, _all_locks,\n                            _active_caves,\n                        )",
)
changed_init = changed_init or c

# --- I3: _BUNDLE_WARP gains liurnia_caves + limgrave_underground (warp-in for split links) ---
init, c = repl(
    init,
    '        _BUNDLE_WARP = {\n'
    '            "dlc_catacombs": ("Spelunker\'s Messmerflame Torch", ["Fog Rift Catacombs", "Belurat Gaol"]),\n'
    '            "altus_caves": ("Spelunker\'s Steel-Wire Torch", ["Sainted Hero\'s Grave", "Unsightly Catacombs",\n'
    '                "Perfumer\'s Grotto", "Sage\'s Cave", "Old Altus Tunnel", "Altus Tunnel"]),\n'
    '            "mountaintops_caves": ("Spelunker\'s Beast-Repellent Torch", ["Giant-Conquering Hero\'s Grave",\n'
    '                "Giants\' Mountaintop Catacombs", "Spiritcaller Cave", "Consecrated Snowfield Catacombs",\n'
    '                "Cave of the Forlorn", "Yelough Anix Tunnel"]),\n'
    '        }',
    '        _BUNDLE_WARP = {\n'
    '            "dlc_catacombs": ("Spelunker\'s Messmerflame Torch", ["Fog Rift Catacombs", "Belurat Gaol"]),\n'
    '            "altus_caves": ("Spelunker\'s Steel-Wire Torch", ["Sainted Hero\'s Grave", "Unsightly Catacombs",\n'
    '                "Perfumer\'s Grotto", "Sage\'s Cave", "Old Altus Tunnel", "Altus Tunnel"]),\n'
    '            "mountaintops_caves": ("Spelunker\'s Beast-Repellent Torch", ["Giant-Conquering Hero\'s Grave",\n'
    '                "Giants\' Mountaintop Catacombs", "Spiritcaller Cave", "Consecrated Snowfield Catacombs",\n'
    '                "Cave of the Forlorn", "Yelough Anix Tunnel"]),\n'
    '            "liurnia_caves": ("Spelunker\'s Ghostflame Torch", ["Stillwater Cave", "Lakeside Crystal Cave",\n'
    '                "Academy Crystal Cave", "Road\'s End Catacombs", "Black Knife Catacombs",\n'
    '                "Cliffbottom Catacombs", "Raya Lucaria Crystal Tunnel", "Ruin-Strewn Precipice"]),\n'
    '            "limgrave_underground": ("Spelunker\'s Torch", ["Fringefolk Hero\'s Grave", "Coastal Cave",\n'
    '                "Church of Dragon Communion", "Groveside Cave", "Stormfoot Catacombs", "Limgrave Tunnels",\n'
    '                "Murkwater Cave", "Murkwater Catacombs", "Highroad Cave", "Deathtouched Catacombs"]),\n'
    '        }',
    "I3 _BUNDLE_WARP adds liurnia_caves + limgrave_underground",
    '"liurnia_caves": ("Spelunker\'s Ghostflame Torch", ["Stillwater Cave"',
)
changed_init = changed_init or c


# ============================ commit (write only after all anchors matched) ============================
if changed_spine:
    with io.open(SPINE_PY, "w", encoding="utf-8", newline="") as f:
        f.write(spine)
    print(f"WROTE {SPINE_PY}")
else:
    print(f"no change to {SPINE_PY}")

if changed_init:
    with io.open(INIT_PY, "w", encoding="utf-8", newline="") as f:
        f.write(init)
    print(f"WROTE {INIT_PY}")
else:
    print(f"no change to {INIT_PY}")

# Byte-compile both as a sanity check.
import py_compile
ok = True
for p in (SPINE_PY, INIT_PY):
    try:
        py_compile.compile(p, doraise=True)
        print(f"  compile OK: {p}")
    except py_compile.PyCompileError as e:
        ok = False
        print(f"  COMPILE FAILED: {p}\n{e}")
sys.exit(0 if ok else 1)
