"""Attunement-release boss gate (opt-in) -- SPEC-gf-boss-lock-tracker.md "Attunement-release design".

Warp-and-kill lets a player skip a region by warping to its boss grace and killing the boss. This gate
answers that WITHOUT gating the fight: on lock receipt only K seeded-random graces light (the random
entry door); the region's boss payout DEFERS until the player has COLLECTED `threshold` of the region's
freely-reachable checks ("attunement"), at which point the region's remaining graces bloom and the
banked boss reward releases. All client machinery is the EXISTING grace-lighting + P3b flag-watch +
deferred/burst-release path -- this feature only EMITS the plan; it adds NO items, regions, or rules,
so it is winnable by construction (attunement is always satisfiable from the region's own checks, which
need nothing but the region Lock).

Gated behind `attunement_gate` (Toggle, default 0):
  OFF -> zero change: grace_rando keeps its freebie/bundle behavior, no regionAttunement key is emitted,
         and world.random is NOT touched (default seeds stay byte-identical).
  ON  -> emits regionAttunement and hands grace_rando the K random-start graces via world.gf_attunement.

Emitted (kept regions only, gate ON):
  regionAttunement = {region: {"threshold": int, "member_ap_ids": [int], "bloom_flags": [int]}}

  threshold      = clamp(round(0.10 * N), 5, 20), then capped at N so it is ALWAYS satisfiable from the
                   region's own checks. N = the region's FREELY-REACHABLE check count = its checks minus
                   boss-arena (LOCATION_TAGS 'Boss') and missable (MISSABLE_LOCATIONS) -- same freely-
                   placeable lesson as the important_locations juice guard.
  member_ap_ids  = that freely-reachable ap_id set (what counts toward attunement).
  K (start doors)= clamp(ceil(n_graces / 8), 1, 3) seeded-random graces (n_graces = REGION_GRACE_POINTS
                   for the region). Deterministic per seed via world.random -> the entry door varies by
                   seed. These K go into regionGraces (lit on lock receipt) via grace_rando.
  bloom_flags    = the region's remaining graces (REGION_GRACE_POINTS minus the K start doors).

Boss-arena grace: REGION_GRACE_POINTS is generated (gen_data.py) with _BOSS_GATED_GRACE_FLAGS and
_ARENA_GRACE_FLAGS ALREADY excluded, so neither the random-start draw nor bloom_flags can ever light a
boss-bonfire / remembrance-arena grace (those don't physically exist until the boss is felled -- lighting
one is a soft-lock). The task's minimum bar (exclude the boss-arena grace + _BOSS_GATED_GRACE_FLAGS) is
therefore met by construction. FOLLOW-UP: the boss-antechamber-NEIGHBOR grace (a real grace beside each
fog gate, ~one curated flag per boss) is NOT yet added to bloom_flags -- identifying it needs an MSB
artifact pass. Until then the client's boss payout is what reveals the arena grace on kill+attune.
"""
import math

from Options import Toggle
from ..registry import Feature, register
from .. import contract

try:
    from ..region_graces import REGION_GRACE_POINTS
except Exception:  # not yet generated
    REGION_GRACE_POINTS = {}
try:
    from ..data import LOCATIONS
except Exception:
    LOCATIONS = {}
try:
    from ..location_tags import LOCATION_TAGS
except Exception:
    LOCATION_TAGS = {}
try:
    from ..missable_locations import MISSABLE_LOCATIONS
except Exception:
    MISSABLE_LOCATIONS = {}


class AttunementGate(Toggle):
    """off (default): regions unlock exactly as today. on: a region lock lights only a few random
    graces, and the region's boss reward stays banked until you have collected enough of that region's
    checks (attunement), then its remaining graces bloom and the banked boss loot releases -- so
    warp-and-kill can't skip a region."""
    display_name = "Attunement Gate"


def _freely_reachable(region):
    """The region's checks that count toward attunement: exclude boss-arena ('Boss' tag) and missable
    checks (the same freely-placeable lesson as important_locations' juice guard)."""
    out = []
    for (_n, ap_id, _f) in LOCATIONS.get(region, []):
        if ap_id in MISSABLE_LOCATIONS:
            continue
        if "Boss" in LOCATION_TAGS.get(ap_id, ()):
            continue
        out.append(ap_id)
    return out


def _threshold(n):
    """clamp(round(0.10*N), 5, 20), then never more than N (so a small region can still attune)."""
    t = min(max(int(round(0.10 * n)), 5), 20)
    return min(t, n)


def _k_start_doors(n_graces):
    """clamp(ceil(n_graces/8), 1, 3): Limgrave(24)->3, Stormveil(10)->2, Raya Lucaria(2)->1."""
    return min(max(math.ceil(n_graces / 8), 1), 3)


def _attunement_on(world):
    o = getattr(world.options, "attunement_gate", None)
    return bool(o is not None and o.value)


@register
class AttunementFeature(Feature):
    name = "attunement"
    OPTIONS = {"attunement_gate": AttunementGate}

    def generate_early(self, world):
        # Compute the per-region plan ONCE, deterministically. Touch world.random ONLY when the gate is
        # ON so default (off) seeds keep byte-identical RNG streams.
        if not _attunement_on(world):
            world.gf_attunement = None
            return
        plan = {}
        for r in world._kept():
            graces = list(REGION_GRACE_POINTS.get(r, []))
            members = _freely_reachable(r)
            if graces:
                k = min(_k_start_doors(len(graces)), len(graces))
                lit = sorted(world.random.sample(graces, k))
            else:
                lit = []
            lit_set = set(lit)
            bloom = [g for g in graces if g not in lit_set]
            plan[r] = {
                "threshold": _threshold(len(members)),
                "member_ap_ids": members,
                "bloom_flags": bloom,
                "region_lit": lit,   # consumed by grace_rando; NOT emitted in regionAttunement
            }
        world.gf_attunement = plan

    def slot_data(self, world):
        plan = getattr(world, "gf_attunement", None)
        if not plan:
            return {}
        return {contract.REGION_ATTUNEMENT: {
            r: {"threshold": v["threshold"],
                "member_ap_ids": list(v["member_ap_ids"]),
                "bloom_flags": list(v["bloom_flags"])}
            for r, v in plan.items()}}
