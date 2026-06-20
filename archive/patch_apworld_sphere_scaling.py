#!/usr/bin/env python3
"""
patch_apworld_sphere_scaling.py -- apworld INSPECTION slice of sphere-ordered completion scaling
(SPEC-sphere-ordered-scaling.md). v2 of completion scaling: tier by AP fill SPHERE, not geography,
so a random start region = sphere 1 = tier 1 (start-relative). THIS slice only computes + emits the
per-region target table + a readable diag; the baker enemy->region bridge that APPLIES it is a follow-up.

options.py:
  + CompletionScalingBasis (geographic [default, = current v1] / sphere)
__init__.py / fill_slot_data (post-fill -> get_spheres available):
  + when completion_scaling on AND basis=sphere: region_sphere = earliest AP sphere among a region's
    locations; target = floor + curve(sphere/maxSphere)*(1-floor) (same flat/gentle/steep curve).
    Emits "completionScalingBasis" + "regionSphereTargets" {region: frac}; writes ER_SPHERE_TIERS.txt
    (region\tsphere\ttarget, sorted by sphere) next to the apworld for eyeballing. Inert otherwise.

NEXT (not here): baker builds MSB-map -> region from location placements and reshapes each enemy by
regionSphereTargets[region] (TODO #22 / SPEC). Until then sphere basis emits the table but the baker
still applies the v1 geographic reshape.

Run on Windows. Idempotent. Binary I/O preserves CRLF. get_spheres is heavy -> gated on basis=sphere.
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


def _ins_before(data, anchor, ins, label):
    if data.count(anchor) != 1:
        raise SystemExit(f"[FAIL] {label}: anchor x{data.count(anchor)} (want 1). No write.")
    return data.replace(anchor, ins + anchor, 1)


def _ins_after(data, anchor, ins, label):
    if data.count(anchor) != 1:
        raise SystemExit(f"[FAIL] {label}: anchor x{data.count(anchor)} (want 1). No write.")
    return data.replace(anchor, anchor + ins, 1)


OPT_CLASS = _crlf('''\
class CompletionScalingBasis(Choice):
    """How completion_scaling orders the tiers.
    - geographic: by each enemy's native (vanilla) area tier. Start-UNAWARE -- a random start still
      fights softened-but-mid-game enemies. Cheap; the v1 default.
    - sphere: by each REGION's Archipelago fill SPHERE, so your rolled start region is sphere 1
      (tier 1) and difficulty climbs with YOUR progression, not geography. Needs the baker bridge
      (SPEC-sphere-ordered-scaling.md) to actually apply; the apworld emits the table + ER_SPHERE_TIERS.txt
      either way for inspection."""
    display_name = "Completion Scaling Basis"
    option_geographic = 0
    option_sphere = 1
    default = 0

''')

OPT_FIELD = _crlf('    completion_scaling_basis: CompletionScalingBasis\n')

CS_BLOCK = _crlf('''\
        # Sphere-ordered completion scaling (SPEC-sphere-ordered-scaling.md): when basis=sphere, tier
        # each REGION by its AP fill sphere so the rolled start region = sphere 1 = tier 1
        # (start-relative). Emits regionSphereTargets {region: frac} + ER_SPHERE_TIERS.txt for
        # inspection. get_spheres is heavy -> computed only on demand. Baker bridge that APPLIES this
        # is a follow-up (TODO #22); for now it's the inspectable table.
        region_sphere_targets = {}
        if self.options.completion_scaling.value and self.options.completion_scaling_basis.value == 1:
            import os as _csos
            _cs_mode = self.options.completion_scaling.value
            _cs_floor = self.options.completion_scaling_floor.value / 100.0
            def _cs_curve(d):
                if _cs_mode == 2:
                    return d ** 1.6
                if _cs_mode == 3:
                    return d ** 0.55
                return d
            _region_sphere = {}
            _spheres = list(self.multiworld.get_spheres())
            _sealed = getattr(self, "_spine_sealed_regions", set())
            for _si, _sphere in enumerate(_spheres):
                for _loc in _sphere:
                    if getattr(_loc, "player", None) != self.player:
                        continue
                    _rn = _loc.parent_region.name if getattr(_loc, "parent_region", None) else None
                    if _rn and _rn not in _sealed and _rn not in _region_sphere:
                        _region_sphere[_rn] = _si
            _maxsph = max(1, max(_region_sphere.values(), default=1))
            for _rn, _sph in _region_sphere.items():
                _d = _sph / _maxsph
                region_sphere_targets[_rn] = round(_cs_floor + _cs_curve(_d) * (1.0 - _cs_floor), 4)
            try:
                _lines = ["region\\tsphere\\ttarget"]
                for _rn in sorted(_region_sphere, key=lambda r: (_region_sphere[r], r)):
                    _lines.append(f"{_rn}\\t{_region_sphere[_rn]}\\t{region_sphere_targets[_rn]}")
                with open(_csos.path.join(_csos.path.dirname(__file__), "ER_SPHERE_TIERS.txt"), "w") as _df:
                    _df.write("\\n".join(_lines))
            except Exception:
                pass
''')

SD_KEYS = _crlf('''\
            # Sphere-ordered completion scaling (SPEC-sphere-ordered-scaling.md): basis + per-region
            # AP-sphere target table. {} / geographic unless completion_scaling on with basis=sphere.
            # The baker bridge that consumes regionSphereTargets is a follow-up (TODO #22).
            "completionScalingBasis": self.options.completion_scaling_basis.value,
            "regionSphereTargets": region_sphere_targets,
''')


def patch_options(data):
    if b"completion_scaling_basis: CompletionScalingBasis" in data:
        print("[skip] options.py already patched.")
        return data, False
    data = _ins_before(data, b"@dataclass\r\nclass EROptions(PerGameCommonOptions):", OPT_CLASS, "options class")
    data = _ins_after(data, b"    completion_scaling_floor: CompletionScalingFloor\r\n", OPT_FIELD, "options field")
    return data, True


def patch_init(data):
    if b"regionSphereTargets" in data:
        print("[skip] __init__.py already patched.")
        return data, False
    data = _ins_before(data, b"        slot_data = {\r\n", CS_BLOCK, "fill_slot_data compute block")
    data = _ins_after(data, b'            "reveal_all_maps": self.options.map_option.value == 1,\r\n', SD_KEYS, "slot_data keys")
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
        print("[ok] patched options.py (+ CompletionScalingBasis)")
    if ic:
        _write(INIT, i2)
        print("[ok] patched __init__.py (sphere targets + ER_SPHERE_TIERS.txt)")
    if not (oc or ic):
        print("[done] nothing to do.")
    else:
        print("[done] sphere-scaling inspection slice applied. Rebuild apworld; gen a random-start seed "
              "with completion_scaling: gentle + completion_scaling_basis: sphere, then read "
              "Archipelago/worlds/eldenring/ER_SPHERE_TIERS.txt (region -> sphere -> target).")


if __name__ == "__main__":
    main()
