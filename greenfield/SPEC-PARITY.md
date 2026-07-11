# Greenfield ER — feature-parity spec (matt-free)

**Goal:** bring the greenfield world up to par with the existing `worlds/eldenring` apworld —
num_regions, scaling, boss locks, shops, pool curation, grace rando, and the full option surface —
**without inheriting the Bedrock/matt foundation.** The MVP (Shattering: hub-and-spoke region locks,
generic filler, `locationFlags`) already gens and is winnable. This spec is the additive roadmap
from there.

Read `LESSONS-LEARNED.md` first — it is the design contract this spec obeys. The one-line version:
**every rule keys off REGION (or the world's own data columns), never off an imported location name.**

---

## 0. Non-negotiables (provenance + architecture)

These are hard constraints. A feature that violates one is not "at par" — it is a re-introduction
of the thing greenfield exists to escape.

**P1 — No Bedrock/matt data or code is copied.** Concretely, greenfield must NOT emit or depend on:
`locationIdsToKeys`, `locationIdsToTargets`, any matt key-string token, the original apworld's
location-NAME set, or its name-keyed rule modules. The client already supports a keyless path
(`locationFlags` = {ap_id: [event flag]}); greenfield rides that and only that.

**P2 — Every feature is re-derived from greenfield's OWN substrate.** The backbone
(`region_map.csv`, 5,163 rows) carries enough to rebuild each feature from scratch:

| column | what it is | features it powers |
|--------|-----------|--------------------|
| `flag` | vanilla event flag (the check's acquisition flag) | `locationFlags`, grace bundles, shop stock, boss/sweep detection |
| `map` | MSB map id (e.g. `m10_01_00_00` Stormveil, `m30_…` catacombs) | dungeon identity for boss locks/sweeps, area-code scaling |
| `method` | `treasure` / `emevd` / `boss_arena` / `shop_merchant` / `shop_multi` / `cookbook` / `global*` / `flag_prefix` / `synthetic_areacode` | shop detection, boss triggers, filler classification |
| `item_name` | vanilla item at that flag | pool builder ranking, progressive items, filler/junk tags, capped uniques |
| `region` | fine-grained region (271 distinct) | collapsed to the 22 majors in `gen_data.py` |

The rule of thumb: wherever the existing apworld does `location_dictionary[name]` or matches a matt
key, greenfield does the equivalent lookup on `map` / `method` / `flag` / `item_name`. Those columns
come from vanilla params (`ItemLotParam`, `ShopLineupParam`), MSB, and EMEVD — game data, not Bedrock.

**P3 — Alaric's own feature logic is portable, but must be re-keyed.** The spine model, the
smoothstep scaling curve, the sweep-gate boss-lock design, the pool-builder ladder, grace bundling —
that's your authorship and it moves over. What does NOT move is the *coupling*: each ported module
must be reworked to consume region/map-id keys instead of location names. Porting = re-key, not copy.

**P4 — The client contract stays stable.** Greenfield emits the same slot_data KEY NAMES the client
already reads (so no client fork is needed for parity), minus the two Bedrock-tainted keys in P1.
Section 8 is the authoritative greenfield key list.

**P5 — CI gates every phase.** The `-Greenfield` / `-OnlyGreenfield` gate (data drift + pure unit +
isolated gen + AP `WorldTestBase`) already exists. Each phase below ships with the tests that promote
its manifest row in `eldenring/tests/README.md` from "deferred" to "ported."

---

## 1. Current baseline (what ships today)

- `eldenring/__init__.py` — hub-and-spoke: `Menu → Roundtable Hold (free) → each of 22 regions`,
  entrance gated by `state.has("<Region> Lock")`. Goal = `has_all(all locks)`. Pool = 22 progression
  locks + `Rune` filler. `fill_slot_data` emits `world_logic` + `locationFlags` only.
- `eldenring/data.py` — GENERATED (`HUB`, `REGIONS`, `LOCATIONS{region:[(name,ap_id,flag)]}`),
  3,944 placeable checks, ap-ids contiguous from 7,770,000.
- `gen_data.py` — regenerates `data.py` from `region_map.csv` + grace anchors; collapses the 271 fine
  regions to 22 majors via `PLAY2AP` / `REGION_MAP`.
- `GFOptions(PerGameCommonOptions)` — **empty**. This is the biggest gap: no option surface yet.

**Prerequisite that blocks everything else: the boot contract (Phase 0).** Until received-item grants
work, no feature that grants an item on receipt (locks, medallions, graces, filler) actually does
anything in-game.

---

## 2. Phasing overview

| phase | feature(s) | unlocks | depends on |
|-------|-----------|---------|-----------|
| 0 | Boot contract: `apIdsToItemIds` + `regionOpenFlags` + real filler item | in-game boot; region-open on lock receipt | — |
| 1 | Options surface skeleton + `num_regions` spine (marquee) | region sealing / capital goal | 0 |
| 2 | Completion scaling + Scadutree blessing | difficulty curve | 1 |
| 3 | Boss locks / dungeon sweeps | sweep-gated bosses | 0 (1 for region scope) |
| 4 | Shops as checks + merchant bells | shop checks, bell logic | 0 |
| 5 | Pool builder / curated fill / filler strategies / capped uniques | item-pool quality | 0 |
| 6 | Grace rando | per-region grace bundles | 0, 1 |
| 7 | Key gates / exclusions / local items / progressive items / deathlink / start options | long tail | 0 |

Phases 2–7 are largely independent once 0 and the options skeleton (1) land; they can be built in any
order. `num_regions` (1) is prioritized because it is the marquee mode.

---

## 3. Phase 0 — Boot contract (the unblocker)

The MVP gens but doesn't fully boot: filler is a synthetic `Rune` with no game item id, and locks
grant nothing on receipt. Fix both.

**0a. Real filler item + `apIdsToItemIds`.** Every AP item id must map to a real game item id so the
client can grant it. Add `apIdsToItemIds = {ap_item_id: game_item_id}` to slot_data.
- Filler: pick a concrete vanilla item id for `Rune` (a Rune Arc / small runes item — from vanilla
  `EquipParamGoods`, matt-free). Later phases replace generic filler with pool-builder output.
- Locks are SYNTHETIC (grant = set a region-open flag, not a game item) — they get an entry in
  `regionOpenFlags`, NOT `apIdsToItemIds`.

**0b. `regionOpenFlags` = {"<Region> Lock": [open_flag]}.** On lock receipt the client flips the
region open. Greenfield must supply an open flag per region **derived from its own data, not matt's.**
Source of truth: reuse the vanilla grace/BonfireWarp warp-unlock flags already in
`elden_ring_artifacts/grace_flags.tsv` (the same anchors `gen_data.py` uses). Pick one canonical
open/warp flag per major region (the region's "front-door" grace) and emit it. Document the chosen
flag per region in a generated `region_open_flags.py` (like `data.py`, regenerated by `gen_data.py`).

**Keying:** region. **slot_data:** `apIdsToItemIds`, `itemCounts`, `regionOpenFlags`.
**Provenance:** filler id from vanilla params; open flags from vanilla grace anchors. No Bedrock.
**Tests (promote `WorldTestBase`):** every REGION has a `regionOpenFlags` entry; every non-lock AP id
has an `apIdsToItemIds` entry; open-flag set is unique and within a valid vanilla flag band.
**In-game proof:** connect a fresh seed, receive a lock, confirm the region opens and filler grants.

---

## 4. Phase 1 — num_regions (marquee) + options skeleton

`num_regions` is "the thing that turns ER into an Archipelago game." Port your spine model onto the
clean base.

**1a. Options skeleton.** Replace empty `GFOptions` with a real dataclass. Start with the options this
and later phases need; grow it per phase (Section 7 is the full target list). Minimum for Phase 1:
`EndingCondition`, `WorldLogic`, `NumRegions`, `NumRegionsOrder` (rolled|spine),
`GreatRunesRequired`. Every option needs a description (the existing apworld has an
`options-descriptions` CI gate — greenfield gets the same, see Section 9).

**1b. The spine, re-keyed to greenfield regions.** The existing `region_spine.py` SPINE is 12 ordered
steps over regions — that's your design and it ports. Re-express each step over greenfield's OWN 22
region names (Section 1), NOT the imported set. `compute_region_scope(num_regions, order)` returns
`{kept_regions, sealed_regions, effective_count}`:
- **rolled:** random N majors from the overworld set.
- **spine:** first-N steps of the fixed SPINE path.
- Always-kept: `Roundtable Hold` (hub) + the goal region (Leyndell for capital ending).
- **Sealed region → its checks become events** (locked-vanilla, removed from the fill pool) and its
  lock is removed from the item pool. This is a pure region-set operation — no location names.

**1c. Sphere targets for the client.** Emit `region_count`, `completionScalingBasis` (=1 sphere),
`regionSphereTargets` {region→tier 0..1}, `regionSphereTargetRanges` [[area_lo, area_hi, tier*1e4]].
Area ranges come from greenfield's `map`/area codes, not matt addresses.

**Keying:** region. **slot_data:** `region_count`, `regionSphereTargets`, `regionSphereTargetRanges`,
`completionScalingBasis`. **Tests:** sealed-region checks are events not locations; kept-count ==
effective_count; goal reachable at every `num_regions` in 0..N (fixed-seed diversity gate, mirroring
`run_region_diversity.ps1`). **Watch:** `num_regions` is the 100%-green marquee gate — its bugs
outrank equal-severity bugs elsewhere.

---

## 5. Phase 2 — Scaling (completion scaling + Scadutree)

Completion scaling is hardcoded-on in the existing apworld (smoothstep over sphere). Port the curve
verbatim (it's math, not matt data).

- Curve: `d = sphere / max_sphere; tier = floor + (d*d*(3-2*d)) * (1 - floor)`.
- Options: `CompletionScalingFloor` (0–50%), `GlobalScadutreeBlessing` (off|player_only|scaled).
- **slot_data:** `completion_scaling` (=4 smoothstep), `completion_scaling_floor`,
  `global_scadutree_blessing`, plus the `regionSphereTargets` from Phase 1.

**Keying:** region (sphere is per region). **Provenance:** curve + option logic are yours; sphere
index is AP-fill-derived. No Bedrock. **Tests:** floor clamps tier; monotonic tier over sphere;
Scadutree levels map correctly.

---

## 6. Phase 3 — Boss locks / dungeon sweeps

The existing design is the **sweep-gate model** (no fog gates): a dungeon's non-trigger checks are
"swept" (granted) when its trigger boss is killed, and an optional boss-lock item gates the sweep.
This is your design. The only thing that changes is how a "dungeon" and its "trigger" are identified —
greenfield derives them from `map` + `method`, not matt location names.

**3a. Dungeon grouping (matt-free).** Group locations by `map` (MSB id) — every `m30_*` catacomb,
`m31_*` cave, `m32_*` grave, `m10_01` Stormveil, etc. is a natural dungeon. `method` refines it:
`boss_arena` (25 rows) and `emevd` boss flags mark the trigger; `treasure` rows are sweep members.

**3b. Trigger selection.** Within a dungeon group, the trigger is the `boss_arena`/prominent-boss row
(fall back to the highest-flag emevd row if none). Build
`dungeonSweeps = {str(trigger_apLocId): [member_apLocIds]}` and, when boss locks are on,
`sweepLockGates = {str(trigger_apLocId): "<lock item> "}`.

**3c. Options.** `DungeonSweep` (none|minidungeons|all|bosses), `BossLockPlacement`
(scatter|own_region|any_boss). Boss-lock items are region-scoped (host on a non-trigger boss in the
sweep-group region for legibility).

**Keying:** location trigger + region scope (unavoidable — a sweep is inherently per-dungeon). But the
trigger is identified by `map`/`method`, never by an imported name. **slot_data:** `dungeonSweeps`,
`sweepLockGates`, optional `chokepoint_sweeps`. **Tests:** every trigger is a real boss row; members
disjoint across dungeons; sweep-group region matches the region set; a lost boss-lock never softlocks
a grace-only start (reconcile against `region_graces`, per the known bundle-lock gap).

---

## 7. Phase 4 — Shops + merchant bells

**4a. Shops as checks.** `method ∈ {shop_merchant, shop_multi, cookbook, shop_reference}` (567 rows)
are the shops. The client detects a shop purchase via the row's `ShopLineupParam.eventFlag_forStock`.
Greenfield already has this vanilla mapping (`shoplineup_flags.json`, derived from ShopLineupParam —
game data, matt-free). Emit `shopRowFlags = {str(shop_row_id): eventFlag_forStock}` and
`shopPreviewGoods = {str(apLocId): vanilla_good_id}` for goods-slot scouting.
**Provenance check:** confirm the shop-row → flag table is regenerated from vanilla ShopLineupParam,
NOT copied from the existing apworld's `shop_row_flags.json` if that file embeds matt addresses. If in
doubt, regenerate it in the matt-free pipeline.

**4b. Merchant bells.** 11 base + 1 DLC bell-bearing merchants gate their shop stock. Existing code
matches bells to shops by location-name substring — greenfield instead maps each bell to the
merchant's shop rows by `map`/merchant id. Option `MerchantBellLogic` (off|logic_only): when on,
that merchant's shop checks require the bell (promoted to progression).

**Keying:** location (a shop slot is a check) but identified by shop-row id, not name.
**slot_data:** `shopRowFlags`, `shopPreviewGoods`. **Tests:** every shop row maps to a valid vanilla
flag; bell-gated shops require the bell in logic; shops are always checks (no legibility regression).

---

## 8. Phase 5 — Pool builder / curated fill / filler / capped uniques

All item-pool composition; no location coupling. Port your ladder and routing; source item identity
from `item_name` (already in the backbone) ranked against vanilla `EquipParam*` tiers.

- `PoolBuilder` (+`PoolBuilderIntensity` normal|high|max): scrub C/D/F gear + dupes + junk, swap in
  ranked S-tier juice. Location count preserved; only items change.
- `CuratedFill`: mark big-ticket locations AP-priority (soft; no hard exclude → no FillError).
- `FillerUpgradePct`, `FillerForeignPct`, `FillerReplacement`, `JunkRetention`(+`Style`): filler mix.
- `CappedUniques`: slot-expanding uniques must not exceed their vanilla game cap in the pool.

**Keying:** item (by `item_name`/game id). **slot_data:** none directly (composition flows through
`apIdsToItemIds`/`itemCounts`). **Tests:** capped uniques never exceed cap; pool_builder is
count-neutral; grace/filler don't leak into progression; curated_fill keeps headroom (no FillError).

---

## 9. Phase 6 — Grace rando

Per-region grace bundling; region-keyed, so a clean port.
- Data: `REGION_GRACE_POINTS` = {region: [grace flags]} — re-derive from `grace_flags.tsv` grouped by
  the same major-region collapse `gen_data.py` uses (matt-free anchors).
- `GraceRando` (default on under region gating): receiving a lock lights ONE random grace (the warp-in
  freebie); the region's other graces become in-region item drops (count-neutral). Off = light all.
- **slot_data:** `regionGraces` {lock→[flags to light]}, `graceItems` {region→[flags placed as drops]},
  `startGraces` [flags lit at load].

**Keying:** region. **Tests:** every lock has a freebie grace; placed graces stay in-region; a
region-lock start always lights ≥1 cave/overworld grace (the known cave-start-no-graces class).

---

## 10. Phase 7 — Long tail

Independent, mostly item- or option-level; batch as capacity allows.

- **Key gates / important_locations / exclusions / missables:** `important_locations` tags
  (Remembrance, Boss, Church, Fragment, …) derive from `method` + `item_name` + `map`, not names.
  `exclude_locations` (dlc|hidden|blizzard), `excluded_location_behavior`,
  `missable_location_behavior`.
- **Local items:** `LocalItemOnly` + `ExcludeLocalItemOnly` (Weapon/Armor/Accessory/AshofWar) —
  item-classification level, no location coupling.
- **Progressive items:** `ProgressiveItems` (stone_bells|glovewort_bells|flasks|physick) + counts →
  `progressiveGrants`.
- **Deathlink:** AP-common option → `options["death_link"]`; reserve the client's dedicated
  kill/deathlink flags (never assign them as region open flags).
- **Start options:** `RandomStartRegion`, `TorrentStart`, `RandomizeStartingLoadout`, `StartItems`,
  `EarlyLeveling` → `startRegion`/`startItems`/`startGraces`/torrent handoff flags. (Note the known
  region-lock-start torrent + cave-start grace bugs — bake their fixes in here.)
- **DLC:** `EnableDLC`, `DLCOnly`, `DLCTimingOption`, Scadutree frontload, Messmer kindle. Greenfield
  already buckets DLC into coarse regions (Land of Shadow, Shadow Keep, …); DLC rides as plain lock
  gates (no separate spine).

---

## 11. Options surface (target)

`GFOptions` grows from empty to ~40 options across phases. Group and land them with their phase:

- **Goal/logic (P1):** EndingCondition, WorldLogic, RegionSoftLogic, RegionAccessLogic, ExtraRegionLocks.
- **num_regions (P1):** NumRegions, NumRegionsOrder, GracesPerRegion, GreatRunesRequired,
  GreatRunesFinalBoss, GreatRunesMountaintops.
- **Scaling (P2):** CompletionScalingFloor, GlobalScadutreeBlessing.
- **Boss locks (P3):** DungeonSweep, BossLockPlacement.
- **Shops (P4):** MerchantBellLogic.
- **Pool (P5):** LocationPool, PoolBuilder, PoolBuilderIntensity, CuratedFill, FillerUpgradePct,
  FillerForeignPct, FillerReplacement, JunkRetention, JunkRetentionStyle, DLCGearCuration,
  NoSpiritAshes, CappedUniques.
- **Grace (P6):** GraceRando.
- **Long tail (P7):** important_locations, exclude_locations + behaviors, LocalItemOnly +
  ExcludeLocalItemOnly, ProgressiveItems + counts, DeathLink, RandomStartRegion, TorrentStart,
  RandomizeStartingLoadout, EarlyLeveling, EnableDLC, DLCOnly, DLCTimingOption, ScadutreeFrontload,
  MessmerKindle (+Required/+Max), QuickStart.

Each option must carry a docstring/description (Section 9 gate). This is the greenfield analog of the
existing apworld's ~50-option `EROptions` dataclass, minus the retired/legacy options.

---

## 12. slot_data contract (greenfield target)

Greenfield emits the client's existing key names so no client fork is needed. **Two keys are dropped
by design (P1): `locationIdsToKeys`, `locationIdsToTargets`** — the matt key contract. Everything the
client needs, greenfield provides via flags.

| key | phase | keyed by | source (matt-free) |
|-----|-------|----------|--------------------|
| `world_logic` | MVP | — | option |
| `locationFlags` | MVP | location | `flag` column |
| `apIdsToItemIds`, `itemCounts` | 0 | item | vanilla item ids |
| `regionOpenFlags` | 0 | region | grace warp flags |
| `region_count`, `regionSphereTargets`, `regionSphereTargetRanges`, `completionScalingBasis` | 1 | region | spine + area codes |
| `completion_scaling`, `completion_scaling_floor`, `global_scadutree_blessing` | 2 | region | curve + option |
| `dungeonSweeps`, `sweepLockGates`, `chokepoint_sweeps` | 3 | location trigger (via `map`/`method`) | MSB/EMEVD |
| `shopRowFlags`, `shopPreviewGoods` | 4 | location (shop row) | vanilla ShopLineupParam |
| `progressiveGrants`, `lockGrantItems`, `startItems` | 7 | item | vanilla params |
| `regionGraces`, `graceItems`, `startGraces` | 6 | region | grace anchors |
| `goalLocations`, `areaLockFlags`, `lockRevealFlags` | 1/7 | location/region | `map`/area codes |
| `options{…}`, `versions` | all | — | option surface |

Section 8's determinism rule holds: greenfield slot_data must be reproducible across runs
(`test_gf_world.py::test_slot_data_is_seed_independent` already guards the MVP subset; extend per
phase).

---

## 13. Test + CI parity plan

Each phase promotes its rows in `eldenring/tests/README.md` from "deferred" to "ported." Target
end-state maps 1:1 onto the existing apworld's test battery, but every greenfield test is written
against greenfield's own data:

| existing test | greenfield analog | phase |
|---------------|-------------------|-------|
| `test_data_tables` | `test_gf_data` (done) | MVP |
| `TestER` / `test_slot_data_determinism` | `test_gf_world` (done) | MVP |
| `test_options_descriptions`, `TestEROptionMatrix` | `test_gf_options_*` | 1 |
| region diversity (`run_region_diversity.ps1`) | `run_gf_region_diversity.ps1` | 1 |
| `test_boss_locks` | `test_gf_boss_locks` | 3 |
| `test_shop_checks_gen`, `test_shop_slot_map_gen`, `test_shop_lock_legibility`, `test_merchant_bells` | `test_gf_shops*` | 4 |
| `test_curated_fill`, `test_pool_builder_filler`, `test_capped_uniques_pool`, `test_grace_pool_leak` | `test_gf_pool*` | 5 |
| `test_key_gates_gen`, `test_local_items_gen`, `test_check_item_suppression` | `test_gf_*` | 7 |
| `test_slot_data_fixture` | `test_gf_slot_data_fixture` (Rust contract) | 0/1 |

Every phase runs under `.\run_ci.ps1 -OnlyGreenfield` (fast inner loop) and the full `run_ci.ps1`
before merge. Add a **provenance CI check** (Phase 0): grep the greenfield tree + emitted slot_data
for the banned keys/strings (`locationIdsToKeys`, matt key tokens) and fail if any appear — a
standing guard that parity work never silently re-imports the Bedrock foundation.

---

## 14. Open decisions (flag before building)

1. **DLC depth:** ride DLC as coarse lock-gate buckets (cheap, matches MVP) vs. a full DLC sub-spine.
   Recommend coarse buckets for parity-v1; sub-spine is a later enhancement.
2. **Filler item identity:** which vanilla item backs generic `Rune` filler pre-pool-builder.
3. **Shop-flag table provenance:** confirm `shoplineup_flags.json` / any shop-row table is regenerated
   from vanilla ShopLineupParam and carries no matt addresses; regenerate in-pipeline if unsure.
4. **`region_map.csv` low-confidence rows:** 39 rows in `matt-free-pipeline/low_confidence_review.csv`
   (DLC sub-areas + block-100900 Abandoned Merchant) need an in-game region audit before Phase 1
   sealing trusts them.

---

## 15. Sequencing (recommended)

1. **Phase 0** (boot contract) — nothing else is real until this lands. Small, high-leverage.
2. **Phase 1** (options skeleton + num_regions) — the marquee mode; unblocks the option surface.
3. Then **2/3/6 in parallel** (scaling, boss locks, grace rando — mostly independent), **4** (shops),
   **5** (pool), **7** (long tail) as capacity allows.
4. Ship a **parity-v1** tag when 0–6 are green under `run_ci.ps1`; fold Phase 7 into parity-v1.1.

The through-line: greenfield already proved the *data* is sound (3,944 clean checks). Parity is not
new datamining — it is re-keying your own feature code from location names to the region/`map`/`method`
columns you already have, one CI-gated phase at a time.
