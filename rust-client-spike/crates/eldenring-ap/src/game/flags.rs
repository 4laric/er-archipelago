//! REPORT layer — getting checks to the AP server, and event-flag read/set.
//!
//! Two jobs that were `CSEventFlagMan` + the protocol layer in C++:
//!   1. A check was observed (in the detour) -> hand its AP location id to the network thread.
//!   2. Detect checks whose acquisition BYPASSES the detour (shop buys, NPC gifts, offline
//!      pickups) by polling each location's guarding event flag (apconfig.json "location_flags"),
//!      and set collected/grace/region flags (region fusion, map reveal, DLC-entry warps, ...).
//!
//! ⚠️ COMPILE-TARGET SKETCH (not yet built). Symbols RESOLVED against eldenring 0.14 —
//! see the spike root's VERIFY-RESOLUTION.md. The flag get/set + region-id accessors below are wired.

use std::sync::mpsc::{Receiver, SyncSender};
use std::sync::OnceLock;

use eldenring::cs::{CSEventFlagMan, WorldChrMan};
use fromsoftware_shared::FromStatic;

/// Bounded queue of AP location ids observed on the game thread, drained by the network thread and
/// sent as `LocationChecks`. Mirrors the C++ cross-thread `checkedLocationsList`, but a real
/// channel instead of a no-lock shared vec (removes a latent race the C++ comments hand-wave).
struct ReportChannel {
    tx: SyncSender<i64>,
    rx: std::sync::Mutex<Receiver<i64>>,
}

fn channel() -> &'static ReportChannel {
    static CH: OnceLock<ReportChannel> = OnceLock::new();
    CH.get_or_init(|| {
        let (tx, rx) = std::sync::mpsc::sync_channel(4096);
        ReportChannel {
            tx,
            rx: std::sync::Mutex::new(rx),
        }
    })
}

/// Called from the detour (game thread): enqueue a check. Never blocks the game; drops with a warn
/// if the queue is somehow full (network thread wedged).
pub fn report_location(ap_location_id: i64) {
    if channel().tx.try_send(ap_location_id).is_err() {
        tracing::warn!("report queue full; dropped location {ap_location_id}");
    }
}

/// Called from the network thread: drain everything observed since last poll, to batch into one
/// `LocationChecks`.
#[allow(dead_code)]
pub fn drain_reported() -> Vec<i64> {
    let rx = channel().rx.lock().unwrap();
    rx.try_iter().collect()
}

// --- event flags (er_hooks.h EventFlag_* / er_singletons.h CSEventFlagMan) ------------------------

/// Read an event flag (true = set). Used to detect detour-bypassing acquisitions and as the
/// region/natural-key latch. Safe before the flag holder initializes: returns false.
#[allow(dead_code)]
pub fn get_event_flag(flag_id: u32) -> bool {
    // RESOLVED: get/set live on `CSEventFlagMan.virtual_memory_flag` (type CSFD4VirtualMemoryFlag),
    // taking `impl Into<EventFlag>` (a u32 auto-converts) — NOT a `get_event_flag` on the manager.
    // Returns false before the manager initializes.
    match unsafe { CSEventFlagMan::instance() } {
        Ok(m) => m.virtual_memory_flag.get_flag(flag_id),
        Err(_) => false,
    }
}

/// Set an event flag. Idempotent + game-save-persisted, so re-running on reconnect/replay is
/// harmless (the C++ relied on exactly this for grace/region/map-reveal flags).
#[allow(dead_code)]
pub fn set_event_flag(flag_id: u32, enabled: bool) {
    let _ = try_set_event_flag(flag_id, enabled);
}

/// Set an event flag, returning whether the flag HOLDER was ready (true = set, false = retry later).
/// Phase 5's FlushPendingGraceFlags / revealAllMaps need this: a flag set before CSEventFlagMan is
/// up is silently dropped by new-game init, so the queue must re-try until the holder exists
/// (mirrors the C++ `SetEventFlag` BOOL return). Idempotent + save-persisted once it does land.
#[allow(dead_code)]
pub fn try_set_event_flag(flag_id: u32, enabled: bool) -> bool {
    // RESOLVED: `set_flag(impl Into<EventFlag>, bool)` on the virtual_memory_flag.
    match unsafe { CSEventFlagMan::instance_mut() } {
        Ok(m) => {
            m.virtual_memory_flag.set_flag(flag_id, enabled);
            true
        }
        Err(_) => {
            tracing::debug!("set_event_flag({flag_id}, {enabled}): CSEventFlagMan not up yet");
            false
        }
    }
}

/// Player's current `PlayRegionId` (region-lock physical enforcement), or `None` if not in-world.
/// C++ read `FieldArea + 0xE4`; the crate exposes this via the field-area singleton.
#[allow(dead_code)]
pub fn play_region_id() -> Option<i32> {
    // RESOLVED: there is NO CSFieldArea region accessor. Current region =
    // WorldChrMan.main_player -> PlayerIns.play_region_id (u32). None if not in-world.
    let wcm = unsafe { WorldChrMan::instance() }.ok()?;
    Some(wcm.main_player.as_ref()?.play_region_id as i32)
}

/// True once the player is loaded into the world (WorldChrMan.main_player present). Used to gate
/// param-table access: at the first frames during boot the params aren't populated and iterating
/// EquipParamGoods faults, but in-world they are guaranteed loaded.
pub fn in_world() -> bool {
    play_region_id().is_some()
}
