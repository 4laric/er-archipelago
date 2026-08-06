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
# It does not bind today -- the smallest measured seed is 727 locations (num_regions 1) and the cap
# of 12 needs 26 fragments, 3.6%. It exists because the cap is explicitly a tunable ("if the
# playtest says it feels weak, raise this ONE constant", scaling.py:393) and raising it to 20 costs
# 50 fragments. A feature that can over-constrain the fill gates itself on what the pool can supply
# (CONTRIBUTING, Feature architecture); a guard nobody can trigger is untested, so
# `fragments_to_inject` is pure and the clamp path has a direct unit test.
MAX_POOL_SHARE = 0.10


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
    return want


def natural_fragments(world) -> int:
    """Scadutree Fragments already headed for the pool from this seed's kept regions.

    Same source and same shape as `presence_floor.present_roster` -- `LOCATION_ITEM` over
    `[HUB] + kept` -- because that is what `core.create_items` actually draws the vanilla extras
    from. Zero when `item_shuffle` is off: no vanilla item enters the pool at all then, so every
    fragment is absent rather than present.

    ⚠️ COUNTS PLACEMENTS, NOT UNITS -- a known, BOUNDED overshoot. Four of vanilla's 46 fragment lot
    slots drop x2 (datamined 2026-08-06), and the generated data carries no per-lot quantity, so a
    seed keeping all four reads its natural supply as 4 units low and injects up to 4 more than it
    needs. Overshoot, never shortfall, and capped at 4 out of 50. Fixing it properly means teaching
    gen_data.py to carry lot quantities and regenerating, which is a data change and does not belong
    in an options PR.
    """
    o = getattr(world.options, "item_shuffle", None)
    if not (o is not None and o.value) or not LOCATION_ITEM:
        return 0
    if FRAGMENT in getattr(world, "gf_dlc_excluded", frozenset()):
        return 0
    kept = list(world._kept()) if hasattr(world, "_kept") else []
    n = 0
    for rn in [HUB] + kept:
        for (_name, ap_id, _flag) in LOCATIONS.get(rn, []):
            if LOCATION_ITEM.get(ap_id) == FRAGMENT:
                n += 1
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
    target = SCADU_INJECTION_TARGET
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
