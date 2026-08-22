"""tarnished_pack.py -- pool exclusion for the Elden Ring Tarnished Pack (2026-08-28).

WHY THIS EXISTS
---------------
The Tarnished Pack adds 2 starting classes, 4 armor sets, and 3 Torrent skins as an ENTITLEMENT
unlock. Placing a pack item for a player who does not own the pack is unwinnable in exactly the way
a DLC item is unwinnable in a base-only seed. #241's ruling is to exclude the new items from the
pool ENTIRELY -- there is no `enable_tarnished_pack` option yet -- so this exclusion is
UNCONDITIONAL, unlike the DLC exclusion which only fires when `enable_dlc` is off.

THE ONE PATCH-DAY STEP (2026-08-28)
-----------------------------------
The new items' catalog NAMES do not exist until the regulation ships. On patch day, AFTER the fresh
Windows param dump + regen (#241), paste the new armor (and any new goods) catalog names -- exactly
as they appear in `ITEM_CATALOG` post-regen -- into `TARNISHED_PACK_ITEM_NAMES` below. No other
wiring is required: `core` publishes this set into `gf_dlc_excluded`, which every pool-augmentation
path already reads (filler_budget, pool_builder, presence_floor, progressive, finale, scadu_supply,
filler_foreign, ...). The starting CLASSES are `CharaInitParam` loadouts, not catalog items, so they
do not enter the item pool and need nothing here; the Torrent skins are cosmetic and likewise not
catalog items. Only the ARMOR (and any new GOODS) can be drawn as juice/filler -- those are what
this set names.

    HAND-MAINTAINED, NOT GENERATED. This module survives regen; do NOT move these names into the
    generated item_ids.py (regen would overwrite them). Names must match ITEM_CATALOG exactly.

Kept AP-free on purpose (no BaseClasses/Options import), so the decision is host-testable without the
AP env -- the same "separate the decision from the I/O" split the rest of the package uses.
"""

# Empty until 2026-08-28. See the module docstring for the single patch-day step. A NON-empty set
# here before patch day would silently drop real items from the pool, so a test pins it empty.
TARNISHED_PACK_ITEM_NAMES: "frozenset[str]" = frozenset()


def pool_excluded_names(dlc_on: bool, dlc_item_names) -> "frozenset[str]":
    """The catalog NAMES no pool-augmentation path may inject, resolved once so every consumer reads
    the same decision (core publishes it as ``gf_dlc_excluded``).

    DLC items are excluded only when DLC is OFF; Tarnished Pack items are excluded UNCONDITIONALLY
    (#241 -- no owner-entitlement option exists yet). Reads ``TARNISHED_PACK_ITEM_NAMES`` at call
    time, so a patch-day edit to that set takes effect with no other change.
    """
    dlc = frozenset() if dlc_on else frozenset(dlc_item_names)
    return dlc | TARNISHED_PACK_ITEM_NAMES
