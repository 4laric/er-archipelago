# SPEC — Porting the ER Archipelago runtime client from C++ to Rust

Status: draft / decision doc. Owner: Alaric. Created 2026-06-23.
Scope: the runtime client only (`Dark-Souls-III-Archipelago-client/archipelago-client`, the C++ DLL
injected into `eldenring.exe`). The apworld (Python), the static randomizer (C#), and the bake
pipeline are out of scope except where the client's contract with them constrains the port.

See HANDOFF.md / `git log --all -- archive/HANDOFF.md` (archive/ was removed 2026-07-12; the blobs remain in git history) for project state, SYNC-RUNBOOK.md for the multiworld loop,
tools/NOTES.md (in the client repo) for the RE provenance behind every address used below.

---

## 0. Why this is worth doing — the real driver

The upstream lineage of this client has **already moved to Rust**. This client is the ER port of
nex3's C++ DS3 Archipelago client. That DS3 client has since been rewritten and now lives in
[`fswap/from-software-archipelago-clients`](https://github.com/fswap/from-software-archipelago-clients):
a single Cargo workspace (`crates/`), MIT-licensed, ~99.6% Rust, with a shipping DS3 client
(release `ds3-v4.0.2`, May 2026) and **Sekiro + Elden Ring explicitly listed as planned**.

So "convert the client to Rust" is really **"converge ER onto the fswap workspace and the shared
souls-AP infrastructure"** rather than a from-scratch language swap. The payoff is not just memory
safety; it is:

- Stop maintaining a private one-off. The ER client becomes the `eldenring` member of a workspace
  that other people already maintain (protocol layer, save handling, loader glue, CI).
- Delete almost all of our hand-rolled binding layer. The `er_hooks.h` AOB/RVA sprawl,
  `er_singletons.h` FD4 accessor, the param-table walk, the inventory struct, FieldArea/PlayRegionId
  — these are exactly what the [`fromsoftware-rs`](https://github.com/vswarte/fromsoftware-rs)
  crates (`eldenring`, `fromsoftware-shared`, published on crates.io, v0.14.0 May 2026) already
  provide as typed, community-maintained, patch-tracked structures.
- Get a `cargo`-based, cross-compilable build (the MSVC `.sln`/`.vcxproj` goes away).

The flip side, stated honestly up front: our ER client is **not** the MVP the upstream DS3 client
was. It has grown a large ER-specific feature surface (region fusion, natural-key triggers,
progressive stone bells, dungeon/boss-attribution sweeps, auto-upgrade, global Scadutree blessing,
DLC-only auto-entry, random start). None of that exists in the Rust DS3 client. The port carries all
of it. That is the bulk of the work and the bulk of the risk, and it is mostly *logic* porting, not
binding work.

---

## 1. What exists today (grounded in the current source)

The client is a ~4,600-line MSVC C++ DLL (`archipelago-client.sln` / `.vcxproj`) injected into
`eldenring.exe` 2.6.2.0 (sha256 `3410…3492ddb`). It already self-initializes from `DllMain`
(`CCore::StandaloneInit`) so it runs under ModEngine2, ModEngine3, or Elden Mod Loader — loader
independence is already a design goal, which matters for the Rust target (see §6).

### 1.1 Module map

| C++ unit | Lines | Responsibility |
|---|---:|---|
| `Core.{h,cpp}` | ~1,460 | Lifecycle (`on_attach`/`Run` poll loop, `RUN_SLEEP=2000`), config + save JSON I/O, console prompts, and **all ER state**: `locationFlags` polling, `dungeonSweeps`/`sweepFlags`, region graces/open flags, natural-key triggers, progressive grants, start items, notify grants, DLC/random-start warps. This is where the ER-specific weight lives. |
| `ArchipelagoInterface.{h,cpp}` | ~630 | All AP networking: wraps `APClient` (apclientpp over wswrap/websocketpp/asio). Sets every protocol handler (`slot_connected`, `items_received`, `print_json`, `bounced`/DeathLink, `room_info` → `ConnectSlot`), `LocationChecks`, `StatusUpdate(GOAL)`, `poll()`. Parses slot_data into the Core state structs. |
| `GameHook.{h,cpp}` | ~240 | Thin shim presenting the legacy `CGameHook` interface; forwards to `er_ap::game::`. DS3-specific features (auto-equip, banners, Path of the Dragon, DeathLink) are stubbed for the ER MVP. |
| `er_gamehook.h` + `er_gamehook_win.cpp` | ~945 | The runtime glue, split into a **pure core** (param-table walk, row lookup, synthetic-id decode, pickup decision — host-testable) and a **Windows layer** (AOB scan, singleton/pointer resolution, the `AddItemFunc` MinHook detour, grant call, event-flag set, inventory removal, auto-upgrade, Scadutree tick). |
| `er_hooks.h` | ~145 | The binding map: build-pinned AOBs + resolved RVAs for `AddItemFunc`, `InventoryAccessor`, `ParamBase`, event-flag set/get, `FieldArea`, `GameDataMan`, plus all the param/inventory offsets. |
| `er_singletons.h` | ~60 | FD4 singleton resolution (`SoloParamRepository`, `CSRegulationManager`, `CSEventFlagMan`) by name-string → LEA → instance slot. |
| `er_item_decode.h` / `er_goods_row.h` | ~135 | The synthetic-placeholder encoding contract: category nibble, synthetic-id bound, the `vagrantItemLotId | vagrantBonusEneDrop<<32` decode (the unsigned casts are load-bearing), local-item = `basicPrice × sellValue`, foreign-remove flag. |
| `er_version_check.h` | ~137 | node-semver-exact range check for the `versions` lockstep contract, deliberately not delegated to a library (the `includePrerelease=false` prerelease rule is the load-bearing bit). |
| `ItemRandomiser.{h,cpp}`, `Core.h` constants, `GameTypes.h`, `AutoEquip.*`, `Params.h` | ~ | Queues (`ReceivedItemsQueue`, `checkedLocationsList`), error codes, DS3-era types (mostly vestigial under the goods-only ER model). |

### 1.2 Vendored dependencies (what the Rust port must replace)

minhook, apclientpp, wswrap, websocketpp + asio (standalone), spdlog, nlohmann/json, `mem`,
`fd4_singleton`, ModEngine2 extension headers. Each maps to a Rust equivalent in §3.

### 1.3 The client's four jobs (the invariant the port must preserve)

From `er_hooks.h`, verbatim framing, because these are the contract:

1. **DETECT** a synthetic-placeholder pickup → hook `AddItemFunc` (all item lots route through it).
2. **DECODE** the placeholder payload → read its `EquipParamGoods` row (ParamBase walk + goods-row offsets).
3. **GRANT** a local item / **RECEIVE** a foreign item → call `AddItemFunc` with an item descriptor.
4. **REPORT** the AP check → `CSEventFlagMan` flag set/get + the AP protocol (`LocationChecks`).

Plus the cross-cutting machinery: the 2 s poll loop, JSON config/save persistence, slot_data parsing,
the semver gate, and the large ER feature set layered on top of 1–4.

---

## 2. The encoding & RE contracts that must survive the port byte-for-byte

These are the parts where a "clean rewrite" can silently break a live seed. They are already
isolated and host-tested in C++; the Rust port must reproduce them and re-run the same golden
vectors.

- **Synthetic detection:** category == goods (`id & 0xF0000000 == 0x40000000`) AND
  `(id & 0x0FFFFFFF) > 3,780,000`.
- **Decode:** AP location id =
  `((long)(uint)vagrantItemLotId) | ((long)(uint)vagrantBonusEneDropItemLotId) << 32`. The
  **unsigned** casts are load-bearing — both fields are signed s32 and a naive widen corrupts the
  bit-31 halves. (`tests/reconcile_test` checks the bit-31 corruption cases against spec-2's
  `vagrant_codec.py`.) In Rust: `((vagrant as u32) as i64) | (((bonus as u32) as i64) << 32)`.
- **Param walk:** `repo → +index*0x48+0x88 (hdr) → +0x80 → +0x80 (blob)`; `rowCount @ blob+0x0A`;
  24-byte index entries from `blob+0x40`; row data at `blob + dataOffset`. Goods row stride 176
  (0xB0). The **double** `+0x80` deref is the one that was historically wrong — keep it.
- **Goods-row carrier fields:** `basicPrice 0x10`, `sellValue 0x14`, `disableUseAtOutOfColiseum
  0x4A bit 5 (mask 0x20)`, `vagrantItemLotId 0x54`, `vagrantBonusEneDropItemLotId 0x58`.
- **Semver gate:** node-semver semantics with `includePrerelease=false`; a prerelease version
  satisfies a range only if some comparator shares its exact `[major,minor,patch]` and also carries
  a prerelease. Current contract band: `>=0.1.0-beta.2 <0.1.0-beta.3`.

**Decision: keep #2/#3 in a pure, `no-FFI`, host-testable Rust module (`er_codec`) with the existing
golden vectors ported first, before any in-process code is written.** This is the lowest-risk
starting point regardless of which strategy in §4 we pick.

---

## 3. Component → Rust mapping

| Current C++ | Rust replacement | Notes |
|---|---|---|
| `er_hooks.h` AOBs + RVAs (AddItemFunc, ParamBase, FieldArea, GameDataMan, inventory, event flags) | [`eldenring`](https://crates.io/crates/eldenring) + [`fromsoftware-shared`](https://crates.io/crates/fromsoftware-shared) crates | These crates expose typed `SoloParamRepository`, `CSRegulationManager`, `CSEventFlagMan`, inventory, FieldArea/PlayRegionId, param structures. **Replaces most of `er_hooks.h`, `er_singletons.h`, and the param-walk.** Verify the crate exposes `EquipParamGoods` rows + the vagrant fields; if not, keep our goods-row reader as a thin typed view. |
| `er_singletons.h` FD4 finder | `fromsoftware-shared` `FromSingleton` / from-singleton (Dasaav) | The crate ecosystem already implements the FD4 singleton finder (credited: Sfix/Tremwil/Dasaav). Delete ours. |
| `AddItemFunc` MinHook detour | [`retour`](https://crates.io/crates/retour) (`retour-rs`) | Static/inline detour. The detour body becomes safe-ish Rust over an `unsafe extern "C"` trampoline. |
| AOB scanning (`mem` subproject) | `fromsoftware-shared` scanner, or [`patternsleuth`](https://github.com/trumank/patternsleuth) / a small `aob`/`pelite` helper | Prefer the crate's resolver so patches track upstream. Keep our AOBs as a fallback table. |
| apclientpp + wswrap + websocketpp + asio | **First choice: fswap's own AP/protocol crate in `from-software-archipelago-clients/crates`.** Fallback: [`archipelago-rs`](https://crates.io/crates/archipelago-rs), or a thin layer over `tokio-tungstenite` + `serde_json`. | The whole point of converging is to share fswap's protocol layer. Must confirm it supports: `ConnectSlot` with `items_handling 0b111`, `LocationChecks`, `StatusUpdate(GOAL)`, `Bounce`/DeathLink tags, `Sync`, `print_json` rendering, `set_*_handler` equivalents, and slot_data passthrough. |
| nlohmann/json | [`serde` + `serde_json`](https://crates.io/crates/serde_json) | slot_data and apconfig.json become `#[derive(Deserialize)]` structs — this also documents the contract far better than `data.at("…")`. |
| spdlog | [`tracing`](https://crates.io/crates/tracing) + `tracing-subscriber` (or `log`+`env_logger`) | File + console sink; match current log layout if the runbooks grep it. |
| ModEngine2 extension entrypoint + `StandaloneInit` from `DllMain` | `DllMain` via [`windows`](https://crates.io/crates/windows) crate `#[no_mangle] extern "system" fn DllMain`; optional [me3](https://github.com/garyttierney/me3) (ModEngine3, Rust) host-DLL entry | Keep the "init from DllMain so any loader works" design. me3 is the Rust successor to ME2 and the natural loader to support; ME2 stays supported via the same DllMain path. |
| Win32 calls (heap, long paths, console prompts, `GetLastError`) | `windows` crate | Console prompts can stay, or move to a config-file-only flow (see open questions). |
| `er_version_check.h` | Port verbatim into an `er_semver` module **or** use the [`semver`](https://crates.io/crates/semver) crate **only if** its prerelease matching matches node-semver `includePrerelease=false` | The `semver` crate follows Cargo semantics, which differ from node-semver on prereleases. Safer to port our explicit implementation and keep the test vectors. |
| `Core` state structs (`std::unordered_map<...>`) | plain `HashMap`/`HashSet`/`Vec` in a `ClientState` struct | Direct, mechanical. |
| Cross-thread queues (`receivedItemsQueue`, `pendingGraceFlags`, no-lock by convention) | `crossbeam`/`std::sync::mpsc` channel or `Mutex<VecDeque>` | The current code relies on "single producer on the AP thread, single consumer on the game tick." Make that explicit with a channel; it removes a class of latent data races the C++ comment hand-waves. |

---

## 4. Two migration strategies

### Strategy A — Incremental FFI (port behind the existing C++ shell)

Build a Rust `staticlib`/`cdylib` and call it from the current C++ client via a small `extern "C"`
boundary, porting one module at a time while the client stays buildable and shippable.

Order: `er_codec` (decode/encode + golden vectors) → `er_semver` → config/save (serde) → the pure
param-walk → then the in-process pieces (detour, singletons) → finally the `Core` loop, at which
point C++ is a thin `DllMain` stub and you flip it.

- **Pros:** Always shippable; each step is independently testable against the live game; the
  load-bearing contracts (§2) get ported and re-validated *first*, in isolation; low blast radius;
  you can pause anytime with a working client.
- **Cons:** You maintain a C++/Rust FFI seam for months (cbindgen, two toolchains, MSVC stays in the
  loop until the end); the seam is itself `unsafe` and a bug source; you do *not* get to adopt the
  fswap workspace structure or `fromsoftware-rs` typed singletons until late, because the C++ side
  still owns the binding layer. You partly pay the porting cost twice (FFI shims you later delete).
- **Best when:** the priority is "never have a broken client" and you want to de-risk the encoding
  contracts before anything else.

### Strategy B — Clean-room rewrite that converges on the fswap workspace

Start a new `eldenring` client crate, ideally as a member of (a fork of) the
`from-software-archipelago-clients` workspace, building directly on `fromsoftware-rs` (`eldenring` +
`fromsoftware-shared`), `retour`, `serde`, and fswap's shared protocol/save/loader crates. Port the
logic top-down; the old C++ client keeps shipping untouched until the Rust one reaches parity, then
you cut over.

- **Pros:** You get the real prize immediately — the typed singletons/params, the shared protocol
  and loader infra, the cargo build, the workspace structure, CI. No throwaway FFI seam. The result
  is idiomatic and is the thing you actually want to maintain. Aligns ER with where DS3/Sekiro are
  going so a future shared feature lands once, not three times.
- **Cons:** No working *Rust* client until parity is reached (the C++ one still runs in the
  meantime, so users aren't blocked, but the new path is unverified end-to-end for a while);
  biggest risk concentrated in the large ER feature surface (§1, region/natural-key/progressive/
  sweep/auto-upgrade/Scadutree) which has no upstream Rust precedent; requires the
  `fromsoftware-rs` crates to actually expose the ER structures we need (param goods rows, the
  vagrant carrier fields, inventory remove) — a dependency on someone else's coverage.
- **Best when:** the priority is the end-state (one maintained ecosystem client), and the C++ client
  shipping in parallel is an acceptable safety net during the build-out.

### Recommendation — **B, sequenced with A's first two phases as a de-risking prelude**

Go for the clean-room converge-on-fswap rewrite (B), because the stated driver is ecosystem
alignment and the throwaway FFI seam in A directly works against that — A keeps the C++ binding
layer alive precisely the part B exists to delete. But **borrow A's discipline for the contracts**:
before writing any in-process Rust, stand up the pure `er_codec` and `er_semver` crates with the
existing golden vectors ported and green (these compile and test on Linux/macOS, no game needed).
That captures the only parts where a rewrite can silently corrupt a live seed, cheaply and first.

Concretely, the recommended path:

1. **Spike (1–2 days):** new `eldenring-ap` crate in a fork of the fswap workspace. Build a do-nothing
   DLL that loads under me3/ME2, resolves `SoloParamRepository` via `fromsoftware-rs`, and logs the
   goods param rowCount. This validates the single biggest assumption — that the crates expose what
   we need — before committing.
2. **Port the pure contracts:** `er_codec` (decode/encode, synthetic detection, local-item math) and
   `er_semver`, each with the C++ golden vectors. Host-tested, no game.
3. **The four jobs (MVP parity with the original DS3-level loop):** `AddItemFunc` detour via
   `retour` (DETECT/GRANT), param-walk via the crate's typed `SoloParamRepository` + our goods-row
   view (DECODE), `CSEventFlagMan` set/get + `LocationChecks` (REPORT). Get a goods-only seed
   working end-to-end in-game.
4. **AP protocol + persistence:** slot_data/apconfig as serde structs; config/save I/O; the poll
   loop with the channel-based received-items/grace queues.
5. **The ER feature surface, one SPEC at a time, each behind its slot_data flag and validated against
   a seed that uses it:** location-flag polling, dungeon + boss-attribution sweeps, region graces /
   open flags / map reveal, natural-key triggers, progressive stone bells, start items + notify
   grants, DLC-only auto-entry, random start, auto-upgrade, global Scadutree blessing. (This is the
   long tail; sequence by what current seeds actually use — check Alaric.yaml / the MASTER template.)
6. **Cutover:** when parity + the regression seeds pass, flip the submodule and retire the C++ client.

---

## 5. Validation plan (must exist before cutover)

- **Golden-vector tests** for `er_codec` and `er_semver`, ported from the C++ `tests/` (the
  `reconcile_test`, `walk_test`, version-acceptance vectors). These run in CI on Linux — keep that.
- **A live param-walk smoke test** logged on first run (the two flags tools/NOTES.md already calls
  out: the picked-up id sits at `entry+0x04`; returning 0 from the detour drops the placeholder).
- **A seed matrix**: at minimum one goods-only base seed, one DLC seed, and one seed per major ER
  feature (region_lock, natural keys, progressive, sweeps, random start, dlc_only). Reuse the
  existing `gen-test` fill-regression yamls as the source of truth for "what must still work."
- **Version-lockstep check**: the Rust client's contract version must sit in the same band the
  apworld emits; bake-time and connect-time both gate on it. Don't change the band during the port.
- **Verification subagent / second pass** on the decode and param-walk modules specifically, since a
  silent error there corrupts checks rather than crashing.

---

## 6. Loader, build, and packaging

- **Build:** `cargo build --target x86_64-pc-windows-msvc` (or `…-gnu`) producing a `cdylib`
  (`.dll`). Cross-compilable from Linux/mac for CI; final release build on the matching target.
  The `.sln`/`.vcxproj` and the MSVC PreprocessorDefinitions dance go away.
- **Entry point:** `DllMain` (via the `windows` crate) calls the equivalent of `StandaloneInit` so
  the client works under **me3 (ModEngine3, Rust)**, ModEngine2, and Elden Mod Loader alike — the
  same loader-independence the C++ client already has. me3 is the natural primary loader since it's
  the Rust successor and the ecosystem is moving there.
- **Packaging:** the apworld/randomizer lockstep (SYNC-RUNBOOK.md) is unaffected — the client DLL
  name and the `versions` contract are the only things the host bundle cares about. Keep the DLL
  name stable or update the runbook + RandomizerHelper_config.ini in the same change.

---

## 7. Licensing note

Unlike `SoulsRandomizers` (private — thefifthmatt's randomizer isn't freely licensed), the client's
upstream (fswap) is **MIT**, and `fromsoftware-rs` is MIT/Apache-2.0. A Rust ER client built on them
can be MIT and could plausibly be **upstreamed into the fswap workspace** as the ER member — which is
arguably the best long-term home for it. That is a separate decision from this port, but the port
should keep that door open (clean module boundaries, no SoulsRandomizers code leaking into the
client, MIT headers).

---

## 8. Open questions / decisions needed

1. **Fork vs. separate workspace:** add the ER client as a member crate in a fork of
   `from-software-archipelago-clients` (best for upstreaming, couples us to their churn), or a
   standalone workspace that only *depends on* the published crates? Recommend: fork, develop on a
   branch, with upstreaming as the aspiration.
2. **Does `fromsoftware-rs`'s `eldenring` crate expose what we need?** Specifically: `EquipParamGoods`
   rows reachable from `SoloParamRepository`, the vagrant carrier fields, inventory item
   add/remove, `FieldArea.PlayRegionId`, `CSEventFlagMan` get/set. The §4 spike answers this; if
   gaps exist, decide contribute-upstream vs. local typed view.
3. **AP protocol layer:** reuse fswap's crate (preferred), `archipelago-rs`, or roll a thin
   tungstenite+serde layer? Depends on what fswap's workspace actually factors out — verify by
   reading `from-software-archipelago-clients/crates`.
4. **Console UX:** keep the interactive console prompts (slot/password/seed-mismatch "are you
   sure?"), or move to config-file + in-game messaging? The Rust DS3 client's UX is a reference.
5. **DeathLink and other DS3 features currently stubbed in ER:** port now or leave stubbed? (Most are
   already no-ops in the ER C++ client.)
6. **Event-flag persistence migration** (the `last_received_index` JSON-vs-native-save TODO in
   Core.h): resolve during the port or carry the JSON-file system of record forward as-is?

---

## 9. Effort shape (rough, not a commitment)

- Spike + pure contracts (phases 1–2): small, high-confidence, do first.
- Four-jobs MVP (phase 3–4): medium; this is where the `fromsoftware-rs`/`retour` integration risk
  lives, front-loaded by the spike.
- ER feature surface (phase 5): the large majority of the work; scales with how many SPEC features
  current seeds actually require. Sequence by real usage, not by completeness.
- Cutover (phase 6): small once the seed matrix is green.

The dominant cost is re-implementing the ER feature logic, **not** the binding layer — the binding
layer is mostly *deleted* and replaced by crates. That is the single most important planning fact in
this document.

---

## Appendix — references

- fswap Rust souls-AP clients (convergence target): https://github.com/fswap/from-software-archipelago-clients
- fromsoftware-rs typed bindings (replaces our binding layer): https://github.com/vswarte/fromsoftware-rs — crates: `eldenring`, `darksouls3`, `nightreign`, `sekiro`, `fromsoftware-shared`
- libER (underlying ER structures): https://github.com/Dasaav-dsv/libER
- me3 (ModEngine3, Rust mod loader): https://github.com/garyttierney/me3 · https://me3.help
- retour-rs (detour/hook crate): https://crates.io/crates/retour
- RE provenance for every address/offset reused above: `Dark-Souls-III-Archipelago-client/tools/NOTES.md`
