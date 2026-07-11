# SPEC — Item / Check Tracker

Status: IMPLEMENTED 2026-07-04 — Option A window built and working in-client (toggle F6 / "Tracker" overlay menu). Phase 2+ (map-pinned panel, DataStorage hints, true world-map pins) remain future work.
Owner: Alaric
Scope: an in-client tracker showing what checks remain, what items you hold, and which locations
another player has hinted, as a dedicated overlay window (Option A). Map-marker work is deferred.

---

## TL;DR

Build **Option A — a dedicated "Tracker" window inside the existing hudhook/imgui overlay**,
toggled by hotkey + a menu entry. Every data source it needs is already live in the client; it's
additive and carries no RE risk. **Option B (markers on the actual in-game world map) is deferred** —
true pinned pins need map-UI RE + a world→screen projection we don't have. A screen-space HUD panel
is the eventual "on the map" experience but is out of v0.1.

Locked decisions (2026-07-04): separate window, hotkey toggle from the menu; region grouping via a
static `er-logic` table; hotkey-only (no map-open detection yet); **hint highlighting IS in v0.1**.

---

## What the client already knows (grounding)

From `from-software-archipelago-clients/crates`:

- **Overlay is hudhook + imgui** (`shared/src/overlay.rs`). One main window (menu bar, log, say
  input, connect modal) plus a settings window, both drawn every frame over the game viewport. A new
  window + menu toggle mirrors the existing `settings_window_visible` pattern — local change, no new
  subsystem.
- **AP client state** (`archipelago_rs`, used in `eldenring-archipelago/src/core.rs`): exposes
  `checked_locations()`, `unchecked_locations()`, `received_items()` (full history mirrored via
  `RecvItem`), and item/location id↔name maps. `core.rs` already keeps a `received_through` watermark
  and a cumulative `received_all` name set each tick.
- **slot_data** parsed for regions, DLC, progressive tiers, goal, deathlink
  (`er-logic/src/{options,progressive,version}.rs`) — seed shape without extra plumbing.
- **Current region** live: `WorldChrMan.main_player.play_region_id` (`flags.rs`), reduced to a
  5-digit subregion in `region_lock.rs` — for the current-region highlight and grouping.
- **Region-lock model** (`er-logic/src/region_lock.rs`): `[lo, hi, open_flag]` subregion ranges →
  open flags; boss/sweep gates track unlocked regions. Backbone for locked/unlocked rendering.
- **Hints already arrive**: the overlay handles a `Hint` server-message variant and already filters
  it to our slot (`overlay.rs:498`, `item.receiver()/sender().name() == config.slot()`). Hints are
  also stored server-side in DataStorage (`_read_hints_{team}_{slot}`, see `archipelago_rs
  src/event.rs:121`).

Conclusion: a tracker is a **read/aggregate + render** feature. No new game hooks for Option A. The
one piece needing real plumbing is the standing hint set (see Hint highlighting below).

---

## Option A — Tracker window (v0.1)

A second imgui window, toggled by a **hotkey** and a **menu-bar entry** (next to Settings),
remembered like `settings_window_visible`.

### Panels

1. **Progress header** — `checks: done / total` for the active goal ending + a "goal reached"
   indicator wired to the existing goal config. Optional bar.
2. **Checks by region** — collapsing tree, one node per region (grouped via the static
   location→region table, below). Each node shows `done/total` and expands to unchecked location
   names. Locked regions render dimmed with their gate item/key (from the region-lock ranges).
   Current region (from `play_region_id`) highlighted. **Hinted locations are visually marked**
   (see below).
3. **Key / progression items held** — progressive ladders at current tier (great runes, scadutree,
   medallions, region keys) from `received_all` + `progressive::parse`.
4. **Hints** — a flat list of standing hints relevant to this slot: the hinted location, its region,
   the item, and the other player it concerns. Same locations are cross-marked in panel 2.
5. **Recent receipts** (optional) — last N received items with source player, reusing
   `notif_ticker` / `name_override` display strings.

### Hint highlighting (in scope, needs a small dependency)

Goal: mark any location another player has hinted (or that's been hinted for us) in the checks tree
and list them in the Hints panel.

The overlay currently *renders* `Hint` prints in the log but does not *retain* a queryable set. Two
ways to get a standing set, cheapest first:

- **(a) Accumulate streamed `Print::Hint`** into a `HashSet<location_id>` (+ metadata) held in
  `Core`. Simple, no new server calls; the server replays relevant hints on connect so the set
  rebuilds each session. Risk: relies on replay-on-connect completeness.
- **(b) Read DataStorage `_read_hints_{team}_{slot}`** for the authoritative standing list. More
  robust but the `archipelago_rs` fork exposes no `hints()` accessor today — needs a small Get/
  Retrieved round-trip added (candidate for a tiny upstream/fork addition; relates to
  `[[nex3-archipelago-rs-pr]]`).

Recommend shipping **(a)** for v0.1 (self-contained, no fork change) and noting (b) as the robust
follow-up. Pure hint-set bookkeeping (parse → set → mark) lives in `er-logic` and is unit-testable.

### UX / interaction

- Hotkey toggle (pick a default, rebindable later) + menu-bar entry.
- Reuse existing font-scale + unfocused-opacity so it matches the overlay; inherit the
  Escape/load-into-game auto-defocus.
- Filters: hide-completed-regions, DLC-only, search box (imgui `input_text`, like the say input),
  and a "hinted only" filter.

### Data flow

- Build a `TrackerModel` snapshot once per render inside the existing single `Core` borrow (the
  overlay takes `core` once per frame — do NOT add a second lock; see the comment on `render`).
  Populate from `checked_locations` / `unchecked_locations` / `received_all` / slot_data / hint set.
- **Location→region grouping = static table in `er-logic`** (locked decision): pure, unit-testable,
  no gen-side change; generated from the same source as the AP location id↔name map. Fits the
  er-logic/test conventions (invariant tests like `test_data_tables.py` on the apworld side can
  assert the table stays in sync with locations.py).

### Cost / risk

Low. Touch points: `overlay.rs` (new window + toggle), a `TrackerModel` + static region table +
hint-set module in `er-logic` (with tests), and a small hint-accumulation hook in `Core`. No RE, no
regulation edits. Verify counts vs a generated spoiler on Windows; verify hint marks by placing a
hint in a 2-slot test seed.

---

## Option B — "on the in-game map" (DEFERRED)

- **B1 — screen-space HUD panel** (feasible later, small): draw the tracker pinned while the map is
  open. hudhook already renders over everything; the missing piece is map-open detection (probe the
  typed `eldenring` menu singletons for a screen-state flag). Not in v0.1.
- **B2 — markers pinned to world-map coordinates** (not feasible now): needs map-screen open/pan/zoom
  state, a world→map-screen projection, and per-location world coords (we track checks by flag/region,
  not XY). None exist in the codebase. Separate RE project; coordinate with the poptracker map
  (`[[er-poptracker-dlc-only]]`).

---

## Phased plan

- **Phase 1 (v0.1) — ✅ DONE / shipped:** Option A window — `TrackerModel` + static
  location→region table + hint-set module in `er-logic` (tested); new window + hotkey/menu toggle in
  `overlay.rs`; hint accumulation in `Core`. Verify counts vs spoiler; verify hint marks in a 2-slot
  seed.
- **Phase 2:** B1 screen-space pinned panel + map-open detection; robust hints via DataStorage (b).
- **Backlog:** B2 true map pins (own RE spec + per-location coordinate dataset).

## Resolved decisions

1. Separate window, hotkey toggle from the menu. ✅
2. Region grouping via a static `er-logic` table (testable), not slot_data. ✅
3. Map-open detection: hotkey-only first. ✅
4. Hint highlighting IS in v0.1 — mark any location another player has hinted, via accumulated
   `Print::Hint` (option a); DataStorage `_read_hints` is the Phase-2 robustness follow-up. ✅
