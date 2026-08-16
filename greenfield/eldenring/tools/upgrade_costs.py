"""Cost tables + count-accurate solvers for the per-sphere upgrade-curve analyzer.

Data-derived numbers live in the generated upgrade_costs_data.py (tools/gen_upgrade_costs.py, from
vanilla params + elden_ring_artifacts/*_per_level.txt). This module adds the KNOWN constants that
have no source file (Golden Rune values, Sacred Tear = 1/level), the flatten override, and the
solvers. If upgrade_costs_data is absent it degrades to small built-in defaults so imports still work.

Every solver is count-accurate: it spends the cumulative reachable multiset of items against the
per-level cost and returns the highest level fully paid for. `stones_per_level` mirrors the in-game
`flatten_regular_upgrades` knob (default = the real 2/4/6 ladder; flatten -> 1s).
"""
import os, sys
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:  # generated (data-derived); regenerate with tools/gen_upgrade_costs.py
    from upgrade_costs_data import (  # noqa: F401
        STANDARD_UPGRADE, SOMBER_UPGRADE, LEVEL_RUNE_COST_TABLE,
        FLASK_BASE_CHARGES, FLASK_CHARGE_SEED_COST, SCADUTREE_FRAGMENT_COST, REVERED_ASH_COST,
    )
except ImportError:  # minimal fallbacks so the module imports without the generated data
    STANDARD_UPGRADE = [(i, f"Smithing Stone [{(i-1)//3+1}]", (2, 4, 6)[(i-1) % 3]) for i in range(1, 25)] + \
                       [(25, "Ancient Dragon Smithing Stone", 1)]
    SOMBER_UPGRADE = [(i, f"Somber Smithing Stone [{i}]", 1) for i in range(1, 10)] + \
                     [(10, "Somber Ancient Dragon Smithing Stone", 1)]
    LEVEL_RUNE_COST_TABLE = {}
    FLASK_BASE_CHARGES = 4
    FLASK_CHARGE_SEED_COST = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]
    SCADUTREE_FRAGMENT_COST = [1] + [2] * 8 + [3] * 11
    REVERED_ASH_COST = [1, 1, 1, 2, 2, 3, 3, 3, 4, 5]

# ---------------------------------------------------------------------------------------------
# Rune item -> runes granted. DERIVED, and it was a hand-list until 2026-08-16.
#
# 🛑 THE HAND-LIST WAS WRONG ON 7 OF ITS 22 ROWS (#749), and its own header said "KNOWN constants
# (no source file)" while the source file existed. Hero's Rune [1]-[5] read
# 2,500 / 3,800 / 5,000 / 6,250 / 7,500 against the params' 15,000-35,000 -- and those five numbers
# are Golden Rune [7]/[9]/[10]/[11]/[12]'s payouts, so whatever wrote it was reading down the wrong
# column. Shadow Realm Rune [1]/[2] read 1,000/1,600 against 7,500/10,000. It also omitted nine
# catalog runes outright (Broken, Leda's, Marika's, Rune of an Unsung Hero, Shadow Realm [3]-[7]).
# The other 15 rows were right, which is exactly why nobody noticed.
#
# Retyping the seven would reproduce the defect class rather than the defect, so this DERIVES:
# `shop_stock_data.RUNE_PAYOUT` is generated from EquipParamGoods.refId_default ->
# SpEffectParam.soul, and is already the source `item_categories.rune_payout()` reads. One datum,
# one source. `test_gf_upgrade_costs_runes` asserts the equality and types no payouts.
#
# ⚠️ THE FALLBACK IS DELIBERATELY EMPTY, not a smaller hand-list. This module degrades rather than
# raising when the generated data is absent (see the try/except above), and that property has to
# survive -- but a partial rune table is worse than none here: the solvers below spend a multiset
# against a cost, so an item silently worth 0 under-counts, while a MISSING item is a KeyError the
# caller can see. Nothing in the world imports RUNE_VALUE today; the analyzer is its only consumer.
def _derive_rune_values() -> Dict[str, int]:
    _GOODS_NIBBLE, _ROW_MASK = 0x40000000, 0x0FFFFFFF
    try:
        _here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, _here)
        from shop_stock_data import RUNE_PAYOUT   # noqa: PLC0415 -- generated leaf
        from item_ids import ITEM_CATALOG         # noqa: PLC0415 -- generated leaf
    except ImportError:
        return {}
    out: Dict[str, int] = {}
    for name, full in ITEM_CATALOG.items():
        if (full & 0xF0000000) != _GOODS_NIBBLE:
            continue
        payout = RUNE_PAYOUT.get(full & _ROW_MASK)
        if payout is not None:
            out[name] = int(payout)
    return out


RUNE_VALUE: Dict[str, int] = _derive_rune_values()

# KNOWN: Sacred Tears upgrade flask potency, one per level (~12 in base game). No source file.
FLASK_POTENCY_TEAR_COST: List[int] = [1] * 12


def level_rune_cost(lvl: int) -> int:
    """Runes to advance TO character level `lvl` (data-derived table; formula fallback past its range)."""
    if lvl <= 1:
        return 0
    if lvl in LEVEL_RUNE_COST_TABLE:
        return LEVEL_RUNE_COST_TABLE[lvl]
    return max(1, round(0.02 * lvl**3 + 3.06 * lvl**2 + 105.6 * lvl - 895))


# ---------------------------------------------------------------------------------------------
# Solvers -- all count-accurate. `have` is a name->count multiset of REACHABLE items.

def _flatten_standard(stones_per_level) -> List[Tuple[int, str, int]]:
    """Flatten override for STANDARD_UPGRADE counts (tier assignment kept). stones_per_level:
    None = real ladder | int N = N/level | list len 25 (per-level) / 8 (per-tier) / 3 (within-band)."""
    if stones_per_level is None:
        return STANDARD_UPGRADE
    out = []
    for i, (lvl, stone, cnt) in enumerate(STANDARD_UPGRADE):
        if isinstance(stones_per_level, int):
            new = min(cnt, stones_per_level) if lvl < 25 else cnt   # cap-at-N (client lower-only)
        elif len(stones_per_level) == 25:
            new = stones_per_level[i]
        elif len(stones_per_level) == 3:
            new = cnt if lvl == 25 else stones_per_level[(lvl - 1) % 3]
        else:
            new = cnt if lvl == 25 else stones_per_level[(lvl - 1) // 3]
        out.append((lvl, stone, new))
    return out

def max_weapon_level(have: Dict[str, int], ladder: List[Tuple[int, str, int]]) -> int:
    pool = dict(have)
    for lvl, stone, cnt in ladder:
        if pool.get(stone, 0) < cnt:
            return lvl - 1
        pool[stone] -= cnt
    return ladder[-1][0]

def max_standard_level(have: Dict[str, int], stones_per_level=None) -> int:
    return max_weapon_level(have, _flatten_standard(stones_per_level))

def max_somber_level(have: Dict[str, int]) -> int:
    return max_weapon_level(have, SOMBER_UPGRADE)

def _max_from_steps(count: int, step_costs: List[int]) -> int:
    spent = 0
    for i, c in enumerate(step_costs):
        spent += c
        if spent > count:
            return i
    return len(step_costs)

def max_flask_charges(golden_seeds: int) -> int:
    """TOTAL flask charges (base + seed-bought upgrades)."""
    return FLASK_BASE_CHARGES + _max_from_steps(golden_seeds, FLASK_CHARGE_SEED_COST)

def max_flask_potency(sacred_tears: int) -> int:
    return _max_from_steps(sacred_tears, FLASK_POTENCY_TEAR_COST)

def max_scadutree(fragments: int) -> int:
    return _max_from_steps(fragments, SCADUTREE_FRAGMENT_COST)

def max_revered(ashes: int) -> int:
    return _max_from_steps(ashes, REVERED_ASH_COST)

def max_character_level(total_runes: int, start_level: int = 1, cap: int = 713) -> int:
    lvl, spent = start_level, 0
    while lvl < cap:
        spent += level_rune_cost(lvl + 1)
        if spent > total_runes:
            break
        lvl += 1
    return lvl

def runes_from_items(have: Dict[str, int]) -> int:
    return sum(RUNE_VALUE.get(n, 0) * c for n, c in have.items())
