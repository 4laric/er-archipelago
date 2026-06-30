//! shop_preview.rs — show the AP reward on a randomized shop slot.
//!
//! A pure-runtime shop slot sells its VANILLA ware (no bake rewrote ShopLineupParam.equipId), so the
//! menu shows e.g. "Glintstone Pebble" even though buying it sends an AP item out. This overwrites that
//! vanilla good's GoodsName (cat 10) + GoodsCaption (cat 24) in place with the scouted AP item, so the
//! slot reads as what it really gives. Driven by slot_data `shopPreviewGoods` = {AP location id ->
//! vanilla good id it displays}; the AP item comes from the scout cache (`scout_proof::lookup`).
//!
//! ⚠️ The overwrite is GLOBAL (the FMG entry is shared) — that good is renamed everywhere (inventory,
//! other shops). Accepted tradeoff for shop-exclusive wares; we keep it tame by (a) only touching slots
//! whose item is FOREIGN (going to another player), and (b) only overwriting the NAME when the AP name
//! fits the vanilla slot (entries are packed; in-place writes can't grow). The CAPTION almost always
//! fits (vanilla lore is long), so the lore box is the reliable carrier.
//!
//! Mechanism = the proven in-place path (fmg_probe gate): `SearchStringTable(repo,0,cat,id)` returns the
//! live UTF-16 buffer; overwrite under VirtualProtect RW, NUL-terminate, restore protection.

#![allow(dead_code)]

use std::ffi::c_void;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;

const REPO_RVA: usize = 0x3D7D4F8;
const SEARCH_RVA: usize = 0x266D3C0;
const SEARCH_SIG: &[u8] = &[
    0x3B, 0x51, 0x10, 0x73, 0x29, 0x44, 0x3B, 0x41, 0x14, 0x73, 0x23, 0x48, 0x8B, 0x41, 0x08,
];
const GOODS_NAME_CAT: u32 = 10;
const GOODS_CAPTION_CAT: u32 = 24;

type SearchFn = unsafe extern "C" fn(*mut c_void, u32, u32, u32) -> *const u16;

/// slot_data `shopPreviewGoods` -> (AP location id, vanilla good id). Set by net.rs at connect.
static CONFIGURED: Mutex<Vec<(i64, i32)>> = Mutex::new(Vec::new());
static CONFIGURED_SET: AtomicBool = AtomicBool::new(false);
static DONE: AtomicBool = AtomicBool::new(false);

pub fn configure(pairs: Vec<(i64, i32)>) {
    tracing::info!("shop-preview: configured {} goods slot(s) from slot_data shopPreviewGoods", pairs.len());
    *CONFIGURED.lock().unwrap() = pairs;
    CONFIGURED_SET.store(true, Ordering::Relaxed);
}

fn plausible(p: usize) -> bool {
    p >= 0x10000 && p < 0x7FFF_FFFF_FFFF
}
fn module_base() -> Option<usize> {
    use windows::Win32::System::LibraryLoader::GetModuleHandleW;
    Some(unsafe { GetModuleHandleW(None) }.ok()?.0 as usize)
}
unsafe fn read_usize(a: usize) -> usize {
    (a as *const usize).read_unaligned()
}
fn sig_ok(addr: usize) -> bool {
    let b = unsafe { std::slice::from_raw_parts(addr as *const u8, SEARCH_SIG.len()) };
    b == SEARCH_SIG
}

/// UTF-16 length (units, excluding NUL) of the live string at `ptr`, or None if implausible/empty.
unsafe fn str_units(ptr: *const u16) -> Option<usize> {
    if !plausible(ptr as usize) {
        return None;
    }
    let mut n = 0usize;
    while n < 4096 {
        if ptr.add(n).read_unaligned() == 0 {
            break;
        }
        n += 1;
    }
    if n == 0 {
        None
    } else {
        Some(n)
    }
}

/// Overwrite the FMG entry (category, id) with `new` IN PLACE, only if it fits within the original
/// entry (<= original units). Returns true if written. The buffer must already exist (vanilla id).
unsafe fn overwrite(search: SearchFn, repo: *mut c_void, category: u32, id: u32, new: &[u16]) -> bool {
    let ptr = search(repo, 0, category, id);
    let orig = match str_units(ptr) {
        Some(n) => n,
        None => return false, // no existing entry to overwrite
    };
    if new.len() > orig {
        return false; // would overrun the packed entry; caller falls back / skips
    }
    use windows::Win32::System::Memory::{VirtualProtect, PAGE_PROTECTION_FLAGS, PAGE_READWRITE};
    let bytes = (new.len() + 1) * 2;
    let mut old = PAGE_PROTECTION_FLAGS(0);
    if VirtualProtect(ptr as *const c_void, bytes, PAGE_READWRITE, &mut old).is_err() {
        return false;
    }
    let dst = ptr as *mut u16;
    for (i, &u) in new.iter().enumerate() {
        dst.add(i).write_unaligned(u);
    }
    dst.add(new.len()).write_unaligned(0); // NUL-terminate (fits: new.len() < orig, NUL slot exists)
    let _ = VirtualProtect(ptr as *const c_void, bytes, old, &mut old);
    true
}

/// In-world, scout-ready: overwrite each previewed shop good's name+caption with its AP item. Latches.
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
    let base = match module_base() {
        Some(b) => b,
        None => return true,
    };
    let search_addr = base + SEARCH_RVA;
    if !sig_ok(search_addr) {
        tracing::warn!("shop-preview: SearchStringTable sig mismatch; abort");
        DONE.store(true, Ordering::Relaxed);
        return true;
    }
    let search: SearchFn = unsafe { std::mem::transmute::<usize, SearchFn>(search_addr) };
    let repo = unsafe { read_usize(base + REPO_RVA) };
    if !plausible(repo) {
        return false; // repo not up yet
    }
    let repo = repo as *mut c_void;

    let (mut names, mut caps, mut foreign, mut name_skips) = (0u32, 0u32, 0u32, 0u32);
    for (loc, good) in &pairs {
        let Some(s) = super::scout_proof::lookup(*loc) else { continue };
        // Preview EVERY randomized goods slot, not just foreign ones — in a 2-slot most shop rewards
        // are your OWN game's items, and skipping them leaves the shop looking un-randomized. `foreign`
        // is still tracked for the log + caption wording.
        if s.foreign {
            foreign += 1;
        }
        let gid = *good as u32;
        // NAME: just the AP item name; overwrite only if it fits the vanilla slot.
        let nm: Vec<u16> = s.name.encode_utf16().collect();
        if unsafe { overwrite(search, repo, GOODS_NAME_CAT, gid, &nm) } {
            names += 1;
        } else {
            name_skips += 1;
        }
        // CAPTION: full AP info (name included, so it reads even if the name didn't fit). Vanilla lore
        // is long, so this fits in place.
        let cap = format!("AP: {}\nFor: {} ({})\n{}", s.name, s.owner, s.game, s.kind.label());
        let cu: Vec<u16> = cap.encode_utf16().collect();
        if unsafe { overwrite(search, repo, GOODS_CAPTION_CAT, gid, &cu) } {
            caps += 1;
        }
    }
    tracing::info!(
        "shop-preview: {} slots ({} foreign) -> {} names + {} captions overwritten ({} names too long, kept vanilla)",
        pairs.len(), foreign, names, caps, name_skips
    );
    DONE.store(true, Ordering::Relaxed);
    true
}
