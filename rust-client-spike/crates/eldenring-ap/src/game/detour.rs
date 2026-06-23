//! DETECT + GRANT layer — the `AddItemFunc` detour (Phase 3). Replaces the MinHook detour in the
//! C++ `er_gamehook_win.cpp` with retour's STABLE `GenericDetour` (the nightly `static_detour!` is
//! gone — fromsoftware-rs pins stable; see the spike root's VERIFY-RESOLUTION.md).
//!
//! `AddItemFunc` is the linchpin: every item lot routes through it, so hooking its entry yields
//! pickup DETECTION, and calling the trampoline (`HOOK.call(...)`) performs the original GRANT.
//! Binding facts (build-pinned, CE-cross-validated) come from the C++ `er_hooks.h`.
//!
//! STILL OPEN (real RE, not symbol lookup): a version-robust AOB scan for AddItemFunc — today it's
//! module base + the pinned 2.6.2.0 RVA, guarded by a leading-byte signature so a WRONG address
//! REFUSES to install instead of detouring garbage and crashing. Local grant (Phase 3b): SUPPRESS
//! the world pickup (return 0 -> no full "You got" acquisition popup) and grant the item via a
//! STANDALONE AddItemFunc call with a constructed descriptor (C++ GrantItem port) so it uses ER's
//! non-interrupting item-gain TICKER. Reuses the live inventory pointer the detour is handed.

use std::ffi::c_void;
use std::sync::OnceLock;

use retour::GenericDetour;

use er_codec::{decide_pickup, decode_synthetic, is_synthetic_goods, row_id_of, PickupAction};

use super::{flags, params};

/// Raw target ABI: AddItemFunc(rcx = inventory, rdx = &itembuf entry, r8 = &itembuf, r9 = 0).
type AddItemFn = unsafe extern "C" fn(*mut c_void, *mut c_void, *mut c_void, u64) -> u64;

/// The installed detour. `GenericDetour<T>` is `Send + Sync` (docs.rs/retour 0.3.1), so a `static`
/// `OnceLock` is its home; we keep it for the process lifetime and call `.call(..)` on it to reach
/// the original function from inside the hook.
static HOOK: OnceLock<GenericDetour<AddItemFn>> = OnceLock::new();

// --- AddItemFunc binding (er_hooks.h, eldenring.exe 2.6.2.0) --------------------------------------
const ADD_ITEM_FUNC_RVA: usize = 0x0056_05B0;
// Leading concrete bytes of the prologue (wildcard tail dropped) — the install guard.
const ADD_ITEM_FUNC_SIG: &[u8] = &[
    0x40, 0x55, 0x56, 0x57, 0x41, 0x54, 0x41, 0x55, 0x41, 0x56, 0x41, 0x57, 0x48, 0x8D, 0xAC, 0x24,
];

// itembuffer entry layout: rdx points at the entry (itembuf + 0x20); id at entry+0x04.
const ITEMBUF_ENTRY_ID_OFF: usize = 0x04; // s32: itemId | (categoryNibble << 28), at entry+0x04
const ITEMBUF_ENTRY_OFF: usize = 0x20; // a constructed itembuf's entry sits at buf+0x20 (C++ GrantItem)

/// Resolve `AddItemFunc`, verify its signature, and install the detour. Idempotent.
pub fn install() -> Result<(), Box<dyn std::error::Error>> {
    if HOOK.get().is_some() {
        return Ok(());
    }
    let target_addr =
        resolve_add_item_func().ok_or("AddItemFunc address unresolved (no module base)")?;

    // Guard: refuse a wrong address (stale RVA for this game build) — detouring the wrong bytes
    // would crash. SAFETY: target_addr is inside the loaded module's mapped .text.
    if !signature_matches(target_addr) {
        super::breadcrumb("detour: SIGNATURE MISMATCH at AddItemFunc RVA; NOT installing");
        return Err(format!(
            "AddItemFunc signature mismatch @ {target_addr:#x} — pinned RVA is stale for this game build (needs an AOB scan / matching version)"
        )
        .into());
    }

    // SAFETY: target_addr points at the resolved AddItemFunc; the detour fn matches its ABI.
    let target: AddItemFn = unsafe { std::mem::transmute::<usize, AddItemFn>(target_addr) };
    let detour = unsafe { GenericDetour::<AddItemFn>::new(target, add_item_detour)? };
    unsafe {
        detour.enable()?;
    }
    let _ = HOOK.set(detour);
    super::breadcrumb("detour: AddItemFunc hook installed + enabled");
    tracing::info!("AddItemFunc detour installed @ {target_addr:#x}");
    Ok(())
}

/// Call the original AddItemFunc via the trampoline (bypasses the hook). Returns 0 if the hook
/// somehow isn't set — never re-enters the detour.
fn call_original(inventory: *mut c_void, entry: *mut c_void, itembuf: *mut c_void, r9: u64) -> u64 {
    match HOOK.get() {
        // SAFETY: calls the original AddItemFunc via retour's trampoline with the exact ABI.
        Some(h) => unsafe { h.call(inventory, entry, itembuf, r9) },
        None => 0,
    }
}

/// The detour body. Tiny unsafe surface: read the inbound id, hand the *decision* to pure `er_codec`,
/// and either suppress (drop placeholder + report the check) or pass through to the real function.
unsafe extern "C" fn add_item_detour(
    inventory: *mut c_void,
    entry: *mut c_void,
    itembuf: *mut c_void,
    r9: u64,
) -> u64 {
    // SAFETY: `entry` is the descriptor the game passes (rdx); id at entry+0x04.
    let raw_id = read_i32(entry, ITEMBUF_ENTRY_ID_OFF) as u32;

    if !is_synthetic_goods(raw_id) {
        return call_original(inventory, entry, itembuf, r9);
    }

    match params::goods_row_fields(row_id_of(raw_id) as i32) {
        Some(fields) => {
            let item = decode_synthetic(&fields);
            tracing::info!(
                "AP check: synthetic goods {raw_id:#x} -> location {} (local item {} x{}, foreign={})",
                item.ap_location_id,
                item.local_item_id,
                item.local_quantity,
                item.foreign_remove
            );
            // REPORT: every synthetic pickup is an AP check, local or foreign.
            flags::report_location(item.ap_location_id);

            match decide_pickup(&item) {
                PickupAction::SuppressAndGrant => {
                    // SUPPRESS the world pickup (return 0 -> no full "You got" popup), then grant the
                    // local item via a STANDALONE AddItemFunc call (constructed descriptor) so it uses
                    // ER's non-interrupting item-gain ticker. Reuses the live `inventory` pointer.
                    tracing::info!(
                        "granting local goods {} x{} (ticker)",
                        item.local_item_id,
                        item.local_quantity
                    );
                    grant_item(inventory, item.local_item_id, item.local_quantity);
                    0
                }
                PickupAction::Suppress => 0, // foreign / no-local: report only, drop placeholder
            }
        }
        None => {
            tracing::warn!("synthetic id {raw_id:#x} but goods row unresolved; passing through");
            call_original(inventory, entry, itembuf, r9)
        }
    }
}

/// Resolve the function address. TODO (version-robustness): replace the pinned RVA with an AOB scan
/// of the module .text. Today: module base + pinned 2.6.2.0 RVA, guarded by signature_matches().
fn resolve_add_item_func() -> Option<usize> {
    Some(current_module_base()? + ADD_ITEM_FUNC_RVA)
}

/// Base address of the host process module (`eldenring.exe`). `GetModuleHandleW(None)` -> HMODULE;
/// `HMODULE(pub *mut c_void)`, so the base as `usize` is `hmodule.0 as usize`.
fn current_module_base() -> Option<usize> {
    use windows::Win32::System::LibraryLoader::GetModuleHandleW;
    let hmodule = unsafe { GetModuleHandleW(None) }.ok()?;
    Some(hmodule.0 as usize)
}

/// True iff the bytes at `addr` start with the AddItemFunc prologue signature.
/// SAFETY: reads ADD_ITEM_FUNC_SIG.len() bytes from `addr`; caller passes a module .text address.
fn signature_matches(addr: usize) -> bool {
    let actual = unsafe { std::slice::from_raw_parts(addr as *const u8, ADD_ITEM_FUNC_SIG.len()) };
    actual == ADD_ITEM_FUNC_SIG
}

/// SAFETY: caller guarantees `base + off + 4` is readable.
unsafe fn read_i32(base: *const c_void, off: usize) -> i32 {
    let p = (base as *const u8).add(off) as *const i32;
    p.read_unaligned()
}

/// Grant an item via a STANDALONE AddItemFunc call with a constructed descriptor (port of the C++
/// `GrantItem`). Reuses the live `inventory` pointer the detour was handed. Because this is a direct
/// call (not the world-pickup flow), the game shows its non-interrupting item-gain TICKER rather
/// than the full "You got" acquisition popup. `id_with_category` already carries the category nibble.
fn grant_item(inventory: *mut c_void, id_with_category: i32, quantity: i32) {
    if id_with_category == 0 || inventory.is_null() {
        return;
    }
    // 0x50-byte descriptor, 8-aligned (C++ alignas(8); CE table): entry count @+0x20=1, id @+0x24,
    // qty @+0x28, gem @+0x30=-1, trailing -1s @ +0x34 / +0x40(i64) / +0x4C. entry = buf+0x20.
    let mut buf = [0u64; 0x50 / 8];
    let base = buf.as_mut_ptr() as *mut u8;
    unsafe {
        (base.add(0x20) as *mut i32).write_unaligned(1);
        (base.add(0x24) as *mut i32).write_unaligned(id_with_category);
        (base.add(0x28) as *mut i32).write_unaligned(quantity);
        (base.add(0x30) as *mut i32).write_unaligned(-1);
        (base.add(0x34) as *mut i32).write_unaligned(-1);
        (base.add(0x40) as *mut i64).write_unaligned(-1);
        (base.add(0x4C) as *mut i32).write_unaligned(-1);
        let entry = base.add(ITEMBUF_ENTRY_OFF) as *mut c_void;
        let itembuf = base as *mut c_void;
        if let Some(h) = HOOK.get() {
            h.call(inventory, entry, itembuf, 0);
        }
    }
}
