//! In-process / Windows-only glue for the ER Archipelago client.
//!
//! ⚠️ COMPILE-TARGET SKETCH, not yet built. The structure and the *confirmed* API calls
//! (`CSTaskImp::wait_for_instance` + `run_recurring`, the me3 `DllMain` shape, the
//! `EQUIP_PARAM_GOODS_ST` param struct, `retour`'s `static_detour!`) are taken from the real
//! `eldenring` 0.14 docs + the fromsoftware-rs examples. Anything tagged `// VERIFY:` is a symbol
//! name or method whose exact spelling must be confirmed against docs.rs/eldenring before this
//! compiles. Build it on the Windows laptop (`cargo build --target x86_64-pc-windows-msvc`).
//!
//! This module replaces, in one place, what the C++ client spread across `er_hooks.h`,
//! `er_singletons.h`, `er_gamehook_win.cpp`, and the `mem`/`minhook`/`fd4_singleton` subprojects.
//! The *decisions* (what counts as synthetic, how to recombine the location id, grant-vs-suppress)
//! stay in the pure, host-tested `er_codec` crate — this module only does the unsafe I/O.

mod detour;
mod flags;
mod params;

use std::time::Duration;

// VERIFY: exact paths. From the apply-speffect example these live under `eldenring::cs` and
// `eldenring::fd4`; `FromStatic`/task ext traits come from `fromsoftware_shared`.
use eldenring::cs::{CSTaskGroupIndex, CSTaskImp};
use eldenring::fd4::FD4TaskData;
use fromsoftware_shared::SharedTaskImpExt;

/// Worker-thread entry, spawned from `DllMain`. Mirrors the C++ `CCore::on_attach` + `Run` loop,
/// but instead of a 2s sleep loop it registers a per-frame task (the idiomatic fromsoftware-rs
/// pattern) — strictly better than `RUN_SLEEP=2000` for pickup latency and flag polling.
pub fn init() {
    init_logging();
    tracing::info!("eldenring-ap {}: worker thread up", crate::CONTRACT_VERSION);

    // Phase-1 spike payoff: prove the crate exposes the goods param before anything else.
    params::spike_log_goods_rowcount();

    // DETECT/GRANT: install the AddItemFunc detour once. (er_gamehook_win.cpp Init())
    if let Err(e) = detour::install() {
        tracing::error!("AddItemFunc detour install failed: {e}");
        return;
    }

    // The settled in-world tick. Everything that must run on the game thread goes here: draining
    // the received-items / grant / grace-flag queues, polling location flags (REPORT for
    // acquisitions that bypass the detour), evaluating natural-key triggers, etc. (SPEC §4 phase 5)
    let cs_task = match CSTaskImp::wait_for_instance(Duration::MAX) {
        Ok(t) => t,
        Err(e) => {
            tracing::error!("no CSTaskImp: {e:?}");
            return;
        }
    };
    cs_task.run_recurring(
        |_: &FD4TaskData| {
            tick();
        },
        CSTaskGroupIndex::FrameBegin,
    );

    // TODO(phase 4): spawn the AP networking thread here (connect, poll, items_received ->
    // received-items queue, LocationChecks <- the report queue). Kept off the game thread.
}

/// One settled-in-world game tick. No-op until the queues exist (phase 4/5).
fn tick() {
    // TODO(phase 5): drain report queue -> set collected flags; drain received-items queue ->
    // grant via params/detour; flush pending grace/open flags; evaluate natural-key triggers.
}

fn init_logging() {
    // Replaces spdlog: a file + (optional) console sink. tracing_subscriber init is idempotent-ish;
    // guard against double-init if the loader attaches twice.
    let _ = tracing_subscriber::fmt()
        .with_max_level(tracing::Level::DEBUG)
        .try_init();
}
