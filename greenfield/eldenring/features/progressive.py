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
    (SPEC-PARITY: ProgressiveItems stone_bells). The Kth copy sets the Twin Maiden ShopLineupParam
    stock flags for that rung AND its shared release flag -- setting both halves is the shop unlock,
    with no hand-in and no physical bearing grant. Granting both representations makes the game
    reject the bearing as already handed in (live playtest 2026-08-17, #804).
    Flags verified against vanilla_er/ShopLineupParam.csv (Twin Maiden shop 1018xx: item 10100 ->
    stock 280080, tier release 11109751, etc.). 1 copy of each is forced to sphere 0 so the
    upgrade ramp opens at the start; the rest distribute normally. Copies past the last tier are
    silent no-ops client-side (the k < tiers guard). The VANILLA bell bearings SUBSTITUTE to the
    progressive item exactly as the flask checks do (vanilla_substitutions), so the pool cannot hold
    both ladders at once -- before #539 it held BOTH, and a single vanilla `Somberstone Miner's Bell
    Bearing [5]` handed the player the top rung on pickup. That does not degrade the ladder, it
    BYPASSES it (boblerrr, live playtest 2026-08-10).

WHY THE BELLS KEEP A COPY FLOOR AND THE FLASK DOES NOT (the _POOL_COUNTS ruling, #539)
--------------------------------------------------------------------------------------
PROG_FLASK deliberately has no _POOL_COUNTS entry: every copy comes from substitution, which is what
makes it count-exact and lets the ladder length follow the checks the seed actually kept. #539
proposed the same for the bells -- drop their _POOL_COUNTS and let substitution be the only source.
REJECTED, for two reasons the vanilla data makes unavoidable:

  * THE SOMBER LADDER WOULD BE PERMANENTLY ONE RUNG SHORT. `Somberstone Miner's Bell Bearing [1]`
    does not exist in the vanilla item data (it is not a looted item), so the whole game holds only
    FOUR somber bell checks against FIVE somber rungs. Pure substitution therefore caps the somber
    ladder at 4 copies in EVERY seed, and rung 5 -- the Somber Smithing Stone [9] shop unlock, the
    endgame material -- becomes unreachable. The flask has no analogue: its ladder LENGTH is a design
    choice that bends to the copy count, the bells' is fixed by _BELL_GRANTS and cannot bend.
  * A SEED CAN KEEP ZERO BELL CHECKS. The eight checks live in Altus, Liurnia, Mountaintops and Farum
    Azula. A num_regions seed that keeps none of those -- or dlc_only, or item_shuffle off, where
    core never walks the vanilla items at all -- would get a ZERO-copy ladder: the feature silently
    inert, and generate_early asking AP to bias a sphere-0 copy that does not exist. This is exactly
    the case flask_inject_count / DLC_ONLY_FLASK_COPIES exist for on the flask side.

So the bells use the flask's OTHER half. Substitution supplies the copies (count-neutral, and it is
what removes the vanilla bearings from the pool), and create_items TOPS UP to the ladder length --
bell_inject_count. Total copies == len(_BELL_GRANTS[name]) in every seed, 4 smithing and 5 somber, so
every rung is reachable and no copy is a dud. That also retires the old fixed count's 5th smithing
copy, which had no rung to grant.

THE SECOND SOURCE. Substitution alone does NOT empty the pool of vanilla bearings: features/
presence_floor.py injects one copy of every roster item whose home region was not kept, and the bell
bearings are on that roster -- which is why all 8 showed up even in a 4-region seed. With this toggle
on, the progressive ladder IS the guaranteed supply (the floor above holds in every seed, including
the dlc_only case presence_floor was written for), so that feature drops the bell bearings from its
roster. Both edits are required; either one alone leaves the bypass in place.

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
# The "potency" field below is therefore DOCUMENTATION ONLY (kept accurate to the even-copy
# schedule); the client takes potency from the ledgered tears, not this ladder.
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
# min(rung//2, 12), NOT distributed through _cum_levels like charges.
FLASK_CHARGES_BASE = 4
FLASK_CHARGES_MAX = 14
FLASK_POTENCY_MAX = 12
_CHARGE_STEP_WEIGHTS: List[int] = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6]   # 12 steps (2 -> 14), escalating
_POTENCY_STEP_WEIGHTS: List[int] = list(FLASK_POTENCY_TEAR_COST)          # 12 flat steps; documentation only

# When NO Golden Seed / Sacred Tear check is kept (dlc_only, or a num_regions seed that seals every
# flask region), there are no substituted PROG_FLASK copies -- so inject a fixed count of copies and
# build a ladder that maxes by the last rung. 12 copies: one Sacred Tear per copy needs 12 copies to
# reach potency 12 under an alternating schedule. Twenty-four copies fully max both axes.
DLC_ONLY_FLASK_COPIES = 24


def _flasks_on(world) -> bool:
    o = getattr(world.options, "progressive_flasks", None)
    return bool(o is not None and o.value)


def _shuffle_on(world) -> bool:
    """item_shuffle -- core only walks the vanilla items (and therefore only SUBSTITUTES) when it is
    on. A copy count derived from the walk has to agree with that or it will credit substituted
    copies that core never made."""
    o = getattr(world.options, "item_shuffle", None)
    return bool(o is not None and o.value)


def _kept_check_count(world, regions, names) -> int:
    """How many of `regions`' locations vanilla-hold one of `names` this seed. Mirrors core's extras
    source (LOCATION_ITEM) and honours the DLC-off exclusion -- so it equals the progressive copies
    core.vanilla_substitutions adds for those regions. ONE walk, shared by the flask and the bells:
    a second copy of it would be a second chance to disagree with core about what "kept" means."""
    if not LOCATION_ITEM:
        return 0
    excl = getattr(world, "gf_dlc_excluded", frozenset())
    name_to_id = getattr(world, "item_name_to_id", {})
    names = frozenset(names)
    n = 0
    for rn in regions:
        for (_name, ap_id, _flag) in LOCATIONS.get(rn, []):
            nm = LOCATION_ITEM.get(ap_id)
            if nm in names and nm in name_to_id and nm not in excl:
                n += 1
    return n


def _flask_check_count(world, regions) -> int:
    """How many of `regions`' locations vanilla-hold a Golden Seed / Sacred Tear this seed. Mirrors
    core's extras source (LOCATION_ITEM) and honours the DLC-off exclusion -- so it equals the
    PROG_FLASK copies core.vanilla_substitutions adds for those regions."""
    return _kept_check_count(world, regions, VANILLA_FLASK_ITEMS)


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
    (= min(rung//2, 12)) and is DOCUMENTATION ONLY -- the client sets potency from ledgered Sacred
    Tears on even copies. With the normal >=24 copies (full seed, or dlc_only's fixed 24) the last
    rung is (FLASK_CHARGES_MAX, FLASK_POTENCY_MAX); with fewer than 24
    copies potency honestly tops out below 12 (fewer tears granted). Deterministic (closed-form;
    world.random not needed) and cached on the world so create_items and slot_data agree."""
    cached = getattr(world, "gf_flask_ladder", None)
    if cached is not None:
        return cached
    n = flask_copy_count(world)
    if n <= 0:
        world.gf_flask_ladder = []
        return []
    # Alternating ruling (#798): odd copies advance CHARGES, even copies grant +1 POTENCY. Derive
    # both cumulative targets from the copy ordinal so reconnect/retry cannot shift the sequence.
    # The first charge target is 5, one above the vanilla starting allocation of 4; it can therefore
    # never be silently absorbed by a fresh character. Each later scheduled charge advances one more
    # observable step until the vanilla cap. Potency is one consumed Sacred Tear on each even copy.
    charge_copies = (n + 1) // 2
    charge_targets = [min(FLASK_CHARGES_BASE + ordinal, FLASK_CHARGES_MAX)
                      for ordinal in range(1, charge_copies + 1)]
    ladder = []
    for copy in range(1, n + 1):
        charges = charge_targets[(copy - 1) // 2]
        potency = min(copy // 2, FLASK_POTENCY_MAX)
        ladder.append({"charges": charges, "potency": potency})
    world.gf_flask_ladder = ladder
    return ladder


# Vanilla pool items the unified flask ladder REPLACES, one-for-one, when progressive_flasks is on.
# core.create_items substitutes these names as it reads each check's vanilla item, so the copy count
# is exactly the number of seed/tear checks the seed actually kept -- count-neutral, and it scales
# with num_regions / DLC for free (a 4-region seed simply has fewer rungs available, which is the
# honest outcome, not a bug). This is why PROG_FLASK has no _POOL_COUNTS entry.
VANILLA_FLASK_ITEMS = ("Golden Seed", "Sacred Tear")

# Vanilla pool items the progressive stone-bell ladders REPLACE, one-for-one, when
# progressive_stone_bells is on (#539). These are ALL the bell bearings the vanilla item data has:
# Smithing-Stone [1]-[4] and Somberstone [1]-[5].
#
# ⭐⭐⭐ 2026-08-13 (#191): NINE, not eight. This list said eight because
# `Somberstone Miner's Bell Bearing [1]` was "absent from the vanilla name catalog (it is not a
# looted item)". That premise was WRONG, and it was wrong for a reason nothing here could see: the
# catalog is CHECK-derived, the bearing hangs off flag 520670 as lot 20673 -- a SIBLING of a
# shared-flag family -- and until the co-check allowlist widened, siblings were never projected. It
# is looted, it is a real catalog item, and with the ladder on a vanilla copy of it was therefore
# eligible for the pool: the top-rung-bypass leak (#539) this substitution exists to stop, hiding
# behind a data gap. Caught by test_gf_progressive's VANILLA_BELL_ITEMS-vs-catalog gate, which is
# exactly the "a data rename shrinks the substitution LOUDLY" guard below doing its job in reverse.
#
# 🛑 CONSEQUENCE NOT ACTED ON HERE: the module docstring justifies the somber ladder's INJECTED
# FLOOR on this same "Somberstone [1] cannot be found" premise. That premise is now dead, so the
# injected floor may be redundant -- but removing it changes what a seed grants, so it is a ruling,
# not a cleanup. Left in place deliberately; see #191.
# test_gf_progressive asserts every name here resolves against the real item catalog, so a data
# rename shrinks the substitution LOUDLY rather than silently putting the vanilla ladder back.
VANILLA_BELL_ITEMS: Dict[str, str] = dict(
    [("Smithing-Stone Miner's Bell Bearing [%d]" % i, PROG_SMITHING_BELL) for i in range(1, 5)]
    + [("Somberstone Miner's Bell Bearing [%d]" % i, PROG_SOMBER_BELL) for i in range(1, 6)]
)


def vanilla_substitutions(world) -> Dict[str, str]:
    """{vanilla item name -> progressive item name} for core's item_shuffle pool. Empty when every
    substituting toggle is off.

    TWO ladders substitute here, and both must, for the same reason: while a vanilla pickup that
    grants a ladder's TOP RUNG outright is still in the pool, the ladder is not paced, it is bypassed
    (#539). core.create_items reads this at the single place vanilla items are rewritten, so a name
    added here leaves the pool everywhere by construction -- but only where core walks the vanilla
    items at all, which is why presence_floor needs its own guard (see the module docstring)."""
    subs: Dict[str, str] = {}
    opt = getattr(world.options, "progressive_flasks", None)
    if opt is not None and opt.value:
        subs.update({n: PROG_FLASK for n in VANILLA_FLASK_ITEMS})
    if _bells_on(world):
        subs.update(VANILLA_BELL_ITEMS)
    return subs

# ---- progressive stone-bell grant ladders (shop-unlock flags only) ----------------------------
# Setting the flags IS the shop unlock (no hand-over to the Twin Maidens needed). Do not also grant
# the corresponding physical bearing: once its shop flags are set, Elden Ring treats the bearing as
# already handed in and refuses it as over-capacity (#804).
#
# EACH RUNG NEEDS BOTH PARAM GATES. ShopLineupParam.eventFlag_forStock unlocks the individual rows;
# eventFlag_forRelease makes that bearing's shelf EXIST in the menu. The first implementation set
# only the stock flags, so receipts reconciled forever without the stones appearing. Values below
# are read from vanilla_er/ShopLineupParam.csv block 1018: two stock flags + one shared release flag
# per tier, except Somber [5], which has one stock row.
_BELL_GRANTS: Dict[str, List[Dict[str, Any]]] = {
    PROG_SMITHING_BELL: [
        {"flags": [280080, 280090, 11109751]},  # Smithing Stone [1],[2]
        {"flags": [280110, 280120, 11109752]},  # Smithing Stone [3],[4]
        {"flags": [280140, 280150, 11109753]},  # Smithing Stone [5],[6]
        {"flags": [280160, 280170, 11109754]},  # Smithing Stone [7],[8]
    ],
    PROG_SOMBER_BELL: [
        {"flags": [280180, 280190, 11109755]},  # Somber [1],[2]
        {"flags": [280200, 280210, 11109756]},  # Somber [3],[4]
        {"flags": [280230, 280240, 11109757]},  # Somber [5],[6]
        {"flags": [280250, 280260, 11109758]},  # Somber [7],[8]
        {"flags": [280280, 11109759]},          # Somber [9]
    ],
}

# How many copies of each progressive item to place in the pool when its toggle is on. Bounded well
# under the ladder length so copies land inside the meaningful ladder (no overflow spam), and small
# enough to stay comfortably count-neutral against the filler tail.
_POOL_COUNTS: Dict[str, int] = {
    # PROG_FLASK is deliberately absent: its copies come from substituting the seed/tear checks the
    # seed actually kept (see vanilla_substitutions), not from a fixed count. The two STONE BELLS
    # left this table in #539 for the same reason -- they substitute now, so a fixed count would ADD
    # copies on top of the substituted ones. They are not pure-substitution either: bell_inject_count
    # tops them up to the ladder length, because the vanilla data cannot supply the somber ladder's
    # 5th rung and a seed can keep zero bell checks. See the module docstring for the full ruling.
    PROG_STONESWORD_KEY: 6,
}


def _bells_on(world) -> bool:
    o = getattr(world.options, "progressive_stone_bells", None)
    return bool(o is not None and o.value)


def bell_ladder_len(name: str) -> int:
    """Rungs in this bell's grant ladder -- 4 smithing, 5 somber. _BELL_GRANTS is the ONLY definition
    of how many copies are meaningful, so it is also the definition of how many copies to have."""
    return len(_BELL_GRANTS.get(name, ()))


def _substituted_bell_copies(world, name: str) -> int:
    """Copies of `name` core.vanilla_substitutions puts in the pool == every kept check whose vanilla
    item is one of that bell's vanilla bearings (HUB included, exactly as the flask counts it). Zero
    when item_shuffle is off: core never walks the vanilla items, so it substitutes nothing."""
    if not _bells_on(world) or not _shuffle_on(world):
        return 0
    kept = list(world._kept()) if hasattr(world, "_kept") else []
    names = [v for v, prog in VANILLA_BELL_ITEMS.items() if prog == name]
    return _kept_check_count(world, [HUB] + kept, names)


def bell_copy_count(world, name: str) -> int:
    """The number of copies of `name` this seed will actually have == the ladder length, in every
    seed: substitution supplies at most 4 (the vanilla data holds only 4 checks per bell) and
    create_items tops up the rest. max(), not a bare ladder length, so a future data regen that adds
    a bell check cannot make this UNDERSTATE the pool and desync the count from what core built."""
    if not _bells_on(world):
        return 0
    return max(bell_ladder_len(name), _substituted_bell_copies(world, name))


def bell_inject_count(world, name: str) -> int:
    """Copies of `name` THIS feature injects (create_items): the top-up between what substitution
    supplied and the ladder length. Always >0 for the somber bell (4 vanilla checks, 5 rungs) and in
    any seed that kept few bell checks; count-neutral either way, because core sizes the filler tail
    as `total_locations - len(pool)` AFTER this runs."""
    return max(0, bell_copy_count(world, name) - _substituted_bell_copies(world, name))

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
    Upgrade" item instead, one-for-one. Copies alternate deterministically: Charge, then +1 potency,
    then Charge, then +1, continuing in that order. The first copy visibly raises total charges above
    the vanilla starting allocation; +1 copies grant a Sacred Tear to spend at a grace. Off: seeds
    and tears stay discrete pickups at their shuffled locations. Flasks never gate logic, so either
    way the seed is always winnable."""
    display_name = "Progressive Flasks"
    default = 1


class ProgressiveStoneswordKeys(Toggle):
    """Off (default). On: add Progressive Stonesword Key items -- each copy grants one Stonesword
    Key for opening Imp Statue seals. Never gates logic (Region Locks are the only progression), so
    this is always winnable."""
    display_name = "Progressive Stonesword Keys"


class ProgressiveStoneBells(Toggle):
    """Off (default). On: the vanilla Miner's Bell Bearings are replaced by two progressive
    items -- Progressive Smithing-Stone and Progressive Somberstone Miner's Bell Bearing -- and each
    copy you receive unlocks the next tier of the Twin Maidens' smithing-stone shop directly (no
    hand-over). One copy of each is forced to sphere 0, so the upgrade ramp opens at the start, and
    there are exactly as many copies as there are shop tiers to unlock (4 and 5), so no copy is
    wasted and no single pickup skips you to the top. Never gates logic (Region Locks are the only
    progression), so this is always winnable."""
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
        (flasks, stonesword keys) repeat a single good with no flags; stone bells carry only the
        shop-unlock flags for that rung."""
        # `consumed`: the rung's goods are SPENT by the player, so the client must grant them exactly
        # ONCE (ledgered by the copy's stream index) rather than treating them as something the player
        # should OWN. Absent/false = owned = the client's self-healing `unique_goods` path.
        #
        # This distinction is not a nicety. The flask POTENCY rungs grant Sacred Tears, which are spent
        # at a Site of Grace. Shipped as OWNED, the reconciler saw the spent tear missing from the
        # inventory and handed it straight back -- upgrade, re-grant, upgrade, re-grant, unbounded,
        # until the flask ran past its cap and the game CTD'd. (Alaric, live playtest 2026-07-12.) So
        # the flask tears MUST be consumed=True.
        #
        # The flask rides progressiveGrants for its POTENCY axis ONLY: one consumed Sacred Tear per
        # copy, so the player upgrades potency at a grace the vanilla way (which updates every flask
        # mirror -- inventory entry, equipped/quickslot ref, global GaItem -- correctly). The CHARGES
        # axis is a separate reconciled leveled state (contract.flaskLadder, direct write). The old
        # in-place potency item-id swap CTD'd on death against the half-updated mirrors (playtest
        # 2026-07-19); granting a tear + a grace upgrade is the proven safe path.
        if name == PROG_FLASK:
            # Keep one progressiveGrants rung per pool copy so the tier ordinal is the authoritative
            # schedule. Odd copies are explicit no-ops here (their charge effect rides flaskLadder);
            # even copies grant exactly one consumed Sacred Tear until potency caps.
            return [
                ({"goods": _GOOD_SACRED_TEAR | _GOODS_NIBBLE, "flags": [], "consumed": True}
                 if copy % 2 == 0 and copy // 2 <= FLASK_POTENCY_MAX else {"noop": True})
                for copy in range(1, flask_copy_count(world) + 1)
            ]
        if name in _BELL_GRANTS:
            return [{"flags": list(e["flags"])}
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
            if name in _BELL_GRANTS:
                # Same model as the flask, for the same reason: substituting the kept bell checks
                # supplies the copies (count-neutral, and it is what takes the vanilla bearings OUT
                # of the pool), and this tops up to the ladder length so every rung is reachable even
                # in a seed that kept no bell check at all. #539 -- see the module docstring for why
                # the bells need that floor when the flask's substitution-only model does not.
                pool += [world.create_item(name) for _ in range(bell_inject_count(world, name))]
                continue
            if name not in _POOL_COUNTS:
                continue
            pool += [world.create_item(name) for _ in range(_POOL_COUNTS[name])]
        return pool

    def slot_data(self, world) -> Dict[str, Any]:
        # progressiveGrants = {item_name: [{"goods": FullID, "flags": [...], "consumed": bool}, ...]}.
        # Empty {} when no progressive toggle is on. Stonesword keys carry empty flags (spend-at-seal
        # goods); stone bells carry the Twin Maiden shop-unlock flags per rung (set = unlock). PROG_FLASK
        # IS INCLUDED: its POTENCY axis is consumed Sacred Tears on even copies (the player upgrades potency at a
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
