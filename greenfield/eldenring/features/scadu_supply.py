"""scadu_supply -- guarantee the Scadutree blessing has the fragments its CAP was budgeted for.

WHY THIS EXISTS
---------------
`global_scadutree_blessing` ships a cap (`scaling.SCADU_BLESSING_CAP`, 12) whose entire purpose is
to bound an INJECTION -- SPEC-global-scadutree-blessing-20260729 §9.2 put it to Alaric as
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
    from ..item_ids import LOCATION_ITEM
except Exception:  # pre-regen: no catalog -> nothing resolves, feature is inert
    LOCATION_ITEM = {}
try:
    from ..data import HUB, LOCATIONS
except Exception:
    HUB, LOCATIONS = "Roundtable Hold", {}


FRAGMENT = "Scadutree Fragment"

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


def fragments_to_inject(mode: int, cap: int, natural: int, total_locations: int,
                        excluded: bool) -> int:
    """How many Scadutree Fragments this seed must inject. PURE -- no world, no AP.

    `mode` is `global_scadutree_blessing` (0 off / 1 player_only / 2 scaled); `cap` is
    `scaduBlessingCap`; `natural` is the fragments already in the pool from kept regions;
    `excluded` is True when the fragment is DLC-excluded this seed.
    """
    if mode not in (1, 2) or excluded:
        return 0
    if cap <= 0 or cap >= len(SCADU_CUM):
        # An out-of-range cap is a bug upstream, not something to guess a budget for.
        return 0
    want = SCADU_CUM[cap] - max(0, natural)
    if want <= 0:
        return 0
    ceiling = int(max(0, total_locations) * MAX_POOL_SHARE)
    return min(want, ceiling)


def natural_fragments(world) -> int:
    """Scadutree Fragments already headed for the pool from this seed's kept regions.

    Same source and same shape as `presence_floor.present_roster` -- `LOCATION_ITEM` over
    `[HUB] + kept` -- because that is what `core.create_items` actually draws the vanilla extras
    from. Zero when `item_shuffle` is off: no vanilla item enters the pool at all then, so every
    fragment is absent rather than present.
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
    """-> (mode, cap, natural, want, injected). The numbers the log line reports."""
    from . import scaling
    o = getattr(world.options, "global_scadutree_blessing", None)
    mode = int(o.value) if o is not None else 0
    cap = int(getattr(scaling, "SCADU_BLESSING_CAP", 0))
    excluded = FRAGMENT in getattr(world, "gf_dlc_excluded", frozenset())
    natural = natural_fragments(world)
    total = _total_locations(world)
    injected = fragments_to_inject(mode, cap, natural, total, excluded)
    bad_cap = cap <= 0 or cap >= len(SCADU_CUM)
    want = 0 if (mode not in (1, 2) or excluded or bad_cap) else max(0, SCADU_CUM[cap] - natural)
    return mode, cap, natural, want, injected


@register
class ScaduSupply(Feature):
    name = "scadu_supply"
    # No NEW item names: "Scadutree Fragment" is already a registered ITEM_CATALOG good with its
    # FullID in _AP_IDS_TO_ITEM_IDS, so the client grants it unchanged and the blessing's
    # received-stream counter (er-logic `SCADU_FRAGMENT_GOODS`) recognises it. Declaring it in ITEMS
    # would mint a fresh feature id and DROP that mapping -- same reasoning as presence_floor.
    ITEMS = {}

    def create_items(self, world) -> List:
        import logging
        mode, cap, natural, want, injected = plan(world)
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
                "[%s:%d] scadu_supply: cap %d needs %d fragment(s), seed has %d natural, but only "
                "%d could be injected (clamped to %.0f%% of %d locations) -- the blessing cannot "
                "reach its cap this seed",
                world.game, world.player, cap, SCADU_CUM[cap], natural, injected,
                MAX_POOL_SHARE * 100, _total_locations(world))
        else:
            log.info(
                "[%s:%d] scadu_supply: %d fragment(s) in pool for cap %d (%d natural + %d injected)",
                world.game, world.player, natural + injected, cap, natural, injected)
        out: List = []
        for _ in range(injected):
            it = world.create_item(FRAGMENT)
            it.classification = ItemClassification.useful
            out.append(it)
        return out
