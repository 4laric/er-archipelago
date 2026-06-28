#!/usr/bin/env python3
r"""patch_apworld_options_regroup.py

SPEC-options-consolidation.md, Part 4 (the safe, presentation-only change).

Rebuild the `option_groups = [...]` block at the end of
  Archipelago/worlds/eldenring/options.py
so that EVERY field in the `EROptions` dataclass lands in a named OptionGroup.

Today only ~40 of the 84 options are grouped; the rest spill into the webhost's
ungrouped "Game Options" bucket. This patch does NOT touch any option class, the
dataclass, or any feature logic -- it only replaces the trailing `option_groups`
list literal. The set of options, their names, defaults and behaviour are unchanged,
so generation behaviour is identical; the only observable difference is how options
are grouped on the webhost / in generated templates.

HOW IT WORKS
  * The `option_groups = [` list literal is the LAST top-level block in options.py,
    so the patch slices from that anchor to EOF and writes a freshly generated block.
  * The block is generated from the GROUPS table below. Every class referenced is
    asserted to be available (defined as `class NAME(` in the file, or imported -- only
    DeathLink) and present exactly once in the new block; the union of GROUPS is
    asserted to equal the 84 EROptions members -- so a typo, drop or duplicate fails
    the patch before any write.
  * The whole rewritten file is compiled (syntax check) before writing.
  * CRLF/LF agnostic: EOL is detected from the file and the generated block is
    normalised to it.

USAGE (Windows, from the repo root):
    python patch_apworld_options_regroup.py
    .\build.ps1 -Apworld          # repackage worlds/eldenring -> eldenring.apworld
    # then gen-test (see gen-test/options-regroup-yamls/README.txt):
    .\build.ps1 -Randomizer -Generate
"""
import os, sys

REPO   = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(REPO, "Archipelago", "worlds", "eldenring", "options.py")

# Prove we read to the very end of the current option_groups block.
TAIL_SYMBOL = b"ImpoliteEnemies,"
# Anchor: start of the block we replace (must occur exactly once; it is the last block).
ANCHOR = b"option_groups = ["
# Idempotency / verify marker (placed just above the rebuilt block).
MARKER = b"# option_groups rebuilt by patch_apworld_options_regroup -- see docs/er/SPEC-options-consolidation.md"

# Classes that are IMPORTED into options.py rather than defined there.
IMPORTED = {"DeathLink"}

# --- the grouping. (group display name, [Option class names, in display order]) ----
# Every EROptions field appears exactly once across these lists. Names map field->class
# exactly as declared in options.py; classes are NOT renamed or moved, only referenced.
GROUPS = [
    ("Goal & World Logic", [
        "EndingCondition", "WorldLogic", "RegionBossPercent", "RegionBossType",
        "RegionSoftLogic", "DeathlessRouting", "RegionAccessLogic", "RoyalAccess",
        "ExtraRegionLocks",
    ]),
    ("Great Runes", [
        "GreatRunesRequired", "GreatRunesFinalBoss", "GreatRunesMountaintops",
        "GreatRunesPresent",
    ]),
    ("Short Runs (Capital)", [
        "GracesPerRegion", "RegionCount", "NumRegions", "NumRegionsRuneSource",
        "NumRegionsChain",
    ]),
    ("Start", [
        "RandomStartRegion", "StartRegionFreebie", "EarlyLeveling",
        "RandomizeStartingLoadout", "TorrentStart",
    ]),
    ("DLC", [
        "EnableDLC", "DLCOnly", "DLCTimingOption", "ScadutreeFrontload",
        "MessmerKindle", "MessmerKindleRequired", "MessmerKindleMax", "BlessingOption",
    ]),
    ("DLC-Only Catch-up", [
        "QuickStart", "DLCOnlyRuneCatchup",
    ]),
    ("Pool & Curation", [
        "LocationPool", "PoolBuilder", "PoolBuilderDLCGear", "DLCGearCuration",
        "FillerReplacement", "JunkRetention", "JunkRetentionStyle",
        "TidyFunConsumables", "SoftConsumableShop", "DerandomizeGurranq",
        "DerandomizeQuestlines", "SoftProgression", "NoSpiritAshes", "RandomizeEnia",
    ]),
    ("Progressive Items", [
        "ProgressiveStoneBells", "ProgressiveBellCount", "ProgressiveBellEarlyCount",
        "ProgressiveGlovewortBells", "ProgressiveFlasks", "ProgressiveFlaskEarlyCount",
        "ProgressivePhysick",
    ]),
    ("Fill Priority", [
        "ERImportantLocations", "ERExcludeLocations", "ExcludedLocationBehaviorOption",
        "MissableLocationBehaviorOption", "FlaskUpgradeOption", "MerchantBellLogic",
        "LocalItemOnly", "ExcludeLocalItemOnly",
    ]),
    ("Sweep", [
        "DungeonSweep", "GraceSweep",
    ]),
    ("Enemy Randomizer", [
        "EnemyRando", "SwapMultiBoss", "BossRunesMatchOriginal", "ImpoliteEnemies",
        "CompletionScaling", "CompletionScalingFloor", "CompletionScalingBasis",
        "GlobalScadutreeBlessing",
    ]),
    ("Equipment & QoL", [
        "AutoEquipOption", "AutoUpgradeOption", "NoWeaponRequirements",
        "CraftingKitOption", "MapOption", "SmithingBellBearingOption",
        "SpellShopSpellsOnly", "EarlyLegacyDungeonsEarly", "MaterialRando",
        "DisableSerpentHunterUpgrade", "BellPhysickOption", "DeathLink",
    ]),
]

# The 84 EROptions members (as class names), used to assert full + exact coverage.
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
    lf_only = data.count(b"\n") - crlf
    return b"\r\n" if crlf >= lf_only else b"\n"


def _build_block_text() -> str:
    lines = ["option_groups = ["]
    for name, classes in GROUPS:
        lines.append(f'    OptionGroup("{name}", [')
        for c in classes:
            lines.append(f"        {c},")
        lines.append("    ]),")
    lines.append("]")
    lines.append("")  # trailing newline at EOF
    return "\n".join(lines)


def main():
    # ---- static coverage checks on the GROUPS table itself (no file needed) ----
    grouped = [c for _, cs in GROUPS for c in cs]
    if sorted(grouped) != sorted(EXPECTED):
        missing = sorted(set(EXPECTED) - set(grouped))
        extra = sorted(set(grouped) - set(EXPECTED))
        dupes = sorted({c for c in grouped if grouped.count(c) > 1})
        sys.exit(f"ERROR: GROUPS != EXPECTED. missing={missing} extra={extra} dupes={dupes}")
    if len(EXPECTED) != 84 or len(grouped) != 84:
        sys.exit(f"ERROR: expected 84 options, EXPECTED={len(EXPECTED)} grouped={len(grouped)}")

    if not os.path.isfile(TARGET):
        sys.exit(f"ERROR: not found: {TARGET}")
    size = os.path.getsize(TARGET)
    with open(TARGET, "rb") as f:
        data = f.read()

    if len(data) != size:
        sys.exit(f"ERROR: short read ({len(data)} != {size}) -- I/O truncation; aborting, no write.")
    if TAIL_SYMBOL not in data:
        sys.exit(f"ERROR: tail symbol {TAIL_SYMBOL!r} missing -- source looks truncated; aborting.")
    if MARKER in data:
        print("Already patched -- option_groups already rebuilt. No change.")
        return

    n = data.count(ANCHOR)
    if n != 1:
        sys.exit(f"ERROR: anchor {ANCHOR!r} found {n} times, expected 1. Aborting (no write).")

    # every referenced class must be available: defined as `class NAME(` or imported.
    for c in EXPECTED:
        if c in IMPORTED:
            if c.encode() not in data:
                sys.exit(f"ERROR: imported class {c} not found in options.py. Aborting.")
        elif (b"class " + c.encode() + b"(") not in data:
            sys.exit(f"ERROR: class {c} is referenced but not defined in options.py. Aborting.")

    eol = _detect_eol(data)
    idx = data.index(ANCHOR)
    head = data[:idx]  # everything up to (and the blank line before) the old block

    payload_text = MARKER.decode() + "\n" + _build_block_text()
    payload = payload_text.encode("utf-8").replace(b"\n", eol)
    new = head + payload

    # every option referenced exactly once in the new block (trailing comma guards
    # against prefix collisions like NumRegions vs NumRegionsChain).
    for c in EXPECTED:
        token = b"        " + c.encode() + b","
        if payload.count(token) != 1:
            sys.exit(f"ERROR: class {c} appears {payload.count(token)}x in new block (want 1). Aborting.")

    # syntax-compile the whole rewritten file before touching disk
    try:
        compile(new.decode("utf-8"), TARGET, "exec")
    except SyntaxError as e:
        sys.exit(f"ERROR: rewritten options.py does not compile: {e}. Aborting (no write).")

    bak = TARGET + ".bak_optionsregroup"
    with open(bak, "wb") as f:
        f.write(data)
    with open(TARGET, "wb") as f:
        f.write(new)

    with open(TARGET, "rb") as f:
        chk = f.read()
    if MARKER not in chk or TAIL_SYMBOL not in chk or chk != new:
        sys.exit(f"ERROR: verification AFTER write FAILED. Restore from {bak}")

    eol_name = "CRLF" if eol == b"\r\n" else "LF"
    print("OK: option_groups rebuilt -- all 84 EROptions members grouped.")
    print(f"  target : {TARGET}")
    print(f"  backup : {bak}")
    print(f"  groups : {len(GROUPS)}  ({', '.join(name for name, _ in GROUPS)})")
    print(f"  size   : {size} -> {len(chk)} ({len(chk) - size:+d} bytes)")
    print(f"  eol    : {eol_name}")
    print("Next: .\\build.ps1 -Apworld   then gen-test (gen-test/options-regroup-yamls/).")


if __name__ == "__main__":
    main()
