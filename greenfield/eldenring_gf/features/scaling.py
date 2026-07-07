"""SPEC-PARITY Phase 2 -- completion scaling + Scadutree blessing (COMPLETE).

Curve is client-side (smoothstep over sphere; completion_scaling=4); the gate/floor the client
actually reads live in sd["options"] (core._options_echo, F1 fix). This feature adds the option
surface, the legacy top-level echoes, and -- as of I2 (2026-07-06) -- the LIVE scaling wire:

  regionSphereTargetRanges = [[lo, hi, target], ...]   (er-logic/scaling.rs:150-165, SCALING_WIRE)

with lo == hi == a region's 5-digit play_region bucket (runtime play_region_id / 100 -- the SAME
bucket space areaLockFlags speaks; geometry reused from features/area_locks.REGION_PLAY_IDS, itself
REGION_ID_MAP.md-derived, matt-free). target = the region's progression depth, normalized to
0..TARGET_MAX with the DEEPEST kept region == TARGET_MAX (the client re-normalizes by the max
emitted target, tier_for_target). Depth = the region's position along region_spine.SPINE *within
the kept set*: pure + deterministic (independent of num_regions_order roll order), first kept
region -> 0 (floor tier), deepest -> TARGET_MAX (top tier), even ramp between. A bucket absent from
the wire (hub, tutorial, unmapped sub-areas) falls back to the client's floor tier -- unknown =
don't scale up. The flat map (regionSphereTargets) is emitted transitionally as {} by core.py;
ranges are the live wire, so this feature deliberately does NOT emit the flat key (merge_slot_data
raises on duplicate keys).
"""
from Options import Range, Choice
from ..registry import Feature, register
from ..region_spine import SPINE
from .. import contract
from .area_locks import REGION_PLAY_IDS

# Wire normalization ceiling. The client normalizes by the max emitted target (scaling.rs
# tier_for_target), so the exact ceiling only needs enough integer resolution over er-logic's
# 10-tier ladder; 10000 matches the frozen I2 spec.
TARGET_MAX = 10000


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
    return triples


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


def _targets_from_spheres(region_sphere):
    """region -> target 0..TARGET_MAX, normalized so the deepest sphere == TARGET_MAX; regions that
    share a sphere share a target (equal access depth = equal scaling)."""
    if not region_sphere:
        return {}
    max_s = max(region_sphere.values())
    if max_s <= 0:
        return {r: 0 for r in region_sphere}
    return {r: round(s / max_s * TARGET_MAX) for r, s in region_sphere.items()}


def _ranges_from_targets(region_target):
    triples = []
    for region, target in region_target.items():
        for pid in REGION_PLAY_IDS.get(region, []):
            triples.append([pid, pid, target])
    return triples


class CompletionScalingFloor(Range):
    """Minimum completion-scaling tier as a percent of max, applied from the start so early regions
    aren't trivially weak. 0 = the full smoothstep curve from zero."""
    display_name = "Completion Scaling Floor"
    range_start = 0
    range_end = 50
    default = 0


class GlobalScadutreeBlessing(Choice):
    """DLC Scadutree blessing scope. off = DLC-only (vanilla); player_only = your blessing applies
    game-wide; scaled = blessing level scales with progress everywhere."""
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
        # TRUE FILL SPHERE (2026-07-07): target = the playthrough sphere each region's Lock is
        # obtained in (start-open region -> 0 floor), so a random-start num_regions seed scales from
        # the region you can actually reach, not geography. SPINE-order depth is the fallback when the
        # fill sphere can't be computed (no world / degenerate).
        region_sphere = _region_fill_spheres(world)
        ranges = (_ranges_from_targets(_targets_from_spheres(region_sphere))
                  if region_sphere else sphere_target_ranges(world._kept()))
        return {
            "completion_scaling": 4,  # smoothstep (client curve id; SPEC-PARITY P2)
            "completion_scaling_floor": int(world.options.completion_scaling_floor.value),
            "global_scadutree_blessing": int(world.options.global_scadutree_blessing.value),
            contract.REGION_SPHERE_TARGET_RANGES: ranges,
        }
