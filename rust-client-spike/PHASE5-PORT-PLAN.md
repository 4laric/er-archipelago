# Rust Client — Phase 5 Port Plan

*2026-06-23. Sequencing the ER feature surface onto the Phase-4 Rust client. Phase 4 (the goods-only
MVP loop: connect → detect → decode → grant → LocationChecks → goal) is compile-green; Phase 5 ports
the "sophisticated" behaviours that today live ONLY in the C++ client (`ArchipelagoInterface.cpp`,
`Core.cpp`, `GameHook.cpp`, `er_gamehook_win.cpp`). Companion to PORT-GAP-MAP.md and
SPEC-rust-client-port.md §4 phase 5.*

## STATUS — Step 0 + Wave A landed & in-game validated; Waves C/D + RE scaffolds wired (2026-06-23)

Branch `port-gap-map`. Build runs on Windows (sandbox has no Rust toolchain; game modules are
`#[cfg(windows)]`). NOTE: the Edit tool truncates this repo's CRLF files — all Rust edits this
session were reconstructed from the git base via Python patch + `cp` + byte/brace verify.

**Step 0 + Wave A (BUILT GREEN + IN-GAME VALIDATED):** a region-lock seed received the lock, set the
grace/open flags, granted the unlock-notify item, and OPENED the region (walked into Altus, no KICK);
reconnect re-applied flags with no re-grant. Plus the double-grant fix: the detour now suppresses +
reports only and lets the server own-world echo be the single grant (Phase-3 local grant removed).
`features.rs` holds the whole Wave-A surface.

**Wave C / D / RE scaffolds (WIRED, built but not yet exercised in-game):**
- `progressive.rs` — progressive bells/physick (`progressiveGrants`): tier-by-receipt-order, persisted
  `progressive_high_index`/`progressive_counter` round-tripped through grant.rs's save. Net loop calls
  `progressive::on_item_received` and skips the normal grant for progressive items.
- `deathlink.rs` — DeathLink (`options.death_link`): protocol COMPLETE on archipelago_rs (tag at
  connect, `Event::DeathLink` in, `death_link()` out). Two `// RE:` holes remain — `kill_player()` and
  `read_local_death()` (both reach the player via the proven `WorldChrMan.main_player`; only the
  HP/death field offset is missing). Inert until filled: receives + logs, never kills/originates yet.
- `upgrades.rs` — `auto_upgrade` + `global_scadutree_blessing`, RE-gated and INERT (`apply_auto_upgrade`
  returns input unchanged, `tick_global_scadu` early-returns). Hooked at the single grant choke
  (`detour::grant_full_id`) + the tick. CE worksheet: `RE-WORKSHEET-autoupgrade-scadu.md`.

Per-feature wiring notes: `PROGRESSIVE-WIRING.md`, `DEATHLINK-WIRING.md` (both already reconciled into
the shared files). Remaining to make C/D live = the CE session for the 4 RE holes (auto_upgrade
reinforce read, scadu stored-blessing write, DeathLink kill + death-detect).

## The shape of the work

Almost every C++ feature is the SAME three-step pattern, so the port is mostly **build the shared
plumbing once, then add a data table + a few lines per feature** — not 20 independent ports.

1. **Receive (net thread, keyed by item NAME).** `set_items_received_handler` looks the AP item NAME
   up in a `name -> {flags|grant}` table and queues an effect. The Rust receive loop already has the
   name (`ri.item().name()`); it just needs the tables + the queues below.
2. **Tick (game thread).** Drains those queues by calling `set_event_flag` / `grant_full_id`
   (both already exist), and polls game state (`play_region_id`, event flags) for latches/sweeps.
3. **Persist.** A couple of features extend the Phase-4 save file (`last_received_index`) with one
   more counter (`progressive_high_index`).

Thread rule (inherited from Phase 4): NAME-keyed decisions happen on the net thread and **queue**;
all event-flag writes, grants, and flag reads happen on the FrameBegin tick. Never touch game memory
from the net thread.

## Step 0 — shared plumbing (build FIRST; everything else reuses it)

| Plumbing | C++ source | Rust target | Notes |
|---|---|---|---|
| Grace-flag queue + drain | `CCore::FlushPendingGraceFlags` (Core.cpp:997) | new `pendingGraceFlags` channel + `flush_grace_flags()` in the tick | `set_event_flag` already in flags.rs; dedup via a `graceFlagsSetThisSession` set; re-queue if the holder isn't ready (returns false). |
| Notify-grant queue + drain | `pendingNotifyGrants` drain (Core.cpp:461) | new channel + drain in the tick via `detour::grant_full_id` | already have the grant primitive. |
| Name-keyed receive dispatch | `set_items_received_handler` (ArchipelagoInterface.cpp:312) | extend `net::connect_and_serve` receive loop | one `match`/HashMap lookup on `ri.item().name()`. |
| Received-NAME set | `Core->receivedItemNames` (ArchipelagoInterface.cpp:330) | `HashSet<Ustr>` on the net thread | needed by natural-key triggers; rebuilt from replay, no persistence. |
| Location-flag polling | `CCore::PollLocationFlags` (Core.cpp:932) | new tick handler → `flags::report_location` | reads guarding flags via `get_event_flag` (game thread); `flagSentLocations` dedup. |
| apconfig extension | `location_flags`, `sweep_flags` (apconfig.json) | add to `net::ApConfig` | these two maps are apconfig-side, NOT slot_data. |

Once Step 0 exists, the Wave-A features are mostly `serde` fields + table entries.

## Wave A — what your live seeds use every day

Your main modes (DLC mini-campaign `ending=messmer`, Godrick goal, `num_regions`, region locks) lean
on the region-lock ecosystem + start grants. ec-goal detection itself already shipped in Phase 4.

| Feature | slot_data key | C++ source | Rust target | Effort |
|---|---|---|---|---|
| Region-lock graces | `regionGraces` | recv handler:337 → pendingGraceFlags | recv table → grace queue | S |
| Region-open flags | `regionOpenFlags` | recv:358 | recv table → grace queue | S |
| Lock reveal/open flags | `lockRevealFlags` | recv:366 | recv table → grace queue | S |
| Lock unlock-notify item | `lockNotifyItems` | recv:375 → pendingNotifyGrants | recv table → notify queue | S |
| Grace rando | `graceItems` | recv:349 | recv table → grace queue | S |
| Start graces (Limgrave) | `startGraces` | parsed at connect:239 → grace queue | connect → grace queue | S |
| Start items / quick_start | `startItems` | once-per-save drain (Core.cpp:484) | connect → start-item queue, once-per-save | S |
| Map reveal (give) + fragment flags | `reveal_all_maps`, kMapUnlockFlags | revealAllMaps (Core.cpp:546) + GiveNextItem (GameHook.cpp:64) | tick + grant-path flag set | S |
| DLC auto-entry warp | `dlcEntryWarpFlag`/`dlcStartAreaId` | Core.cpp:611 latch | tick: `play_region_id`==start → set flag | S |
| Random start warp | `randomStartWarpFlag`/`AreaId`/`DoneFlag` | Core.cpp:625 latch | tick latch | S |
| Key-item acquire flags | (client const table) | recv:407 (Rold 400001, Drawing-Room 400072) | recv const table → grace queue | S |
| Companion acquire flags | (client const table) | recv:384 (Spirit Bell 60110, whetblades) | recv const table → grace queue | S |
| Great-rune restore goods | (client const table) | recv:430 → grant restored row | recv const table → grant queue | S |
| **auto_upgrade** | `options.auto_upgrade` | `AutoUpgradeWeaponId` in `GrantItem` (er_gamehook_win.cpp:201) | hook in `detour::grant_item` + reinforce-level read | **M (RE)** |

Most of Wave A is small once Step 0 lands. `auto_upgrade` is the one that needs real game-memory work
(read your current highest reinforce level on the matching smithing track) — it's broadly useful
(any weapon seed), so do it early but budget for the RE.

## Wave B — sweeps & polling (after the region ecosystem)

| Feature | key | C++ source | Rust target | Effort |
|---|---|---|---|---|
| Flag-bypass check detection | `location_flags` (apconfig) | PollLocationFlags:935 | tick poll → report_location | S |
| Dungeon sweep | `dungeonSweeps` (slot_data) | PollLocationFlags:950 | tick poll | S |
| Boss/grace attribution sweep | `sweep_flags` (apconfig) | PollLocationFlags:970 | tick poll | M |
| Global Scadutree blessing | `options.global_scadutree_blessing` | `SetGlobalScaduBlessing` | client RE | M (RE) |

## Wave C — default-OFF / niche (port when a seed needs them)

| Feature | key | C++ source | Rust target | Effort |
|---|---|---|---|---|
| Progressive bells / physick | `progressiveGrants` | recv:452 (tier by receipt order) | recv + tier counter | **M** (persist `progressive_high_index` in the save) |
| Natural-key triggers | `naturalKeyTriggers` | EvaluateNaturalKeyTriggers (Core.cpp:1026) | tick: NAME+flag clause disjunction → grace/notify queues | M (needs received-NAME set + flag reads) |
| Soft-consumable shop / curation | (apworld-side mostly) | — | minimal client | S |

## Wave D — needs new RE / deferred (own mini-specs)

| Feature | key | C++ status | Blocker |
|---|---|---|---|
| auto_equip / lock_equip | `options.auto_equip`, `options.lock_equip` | client `equipItem` is a STUB | RE the ChrAsm equip fn (see [[er-auto-equip-spec]]) |
| Inventory removal / missed-item recovery | — | `removeFromInventory` works in C++; `sendMissedItems` is a no-op | port the EquipInventoryData walk (er_gamehook_win.cpp:408) |
| On-screen notification banner | (notify v2) | `showBanner` logs only in this build | native FMG/event-banner or hudhook — design choice (PORT-GAP-MAP piece 3) |
| DeathLink | `options.death_link` | C++ has Bounce + DeathLink tag | wire `ConnectionOptions.tags(["DeathLink"])` + `Event::DeathLink`/`client.death_link()` (archipelago_rs has both) |

## Validation

Per SPEC §5: reuse the `gen-test` fill-regression yamls as the "what must still work" matrix, and add
one seed per feature being ported. Wave A is validated by your everyday DLC-messmer / region-lock /
num_regions seeds; Wave C needs a seed that turns the relevant flag on (progressive bells, natural
keys). Each feature lands behind its slot_data flag, so an unported one is simply inert, never wrong.

## Open risks carried from Phase 4

- **Inventory pointer dependency.** Server grants (and thus great-rune-restore / notify grants) wait
  for the session's first local pickup to capture `LAST_INVENTORY`. A version-robust independent
  inventory resolve via fromsoftware-rs (GameDataMan → PlayerGameData) removes this — worth doing
  before Wave A grants are leaned on.
- **Flag reads are game-thread only.** PollLocationFlags, the warp latches, and natural-key flag
  checks must run on the tick, not the net thread — mirror the Phase-4 queue/drain split.
- **Active C++ bugs not to re-port.** The AP icon override, Spirit-Calling-Bell usability, and
  DLC-lock notification gaps are live C++ issues — fix the design, don't copy the bug.
