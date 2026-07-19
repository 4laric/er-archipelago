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

Ships three independent toggles (progressive_flasks default ON; the others default OFF):
  - Progressive Flasks -> ONE item, "Progressive Flask Upgrade", replacing every Golden Seed and
    Sacred Tear check one-for-one. The flask is a HYBRID across two INDEPENDENT axes, and it rides
    BOTH wires at once (intentional, non-overlapping):
      * CHARGES = a reconciled LEVELED STATE (client-side, contract.flaskLadder). The Kth copy moves
        the flask charge target to flaskLadder[K-1]["charges"]; the client reconciles the live flask
        directly (a direct write to PlayerGameData.max_hp_flask -- CONFIRMED SAFE). A leveled charge
        target has no spend to heal, so it cannot trigger the re-grant CTD class.
      * POTENCY = GRANTED SACRED TEARS via progressiveGrants (the proven consumed/ledgered path). The
        Kth copy grants ONE consumed Sacred Tear (good 10020), and the player upgrades flask potency
        at a Site of Grace the vanilla way -- which correctly updates EVERY flask mirror (the
        inventory entry, the equipped/quickslot reference, AND the global GaItem). One Sacred Tear per
        copy => one ledger entry per stream index => no batching problem.
    WHY THE SPLIT: an earlier build tried to raise potency by an in-place inventory item-id swap
    (base+level*2). That CTD'd on death -- ER mirrors the flask tier across the inventory entry, the
    equipped/quickslot reference, AND the global GaItem, and death's flask-refill crashed on the
    half-updated state (playtest 2026-07-19). Granting a Sacred Tear and letting the player upgrade at
    a grace touches every mirror safely, exactly as vanilla does. (An even earlier build shipped the
    tears OWNED rather than consumed; reconcile.rs self-healed a SPENT tear and re-granted unbounded
    until the flask ran past its cap and CTD'd, playtest 2026-07-12 -- hence consumed=True is
    REQUIRED.) The charge axis's "later pickups buy less" deceleration is baked into the escalating
    charge-step weights; the potency axis is a flat +1 tear per copy. The ladder's LENGTH follows the
    kept seed/tear checks (num_regions / DLC scale it for free); when NONE are kept (dlc_only) a fixed
    12 copies are injected -- enough for both charges (max 14) and potency (max 12, one tear each) to
    fully max by copy 12. PROG_FLASK stays a pool item and the Golden Seed / Sacred Tear checks still
    SUBSTITUTE to it; the flask now appears in BOTH progressiveGrants (potency tears) and flaskLadder
    (charges) at once.
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
import itertools
from typing import Any, Dict, List

from BaseClasses import ItemClassification
from Options import Toggle
from ..registry import Feature, register
from .. import contract

try:  # the flask leveled-ladder length follows the kept Golden Seed / Sacred Tear checks
    from ..data import HUB, LOCATIONS
except Exception:
    HUB, LOCATIONS = "Roundtable Hold", {}
try:
    from ..item_ids import LOCATION_ITEM
except Exception:
    LOCATION_ITEM = {}

_GOODS_NIBBLE = 0x40000000  # ER FullID category nibble for GOODS (mirrors core._GOODS_NIBBLE)
_GOOD_SACRED_TEAR = 10020    # vanilla EquipParamGoods id for Sacred Tear (FullID 0x40000000|10020 =
                             # 1073751844, matches item_ids.py). The flask POTENCY axis grants these
                             # as consumed goods (the player upgrades potency at a grace the vanilla
                             # way, which updates every flask mirror -- see the module docstring).

# ---- progressive item names -------------------------------------------------------------------
PROG_FLASK = "Progressive Flask Upgrade"
PROG_STONESWORD_KEY = "Progressive Stonesword Key"
PROG_SMITHING_BELL = "Progressive Smithing-Stone Miner's Bell Bearing"
PROG_SOMBER_BELL = "Progressive Somberstone Miner's Bell Bearing"

# ---- vanilla goods ladders (RE-EXPRESSED vanilla EquipParamGoods ids; matt-free) --------------
# Fungible flasks repeat the same good up to the vanilla max; the stonesword key repeats good 8000.
# Ladder length = the meaningful cap (client overflows extra copies to a Lord's Rune).
_GOODS_LADDERS: Dict[str, List[int]] = {
    PROG_STONESWORD_KEY: [8000] * 10,  # Stonesword Key; 10 copies = a generous supply
}

# ---- unified flask LEVELED ladder (CHARGES axis) ----------------------------------------------
# The flask is a HYBRID. Its CHARGES axis is a reconciled LEVELED STATE (client-side): the Kth copy of
# PROG_FLASK moves the player's flask charge target to flaskLadder[K-1]["charges"], and the client
# reconciles the live flask with a direct write (PlayerGameData.max_hp_flask -- CONFIRMED SAFE). A
# leveled charge target has no spend to heal, so it cannot trigger the re-grant CTD class.
#
# Its POTENCY axis is NOT set from this ladder on the client -- it is GRANTED as consumed Sacred Tears
# via progressiveGrants (see _grant_ladder(PROG_FLASK) and the module docstring), because the in-place
# potency item-id swap CTD'd on death (ER mirrors flask tier across the inventory entry, the equipped/
# quickslot reference, AND the global GaItem; death's flask-refill crashed on the half-updated state,
# playtest 2026-07-19). Granting a tear and upgrading at a grace touches every mirror the vanilla way.
# The "potency" field below is therefore DOCUMENTATION ONLY (kept accurate = min(rung, 12), one tear
# per copy); the client takes potency from the ledgered tears, not this ladder.
#
# The deceleration the old design inherited from the vanilla cost table is baked into the ladder's
# escalating charge-step weights below.
#
# The vanilla per-level cost tables are RETAINED as documented vanilla data + the single-source datum
# tests/test_gf_progressive_flasks.py::test_cost_tables_match_tools guards against tools/upgrade_costs.py
# drift. (tools/ is a script package: sys.path hacks, no __init__, not guaranteed to ship in the
# apworld zip -- importing it at runtime would be a load-bearing fragility for a table that ~never
# changes.)
FLASK_CHARGE_SEED_COST: List[int] = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]   # vanilla seeds per charge level -> 30
FLASK_POTENCY_TEAR_COST: List[int] = [1] * 12                        # vanilla tears per potency level -> 12

# Leveled-ladder bounds (the wire contract, contract.flaskLadder): charges climb 2 -> 14 (12 steps),
# potency 0 -> 12 (12 steps); the last rung is (14, 12). NB the wire spec (2->14, 12 steps) is followed
# literally; vanilla's own base is 4 charges + 10 seed-bought steps (tools/upgrade_costs FLASK_BASE_
# CHARGES) -- see the deliverable note. Charge steps carry ESCALATING weights so the ladder rises fast
# early and slow late (the inherited deceleration). The POTENCY axis climbs a flat +1 PER RUNG (capped
# at 12): potency is granted as one consumed Sacred Tear per copy, so a rung MUST NOT advance potency
# by more than 1 (a +2 rung would need 2 tears at one copy = 2 ledger entries at one stream index = the
# batching the consumed-goods ledger forbids). See flask_ladder() -- potency is computed directly as
# min(rung, 12), NOT distributed through _cum_levels like charges.
FLASK_CHARGES_BASE = 2
FLASK_CHARGES_MAX = 14
FLASK_POTENCY_MAX = 12
_CHARGE_STEP_WEIGHTS: List[int] = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6]   # 12 steps (2 -> 14), escalating
_POTENCY_STEP_WEIGHTS: List[int] = list(FLASK_POTENCY_TEAR_COST)          # 12 flat steps; documentation only

# When NO Golden Seed / Sacred Tear check is kept (dlc_only, or a num_regions seed that seals every
# flask region), there are no substituted PROG_FLASK copies -- so inject a fixed count of copies and
# build a ladder that maxes by the last rung. 12 copies: one Sacred Tear per copy needs 12 copies to
# reach potency 12, and the escalating charge schedule reaches 14 at rung 12 -- so both axes fully max
# exactly at copy 12 (ladder length == copies == DLC_ONLY_FLASK_COPIES).
DLC_ONLY_FLASK_COPIES = 12


def _flasks_on(world) -> bool:
    o = getattr(world.options, "progressive_flasks", None)
    return bool(o is not None and o.value)


def _flask_check_count(world, regions) -> int:
    """How many of `regions`' locations vanilla-hold a Golden Seed / Sacred Tear this seed. Mirrors
    core's extras source (LOCATION_ITEM) and honours the DLC-off exclusion -- so it equals the
    PROG_FLASK copies core.vanilla_substitutions adds for those regions."""
    if not LOCATION_ITEM:
        return 0
    excl = getattr(world, "gf_dlc_excluded", frozenset())
    name_to_id = getattr(world, "item_name_to_id", {})
    n = 0
    for rn in regions:
        for (_name, ap_id, _flag) in LOCATIONS.get(rn, []):
            nm = LOCATION_ITEM.get(ap_id)
            if nm in VANILLA_FLASK_ITEMS and nm in name_to_id and nm not in excl:
                n += 1
    return n


def _substituted_flask_copies(world) -> int:
    """PROG_FLASK copies core.vanilla_substitutions puts in the pool == every kept flask check,
    INCLUDING the HUB. (Roundtable Hold always holds one Golden Seed, so this is >= 1 whenever
    item_shuffle is on -- which is why 'dlc_only keeps zero flask checks' is detected on the kept
    REGIONS, not the total: see flask_copy_count.)"""
    kept = list(world._kept()) if hasattr(world, "_kept") else []
    return _flask_check_count(world, [HUB] + kept)


def _region_flask_copies(world) -> int:
    """Kept flask checks EXCLUDING the always-kept HUB. 0 => no kept REGION has a seed/tear check
    (dlc_only, or a num_regions seed that seals every flask region) -- the trigger for the fixed
    ladder floor. (The HUB's lone Golden Seed is not enough to build a real flask curve on its own.)"""
    kept = list(world._kept()) if hasattr(world, "_kept") else []
    return _flask_check_count(world, list(kept))


def flask_copy_count(world) -> int:
    """The number of PROG_FLASK copies this seed will actually have == the flaskLadder length. When a
    kept region has flask checks: every substituted copy (HUB + regions). When none does (dlc_only):
    a fixed floor (DLC_ONLY_FLASK_COPIES) so the mode still has a real flask curve. 0 when flasks
    off."""
    if not _flasks_on(world):
        return 0
    if _region_flask_copies(world) > 0:
        return _substituted_flask_copies(world)
    return DLC_ONLY_FLASK_COPIES


def flask_inject_count(world) -> int:
    """PROG_FLASK copies THIS feature injects (create_items). Normal case: 0 -- the copies come from
    core.vanilla_substitutions of the kept seed/tear checks. dlc_only-style (no kept region has a flask
    check): top the pool up to DLC_ONLY_FLASK_COPIES, accounting for the HUB's lone substituted copy so
    the pool holds EXACTLY flask_copy_count() PROG_FLASK (ladder length == actual copies)."""
    if not _flasks_on(world):
        return 0
    return max(0, flask_copy_count(world) - _substituted_flask_copies(world))


def _cum_levels(n_rungs: int, weights: List[int]) -> List[int]:
    """Cumulative level after each of `n_rungs` rungs, distributing len(weights) unit level-ups across
    the rungs proportionally to cumulative WEIGHT (heavier/later steps take more rungs). Monotonic
    non-decreasing; reaches len(weights) EXACTLY at the last rung (progress is scaled to hit the final
    threshold only at rung n_rungs). n_rungs < len(weights) => some rungs advance multiple levels."""
    thresholds = list(itertools.accumulate(weights))   # thresholds[j] = cost to REACH level j+1
    total = thresholds[-1]
    out: List[int] = []
    for r in range(1, n_rungs + 1):
        spent = total * r / n_rungs
        lvl = sum(1 for t in thresholds if t <= spent + 1e-9)   # +eps so the last rung clears the top
        out.append(lvl)
    return out


def flask_ladder(world) -> List[Dict[str, int]]:
    """The flaskLadder wire: [{"charges", "potency"}, ...], one rung per PROG_FLASK copy. Monotonic
    non-decreasing. CHARGES reaches FLASK_CHARGES_MAX at the last rung (the client reconciles the flask
    charge target via a direct write). POTENCY climbs a flat +1 per rung capped at FLASK_POTENCY_MAX
    (= min(rung, 12)) and is DOCUMENTATION ONLY -- the client sets potency from the ledgered Sacred
    Tears granted in progressiveGrants, one tear per copy. With the normal >=12 copies (full seed, or
    dlc_only's fixed 12) the last rung is (FLASK_CHARGES_MAX, FLASK_POTENCY_MAX); with fewer than 12
    copies potency honestly tops out below 12 (fewer tears granted). Deterministic (closed-form;
    world.random not needed) and cached on the world so create_items and slot_data agree."""
    cached = getattr(world, "gf_flask_ladder", None)
    if cached is not None:
        return cached
    n = flask_copy_count(world)
    if n <= 0:
        world.gf_flask_ladder = []
        return []
    # CHARGES: escalating-weight schedule reaching FLASK_CHARGES_MAX at the last rung (client direct
    # write). POTENCY: a flat +1 per rung capped at FLASK_POTENCY_MAX -- computed directly, NOT through
    # _cum_levels, because potency is granted as ONE consumed Sacred Tear per copy (a +2 rung would need
    # 2 tears at one stream index = the batching the ledger forbids). Potency here is documentation only
    # (the client takes potency from the ledgered tears), but it is kept accurate = min(rung, 12).
    charge_lv = _cum_levels(n, _CHARGE_STEP_WEIGHTS)
    ladder = [{"charges": FLASK_CHARGES_BASE + c, "potency": min(rung, FLASK_POTENCY_MAX)}
              for rung, c in enumerate(charge_lv, start=1)]
    world.gf_flask_ladder = ladder
    return ladder


# Vanilla pool items the unified flask ladder REPLACES, one-for-one, when progressive_flasks is on.
# core.create_items substitutes these names as it reads each check's vanilla item, so the copy count
# is exactly the number of seed/tear checks the seed actually kept -- count-neutral, and it scales
# with num_regions / DLC for free (a 4-region seed simply has fewer rungs available, which is the
# honest outcome, not a bug). This is why PROG_FLASK has no _POOL_COUNTS entry.
VANILLA_FLASK_ITEMS = ("Golden Seed", "Sacred Tear")


def vanilla_substitutions(world) -> Dict[str, str]:
    """{vanilla item name -> progressive item name} for core's item_shuffle pool. Empty when off."""
    opt = getattr(world.options, "progressive_flasks", None)
    if not (opt is not None and opt.value):
        return {}
    return {n: PROG_FLASK for n in VANILLA_FLASK_ITEMS}

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
    # PROG_FLASK is deliberately absent: its copies come from substituting the seed/tear checks the
    # seed actually kept (see vanilla_substitutions), not from a fixed count.
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
_FLASK_ITEMS = (PROG_FLASK,)
_KEY_ITEMS = (PROG_STONESWORD_KEY,)
_BELL_ITEMS = (PROG_SMITHING_BELL, PROG_SOMBER_BELL)


class ProgressiveFlasks(Toggle):
    """On (default): every Golden Seed and Sacred Tear check pays out a single "Progressive Flask
    Upgrade" item instead, one-for-one. Each copy raises your flask on two axes: CHARGES climb on an
    escalating schedule the client applies directly, and POTENCY rises by granting you a Sacred Tear
    that you spend at a grace the vanilla way -- so upgrades arrive on a steady cadence instead of a
    pile of silent flat pickups. Off: seeds and tears stay discrete pickups at their shuffled
    locations. Flasks never gate logic, so either way the seed is always winnable."""
    display_name = "Progressive Flasks"
    default = 1


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
        PROG_FLASK: ItemClassification.useful,
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

    def _grant_ladder(self, world, name: str) -> List[Dict[str, Any]]:
        """Client `progressiveGrants` ladder for one progressive item: an ordered list of
        {"goods": GOODS-packed FullID, "flags": [event flags], "consumed": bool}. Fungible/keyed items
        (flasks, stonesword keys) repeat a single good with no flags; stone bells carry a per-tier good
        AND the shop-unlock flags for that rung."""
        # `consumed`: the rung's goods are SPENT by the player, so the client must grant them exactly
        # ONCE (ledgered by the copy's stream index) rather than treating them as something the player
        # should OWN. Absent/false = owned = the client's self-healing `unique_goods` path.
        #
        # This distinction is not a nicety. The flask POTENCY rungs grant Sacred Tears, which are spent
        # at a Site of Grace. Shipped as OWNED, the reconciler saw the spent tear missing from the
        # inventory and handed it straight back -- upgrade, re-grant, upgrade, re-grant, unbounded,
        # until the flask ran past its cap and the game CTD'd. (Alaric, live playtest 2026-07-12.) So
        # the flask tears MUST be consumed=True. Bell bearings are the opposite: a key item you keep
        # forever, and self-healing is exactly what you want if one is ever lost. Same ladder machinery,
        # opposite grant semantics -- so the semantics have to be stated, not assumed.
        #
        # The flask rides progressiveGrants for its POTENCY axis ONLY: one consumed Sacred Tear per
        # copy, so the player upgrades potency at a grace the vanilla way (which updates every flask
        # mirror -- inventory entry, equipped/quickslot ref, global GaItem -- correctly). The CHARGES
        # axis is a separate reconciled leveled state (contract.flaskLadder, direct write). The old
        # in-place potency item-id swap CTD'd on death against the half-updated mirrors (playtest
        # 2026-07-19); granting a tear + a grace upgrade is the proven safe path.
        if name == PROG_FLASK:
            # POTENCY axis: one consumed Sacred Tear per copy, FLASK_POTENCY_MAX rungs (12). No flags.
            # Copies past rung 12 overflow to a Lord's Rune client-side (existing behavior -- fine).
            return [{"goods": _GOOD_SACRED_TEAR | _GOODS_NIBBLE, "flags": [], "consumed": True}
                    for _ in range(FLASK_POTENCY_MAX)]
        if name in _BELL_GRANTS:
            return [{"goods": e["goods"] | _GOODS_NIBBLE, "flags": list(e["flags"]), "consumed": False}
                    for e in _BELL_GRANTS[name]]
        # Stonesword Keys are spent on Imp Statue seals -> consumed.
        return [{"goods": good | _GOODS_NIBBLE, "flags": [], "consumed": True}
                for good in _GOODS_LADDERS[name]]

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
            if name == PROG_FLASK:
                # Normal case: PROG_FLASK copies come from core.vanilla_substitutions of the kept
                # seed/tear checks (inject 0). dlc_only-style (no flask check kept): inject a fixed
                # count so the leveled ladder still has copies to advance. Count-neutral either way.
                pool += [world.create_item(PROG_FLASK) for _ in range(flask_inject_count(world))]
                continue
            if name not in _POOL_COUNTS:
                continue
            pool += [world.create_item(name) for _ in range(_POOL_COUNTS[name])]
        return pool

    def slot_data(self, world) -> Dict[str, Any]:
        # progressiveGrants = {item_name: [{"goods": FullID, "flags": [...], "consumed": bool}, ...]}.
        # Empty {} when no progressive toggle is on. Stonesword keys carry empty flags (spend-at-seal
        # goods); stone bells carry the Twin Maiden shop-unlock flags per rung (set = unlock). PROG_FLASK
        # IS INCLUDED: its POTENCY axis is 12 consumed Sacred Tears (the player upgrades potency at a
        # grace the vanilla way, which updates every flask mirror safely). Its CHARGES axis rides the
        # SEPARATE flaskLadder wire below (a reconciled leveled state, direct write). The flask appearing
        # in BOTH wires is intentional and non-overlapping (tears != charges): the old in-place potency
        # item-id swap CTD'd on death against ER's half-updated flask mirrors (playtest 2026-07-19), and
        # an even older OWNED-tears build re-granted spent tears unbounded (playtest 2026-07-12) -- so
        # potency is now consumed-goods grants and consumed=True is required.
        grants: Dict[str, List[Dict[str, Any]]] = {}
        for name in self._active_items(world):
            grants[name] = self._grant_ladder(world, name)
        out: Dict[str, Any] = {contract.PROGRESSIVE_GRANTS: grants}
        # flaskLadder: the cumulative {charges, potency} target per received PROG_FLASK copy (charges are
        # the load-bearing axis client-side; potency is documentation). Emitted only when
        # progressive_flasks is on (absent otherwise).
        if _flasks_on(world):
            out[contract.FLASK_LADDER] = flask_ladder(world)
        return out
