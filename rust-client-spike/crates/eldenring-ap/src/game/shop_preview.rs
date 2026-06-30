//! shop_preview.rs — make a pure-runtime shop slot READ as the AP reward it actually gives.
//!
//! A pure-runtime shop slot sells its VANILLA ware (no bake rewrote ShopLineupParam.equipId), so the
//! menu would show e.g. "Cracked Pot" even though buying it hands out an AP item. This rewrites that
//! vanilla good's FMG strings to the scouted AP item:
//!   * GoodsName    (cat 10) — the slot title (grid tile + detail pane),
//!   * GoodsInfo    (cat 20) — the "Item Effect" line the BUY/inspect menu actually renders,
//!   * GoodsCaption (cat 24) — the long inventory lore box (shown once the item is owned).
//! Driven by slot_data `shopPreviewGoods` = {AP location id -> vanilla good id it displays}; the AP
//! item text comes from the scout cache (`scout_proof::lookup`).
//!
//! Mechanism: EXTEND-SWAP via `fmg_inject::extend_swap_overrides`, NOT in-place. The old in-place path
//! could only write a string that FIT the packed vanilla entry, so a longer AP name/info silently kept
//! vanilla (e.g. "Fulgurbloom x4" can't overwrite "Cracked Pot", and 165/266 names were dropped this
//! way). extend-swap rebuilds the category block from the LIVE pointer — preserving fmg_inject's
//! synthetic-goods swap — with the overridden ids redirected to freshly-appended strings, so any length
//! fits. The rebuild is validated in our own memory before the atomic swap; a mismatch aborts (game
//! untouched). Runs AFTER fmg_inject each tick (see mod.rs), so it reads the post-swap blocks.
//!
//! ⚠️ The override is GLOBAL — the FMG entry is shared, so the good is renamed everywhere (inventory,
//! other shops). Accepted tradeoff for shop-exclusive wares. We dedup by good id first: this seed has
//! 266 slots but only ~212 distinct goods, and the shared entry can only show one reward, so duplicates
//! collapse to last-wins (the GIVEN item is still correct — it comes from the flag/grant, not the name).

#![allow(dead_code)]

use std::collections::HashMap;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;

const GOODS_NAME_CAT: u32 = 10;
/// GoodsInfo — the short "Item Effect" line the BUY/inspect menu actually renders (confirmed in-game).
const GOODS_INFO_CAT: u32 = 20;
/// GoodsCaption — the long inventory lore box (shown once the item is owned).
const GOODS_CAPTION_CAT: u32 = 24;

/// slot_data `shopPreviewGoods` -> (AP location id, vanilla good id). Set by net.rs at connect.
static CONFIGURED: Mutex<Vec<(i64, i32)>> = Mutex::new(Vec::new());
static CONFIGURED_SET: AtomicBool = AtomicBool::new(false);
static DONE: AtomicBool = AtomicBool::new(false);

pub fn configure(pairs: Vec<(i64, i32)>) {
    tracing::info!("shop-preview: configured {} goods slot(s) from slot_data shopPreviewGoods", pairs.len());
    *CONFIGURED.lock().unwrap() = pairs;
    CONFIGURED_SET.store(true, Ordering::Relaxed);
}

/// In-world, scout-ready: rewrite each previewed shop good's name + info + caption to its AP item via
/// extend-swap (so any length fits). Latches once applied.
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

    // Build per-category override maps (vanilla good id -> AP text) from the scout cache, deduped by
    // good id (the FMG entry is global; duplicates would otherwise fail the rebuild's validation).
    let mut nmap: HashMap<u32, Vec<u16>> = HashMap::new();
    let mut imap: HashMap<u32, Vec<u16>> = HashMap::new();
    let mut cmap: HashMap<u32, Vec<u16>> = HashMap::new();
    let mut foreign = 0u32;
    for (loc, good) in &pairs {
        let Some(s) = super::scout_proof::lookup(*loc) else { continue };
        if s.foreign {
            foreign += 1;
        }
        let gid = *good as u32;
        // NAME: the AP item name (slot title).
        nmap.insert(gid, s.name.encode_utf16().collect());
        // INFO + CAPTION: the same multi-line AP routing block that renders cleanly in the Item Effect
        // box ("AP: <item> / For: <owner> (<game>) / <kind>").
        let text = format!("AP: {}\nFor: {} ({})\n{}", s.name, s.owner, s.game, s.kind.label());
        let units: Vec<u16> = text.encode_utf16().collect();
        imap.insert(gid, units.clone());
        cmap.insert(gid, units);
    }
    let names: Vec<(u32, Vec<u16>)> = nmap.into_iter().collect();
    let infos: Vec<(u32, Vec<u16>)> = imap.into_iter().collect();
    let caps: Vec<(u32, Vec<u16>)> = cmap.into_iter().collect();

    let n = super::fmg_inject::extend_swap_overrides(GOODS_NAME_CAT, &names);
    let i = super::fmg_inject::extend_swap_overrides(GOODS_INFO_CAT, &infos);
    let c = super::fmg_inject::extend_swap_overrides(GOODS_CAPTION_CAT, &caps);
    tracing::info!(
        "shop-preview: {} slots ({} foreign, {} distinct) -> extend-swap names={} infos={} captions={}",
        pairs.len(),
        foreign,
        names.len(),
        n,
        i,
        c
    );
    DONE.store(true, Ordering::Relaxed);
    true
}
