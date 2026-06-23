//! DETECT + GRANT layer — the `AddItemFunc` detour. Replaces the MinHook detour in
//! `er_gamehook_win.cpp` with `retour`'s `static_detour!`.
//!
//! `AddItemFunc` is the linchpin: every item lot routes through it, so hooking its entry yields
//! pickup DETECTION, and calling the trampoline performs a GRANT. Binding facts (build-pinned,
//! CE-cross-validated) come from `er_hooks.h`.
//!
//! ⚠️ COMPILE-TARGET SKETCH. `// VERIFY:` marks the address-resolution call and the exact ABI of
//! the target to confirm on the laptop. First-run confirmations are flagged per tools/NOTES.md.

use std::ffi::c_void;

use er_codec::{decide_pickup, decode_synthetic, is_synthetic_goods, row_id_of, PickupAction};

use super::{flags, params};

// --- AddItemFunc binding (er_hooks.h, eldenring.exe 2.6.2.0) --------------------------------------
// AddItemFunc(rcx = inventory instance, rdx = &itembuf + ITEMBUF_ENTRY_OFF, r8 = &itembuf, r9 = 0).
// The Win64 ABI maps these to the first four `extern "C"` args.
const ADD_ITEM_FUNC_RVA: usize = 0x0056_05B0;
#[allow(dead_code)]
const ADD_ITEM_FUNC_AOB: &str = "40 55 56 57 41 54 41 55 41 56 41 57 48 8D AC 24 70 FF FF FF 48 81 EC 90 01 00 00 48 C7 45 C8 FE FF FF FF 48 89 9C 24 D8 01 00 00 48 8B 05";

// item descriptor ("itembuffer") entry layout. rdx points at the entry (itembuf + 0x20).
const ITEMBUF_ENTRY_ID_OFF: usize = 0x04; // s32: itemId | (categoryNibble << 28)  (== itembuf+0x24)
const ITEMBUF_ENTRY_QTY_OFF: usize = 0x08; // s32: quantity                          (== itembuf+0x28)

// retour generates the trampoline + enable/disable. The signature is the raw target ABI.
retour::static_detour! {
    static AddItemHook: unsafe extern "C" fn(*mut c_void, *mut c_void, *mut c_void, u64) -> u64;
}

/// Resolve `AddItemFunc` and install the detour. Idempotent.
pub fn install() -> Result<(), Box<dyn std::error::Error>> {
    let target = resolve_add_item_func().ok_or("AddItemFunc not found (AOB miss)")?;

    // SAFETY: `target` points at the resolved function in the loaded module; the closure runs on
    // the game's calling thread. retour handles trampoline relocation.
    unsafe {
        let f: unsafe extern "C" fn(*mut c_void, *mut c_void, *mut c_void, u64) -> u64 =
            std::mem::transmute(target);
        AddItemHook.initialize(f, add_item_detour)?;
        AddItemHook.enable()?;
    }
    tracing::info!("AddItemFunc detour installed @ {target:#x}");
    Ok(())
}

/// The detour body. Keeps the unsafe surface tiny: read the inbound id, hand the *decision* to the
/// pure `er_codec`, and either suppress (drop placeholder + report) or pass through to the real
/// function.
fn add_item_detour(
    inventory: *mut c_void,
    entry: *mut c_void,
    itembuf: *mut c_void,
    r9: u64,
) -> u64 {
    // SAFETY: `entry` is the descriptor the game passes (rdx); id at entry+0x04, qty at entry+0x08.
    // VERIFY (NOTES.md #1): confirm the picked-up id really sits at entry+0x04 by logging rawId for
    // a few pickups on first run.
    let raw_id = unsafe { read_i32(entry, ITEMBUF_ENTRY_ID_OFF) } as u32;

    if !is_synthetic_goods(raw_id) {
        // Real item — leave the game's behavior untouched.
        return unsafe { AddItemHook.call(inventory, entry, itembuf, r9) };
    }

    // Synthetic placeholder: decode it from the typed goods param (DECODE layer).
    match params::goods_row_fields(row_id_of(raw_id) as i32) {
        Some(fields) => {
            let item = decode_synthetic(&fields);

            // REPORT: every synthetic pickup is an AP check, local or foreign.
            flags::report_location(item.ap_location_id);

            match decide_pickup(&item) {
                PickupAction::SuppressAndGrant => {
                    // Drop the placeholder, then grant the local replacement. Queue the grant
                    // rather than re-entering AddItemFunc from inside its own detour.
                    grant_local(item.local_item_id, item.local_quantity);
                    // VERIFY (NOTES.md #2): returning 0 cleanly drops the placeholder.
                    0
                }
                PickupAction::Suppress => {
                    // Foreign check (or no local item): report only, drop the placeholder.
                    0
                }
            }
        }
        None => {
            // Couldn't resolve the row (param repo not ready?) — fail safe: behave like vanilla so
            // we never eat a real pickup.
            tracing::warn!("synthetic id {raw_id:#x} but goods row unresolved; passing through");
            unsafe { AddItemHook.call(inventory, entry, itembuf, r9) }
        }
    }
}

/// Grant a local item by full gib id (id | category). For us category is always GOODS. Calls the
/// real `AddItemFunc` via the trampoline (bypasses the detour).
///
/// TODO(phase 3): construct the itembuf descriptor + obtain the inventory instance (rcx). In the
/// C++ client this was `GrantItem` building a stack itembuf and resolving the inventory ptr-loc; in
/// Rust the inventory comes from the `eldenring` crate (GameDataMan -> PlayerGameData -> inventory).
/// Until then this is a no-op stub so the decision path is exercisable.
fn grant_local(local_item_id: i32, qty: i32) {
    if local_item_id == 0 {
        return;
    }
    let _full_id = (local_item_id as u32) | er_codec::CATEGORY_GOODS;
    tracing::debug!("TODO grant_local id={local_item_id} qty={qty}");
    // unsafe { AddItemHook.call(inventory, &mut entry, &mut itembuf, 0) };
}

/// Resolve the function address. VERIFY: wire to an AOB scanner — `pelite` (already a transitive
/// dep of `eldenring`) or `patternsleuth`. Until then, fall back to ImageBase + RVA for the pinned
/// 2.6.2.0 build (works only on that exact exe — the AOB is what survives patches).
fn resolve_add_item_func() -> Option<usize> {
    // TODO: scan module .text for ADD_ITEM_FUNC_AOB and return the match. Pinned fallback:
    let module_base = current_module_base()?;
    Some(module_base + ADD_ITEM_FUNC_RVA)
}

/// Base address of `eldenring.exe`. VERIFY: use `windows::Win32::System::LibraryLoader::
/// GetModuleHandleW(None)` (whole process) and cast.
fn current_module_base() -> Option<usize> {
    None
}

/// SAFETY: caller guarantees `base + off + 4` is readable.
unsafe fn read_i32(base: *const c_void, off: usize) -> i32 {
    let p = (base as *const u8).add(off) as *const i32;
    p.read_unaligned()
}
