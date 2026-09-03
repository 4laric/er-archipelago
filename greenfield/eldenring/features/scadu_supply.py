"""scadu_supply -- guarantee the Scadutree blessing has the fragments its CAP was budgeted for.

WHY THIS EXISTS
---------------
The blessing ships an injection budget (`SCADU_INJECTION_TARGET`, 12 -- it lived in
`scaling.SCADU_BLESSING_CAP` until 2026-08-06, where it also served as a ceiling that no longer
exists) whose entire purpose is to bound an INJECTION -- SPEC-global-scadutree-blessing-20260729 §9.2 put it to Alaric as
*"Injection budget. SCADU_CUM[20] = 50 fragments is a lot of filler to displace in a base seed. Cap
at 12 (26 fragments) instead?"*, and its acceptance criteria read:

    Pure (world): injection count is a function of the cap; a no-DLC seed at mode 1 contains
    >= SCADU_CUM[cap] fragments; a DLC seed injects none.

**The cap shipped. The injection did not.** Until this file, the only occurrence of `SCADU_CUM`
anywhere in `greenfield/` was inside the comment at `scaling.py:387` explaining the cap. So the
ceiling sat over a supply that arrived purely by luck of the DLC-region draw.

MEASURED (2026-08-01, 40 seeds per row, `num_regions_order: rolled`, `enable_dlc: 1`): reaching the
cap needs 26 fragments, and at the SHIPPED DEFAULT of `num_regions: 6` only **1 seed in 40** could
get there. Median reachable blessing was 3 of 12. Seed `AP_90729554631839684613` -- 8 regions, one
of them DLC (Enir Ilim) -- carried **3** fragments, i.e. blessing level 2 against a cap of 12.

THE TRIGGER IS A COUNT, NOT A BOOLEAN
-------------------------------------
The spec's own rule ("a DLC seed injects none") is a boolean standing in for a count, and building
it as written would NOT have fixed the reported seed: that seed *is* a DLC seed and is 23 fragments
short. One DLC region satisfies the boolean while missing the target entirely -- the same wrong-arity
shape CONTRIBUTING's "when the data contradicts the model, the MODEL changes" section is about.

So the rule here is arithmetic on the number:

    inject = max(0, SCADU_CUM[cap] - natural)

from which no-DLC (inject 26), one-DLC-region (inject 23) and full-DLC (inject 0) all fall out.
"A DLC seed injects none" becomes a *consequence* rather than a condition.

COUNT-NEUTRALITY
----------------
Modelled on features/presence_floor.py, which is modelled on features/progressive.py. `create_items`
returns pool items; `core.create_items` adds every feature's contribution BEFORE it sizes the filler
tail (`slots = total - len(pool)`), so each injected fragment displaces exactly one filler/Rune tail
slot and the pool stays count-exact. Nothing here adds a location.

Injected copies are `useful`, never progression: fragments gate nothing, and promoting them would
over-constrain fill for no logical gain. `filler_curation.COLLECTATHON_ITEMS` already protects
"Scadutree Fragment" from junk seizure, so natural copies survive as themselves and are not
displaced by the tail -- which is what makes `natural` a number worth subtracting.

DLC OFF
-------
"Scadutree Fragment" is a DLC good, so with `enable_dlc` off it sits in `world.gf_dlc_excluded` and
injecting it would leak DLC content into a base-game pool (the class `test_gf_dlc_pool_leak` guards).
This feature therefore injects NOTHING when the fragment is excluded, and says so.

That leaves mode 1 + `enable_dlc: 0` structurally inert -- the blessing is on and there are no
fragments to raise it. The spec's phrase "a no-DLC seed" is ambiguous between "DLC content disabled"
and "DLC content enabled but no DLC region kept"; this file implements the second and refuses the
first, because the leak guard is the stronger constraint and a silent leak is worse than a stated
no-op. Flagged for a ruling rather than silently picked.
"""
from typing import List
import math

from BaseClasses import ItemClassification
from ..registry import Feature, register

try:
    from ..item_ids import ITEM_CATALOG, LOCATION_ITEM
except Exception:  # pre-regen: no catalog -> nothing resolves, feature is inert
    ITEM_CATALOG, LOCATION_ITEM = {}, {}
try:
    from ..data import HUB, LOCATIONS
except Exception:
    HUB, LOCATIONS = "Roundtable Hold", {}


FRAGMENT = "Scadutree Fragment"

# The x2 stack, a SECOND AP item resolving to the SAME game item.
#
# WHY A NEW ID RATHER THAN itemCounts ON THE EXISTING ONE. `itemCounts` is keyed by AP item id, and
# every copy of "Scadutree Fragment" shares one -- so stacking it there is all-or-nothing and would
# silently double the VANILLA-placed fragments too, doubling a DLC seed's natural supply. A separate
# id keeps the two independent: vanilla placements stay x1 and only the injection stacks.
#
# The client needs NOTHING for this. `er_logic::upgrades::fragment_units_for` resolves through
# apIdsToItemIds and multiplies by itemCounts (`unwrap_or(1).max(1)`), so it counts this as two
# fragments without knowing the item is new -- and the grant path uses the same pair.
FRAGMENT_X2 = "Scadutree Fragment x2"

# Cumulative Scadutree Fragments required for blessing level 0..20 (vanilla curve).
#
# MIRROR of `er-logic/src/upgrades.rs::SCADU_CUM`, which is what the CLIENT derives the live
# blessing level from. Two copies of one game constant across two repos is exactly the drift this
# repo gates elsewhere (`scaling_ladder_mirror`, `client_can_sell_mirror`), so
# tests/test_gf_scadu_supply.py diffs this tuple against the Rust source rung for rung and fails on
# disagreement. Do not edit one side alone.
SCADU_CUM = (0, 1, 3, 5, 7, 9, 11, 13, 15, 17, 20, 23, 26, 29, 32, 35, 38, 41, 44, 47, 50)

# The injection may never claim more than this share of a seed's locations.
#
# ⭐ IT BINDS NOW, BY DESIGN (2026-08-06). When this landed it could not fire on a real seed -- the
# smallest measured seed was 727 locations, because `goal: auto` force-kept GOAL_REGION and its
# REGION_PARENT closure put a 3-region floor under `num_regions: 1`. SPEC-ashen-capital-lock
# removed that force-keep (the burn is an item now), so a genuinely one-region seed exists for the
# first time: hub + one region, 240-360 locations. On 16 of the 30 possible draws (measured
# 2026-08-06, tests/test_gf_scadu_supply.py sweeps all of them) 50 units will not fit in a 10%
# share; injection stops short of SCADU_INJECTION_TARGET, `create_items` WARNS with the numbers,
# and the blessing tops out around level 14-18 instead of 20. That degrade is the RULING, not a
# bug: the target is a difficulty knob (`useful`, gates nothing, no player-facing promise names
# it), while the clamp is what keeps a tiny seed's pool from becoming a fragment pile -- the whole
# reason it exists. The clamp wins; the loss is stated; CLAMP_FLOOR_LEVEL below bounds it.
MAX_POOL_SHARE = 0.10

# The blessing level the clamp must never starve a REAL seed below: the ORIGINAL shipped cap
# (`scaling.SCADU_BLESSING_CAP` until 2026-08-06 -- the number the 12->20 target raise replaced).
# When 12 WAS the target it was judged an acceptable whole-playthrough supply, so it is the line
# between "tops out early" (fine, warned) and "starved" (a defect).
#
# 2026-08-25 (#1013): NOW ENFORCED IN CODE, as a bounded breach of the share ceiling. It was
# deliberately NOT enforced ("a floor that overrides the share ceiling would breach it exactly on
# the degenerate pools the ceiling exists for") while real geometry kept the floor unreachable --
# the smallest one-region draw still injected 32 units. Enia's shop going vanilla removed her 100
# hub rows, and with them the smallest draw (Abyssal, hub + one tiny region, ~150 locations) fell
# through the floor: 2 natural + 20 clamped injected = 22 < 26 units. The ruling on the
# clamp-vs-floor trade the old comment asked for: the floor wins, but ONLY the floor -- the
# breach is capped at SCADU_CUM[CLAMP_FLOOR_LEVEL] units (never the target), so a ~150-location
# seed pays ~18 items (~12%) for level 12, not 36 items (~24%) for level 20. The target stays
# share-clamped; the loss is still stated by the create_items warning.
CLAMP_FLOOR_LEVEL = 12


# ---- THE INJECTION BUDGET (moved here 2026-08-06) ----------------------------------------------
# Was `scaling.SCADU_BLESSING_CAP`, where it doubled as a ceiling on the applied blessing. The
# ceiling is gone -- the vanilla ladder's 20 is the only one now -- but the number it was actually
# reasoned about survives, because that reasoning was always about POOL PRESSURE and never about
# where to stop:
#
#   SCADU_CUM[20] = 50 fragments vs SCADU_CUM[12] = 26, for +11% attack. In a base-game seed every
#   one of those 24 extra fragments is a forced-`useful` item displacing filler.
#
# So this is what the seed GUARANTEES is reachable, not what it permits. A lucky region draw can
# still carry a player past level 12; nothing clamps them.
SCADU_INJECTION_TARGET = 20

# ⭐ WHY 20 AND NOT A CHOSEN NUMBER (2026-08-06). Datamined from gen_inputs.db, ItemLotParam_map +
# ItemLotParam_enemy, goods 2010000: vanilla hand-places 46 fragment lot slots -- 42 of them x1 and
# 4 of them x2 -- for exactly **50 units**, which is exactly SCADU_CUM[20]. FromSoft budgeted the
# base game to reach the top of the ladder on a complete sweep. So the target is not a balance pick
# at all; it is the game's own supply, restated. (The 12 that used to live here was a POOL-PRESSURE
# argument, and the stack below is what answers that instead.)

# Share of injected UNITS delivered as x2 stacks, as a divisor: one x2 per this many units.
#
# 4 => half the units arrive stacked (each x2 is 2 units). 50 units becomes 12 x2 + 26 x1 = 38 pool
# items instead of 50 -- so raising the target from 12 to 20 costs ~12 more item slots, not 24.
#
# 🛑 NOT VANILLA'S OWN RATIO, DELIBERATELY. Vanilla's mix is 4 stacks in 46 drops; mirroring it
# would need ~46 items for the same 50 units and would buy nothing, and calling that "authentic"
# would borrow authority the number does not have -- where FromSoft hand-placed a x2 is a fact about
# level design, not a rule about pool budgets. Alaric's call 2026-08-06: a visible MIX, weighted for
# the pool, rather than either extreme (all-x1 is 50 items; all-x2 is 25 and no mix at all).
UNITS_PER_STACK_ITEM = 4


def split_injection(units: int):
    """`units` of blessing supply -> `(singles, stacks)` pool ITEMS. PURE.

    Each stack is worth 2 units, so `stacks = units // UNITS_PER_STACK_ITEM` puts about half the
    units in stacks and the remainder in singles. Integer division means small injections are all
    singles (a 3-unit top-up is 3 x1, not 1 x2 + 1 x1) -- the mix appears when there is enough
    supply for it to be a mix rather than a rounding artefact.
    """
    units = max(0, units)
    stacks = units // UNITS_PER_STACK_ITEM
    return units - 2 * stacks, stacks


def items_for_units(units: int) -> int:
    """Pool ITEM count for `units` of supply -- what the pool-share ceiling actually has to bound.

    The ceiling exists to stop the injection eating the filler pool, and the pool is charged per
    ITEM, not per unit. Bounding units instead (which is what this did while every fragment was a
    single) would under-count a stacked injection by half and let it overrun the share it was given.
    """
    singles, stacks = split_injection(units)
    return singles + stacks


def fragments_to_inject(mode: int, target: int, natural: int, total_locations: int,
                        excluded: bool) -> int:
    """How many Scadutree Fragments this seed must inject. PURE -- no world, no AP.

    `mode` is the derived blessing mode (0 off / 1 anywhere / 2 anywhere+catch-up /
    3 dlc_only+catch-up); `target` is SCADU_INJECTION_TARGET, the level the seed GUARANTEES is
    reachable; `natural` is the fragments already in the pool from kept regions; `excluded` is True
    when the fragment is DLC-excluded this seed.

    🛑 MODES 1 AND 2 ONLY, and mode 3 is not an oversight. Mode 3 is vanilla SCOPE -- the game still
    runs its own fragment ladder and the catch-up floor does the work inside the DLC -- so injecting
    fragments would be paying pool pressure for a curve the player deliberately declined.
    """
    if mode not in (1, 2) or excluded:
        return 0
    if target <= 0 or target >= len(SCADU_CUM):
        # An out-of-range target is a bug upstream, not something to guess a budget for.
        return 0
    want = SCADU_CUM[target] - max(0, natural)
    if want <= 0:
        return 0
    ceiling = int(max(0, total_locations) * MAX_POOL_SHARE)
    # Shed UNITS until the ITEMS they become fit the share. A closed form exists (items = w - w//4)
    # but the loop is bounded by SCADU_CUM[20] = 50 and says what it means; a seed this small is
    # already being told, loudly, that it cannot reach the target.
    while want > 0 and items_for_units(want) > ceiling:
        want -= 1
    # ...but never below the FLOOR (2026-08-25, #1013 -- see CLAMP_FLOOR_LEVEL): the clamp may
    # starve the TARGET, not the original cap. The breach is bounded at floor units, and it only
    # fires on a REAL pool -- a zero ceiling means a pool too small to charge (total < 10), where
    # injecting 26 units would BE the pool. No real seed is that small (the hub alone is not).
    floor_level = min(CLAMP_FLOOR_LEVEL, target)
    floor_want = SCADU_CUM[floor_level] - max(0, natural)
    if ceiling > 0 and want < floor_want:
        want = floor_want
    return want


def target_for_difficulty(maximum_difficulty_pct: int) -> int:
    """Resolved enemy ceiling -> guaranteed blessing level.

    The automatic enemy ceiling already scales with run length. Reuse that resolved percentage so
    a short seed does not reserve the full 50-fragment budget needed only by an uncapped run. An
    explicit maximum follows the same conversion, so explicitly selecting 100 still requests 20.
    Round upward: the supply must not land below the ceiling it is intended to counterweight.
    """
    pct = max(0, min(100, int(maximum_difficulty_pct)))
    return int(math.ceil((len(SCADU_CUM) - 1) * pct / 100.0))


def natural_fragments(world) -> int:
    """Scadutree Fragments already headed for the pool from this seed's kept regions.

    Same source and same shape as `presence_floor.present_roster` -- `LOCATION_ITEM` over
    `[HUB] + kept` -- because that is what `core.create_items` actually draws the vanilla extras
    from. Zero when `item_shuffle` is off: no vanilla item enters the pool at all then, so every
    fragment is absent rather than present.

    ⭐ UNITS, NOT PLACEMENTS (#616, 2026-08-13). Four of vanilla's 46 fragment lot slots drop x2, so
    46 kept checks hand over 50 units. This used to count placements, because the generated data
    carried no per-lot quantity and the overshoot it caused (up to 4 injected units too many) was
    documented as bounded rather than fixed. `item_ids.LOCATION_UNITS` now carries the quantity and
    `core.create_items` promotes those four locations to `Scadutree Fragment x2`, so counting
    placements here would no longer be a bounded overshoot -- it would be a DISAGREEMENT with the
    pool core actually builds, and test_gf_options asserts `frags == natural + injected` on exactly
    that. So this asks core the same question core asks: `stacked_vanilla_name`, on the same ap id,
    against the same `item_name_to_id`. One arbiter, not a second copy of the rule.
    """
    o = getattr(world.options, "item_shuffle", None)
    if not (o is not None and o.value) or not LOCATION_ITEM:
        return 0
    if FRAGMENT in getattr(world, "gf_dlc_excluded", frozenset()):
        return 0
    from ..core import stacked_vanilla_name  # local: core imports the feature registry
    name_to_id = getattr(world, "item_name_to_id", None) or {}
    kept = list(world._kept()) if hasattr(world, "_kept") else []
    n = 0
    for rn in [HUB] + kept:
        # Core builds the pool from `_seed_locations`, after progression-surface and other
        # per-seed location filters. Counting raw LOCATIONS here credited fragments on checks that
        # would never enter the pool; the rolled witness reached 49/50 after one such row was cut.
        # Fall back only for the tiny pure-test worlds that deliberately provide no core seam.
        rows = (world._seed_locations(rn) if hasattr(world, "_seed_locations")
                else LOCATIONS.get(rn, []))
        for (_name, ap_id, _flag) in rows:
            if LOCATION_ITEM.get(ap_id) == FRAGMENT:
                n += stacked_vanilla_name(FRAGMENT, ap_id, name_to_id)[1]
    return n


def _total_locations(world) -> int:
    """The seed's location count, mirroring `core.create_items`' own arithmetic (LOCATIONS over
    HUB + kept, plus feature-owned extras). Used only to bound the injection."""
    kept = list(world._kept()) if hasattr(world, "_kept") else []
    total = len(LOCATIONS.get(HUB, [])) + sum(len(LOCATIONS.get(r, [])) for r in kept)
    return total + len(getattr(world, "gf_extra_locations", ()))


def plan(world):
    """-> (mode, target, natural, want, injected). The numbers the log line reports."""
    from . import scaling
    # 🛑 THE DERIVED MODE, never the deprecated `global_scadutree_blessing` option. It was split on
    # 2026-08-06 into scadutree_blessing_scope + dlc_blessing_catchup; reading the old key here
    # would see 0 for every player who used the new names and this seed would inject nothing while
    # the blessing was on -- silently reproducing the exact supply bug this whole file exists to fix.
    mode = scaling.blessing_mode(world)
    target = target_for_difficulty(scaling.resolved_max_difficulty(world))
    excluded = FRAGMENT in getattr(world, "gf_dlc_excluded", frozenset())
    natural = natural_fragments(world)
    total = _total_locations(world)
    injected = fragments_to_inject(mode, target, natural, total, excluded)
    bad_target = target <= 0 or target >= len(SCADU_CUM)
    want = 0 if (mode not in (1, 2) or excluded or bad_target) else max(
        0, SCADU_CUM[target] - natural)
    return mode, target, natural, want, injected


@register
class ScaduSupply(Feature):
    name = "scadu_supply"
    # No NEW item names: "Scadutree Fragment" is already a registered ITEM_CATALOG good with its
    # FullID in _AP_IDS_TO_ITEM_IDS, so the client grants it unchanged and the blessing's
    # received-stream counter (er-logic `SCADU_FRAGMENT_GOODS`) recognises it. Declaring it in ITEMS
    # would mint a fresh feature id and DROP that mapping -- same reasoning as presence_floor.
    # The x2 stack IS a minted feature item (the x1 is not -- it is already an ITEM_CATALOG good
    # whose id and FullID mapping core builds). Minting alone would leave it ungrantable, which is
    # what the note above warns about, so ITEM_GRANTS carries the two things core cannot infer: the
    # game FullID it resolves to, and the quantity the client hands over.
    ITEMS = {FRAGMENT_X2: ItemClassification.useful}
    ITEM_GRANTS = {FRAGMENT_X2: (ITEM_CATALOG.get(FRAGMENT, 0), 2)} if ITEM_CATALOG else {}

    def create_items(self, world) -> List:
        import logging
        mode, target, natural, want, injected = plan(world)
        log = logging.getLogger("Greenfield")
        if mode not in (1, 2):
            return []
        # Arming telemetry: COUNTS, not a boolean. "inert because X" is required of any path that
        # can degrade to a no-op (CONTRIBUTING, Runtime visibility), and the count is what tells a
        # degenerate seed apart from a working one.
        if want == 0 and natural == 0:
            log.info(
                "[%s:%d] scadu_supply: INERT -- mode %d but Scadutree Fragment is unavailable "
                "this seed (DLC-excluded or item_shuffle off); the blessing has no fragments",
                world.game, world.player, mode)
        elif injected < want:
            floor_units = SCADU_CUM[CLAMP_FLOOR_LEVEL]
            if natural + injected >= floor_units and items_for_units(injected) > int(
                    _total_locations(world) * MAX_POOL_SHARE):
                log.warning(
                    "[%s:%d] scadu_supply: target %d needs %d fragment unit(s), seed has %d "
                    "natural, and the %.0f%% pool-share clamp stops injection at %d -- the "
                    "blessing cannot reach its target this seed, but the level-%d floor (%d "
                    "units) overrode the ceiling, so it holds its original cap and only the "
                    "target is lost",
                    world.game, world.player, target, SCADU_CUM[target], natural,
                    MAX_POOL_SHARE * 100, injected, CLAMP_FLOOR_LEVEL, floor_units)
            else:
                log.warning(
                    "[%s:%d] scadu_supply: target %d needs %d fragment unit(s), seed has %d natural, "
                    "but only %d could be injected (%d pool item(s), clamped to %.0f%% of %d "
                    "locations) -- the blessing cannot reach its target this seed",
                    world.game, world.player, target, SCADU_CUM[target], natural, injected,
                    items_for_units(injected), MAX_POOL_SHARE * 100, _total_locations(world))
        else:
            log.info(
                "[%s:%d] scadu_supply: %d fragment unit(s) in pool for target %d (%d natural + %d "
                "injected as %d x1 + %d x2 = %d item(s))",
                world.game, world.player, natural + injected, target, natural, injected,
                *split_injection(injected), items_for_units(injected))
        singles, stacks = split_injection(injected)
        out: List = []
        for name, n in ((FRAGMENT, singles), (FRAGMENT_X2, stacks)):
            for _ in range(n):
                it = world.create_item(name)
                # 🛑 useful, NEVER progression. Nothing in the logic may require a blessing level:
                # the whole feature is an optional power curve, and a progression fragment would put
                # the fill under a constraint the vanilla game does not have.
                it.classification = ItemClassification.useful
                out.append(it)
        return out
