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

use std::collections::HashSet;
use std::sync::mpsc::{Receiver, SyncSender};
use std::sync::{Mutex, OnceLock};

use eldenring::cs::{CSEventFlagMan, WorldChrMan};
use er_logic::location_check::LocationChecks;
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

// --- pure-runtime (no-baker) location-check detection (er_logic::location_check) ------------------
//
// The pure-runtime loop polls vanilla ACQUISITION flags emitted in slot_data (`locationFlags`)
// rather than relying on the apconfig `location_flags` bake or the synthetic-carrier detour. The
// pure decision table (`LocationChecks`) lives in `er-logic` (host-tested); this is just the holder
// + the game-thread poll seam, parallel to the ReportChannel above. Built once at connect (net.rs)
// and ticked on the game thread (mod.rs), beside the region-lock poll.

/// The connect-built detection table. `None` until `configure_location_checks` runs.
fn location_checks() -> &'static Mutex<Option<LocationChecks>> {
    static LC: OnceLock<Mutex<Option<LocationChecks>>> = OnceLock::new();
    LC.get_or_init(|| Mutex::new(None))
}

/// Called from the net thread at CONNECT: install the slot_data `locationFlags` detection table,
/// optionally primed with the server's already-checked locations so a reconnect mid-run doesn't
/// re-report. Replaces the table on every (re)connect — `LocationChecks` carries its own per-session
/// `fired` set, so a fresh connect re-primes cleanly.
#[allow(dead_code)]
pub fn configure_location_checks(mut lc: LocationChecks, already_checked: &HashSet<i64>) {
    if !already_checked.is_empty() {
        lc.prime_checked(already_checked);
    }
    *location_checks().lock().unwrap() = Some(lc);
}

/// Called from the game tick (mod.rs), beside the region-lock poll: poll the pure detection table
/// against live acquisition flags and enqueue every newly-completed AP location id onto the report
/// channel (the net thread drains it via `drain_reported` -> `mark_checked`). No-op until configured.
/// `in_world` is the same source the region-lock poll uses (`flags::in_world()`).
pub fn poll_location_checks(in_world: bool) {
    let mut guard = location_checks().lock().unwrap();
    let Some(lc) = guard.as_mut() else { return };
    let newly = lc.poll(in_world, &get_event_flag);
    drop(guard); // release the lock before report_location (which takes the channel lock)
    for loc in newly {
        #[cfg(feature = "net")]
        notify_sent(loc);
        report_location(loc);
    }
}

/// On a newly-completed check, if the item there goes to ANOTHER player, print "Sent X -> Player" to
/// the console overlay (the pure-runtime legibility win — flag-routed sends are otherwise invisible).
/// Own-world pickups are skipped (you can see what you grabbed). No-op until the scout cache is filled.
#[cfg(feature = "net")]
fn notify_sent(loc: i64) {
    if let Some(s) = super::scout_proof::lookup(loc) {
        if s.foreign {
            super::console::notify(&format!("Sent {} -> {} [{}]", s.name, s.owner, s.kind.label()));
        }
    }
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
