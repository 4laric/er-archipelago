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
- That `archipelago_rs` 2.1.1's API matches the spike's queue shapes (location send + items_received callback).
