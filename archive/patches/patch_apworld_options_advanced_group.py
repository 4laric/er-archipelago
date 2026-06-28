#!/usr/bin/env python3
r"""patch_apworld_options_advanced_group.py

SPEC-options-consolidation.md, Part 2 -- "deprecate = flag + hide" (presentation only).

The Part-2 audit candidates (global_scadutree_blessing, completion_scaling_basis=sphere,
great_runes_present, pool_builder_dlc_gear, region_boss_type, deathless_routing,
royal_access, disable_serpent_hunter_upgrade) are EXPERIMENTAL, unfinished, or
ultra-niche -- but every one has real backing logic (51 refs across __init__.py /
region_spine.py), so DELETING them is feature-removing surgery, not cleanup. Instead we
HIDE them: move all 8 into a new "Advanced & Experimental" OptionGroup with
start_collapsed=True, so they drop out of the default webhost view but still work.

This rebuilds the trailing `option_groups` block (13 groups, all 84 EROptions members),
SUPERSEDING patch_apworld_options_regroup.py's block -- it is self-contained and works
whether or not the regroup patch ran (it removes any prior `# option_groups ...` marker
line first, then writes its own). No option class, dataclass, default or logic changes,
so generation behaviour is identical.

Idempotent (re-running reproduces byte-identical output). CRLF/LF agnostic. Backup +
full-file compile + post-write verify.

USAGE (Windows, repo root):
    python patch_apworld_options_advanced_group.py
    .\build.ps1 -Apworld
"""
import os, re, sys

REPO   = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(REPO, "Archipelago", "worlds", "eldenring", "options.py")

# Tail proof: the LAST EROptions dataclass member (present on fresh AND post-regroup
# files; the dataclass is never touched). Reading through it means we reached the
# option_groups block that immediately follows.
TAIL_SYMBOL = b"pool_builder_dlc_gear: PoolBuilderDLCGear"
ANCHOR = b"option_groups = ["
# Our marker; any prior `# option_groups ...` line (incl. the regroup patch's) is removed.
MARKER = b"# option_groups: advanced/experimental split by patch_apworld_options_advanced_group -- see docs/er/SPEC-options-consolidation.md"
PRIOR_MARKER_RE = re.compile(rb"(?m)^# option_groups[^\n]*\n")

IMPORTED = {"DeathLink"}

# (group name, [classes], start_collapsed). All 84 EROptions members appear once.
GROUPS = [
    ("Goal & World Logic", [
        "EndingCondition", "WorldLogic", "RegionBossPercent", "RegionSoftLogic",
        "RegionAccessLogic", "ExtraRegionLocks",
    ], False),
    ("Great Runes", [
        "GreatRunesRequired", "GreatRunesFinalBoss", "GreatRunesMountaintops",
    ], False),
    ("Short Runs (Capital)", [
        "GracesPerRegion", "RegionCount", "NumRegions", "NumRegionsRuneSource",
        "NumRegionsChain",
    ], False),
    ("Start", [
        "RandomStartRegion", "StartRegionFreebie", "EarlyLeveling",
        "RandomizeStartingLoadout", "TorrentStart",
    ], False),
    ("DLC", [
        "EnableDLC", "DLCOnly", "DLCTimingOption", "ScadutreeFrontload",
        "MessmerKindle", "MessmerKindleRequired", "MessmerKindleMax", "BlessingOption",
    ], False),
    ("DLC-Only Catch-up", [
        "QuickStart", "DLCOnlyRuneCatchup",
    ], False),
    ("Pool & Curation", [
        "LocationPool", "PoolBuilder", "DLCGearCuration", "FillerReplacement",
        "JunkRetention", "JunkRetentionStyle", "TidyFunConsumables", "SoftConsumableShop",
        "DerandomizeGurranq", "DerandomizeQuestlines", "SoftProgression", "NoSpiritAshes",
        "RandomizeEnia",
    ], False),
    ("Progressive Items", [
        "ProgressiveStoneBells", "ProgressiveBellCount", "ProgressiveBellEarlyCount",
        "ProgressiveGlovewortBells", "ProgressiveFlasks", "ProgressiveFlaskEarlyCount",
        "ProgressivePhysick",
    ], False),
    ("Fill Priority", [
        "ERImportantLocations", "ERExcludeLocations", "ExcludedLocationBehaviorOption",
        "MissableLocationBehaviorOption", "FlaskUpgradeOption", "MerchantBellLogic",
        "LocalItemOnly", "ExcludeLocalItemOnly",
    ], False),
    ("Sweep", [
        "DungeonSweep", "GraceSweep",
    ], False),
    ("Enemy Randomizer", [
        "EnemyRando", "SwapMultiBoss", "BossRunesMatchOriginal", "ImpoliteEnemies",
        "CompletionScaling", "CompletionScalingFloor",
    ], False),
    ("Equipment & QoL", [
        "AutoEquipOption", "AutoUpgradeOption", "NoWeaponRequirements", "CraftingKitOption",
        "MapOption", "SmithingBellBearingOption", "SpellShopSpellsOnly",
        "EarlyLegacyDungeonsEarly", "MaterialRando", "BellPhysickOption", "DeathLink",
    ], False),
    # --- hidden by default: experimental / unfinished / ultra-niche -----------
    ("Advanced & Experimental", [
        "GlobalScadutreeBlessing",       # EXPERIMENTAL; client-side, enemy-side unbuilt
        "CompletionScalingBasis",        # 'sphere' needs an unwired baker bridge
        "GreatRunesPresent",             # only num_regions+rune_source=pool
        "PoolBuilderDLCGear",            # overlaps dlc_gear_curation; DLC-dep footgun
        "RegionBossType",                # region_bosses sub-knob
        "DeathlessRouting",              # niche logic exclusion
        "RoyalAccess",                   # niche convenience
        "DisableSerpentHunterUpgrade",   # niche base-rando tweak
    ], True),
]

EXPECTED = [
    "EndingCondition", "WorldLogic", "RegionBossPercent", "RegionBossType",
    "RegionSoftLogic", "GreatRunesRequired", "GreatRunesFinalBoss",
    "GreatRunesMountaintops", "GreatRunesPresent", "DeathlessRouting",
    "GracesPerRegion", "RegionAccessLogic", "RegionCount", "NumRegions",
    "NumRegionsRuneSource", "NumRegionsChain", "CompletionScaling",
    "CompletionScalingFloor", "CompletionScalingBasis", "GlobalScadutreeBlessing",
    "RandomStartRegion", "StartRegionFreebie", "RoyalAccess", "EarlyLeveling",
    "ExtraRegionLocks", "EnableDLC", "DLCOnly", "QuickStart", "DLCOnlyRuneCatchup",
    "ScadutreeFrontload", "MessmerKindle", "MessmerKindleRequired", "MessmerKindleMax",
    "DLCTimingOption", "EnemyRando", "MaterialRando", "DeathLink",
    "RandomizeStartingLoadout", "AutoEquipOption", "AutoUpgradeOption",
    "ProgressiveStoneBells", "ProgressiveBellCount", "ProgressiveBellEarlyCount",
    "ProgressivePhysick", "CraftingKitOption", "RandomizeEnia", "MapOption",
    "SmithingBellBearingOption", "MerchantBellLogic", "SpellShopSpellsOnly",
    "EarlyLegacyDungeonsEarly", "LocalItemOnly", "ExcludeLocalItemOnly",
    "ERImportantLocations", "ERExcludeLocations", "ExcludedLocationBehaviorOption",
    "MissableLocationBehaviorOption", "DungeonSweep", "GraceSweep",
    "NoWeaponRequirements", "SwapMultiBoss", "BossRunesMatchOriginal",
    "ImpoliteEnemies", "DisableSerpentHunterUpgrade", "BellPhysickOption",
    "TorrentStart", "FlaskUpgradeOption", "BlessingOption", "SoftProgression",
    "TidyFunConsumables", "SoftConsumableShop", "DerandomizeGurranq",
    "DerandomizeQuestlines", "LocationPool", "DLCGearCuration", "JunkRetention",
    "JunkRetentionStyle", "FillerReplacement", "NoSpiritAshes", "ProgressiveFlasks",
    "ProgressiveFlaskEarlyCount", "ProgressiveGlovewortBells", "PoolBuilder",
    "PoolBuilderDLCGear",
]


def _detect_eol(data: bytes) -> bytes:
    crlf = data.count(b"\r\n")
    return b"\r\n" if crlf >= (data.count(b"\n") - crlf) else b"\n"


def _build_block_text() -> str:
    lines = ["option_groups = ["]
    for name, classes, collapsed in GROUPS:
        lines.append(f'    OptionGroup("{name}", [')
        for c in classes:
            lines.append(f"        {c},")
        lines.append("    ], start_collapsed=True)," if collapsed else "    ]),")
    lines.append("]")
    lines.append("")
    return "\n".join(lines)


def main():
    grouped = [c for _, cs, _ in GROUPS for c in cs]
    if sorted(grouped) != sorted(EXPECTED):
        missing = sorted(set(EXPECTED) - set(grouped)); extra = sorted(set(grouped) - set(EXPECTED))
        dupes = sorted({c for c in grouped if grouped.count(c) > 1})
        sys.exit(f"ERROR: GROUPS != EXPECTED. missing={missing} extra={extra} dupes={dupes}")
    if len(grouped) != 84:
        sys.exit(f"ERROR: expected 84 options, got {len(grouped)}")

    if not os.path.isfile(TARGET):
        sys.exit(f"ERROR: not found: {TARGET}")
    size = os.path.getsize(TARGET)
    with open(TARGET, "rb") as f:
        orig = f.read()
    if len(orig) != size:
        sys.exit(f"ERROR: short read ({len(orig)} != {size}) -- I/O truncation; aborting.")
    if TAIL_SYMBOL not in orig:
        sys.exit(f"ERROR: tail symbol {TAIL_SYMBOL!r} missing -- source truncated; aborting.")
    for c in EXPECTED:
        if c in IMPORTED:
            if c.encode() not in orig:
                sys.exit(f"ERROR: imported class {c} not found. Aborting.")
        elif (b"class " + c.encode() + b"(") not in orig:
            sys.exit(f"ERROR: class {c} referenced but not defined. Aborting.")

    eol = _detect_eol(orig)
    data = PRIOR_MARKER_RE.sub(b"", orig)  # drop any prior option_groups marker line
    if data.count(ANCHOR) != 1:
        sys.exit(f"ERROR: anchor {ANCHOR!r} found {data.count(ANCHOR)}x after marker strip, expected 1. Aborting.")

    idx = data.index(ANCHOR)
    head = data[:idx]
    payload = (MARKER.decode() + "\n" + _build_block_text()).encode("utf-8").replace(b"\n", eol)
    new = head + payload

    if new == orig:
        print("Already applied -- Advanced & Experimental group already present, identical. No change.")
        return

    for c in EXPECTED:
        if payload.count(b"        " + c.encode() + b",") != 1:
            sys.exit(f"ERROR: class {c} appears {payload.count(b'        ' + c.encode() + b',')}x in new block (want 1). Aborting.")
    if payload.count(b"start_collapsed=True") != 1:
        sys.exit("ERROR: expected exactly one collapsed group. Aborting.")

    try:
        compile(new.decode("utf-8"), TARGET, "exec")
    except SyntaxError as e:
        sys.exit(f"ERROR: rewritten options.py does not compile: {e}. Aborting (no write).")

    bak = TARGET + ".bak_advgroup"
    with open(bak, "wb") as f:
        f.write(orig)
    with open(TARGET, "wb") as f:
        f.write(new)
    with open(TARGET, "rb") as f:
        chk = f.read()
    if chk != new or MARKER not in chk:
        sys.exit(f"ERROR: verification AFTER write FAILED. Restore from {bak}")

    eol_name = "CRLF" if eol == b"\r\n" else "LF"
    moved = next(cs for n, cs, col in GROUPS if col)
    print("OK: Advanced & Experimental group added (collapsed); option_groups rebuilt.")
    print(f"  target : {TARGET}")
    print(f"  backup : {bak}")
    print(f"  groups : {len(GROUPS)} ; hidden ({len(moved)}): {', '.join(moved)}")
    print(f"  size   : {size} -> {len(chk)} ({len(chk) - size:+d} bytes); eol {eol_name}")
    print("Next: .\\build.ps1 -Apworld   then a gen-test (the regroup yamls still apply).")


if __name__ == "__main__":
    main()
