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

Ships two independent toggles (default OFF):
  - Progressive Flasks -> "Progressive Golden Seed" (flask CHARGES; good 10010, cap 30) and
    "Progressive Sacred Tear" (flask POTENCY; good 10020, cap 12). Both are fungible: every copy
    grants the same good, which the player spends at a grace/church.
  - Progressive Stonesword Keys -> "Progressive Stonesword Key" (good 8000). Each copy grants one
    Stonesword Key; the player spends it on an Imp Statue seal.

Every progressive copy is `useful`, NEVER progression -- Region Locks stay the sole progression gate,
so winnability is unaffected. create_items adds a fixed count of copies per active item; core's
count-neutral fill (slots = total_locations - len(pool)) means each copy displaces one filler/Rune
tail item, keeping the pool count-exact.
"""
from typing import Any, Dict, List

from BaseClasses import ItemClassification
from Options import Toggle
from ..registry import Feature, register

_GOODS_NIBBLE = 0x40000000  # ER FullID category nibble for GOODS (mirrors core._GOODS_NIBBLE)

# ---- progressive item names -------------------------------------------------------------------
PROG_GOLDEN_SEED = "Progressive Golden Seed"
PROG_SACRED_TEAR = "Progressive Sacred Tear"
PROG_STONESWORD_KEY = "Progressive Stonesword Key"

# ---- vanilla goods ladders (RE-EXPRESSED vanilla EquipParamGoods ids; matt-free) --------------
# Fungible flasks repeat the same good up to the vanilla max; the stonesword key repeats good 8000.
# Ladder length = the meaningful cap (client overflows extra copies to a Lord's Rune).
_GOODS_LADDERS: Dict[str, List[int]] = {
    PROG_GOLDEN_SEED: [10010] * 30,  # Golden Seed (flask charges); 30 = max charges
    PROG_SACRED_TEAR: [10020] * 12,  # Sacred Tear (flask potency); 12 = max potency
    PROG_STONESWORD_KEY: [8000] * 10,  # Stonesword Key; 10 copies = a generous supply
}

# How many copies of each progressive item to place in the pool when its toggle is on. Bounded well
# under the ladder length so copies land inside the meaningful ladder (no overflow spam), and small
# enough to stay comfortably count-neutral against the filler tail.
_POOL_COUNTS: Dict[str, int] = {
    PROG_GOLDEN_SEED: 8,
    PROG_SACRED_TEAR: 6,
    PROG_STONESWORD_KEY: 6,
}

# Which toggle activates which progressive items.
_FLASK_ITEMS = (PROG_GOLDEN_SEED, PROG_SACRED_TEAR)
_KEY_ITEMS = (PROG_STONESWORD_KEY,)


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


@register
class Progressive(Feature):
    name = "progressive"
    OPTIONS = {
        "progressive_flasks": ProgressiveFlasks,
        "progressive_stonesword_keys": ProgressiveStoneswordKeys,
    }
    # All progressive copies are `useful` (never progression -> Region Locks stay the sole gate).
    ITEMS = {
        PROG_GOLDEN_SEED: ItemClassification.useful,
        PROG_SACRED_TEAR: ItemClassification.useful,
        PROG_STONESWORD_KEY: ItemClassification.useful,
    }

    # ---- helpers ------------------------------------------------------------------------------
    def _active_items(self, world) -> List[str]:
        active: List[str] = []
        flasks = getattr(world.options, "progressive_flasks", None)
        keys = getattr(world.options, "progressive_stonesword_keys", None)
        if flasks and flasks.value:
            active += list(_FLASK_ITEMS)
        if keys and keys.value:
            active += list(_KEY_ITEMS)
        return active

    # ---- hooks --------------------------------------------------------------------------------
    def create_items(self, world) -> List:
        # Add the configured number of copies of each active progressive item. core's count-neutral
        # fill (slots = total_locations - len(pool)) trims one filler-tail item per copy added here.
        pool: List = []
        for name in self._active_items(world):
            pool += [world.create_item(name) for _ in range(_POOL_COUNTS[name])]
        return pool

    def slot_data(self, world) -> Dict[str, Any]:
        # progressiveGrants = {item_name: [{"goods": FullID, "flags": []}, ...]}. Empty {} when no
        # progressive toggle is on. Flags are empty: these are hand-in / spend-at-grace goods with
        # no shop-unlock event flag (Option-A path, like the matt-derived apworld's consumables).
        grants: Dict[str, List[Dict[str, Any]]] = {}
        for name in self._active_items(world):
            grants[name] = [{"goods": good | _GOODS_NIBBLE, "flags": []}
                            for good in _GOODS_LADDERS[name]]
        return {"progressiveGrants": grants}
