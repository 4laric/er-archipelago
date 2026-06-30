//! In-process / Windows-only glue for the ER Archipelago client.
//!
//! ⚠️ COMPILE-TARGET SKETCH, not yet built. The structure and the *confirmed* API calls
//! (`CSTaskImp::wait_for_instance` + `run_recurring`, the me3 `DllMain` shape, the
//! `EQUIP_PARAM_GOODS_ST` param struct, `retour`'s `static_detour!`) are taken from the real
//! `eldenring` 0.14 docs + the fromsoftware-rs examples. Symbol spellings are now RESOLVED (see
//! the spike root's VERIFY-RESOLUTION.md); what remains before this compiles is the AOB scan + grant
//! construction in detour.rs. Build it on the Windows laptop (`cargo build --target x86_64-pc-windows-msvc`).
//!
//! This module replaces, in one place, what the C++ client spread across `er_hooks.h`,
//! `er_singletons.h`, `er_gamehook_win.cpp`, and the `mem`/`minhook`/`fd4_singleton` subprojects.
//! The *decisions* (what counts as synthetic, how to recombine the location id, grant-vs-suppress)
//! stay in the pure, host-tested `er_codec` crate — this module only does the unsafe I/O.

// This in-process module is the one place unsafe FFI lives (FD4 singleton access, the detour, raw
// reads). The crate lint warns on `unsafe` to keep the pure shell clean; allow it HERE, where it's
// expected and reviewed (matches the Cargo.toml intent). `dead_code` is allowed while the phase 3-5
// feature surface is still being wired — handlers exist before their callers do; drop it once wired.
#![allow(unsafe_code, dead_code)]

#[cfg(feature = "detour")]
mod console;
#[cfg(feature = "detour")]
mod detour;
mod flags;
mod params;

// Phase 4 (AP networking). `net` implies `detour` (grants reuse the detour trampoline), so both
// modules are present together. Off-by-default; build with `--features net`.
#[cfg(feature = "net")]
mod deathlink;
#[cfg(feature = "net")]
mod features;
#[cfg(feature = "net")]
mod grant;
#[cfg(feature = "net")]
mod net;
#[cfg(feature = "net")]
mod scout_proof; // STEP 0 pre-scout proof (shop-preview data half); driven from net.rs
#[cfg(feature = "net")]
mod lookupentry_probe; // STEP A diagnostic: logging detour on MsgRepositoryImp::LookupEntry (inert until RVA pinned)
#[cfg(feature = "net")]
mod fmg_probe; // FMG-edit gate sub-step A: READ-ONLY dump of the MsgRepository structure (no writes)
#[cfg(feature = "net")]
mod fmg_inject; // FMG entry injection (staged): name synthetic AP goods by rebuilding GoodsName MsgData
#[cfg(feature = "net")]
mod progressive;
#[cfg(feature = "net")]
mod upgrades;

use std::time::Duration;

// RESOLVED (apply-speffect example + docs.rs 0.14): CSTaskImp/CSTaskGroupIndex in `eldenring::cs`,
// FD4TaskData in `eldenring::fd4`, SharedTaskImpExt re-exported at the `fromsoftware_shared` root.
// `wait_for_instance` is a blocking INHERENT method on CSTaskImp (takes Duration, returns Result);
// `run_recurring` is the ext-trait method and returns a handle that MUST be kept alive (see below).
use eldenring::cs::{CSTaskGroupIndex, CSTaskImp};
use eldenring::fd4::FD4TaskData;
use fromsoftware_shared::SharedTaskImpExt;

/// Worker-thread entry, spawned from `DllMain`. Mirrors the C++ `CCore::on_attach` + `Run` loop,
/// but instead of a 2s sleep loop it registers a per-frame task (the idiomatic fromsoftware-rs
/// pattern) — strictly better than `RUN_SLEEP=2000` for pickup latency and flag polling.
/// Crash-forensic breadcrumb: append one line to `<logs>/eldenring-ap_<ts>.trace.log` and fsync it,
/// so the LAST step before a hard crash is guaranteed on disk (the non-blocking tracing sink can
/// lose un-flushed lines when `panic = "abort"` tears the process down). Per-launch timestamped name
/// so it is always a fresh path, readable through the dev mount.
fn breadcrumb(step: &str) {
    use std::io::Write;
    static PATH: std::sync::OnceLock<std::path::PathBuf> = std::sync::OnceLock::new();
    let path = PATH.get_or_init(|| {
        let dir = std::env::var("ER_AP_LOG_DIR").ok().unwrap_or_else(|| {
            let mut p = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"));
            p.pop();
            p.pop();
            p.push("logs");
            p.to_string_lossy().into_owned()
        });
        let _ = std::fs::create_dir_all(&dir);
        std::path::Path::new(&dir).join(format!("eldenring-ap_{}.trace.log", crate::log_timestamp()))
    });
    if let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open(path) {
        let _ = writeln!(f, "{step}");
        let _ = f.flush();
        let _ = f.sync_all();
    }
}

pub fn init() {
    breadcrumb("init: start");
    let _log_guard = init_logging();
    breadcrumb("init: logging ready");
    tracing::info!("eldenring-ap {}: worker thread up", crate::CONTRACT_VERSION);

    // The Phase-1 spike (goods rowCount) runs on the first IN-WORLD tick (see tick()), NOT here:
    // at PROCESS_ATTACH the SoloParamRepository global is uninitialized, so touching it this early
    // faults and (panic=abort) crashes the game during boot.

    // DETECT/GRANT: install the AddItemFunc detour (Phase 3; `detour` feature, now default + stable).
    // BEST-EFFORT: if the pinned RVA is stale for this game build the signature guard refuses to
    // install — log and CONTINUE so the Phase-1 probe and the rest of init still run.
    #[cfg(feature = "detour")]
    if let Err(e) = detour::install() {
        breadcrumb("init: detour install failed (continuing without it)");
        tracing::error!("AddItemFunc detour install failed: {e}");
    }

    // STEP A diagnostic (shop previews Part 3 gate): logging-only detour on LookupEntry. INERT until
    // LOOKUP_ENTRY_RVA/SIG are pinned (returns Ok without installing), so this is a no-op for normal
    // builds. BEST-EFFORT, same as the detour above. See STEP-A-RUNBOOK.md / SPEC-lookupentry-spike.md.
    #[cfg(feature = "net")]
    if let Err(e) = lookupentry_probe::install() {
        breadcrumb("init: LE-probe install failed (continuing without it)");
        tracing::error!("LookupEntry probe install failed: {e}");
    }

    // Debug console (ports the C++ client's /setflag, /getflag window). Reads stdin on its own thread;
    // commands execute on the game tick (console::tick). Behind `detour` (needs the windows crate).
    #[cfg(feature = "detour")]
    console::init();

    // The settled in-world tick. Everything that must run on the game thread goes here: draining
    // the received-items / grant / grace-flag queues, polling location flags (REPORT for
    // acquisitions that bypass the detour), evaluating natural-key triggers, etc. (SPEC §4 phase 5)
    breadcrumb("init: before wait_for_instance(CSTaskImp)");
    let cs_task = match CSTaskImp::wait_for_instance(Duration::MAX) {
        Ok(t) => {
            breadcrumb("init: CSTaskImp ready");
            t
        }
        Err(e) => {
            breadcrumb("init: CSTaskImp ERR (returning)");
            tracing::error!("no CSTaskImp: {e:?}");
            return;
        }
    };
    // RESOLVED: run_recurring returns a RecurringTaskHandle that unregisters the per-frame task when
    // dropped — so it MUST be held for the process lifetime (the sketch previously dropped it).
    breadcrumb("init: before run_recurring(FrameBegin)");
    let _task_handle = cs_task.run_recurring(
        |_: &FD4TaskData| {
            tick();
        },
        CSTaskGroupIndex::FrameBegin,
    );
    breadcrumb("init: run_recurring registered; parking worker thread");

    // Phase 4: run the AP networking loop on THIS worker thread (off the game thread): connect,
    // poll archipelago_rs, drain the report queue -> LocationChecks, push received items onto the
    // grant queue the FrameBegin tick drains. Running it here (not a fresh thread) keeps the
    // FrameBegin registration `_task_handle` alive for free — net::run() never returns.
    #[cfg(feature = "net")]
    {
        breadcrumb("init: entering AP net loop (worker thread)");
        net::run();
    }

    // Lean detour-only / --no-default-features build: just park the worker thread so `_task_handle`
    // (the FrameBegin task) stays alive for the process lifetime.
    #[cfg(not(feature = "net"))]
    loop {
        std::thread::sleep(Duration::from_secs(60));
    }
}

/// One settled-in-world game tick. No-op until the queues exist (phase 4/5).
fn tick() {
    use std::sync::atomic::{AtomicBool, Ordering};

    // One-shot: lets us tell "crashed before any frame" (task setup) from "crashed in the param
    // probe" (the spike below).
    static FIRST_FRAME: AtomicBool = AtomicBool::new(true);
    if FIRST_FRAME.swap(false, Ordering::Relaxed) {
        breadcrumb("tick: first frame reached");
    }

    // Phase-1 proof: log the goods rowCount once we are IN-WORLD. Gating on WorldChrMan.main_player
    // (not merely "a frame ran") is the fix for the boot-time crash: at the first frames the param
    // tables aren't populated and iterating EquipParamGoods faults; in-world they are loaded.
    static SPIKE_DONE: AtomicBool = AtomicBool::new(false);
    static PROBE_ANNOUNCED: AtomicBool = AtomicBool::new(false);
    if !SPIKE_DONE.load(Ordering::Relaxed) && flags::in_world() {
        if !PROBE_ANNOUNCED.swap(true, Ordering::Relaxed) {
            breadcrumb("tick: in-world; probing SoloParamRepository");
        }
        if params::spike_log_goods_rowcount() {
            breadcrumb("tick: spike resolved (rowCount logged)");
            SPIKE_DONE.store(true, Ordering::Relaxed);
        }
    }

    // FMG-edit gate sub-step A: dump the MsgRepository structure ONCE, read-only (no writes), to
    // confirm the live layout before designing the in-memory string edit. See fmg_probe.rs / spec §2.4.
    #[cfg(feature = "net")]
    {
        static FMG_DUMP_DONE: AtomicBool = AtomicBool::new(false);
        if !FMG_DUMP_DONE.load(Ordering::Relaxed) && flags::in_world() && fmg_probe::dump_repo() {
            FMG_DUMP_DONE.store(true, Ordering::Relaxed);
        }
        // FMG injection (staged): Stage 1 = parse + validate GoodsName MsgData (read-only).
        static FMG_INJECT_DONE: AtomicBool = AtomicBool::new(false);
        if !FMG_INJECT_DONE.load(Ordering::Relaxed) && flags::in_world() && fmg_inject::run() {
            FMG_INJECT_DONE.store(true, Ordering::Relaxed);
        }
    }

    // Phase 4: drain the received-items queue (filled by the AP net thread) and grant each item
    // in-game on THIS thread, where touching inventory is safe; persists last_received_index after
    // each grant. Gated on in-world inside drain_and_grant().
    // Phase 5: execute any queued debug-console commands (/setflag, /getflag, ...) on the game thread.
    #[cfg(feature = "detour")]
    console::tick();

    #[cfg(feature = "net")]
    grant::drain_and_grant();

    // Phase 4: ending_condition 0/1 GOAL detection — poll the boss defeat flag HERE (event-flag
    // reads are only safe on the game thread) and tell the net loop to send CLIENT_GOAL once.
    #[cfg(feature = "net")]
    {
        let gf = net::goal_flag();
        if gf != 0 && flags::get_event_flag(gf) {
            net::signal_goal();
        }
    }

    // Phase 5: the settled-in-world feature tick — flush pending grace/open/reveal flags, grant
    // queued notify + start items, reveal maps, evaluate natural-key triggers, poll location flags
    // (detour-bypassing acquisitions -> report queue), and run the warp / region-lock latches. All
    // event-flag reads/writes + grants happen HERE (game thread); the net thread only queued them.
    #[cfg(feature = "net")]
    features::tick();

    // Pure-runtime (no-baker) location-check poll: detect AP checks by polling the vanilla
    // ACQUISITION flags emitted in slot_data (`locationFlags`) and report each newly-completed
    // location id. Runs beside the region-lock poll (features::tick) on the SAME `in_world` source,
    // and is a cheap no-op until net.rs configures the table at connect (configure_location_checks).
    // This is the detour-bypass path for the vanilla-placement MVP; the synthetic-carrier detour and
    // the apconfig `location_flags` poll (features::poll_location_flags) remain as parallel paths.
    #[cfg(feature = "net")]
    flags::poll_location_checks(flags::in_world());

    // Phase 5 parallel tracks: progressive bells/physick grant+flag drain (Wave C), DeathLink
    // kill/death latches (Wave D, RE-gated), and the global Scadutree blessing writer (RE-gated).
    // Each self-gates (off unless its slot_data flag is set / in-world), so all three are cheap no-ops.
    #[cfg(feature = "net")]
    progressive::tick();
    #[cfg(feature = "net")]
    deathlink::tick();
    #[cfg(feature = "net")]
    upgrades::tick_global_scadu();
}

/// Set up file logging (replaces spdlog with a non-blocking tracing file sink).
///
/// Writes `<spike>/logs/eldenring-ap_<YYYYMMDD_HHMMSS>.log`. The dir is derived from
/// CARGO_MANIFEST_DIR at build time (overridable with $ER_AP_LOG_DIR). A fresh timestamped name per
/// launch means the file is always a NEW path — readable straight off the (otherwise stale-cached)
/// dev mount, and it never clobbers a prior run. Returns the `WorkerGuard`, which the caller MUST
/// keep alive for the process lifetime or the background writer thread shuts down and lines are lost.
fn init_logging() -> Option<tracing_appender::non_blocking::WorkerGuard> {
    let dir = std::env::var("ER_AP_LOG_DIR").ok().unwrap_or_else(|| {
        let mut p = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")); // <spike>\crates\eldenring-ap
        p.pop(); // <spike>\crates
        p.pop(); // <spike>
        p.push("logs");
        p.to_string_lossy().into_owned()
    });
    if std::fs::create_dir_all(&dir).is_err() {
        // Never panic on the loader thread: fall back to the default (stdout) subscriber.
        let _ = tracing_subscriber::fmt().with_max_level(tracing::Level::DEBUG).try_init();
        return None;
    }
    let filename = format!("eldenring-ap_{}.log", crate::log_timestamp());
    let appender = tracing_appender::rolling::never(&dir, &filename);
    let (writer, guard) = tracing_appender::non_blocking(appender);
    let _ = tracing_subscriber::fmt()
        .with_writer(writer)
        .with_ansi(false)
        .with_max_level(tracing::Level::DEBUG)
        .try_init();
    tracing::info!("log file: {}\\{}", dir, filename);
    Some(guard)
}
