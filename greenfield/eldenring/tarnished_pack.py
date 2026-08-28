"""Patch 1.17 (Tarnished Pack) item-pool safety.

The 2026-08-28 param diff established 31 new base items, but the shipped English FMGs do not yet
name them and non-owner grant/use behaviour has not been proven. Until #1096 resolves those two
questions, these items must never enter an Archipelago pool.

IDs, rather than names, are the stable boundary here: the generated catalog maps display names to
the game's category-qualified ``FullID`` values. When a later FMG refresh makes any of these rows
visible to the catalog, this module resolves their names and excludes them automatically. On the
current data the resolution is deliberately empty, so existing seeds are unchanged.

Source: clean pre-1.17/current ``gen_inputs.db`` param-table diff recorded on #1096. Weapon rows
are collapsed through ``originEquipWep`` so reinforcement variants count as one base item.
"""

from typing import Mapping


# Raw param row IDs added by Patch 1.17. Keep the categories separate: the same raw integer can
# legally occur in more than one game item table, while FullID's high nibble disambiguates them.
TARNISHED_PACK_WEAPON_IDS = frozenset({
    3_560_000,
    3_910_000,
    8_530_000,
    13_510_000,
    13_900_000,
    31_540_000,
    62_520_000,
    64_530_000,
    66_530_000,
    67_530_000,
})

TARNISHED_PACK_ARMOR_IDS = frozenset({
    5_340_000, 5_340_100, 5_340_200, 5_340_300,
    5_350_000, 5_350_100, 5_350_200, 5_350_300, 5_351_100,
    5_360_000, 5_360_100, 5_360_200, 5_360_300, 5_361_000,
    5_370_000, 5_370_100, 5_370_200, 5_370_300,
})

TARNISHED_PACK_GOODS_IDS = frozenset({2_009_600, 2_009_610, 2_009_620})

# FullID category tags match ItemId::category in the client and the generated ITEM_CATALOG:
# weapons=0x0..., armor=0x1..., goods=0x4....
TARNISHED_PACK_FULL_IDS = frozenset(
    TARNISHED_PACK_WEAPON_IDS
    | {0x1000_0000 | row_id for row_id in TARNISHED_PACK_ARMOR_IDS}
    | {0x4000_0000 | row_id for row_id in TARNISHED_PACK_GOODS_IDS}
)


def tarnished_pack_names(item_catalog: Mapping[str, int]) -> "frozenset[str]":
    """Resolve every currently named Patch 1.17 item from the generated item catalog."""
    return frozenset(
        name for name, full_id in item_catalog.items() if full_id in TARNISHED_PACK_FULL_IDS)


def pool_excluded_names(
        dlc_on: bool, dlc_item_names, item_catalog: Mapping[str, int]) -> "frozenset[str]":
    """Return names no pool-augmentation path may inject.

    DLC items retain their existing option-dependent behaviour. Patch 1.17 items are excluded
    unconditionally until an explicit, evidence-backed entitlement option is implemented (#1096).
    """
    dlc = frozenset() if dlc_on else frozenset(dlc_item_names)
    return dlc | tarnished_pack_names(item_catalog)
