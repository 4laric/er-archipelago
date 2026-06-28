#!/usr/bin/env python3
r"""patch_apworld_progressive_items_options.py

SPEC-options-consolidation.md, Part 3 -- the progressive-items merge (options half).
Pairs with patch_apworld_progressive_items_init.py (the generate_early mapping).

Collapses the four sibling toggles
  progressive_stone_bells / progressive_glovewort_bells / progressive_flasks /
  progressive_physick
into ONE consolidated front-end OptionSet `progressive_items` with keys
  {stone_bells, glovewort_bells, flasks, physick}.

BACKWARD COMPATIBLE: the four boolean options STAY in the dataclass and remain the
internal source of truth (all downstream logic reads them via the _progressive_*_active
accessors + slot_data). The companion __init__ patch maps the set onto those booleans at
generate_early (OR-union), so:
  - new yamls use `progressive_items: [flasks, physick]`
  - old yamls using `progressive_flasks: true` keep working unchanged
The four legacy toggles are moved into a new collapsed "Superseded (use progressive_items)"
OptionGroup so they drop out of the default webhost view but stay usable.

THREE changes to options.py:
  (A) insert `class ProgressiveItems(OptionSet)` before ProgressiveStoneBells
  (B) insert `progressive_items: ProgressiveItems` into the EROptions dataclass
  (C) rebuild option_groups (15 -> 14 named groups incl. the new field; SUPERSEDES the
      regroup / advanced-group block via marker-strip). 85 members total.

CRLF/LF agnostic. Idempotent. Backup + full-file compile + post-write verify.

USAGE (Windows, repo root):
    python patch_apworld_progressive_items_options.py
    python patch_apworld_progressive_items_init.py
    .\build.ps1 -Apworld
"""
import os, re, sys

REPO   = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(REPO, "Archipelago", "worlds", "eldenring", "options.py")

TAIL_SYMBOL = b"pool_builder_dlc_gear: PoolBuilderDLCGear"   # last dataclass member
ANCHOR_GROUPS = b"option_groups = ["
MARKER = b"# option_groups: progressive_items merge by patch_apworld_progressive_items_options -- see docs/er/SPEC-options-consolidation.md"
PRIOR_MARKER_RE = re.compile(rb"(?m)^# option_groups[^\n]*\n")

CLASS_ANCHOR = b"class ProgressiveStoneBells(Toggle):"
CLASS_PRESENT = b"class ProgressiveItems(OptionSet):"
CLASS_LINES = [
    b"class ProgressiveItems(OptionSet):",
    b'    """Consolidated front-end for the progressive upgrade-item families. Each key replaces',
    b"    that family's discrete pickups with PROGRESSIVE items (see the individual options for the",
    b"    full detail). This is the preferred way to set them; the legacy per-family toggles still",
    b"    work and are OR-unioned in (mapped onto the booleans at generate_early).",
    b"",
    b"      stone_bells     -- Miner's Bell Bearings -> 2 progressive (Smithing x4 / Somber x5)",
    b"      glovewort_bells -- Glovewort Picker's Bell Bearings -> 2 progressive (Grave x3 / Ghost x3)",
    b"      flasks          -- Golden Seeds + Sacred Tears -> 2 progressive (charges / potency)",
    b"      physick         -- Flask of Wondrous Physick + low-value tears -> 1 progressive ladder",
    b'    """',
    b'    display_name = "Progressive Items"',
    b'    valid_keys = {"stone_bells", "glovewort_bells", "flasks", "physick"}',
    b"",
    b"",
]

FIELD_ANCHOR = b"    progressive_stone_bells: ProgressiveStoneBells"
FIELD_PRESENT = b"    progressive_items: ProgressiveItems"
FIELD_LINE = b"    progressive_items: ProgressiveItems"

IMPORTED = {"DeathLink"}

GROUPS = [
    ("Goal & World Logic", ["EndingCondition", "WorldLogic", "RegionBossPercent",
        "RegionSoftLogic", "RegionAccessLogic", "ExtraRegionLocks"], False),
    ("Great Runes", ["GreatRunesRequired", "GreatRunesFinalBoss",
        "GreatRunesMountaintops"], False),
    ("Short Runs (Capital)", ["GracesPerRegion", "RegionCount", "NumRegions",
        "NumRegionsRuneSource", "NumRegionsChain"], False),
    ("Start", ["RandomStartRegion", "StartRegionFreebie", "EarlyLeveling",
        "RandomizeStartingLoadout", "TorrentStart"], False),
    ("DLC", ["EnableDLC", "DLCOnly", "DLCTimingOption", "ScadutreeFrontload",
        "MessmerKindle", "MessmerKindleRequired", "MessmerKindleMax", "BlessingOption"], False),
    ("DLC-Only Catch-up", ["QuickStart", "DLCOnlyRuneCatchup"], False),
    ("Pool & Curation", ["LocationPool", "PoolBuilder", "DLCGearCuration",
        "FillerReplacement", "JunkRetention", "JunkRetentionStyle", "TidyFunConsumables",
        "SoftConsumableShop", "DerandomizeGurranq", "DerandomizeQuestlines",
        "SoftProgression", "NoSpiritAshes", "RandomizeEnia"], False),
    ("Progressive Items", ["ProgressiveItems", "ProgressiveBellCount",
        "ProgressiveBellEarlyCount", "ProgressiveFlaskEarlyCount"], False),
    ("Fill Priority", ["ERImportantLocations", "ERExcludeLocations",
        "ExcludedLocationBehaviorOption", "MissableLocationBehaviorOption",
        "FlaskUpgradeOption", "MerchantBellLogic", "LocalItemOnly",
        "ExcludeLocalItemOnly"], False),
    ("Sweep", ["DungeonSweep", "GraceSweep"], False),
    ("Enemy Randomizer", ["EnemyRando", "SwapMultiBoss", "BossRunesMatchOriginal",
        "ImpoliteEnemies", "CompletionScaling", "CompletionScalingFloor"], False),
    ("Equipment & QoL", ["AutoEquipOption", "AutoUpgradeOption", "NoWeaponRequirements",
        "CraftingKitOption", "MapOption", "SmithingBellBearingOption",
        "SpellShopSpellsOnly", "EarlyLegacyDungeonsEarly", "MaterialRando",
        "BellPhysickOption", "DeathLink"], False),
    ("Superseded (use progressive_items)", ["ProgressiveStoneBells",
        "ProgressiveGlovewortBells", "ProgressiveFlasks", "ProgressivePhysick"], True),
    ("Advanced & Experimental", ["GlobalScadutreeBlessing", "CompletionScalingBasis",
        "GreatRunesPresent", "PoolBuilderDLCGear", "RegionBossType", "DeathlessRouting",
        "RoyalAccess", "DisableSerpentHunterUpgrade"], True),
]

EXPECTED = [
    "EndingCondition", "WorldLogic", "RegionBossPercent", "RegionBossType",
    "RegionSoftLogic", "GreatRunesRequired", "GreatRunesFinalBoss",
    "GreatRunesMountaintops", "GreatRunesPresent", "DeathlessRouting", "GracesPerRegion",
    "RegionAccessLogic", "RegionCount", "NumRegions", "NumRegionsRuneSource",
    "NumRegionsChain", "CompletionScaling", "CompletionScalingFloor",
    "CompletionScalingBasis", "GlobalScadutreeBlessing", "RandomStartRegion",
    "StartRegionFreebie", "RoyalAccess", "EarlyLeveling", "ExtraRegionLocks", "EnableDLC",
    "DLCOnly", "QuickStart", "DLCOnlyRuneCatchup", "ScadutreeFrontload", "MessmerKindle",
    "MessmerKindleRequired", "MessmerKindleMax", "DLCTimingOption", "EnemyRando",
    "MaterialRando", "DeathLink", "RandomizeStartingLoadout", "AutoEquipOption",
    "AutoUpgradeOption", "ProgressiveStoneBells", "ProgressiveBellCount",
    "ProgressiveBellEarlyCount", "ProgressivePhysick", "CraftingKitOption",
    "RandomizeEnia", "MapOption", "SmithingBellBearingOption", "MerchantBellLogic",
    "SpellShopSpellsOnly", "EarlyLegacyDungeonsEarly", "LocalItemOnly",
    "ExcludeLocalItemOnly", "ERImportantLocations", "ERExcludeLocations",
    "ExcludedLocationBehaviorOption", "MissableLocationBehaviorOption", "DungeonSweep",
    "GraceSweep", "NoWeaponRequirements", "SwapMultiBoss", "BossRunesMatchOriginal",
    "ImpoliteEnemies", "DisableSerpentHunterUpgrade", "BellPhysickOption", "TorrentStart",
    "FlaskUpgradeOption", "BlessingOption", "SoftProgression", "TidyFunConsumables",
    "SoftConsumableShop", "DerandomizeGurranq", "DerandomizeQuestlines", "LocationPool",
    "DLCGearCuration", "JunkRetention", "JunkRetentionStyle", "FillerReplacement",
    "NoSpiritAshes", "ProgressiveFlasks", "ProgressiveFlaskEarlyCount",
    "ProgressiveGlovewortBells", "PoolBuilder", "PoolBuilderDLCGear",
    "ProgressiveItems",   # the new consolidated field (85th)
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
        sys.exit(f"ERROR: GROUPS != EXPECTED. missing={sorted(set(EXPECTED)-set(grouped))} "
                 f"extra={sorted(set(grouped)-set(EXPECTED))} "
                 f"dupes={sorted({c for c in grouped if grouped.count(c)>1})}")
    if len(grouped) != 85:
        sys.exit(f"ERROR: expected 85 options, got {len(grouped)}")

    if not os.path.isfile(TARGET):
        sys.exit(f"ERROR: not found: {TARGET}")
    size = os.path.getsize(TARGET)
    with open(TARGET, "rb") as f:
        orig = f.read()
    if len(orig) != size:
        sys.exit(f"ERROR: short read ({len(orig)} != {size}) -- I/O truncation; aborting.")
    if TAIL_SYMBOL not in orig:
        sys.exit(f"ERROR: tail symbol {TAIL_SYMBOL!r} missing -- source truncated; aborting.")

    eol = _detect_eol(orig)
    data = orig

    # (A) insert ProgressiveItems class
    if CLASS_PRESENT not in data:
        if data.count(CLASS_ANCHOR) != 1:
            sys.exit(f"ERROR: class anchor {CLASS_ANCHOR!r} found {data.count(CLASS_ANCHOR)}x. Aborting.")
        block = eol.join(CLASS_LINES) + eol
        data = data.replace(CLASS_ANCHOR, block + CLASS_ANCHOR, 1)

    # (B) insert dataclass field
    if FIELD_PRESENT not in data:
        if data.count(FIELD_ANCHOR) != 1:
            sys.exit(f"ERROR: field anchor {FIELD_ANCHOR!r} found {data.count(FIELD_ANCHOR)}x. Aborting.")
        data = data.replace(FIELD_ANCHOR, FIELD_LINE + eol + FIELD_ANCHOR, 1)

    # every referenced class now available (defined or imported)
    for c in EXPECTED:
        if c in IMPORTED:
            if c.encode() not in data:
                sys.exit(f"ERROR: imported class {c} not found. Aborting.")
        elif (b"class " + c.encode() + b"(") not in data:
            sys.exit(f"ERROR: class {c} referenced but not defined. Aborting.")

    # (C) rebuild option_groups (supersede)
    data = PRIOR_MARKER_RE.sub(b"", data)
    if data.count(ANCHOR_GROUPS) != 1:
        sys.exit(f"ERROR: anchor {ANCHOR_GROUPS!r} found {data.count(ANCHOR_GROUPS)}x after marker strip. Aborting.")
    idx = data.index(ANCHOR_GROUPS)
    payload = (MARKER.decode() + "\n" + _build_block_text()).encode("utf-8").replace(b"\n", eol)
    new = data[:idx] + payload

    if new == orig:
        print("Already applied -- progressive_items present and groups identical. No change.")
        return

    for c in EXPECTED:
        if payload.count(b"        " + c.encode() + b",") != 1:
            sys.exit(f"ERROR: class {c} appears {payload.count(b'        '+c.encode()+b',')}x in new block (want 1). Aborting.")
    if payload.count(b"start_collapsed=True") != 2:
        sys.exit(f"ERROR: expected 2 collapsed groups, got {payload.count(b'start_collapsed=True')}. Aborting.")

    try:
        compile(new.decode("utf-8"), TARGET, "exec")
    except SyntaxError as e:
        sys.exit(f"ERROR: rewritten options.py does not compile: {e}. Aborting (no write).")

    bak = TARGET + ".bak_progressiveitems"
    with open(bak, "wb") as f:
        f.write(orig)
    with open(TARGET, "wb") as f:
        f.write(new)
    with open(TARGET, "rb") as f:
        chk = f.read()
    if chk != new or CLASS_PRESENT not in chk or FIELD_PRESENT not in chk or MARKER not in chk:
        sys.exit(f"ERROR: verification AFTER write FAILED. Restore from {bak}")

    eol_name = "CRLF" if eol == b"\r\n" else "LF"
    print("OK: progressive_items OptionSet added; 4 legacy toggles moved to a collapsed group.")
    print(f"  target : {TARGET}")
    print(f"  backup : {bak}")
    print(f"  groups : {len(GROUPS)} (2 collapsed) ; members: {len(EXPECTED)}")
    print(f"  size   : {size} -> {len(chk)} ({len(chk) - size:+d} bytes); eol {eol_name}")
    print("Next: python patch_apworld_progressive_items_init.py  then  .\\build.ps1 -Apworld")


if __name__ == "__main__":
    main()
