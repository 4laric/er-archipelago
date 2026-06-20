# -*- coding: utf-8 -*-
"""DRAFT — Phase 0 data for SPEC-relevance-uplift.md (Alaric, 2026-06-16).

Merge these into `Archipelago/worlds/eldenring/curation.py` on Windows (do NOT Edit the
live CRLF apworld file from the sandbox — see memory crlf-edit-truncation; patch via
Python + verify on disk). Names below are verified against items.py item_table keys.

Scope recap: dlc_only only. Defer worst DLC *consumable/material* filler from the pool,
inject an equal number of base-game juice (invariant injected<=skippable, count-neutral,
mirror of dlc_gear_curation in __init__.py:905). Gear is handled by dlc_gear_curation, not
here. Stones/upgrade access is a SEPARATE progression lever (see note at bottom), not part
of this count-neutral swap. Larval Tears are intentionally absent (no Rennala = no respec
in dlc_only).
"""

from .items import item_table, ERItemCategory
from .Items import ItemClassification  # adjust import to match curation.py's existing one

# ---------------------------------------------------------------------------
# CUT SET — removable DLC filler (funds the swap)
# ---------------------------------------------------------------------------
# Predicate-based, NOT a hand denylist: anything that is DLC + GOODS + filler-classified +
# not explicitly kept. Codegen can dump the resolved explicit set to a report for review.
# Reuse the ammo guard (er-ammo-filler-guard): never catch a named "ammo" that is actually
# a weapon by id-range (Bolt of Gransax etc.).

UPLIFT_KEEP_DLC = frozenset({
    # one-off "actually keep this DLC filler" decisions surfaced by the report
})

def is_uplift_cut_dlc(name: str) -> bool:
    item = item_table.get(name)
    if item is None:
        return False
    if not getattr(item, "is_dlc", False):
        return False
    if item.classification != ItemClassification.filler:
        return False
    if item.category != ERItemCategory.GOODS:
        return False
    if name in UPLIFT_KEEP_DLC:
        return False
    # TODO: id-range ammo guard — exclude bolt/arrow ranges that are filler-but-wanted,
    # mirror er-ammo-filler-guard's WEAPON-promotion exclusion.
    return True

# Worst-first ordering when budget < cut set (drop crafting mats before decent throwables).
# Provisional: lower runes-value / pure-material first. Refine against the report.
def uplift_cut_drop_rank(name: str) -> int:
    item = item_table.get(name)
    return getattr(item, "runes", 0) or 0   # 0-rune crafting mats sort first


# ---------------------------------------------------------------------------
# INJECT SET — base-game juice (is_dlc == False only)
# ---------------------------------------------------------------------------
# UNIQUES — inject once each, useful-tier. (S-tier WEAPON/ARMOR/spell injects are pulled
# programmatically from item_tiers.ITEM_TIERS == "S" filtered to is_dlc==False, so they're
# NOT hand-listed here. The lists below are the categories item_tiers doesn't cover yet.)

# Top spirit ashes (base game). Biggest solo-run difficulty lever. Verified keys.
UPLIFT_SPIRITS_TOP = frozenset({
    "Mimic Tear Ashes",
    "Black Knife Tiche",
    "Lhutel the Headless",
    "Redmane Knight Ogha",
    "Ancient Dragon Knight Kristoff",
    "Greatshield Soldier Ashes",
    "Latenna the Albinauric",
    "Nightmaiden & Swordstress Puppets",
    "Cleanrot Knight Finlay",
    "Dung Eater Puppet",
    "Banished Knight Oleg",
})

# Talismans — PROVISIONAL S/A hand list seeded from community PvE refs (gameleap /
# rankedboost / gamerant, fetched 2026-06-16). Phase 2: replace by folding ACCESSORY into
# the item_tiers.tsv pipeline like weapons/armor/spells. Verified keys.
UPLIFT_TALISMANS_S = frozenset({
    "Erdtree's Favor +2",
    "Radagon's Soreseal",
    "Marika's Soreseal",
    "Shard of Alexander",
    "Godfrey Icon",
    "Radagon Icon",
    "Old Lord's Talisman",
    "Gold Scarab",
    "Millicent's Prosthesis",
    "Ritual Sword Talisman",
    "Graven-Mass Talisman",
    "Dragoncrest Greatshield Talisman",
    "Crimson Amber Medallion +2",
    "Blessed Dew Talisman",
})

# Permanent character upgrades — count-capped uniques (extra copies are wasted).
UPLIFT_UNIQUE_CAPS = {
    "Memory Stone": 8,    # vanilla count
    "Talisman Pouch": 3,  # vanilla count
}

# Spirit-ash UPGRADE access — pairs with UPLIFT_SPIRITS_TOP so the spirits can scale.
# Non-progression, so these may ride the count-neutral swap. (Grave Glovewort = regular
# spirits; Ghost-Glovewort = +tier spirits.)
UPLIFT_GLOVEWORT_BELLS = frozenset({
    "Glovewort Picker's Bell Bearing [1]",
    "Glovewort Picker's Bell Bearing [2]",
    "Glovewort Picker's Bell Bearing [3]",
    "Ghost-Glovewort Picker's Bell Bearing [1]",
    "Ghost-Glovewort Picker's Bell Bearing [2]",
    "Ghost-Glovewort Picker's Bell Bearing [3]",
})

# STACKABLES — repeat to fill the remaining budget, filler-tier, weighted.
# Juicy runes: select by runes-value rather than hand-list, so it stays in sync with
# items.py. Numen's Rune (2913) = 12500 runes is the archetype.
UPLIFT_RUNE_MIN_VALUE = 5000   # tune; Numen's=12500, Lord's/Hero's/Golden[10+] qualify

def is_uplift_rune(name: str) -> bool:
    item = item_table.get(name)
    return (item is not None
            and not getattr(item, "is_dlc", False)
            and (getattr(item, "runes", 0) or 0) >= UPLIFT_RUNE_MIN_VALUE)

# Flask economy. Verify exact keys against item_table before committing.
UPLIFT_SEEDS_TEARS = frozenset({
    "Golden Seed",
    "Sacred Tear",
})

# Physick (Crystal) tears — each unique in vanilla; inject once each. Build from the
# ACCESSORY/GOODS crystal-tear id range in items.py (left as a TODO list-build, not
# hand-enumerated here).

# Weighted distribution for the stackable remainder (tune against the report).
UPLIFT_STACKABLE_WEIGHTS = {
    "runes":        40,   # is_uplift_rune pool
    "seeds_tears":  20,   # UPLIFT_SEEDS_TEARS
    "physick":      10,   # crystal tears
    "glovewort":    10,   # UPLIFT_GLOVEWORT_BELLS (if spirits injected)
    "misc_consum":  20,   # top boluses / grease / etc.
    # NOTE: NO raw smithing/somber stones here — see stone lever below.
}

# ---------------------------------------------------------------------------
# STONE / UPGRADE ACCESS — SEPARATE LEVER (not part of the count-neutral swap)
# ---------------------------------------------------------------------------
# A pile of high stones is useless: weapons climb +1->+2->...; you need the whole ladder.
# Solve via the Miner's Bell Bearings, which unlock the full stone range for purchase at
# the Twin Maidens (Roundtable is reachable in dlc_only). These are classification=
# progression in items.py (8951-8959), so they must go on the GUARANTEED progression-
# injectable path (the one the rune-skip demand-drop frees in-world slots for), NOT the
# filler swap. Gate the whole thing on auto_upgrade == OFF (with auto_upgrade on, weapons
# upgrade for free and none of this is needed). Dependency: shop-refresh-on-unlock
# (er-merchant-bell-bearing-logic / er-qol-patches-shop) so received bearings actually
# add stock.
UPLIFT_STONE_BELLS = frozenset({
    "Smithing-Stone Miner's Bell Bearing [1]",
    "Smithing-Stone Miner's Bell Bearing [2]",
    "Smithing-Stone Miner's Bell Bearing [3]",
    "Smithing-Stone Miner's Bell Bearing [4]",
    "Somberstone Miner's Bell Bearing [1]",
    "Somberstone Miner's Bell Bearing [2]",
    "Somberstone Miner's Bell Bearing [3]",
    "Somberstone Miner's Bell Bearing [4]",
    "Somberstone Miner's Bell Bearing [5]",
})
