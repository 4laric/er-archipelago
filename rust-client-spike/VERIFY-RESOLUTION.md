# VERIFY-RESOLUTION — eldenring 0.14 symbol mapping

Resolves the `// VERIFY:` tags in `crates/eldenring-ap/src/game/*.rs` against live docs.rs +
the fromsoftware-rs examples (fetched 2026-06-23). Pairs with `BUILD-NOTES.md §3` (the checklist)
and `README.md`. Target crates: `eldenring` 0.14.0, `fromsoftware-shared` 0.14.0, `retour` 0.3,
`windows` (the crate's actual pin is **^0.61**, not the 0.58 the Cargo.toml guessed).

> **Status:** the symbol spellings below are confirmed from docs.rs; the edits applying them to
> `game/` are **not compiler-checked** — the in-process modules are `#[cfg(windows)]` and there is
> no MSVC toolchain in the sandbox. Build on the laptop (`cargo build --target
> x86_64-pc-windows-msvc`) to typecheck. The pure crates still test green (14/14) on Linux.

---

## The five corrections that matter (the sketch's guesses were wrong here)

1. **Singletons are `unsafe fn instance() -> Result<&'static Self, InstanceError>` via the
   `FromStatic` blanket impl** — not a safe `Option`-returning inherent `instance()`. Every
   singleton call needs `use fromsoftware_shared::FromStatic;`, an `unsafe { }` block, and `.ok()?`
   (or match on the `Result`). `instance_mut()` for `&mut`. Applies to `SoloParamRepository`,
   `CSEventFlagMan`, `WorldChrMan`.
2. **Row lookup is generic over `SoloParam`, not `ParamDef`.** `ParamDef` only carries
   `{ NAME, INDEX }` — it cannot look up rows. The goods marker is the **zero-sized
   `eldenring::cs::EquipParamGoods`** (`impl SoloParam`, `INDEX = 3`, `StructType =
   EQUIP_PARAM_GOODS_ST`). You write `repo.get::<EquipParamGoods>(id)`.
3. **Event flags are `get_flag` / `set_flag` on `CSEventFlagMan.virtual_memory_flag`** (type
   `CSFD4VirtualMemoryFlag`), taking `impl Into<EventFlag>` (a `u32` auto-converts) — NOT a
   `get_event_flag` / `set_event_flag` on the manager itself.
4. **There is no `CSFieldArea`.** Current region = `WorldChrMan.main_player` →
   `PlayerIns.play_region_id` (`u32`). The `FieldArea` type exists but only holds area/block ids.
5. **Goods fields are snake_case getter/setter METHODS, not public fields**; bitfields are typed
   `bool` getters. `row.basic_price()`, `row.disable_use_at_out_of_coliseum()`.

Also fixed: `run_recurring` returns a `RecurringTaskHandle` that **unregisters the per-frame task
when dropped** — the sketch dropped it. `mod.rs` now binds it (`let _task_handle = …`) and parks
the worker thread to keep it alive.

---

## 1. Param lookup — `params.rs` (RESOLVED, wired)

| Need | Confirmed symbol | Source |
|---|---|---|
| Goods row struct | `eldenring::param::EQUIP_PARAM_GOODS_ST` | docs.rs/eldenring/0.14.0/eldenring/param/ |
| Turbofish marker | `eldenring::cs::EquipParamGoods` (zero-sized; `INDEX 3`, `StructType = EQUIP_PARAM_GOODS_ST`) | …/eldenring/cs/trait.SoloParam.html |
| `SoloParam` trait | `const NAME: &'static str; const INDEX: u32; type StructType: ParamDef;` | …/src/eldenring/cs/solo_param_repository.rs.html#494 |
| Repo singleton | `unsafe { SoloParamRepository::instance() } -> Result<&'static Self, InstanceError>` | …/eldenring/cs/struct.SoloParamRepository.html |
| One row by id | `repo.get::<EquipParamGoods>(id: u32) -> Option<&EQUIP_PARAM_GOODS_ST>` | ditto |
| Iterate/count | `repo.rows::<EquipParamGoods>() -> impl Iterator<Item=(u32, &…)>`; count via `.count()`, firstRowId via `.next().map(\|(id,_)\| id)` | ditto |
| Field reads | `vagrant_item_lot_id()`, `vagrant_bonus_ene_drop_item_lot_id()`, `basic_price()`, `sell_value()`, `disable_use_at_out_of_coliseum()` (all `&self` methods) | …/param/struct.EQUIP_PARAM_GOODS_ST.html |

`spike_log_goods_rowcount()` now logs `rowCount` **and** `firstRowId` for the NOTES.md `3571 / 0`
cross-check.

## 2. Event flags + region — `flags.rs` (RESOLVED, wired)

| Need | Confirmed symbol | Source |
|---|---|---|
| Flag manager | `eldenring::cs::CSEventFlagMan` (singleton via `FromStatic`) | …/eldenring/cs/struct.CSEventFlagMan.html |
| Get flag | `CSEventFlagMan::instance()?.virtual_memory_flag.get_flag(flag_id) -> bool` | …/src/eldenring/cs/event_flag.rs.html |
| Set flag | `CSEventFlagMan::instance_mut()?.virtual_memory_flag.set_flag(flag_id, state)` | ditto |
| `EventFlag` | `#[repr(transparent)] struct EventFlag(u32)` + `From<u32>` (pass a `u32` literal) | ditto |
| Region id | `WorldChrMan::instance()?.main_player.as_ref()?.play_region_id` (`u32`) | …/src/eldenring/cs/{world_chr_man,chr_ins}.rs.html |

## 3. Task loop — `mod.rs` (RESOLVED; imports were already correct)

| Need | Confirmed symbol | Note |
|---|---|---|
| `CSTaskImp`, `CSTaskGroupIndex` | `eldenring::cs::…` (`FrameBegin` / `FrameEnd` variants exist) | — |
| `FD4TaskData` | `eldenring::fd4::FD4TaskData` (`delta_time: FD4Time`, not raw f32) | — |
| Ext trait | `fromsoftware_shared::SharedTaskImpExt` (re-export of `…::task::SharedTaskImpExt`) | provides `run_recurring` |
| `wait_for_instance` | **inherent blocking method on `CSTaskImp`**: `fn wait_for_instance(Duration) -> Result<&'static Self, SystemInitError>` | not async, not on the ext trait |
| `run_recurring` | `fn run_recurring<T: Into<RecurringTask<…>>>(&self, execute: T, group: TIndex) -> RecurringTaskHandle<…>` | **keep the handle alive** |

Idiom (verbatim, fromsoftware-rs `apply-speffect` example):
```rust
let cs_task = CSTaskImp::wait_for_instance(Duration::MAX).unwrap();
cs_task.run_recurring(|_: &FD4TaskData| { /* per-frame */ }, CSTaskGroupIndex::FrameBegin);
```

## 4. retour 0.3 — `detour.rs` (already correct; confirmed)

`static_detour! { static AddItemHook: unsafe extern "C" fn(...) -> u64; }` (feature
`static-detour`). Generated `StaticDetour<T>`: `unsafe initialize(target, closure) -> Result<&Self>`,
`unsafe enable() -> Result<()>`, `call(args) -> Output` (panics if not initialized). Crate renamed
`detour` → `retour`; import `use retour::static_detour;`.
Source: docs.rs/retour/0.3.1/retour/macro.static_detour.html.

> **TOOLCHAIN (build-verified 2026-06-23):** `static_detour!` requires **nightly**
> (`#![feature(unboxed_closures, tuple_trait)]` → `error[E0554]` on stable). But fromsoftware-rs
> pins **stable** (`rust-toolchain.toml` = `channel = "stable"`), so the ecosystem avoids the static
> detour. **Decision:** stay on stable; Phase 3 implements `detour.rs` with retour's stable
> **`GenericDetour`** (that API needs no feature flag). For now the `detour` module + the
> `retour`/`windows` deps sit behind an **off-by-default `detour` cargo feature**, so the Phase-1
> spike builds on stable. Also bumped `windows` 0.58 → 0.61 to match eldenring 0.14's pin.

## 5. Module base — `detour.rs` (RESOLVED, wired)

`windows::Win32::System::LibraryLoader::GetModuleHandleW(None) -> Result<HMODULE>`;
`HMODULE(pub *mut c_void)`, so base = `hmodule.0 as usize`. Signature stable across windows
0.58–0.62. Source: microsoft.github.io/windows-docs-rs (GetModuleHandleW / HMODULE).
**Bump `Cargo.toml`'s `windows = "0.58"` to `"0.61"`** to match the eldenring pin.

## 6. DllMain — `lib.rs` (already correct; confirmed)

The examples use a raw 2-arg `#[unsafe(no_mangle)] pub unsafe extern "C" fn DllMain(_h: u64,
reason: u32) -> bool` — bail unless `reason == 1` (PROCESS_ATTACH), then `std::thread::spawn` and
block on `wait_for_instance` inside the new thread. No me3-specific entry macro. The current
`lib.rs` matches.

---

## Still open (real RE / impl — NOT symbol lookup)

- **`detour.rs` — AOB scan for `AddItemFunc`.** Still a `current_module_base() + RVA` fallback
  (works only on the pinned 2.6.2.0 exe). Wire to `pelite` (transitive dep of `eldenring`) or
  `patternsleuth` to scan `.text` for `ADD_ITEM_FUNC_AOB`. This is what survives patches.
- **`detour.rs` — `grant_local` itembuf construction.** Build the itembuf descriptor + obtain the
  inventory instance (GameDataMan → PlayerGameData → inventory) before `AddItemHook.call(...)`.
  Still a no-op stub. (Phase 3.)
- **First-run confirmations** (BUILD-NOTES.md §4): rowCount ≈ 3571 / firstRowId 0; pickup id at
  `entry + 0x04`; returning `0` cleanly drops the placeholder.

## Two residual uncertainties to eyeball on the laptop

1. The exact singleton accessor identifier (`instance()` vs a `FromStatic::from_static()` spelling)
   is generated by the `#[shared::singleton(...)]` macro and wasn't pinned to a verbatim source
   line — but the `unsafe` + `Result<&'static Self>` shape is confirmed. The compiler will name the
   right method instantly if `instance()` is off.
2. The resolved `windows` patch version (`0.61.x`) — signature is stable, low risk.
