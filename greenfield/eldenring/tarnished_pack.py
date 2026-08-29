"""Patch 1.17 (Tarnished Pack) item-pool catalog and ownership boundary.

The 2026-08-28 param diff established 31 new rows. The shipped English FMGs do not name them, so
the 26 player-equipment names below are joined to IDs only where independent acquisition evidence
settles the mapping: starting loadouts, field/shop lots, or invasion co-awards. Two NPC-only weapon
bases and three Spectral Steed unlock goods deliberately remain outside the item pool.

The equipment is available only when the explicit ownership option is enabled. Non-owner grant/use
behaviour remains unproven, so default-off is the safety boundary rather than a hopeful runtime
grant. ``gen_data.py`` adds this roster to the generated catalog and gives it honorary S tier.

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

# Player-receivable equipment only. Sources: the verified parameter/MSB census on #1096 plus live
# menu witnesses; public post-release acquisition guides independently corroborate the display
# names and routes. 3_910_000 and 13_900_000 are invasion-NPC weapon bases, not separate rewards.
TARNISHED_PACK_EQUIPMENT = {
    "Leontiel's Greatsword": 3_560_000,
    "Hefty Scimitar": 8_530_000,
    "Golden Order Flail": 13_510_000,
    "Silver Grooved Shield": 31_540_000,
    "Ritual Thrusting Shield": 62_520_000,
    "Reverse-Bladed Sword": 64_530_000,
    "Reed Great Katana": 66_530_000,
    "Idus Sword": 67_530_000,
    "Broken Gold Mask": 0x1000_0000 | 5_340_000,
    "Gold Tattoo (Chest)": 0x1000_0000 | 5_340_100,
    "Gold Tattoo (Arm)": 0x1000_0000 | 5_340_200,
    "Gold Tattoo (Leg)": 0x1000_0000 | 5_340_300,
    "Silver Grooved Helm": 0x1000_0000 | 5_350_000,
    "Silver Grooved Armor": 0x1000_0000 | 5_350_100,
    "Silver Grooved Gauntlets": 0x1000_0000 | 5_350_200,
    "Silver Grooved Greaves": 0x1000_0000 | 5_350_300,
    "Silver Grooved Armor (Altered)": 0x1000_0000 | 5_351_100,
    "Leontiel's Hat": 0x1000_0000 | 5_360_000,
    "Leontiel's Armor": 0x1000_0000 | 5_360_100,
    "Leontiel's Leather Gloves": 0x1000_0000 | 5_360_200,
    "Leontiel's Boots": 0x1000_0000 | 5_360_300,
    "Leontiel's Hat (Altered)": 0x1000_0000 | 5_361_000,
    "Steel Helm": 0x1000_0000 | 5_370_000,
    "Steel Armor": 0x1000_0000 | 5_370_100,
    "Steel Gauntlets": 0x1000_0000 | 5_370_200,
    "Steel Greaves": 0x1000_0000 | 5_370_300,
}

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
        dlc_on: bool, dlc_item_names, item_catalog: Mapping[str, int],
        tarnished_pack_on: bool = False) -> "frozenset[str]":
    """Return names no pool-augmentation path may inject.

    DLC items retain their existing option-dependent behaviour. Tarnished Pack equipment is
    admitted only when its explicit ownership toggle is on (#1096).
    """
    dlc = frozenset() if dlc_on else frozenset(dlc_item_names)
    tarnished = frozenset() if tarnished_pack_on else tarnished_pack_names(item_catalog)
    return dlc | tarnished
