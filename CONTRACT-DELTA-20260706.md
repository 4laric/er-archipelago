# CONTRACT DELTA (frozen) — Wave 2 authoritative spec

**Date:** 2026-07-06 · Reconciled by Opus from `RECON-contract-keys-20260706.md` (R1) +
`RECON-tracker-scaling-20260706.md` (R2). This is the single source of truth for Wave 2. Key names,
nesting, and shapes below are FROZEN — agents implement to this, not to their own re-derivation.

## Reconciliation summary (41 client-read keys, 36 gf emissions)
OK 17 · WRONG-NESTING (F1) 5 · WRONG-SHAPE 1 · MISSING-with-consumer 5 · MISSING-by-design (bedrock) 10 ·
DEAD emissions 11. Full tables in the two RECON files.

## Decisions (Opus, made — implement as stated)
- **D1 — Keep legacy top-level duplicates.** Do NOT edit `deathlink.py`/`weapon_reqs.py`/etc. to
  remove their top-level emissions. I1 adds a *central* `sd["options"]` echo read from
  `world.options`. Client reads ONLY the options path for these five, so the top-level twins are
  harmless (different path → no merge collision). Cleanup deferred post-v0.1. **This keeps I1 confined
  to `contract.py`/`core.py`/`registry.py` and touches no feature file.**
- **D2 — Strict validator (F2) + declare everything currently emitted.** Make `validate_slot_data`
  reject any emitted key not declared in `contract.py`. To keep gen green, I1 must declare EVERY
  currently-emitted-but-undeclared key (lists C + D below) — as GREENFIELD-profile diag keys where
  they have no client reader. The `ci-linux.sh` fuzz gate will catch any missed declaration.
- **D3 — `required` must be profile-aware.** Bedrock-profile keys (list below) must NOT be required
  for a GREENFIELD-profile gen, or greenfield gen fails demanding Bedrock data. Validator gates
  `required` by the active profile.
- **D4 — Scaling arms via ranges.** `regionSphereTargetRanges` (I2) is the working wire.
  `regionSphereTargets` gets reshaped to `{str(i32): i32}` (emit `{}` if no point targets) so it's no
  longer unparseable; fix its stale "informational" doc.
- **D5 — auto_upgrade / flatten_regular_upgrades** have no gf feature yet → echo constant `0` (off)
  in the options dict so the client reads a defined value. Declared, producer = core echo.

---

## I1 — SPINE (owns `contract.py`, `core.py`, `registry.py` exclusively)

### 1. Add nested-key support to contract.py
Every `ContractKey` is top-level today. Add an `options` sub-dict concept: one top-level key
`options` (shape = OPTIONS_DICT, a new checker validating each declared sub-key's shape). Sub-keys are
declared with their own name/shape/producer/consumer.

### 2. Declare + centrally emit the options echo (fixes F1 — all 8 at once)
Top-level key `options` (dict). In `core.py` build it from `world.options`. Sub-keys:

| sub-key | shape | value |
|---|---|---|
| `death_link` | bool/int | `world.options.death_link.value` |
| `enable_dlc` | bool/int | RESOLVED dlc bool (core.py:190-191 semantics; dlc_only implies on) |
| `no_weapon_requirements` | bool/int | option value |
| `completion_scaling` | bool/int | option value (nonzero = on; current `4` is fine as truthy) |
| `completion_scaling_floor` | number | option value (client reads as f64) |
| `global_scadutree_blessing` | int | option value |
| `auto_upgrade` | int | constant `0` (D5) |
| `flatten_regular_upgrades` | int | constant `0` (D5) |

### 3. Declare scaling keys (produced by I2 — declare here, don't emit here)
- `regionSphereTargetRanges` — TOP, shape `[[lo:int, hi:int, target:int], ...]`, required=False,
  producer=features/scaling.py, consumer=er-logic/scaling.rs:150.
- `regionSphereTargets` — TOP, reshape declaration to `{str(i32): i32}` (was ANY "informational"); fix
  doc (client DOES parse it, scaling.rs:148).
- `completionScalingBasis` — TOP, int(1)|"sphere"; already emitted (core.py:362), just declare.

### 4. Declare the tracker key note (produced by nothing new — I3 output is compiled, not slot_data)
- `regionOpenFlags` — already declared (contract.py:141-143). Add key-naming rule to its doc: keys
  MUST be `"<Region> Lock"` strings matching COARSE_LOCK_ITEMS (I3 relies on this).

### 5. Declare currently-emitted-but-undeclared keys (D2 — so strict-emit stays green)
- With live client consumer: `sweepLockGates` (`{str(i64):str}`, flagpoll.rs:119),
  `versions` (str semver; emission optional for now), plus confirm `lockRevealFlags` (contract.py:151
  producer "(future)" but region.rs:121 is live — mark live).
- Bedrock-profile, no gf producer (declare profile=BEDROCK, required only under BEDROCK — D3):
  `locationIdsToKeys`, `itemCounts`, `naturalKeyTriggers`, `lockGrantItems`,
  `randomStartDoneFlag`, `randomStartWarpFlag`, `randomStartAreaId`, `randomStartGraceId`,
  `fogWalls`, `fogWallDebug`.
- GREENFIELD diag keys, no client read (declare shape ANY, doc "diagnostic — no client read"):
  `region_count`, `ending_condition`, `great_runes_required`, `great_rune_items`, `bossLocations`,
  `filler_foreign_localized`, `pool_builder`, `pool_builder_juice_added`,
  `pool_builder_intensity_floor`, `pool_builder_juice_candidates`, `world_logic`.
- Producer-string fixes: `enable_dlc` (contract.py:201 → now true via echo), `dungeonSweeps`
  (contract.py:217 tagged bedrock but boss_locks.py:66 emits empty — retag GREENFIELD or stop emitting).

### 6. Regenerate the client mirror
After contract.py changes, run `gen_contract.py` so `contract_gen.rs` + CONTRACT.md + contract.json
regenerate. (Do NOT cargo-build — that's Alaric.)

### Validate: `bash greenfield/ci-linux.sh` stays GREEN (all gates, esp. fuzz).

---

## I2 — SCALING (owns `features/scaling.py` + a spec md; declarations done by I1)
Emit top-level `regionSphereTargetRanges = [[lo, hi, target], ...]` (i32 triples, play_region_id/100
sub-id space, target 0..10000, normalized by max) using `REGION_PLAY_IDS` (already in
`features/area_locks.py`). Reshape/emit `regionSphereTargets` as `{str(i32): i32}` (or `{}`). Do NOT
touch contract.py — I1 declares your keys. Client parse is `er-logic/scaling.rs:144-188`
`parse_scaling_config` (gate = `sd["options"]["completion_scaling"]`, floor =
`sd["options"]["completion_scaling_floor"]` as HP multiplier ≥ 0). Write
`SPEC-client-scaling-20260706.md` confirming no `scaling.rs` change is needed (greenfield now matches).
Validate greenfield-side with `ci-linux.sh`; confirm the key is present in a generated seed's slot_data.

---

## I3 — TRACKER (owns `tools/gen_location_regions.py` + regenerated `tracker_regions.rs`)
Re-point `tools/gen_location_regions.py` from the OLD apworld
(`Archipelago/worlds/eldenring/{locations,map_region_data,grace_data}.py`, ids 7,000,000+) to
GREENFIELD data (`greenfield/eldenring/data.py` LOCATIONS, ids 7,770,000–7,773,957 +
`region_open_flags.py` + `region_graces.py`). Column mapping (from R2): fine=coarse=region name (23
buckets, `""` for Roundtable Hold); coarse-lock item = `{region: f"{region} Lock"}`; missable =
MISSABLE_LOCATIONS keys; big_ticket default = LOCATION_TAGS Boss ∪ Remembrance (~52 ids). Output
`.rs` shape UNCHANGED. The generator should become AP-env-free. Regenerate `tracker_regions.rs` but
**do NOT cargo-build** — leave it for Alaric. Write `SPEC-client-tracker-20260706.md` listing exactly
what Alaric must `cargo build`/`test` to confirm.

---

## Handoff to Alaric (client cargo, after Opus merges Wave 2)
`cargo build`/`test` the regenerated `tracker_regions.rs` + `contract_gen.rs`; live greenfield connect
should now log real regions and fire death_link / scaling / weapon_reqs / DLC map-reveal.
