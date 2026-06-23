//! REPORT layer — getting checks to the AP server, and event-flag read/set.
//!
//! Two jobs that were `CSEventFlagMan` + the protocol layer in C++:
//!   1. A check was observed (in the detour) -> hand its AP location id to the network thread.
//!   2. Detect checks whose acquisition BYPASSES the detour (shop buys, NPC gifts, offline
//!      pickups) by polling each location's guarding event flag (apconfig.json "location_flags"),
//!      and set collected/grace/region flags (region fusion, map reveal, DLC-entry warps, ...).
//!
//! ⚠️ COMPILE-TARGET SKETCH. `// VERIFY:` marks the `eldenring` symbol to confirm.

use std::sync::mpsc::{Receiver, SyncSender};
use std::sync::OnceLock;

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
pub fn get_event_flag(_flag_id: u32) -> bool {
    // VERIFY: `eldenring::cs::CSEventFlagMan` (or the crate's flag accessor) get. The C++ resolved
    // GetEventFlag (RVA 0x5F9400) + the flag-holder global; the crate should wrap this.
    false
}

/// Set an event flag. Idempotent + game-save-persisted, so re-running on reconnect/replay is
/// harmless (the C++ relied on exactly this for grace/region/map-reveal flags).
#[allow(dead_code)]
pub fn set_event_flag(_flag_id: u32, _enabled: bool) {
    // VERIFY: CSEventFlagMan set (C++ EventFlag_SetGet RVA 0x5D2110).
    tracing::debug!("TODO set_event_flag");
}

/// Player's current `PlayRegionId` (region-lock physical enforcement), or `None` if not in-world.
/// C++ read `FieldArea + 0xE4`; the crate exposes this via the field-area singleton.
#[allow(dead_code)]
pub fn play_region_id() -> Option<i32> {
    // VERIFY: field-area singleton + PlayRegionId accessor.
    None
}
