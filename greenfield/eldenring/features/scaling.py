"""SPEC-PARITY Phase 2 -- completion scaling + Scadutree blessing (COMPLETE).

Curve is client-side (smoothstep over sphere; completion_scaling=4); the gate/floor the client
actually reads live in sd["options"] (core._options_echo, F1 fix). This feature adds the option
surface, the legacy top-level echoes, and -- as of I2 (2026-07-06) -- the LIVE scaling wire:

  regionSphereTargetRanges = [[lo, hi, target], ...]   (er-logic/scaling.rs:150-165, SCALING_WIRE)

with lo == hi == a region's 5-digit play_region bucket (runtime play_region_id / 100 -- the SAME
bucket space areaLockFlags speaks; geometry reused from features/area_locks.REGION_PLAY_IDS, itself
REGION_ID_MAP.md-derived, matt-free). target = the region's position in a TOTAL topological order
of the seed's lock chain, normalized to 0..TARGET_MAX (the client re-normalizes by the max emitted
target, tier_for_target).

THE ORDER RAMP (2026-07-15, Alaric playtest: "felt easy... spent most time in sphere 1-2"). Scaling
used to be keyed on the raw FILL SPHERE, so every same-sphere region got the SAME target -- and the
lock DAG is wide early, so most of the map sat at the sphere-1/2 tier. Now the spheres (the DAG's
level structure, from mw.get_spheres()) are LINEARIZED into a total order: sphere ascending, with a
seed-deterministic RANDOM tie-break among same-sphere regions (_order_from_spheres). Scaling ramps
evenly over ORDER POSITION 0..N-1 -> target 0..TARGET_MAX (_targets_from_order), so two same-sphere
regions land on different tiers, the mid/high tiers are actually populated, and the curve still
never puts a region above its reachability: sphere-primary sort means a region's target is always
strictly below every strictly-later-sphere region's target (asserted at gen). Same seed -> same
order -> same scaling (the tie-break RNG is keyed on (multiworld.seed, player), NOT the shared
world.random stream -- see _order_rng). FALLBACK when the fill spheres are uncomputable: SPINE-order
depth (sphere_target_ranges) -- pure + deterministic, independent of num_regions_order roll order,
and already a total order. A bucket absent from the wire (hub, tutorial, unmapped sub-areas) falls
back to the client's floor tier -- unknown = don't scale up. The flat map (regionSphereTargets) is emitted transitionally as {} by core.py;
ranges are the live wire, so this feature deliberately does NOT emit the flat key (merge_slot_data
raises on duplicate keys).
"""
import random

from Options import Range, Choice
from ..registry import Feature, register
from ..region_spine import SPINE, DLC_REGIONS
from .. import contract
from .area_locks import REGION_PLAY_IDS

# Wire normalization ceiling. The client normalizes by the max emitted target (scaling.rs
# tier_for_target), so the exact ceiling only needs enough integer resolution over er-logic's
# 10-tier ladder; 10000 matches the frozen I2 spec.
TARGET_MAX = 10000


# ---- Intra-fold scaling delta (2026-07-22, Alaric; SPEC-intra-fold-scaling-delta-20260722.md) ----
# A region's sphere target is broadcast FLAT to all its play_region buckets. When a region FOLDS
# several vanilla areas of different native difficulty into one bucket-set, that flattens them --
# worst case Greyoll's Dragonbarrow, a late-tier pocket inside the Caelid bucket, scaled down to
# Caelid's target. This adds a HAND-AUTHORED per-bucket DELTA (target-space, 0..TARGET_MAX) applied
# ON TOP of the region's target, CLAMPED so a bumped bucket can never reach the NEXT region's target
# in the order (a local nudge, never a sphere-jump; preserves the "strictly below every later region"
# invariant the order ramp asserts, and never inflates the max the client normalizes by). Playtest-
# feel values, exactly like DLC_BLESSING_FLOORS. Scope = folded sub-areas ONLY (delta 0 == identity).
# This is INTRA-fold variance, NOT cross-region reordering -- the 2026-06-19 "same sphere = same tier /
# don't fix inversions" ruling is about REGION ordering and is untouched.
_SCALING_BUCKET_DELTA = {
    # bucket (play_region_id // 100) : delta in target space (0..TARGET_MAX)
    64020: 2500,   # !! CONFIRM BUCKET + TUNE VALUE: Greyoll's Dragonbarrow (m60_49_40; m60_51_43 --
                   #    the NE Caelid overworld tiles). Late-tier pocket folded into Caelid; this bumps
                   #    it back toward its vanilla difficulty. 2500 ~= a couple tiers on the 0..10000 ramp.
}


def _apply_bucket_delta(triples):
    """Add _SCALING_BUCKET_DELTA to matching buckets, clamped STRICTLY below the next distinct region
    target (never a sphere-jump; never inflates the client-normalized max). Pure; empty delta ==
    identity. triples = [[lo, hi, target], ...] with lo == hi == the bucket."""
    if not _SCALING_BUCKET_DELTA:
        return triples
    distinct = sorted({t for _, _, t in triples})
    out = []
    for lo, hi, target in triples:
        d = _SCALING_BUCKET_DELTA.get(lo, 0)  # lo == hi == play_region bucket
        if d:
            nxt = next((t for t in distinct if t > target), None)
            ceil = (nxt - 1) if nxt is not None else TARGET_MAX
            target = min(target + d, ceil)
        out.append([lo, hi, target])
    return out


def sphere_target_ranges(kept):
    """[[lo, hi, target], ...] triples for `kept` region names (pure; unit-testable without AP).

    SPINE-ordered depth within the kept set, normalized so the deepest kept region == TARGET_MAX.
    One lo == hi triple per play_region bucket of each kept region (same bucket space as
    areaLockFlags). A single kept region emits target 0 (max target 0 == floor everywhere,
    scaling.rs) -- a one-region seed has no progression depth to scale over.
    """
    ordered = [r for r in SPINE if r in set(kept)]
    span = max(len(ordered) - 1, 1)
    triples = []
    for i, region in enumerate(ordered):
        target = round(i * TARGET_MAX / span)
        for pid in REGION_PLAY_IDS.get(region, []):
            triples.append([pid, pid, target])
    return _apply_bucket_delta(triples)


def _region_fill_spheres(world):
    """kept region -> the playthrough sphere its `<R> Lock` is obtained in (0 = start/precollected).
    TRUE FILL SPHERE: reflects where each lock actually landed this seed, so a random-start
    num_regions seed scales from the region you can reach, not geography. {} if uncomputable."""
    player = world.player
    mw = world.multiworld
    lock_to_region = {f"{r} Lock": r for r in world._kept()}
    sphere = {}
    for it in mw.precollected_items[player]:            # start-open region(s) -> sphere 0
        r = lock_to_region.get(it.name)
        if r is not None:
            sphere[r] = 0
    try:
        for i, locset in enumerate(mw.get_spheres()):   # 0-indexed fill spheres; +1 keeps start below
            for loc in locset:
                it = getattr(loc, "item", None)
                if it is not None and getattr(it, "player", None) == player:
                    r = lock_to_region.get(it.name)
                    if r is not None and r not in sphere:
                        sphere[r] = i + 1
    except Exception:
        return {}
    if sphere:                                          # any lock not located -> treat as deepest
        deepest = max(sphere.values())
        for r in world._kept():
            sphere.setdefault(r, deepest + 1)
    return sphere


def _order_from_spheres(region_sphere, rng):
    """A TOTAL topological order (linearization of the lock-chain DAG) over the regions of
    `region_sphere`. Primary key = the region's fill sphere (the DAG's level structure -- a sphere-i
    lock can only require locks from spheres < i, so sphere-ascending IS a valid topological sort);
    tie-break among same-sphere regions = random jitter from `rng` (seed-deterministic, see
    _order_rng). The base iteration order is sorted() so the jitter is the ONLY tie-breaker -- dict
    insertion order (which leaks set iteration order from mw.get_spheres()) never reaches the wire.
    The topological property is ASSERTED, not trusted: if the order ever puts a region before a
    strictly-earlier-sphere region, generation dies loudly rather than shipping an inverted curve."""
    regions = sorted(region_sphere)
    jitter = {r: rng.random() for r in regions}
    order = sorted(regions, key=lambda r: (region_sphere[r], jitter[r]))
    for a, b in zip(order, order[1:]):
        if region_sphere[a] > region_sphere[b]:
            raise AssertionError(
                f"scaling order is not a topological sort of the lock chain: {a!r} (sphere "
                f"{region_sphere[a]}) precedes {b!r} (sphere {region_sphere[b]})")
    return order


def _targets_from_order(order):
    """region -> target 0..TARGET_MAX: an even, strictly MONOTONIC ramp over the total order
    (position 0 -> 0, last -> TARGET_MAX; a single region -> 0, no depth to scale over). Same-sphere
    regions occupy different positions, so they get DIFFERENT targets -- that is the point of the
    order ramp. Monotone along reachability by construction: the order is sphere-primary, so no
    region's target ever exceeds a region it cannot precede."""
    span = max(len(order) - 1, 1)
    return {r: round(i * TARGET_MAX / span) for i, r in enumerate(order)}


def _order_rng(world):
    """Seed-deterministic RNG for the same-sphere tie-breaks. Deliberately NOT world.random: slot_data
    is built more than once for one seed (fill_slot_data re-entry; test_slot_data_is_deterministic),
    and drawing from the shared stream would reshuffle the order on every call. Keyed on
    (multiworld.seed, player) so it is stable per seed and per player, and independent of every other
    roll in the generation -- the guarantee the old SPINE-depth comment promised, kept true."""
    return random.Random(f"{world.multiworld.seed}:{world.player}:er-scaling-order")


def _ranges_from_targets(region_target):
    """[[lo, hi, target], ...] sorted by play_region id.

    DETERMINISM: `region_target` inherits its dict ORDER from `_region_fill_spheres`, which walks
    `mw.get_spheres()` -- and each sphere is a SET, whose iteration order varies between runs. The
    VALUES are stable (every lock in sphere i gets i+1), but the insertion order is not, so emitting
    in dict order made slot_data differ for the SAME seed run twice. Sort so the wire is a pure
    function of the fill result. (Caught by test_gf_world::test_slot_data_is_deterministic.)"""
    triples = []
    for region, target in region_target.items():
        for pid in REGION_PLAY_IDS.get(region, []):
            triples.append([pid, pid, target])
    return sorted(_apply_bucket_delta(triples))


# ---- DLC Scadutree-blessing floors (global_scadutree_blessing == 2 "scaled") --------------------
# DLC enemies are tuned around a per-AREA Scadutree Blessing level (a DLC-only player-side damage/
# defence multiplier), decoupled from runes/level. In this rando the fragments that raise blessing are
# scattered multiworld checks, so you can reach a DLC region with ~0 blessing and get brutalised. Mode
# 2 grants a blessing FLOOR keyed on which DLC region you're in (NOT the normalized sphere depth --
# blessing expectation is ABSOLUTE per area: Bayle assumes ~14 whenever you fight him, however deep the
# seed put Jagged Peak). Floors sit ~3-4 levels UNDER vanilla expectation so collected fragments still
# buy visible power; the client's raise-only writer takes max(held-fragment level, floor). (fable
# consult 2026-07-11.)
# Region-spine v2: the DLC split means every floor is per-REGION now; values carried over where the
# region existed before, and the regions split OUT of a coarse one start from vanilla-expectation
# feel (~3-4 under, same rule): Ensis/Cerulean/Charo's were inside Gravesite's floor-1 blanket and
# are tuned a little above it; Stone Coffin keeps the 10 it had as a per-bucket override of
# Gravesite; Scaduview (Metyr, Keep environs) and Rauh Base ride their neighbours. Playtest-feel
# values -- flagged for review in SPEC-region-spine-v2.md, like the boss scaling tiers.
DLC_BLESSING_FLOORS = {
    "Gravesite": 1,
    "Ensis": 2,
    "Cerulean": 2,
    "Charo's": 2,
    "Belurat": 3,
    "Scadu Altus": 7,
    "Shadow Keep": 10,   # includes the folded-in Scaduview Hinterland (2026-07-19); same floor it had
    "Stone Coffin": 10,
    "Rauh Base": 10,
    "Ancient Ruins": 12,
    "Jagged Peak": 12,
    "Abyssal": 12,
    "Enir Ilim": 15,
}
# Per-play_region-bucket overrides for sub-areas whose native tuning diverges from their region
# floor. EMPTY since the v2 split -- Stone Coffin (22000), the only entry, is its own region now.
# Kept as a mechanism: a future shared-bucket sub-area (an Ellac-class fold) may need one.
_DLC_BLESSING_BUCKET_OVERRIDE = {}


def blessing_floor_ranges(kept):
    """[[lo, hi, floor], ...] Scadutree-blessing floors per DLC-region play_region bucket, for the kept
    DLC regions (pure; unit-testable without AP). Same lo==hi bucket space as regionSphereTargetRanges /
    areaLockFlags. Empty when no DLC region is kept. Per-bucket overrides win over the region floor."""
    keptset = set(kept)
    triples = []
    for region in DLC_REGIONS:
        if region not in keptset:
            continue
        base = DLC_BLESSING_FLOORS.get(region, 0)
        for pid in REGION_PLAY_IDS.get(region, []):
            triples.append([pid, pid, _DLC_BLESSING_BUCKET_OVERRIDE.get(pid, base)])
    return triples


class CompletionScalingFloor(Range):
    """Minimum completion-scaling tier as a percent of max, applied from the start so early regions
    aren't trivially weak. 0 = the full smoothstep curve from zero."""
    display_name = "Completion Scaling Floor"
    range_start = 0
    range_end = 50
    default = 0


class GlobalScadutreeBlessing(Choice):
    """How Scadutree Blessing (the DLC-only combat multiplier) is delivered. The stored blessing byte
    is DLC-area-gated by the engine, so NONE of these modes touch base-game balance. off = vanilla
    (blessing only from fragments you hold, applied by the game). player_only = the client raises your
    blessing from held Scadutree Fragments via the vanilla curve (same effect, applied eagerly).
    scaled = player_only PLUS a per-DLC-region blessing FLOOR, so a DLC region you unlock without
    fragments still meets that area's expected blessing and its enemies aren't insane; collected
    fragments still count above the floor (max). Default OFF (2026-07-18 balance call): the floor made
    the DLC too easy -- you started every area already blessed -- so blessing is fully vanilla by
    default (earn it from fragments). scaled/player_only remain available if you want the safety net."""
    display_name = "Global Scadutree Blessing"
    option_off = 0
    option_player_only = 1
    option_scaled = 2
    default = 0


@register
class Scaling(Feature):
    name = "scaling"
    OPTIONS = {
        "completion_scaling_floor": CompletionScalingFloor,
        "global_scadutree_blessing": GlobalScadutreeBlessing,
    }

    def slot_data(self, world):
        # ORDER RAMP (2026-07-15): the fill spheres (TRUE per-seed reachability, 2026-07-07) are
        # linearized into a total topological order with seed-deterministic tie-breaks, and the
        # target ramps over ORDER POSITION -- so same-sphere regions scale differently and the
        # mid/high tiers are populated even though the lock DAG is wide early ("felt easy").
        # SPINE-order depth is the fallback when the fill sphere can't be computed (no world /
        # degenerate); it is already a total order.
        region_sphere = _region_fill_spheres(world)
        if region_sphere:
            order = _order_from_spheres(region_sphere, _order_rng(world))
            ranges = _ranges_from_targets(_targets_from_order(order))
        else:
            ranges = sphere_target_ranges(world._kept())
        blessing = int(world.options.global_scadutree_blessing.value)
        out = {
            "completion_scaling": 4,  # smoothstep (client curve id; SPEC-PARITY P2)
            "completion_scaling_floor": int(world.options.completion_scaling_floor.value),
            "global_scadutree_blessing": blessing,
            contract.REGION_SPHERE_TARGET_RANGES: ranges,
        }
        # mode 2 (scaled): emit the per-DLC-region blessing floor wire, but only when DLC regions are
        # actually kept (otherwise inert -- no key, so a base-game seed is byte-identical to mode 1).
        if blessing == 2:
            kept = world._kept()
            if set(kept) & DLC_REGIONS:
                floors = blessing_floor_ranges(kept)
                if floors:
                    out[contract.DLC_SCADUTREE_FLOOR_RANGES] = floors
        return out
