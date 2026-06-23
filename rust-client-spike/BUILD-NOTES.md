# BUILD-NOTES — rust-client-spike (laptop side)

How to build, verify, and load the Rust client spike on the Windows dev box. Pairs with
`README.md` (what's here) and `../SPEC-rust-client-port.md` (the plan).

---

## 0. Before you sink weeks into this: coordinate with fswap FIRST

This is the highest-leverage step and the one easiest to skip (per MEMORY: *builds solo,
undershoots outreach — surface EARLY*). The whole value of this port is **converging on the
Rust souls-AP ecosystem**, and that ecosystem is run by other people:

- `fswap/from-software-archipelago-clients` already lists **Elden Ring as PLANNED**. Building the
  ER client entirely solo and *then* showing up risks duplicating work someone's already scoping —
  or diverging from conventions that would block upstreaming. The memory note
  `er-fromsoft-ap-ecosystem.md` has the contacts (nex3 — Mastodon/GitHub; fswap) and the read that
  **Sekiro is the real precedent** to study (a fresh non-DS3 client in their workspace).
- Concrete asks to open the conversation with: *Is anyone working on the ER client yet? Would you
  take it as a workspace member? Which crate factors out the AP protocol / save / loader glue so I
  build on it instead of around it?* (That last one is SPEC §8 decision 3, and the answer
  determines half the architecture.)
- Licensing stays clean on the client side (fswap = MIT, fromsoftware-rs = MIT/Apache-2.0). The
  thefifthmatt landmine is on the **randomizer** fork, not this client — keep them separate (no
  SoulsRandomizers code in here) and the upstreaming door stays open. See
  `er-thefifthmatt-upstream-path.md`.

Do this conversation before phase 3, not after.

---

## 1. Toolchain

```powershell
# rustup with the MSVC target (matches eldenring-rs / fswap; docs.rs builds for
# x86_64-pc-windows-msvc).
rustup default stable
rustup target add x86_64-pc-windows-msvc
rustc --version    # spike was scaffolded against 1.96
```

The pure crates also build with the GNU target and on Linux/macOS — useful for CI.

## 2. Build & test

```powershell
cd <repo>\rust-client-spike

# Pure logic only (fast; the in-process game module is cfg'd out here):
cargo test                       # 14 tests: 7 er-codec, 5 er-semver, 2 eldenring-ap

# The real injected DLL (pulls eldenring / retour / windows; compiles the game module):
cargo build --release --target x86_64-pc-windows-msvc
# -> target\x86_64-pc-windows-msvc\release\eldenring_ap.dll
```

If `cargo` errors with **"failed to remove … Operation not permitted"**, you're building on the
sandbox mount (it blocks unlink — MEMORY `sandbox-mount-no-unlink`). On the laptop this won't
happen; in the sandbox set `CARGO_TARGET_DIR` to a local path (`$env:CARGO_TARGET_DIR="$env:TEMP\er-spike-target"`).

## 3. Resolve the `// VERIFY:` markers (gate for first compile)

The `game/` module is a compile-target sketch. Every spot whose exact symbol/method must be
confirmed against `eldenring` 0.14 is tagged. Find them all:

```powershell
Select-String -Path crates\eldenring-ap\src\game\*.rs -Pattern '// VERIFY:'
```

Checklist (resolve against https://docs.rs/eldenring/0.14.0 — note it documents the MSVC target):

- [ ] `params.rs` — the `ParamDef` "safe param lookup" call: how you get an `EQUIP_PARAM_GOODS_ST`
      row by id, and how to count rows (`spike_log_goods_rowcount`).
- [ ] `params.rs` — field names on `EQUIP_PARAM_GOODS_ST` (`vagrant_item_lot_id`,
      `vagrant_bonus_ene_drop_item_lot_id`, `basic_price`, `sell_value`) and the
      `disable_use_at_out_of_coliseum` bitfield accessor.
- [ ] `detour.rs` — AOB scan for `AddItemFunc` (use `pelite`, already a transitive dep, or
      `patternsleuth`) and `GetModuleHandleW(None)` for the module base (`windows` crate).
- [ ] `detour.rs` — the real grant: build the itembuf descriptor + get the inventory instance
      (GameDataMan → PlayerGameData → inventory) and call `AddItemHook.call(...)`.
- [ ] `flags.rs` — `CSEventFlagMan` get/set and the field-area `PlayRegionId` accessor.
- [ ] `mod.rs` — confirm `CSTaskImp` / `CSTaskGroupIndex` / `FD4TaskData` / `SharedTaskImpExt`
      import paths (taken from the apply-speffect example; should be exact).

## 4. First-run confirmations (from the client repo's `tools/NOTES.md`)

Once it builds and loads:

1. **Phase-1 proof:** `params::spike_log_goods_rowcount()` should log a rowCount near **3571**
   (firstRowId 0). That confirms `fromsoftware-rs` reaches the goods param and the manual ParamBase
   walk is dead. If this works, Strategy B's central assumption holds.
2. **Detour id offset:** log `raw_id` in `add_item_detour` for a few pickups; confirm the id sits at
   `entry + 0x04` (NOTES.md #1).
3. **Suppress drop:** confirm returning `0` from the detour cleanly drops the placeholder
   (NOTES.md #2).

## 5. Loader & deploy

- The DLL self-inits from `DllMain` (worker thread), matching the C++ client's "works under any
  loader" design. The entry uses the **me3 / libraryloader 2-arg convention** from the
  fromsoftware-rs examples. me3 (ModEngine3, Rust) is the primary target.
- For raw OS `LoadLibrary` / ModEngine2 / Elden Mod Loader you need the **3-arg Win32 `DllMain`**
  instead — add it behind a cargo feature if EML/ME2 must keep working (the C++ client supported
  both). Decide this when you pick the loader.
- Deploy: drop the built DLL where your loader expects mod DLLs. The apworld/randomizer lockstep
  (SYNC-RUNBOOK.md) only cares about the DLL name + the `versions` contract — keep
  `CONTRACT_VERSION` (`crates/eldenring-ap/src/lib.rs`) inside the band the apworld emits, and don't
  bump it during the port.

## 6. Git (sandbox vs laptop)

Per MEMORY (`sandbox-mount-no-unlink`, `er-sandbox-git-sync`): the sandbox can't drive git on the
mount and uses HTTPS+PAT (SSH blocked). **Commit and push from the laptop.** Anything generated in
the sandbox is handed over as files, not commits.
