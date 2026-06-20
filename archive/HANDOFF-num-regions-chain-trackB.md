# HANDOFF — Track B: Apworld sphere emission

Spec: SPEC-num-regions-chain.md (contract §4 is frozen). Track owner edits ONLY this file + the patches below.
Deliverables: apply `patch_apworld_completion_scaling.py` THEN `patch_apworld_sphere_scaling.py` (both already exist, NOT yet in deployed source); extend only if needed.

## Scope (files this track may touch)
- `Archipelago/worlds/eldenring/__init__.py` — `fill_slot_data` only (~L4540, before `slot_data = {`, and the key after `reveal_all_maps`).
- `Archipelago/worlds/eldenring/options.py` — scaling option fields (if not already applied).
DO NOT touch the num_regions block / warp helper (Track A) or any `.cs` (Track C).

## Steps
- [ ] Apply `patch_apworld_completion_scaling.py` (emits `completion_scaling` + `completion_scaling_floor` under options). NOTE its header says "requires enemy_rando ON" — confirm the EMISSION is NOT gated on enemy_rando; these runs are enemy-OFF and the keys must still emit.
- [ ] Apply `patch_apworld_sphere_scaling.py` (emits `completionScalingBasis` + `regionSphereTargets`, writes `ER_SPHERE_TIERS.txt`).
- [ ] If either gates emission on `enemy_rando`, patch it to emit regardless (baker scale-only path consumes it with enemy-OFF).

## Contract owned (§4)
`completion_scaling`, `completion_scaling_floor` (under options); `completionScalingBasis`, `regionSphereTargets` (top level). Schema is FROZEN — Track C consumes verbatim.

## Verify
After A+B applied: gen with `completion_scaling: gentle` + `completion_scaling_basis: sphere`; `ER_SPHERE_TIERS.txt` shows a 1..N gradient; slot_data carries `completionScalingBasis: 1` + non-empty `regionSphereTargets`.

## Status / notes — RESOLVED 2026-06-19 (Track B dry-run complete)

### Apply order (Windows, run by Alaric from repo root)
1. `python patch_apworld_completion_scaling.py`
2. `python patch_apworld_sphere_scaling.py`
(No third patch — see gating finding.) Anchors are unique and disjoint from Track A's num_regions block; order within B is the above for clarity. After A+B+C: `.\build.ps1 -Randomizer -Generate`.

### Current deployed state (verified on disk)
- `options.py` is ALREADY fully patched: `CompletionScaling`, `CompletionScalingFloor`, `CompletionScalingBasis` classes present (L870-905) and all three fields registered on `EROptions` (`completion_scaling` / `completion_scaling_floor` / `completion_scaling_basis`, L922-924). Both patches' `patch_options()` therefore hit their idempotency `[skip]` — no options.py write on re-run.
- `__init__.py` `fill_slot_data` (`slot_data = {` ~L4540) does NOT yet emit any of the four keys. Both patches' `patch_init()` splice cleanly into it.

### Dry-run result (copies in /tmp/trackB, never touched real source)
- Both patches APPLY cleanly in order: `[skip] options.py` + `[ok] patched __init__.py` for each.
- IDEMPOTENT: second run = `[skip]` / `[done] nothing to do.` for both.
- CRLF PRESERVED: patched `__init__.py` keeps all 4565→4611 CRLF lines, adds 0 new lone-LF (the 94 pre-existing lone-LFs are inside vanilla string literals, present in the UNPATCHED original too — not introduced by these patches).
- Inserted `CS_BLOCK` (sphere compute, before `slot_data = {`) parses as valid standalone Python (indentation + braces balanced). `options.py` compiles.
- NOTE: a full `py_compile` of `__init__.py` could NOT be run in the sandbox — the Linux mount silently TRUNCATES the read of this 306 KB file at ~306324 bytes (stops mid-comment ~L4659), so both the patched copy and the UNPATCHED original "fail" `py_compile` identically with a spurious `'{' was never closed`. This is the known mount-truncation hazard, NOT a patch defect: the real file on Windows (verified via editor read) closes `slot_data` at L4667, `return slot_data` L4669, `interpret_slot_data` L4672. Alaric must run the actual `py_compile` / gen on Windows.

### GATING FINDING — emission is NOT gated on enemy_rando. No follow-up patch written.
- `completion_scaling` / `completion_scaling_floor` are spliced UNCONDITIONALLY into the `"options": {...}` dict (via `_ins_after` the `"world_logic"` line). Value = `self.options.completion_scaling.value` regardless of enemy_rando.
- `completionScalingBasis` / `regionSphereTargets` are spliced UNCONDITIONALLY into the top-level dict (via `_ins_after` the `"reveal_all_maps"` line). `region_sphere_targets` defaults `{}`, so the key is ALWAYS present.
- The "Requires enemy_rando ON" header note in `patch_apworld_completion_scaling.py` refers to the BAKER's reshape pass, not apworld emission. The only `enemy_rando` tokens in `fill_slot_data` are a descriptive comment and the unrelated pre-existing `"enemy_rando"` slot_data key — neither wraps the four contract keys.
- Therefore the four keys emit with `enemy_rando` OFF, and Track C's scale-only path receives them. `patch_apworld_scaling_emit_ungate.py` is NOT needed and was NOT created.

### Sphere computation confirmed (§4 mechanics)
- `regionSphereTargets` is computed from `list(self.multiworld.get_spheres())` POST-fill (inside `fill_slot_data`), so it becomes a real 1..N gradient once Track A forces the chain. Until A lands, targets are ~flat — expected, not a bug.
- The compute is gated on `completion_scaling.value AND completion_scaling_basis.value == 1` (i.e. `completion_scaling_basis: sphere` triggers it); otherwise `region_sphere_targets` stays `{}` and `get_spheres()` (heavy) is skipped. Per region: `region_sphere` = earliest AP sphere among that region's own-player locations; `target = floor + curve(sphere/maxSphere)*(1-floor)`, rounded 4dp. Writes `Archipelago/worlds/eldenring/ER_SPHERE_TIERS.txt` (region\tsphere\ttarget, sorted).

### Confirmed emitted slot_data schema (matches §4 VERBATIM)
- `slot_data["options"]["completion_scaling"]` : int (0 off / 1 flat / 2 gentle / 3 steep)
- `slot_data["options"]["completion_scaling_floor"]` : int (0..50, % of MaxTier)
- `slot_data["completionScalingBasis"]` (top level) : int (0 geographic / 1 sphere)
- `slot_data["regionSphereTargets"]` (top level) : `{ "<AP region name>": float }`, [0.0,1.0], 4dp (empty `{}` unless completion_scaling>0 AND basis==sphere)

Key names + locations are IDENTICAL to the frozen §4 contract; nothing renamed. Track C consumes verbatim.
