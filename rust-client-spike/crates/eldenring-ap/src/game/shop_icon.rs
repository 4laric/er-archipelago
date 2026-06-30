//! shop_icon.rs — AP "flower" icon for FOREIGN (and gem/custom) shop slots only.
//!
//! Own-world rewards are rewritten by `shop_sell` to natively sell the real item (correct icon for any
//! type), so this only handles the slots shop_sell can't: FOREIGN items (no ER counterpart) and gem/
//! custom rewards. For those the displayed vanilla good keeps the AP flower — the TELESCOPE's iconId,
//! which me3's VFS menu override repaints to the flower (see er-ap-icon-override).
//!
//! Writes via the crate's mutable param API (instance_mut + get_mut + typed set_icon_id). GLOBAL per
//! good id. Driven by the shopPreviewGoods (loc, good) pairs; idempotent; latches once scout-ready.

#![allow(dead_code)]

use eldenring::cs::{EquipParamGoods, SoloParamRepository};
use fromsoftware_shared::FromStatic;
use std::collections::HashSet;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;

/// EquipParamGoods row id of the Telescope — the iconId me3's flower texture overrides. Read live.
const TELESCOPE_GOOD_ID: u32 = 2040;

static CONFIGURED: Mutex<Vec<(i64, i32)>> = Mutex::new(Vec::new());
static CONFIGURED_SET: AtomicBool = AtomicBool::new(false);
static DONE: AtomicBool = AtomicBool::new(false);

pub fn configure(pairs: Vec<(i64, i32)>) {
    tracing::info!("shop-icon: configured {} shop slot(s)", pairs.len());
    *CONFIGURED.lock().unwrap() = pairs;
    CONFIGURED_SET.store(true, Ordering::Relaxed);
}

pub fn run() -> bool {
    if DONE.load(Ordering::Relaxed) {
        return true;
    }
    if !CONFIGURED_SET.load(Ordering::Relaxed) {
        return false; // wait for slot_data parse (net.rs)
    }
    if !super::scout_proof::cache_ready() {
        return false; // need the scout cache to tell own-world from foreign
    }
    let pairs = CONFIGURED.lock().unwrap().clone();
    if pairs.is_empty() {
        DONE.store(true, Ordering::Relaxed);
        return true;
    }
    // SAFETY: FD4 singleton; game thread, in-world (caller gates).
    let repo = match unsafe { SoloParamRepository::instance_mut() } {
        Ok(r) => r,
        Err(_) => return false, // repo not up yet — retry next tick
    };
    let tele_icon = match repo.get::<EquipParamGoods>(TELESCOPE_GOOD_ID) {
        Some(row) => row.icon_id(),
        None => return false, // telescope row absent — retry
    };
    let (mut flower, mut native) = (0u32, 0u32);
    let mut seen: HashSet<u32> = HashSet::new();
    for (loc, good) in pairs {
        // Own-world sellable rewards display natively (shop_sell rewrote the slot) -> nothing to flower.
        if super::scout_proof::lookup(loc).map(|s| s.er_sell_id.is_some()).unwrap_or(false) {
            native += 1;
            continue;
        }
        let gid = good as u32;
        if !seen.insert(gid) {
            continue; // dedup
        }
        if let Some(row) = repo.get_mut::<EquipParamGoods>(gid) {
            if row.icon_id() != tele_icon {
                row.set_icon_id(tele_icon);
            }
        }
        flower += 1;
    }
    tracing::info!(
        "shop-icon: {flower} foreign/gem slot(s) flowered, {native} own-world handled by shop_sell (telescope iconId {tele_icon})"
    );
    DONE.store(true, Ordering::Relaxed);
    true
}
