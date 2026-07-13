# Fable 5 architecture review — Greenfield apworld + client (2026-07-06)

Read-only review per FABLE-ARCH-REVIEW-HANDOFF-20260706.md. No code edited, nothing built.
File:line refs are against the repo as mounted 2026-07-06.

---

## 1. System diagram in prose

**Greenfield (Python, gen-time)** builds a hub-and-spoke world: `Menu → Roundtable Hold (free) →
22 region spokes`, each gated by `state.has("<Region> Lock")` (`eldenring/core.py:322-333`).
`num_regions` + DLC toggles shrink the spoke set via the pure `region_spine.compute_kept`
(`region_spine.py:59-83`); sealed regions are simply never instantiated. All world data comes from
generated tables (`data.py`, `item_ids.py`, `region_open_flags.py`, `boss_data.py`, …) which
`gen_data.py` derives from `region_map.csv` + grace anchors — no upstream location names anywhere.

**The seam is slot_data, and only slot_data.** `core.py:_base_slot_data` (core.py:337-370) emits the
keyless base contract (`locationFlags` = {ap_id: flag} scalar, `apIdsToItemIds`, `regionOpenFlags`);
each feature in `features/` contributes its own keys via `registry.merge_slot_data` (collision-
checked, registry.py:70-78); `fill_slot_data` then runs `contract.validate_slot_data(strict=True)`
(core.py:372-375) so a missing/mis-shaped declared key fails at gen. `gen_contract.py` mirrors
`contract.py` into `CONTRACT.md` / `contract.json` / the client's `contract_gen.rs`.

**The client (Rust, run-time)** parses slot_data once on connect (`eldenring-archipelago/src/
core.rs:290-430`), warn-validates it against `contract_gen.rs` (core.rs:295-300), and fans the
parsed config out to ~15 subsystems (region kick-watch, startgrants, shops, goal-send, scaling,
vanilla-suppress detour, …). Pure decisions live in `er-logic` (host-tested: `region_lock.rs`
kick_decision, `tracker.rs`, `scaling.rs`, `options.rs`, `vanilla_suppress.rs`); the live crate is
glue + game memory. The client is dual-path: matt-key resolution (`key_resolver.rs`) is preferred
when `locationIdsToKeys` is present, with fallback to greenfield's `locationFlags`
(core.rs:335-343). Greenfield never emits the matt keys, so it rides the fallback.

Runtime loop: flags poll → checks sent; received items → grants / region-open flags / grace flags;
goal = flag-detected boss locations (`goal.rs`, local-first, `!collect`-immune).

---

## 2. Greenfield architecture

**The registry/feature pattern is genuinely good.** `registry.py` enforces uniqueness of option
fields, item names, and slot_data keys (registry.py:44-78); features may not import core (no
cycles); aggregation helpers are pure and unit-testable. Adding a phase really does touch only one
file. Features are region-keyed as promised — every rule I sampled (`area_locks`, `grace_rando`,
`goal_locations`, `check_item_flags`, `boss_locks`, `important_locations`) keys off region name,
`flag`, `method`, or `item_name`, never an imported location name. The LESSONS-LEARNED design
contract holds in the code.

**num_regions (marquee) is structurally clean.** `compute_kept` is pure, draws only from the
already-filtered eligible pool, always appends the goal region when eligible, and degrades sanely
under `dlc_only` (goal falls to the deepest kept region, goal_locations.py:60-71). Kept-scoping is
consistently applied across `locationFlags`, `regionOpenFlags`, `areaLockFlags`, `checkItemFlags`,
`regionGraces`, `dungeonSweepFlags` — features read `world._kept()` uniformly.

**Weak points:**

- **Silent-degrade imports.** Every generated table is imported under bare `except Exception`
  fallbacks to empty (`core.py:24-33`, and the same pattern in ~6 features). This is exactly the
  shape of the 2026-07-06 all-Rune incident: a corrupted `item_ids.py` degrades to an empty catalog
  and the world "gens fine". `data.py` itself (the location backbone) is imported without a guard —
  good — but the item/flag layers should either fail loudly when the file EXISTS but won't import,
  or assert non-empty in `generate_early` when a dependent option is on.
- **Hand-maintained data inside a feature.** `area_locks.py:44-70` `REGION_PLAY_IDS` is a manually
  curated region→play_region table (with careful provenance comments), while its overworld half
  duplicates knowledge `gen_data.py` already has (PLAY2AP). Drift between them is silent (a missing
  id = never kick-gated). Should be generated alongside `region_open_flags.py`.
- **core.py does real work at import time** (item catalog assembly, GREAT_RUNES scan,
  core.py:36-160). Tolerable at this size, but it means import order and generated-file state
  determine the world's item universe with no seed-time visibility.
- **Generator hygiene is mostly fixed, not fully.** All *writes* force `encoding="utf-8"` and
  `ascii()` keys (gen_data.py:262-691) — the past cp1252 bug is closed on the write side. But
  *reads* of `region_map.csv` (gen_data.py:90), the grace TSVs (:25, :28), and one CSV (:471) use
  platform-default encoding: on Windows, utf-8 names in the substrate would silently mojibake
  (output stays valid Python via `ascii()`, but names would be wrong). One-line fixes.
- **Tests:** 21 `test_gf_*` files cover core, data invariants, num_regions, DLC, ending, and most
  features; the pure suite runs sandbox-side (ci-linux.sh). Coverage vs surface is decent. What is
  missing is a test asserting the slot_data the CLIENT actually reads (see §4) — the fixture test
  validates against contract.py, which shares contract.py's blind spots.

---

## 3. Client architecture

**The er-logic / eldenring-archipelago split is the best thing in the client.** Kick decisions,
tracker aggregation, scaling curve/parse, option parsing, vanilla-suppress, deathlink policy are all
pure, host-tested, and injected with state by the live crate. `tracker.rs` explicitly takes the
location→region table as a parameter to stay data-free — good discipline.

**tracker_regions.rs (5,012 LOC) is not doing too much — but it is the WRONG data for greenfield.**
It is a generated table (`@generated by tools/gen_location_regions.py`, header line 1-6) of
`(id, fine_region, coarse_region, big_ticket, missable)` + five tiny accessors + shape tests. Size
is fine for generated data. The problem: it is generated **from the OLD apworld**
(`Archipelago/worlds/eldenring/{locations,map_region_data,grace_data}.py`) with ids in the
7,000,000 range, while greenfield ids start at 7,770,000 (data.py, tests/README.md). Zero overlap:
under a greenfield seed the tracker window buckets every location into `"(unknown region)"`
(tracker.rs:31-46 under-enforce fallback) and the coarse in-logic distinction is inert. Graceful,
not broken — but the marquee mode's tracker is dark, and the table embeds the old (matt-id-space)
location metadata inside the otherwise provenance-clean client crate. It needs a greenfield twin
generated from `data.py` (+ selection by `world_logic`), or regeneration.

**core.rs:272-430 (`update_live` connect block) is a 150-line inline parse-and-configure monolith**
touching 15+ subsystems. It works, and the one-shot `slot_data_parsed` latch keeps it contained,
but every new contract key grows this block. Extract a `parse_slot_data(sd) -> ParsedConfig` module
when it next changes; not urgent for v0.1.

**Dual-path (matt-key vs keyless) does NOT tangle — it layers.** Precedence is
`locationIdsToKeys` (if non-empty) else `locationFlags` (core.rs:335-343); shop-row resolution
folds in disjointly (`entry().or_insert`, core.rs:344-360). For a single-path greenfield producer
this is clean: the matt path is simply never taken. The residue is a set of bedrock-era config
fields parsed unconditionally with no greenfield producer — `randomStart*` (region.rs:106-125),
`naturalKeyTriggers`, `lockGrantItems` (region.rs:126-127), `itemCounts` (core.rs:318). They
default inert, but they blur which features are live under which profile. The path switch is an
*empty-check*, not an explicit profile check — `world_logic` exists and could gate it.

**Good asymmetry:** the client's contract validation is warn-only (core.rs:295-300) while gen-side
is strict — a partially compatible seed still boots with every problem logged. Correct choice.

---

## 4. The contract seam — the single source of truth leaks on three sides

`contract.py` is a strong idea well executed *for the keys it knows about*: shape checkers mirror
the exact Rust parsers, producer/consumer are documented per key, and the generated
`contract_gen.rs` means both sides validate the same shapes. The 2026-07-06 5-key incident is
exactly what it exists to prevent. But the guarantee currently has holes:

**(a) The client reads an `options` SUB-DICT that greenfield never emits — several features are
dark right now.** `er_logic::options::parse_bool_option` reads `slot_data["options"][key]`
(er-logic/src/options.rs:12-21). Consumers: `death_link` (core.rs:303), `no_weapon_requirements`
(core.rs:305-307), `enable_dlc` → DLC map-reveal (startgrants.rs:66), `completion_scaling`
(eldenring-archipelago/src/scaling.rs:33), plus `sd.pointer("/options/auto_upgrade")`,
`/options/global_scadutree_blessing`, `/options/flatten_regular_upgrades` (core.rs:309-315) and
`/options/completion_scaling_floor` (er-logic/src/scaling.rs:~183). Greenfield emits these keys
**top-level** (features/deathlink.py:18, weapon_reqs.py:26, scaling.py:39-44) and emits no
`"options"` dict anywhere (grepped: zero hits). `contract.py` validates the top-level keys →
**validation passes while the client reads absent paths and defaults everything to off**:
DeathLink, no-weapon-reqs, completion scaling, scadutree blessing, DLC map reveal
(`startgrants.rs:67`'s top-level fallback is `.as_bool()`-only, so even an int `enable_dlc: 1`
top-level would not save it — and greenfield doesn't emit it at all). This is the same failure
class as the 5-key incident, one layer deeper: the contract declares the right key NAME but not the
right key PATH.

**(b) Completion scaling is dark twice over.** Even with (a) fixed, the client's live wire format is
`regionSphereTargetRanges` = `[[lo, hi, target]]` in play_region/100 space
(er-logic/src/scaling.rs:150-165, with an explicit comment that the flat name-keyed map is
"unparseable -> empty"). Greenfield emits only `regionSphereTargets` keyed by region NAME with
FLOAT values (core.py:352-353) — doubly unparseable by `i32_i32_map` (scaling.rs:126-136). And
`contract.py` declares `regionSphereTargets` as shape ANY, "(informational; not enforced by the
client)" — a stale claim — while `regionSphereTargetRanges` is not declared at all. SPEC-PARITY
marks Phase 2 "COMPLETE"; the wire is not connected.

**(c) Undeclared keys flow in both directions, invisibly.** Producers emit keys contract.py does
not know: `region_count`, `completionScalingBasis`, `ending_condition`, `great_runes_required`,
`great_rune_items` (core.py:356-369, some as bare string literals, bypassing the name-constant
discipline), `bossLocations` + `sweepLockGates` (features/boss_locks.py:59,66),
`completion_scaling`/`_floor`/`global_scadutree_blessing` (features/scaling.py:39-44),
`pool_builder*` (pool_builder.py:194-197), `filler_foreign_localized` (filler_foreign.py:123).
The client reads keys contract.py does not know: `sweepLockGates` (flagpoll.rs:117),
`randomStart{DoneFlag,WarpFlag,AreaId,GraceId}` (region.rs:106-125), `fogWalls`/`fogWallDebug`
(fogwall.rs), `versions` (core.rs:~404), and the whole `/options/*` subtree. `validate_slot_data`
ignores unknown keys by design, so none of this is flagged on either side. Minor profile tangle in
the same vein: boss_locks.py:66 emits `dungeonSweeps: {}` although the contract tags that key
BEDROCK-profile with producer "(bedrock apworld)".

Verdict on the seam: the mechanism is right, the coverage is partial. The contract validates what
is declared; the incidents keep coming from what isn't. Close the loop by making *emission* (not
just shape) contract-driven: `merge_slot_data` should reject any key absent from `contract.BY_NAME`
(with an explicit `EXTRA_OK` list if needed), and a client-side audit (grep `sd.get(`/`pointer(` vs
`CONTRACT`) should run in CI.

---

## 5. Top risks, ranked

Architecture (A) vs bug-revealed-by-architecture (B):

1. **(B, blocker-class)** Options subtree mismatch — client reads `sd["options"][...]`, greenfield
   emits top-level; death_link / no_weapon_requirements / enable_dlc(DLC map reveal) /
   completion_scaling / scadutree / upgrade knobs all silently OFF under greenfield.
   `er-logic/src/options.rs:12-21` + `core.rs:303-315` + `startgrants.rs:66` vs
   `features/deathlink.py:18`, `features/scaling.py:39-44`, `features/weapon_reqs.py:26`.
2. **(A)** Contract validates declared keys only, and only their top-level presence/shape —
   undeclared emissions and undeclared client reads (incl. the entire `/options/` path and
   `regionSphereTargetRanges`) are invisible. `contract.py:246-263` (validate ignores unknowns),
   `registry.py:70-78` (merge accepts any key). This is the generator of risk #1 and of the
   2026-07-06 5-key incident; until emission is contract-gated, the next dark feature is a matter
   of time.
3. **(B)** Completion scaling wire format: client live path `regionSphereTargetRanges`
   (er-logic/src/scaling.rs:150-165) has no greenfield producer; the emitted `regionSphereTargets`
   is name+float-keyed and documented-unparseable (core.py:352-353). Marquee-adjacent (scaling is
   the difficulty story for num_regions runs).
4. **(A)** `tracker_regions.rs:1-13` is generated from the OLD apworld's id space (7,000,000 vs
   greenfield 7,770,000) — the in-game tracker degrades to "(unknown region)" for every greenfield
   location, and old-world-derived metadata lives in the client crate (provenance blemish, not a
   leak into greenfield itself).
5. **(A)** Silent-degrade generated-table imports (`core.py:24-33` + feature try/excepts) — the
   all-Rune failure mode is still structurally possible; a corrupt `item_ids.py` produces a
   "working" world.
6. **(A, minor)** Hand-maintained `REGION_PLAY_IDS` (features/area_locks.py:44-70) duplicates
   gen_data knowledge; silent under-enforcement drift. Plus gen_data.py read-side encoding gaps
   (:25, :28, :90, :471).
7. **(A, note)** Sealed (non-kept) regions have no `areaLockFlags` ranges and no checks — in-game
   they are physically enterable vanilla territory with no kick and no suppression
   (checkItemFlags is kept-scoped, check_item_flags.py:53-55). Possibly intended ("sealed =
   vanilla"), but worth an explicit decision for the marquee mode.

Not chased (tracked elsewhere): start-item clobber, flask double-grant, shop weapon slots, etc.

---

## 6. Recommendations (cheap first)

1. **Emit an `options` echo dict** from `_base_slot_data` (`"options": {name: int(value) for
   core+feature option fields}`) — one change, and risk #1's whole key family lights up with zero
   client changes. Then declare `options` in contract.py (new shape OPTIONS_DICT) so it's validated.
2. **Gate emission on declaration:** in `registry.merge_slot_data` (or `fill_slot_data`), reject
   keys not in `contract.BY_NAME`. Move core.py's bare-string keys (`region_count`,
   `ending_condition`, …) into contract.py. ~30 lines total.
3. **Add a client-side key audit to CI:** grep the client for `sd.get("…")` / `pointer("/…")` and
   diff against `contract.json`. Catches direction (c) drift mechanically.
4. **Produce `regionSphereTargetRanges`** in features/scaling.py from area_locks' play-region
   knowledge (ranges are already the client's live format), and fix the stale
   `regionSphereTargets` ANY/"informational" annotation in contract.py.
5. **Regenerate a greenfield `tracker_regions` table** from `data.py` (the generator pattern
   already exists; fine region = greenfield region, coarse = the same, big_ticket from
   location_tags.py), selected by `world_logic`.
6. **Fail loudly on corrupt generated tables:** replace `except Exception → empty` with
   `except ImportError → empty` + re-raise (or log-and-flag) on other exceptions; assert
   ITEM_CATALOG non-empty in generate_early when item_shuffle/varied_filler is on.
7. **Generate `REGION_PLAY_IDS`** into a table next to `region_open_flags.py`; add explicit
   `encoding="utf-8"` to gen_data.py's four unguarded reads.
8. **One-sound-mode candidates:** `dungeonSweeps: {}` + `sweepLockGates: {}` placeholders in
   boss_locks.py — delete until the location-keyed variant has a real producer; consider gating the
   client's matt-key path on an explicit profile signal (`world_logic`) instead of empty-check.

---

## HANDOFF BACK TO OPUS
- **One-paragraph verdict:** The architecture is sound for v0.1 in its bones — the registry/feature
  pattern, region-keyed rules, pure-vs-live crate split, and the two-sided contract are all the
  right shapes, and num_regions' gen-side spine is clean — but the contract's guarantee is
  currently narrower than everyone believes it is: it validates declared top-level keys while the
  client reads an `options` SUB-DICT greenfield never emits (death_link, no_weapon_requirements,
  DLC map reveal, completion scaling, scadutree, upgrade knobs all silently dark) and a scaling wire
  key (`regionSphereTargetRanges`) that has no producer. Fix the options echo + contract-gated
  emission (recs 1-3, ~a day) and the seam actually becomes the single source of truth it claims to
  be; the tracker-table id-space mismatch is the only other v0.1-visible gap.
- **Top 3 risks:**
  1. `er-logic/src/options.rs:12` + `core.rs:303-315`/`startgrants.rs:66` read `options.*`;
     greenfield emits top-level only (features/deathlink.py:18, scaling.py:39, weapon_reqs.py:26) —
     6+ features dark under greenfield despite "contract: slot_data OK".
  2. `contract.py:246` validate ignores unknown keys + `registry.py:70` merge accepts any key —
     undeclared keys flow both directions unchecked (this is what keeps producing dark-feature
     incidents).
  3. `er-logic/src/scaling.rs:150-165` live path `regionSphereTargetRanges` has no greenfield
     producer; emitted `regionSphereTargets` (core.py:352) is name+float-keyed and unparseable —
     completion scaling inert.
- **Needs Windows/cargo/in-game verification:** (1) confirm in a live greenfield connect log that
  death_link/no_weapon_requirements/completion_scaling stay off and the DLC map-reveal flags are
  skipped (predicted from source only); (2) whether AP itself injects any option echo into
  slot_data for this world (I believe not — nothing in greenfield requests it); (3) tracker window
  under a greenfield seed shows "(unknown region)" buckets; (4) cargo test still green after any
  contract_gen.rs regeneration.
- **Open questions for Alaric:** (1) Are sealed (non-kept) regions *intended* to be physically
  enterable vanilla territory (no kick, no suppression, vanilla loot), or should they get
  areaLockFlags ranges with a never-set flag? (2) Should the client's matt-key path be gated on an
  explicit profile signal (`world_logic`) rather than the empty-check, per one-sound-mode? (3) Is
  the plan for the tracker a greenfield-generated `tracker_regions` twin, or a slot_data-driven
  table (which would also remove old-apworld-derived data from the client crate)?
