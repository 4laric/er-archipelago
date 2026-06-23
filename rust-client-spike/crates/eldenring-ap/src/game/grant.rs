//! Phase 4 — server-pushed item GRANT queue + `last_received_index` persistence.
//!
//! The `AddItemFunc` detour (detour.rs) grants LOCAL self-found pickups by rewriting the descriptor
//! in place. Items the SERVER sends (`items_received`) never pass through a pickup, so they must be
//! granted by CONSTRUCTING an itembuf and calling the original AddItemFunc — `detour::grant_full_id`.
//!
//! Threading: the AP net thread (net.rs) `enqueue()`s decoded items; the FrameBegin game tick calls
//! `drain_and_grant()`, which is the ONLY place that touches game inventory. Mirrors the C++
//! ItemRandomiser `receivedItemsQueue` + `CGameHook::GiveNextItem` + `CCore::WriteSaveFile`.
//!
//! Persistence (single-owner = game thread): `PERSIST_INDEX` is the highest received-item index that
//! has actually been GRANTED, written to `archipelago/<seed>_<slot>.json` after each grant. The net
//! thread READS this file once at (re)connect to know where to resume, so a crash before a grant
//! replays the item on reconnect (no double-grant, no loss) — the server re-sends everything under
//! items_handling 0b111.

use std::collections::VecDeque;
use std::path::PathBuf;
use std::sync::atomic::{AtomicI64, Ordering};
use std::sync::mpsc::{Receiver, SyncSender};
use std::sync::{Mutex, OnceLock};

use super::detour;
use super::flags;

/// One server-pushed item to grant in-game.
pub struct GrantMsg {
    /// ER FullID (real item id | category nibble) — already category-tagged by the apworld map.
    pub full_id: i32,
    pub qty: i32,
    /// Global received-item index (the persisted dedup watermark).
    pub ap_index: i64,
    /// AP item name (logging today; on-screen notifications are Phase 5 / open-piece 3).
    pub name: String,
}

struct GrantChannel {
    tx: SyncSender<GrantMsg>,
    rx: Mutex<Receiver<GrantMsg>>,
}

fn channel() -> &'static GrantChannel {
    static CH: OnceLock<GrantChannel> = OnceLock::new();
    CH.get_or_init(|| {
        let (tx, rx) = std::sync::mpsc::sync_channel(4096);
        GrantChannel { tx, rx: Mutex::new(rx) }
    })
}

/// Items popped off the channel but not yet granted (inventory pointer not captured yet). The game
/// thread is the only accessor; held so nothing is lost while we wait for the player's first pickup.
fn pending() -> &'static Mutex<VecDeque<GrantMsg>> {
    static P: OnceLock<Mutex<VecDeque<GrantMsg>>> = OnceLock::new();
    P.get_or_init(|| Mutex::new(VecDeque::new()))
}

static SAVE_PATH: OnceLock<PathBuf> = OnceLock::new();
/// Highest received-item index GRANTED in-game (persisted). -1 = not configured (pre-connect).
static PERSIST_INDEX: AtomicI64 = AtomicI64::new(-1);

/// net thread: enqueue a server-pushed item for the game thread to grant. Never blocks the net loop.
pub fn enqueue(msg: GrantMsg) {
    if channel().tx.try_send(msg).is_err() {
        tracing::warn!("grant queue full; dropped a received item (game tick wedged?)");
    }
}

/// net thread, at (re)connect: record the per-seed save path and the resume index loaded from it.
pub fn configure(save_path: PathBuf, start_index: i64) {
    let _ = SAVE_PATH.set(save_path); // first connect wins; reconnects reuse the same path
    PERSIST_INDEX.store(start_index, Ordering::Relaxed);
}

/// The highest received-item index granted so far (the net thread's resume watermark mirror).
pub fn persisted_index() -> i64 {
    PERSIST_INDEX.load(Ordering::Relaxed)
}

/// Game thread (FrameBegin tick): grant queued items. Gated on in-world AND a captured inventory
/// pointer; un-grantable items stay queued (no index advance => no data loss within a session).
pub fn drain_and_grant() {
    if PERSIST_INDEX.load(Ordering::Relaxed) < 0 {
        return; // not connected / slot_data not parsed yet
    }
    if !flags::in_world() {
        return; // params/inventory not loaded; the detour hasn't captured an inventory pointer
    }

    let mut q = pending().lock().unwrap();
    // Move everything currently in the channel into the ordered pending buffer.
    {
        let rx = channel().rx.lock().unwrap();
        for msg in rx.try_iter() {
            q.push_back(msg);
        }
    }
    if q.is_empty() {
        return;
    }

    let mut advanced = false;
    while let Some(msg) = q.front() {
        // Defensive replay dedup (the net thread already filters, but be safe across reconnects).
        if msg.ap_index < PERSIST_INDEX.load(Ordering::Relaxed) {
            q.pop_front();
            continue;
        }
        // Logic-only region-lock keys carry sentinel er_code 99999/99998 and have no real param row;
        // granting them would hand the game a nonexistent goods row. Skip the grant, advance the
        // index (so they don't replay). Mirrors CGameHook::GiveNextItem.
        let row = (msg.full_id as u32) & 0x0FFF_FFFF;
        let granted = if row == 99_999 || row == 99_998 {
            tracing::info!("received sentinel item '{}' (no in-game grant)", msg.name);
            true
        } else {
            detour::grant_full_id(msg.full_id, msg.qty)
        };

        if !granted {
            // No inventory pointer captured yet (no pickup this session). Leave THIS and the rest
            // queued and retry next tick — do NOT advance the persisted index.
            break;
        }

        tracing::info!(
            "granted received item '{}' (FullID {:#010x} x{})",
            msg.name,
            msg.full_id as u32,
            msg.qty
        );
        let new_idx = msg.ap_index + 1;
        if new_idx > PERSIST_INDEX.load(Ordering::Relaxed) {
            PERSIST_INDEX.store(new_idx, Ordering::Relaxed);
            advanced = true;
        }
        q.pop_front();
    }
    drop(q);

    if advanced {
        write_save();
    }
}

/// Persist `{"last_received_index": N}` atomically (write `.swap`, then rename) so a crash/quit can't
/// orphan the index. Mirrors CCore::WriteAtomic + WriteSaveFile.
fn write_save() {
    let path = match SAVE_PATH.get() {
        Some(p) => p,
        None => return,
    };
    let idx = PERSIST_INDEX.load(Ordering::Relaxed);
    let body = format!("{{\"last_received_index\": {}}}", idx);

    let mut swap_os = std::ffi::OsString::from(path.as_os_str());
    swap_os.push(".swap");
    let swap = PathBuf::from(swap_os);

    if std::fs::write(&swap, body.as_bytes()).is_err() {
        tracing::warn!("save write failed: {:?}", swap);
        return;
    }
    if let Err(e) = std::fs::rename(&swap, path) {
        tracing::debug!("save rename failed ({e}); falling back to direct write");
        let _ = std::fs::write(path, body.as_bytes());
    }
}
