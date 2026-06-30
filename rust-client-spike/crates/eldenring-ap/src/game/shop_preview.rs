//! shop_preview.rs — name/description override for FOREIGN (and gem/custom) shop slots only.
//!
//! Own-world rewards are rewritten by `shop_sell` to natively sell the real item (correct name + lore
//! + icon), so this only handles the slots shop_sell can't: FOREIGN items (no ER counterpart) and gem/
//! custom rewards. For those the displayed vanilla good's FMG name + info + caption are overwritten with
//! the AP routing block ("AP: <item> / For: <owner> (<game>) / <kind>").
//!
//! Mechanism: EXTEND-SWAP via fmg_inject::extend_swap_overrides (rebuilds the category block from the
//! LIVE pointer so any length fits; validated before the atomic swap). Runs AFTER fmg_inject. The
//! override is GLOBAL per good id, so we dedup by good id (the shared FMG entry shows one reward).

#![allow(dead_code)]

use std::collections::HashMap;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;

const GOODS_NAME_CAT: u32 = 10;
const GOODS_INFO_CAT: u32 = 20; // the "Item Effect" line the buy menu renders
const GOODS_CAPTION_CAT: u32 = 24;

static CONFIGURED: Mutex<Vec<(i64, i32)>> = Mutex::new(Vec::new());
static CONFIGURED_SET: AtomicBool = AtomicBool::new(false);
static DONE: AtomicBool = AtomicBool::new(false);

pub fn configure(pairs: Vec<(i64, i32)>) {
    tracing::info!("shop-preview: configured {} shop slot(s)", pairs.len());
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
        return false; // wait for the scout reply
    }
    let pairs = CONFIGURED.lock().unwrap().clone();
    if pairs.is_empty() {
        DONE.store(true, Ordering::Relaxed);
        return true;
    }

    // FOREIGN / gem slots only — own-world slots are sold natively by shop_sell. Per-category override
    // maps (name 10, info 20, caption 24) deduped by good id (the FMG entry is global).
    let mut nmap: HashMap<u32, Vec<u16>> = HashMap::new();
    let mut imap: HashMap<u32, Vec<u16>> = HashMap::new();
    let mut cmap: HashMap<u32, Vec<u16>> = HashMap::new();
    let (mut overridden, mut native) = (0u32, 0u32);
    for (loc, good) in &pairs {
        let Some(s) = super::scout_proof::lookup(*loc) else { continue };
        if s.er_sell_id.is_some() {
            native += 1;
            continue; // own-world: shop_sell sells it natively
        }
        overridden += 1;
        let gid = *good as u32;
        nmap.insert(gid, s.name.encode_utf16().collect());
        let text = format!("AP: {}\nFor: {} ({})\n{}", s.name, s.owner, s.game, s.kind.label());
        let u: Vec<u16> = text.encode_utf16().collect();
        imap.insert(gid, u.clone());
        cmap.insert(gid, u);
    }
    let names: Vec<(u32, Vec<u16>)> = nmap.into_iter().collect();
    let infos: Vec<(u32, Vec<u16>)> = imap.into_iter().collect();
    let caps: Vec<(u32, Vec<u16>)> = cmap.into_iter().collect();
    let n = super::fmg_inject::extend_swap_overrides(GOODS_NAME_CAT, &names);
    let i = super::fmg_inject::extend_swap_overrides(GOODS_INFO_CAT, &infos);
    let c = super::fmg_inject::extend_swap_overrides(GOODS_CAPTION_CAT, &caps);
    tracing::info!(
        "shop-preview: {overridden} foreign/gem slot(s) ({} distinct, {native} own-world via shop_sell) -> extend-swap names={n} infos={i} captions={c}",
        names.len()
    );
    DONE.store(true, Ordering::Relaxed);
    true
}
