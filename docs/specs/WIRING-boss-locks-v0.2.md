# Wiring — boss-lock mode A + countdown kick (Windows finish)

*2026-07-07. The pure logic + apworld emission are done and (Python side) verified in-sandbox. These
are the remaining **game-facing** steps, which need Windows (cargo build + net/detour + in-game). No
sandbox can compile the client (`cargo`/`rustc` absent here).*

## What's already landed (verified where possible)
- **apworld** — `boss_locks.py` emits `bossLockItems = {str(boss_flag): {name:"Felled: <Boss>",
  region, boss_ap_id}}` (kept + base-game only via `region_spine.DLC_REGIONS`); `contract.py`
  declares the key; `test_gf_boss_lock_items.py` added. **Verified**: provision + pytest green
  (48 passed / 16676 subtests; contract strict-emission accepts the key; no DLC leak).
- **er-logic (pure, hand-verified — needs `cargo test -p er-logic` on Windows):**
  - `boss_felled.rs` (NEW; `pub mod boss_felled;` already added to `lib.rs`) — `BossState`,
    `boss_state()`, `newly_felled()`, `BossDef`/`build_boss_group()`.
  - `region_lock.rs` + `region_lock_replay.rs` — `KickCountdown` / `KickAction` (+ `DEFAULT_KICK_GRACE_MS = 10_000`) and new `countdown_replay` tests. Existing `kick_decision`/latch untouched.

## Step 0 — build + unit-test the logic (Windows)
`cargo test -p er-logic` — must be green (new `boss_felled` tests + `countdown_replay` + all
existing). Fix any compile nits (MSRV/edition) before wiring.

## Step 1 — parse `bossLockItems` from slot_data (client)
On connect, deserialize the new key into `Vec<BossDef>` (flag, name, region, boss_ap_id; `gate = None`
for v0.2 mode A). Mirror exactly how `bossLocations` / `dungeonSweepFlags` are parsed today
(`region.rs` / `core.rs` slot_data handling). Without this parse `boss_felled` has no input.

## Step 2 — mode-A "Felled" banner + tracker (core.rs)
`Core::update_live`, **section "5b. Flag-poll"** (fn ~L283; boss/sweep block ~L944–965, beside the
existing `er_logic::sweep_gate::gate_open(...)` at ~L948 — reuse that same boss-defeat flag read via
`crate::flags::get_event_flag`):
- Per boss, call `boss_felled::newly_felled(prev_set, now_set)`; on `true`, push the one-shot banner
  `"Felled: <name>"` through the existing overlay-console/log channel. Track `prev_set` per boss in
  `Core` state (same pattern as other edge-triggered polls).
- Tracker window (`Core::render_tracker_window`, ~L1207): call `boss_felled::build_boss_group(defs,
  flag_set, received)` and render the **Bosses** group (locked / felled / released counts + rows).

## Step 3 — countdown kick (region.rs)
`region.rs::tick_kick`, at the `crate::warp::warp_to_grace(ROUNDTABLE_GRACE_ID)` call:
- Hold a `KickCountdown` beside the existing `KICK_LATCH`. Each tick feed it `now_ms`, the live
  `kick_decision` verdict (`currently_in_sealed`), the region name, and the missing `"<Region> Lock"`
  name.
- Only `warp_to_grace(...)` on `KickAction::Kick`. On `KickAction::Warn`, push `action.banner()`
  through the overlay-console path `tick_kick` already returns (`Option<String>` → `region_msgs` →
  `self.log(ap::Print::message(..))` in core.rs ~L1055). This is the overlay console, NOT
  `notif_ticker.rs` (that only drives the native item-gain ticker).

## Step 4 — build + confirm in-game (Windows)
- `cargo build` the client `.dll` (also picks up the earlier internal `EldenRing` rename — dropping
  the dev-only `(Greenfield)` suffix; the AP game id itself is unchanged from v0.1 — see
  `RELEASE-CHECKLIST-v0.2.md`).
- In-game on one seed: defeat a base boss → "Felled: <Boss>" banner + tracker Bosses row flips;
  enter a sealed region → countdown banner naming the missing lock, then kick after ~10s; leaving
  mid-countdown disarms. Add a client replay/semantic-tier guard for the Felled edge (once-only,
  survives save-load + reconnect) if not covered by the new inline tests.

## Not in scope for v0.2 (forward-compat only)
Mode B (`Boss Key: <Boss>` deferred-release) — `boss_felled::boss_state` already takes the `gate`
arg and composes with `sweep_gate.rs`; the apworld would emit `sweepLockGates` + place the keys. v0.3.
