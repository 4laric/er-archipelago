# RECON — F4 tracker id-space + F3 scaling shape (Wave 1 R2, 2026-07-06)

READ-ONLY recon. All line numbers verified on disk this session.

---

## TRACKER FIX SPEC (F4)

### Ground truth: the two id spaces

- **Old apworld** (`Archipelago/worlds/eldenring/locations.py`): tracker_regions.rs carries
  **4,906 rows, ids 7,000,000..7,004,905** (measured from the generated file).
- **Greenfield** (`greenfield/eldenring/data.py` LOCATIONS): **3,958 locations,
  ids 7,770,000..7,773,957**, dense/contiguous. Base is `BASE_AP=7770000`
  (greenfield/gen_data.py:21). `location_name_to_id` is built purely from LOCATIONS tuples
  (core.py:144-146: `{name: ap_id for locs in LOCATIONS.values() for (name, ap_id, _flag) in locs}`).
  Shop checks are INSIDE this same space (shop_data.py SHOP_ROW_FLAGS: 505 ids, 7770029..7770748).
  Item id spaces for reference: locks/filler at 7780000 (core.py:134), real items at 7790000 (core.py:151).
- **Zero overlap.** Every lookup in the client's `region_table`/`coarse_table`/`big_ticket`/
  `missable` misses for every greenfield location → tracker shows nothing in-logic/grouped
  correctly. Re-pointing the generator IS sufficient — greenfield carries (or trivially derives)
  every column. No er-logic or client-code change needed; output shape stays identical.

### What gen_location_regions.py reads today (tools/gen_location_regions.py, 275 lines)

| Function | Reads | Produces |
|---|---|---|
| `load_locations()` (L107-137) | old `locations.py` via stubbed `BaseClasses` import; iterates `mod.location_tables` | `[(ap_code, fine_region, prominent, missable)]` |
| `coarse_keys()` (L55-57) | regex over `map_region_data.py` (`"name": {"area_ids"`) | set of coarse region keys |
| `region_lock_items()` (L60-65) | exec `grace_data.py` → `REGION_LOCK_ITEM` | coarse region → lock ITEM name |
| `header_buckets()` + `build_fine2coarse()` (L68-101) | `region_order` headers + `HEADER_COARSE`/`FINE_OVERRIDE` hand tables (L32-52) | fine → coarse map |
| `render_rs()` (L144-…) | above | `tracker_regions.rs` (shape below) |

Output shape (MUST NOT change — consumed at
`from-software-archipelago-clients/crates/eldenring-archipelago/src/core.rs:235-238`):
- `LOCATION_META: &[(u64 id, &str fine_region, &str coarse_region, bool big_ticket, bool missable)]` sorted by id
- `COARSE_LOCK_ITEMS: &[(&str coarse, &str lock_item)]`
- fns `location_region_table() / location_coarse_table() / big_ticket_set() / missable_set() / coarse_lock_item_table()`
- generated tests: sorted-unique ids; every non-"" coarse key has a lock item.

### How the client resolves coarse → open (why the mapping below works)

`core.rs:1087-1105 open_coarse_regions()`: coarse name → `coarse_lock_items[coarse]` = lock ITEM
name → `region.region_open_flags[lock_name]` (slot_data `regionOpenFlags`, parsed at
region.rs:120 `str_to_u32`) → live event flag. Greenfield already emits `regionOpenFlags` keyed
**`"<Region> Lock"`** (core.py:352: `{f"{r} Lock": REGION_OPEN_FLAGS[r] for r in kept}`), so the
chain closes if `COARSE_LOCK_ITEMS` maps `region → f"{region} Lock"`. `""` coarse = always open
(er-logic tracker.rs:42); a lock absent from `regionOpenFlags` (sealed / not-kept region) also
reads open (core.rs:1096-1097) — harmless because sealed regions' locations aren't in the seed's
`valid_locations`.

### Re-pointed inputs (greenfield sources — pure data modules, exec/import directly, NO AP stubs needed)

| Column | Greenfield source | Mapping |
|---|---|---|
| id | `data.py` LOCATIONS tuple field 2 (`ap_id`) | as-is |
| fine_region | LOCATIONS dict key (23 keys: HUB 'Roundtable Hold' + the 22 REGIONS) | as-is. NOTE: grouping is coarser than the old ~100 fine regions — acceptable; tracker UI just gets 23 buckets |
| coarse_region | same region name; **`""` for HUB** ('Roundtable Hold' has no lock/open flag) | fine == coarse in greenfield; the whole HEADER_COARSE/FINE_OVERRIDE/header_buckets apparatus is DELETED |
| big_ticket | `location_tags.py` LOCATION_TAGS `{ap_id: [type,...]}` | **greenfield has no `prominent` field — this is the sensible default:** big_ticket = ap_id tagged `'Boss'` or `'Remembrance'` (26+26 ids; tag census: Shop 506, Seedtree 31, Boss 26, Remembrance 26, Revered 24, Fragment 22, Basin 18, Church 13) |
| missable | `missable_locations.py` MISSABLE_LOCATIONS `{ap_id: 'dragon_heart'\|'deathroot'}` | missable = ap_id in dict keys |
| COARSE_LOCK_ITEMS | `data.py` REGIONS + core.py naming rule (core.py:135) | `[(r, f"{r} Lock") for r in REGIONS]` — do NOT read grace_data.py |

`region_open_flags.py` / `region_graces.py` are NOT needed by the generator (the client gets open
flags at runtime from slot_data `regionOpenFlags`); they only prove every one of the 22 regions has
an open flag, i.e. the generated `coarse_keys_have_lock_items` test still passes.

### Concrete change list (gen_location_regions.py)

1. Repoint path consts: `ELD` → `greenfield/eldenring`; sources = `data.py`,
   `location_tags.py`, `missable_locations.py` (+ `region_spine.py`/nothing else).
2. Replace `load_locations()` with a plain import/exec of the three pure-data modules; rows =
   `sorted((ap_id, region, ap_id in BIG, ap_id in MISS) for region, locs in LOCATIONS.items() for (_n, ap_id, _f) in locs)`
   where `BIG = {i for i,t in LOCATION_TAGS.items() if 'Boss' in t or 'Remembrance' in t}`,
   `MISS = set(MISSABLE_LOCATIONS)`.
3. Delete `coarse_keys()/header_buckets()/build_fine2coarse()/HEADER_COARSE/FINE_OVERRIDE`;
   coarse = region name, `""` for `HUB`.
4. Replace `region_lock_items()` with `{r: f"{r} Lock" for r in REGIONS}`.
5. `render_rs()`, lib.rs wiring, `--check` gate: unchanged (update the header comment's Sources line).
6. Expected regen output: 3,958 rows, 52-ish big-ticket, 22 coarse regions, 22 lock items.
   Runs anywhere (pure data modules — no Windows AP env requirement anymore).

**Verdict: re-pointing the generator is sufficient.** Only genuinely absent datum is
`prominent`/big_ticket, cleanly substituted by Boss|Remembrance tags.

### DECLARATIONS NEEDED (TRACKER)
`regionOpenFlags` — already declared (contract.py:141-143, SCALAR_INT_MAP, required, BOTH; keys
MUST be `"<Region> Lock"` strings matching COARSE_LOCK_ITEMS values — add that key-naming rule to
its doc string). No NEW slot_data key: the tracker table is compiled into the client, not shipped
in slot_data.

---

## SCALING FIX SPEC (F3)

### Exact client parse (er-logic/src/scaling.rs `parse_scaling_config`, L144-188)

```rust
pub fn parse_scaling_config(sd: &Value) -> Option<ScalingConfig> {
    if !crate::options::parse_bool_option(sd, "completion_scaling") {   // <- sd["options"]["completion_scaling"]
        return None;
    }
    let region_targets = i32_i32_map(sd.get("regionSphereTargets"));    // {"<i32>": <i32>} else skipped
    ...
    if let Some(arr) = sd.get("regionSphereTargetRanges").and_then(|v| v.as_array()) {
        for row in arr { ... if r.len() != 3 { continue; }
            if let (Some(lo), Some(hi), Some(t)) = (r[0].as_i64(), r[1].as_i64(), r[2].as_i64()) {
                region_ranges.push((lo as i32, hi as i32, t as i32));   // [[lo, hi, target], ...]
    ...
    if region_targets.is_empty() && region_ranges.is_empty() { return None; } // H4 refuse-to-arm
    let basis = match sd.get("completionScalingBasis") {                 // top-level; 1|"sphere" => Sphere
        Some(v) if v.as_str() == Some("sphere") || v.as_i64() == Some(1) => ScalingBasis::Sphere,
        _ => ScalingBasis::Geographic, };
    let floor_mult = sd.pointer("/options/completion_scaling_floor")     // <- NESTED under "options", f64
        .and_then(|v| v.as_f64()).unwrap_or(0.0) as f32;
    let floor_tier = floor_tier_from_multiplier(floor_mult);             // first tier with hp >= mult
```

Key facts:
- Gate: `options.parse_bool_option` (er-logic/src/options.rs:11-21) reads
  **`sd["options"]["completion_scaling"]`** — bool or nonzero int. NESTED under `"options"`.
- `regionSphereTargets` shape (i32_i32_map, scaling.rs L124-136): JSON object
  **`{"<i32-parseable string key>": <integer>}`**. Non-numeric keys are skipped; float values fail
  `as_i64()` and are skipped → name-keyed/float maps parse to EMPTY.
- `regionSphereTargetRanges` shape: JSON array of 3-int arrays **`[[lo, hi, target], ...]`**,
  ids in **play_region_id/100 sub-id space** (e.g. 61000 Limgrave, 10000 Stormveil, 15001 Haligtree).
  This is the blessed live path (SCALING_WIRE comment L152-154: "the flat map only ever carried
  region NAMES (unparseable)").
- Runtime resolution (eldenring-archipelago/src/scaling.rs `tick()`, L73-83):
  `let region = (player.play_region_id / 100) as i32;` then
  `speffect_id_for_tier(tier_for_region(cfg, region))` — exact-map lookup first
  (er-logic scaling.rs `tier_for_region` L93-104), then linear range scan, else floor tier.
  Targets are RELATIVE ints — normalized by `max_target` (`tier = round(target/max_target * 9)`,
  `tier_for_target` L81-90); the old apworld used `int(round(frac * 10000))`, i.e. 0..10000.
- Caller `configure()` (eldenring-archipelago/src/scaling.rs L32-53): logs
  "completion_scaling requested but regionSphereTargets is empty -- enemy scaling left VANILLA"
  when the gate is on but both tables parse empty.

### What greenfield emits TODAY

- `features/scaling.py` (43 lines) `slot_data()` returns **top-level**
  `{"completion_scaling": 4, "completion_scaling_floor": <int 0..50 percent>, "global_scadutree_blessing": <0|1|2>}` —
  merged flat by registry.merge_slot_data. Client looks for the first two under `"options"` → both invisible.
- `core.py:353-363 _base_slot_data`: `"completionScalingBasis": 1` (top-level — CORRECT) and
  `contract.REGION_SPHERE_TARGETS` = `regionSphereTargets` =
  `{region_NAME: round(i/span, 4)}` (core.py:354: name keys + FLOAT values 0..1) —
  **doubly unparseable** by `i32_i32_map` (name key fails parse; float fails as_i64) → empty.
- `regionSphereTargetRanges`: **not emitted at all** (grep: only the OLD apworld
  `Archipelago/worlds/eldenring/slot_data.py:913` emits it).
- Net today: gate false AND both tables empty → `parse_scaling_config` returns `None` → feature
  silently INERT (doesn't even hit the loud VANILLA error, because the gate itself is false).

### Exact greenfield emission needed

1. **`regionSphereTargetRanges`** (top-level, the fix): greenfield already owns the play-id map —
   `features/area_locks.py` `REGION_PLAY_IDS` (L45-68, region → play_region/100 sub-ids, same
   space as `areaLockFlags`). Emit, for kept regions in kept order:
   ```python
   span = max(len(kept) - 1, 1)
   ranges = [[pid, pid, int(round(i / span * 10000))]
             for i, r in enumerate(kept) for pid in REGION_PLAY_IDS.get(r, [])]
   sd["regionSphereTargetRanges"] = sorted(ranges)
   ```
   (lo == hi per pid, mirroring areaLockFlags; target 0..10000 mirrors the old apworld's
   `int(round(frac*10000))` — client normalizes by max, so units only need monotonicity.)
   Alternative (equally valid to the client): fix `regionSphereTargets` to
   `{str(pid): int(round(frac*10000))}` — but ranges are the blessed path; pick ONE and declare it.
2. **`options.completion_scaling`** = 1 (or true) — nested. The current top-level
   `"completion_scaling": 4` does nothing for the gate; the value 4/"smoothstep curve id" story in
   scaling.py's docstring does not match the client (client only truth-tests it; the curve is the
   fixed tier ladder + smoothstep is NOT keyed off this value).
3. **`options.completion_scaling_floor`** = HP **multiplier** (f64), NOT the 0..50 percent.
   Client maps it via `floor_tier_from_multiplier` (scaling.rs L117-123: first tier whose hp ≥
   value; above ladder → TOP tier). Sending the raw percent (e.g. 25) would floor at the TOP tier
   (25 > 3.703) — worst-case inversion. Convert: `tier = round(pct/100 * 9)`; emit
   `SCALING_HP_LADDER[tier]` (mirror the 10 hp values 1.141..3.703 from er-logic SCALING_TIERS)
   or `0.0` when pct == 0.
4. **`completionScalingBasis`: 1** — already correct, keep top-level.
5. Keep the name-keyed `regionSphereTargets` for human inspection only, or drop it; if kept,
   contract doc must say "informational, client-unparseable by design" (it already does —
   contract.py:144-146 shape ANY).
6. `global_scadutree_blessing`: no client consumer found in this recon (out of F3 scope; R1/F1
   territory) — do not declare as consumed.

### DECLARATIONS NEEDED (SCALING)
- `regionSphereTargetRanges` — top-level key, shape TRIPLE_LIST (`[[lo:int, hi:int, target:int], ...]`,
  play_region_id/100 sub-id space, target 0..10000), required when scaling on; producer
  features/scaling.py (+REGION_PLAY_IDS import), consumer `er-logic/src/scaling.rs:150 parse_scaling_config`.
- `options.completion_scaling` — nested under `options`, BOOL_OR_INT, gate; consumer
  `er-logic/src/options.rs:11 parse_bool_option` via eldenring-archipelago/src/scaling.rs:33.
- `options.completion_scaling_floor` — nested under `options`, FLOAT (HP multiplier ≥ 0, 0 = no
  floor; 1.141..3.703 = ladder span); consumer `er-logic/src/scaling.rs:180 pointer("/options/completion_scaling_floor")`.
- `completionScalingBasis` — top-level, INT (1 = sphere) or STR "sphere"; consumer
  `er-logic/src/scaling.rs:172`. Already emitted; just needs declaring.
- (contract.py currently declares ONLY `regionSphereTargets` shape ANY "informational" at
  contract.py:144 — none of the four above exist in the contract; contract_gen.rs:29 mirrors that.
  NOTE: contract needs an `options.*` nesting concept for the two nested keys — currently every
  ContractKey is a top-level name.)
