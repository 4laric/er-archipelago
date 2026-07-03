#!/usr/bin/env python3
"""
er_yaml_lint.py -- sanity-check an Elden Ring Archipelago Players yaml for the
silent option interactions that waste playtests: dead (inert) knobs, conflicting
goals, and the known footguns.

Usage:
    python er_yaml_lint.py [PATH ...]      # files and/or dirs; default: Archipelago/Players
    python er_yaml_lint.py --strict ...    # exit non-zero on warnings too (default: only errors)

Severities:
    [ERROR] the option does the OPPOSITE of what you wrote, or gen will fail
    [WARN ] the option is silently IGNORED / overridden under these settings
    [INFO ] heads-up / style (e.g. a choice value yaml parsed as a bool)

Drift-proof: the set of valid option keys is parsed live from
worlds/eldenring/options.py (the EROptions dataclass), so adding an option in
options.py automatically teaches the linter about it. Pure stdlib + PyYAML.
"""
from __future__ import annotations
import os, re, sys, glob
from difflib import get_close_matches

try:
    import yaml
except ImportError:
    sys.stderr.write("er_yaml_lint: PyYAML not found (pip install pyyaml)\n")
    sys.exit(2)

# ---- locate options.py relative to this script (repo root) ------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_OPTIONS_CANDIDATES = [
    os.path.join(_HERE, "Archipelago", "worlds", "eldenring", "options.py"),
    os.path.join(_HERE, "worlds", "eldenring", "options.py"),
]

# Common (non-ER) keys that are valid in the EldenRing block via PerGameCommonOptions/CommonOptions.
_COMMON_KEYS = {
    "progression_balancing", "accessibility", "local_items", "non_local_items",
    "start_inventory", "start_inventory_from_pool", "start_hints", "start_location_hints",
    "exclude_locations", "priority_locations", "item_links", "plando_items", "death_link",
}

def load_valid_keys() -> set[str]:
    """Parse the EROptions dataclass field names straight from options.py."""
    for path in _OPTIONS_CANDIDATES:
        if os.path.isfile(path):
            src = open(path, "r", encoding="utf-8", errors="replace").read()
            m = re.search(r"class\s+EROptions\b.*?:\n(.*?)(?:\n@|\nclass\s|\noption_groups\b)",
                          src, re.S)
            if not m:
                break
            keys = set(re.findall(r"^\s{4}([a-zA-Z_]\w*)\s*:", m.group(1), re.M))
            if keys:
                return keys | _COMMON_KEYS
    return set()  # empty -> unknown-key check is skipped (can't verify)

VALID_KEYS = load_valid_keys()

# ---- choice option name<->int maps (only what rules / the bool-bug check need) ----
CHOICE = {
    "ending_condition": {"final_boss":0,"elden_beast":1,"all_remembrances":2,"all_bosses":3,"capital":4,"messmer":5,"godrick":6},
    "world_logic": {"region_lock":0,"region_bosses":1,"region_lock_bosses":2,"open_world":3},
    "region_access": {"geographic":0,"warp":1},
    "num_regions_order": {"rolled":0,"spine":1},
    "dlc_timing": {"early":0,"off":1,"late":2},
    "completion_scaling": {"off":0,"flat":1,"gentle":2,"steep":3,"smoothstep":4},
    "completion_scaling_basis": {"geographic":0,"sphere":1},
    "dungeon_sweep": {"none":0,"minidungeons":1,"all":2,"bosses":3},
    "location_pool": {"all":0,"trimmed":1,},
    "global_scadutree_blessing": {"off":0,"player_only":1,"scaled":2},
    "crafting_kit_option": {"randomize":0,"early":1,"do_not_randomize":2,"start_with":3},
    "map_option": {"randomize":0,"give":1,"do_not_randomize":2},
    "smithing_bell_bearing_option": {"randomize":0,"progression_randomize":1,"do_not_randomize":2},
    "merchant_bell_logic": {"off":0,"logic_only":1},
    "bell_physick_option": {"start_with":0,"do_not_randomize":1,"randomize":2},
    "torrent_start": {"auto":0,"on":1,"off":2},
    "random_start_region": {"off":0,"overworld":1,"any_major":2},
    "start_region_freebie": {"hub_only":0,"to_limgrave":1},
    "junk_retention_style": {"comedy":0,"comedy_and_generic":1,"uniform":2},
    "filler_replacement": {"off":0,"runes":1,"stones_and_runes":2},
    "excluded_location_behavior": {"allow_useful":1,"forbid_useful":2,"do_not_randomize":3},
    "missable_location_behavior": {"allow_useful":1,"forbid_useful":2,"do_not_randomize":3},
}
# defaults rules fall back to when a key is absent
DEFAULT = {
    "ending_condition":"final_boss","world_logic":"region_lock","region_access":"geographic",
    "dlc_only":False,"enable_dlc":False,"enemy_rando":False,"grace_rando":True,
    "num_regions":0,"num_regions_order":"rolled","completion_scaling_floor":0,"graces_per_region":3,
    "pool_builder":False,"pool_builder_dlc_gear":False,"soft_progression":False,
    "dlc_only_chain":False,"messmer_kindle":False,"quick_start":False,
    "dlc_only_rune_catchup":False,"num_regions_chain":False,
    "location_pool":"all","excluded_location_behavior":"forbid_useful",
    "missable_location_behavior":"forbid_useful",
}
# options removed in a hard merge -> give a migration hint instead of a bare "unknown"
REMOVED = {
    "region_count": "merged into num_regions -- use `num_regions: N` + `num_regions_order: spine`",
    "flask_upgrade_option": "merged into important_locations (list Seedtree/Church) -- use vanilla_upgrades: [flasks] for the old do_not_randomize",
    "blessing_option": "merged into important_locations (list Fragment/Revered) -- use vanilla_upgrades: [blessings] for the old do_not_randomize",
    "pool_builder_dlc_gear": "removed (Part 2) -- pool_builder injects base juice only; use dlc_gear_curation for DLC gear",
    "great_runes_present": "removed (Part 2) -- num_regions pool deficit injection now targets great_runes_required",    "region_boss_type": "removed (Part 2) -- only fed the disabled region_bosses rules block",
    "num_regions_rune_source": "removed 2026-07-02 (one-sound-mode) -- rune deficits vs great_runes_required are pool-injected automatically in all num_regions modes; delete the key",
    "shop_checks": "removed 2026-07-02 (one-sound-mode) -- shop-slot handling is no longer optional; delete the key",
}

class Finding:
    __slots__ = ("sev","key","msg")
    def __init__(self, sev, key, msg): self.sev, self.key, self.msg = sev, key, msg

# ---- value helpers ----------------------------------------------------------
def as_bool(v):
    if isinstance(v, bool): return v
    if isinstance(v, (int, float)): return bool(v)
    if isinstance(v, str): return v.strip().lower() not in {"off","0","false","none","null","no",""}
    return bool(v)

class Cfg:
    def __init__(self, block: dict):
        self.b = block or {}
        self.bool_choice_hits = []  # (key) where a choice value got parsed as a python bool

    def has(self, k): return k in self.b
    def raw(self, k, d=None): return self.b.get(k, d)

    def truthy(self, k):
        return as_bool(self.b.get(k, DEFAULT.get(k, False)))

    def num(self, k):
        v = self.b.get(k, DEFAULT.get(k, 0))
        try: return int(v)
        except (TypeError, ValueError): return 0

    def cval(self, k):
        """Return the normalized choice NAME (str) for a choice key, or None if absent."""
        if k not in self.b:
            return DEFAULT.get(k)
        v = self.b[k]
        names = CHOICE.get(k, {})
        if isinstance(v, bool):
            # yaml turned an unquoted on/off/yes/no into a python bool -- AP maps it via int(0/1)
            self.bool_choice_hits.append(k)
            inv = {i: n for n, i in names.items()}
            return inv.get(1 if v else 0)
        if isinstance(v, int) and not isinstance(v, bool):
            inv = {i: n for n, i in names.items()}
            return inv.get(v, str(v))
        return str(v).strip().lower()

# ---- the rules --------------------------------------------------------------
def lint_block(block: dict) -> list[Finding]:
    c = Cfg(block)
    out: list[Finding] = []
    def err(k,m): out.append(Finding("ERROR",k,m))
    def warn(k,m): out.append(Finding("WARN",k,m))
    def info(k,m): out.append(Finding("INFO",k,m))

    goal = c.cval("ending_condition")
    wl   = c.cval("world_logic")
    lock_based = wl in ("region_lock", "region_lock_bosses")
    nr   = c.num("num_regions")
    seal_goal = goal in ("capital","messmer","godrick") or nr > 0
    eff_dlc = c.truthy("enable_dlc") or c.truthy("dlc_only") or goal == "messmer"

    # 0) unknown keys (typos / stranded options)
    if VALID_KEYS:
        for k in c.b:
            if k not in VALID_KEYS:
                if k in REMOVED:
                    err(k, f"REMOVED -- {REMOVED[k]}")
                else:
                    sugg = get_close_matches(k, VALID_KEYS, n=3, cutoff=0.6)
                    hint = f" -- did you mean {', '.join(repr(s) for s in sugg)}?" if sugg else " -- typo?"
                    err(k, f"unknown option '{k}'{hint} (silently ignored by AP)")

    # 1) goal forcing
    if goal == "messmer":
        if c.has("dlc_only") and not c.truthy("dlc_only"):
            warn("dlc_only", "ending_condition: messmer FORCES dlc_only ON -- your 'false' is overridden")
        if c.truthy("messmer_kindle"):
            warn("messmer_kindle", "forced OFF under ending_condition: messmer (Enir Ilim is sealed)")
    if goal == "godrick":
        if c.truthy("dlc_only"):
            warn("dlc_only", "ending_condition: godrick FORCES dlc_only OFF -- your 'true' is overridden")
        if wl == "open_world":
            err("world_logic", "ending_condition: godrick needs lock-based world_logic (region_lock / region_lock_bosses)")
    if c.truthy("dlc_only") and c.has("enable_dlc") and not c.truthy("enable_dlc"):
        info("enable_dlc", "dlc_only FORCES enable_dlc ON -- your 'false' is overridden")

    # 2) random_start_region
    rsr = c.cval("random_start_region")
    if rsr and rsr != "off":
        if seal_goal:
            # Name the specific seal goal in play so the message points at the real cause.
            active = []
            if goal in ("capital","messmer","godrick"): active.append(f"ending_condition: {goal}")
            if nr > 0: active.append(f"num_regions: {nr}")
            cause = " + ".join(active)
            _chain = c.truthy("num_regions_chain")
            if nr > 0 and _chain:
                # The chain's link-0 rolls your start region: random_start_region the OPTION is
                # inert, but functionally you DO get a random start -- working as intended.
                # (num_regions_rune_source deleted 2026-07-02; deficit injection is automatic.)
                info("random_start_region",
                     f"the option itself is inert under the seal goal ({cause}), but "
                     "num_regions_chain is set, so the chain's link-0 already rolls your "
                     "start region -- working as intended.")
            else:
                # Why: a seal goal prunes the world to a kept set with the goal boss inside it; a free
                # random spawn could land in a SEALED region, so the apworld resets it and you start at
                # The First Step regardless of this value.
                msg = (f"IGNORED -- a region-seal goal is active ({cause}). random_start_region is "
                       "silently reset to 'off' (the world is pruned to a kept set the goal boss must "
                       "sit inside, and a free spawn could land in a sealed region). You'll start at "
                       "The First Step (Limgrave).")
                if nr > 0:
                    msg += ("\n    Fix (num_regions runs): set num_regions_chain: true to SPAWN in the "
                            "rolled link-0 region.")
                else:
                    msg += ("\n    No random-start path exists under this goal yet (the Roundtable re-root "
                            "rides on num_regions). Drop random_start_region, or switch to a non-seal goal "
                            "(elden_beast / final_boss / all_remembrances / all_bosses) to use it.")
                warn("random_start_region", msg)
        if c.truthy("dlc_only"):
            warn("random_start_region", "INERT under dlc_only -- Gravesite is the fixed sphere-1 hub, "
                 "so there is no overworld region to roll a start in.")
        if not lock_based:
            err("random_start_region", "requires lock-based world_logic (region_lock / region_lock_bosses) "
                f"-- you have world_logic: {wl}. The roll pre-collects a region's LOCK as the free hub, "
                "which only exists when regions are lock-gated.")

    # 3) enemy_rando gates. NOTE: completion_scaling has a scale-only bake pass now, so it
    #    does NOT require enemy_rando; only the swap/runes/impolite toggles do.
    if not c.truthy("enemy_rando"):
        for k in ("swap_multiboss","boss_runes_match","impolite_enemies"):
            if c.truthy(k):
                warn(k, "INERT without enemy_rando: true")
    if c.num("completion_scaling_floor") > 0 and c.cval("completion_scaling") in (None,"off"):
        warn("completion_scaling_floor", "INERT without completion_scaling on")

    # 4) dlc_only gates
    if not c.truthy("dlc_only"):
        for k in ("quick_start","dlc_only_rune_catchup"):
            if c.truthy(k):
                warn(k, "INERT unless dlc_only: true")

    # 5) region gating requires
    if c.raw("extra_region_locks") and not lock_based:
        warn("extra_region_locks", "INERT without lock-based world_logic")
    if nr > 0:
        if goal != "capital":
            warn("num_regions", "only takes effect with ending_condition: capital")
        if not lock_based:
            warn("num_regions", "only takes effect with lock-based world_logic")
    # 6) num_regions_order: spine requested but no regions to order
    if c.cval("num_regions_order") == "spine" and nr == 0:
        warn("num_regions_order", "spine ordering set but num_regions is 0 (nothing to keep)")

    # 7) num_regions sub-options
    if c.truthy("num_regions_chain"):
        if nr == 0:
            warn("num_regions_chain", "INERT unless num_regions > 0")
        elif goal != "capital":
            warn("num_regions_chain", "only takes effect with ending_condition: capital")

    # 7c) rune/region decoupling (2026-07-02): the structural floor is 3 (Limgrave+Leyndell+Altus);
    #     great runes never raise the region count (deficit is pool-injected instead).
    if 0 < nr < 3:
        info("num_regions", "below the structural floor -- raised to 3 at gen (Limgrave + Leyndell + Altus)")
    if nr > 0 and c.num("great_runes_required") > 4:
        err("great_runes_required", "num_regions runs can satisfy at most 4 great runes "
            "(Godrick/Rennala/Radahn/Rykard exist before the capital) -- gen rejects this (OptionError)")

    # 8) dlc_only_chain
    if c.truthy("dlc_only_chain") and goal != "messmer":
        warn("dlc_only_chain", "Phase 1 only acts under ending_condition: messmer -- plain dlc_only warns + no-ops")

    # 10) sweep
    if c.cval("grace_sweep") not in (None,"off") and c.cval("dungeon_sweep") != "bosses":
        warn("grace_sweep", "INERT unless dungeon_sweep: bosses")

    # 11) soft_progression vs accessibility
    if c.truthy("soft_progression") and c.cval("accessibility") == "minimal":
        warn("soft_progression", "no effect under accessibility: minimal (everything spills there anyway)")

    # 12) grace bundle override
    if c.truthy("grace_rando") and lock_based and c.has("graces_per_region") and c.num("graces_per_region") != 3:
        info("graces_per_region", "grace_rando (on) overrides the graces_per_region bundle -- set grace_rando: false to use it")

    # 13) baked-dependency reminders (can't verify from yaml)
    if c.truthy("soft_consumable_shop"):
        info("soft_consumable_shop", "REQUIRES the baked Twin Maiden rows (patch_baker_soft_consumable_shop) -- dead without them")

    # 14) choice value parsed as a YAML boolean (the unquoted on/off/yes/no footgun:
    #     e.g. `dlc_timing: off` -> False -> resolves to option index 0 = 'early', NOT off)
    for k in CHOICE:
        if k in c.b and isinstance(c.b[k], bool):
            info(k, f"YAML parsed this choice as a boolean ({str(c.b[k]).lower()}); quote it (e.g. {k}: \"off\") or it silently resolves to the wrong option")

    # 15b) trimmed + forbid_useful filler shortage (observed 3/3 FillError on the
    #      wizard short_solo sample 2026-07-02: "Not enough filler items for excluded
    #      locations"; the trimmed pool runs out of pure filler for excluded/missables,
    #      especially under seal goals). forbid_useful is the DEFAULT, so this fires on
    #      absent keys too -- allow_useful is the supported pairing with trimmed.
    if c.cval("location_pool") == "trimmed":
        for k in ("excluded_location_behavior", "missable_location_behavior"):
            if c.cval(k) == "forbid_useful":
                warn(k, "trimmed pool + forbid_useful can FillError ('not enough filler "
                        "items for excluded locations') -- set allow_useful")

    # 15) tight-pool accessibility heads-up
    if c.cval("accessibility") == "full" and (seal_goal or c.cval("location_pool") == "lean" or c.raw("extra_region_locks")):
        info("accessibility", "full can FillError on tight/region-locked pools; minimal lets them spill")

    return out

# ---- driver -----------------------------------------------------------------
def lint_file(path: str) -> list[Finding]:
    try:
        docs = list(yaml.safe_load_all(open(path, "r", encoding="utf-8-sig")))
    except Exception as e:
        return [Finding("ERROR", "<file>", f"could not parse yaml: {e}")]
    findings = []
    for doc in docs:
        if isinstance(doc, dict) and isinstance(doc.get("EldenRing"), dict):
            findings += lint_block(doc["EldenRing"])
    return findings

def iter_yaml_paths(paths):
    for p in paths:
        if os.path.isdir(p):
            yield from sorted(glob.glob(os.path.join(p, "*.yaml"))) + sorted(glob.glob(os.path.join(p, "*.yml")))
        else:
            yield p

def main(argv):
    strict = "--strict" in argv
    args = [a for a in argv if not a.startswith("-")]
    if not args:
        for cand in (os.path.join(_HERE, "Archipelago", "Players"), os.path.join(_HERE, "Players")):
            if os.path.isdir(cand): args = [cand]; break
    if not args:
        print("usage: python er_yaml_lint.py [PATH ...]   (no Players dir found)"); return 2

    total_err = total_warn = 0
    any_file = False
    for path in iter_yaml_paths(args):
        any_file = True
        findings = lint_file(path)
        name = os.path.basename(path)
        if not findings:
            print(f"  OK    {name}")
            continue
        print(f"\n{name}")
        order = {"ERROR":0,"WARN":1,"INFO":2}
        for f in sorted(findings, key=lambda x: order[x.sev]):
            print(f"  [{f.sev:<5}] {f.key}: {f.msg}")
            if f.sev == "ERROR": total_err += 1
            elif f.sev == "WARN": total_warn += 1
    if not any_file:
        print("no yaml files found"); return 2
    print(f"\n{total_err} error(s), {total_warn} warning(s)")
    if total_err or (strict and total_warn):
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
