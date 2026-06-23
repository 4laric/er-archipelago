# rust-client-spike

Phase-1 scaffolding for the C++ → Rust client port. See **`../SPEC-rust-client-port.md`** for the
full plan; this directory is the runnable starting point that spec describes (recommendation:
Strategy B with A's pure-contract phases done first).

This is a **spike**, not the final layout — when it graduates, the intended home is a member crate
of a fork of [`fswap/from-software-archipelago-clients`](https://github.com/fswap/from-software-archipelago-clients)
(SPEC §8, decision 1).

## What's here

```
crates/
  er-codec/    PURE. Synthetic-placeholder detection, the sign-safe location-id recombine, and the
               EquipParamGoods row read. Port of er_item_decode.h + er_goods_row.h. #![forbid(unsafe)].
  er-semver/   PURE. node-semver range check with includePrerelease=false (the lockstep `versions`
               gate). Port of er_version_check.h. Deliberately NOT the `semver` crate. #![forbid(unsafe)].
  eldenring-ap/  The injected cdylib SHELL. Pure logic comes from the two crates above.
    src/lib.rs       entry: CONTRACT_VERSION, the semver gate wrapper, the me3-style DllMain.
    src/game/        #[cfg(windows)] in-process layer (compiled out off-Windows):
      mod.rs           worker init + the per-frame task loop (CSTaskImp::run_recurring) that
                       replaces the C++ 2s poll loop.
      detour.rs        DETECT+GRANT: the AddItemFunc detour via retour::static_detour!. Reads the
                       inbound id, delegates the decision to er-codec, suppresses/grants.
      params.rs        DECODE: typed EQUIP_PARAM_GOODS_ST lookup -> er_codec::GoodsRowFields.
                       This is the "delete the binding layer" win — no manual ParamBase walk.
      flags.rs         REPORT: cross-thread check queue (a real channel) + event-flag get/set.
```

> **Status of `game/`:** it is a **compile-target sketch**, written against the real
> `eldenring` 0.14 / `retour` / fromsoftware-rs-examples API — NOT yet built. Lines tagged
> `// VERIFY:` are symbol/method spellings to confirm against docs.rs/eldenring on the laptop
> (e.g. the exact `ParamDef` lookup call, the `CSEventFlagMan` accessor, `GetModuleHandle`). The
> *structure* and the confirmed calls (`CSTaskImp::wait_for_instance` + `run_recurring`, the
> `EQUIP_PARAM_GOODS_ST` struct, `static_detour!`, the me3 `DllMain` shape) are real. It compiles
> out on Linux/macOS, so `cargo test` here still exercises only the pure logic.

## Why the pure crates exist first

`er-codec` and `er-semver` are the parts of the client where a rewrite can **silently corrupt a
live seed** rather than crash (the unsigned-cast recombine, the double `+0x80` param walk decode,
the prerelease-in-range rule). They are ported first, with the exact golden vectors from the C++
`tests/` (`reconcile_test`, `row_test`, `walk_test`, `tests.cpp`), so the contract is locked before
any in-process Rust is written. They build and test on **any** host — no game, no Windows.

## Build & test

The pure crates and the cdylib typecheck on Linux/macOS (Windows deps in `eldenring-ap` are
target-gated and compile out off-Windows):

```sh
cargo test                  # 14 tests: 7 er-codec, 5 er-semver, 2 eldenring-ap
cargo build                 # builds the cdylib shell too (in-process modules cfg'd out)
```

The real DLL build (phase 3+) targets Windows and pulls the gated deps:

```sh
cargo build --release --target x86_64-pc-windows-msvc   # or -gnu
```

> Sandbox note: if `cargo` errors with "failed to remove … Operation not permitted", the build is
> running on a mount that blocks artifact deletion. Set `CARGO_TARGET_DIR` to a local path
> (`export CARGO_TARGET_DIR=/tmp/er-spike-target`) and re-run.

## Next steps (from SPEC §4)

1. **Phase-1 spike proper:** wire `eldenring-ap::game::spike_log_goods_rowcount` to
   `fromsoftware-rs`'s `SoloParamRepository`, build the DLL, load it under me3/ME2, and confirm it
   logs `rowCount=3571 firstRowId=0` (tools/NOTES.md). This validates the one assumption the whole
   strategy rests on — that the crates expose the goods param.
2. **Phase 3:** implement the four jobs (detour via `retour`, decode via `er-codec`, report via
   `CSEventFlagMan`) for a goods-only end-to-end seed.
3. **Phase 5:** port the ER feature surface one SPEC/flag at a time (the long tail).
