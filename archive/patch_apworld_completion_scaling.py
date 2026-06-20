#!/usr/bin/env python3
"""
patch_apworld_completion_scaling.py -- apworld layer for Completion-Percent Scaling (idea #2).
SPEC: SPEC-completion-scaling.md. Pairs with patch_baker_completion_scaling.py.

The baker reshapes each enemy's existing geographic scaling tier by a curve + floor (flat=vanilla,
gentle=easier-for-longer, steep=harder-sooner). In ER, geographic tier IS the completion order, so
reshaping the native curve is the faithful version and needs no region->enemy bridge. This patch
only adds the two options and emits them so the baker can read them.

options.py: CompletionScaling (off/flat/gentle/steep) + CompletionScalingFloor (0..50 % of MaxTier),
registered on EROptions.
__init__.py: emit completion_scaling + completion_scaling_floor INTO slot_data["options"] (baker
reads via (slotData["options"] as JObject)?["..."]?.Value<int>(), like dungeon_sweep).

Requires enemy_rando ON (baker scaling pass runs only in the enemy randomizer).
Run on Windows. Idempotent. Binary I/O preserves CRLF. Composes with patch_apworld_random_start.py.
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
OPTIONS = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "options.py")
INIT = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "__init__.py")


def _read(p):
    with open(p, "rb") as f:
        return f.read()


def _write(p, d):
    with open(p, "wb") as f:
        f.write(d)


def _crlf(t):
    return t.replace("\n", "\r\n").encode("utf-8")


def _ins_before(data, anchor, insert, label):
    if data.count(anchor) != 1:
        raise SystemExit(f"[FAIL] {label}: anchor x{data.count(anchor)} (want 1). No write.")
    return data.replace(anchor, insert + anchor, 1)


def _ins_after(data, anchor, insert, label):
    if data.count(anchor) != 1:
        raise SystemExit(f"[FAIL] {label}: anchor x{data.count(anchor)} (want 1). No write.")
    return data.replace(anchor, anchor + insert, 1)


OPT_CLASSES = _crlf('''\
class CompletionScaling(Choice):
    """Reshape Elden Ring's difficulty curve by seed-completion order rather than leave it vanilla.
    The baker re-scales every enemy from its native (geographic = completion-order) tier along the
    chosen curve. Inspired by FogMod's fog-gate-depth scaling. REQUIRES enemy_rando on.

    - off:    vanilla scaling.
    - flat:   identity (same as vanilla; confirms the pipeline ran).
    - gentle: convex -- easier for longer, difficulty concentrated late.
    - steep:  concave -- difficulty climbs fast, mid-game already punishing."""
    display_name = "Completion Scaling"
    option_off = 0
    option_flat = 1
    option_gentle = 2
    option_steep = 3
    default = 0

class CompletionScalingFloor(Range):
    """Minimum scaling tier as a PERCENT of the baker's MaxTier (0 = earliest tier can stay 1;
    25 = nothing below ~a quarter of the curve). Only with completion_scaling on."""
    display_name = "Completion Scaling Floor (% of MaxTier)"
    range_start = 0
    range_end = 50
    default = 0

''')

OPT_FIELDS = _crlf('''\
    completion_scaling: CompletionScaling
    completion_scaling_floor: CompletionScalingFloor
''')

SD_OPTS = _crlf('''\
                # Completion-percent scaling (SPEC-completion-scaling.md): mode + floor. The baker
                # reshapes each enemy's native scaling tier by this curve/floor (enemy_rando only).
                "completion_scaling": self.options.completion_scaling.value,
                "completion_scaling_floor": self.options.completion_scaling_floor.value,
''')


def patch_options(data):
    if b"completion_scaling: CompletionScaling" in data:
        print("[skip] options.py already patched.")
        return data, False
    data = _ins_before(data, b"@dataclass\r\nclass EROptions(PerGameCommonOptions):", OPT_CLASSES, "options classes")
    data = _ins_after(data, b"    region_count: RegionCount\r\n", OPT_FIELDS, "options fields")
    return data, True


def patch_init(data):
    if b'"completion_scaling": self.options.completion_scaling.value,' in data:
        print("[skip] __init__.py already patched.")
        return data, False
    data = _ins_after(data, b'                "world_logic": self.options.world_logic.value,\r\n', SD_OPTS, "slot_data options")
    return data, True


def main():
    for p in (OPTIONS, INIT):
        if not os.path.isfile(p):
            raise SystemExit(f"[FAIL] not found: {p}")
    o = _read(OPTIONS)
    o2, oc = patch_options(o)
    i = _read(INIT)
    i2, ic = patch_init(i)
    if oc:
        _write(OPTIONS, o2)
        print("[ok] patched options.py")
    if ic:
        _write(INIT, i2)
        print("[ok] patched __init__.py")
    if not (oc or ic):
        print("[done] nothing to do.")
    else:
        print("[done] completion-scaling apworld layer applied. Run patch_baker_completion_scaling.py, rebuild both, gen-test.")


if __name__ == "__main__":
    main()
