"""SPEC-PARITY Phase 7 -- progressive items (COMPLETE).

Collapses a family of fungible/ordered upgrade pickups into a single "Progressive X" AP item whose
Kth received copy grants tier K, via the client's existing `progressiveGrants` contract. The client
already understands `progressiveGrants = {item_name: [{"goods": FullID, "flags": [...]}, ...]}`: it
tracks how many copies of `item_name` it has received and, on the Kth, grants the goods (and sets
any flags) at ladder index K-1. Copies past the ladder length overflow to a Lord's Rune client-side
(same pipeline the matt-derived apworld uses); we do not need to model overflow here.

Matt-free: every good id below is a *vanilla* EquipParamGoods id (game data, re-expressed here from
the vanilla item tables -- NOT any curated/location set). GOODS FullID = good_id | _GOODS_NIBBLE
(0x40000000), matching core's _AP_IDS_TO_ITEM_IDS convention.

Ships three independent toggles (default OFF):
  - Progressive Flasks -> "Progressive Golden Seed" (flask CHARGES; good 10010, cap 30) and
    "Progressive Sacred Tear" (flask POTENCY; good 10020, cap 12). Both are fungible: every copy
    grants the same good, which the player spends at a grace/church.
  - Progressive Stonesword Keys -> "Progressive Stonesword Key" (good 8000). Each copy grants one
    Stonesword Key; the player spends it on an Imp Statue seal.
  - Progressive Stone Bells -> "Progressive Smithing-Stone Miner's Bell Bearing" (4 tiers) and
    "Progressive Somberstone Miner's Bell Bearing" (5 tiers). Ported from the matt-based apworld
    (SPEC-PARITY: ProgressiveItems stone_bells). The Kth copy grants that tier's real bell bearing
    good (8951-8954 Smithing / 8955-8959 Somber) AND sets the Twin Maiden ShopLineupParam
    eventFlag_forStock values for that rung -- setting the flag IS the shop unlock, no hand-in.
    Flags verified against vanilla_er/ShopLineupParam.csv (Twin Maiden shop 1018xx: item 10100 ->
    flag 280080, etc.). 1 copy of each is forced to sphere 0 (generate_early -> early_items) so the
    upgrade ramp opens at the start; the rest distribute normally. Copies past the last tier are
    silent no-ops client-side (the k < tiers guard).

Every progressive copy is `useful`, NEVER progression -- Region Locks stay the sole progression gate,
so winnability is unaffected. create_items adds a fixed count of copies per active item; core's
count-neutral fill (slots = total_locations - len(pool)) means each copy displaces one filler/Rune
tail item, keeping the pool count-exact.
"""
from typing import Any, Dict, List

from BaseClasses import ItemClassification
from Options import Toggle
from ..registry import Feature, register
from .. import contract

_GOODS_NIBBLE = 0x40000000  # ER FullID category nibble for GOODS (mirrors core._GOODS_NIBBLE)

# ---- progressive item names -------------------------------------------------------------------
PROG_GOLDEN_SEED = "Progressive Golden Seed"
PROG_SACRED_TEAR = "Progressive Sacred Tear"
PROG_STONESWORD_KEY = "Progressive Stonesword Key"
PROG_SMITHING_BELL = "Progressive Smithing-Stone Miner's Bell Bearing"
PROG_SOMBER_BELL = "Progressive Somberstone Miner's Bell Bearing"

# ---- vanilla goods ladders (RE-EXPRESSED vanilla EquipParamGoods ids; matt-free) --------------
# Fungible flasks repeat the same good up to the vanilla max; the stonesword key repeats good 8000.
# Ladder length = the meaningful cap (client overflows extra copies to a Lord's Rune).
_GOODS_LADDERS: Dict[str, List[int]] = {
    PROG_GOLDEN_SEED: [10010] * 30,  # Golden Seed (flask charges); 30 = max charges
    PROG_SACRED_TEAR: [10020] * 12,  # Sacred Tear (flask potency); 12 = max potency
    PROG_STONESWORD_KEY: [8000] * 10,  # Stonesword Key; 10 copies = a generous supply
}

# ---- progressive stone-bell grant ladders (goods + shop-unlock flags) -------------------------
# Each entry = {"goods": bell-bearing EquipParamGoods id, "flags": [Twin Maiden ShopLineupParam
# eventFlag_forStock values]}. Setting the flag(s) IS the shop unlock (no hand-over to the Twin
# Maidens needed). Goods 8951-8954 = Smithing-Stone Miner's Bell Bearing [1]-[4]; 8955-8959 =
# Somberstone [1]-[5]. Flags verified against vanilla_er/ShopLineupParam.csv (each stone bell tier
# unlocks two stone material tiers, except Somber [5] which unlocks one). Ported verbatim from the
# matt-based apworld's stone_bells.py -- same game version, same vanilla_er data.
_BELL_GRANTS: Dict[str, List[Dict[str, Any]]] = {
    PROG_SMITHING_BELL: [
        {"goods": 8951, "flags": [280080, 280090]},  # Smithing Stone [1],[2]
        {"goods": 8952, "flags": [280110, 280120]},  # Smithing Stone [3],[4]
        {"goods": 8953, "flags": [280140, 280150]},  # Smithing Stone [5],[6]
        {"goods": 8954, "flags": [280160, 280170]},  # Smithing Stone [7],[8]
    ],
    PROG_SOMBER_BELL: [
        {"goods": 8955, "flags": [280180, 280190]},  # Somber [1],[2]
        {"goods": 8956, "flags": [280200, 280210]},  # Somber [3],[4]
        {"goods": 8957, "flags": [280230, 280240]},  # Somber [5],[6]
        {"goods": 8958, "flags": [280250, 280260]},  # Somber [7],[8]
        {"goods": 8959, "flags": [280280]},          # Somber [9]
    ],
}

# How many copies of each progressive item to place in the pool when its toggle is on. Bounded well
# under the ladder length so copies land inside the meaningful ladder (no overflow spam), and small
# enough to stay comfortably count-neutral against the filler tail.
_POOL_COUNTS: Dict[str, int] = {
    PROG_GOLDEN_SEED: 8,
    PROG_SACRED_TEAR: 6,
    PROG_STONESWORD_KEY: 6,
    PROG_SMITHING_BELL: 5,   # 4 real tiers -> the 5th copy is a silent no-op (spreads the ramp)
    PROG_SOMBER_BELL: 5,     # exactly 5 tiers
}

# Copies of each progressive stone bell to FORCE into sphere 0 (no-item-reachable) via early_items,
# so the upgrade ladder has a first rung at the start. Because the item is progressive, 1 early copy
# guarantees an early first tier; the remaining pool copies distribute normally. Soft/capped by AP
# (bounded by pool availability + sphere-0 size), so it never fails gen.
_BELL_EARLY_COUNT: Dict[str, int] = {
    PROG_SMITHING_BELL: 1,
    PROG_SOMBER_BELL: 1,
}

# Which toggle activates which progressive items.
_FLASK_ITEMS = (PROG_GOLDEN_SEED, PROG_SACRED_TEAR)
_KEY_ITEMS = (PROG_STONESWORD_KEY,)
_BELL_ITEMS = (PROG_SMITHING_BELL, PROG_SOMBER_BELL)


class ProgressiveFlasks(Toggle):
    """Off (default): Golden Seeds / Sacred Tears (if in the pool) are discrete pickups. On: add
    Progressive Golden Seed and Progressive Sacred Tear items -- each copy you receive upgrades your
    flask charges / potency by one, spent at a grace or church. Flasks never gate logic, so this is
    always winnable."""
    display_name = "Progressive Flasks"


class ProgressiveStoneswordKeys(Toggle):
    """Off (default). On: add Progressive Stonesword Key items -- each copy grants one Stonesword
    Key for opening Imp Statue seals. Never gates logic (Region Locks are the only progression), so
    this is always winnable."""
    display_name = "Progressive Stonesword Keys"


class ProgressiveStoneBells(Toggle):
    """Off (default). On: add Progressive Smithing-Stone and Progressive Somberstone Miner's Bell
    Bearing items (5 copies of each in the filler pool, 1 of each forced to sphere 0). Each copy you
    receive unlocks the next tier of the Twin Maidens' smithing-stone shop directly (no hand-over),
    so weapon upgrade materials come online as you find copies. Never gates logic (Region Locks are
    the only progression), so this is always winnable."""
    display_name = "Progressive Stone Bell Bearings"


@register
class Progressive(Feature):
    name = "progressive"
    OPTIONS = {
        "progressive_flasks": ProgressiveFlasks,
        "progressive_stonesword_keys": ProgressiveStoneswordKeys,
        "progressive_stone_bells": ProgressiveStoneBells,
    }
    # All progressive copies are `useful` (never progression -> Region Locks stay the sole gate).
    ITEMS = {
        PROG_GOLDEN_SEED: ItemClassification.useful,
        PROG_SACRED_TEAR: ItemClassification.useful,
        PROG_STONESWORD_KEY: ItemClassification.useful,
        PROG_SMITHING_BELL: ItemClassification.useful,
        PROG_SOMBER_BELL: ItemClassification.useful,
    }

    # ---- helpers ------------------------------------------------------------------------------
    def _active_items(self, world) -> List[str]:
        active: List[str] = []
        flasks = getattr(world.options, "progressive_flasks", None)
        keys = getattr(world.options, "progressive_stonesword_keys", None)
        bells = getattr(world.options, "progressive_stone_bells", None)
        if flasks and flasks.value:
            active += list(_FLASK_ITEMS)
        if keys and keys.value:
            active += list(_KEY_ITEMS)
        if bells and bells.value:
            active += list(_BELL_ITEMS)
        return active

    def _grant_ladder(self, name: str) -> List[Dict[str, Any]]:
        """Client `progressiveGrants` ladder for one progressive item: an ordered list of
        {"goods": GOODS-packed FullID, "flags": [event flags]}. Fungible/keyed items (flasks,
        stonesword keys) repeat a single good with no flags; stone bells carry a per-tier good AND
        the shop-unlock flags for that rung."""
        if name in _BELL_GRANTS:
            return [{"goods": e["goods"] | _GOODS_NIBBLE, "flags": list(e["flags"])}
                    for e in _BELL_GRANTS[name]]
        return [{"goods": good | _GOODS_NIBBLE, "flags": []} for good in _GOODS_LADDERS[name]]

    # ---- hooks --------------------------------------------------------------------------------
    def generate_early(self, world) -> None:
        # Force a small number of stone-bell copies into sphere 0 (no-item-reachable) so the upgrade
        # ladder has an early first rung. AP's early_items biases placement of copies ALREADY in the
        # pool (added by create_items); it is soft + capped by pool availability and sphere-0 size, so
        # it never fails gen. Only the bells opt in (flasks/keys are fine wherever they land).
        active = set(self._active_items(world))
        early = world.multiworld.early_items[world.player]
        for name, n in _BELL_EARLY_COUNT.items():
            if name in active and n > 0:
                early[name] = early.get(name, 0) + n

    def create_items(self, world) -> List:
        # Add the configured number of copies of each active progressive item. core's count-neutral
        # fill (slots = total_locations - len(pool)) trims one filler-tail item per copy added here.
        pool: List = []
        for name in self._active_items(world):
            pool += [world.create_item(name) for _ in range(_POOL_COUNTS[name])]
        return pool

    def slot_data(self, world) -> Dict[str, Any]:
        # progressiveGrants = {item_name: [{"goods": FullID, "flags": [...]}, ...]}. Empty {} when no
        # progressive toggle is on. Flasks / stonesword keys carry empty flags (hand-in / spend-at-
        # grace goods); stone bells carry the Twin Maiden shop-unlock flags per rung (set = unlock).
        grants: Dict[str, List[Dict[str, Any]]] = {}
        for name in self._active_items(world):
            grants[name] = self._grant_ladder(name)
        return {contract.PROGRESSIVE_GRANTS: grants}
