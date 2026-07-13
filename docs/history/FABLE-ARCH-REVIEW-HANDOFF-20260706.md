# Handoff → Fable 5: architecture review of Greenfield + the client

**From:** Opus (main thread) · **Date:** 2026-07-06 · **Model to run:** `fable`
**Task type:** read-only architecture review. **Do NOT edit code.** Produce findings + a handoff back to Opus.

---

## 0. What this is and how to run it

You are reviewing two halves of the Elden Ring Archipelago project that meet at a data contract:

1. **Greenfield** — a from-scratch, matt-free Python apworld (the AP generator side).
2. **The client** — the in-repo Rust runtime that reads slot_data and drives the live game.

This is a **pure read + reason** task. You have a Linux sandbox with the repo mounted at
`/sessions/<session>/mnt/er-archipelago/`. Read files, grep, reason about structure. You **cannot**
run AP gen (needs Windows + Python 3.11) or `cargo` for the Windows-only client crate, and you must
**not** attempt to — this review is about architecture, not building. Do not edit any file.

When done, write findings to `C:\Users\alari\Documents\er-archipelago\FABLE-ARCH-REVIEW-FINDINGS-20260706.md`
and end with the **Handoff back to Opus** block specified in §6.

---

## 1. Review target A — Greenfield apworld

Root: `er-archipelago/greenfield/` — ~18.7k LOC Python.

**Read first (design contract, non-negotiable):** `greenfield/LESSONS-LEARNED.md`, then
`greenfield/SPEC-PARITY.md` §0. The one-line rule everything obeys: *every rule keys off REGION (or
the world's own data columns), never off an imported location name.* The earlier apworld died from
location-NAME coupling to an upstream (Bedrock/matt) foundation; greenfield exists to escape that.

**Orientation docs:** `greenfield/README.md`, `greenfield/HANDOFF.md`, `greenfield/CONTRACT.md`.

**Core module map (`greenfield/eldenring/`):**

| File | LOC | Role |
|---|---|---|
| `__init__.py` | — | World class: items, hub-and-spoke regions, rules, goal, `fill_slot_data` |
| `core.py` | 405 | World assembly / orchestration |
| `contract.py` | 366 | **slot_data contract — single source of truth** (name const + shape + required + producer/consumer per key). `validate_slot_data` wired into `fill_slot_data`; gen fails on drift |
| `data.py` | 4023 | GENERATED: HUB, REGIONS (22 locked spokes), LOCATIONS |
| `item_ids.py` | 5521 | GENERATED item catalogue (note: utf-8/ascii gen bug history — see §4) |
| `region_spine.py` / `region_graces.py` / `region_open_flags.py` | — | region backbone |
| `location_tags.py` | 643 | GENERATED `{ap_id:[type]}` for important_locations |
| `shop_data.py` / `item_tiers.py` / `boss_data.py` / `boss_sweeps.py` | — | data tables |
| `registry.py` | — | feature registry |

**Feature modules (`greenfield/eldenring/features/`):** `area_locks`, `boss_locks`,
`check_item_flags`, `deathlink`, `filler_foreign`, `goal_locations`, `grace_rando`,
`important_locations`, `local_items`, `pool_builder`, `progressive`, `scaling`, `shops`,
`start_grace`, `start_items`, `varied_filler`, `weapon_reqs`. Each is meant to be a self-contained,
region-keyed additive feature. See `features/README.md`.

**Generators / tooling:** `gen_data.py` (703 — regenerates data.py + generated tables),
`gen_contract.py` (emits CONTRACT.md + contract.json + `contract_gen.rs` for the client),
`gen_handoff.py`, `fuzz_gf.py` (203), `gen_fuzz_gf_yamls.py`, `patch_build_greenfield.py`.

**Tests:** `greenfield/eldenring/tests/` — ~25 `test_gf_*.py` files (world, options, num_regions,
boss_locks, shops, pool_builder, progressive, dlc, ending, important_locations, region_diversity,
slot_data_fixture, …).

---

## 2. Review target B — the client

Root: `er-archipelago/from-software-archipelago-clients/` — Rust workspace, multiple crates.
This is a fork of the fswap shared-framework repo (DS3/Sekiro/ER). Read `README.md` and
`CONTRIBUTING.md` at that root — CONTRIBUTING.md is the code-quality bar Alaric holds his own
LLM-generated code to.

**Crates:** `eldenring-archipelago` (the ER client, 6.5k LOC), `er-logic` (pure, host-tested logic,
8.2k LOC), `er-codec`, `er-semver`, `shared` (fswap framework), plus `ds3-archipelago` /
`sdt-archipelago` (sibling games — context only, not under review).

**`eldenring-archipelago/src/` — the live client (Windows-only; net/detour compile on Windows):**

| File | LOC | Role |
|---|---|---|
| `lib.rs` | — | DllMain → shared lifecycle → spawns worker, builds `Core`, schedules `Core::update` each FrameBegin |
| `core.rs` | 1395 | main update loop / orchestration — the heart |
| `contract_gen.rs` | 94 | GENERATED from greenfield `gen_contract.py` — the client half of the contract |
| `key_resolver.rs` | 263 | matt-key `token1` → event flag resolution (the Bedrock-compat path) |
| `detour.rs` | 323 | function hooks |
| `region.rs` | 539 | region lock / open flag handling |
| `fmg_inject.rs` | 715 | in-game text injection |
| `fogwall.rs`, `warp.rs`, `goal.rs`, `deathlink.rs`, `scaling.rs`, `shop_*`, `upgrades.rs`, `startgrants.rs`, `inventory.rs`, `keyitems.rs` | — | feature subsystems |

**`er-logic/src/` — pure logic, unit-tested off the game (this is where architecture lives):**
`tracker_regions.rs` (**5012 LOC — by far the largest file in the repo; flag it for scrutiny**),
`tracker.rs` (487), `receive.rs` (403), `scaling.rs` (413), `progressive.rs` (258), `hook.rs` (254),
`name_override.rs` (214), `region_lock.rs` (212), `deathlink.rs` (197), `upgrades.rs`,
`save_state.rs`, `grants.rs`, `vanilla_suppress.rs`, `grace.rs`, `options.rs`, `sweep_gate.rs`,
`version.rs`. Plus `er-logic/tests/`.

---

## 3. The contract seam (review this carefully — it's the whole point)

Greenfield (Python) and the client (Rust) meet **only** through AP slot_data. As of 2026-07-06 this
was factored into a **two-sided single source of truth**:

- Producer: `greenfield/eldenring/contract.py` → `gen_contract.py` emits `CONTRACT.md`,
  `contract.json`, and `contract_gen.rs`.
- Consumer: client `contract_gen.rs` (generated) + `core.rs` validates slot_data on connect.

Greenfield rides the **keyless** path only: `locationFlags = {ap_id: [event flag]}` for checks, plus
region-open flags and `apIdsToItemIds` for grants. It must NOT emit matt/Bedrock artifacts
(`locationIdsToKeys`, `locationIdsToTargets`, matt key-string tokens, upstream location-NAME set).
The client still *supports* the matt-key path (`key_resolver.rs`) for the Bedrock-compat apworld —
so the client is dual-path while greenfield is single-path. **Assess whether that dual-path client
cleanly serves a single-path producer, or whether the two paths tangle.**

There was recent churn: greenfield emitted only a **subset** of the client's expected contract keys,
leaving features dark until 5 keys were added (`start_grace`, `area_locks`, `goal_locations`,
`check_item_flags`, plus a shop row-id fix). Check the contract for **completeness and drift**: does
every key the client reads have a producer in `contract.py`, and vice versa?

---

## 4. Constraints to judge the architecture against

- **Provenance (P1/P2 in SPEC-PARITY §0):** no Bedrock/matt data or code copied into greenfield;
  every feature re-derived from greenfield's own substrate (`region_map.csv`). Flag any leak.
- **num_regions is the marquee mode** ("the thing that turns ER into an Archipelago game"). Its
  correctness and clarity outrank equal-severity issues elsewhere. Give it extra scrutiny in both
  greenfield (`features/`, tests) and client (`region.rs`, `tracker_regions.rs`).
- **One sound mode per system:** the project deletes unsound alternate modes rather than defending
  them. If you find a fragile toggle, "propose deletion" is a legitimate recommendation.
- **Generated-file discipline:** `data.py`, `item_ids.py`, `location_tags.py`, `contract_gen.rs` are
  GENERATED — review the *generator*, not the output. A past bug: `gen_data.py` wrote files without
  `encoding=utf-8`, so Windows cp1252 corrupted item names → empty catalog. Check that all
  generators force utf-8 + ASCII-safe keys.
- **Dual-write / mount hazards are an environment quirk, not an architecture smell** — ignore any
  null-padding / truncation notes; that's about how files get written from the sandbox, out of scope.

---

## 5. What to produce (the review itself)

Organize findings as:

1. **System diagram in prose** — how greenfield and the client fit together, where the seam is, what
   flows across it.
2. **Greenfield architecture** — module boundaries, coupling, whether features are truly additive and
   region-keyed, generator hygiene, test coverage vs. surface area.
3. **Client architecture** — crate split (`er-logic` pure vs `eldenring-archipelago` live), the
   `tracker_regions.rs` 5k-LOC file (is it doing too much?), dual-path (keyless vs matt-key) coupling.
4. **The contract seam** — completeness, drift risk, whether the single-source-of-truth actually holds.
5. **Top risks, ranked** — with file:line pointers. Separate "architecture" from "bug" (bugs → note
   but don't chase; the live-bug backlog is tracked elsewhere).
6. **Recommendations** — concrete, cheap-first. Call out anything that violates §4 constraints.

Be specific with paths and line numbers. Prefer "X in `file.py:120` couples to Y" over generalities.

---

## 6. Handoff back to Opus (required — end your findings file with this)

```
## HANDOFF BACK TO OPUS
- One-paragraph verdict: is the greenfield↔client architecture sound for v0.1?
- Top 3 risks (file:line, one line each)
- Anything that needs Windows/cargo/in-game verification I couldn't do from the sandbox
- Open questions for Alaric
```

Keep the findings file tight and skimmable. You have a small context budget — read the orientation
docs and the seam files (`contract.py`, `contract_gen.rs`, `core.rs`, `tracker_regions.rs` structure,
a sample of `features/`) rather than every line of the generated tables.
