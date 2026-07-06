"""SPEC-PARITY Phase 2 -- completion scaling + Scadutree blessing (COMPLETE).

Curve is client-side (smoothstep over sphere; completion_scaling=4); core already emits
regionSphereTargets/completionScalingBasis. This feature adds the option surface + the floor and
DLC-blessing knobs. No data derivation -- pure option -> slot_data. Matt-free (curve is math).
"""
from Options import Range, Choice
from ..registry import Feature, register


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
        return {
            "completion_scaling": 4,  # smoothstep (client curve id; SPEC-PARITY P2)
            "completion_scaling_floor": int(world.options.completion_scaling_floor.value),
            "global_scadutree_blessing": int(world.options.global_scadutree_blessing.value),
        }
