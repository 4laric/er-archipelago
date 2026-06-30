//! FMG-edit gate (shop previews Part 3, Mechanism 2 — SPEC-lookupentry-spike.md §2.4 /
//! FMG-EDIT-FINDINGS.md). Proves we can change what a shop slot draws by editing the live GoodsName
//! string in memory — the MapForGoblins technique, no detour, no FMG-format reimplementation.
//!
//! HOW: `SearchStringTable` @ RVA 0x266D3C0 `(repo, group, category, id) -> *const u16` is the game's
//! own message lookup; it returns the LIVE UTF-16 string buffer for an entry (and is fully
//! self-guarding — bounds/null-checks internally, so calling it is safe). We call it for a known
//! GoodsName id to get that item's string pointer, then overwrite the UTF-16 in place (≤ original
//! length, NUL-terminated) under a VirtualProtect RW window. Open a shop/inventory showing that item
//! and the name reads back as our override = gate met.
//!
//! ADDRESSES — verified from eldenring.exe 2.6.2.0: repo global @ base+0x3D7D4F8; SearchStringTable @
//! base+0x266D3C0; ABI rcx=repo, edx=group(=0), r8d=category, r9d=id -> wchar*. GoodsName=category 10
//! (PlaceName=19/GemName=35/ArtsName=42 anchors confirmed live).
//!
//! SAFETY: resolves addresses module-relative; verifies SearchStringTable's prologue before calling;
//! only writes when the override is ≤ the original length (stays inside the entry's slot — entries are
//! packed back-to-back), under VirtualProtect, restoring the old protection after. `DO_WRITE=false`
//! makes this a pure read (logs before-text only).

use std::ffi::c_void;
use std::sync::atomic::{AtomicBool, Ordering};

const REPO_RVA: usize = 0x3D7D4F8;
const SEARCH_RVA: usize = 0x266D3C0;
const SEARCH_SIG: &[u8] = &[
    0x3B, 0x51, 0x10, 0x73, 0x29, 0x44, 0x3B, 0x41, 0x14, 0x73, 0x23, 0x48, 0x8B, 0x41, 0x08,
];

const GOODS_CATEGORY: u32 = 10;
/// "Furlcalling Finger Remedy" — sold by Kalé + the Twin Maidens; common in inventory. 25 UTF-16 units.
const TARGET_GOODS_ID: u32 = 150;
/// Replacement (must be ≤ the original's UTF-16 length). Obvious so the gate is unmistakable.
const OVERRIDE_TEXT: &str = "AP PREVIEW OK";
/// GATE PROVEN 2026-06-30 (id 150 "Furlcalling Finger Remedy" -> "AP PREVIEW OK" in-place). Now OFF —
/// this build is read-only: it confirms id 150 reads vanilla again AND probes the synthetic AP-goods
/// id range to verify they have NO GoodsName entry (so production needs FMG entry injection).
const DO_WRITE: bool = false;
/// Synthetic AP-placeholder goods live above this id (er_codec::SYNTHETIC_GOODS_MIN_ID). We sweep a
/// window to see whether SearchStringTable returns NULL (no entry -> inject) or a buffer (overwrite).
const SYNTH_LO: u32 = 3_780_001;
const SYNTH_HI: u32 = 3_781_200;
const SYNTH_LOG_MAX: usize = 12;

const STR_MAX: usize = 64;

/// rcx=repo, edx=group, r8d=category, r9d=id -> wchar_t* (or null).
type SearchFn = unsafe extern "C" fn(*mut c_void, u32, u32, u32) -> *const u16;

static DONE: AtomicBool = AtomicBool::new(false);

fn plausible(p: usize) -> bool {
    p >= 0x10000 && p < 0x7FFF_FFFF_FFFF
}
fn current_module_base() -> Option<usize> {
    use windows::Win32::System::LibraryLoader::GetModuleHandleW;
    let h = unsafe { GetModuleHandleW(None) }.ok()?;
    Some(h.0 as usize)
}
unsafe fn read_usize(addr: usize) -> usize {
    (addr as *const usize).read_unaligned()
}

/// (string, utf16_unit_len) read from a wchar* — None if implausible/empty.
fn read_utf16(ptr: *const u16) -> Option<(String, usize)> {
    if !plausible(ptr as usize) {
        return None;
    }
    let mut u = Vec::new();
    for i in 0..STR_MAX {
        let c = unsafe { ptr.add(i).read_unaligned() };
        if c == 0 {
            break;
        }
        u.push(c);
    }
    if u.is_empty() {
        return None;
    }
    let n = u.len();
    Some((String::from_utf16_lossy(&u), n))
}

fn sig_ok(addr: usize) -> bool {
    let bytes = unsafe { std::slice::from_raw_parts(addr as *const u8, SEARCH_SIG.len()) };
    bytes == SEARCH_SIG
}

/// Returns true once it has acted (caller stops calling); false while the repo is still null.
pub fn dump_repo() -> bool {
    if DONE.load(Ordering::Relaxed) {
        return true;
    }
    let base = match current_module_base() {
        Some(b) => b,
        None => {
            tracing::warn!("FMG-edit: no module base");
            return true;
        }
    };
    let repo = unsafe { read_usize(base + REPO_RVA) };
    if repo == 0 {
        return false; // not initialized yet
    }
    if !plausible(repo) {
        tracing::warn!("FMG-edit: repo implausible {repo:#x}; abort");
        return true;
    }
    let search_addr = base + SEARCH_RVA;
    if !sig_ok(search_addr) {
        tracing::warn!("FMG-edit: SearchStringTable prologue mismatch @ {search_addr:#x}; abort");
        return true;
    }
    let search: SearchFn = unsafe { std::mem::transmute::<usize, SearchFn>(search_addr) };

    let ptr = unsafe { search(repo as *mut c_void, 0, GOODS_CATEGORY, TARGET_GOODS_ID) };
    let before = read_utf16(ptr);
    tracing::info!("FMG-edit: goods id={TARGET_GOODS_ID} ptr={ptr:p} before={before:?}");

    let (_, orig_len) = match before {
        Some(b) => b,
        None => {
            tracing::warn!("FMG-edit: target id returned no string; nothing to edit");
            DONE.store(true, Ordering::Relaxed);
            return true;
        }
    };
    if !DO_WRITE {
        let _ = orig_len;
        tracing::info!("FMG-edit: DO_WRITE=false; read-only. Probing synthetic AP-goods id range for GoodsName entries…");
        let mut non_null = 0usize;
        let mut logged = 0usize;
        for id in SYNTH_LO..SYNTH_HI {
            let p = unsafe { search(repo as *mut c_void, 0, GOODS_CATEGORY, id) };
            if let Some((s, _)) = read_utf16(p) {
                non_null += 1;
                if logged < SYNTH_LOG_MAX {
                    tracing::info!("FMG-synth:   id={id} ptr={p:p} -> {s:?}");
                    logged += 1;
                }
            }
        }
        tracing::info!(
            "FMG-synth: === {} of {} synthetic ids returned a string. 0 => no GoodsName entries (FMG injection needed); >0 => overwritable ===",
            non_null,
            SYNTH_HI - SYNTH_LO
        );
        DONE.store(true, Ordering::Relaxed);
        return true;
    }

    let new: Vec<u16> = OVERRIDE_TEXT.encode_utf16().collect();
    if new.len() > orig_len {
        tracing::warn!("FMG-edit: override {} units > original {} units; skipping (would overrun the entry)", new.len(), orig_len);
        DONE.store(true, Ordering::Relaxed);
        return true;
    }

    // Overwrite in place under a VirtualProtect RW window.
    use windows::Win32::System::Memory::{VirtualProtect, PAGE_PROTECTION_FLAGS, PAGE_READWRITE};
    let bytes = (new.len() + 1) * 2; // + NUL terminator
    let mut old = PAGE_PROTECTION_FLAGS(0);
    let ok = unsafe { VirtualProtect(ptr as *const c_void, bytes, PAGE_READWRITE, &mut old) };
    if ok.is_err() {
        tracing::warn!("FMG-edit: VirtualProtect RW failed; aborting write");
        DONE.store(true, Ordering::Relaxed);
        return true;
    }
    unsafe {
        let dst = ptr as *mut u16;
        for (i, &u) in new.iter().enumerate() {
            dst.add(i).write_unaligned(u);
        }
        dst.add(new.len()).write_unaligned(0); // NUL-terminate
        let _ = VirtualProtect(ptr as *const c_void, bytes, old, &mut old); // restore protection
    }
    let after = read_utf16(ptr);
    tracing::info!("FMG-edit: WROTE override -> after={after:?}  (open a shop/inventory with that item)");
    DONE.store(true, Ordering::Relaxed);
    true
}
