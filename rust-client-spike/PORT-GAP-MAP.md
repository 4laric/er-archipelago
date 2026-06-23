# Rust Client Port — Gap Map

*2026-06-23. What the ER AP client still needs vs what already exists in `fromsoftware-rs` (the `eldenring` crate), `archipelago_rs`, and fswap's Rust client. Built to scope the port and to hand Natalie a concrete "where do I need general APIs" list.*

---

## TL;DR

The port is **wiring against existing crates, not reverse-engineering**. The spike already nails the hard ER game-side hooks on stable bindings; the two open pieces (`grant_local`, networking) wire to types/crates that already exist, each with a reference implementation in fswap's DS3 client. The "new general bindings" Natalie offered to help with may be close to **empty** — most of what's needed is already in the `eldenring` crate.

## Done (spike, validated in-game)

- **Param access** — `EquipParamGoods` via `SoloParamRepository` (Phase-1, in-game).
- **AddItemFunc detour** — installed clean in-game on stable `GenericDetour` (`@0x7ff6892105b0`), synthetic-goods detect + suppress (Phase-3a).
- **Event flags** — get/set via `CSEventFlagMan` (`event_flag`).
- **In-world gate** — `WorldChrMan.main_player`.
- **Report queue** — `flags.rs` `report_location()` + `drain()` exist (drain to nobody until networking lands).

## Open piece 1 — `grant_local` (inventory grant)

- **Status:** stub (`detour.rs:128`, logs `TODO grant_local`).
- **What it needs:** obtain the inventory instance (GameDataMan → PlayerGameData → inventory) + build the itembuf descriptor, then call the trampoline you already hold (`AddItemHook.call`).
- **Coverage:** ALL types present in `eldenring::cs` — `game_data_man`, `player_game_data`, `item`, `gaitem`, `item_id`. You already hook `AddItemFunc` and hold the trampoline. So this is **wiring, not RE.**
- **Reference impl:** fswap `crates/ds3-archipelago/src/item.rs` (`item::hook_items()` hooks-and-grants for DS3; same shape, different types).
- **Residual:** field-level accessors (which inventory field hangs off `PlayerGameData`) + itembuf layout. Verify against the crate's `player_game_data`/`item`/`gaitem` structs. If a clean inventory-add helper is missing, that one helper is the only candidate for a new binding (lands in nex3's `fromsoftware-extra`).

## Open piece 2 — networking (Phase-4)

- **Status:** TODO (`mod.rs:109` spawn net thread; `mod.rs:145` drain queues).
- **Coverage:** `archipelago_rs = "2.1.1"` is the off-the-shelf AP-protocol crate fswap already depends on. Adopt it; wire `drain()` → location sends, and `items_received` → `grant_local`.
- **Verdict:** **adopt + wire, not RE.**
- **Reference impl:** fswap `crates/ds3-archipelago/` (`core`, `slot_data`, `save_data` modules sitting on `archipelago_rs`). Your `er-semver` version_satisfies already matches their connect-time slot_data version check pattern.

## Open piece 3 — notifications

- **Coverage:** native ER banner via `msg_repository` (exposed in `eldenring::cs`), OR `hudhook`/`imgui` overlay (fswap's cross-game style).
- **Verdict:** **exists both ways — a design choice, not work.** Your C++ client used the native banner (preferred for feel); fswap uses hudhook. Align with them or keep native.

## Already-solved (no new binding)

`event_flag` (flags get/set), `solo_param_repository` (params), `world_chr_man` (in-world), `game_data_man` + `player_game_data` + `item` + `gaitem` + `item_id` (inventory chain), `msg_repository` (messages). The `eldenring` crate is comprehensive because ER is where the fsrs contributors concentrated — exactly as Natalie said.

## Landing in fswap's client (`from-software-archipelago-clients`)

Their workspace = `crates/{ds3-archipelago, sdt-archipelago, shared}` + `archipelago_rs`. Your ER module becomes a sibling crate (e.g. `crates/er-archipelago`). Adopting their `shared` crate gives you lifecycle + panic handling + logger for free (`shared::initialize::<Game>()`, `shared::handle_panics`, `shared::start_logger`), replacing the spike's bespoke DllMain scaffolding.

**Divergences to reconcile:**
- **Hook lib:** you use `retour`/`GenericDetour`; fswap uses `ilhook` (2.3.0, x64). Either align to ilhook or confirm they accept retour.
- **windows crate:** you pin 0.61, fswap pins 0.62. Trivial bump.
- **Bindings source:** you dep `eldenring = "0.14"` (crates.io); fswap pins `vswarte/fromsoftware-rs` via git + nex3's `fromsoftware-extra`. Align to the git pins so new bindings flow through the same channel.

## The actual ask for Natalie (short)

1. Is there a clean inventory-add / item-grant helper for ER, or do I build the itembuf + call the trampoline myself? (the only real "general API" candidate)
2. Should the ER hooks use `ilhook` to match the house style, or is `retour` fine?
3. Confirm the crate layout you'd want the ER module to land as, and which `fromsoftware-rs` / `fromsoftware-extra` git pins to track.

## Open verifies (mine, before quoting "done")

- Exact `PlayerGameData` → inventory field + itembuf struct layout in the `eldenring` crate (confirms grant is pure wiring).
- That `archipelago_rs` 2.1.1's API matches the spik
---

## Phase 4 — IMPLEMENTED (2026-06-23, build pending)

Open piece 2 (networking) is now wired on **`archipelago_rs` 2.1.1** (nex3 — the crate fswap uses).
Crate model = POLL-based (`Connection::update() -> Vec<Event>`), so it runs on the worker thread
`game::init()` already parks — **no async runtime**. New code, all behind an off-by-default `net`
cargo feature (implies `detour`):

- **`game/net.rs`** — connect (`Connection<SlotData>::new`), reconnect loop, `ConnectionOptions`
  with `receive_items(OtherWorlds{own_world:true,starting_inventory:true})` (= C++ items_handling
  0b111) + optional password; typed MVP `SlotData` (apIdsToItemIds / itemCounts / seed / slot /
  versions — serde ignores the Phase-5 keys); `Event` pump; `client.received_items()` -> map AP id
  via `apIdsToItemIds` -> `grant::enqueue`; `flags::drain_reported()` -> `client.mark_checked`;
  GOAL plumbing (`signal_goal()` -> `set_status(ClientStatus::Goal)`); advisory `versions` check via
  `er_semver`. Config from `apconfig.json` (CWD or `$ER_AP_CONFIG`): `{"url":"host:port","slot":..}`.
- **`game/grant.rs`** — server-pushed item GRANT queue + `last_received_index` persistence
  (`archipelago/<seed>_<slot>.json`, atomic write). `drain_and_grant()` runs on the FrameBegin tick
  (only place that touches inventory), gated on in-world; sentinel er_code 99999/99998 skipped.
- **`game/detour.rs`** — added `grant_full_id(full_id, qty)` (builds the 0x50 itembuf — port of C++
  `GrantItem` — and re-enters the original via the trampoline) + caches the live inventory pointer
  (`LAST_INVENTORY`) on every detour call, so server grants need NO new InventoryAccessor AOB.
- **`game/mod.rs`** — `init()` runs `net::run()` on the worker thread (keeps `_task_handle` alive);
  `tick()` calls `grant::drain_and_grant()`.

**Verified API against docs.rs 2.1.1:** `Client::mark_checked(impl IntoIter<impl AsLocationId>)`
(i64: AsLocationId), `set_status(ClientStatus::Goal)`, `received_items() -> &[ReceivedItem]`
(`.index()/.item()/...`; `Item::id() -> i64`, `Item::name() -> Ustr`), `slot_data() -> &S`
(`Connection<S: DeserializeOwned + Send>`), `Connection::new(url, name, Some("EldenRing"), opts)`.

**BUILD (Windows, not compiled in-sandbox):**
`cd rust-client-spike; cargo test --features net; cargo build --release --target x86_64-pc-windows-msvc --features net`
(`.\build.ps1 -Rust` still builds the lean default — net is off-default until this is green; promote
to `default` in eldenring-ap/Cargo.toml once it compiles, like `detour` was). Expect a `// VERIFY`
nit or two on first compile, same as the Phase-3 modules.

**Known MVP limits (documented, for Phase 5):** (1) server grants wait for the FIRST local pickup of
the session (that's when `LAST_INVENTORY` is captured) — a version-robust independent inventory
resolve via fromsoftware-rs is the follow-up; (2) GOAL detection (which boss flag / goalLocations)
is plumbing-only — `signal_goal()` has no caller yet; (3) the rich slot_data feature surface
(graces, natural keys, progressive, DLC auto-entry, notifications) is intentionally Phase 5.
