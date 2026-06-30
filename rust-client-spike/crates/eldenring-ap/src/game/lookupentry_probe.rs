//! STEP A diagnostic (shop previews Part 3 gate) — a READ-ONLY logging detour on
//! `MsgRepositoryImp::LookupEntry`. It substitutes NOTHING: it logs each call's `(this, args, return)`
//! and calls the original. Open a vanilla shop and watch the log — if item-name ids flow through here
//! while the shop is open, the LookupEntry-detour mechanism is GO (SPEC-lookupentry-spike.md §2.0); if
//! not, pivot to the FMG-buffer-edit mechanism (§2.4). See STEP-A-RUNBOOK.md.
//!
//! SAFETY / STATUS: DIAGNOSTIC, gated and INERT until you fill the two build-pinned constants below
//! from a disassembler pass on YOUR eldenring.exe. While `LOOKUP_ENTRY_RVA == 0` (or the prologue
//! signature is empty / mismatched) it REFUSES to install — exactly like `detour.rs`'s AddItemFunc
//! guard — so building with it changes nothing until you've pinned the address. `eldenring` 0.14 does
//! NOT bind MsgRepository (verified 2026-06-29: its `cs` module has SoloParamRepository / CSFileRepository
//! / MsbRepository but no MsgRepository and no LookupEntry), so there is no typed shortcut; RVA-pinning
//! is the path, matching the crate's only working precedent (`detour.rs::ADD_ITEM_FUNC_RVA`).
//!
//! ABI NOTE: LookupEntry's arity is UNVERIFIED. We declare the 4-arg shape
//! `(this, group, category, entry_id) -> *const u16`. On x64 fastcall an over-declared trailing arg is
//! harmless (it rides r9, which a 3-arg original ignores), so this logs safely whether the real
//! function takes 3 or 4 args. The first run's logged values reveal the true arity/arg order — read
//! category (small, e.g. GoodsName) vs id (large) off the logged args, then promote per spec §5.

use std::ffi::c_void;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::OnceLock;

use retour::GenericDetour;

/// Raw target ABI (over-declared 4-arg; see ABI NOTE). Adjust to the true arity once the first run
/// reveals it, then promote to the real `names.rs` hook (SPEC-lookupentry-spike.md §5).
type LookupEntryFn = unsafe extern "C" fn(*mut c_void, u32, i32, i32) -> *const u16;

static HOOK: OnceLock<GenericDetour<LookupEntryFn>> = OnceLock::new();
static CALLS: AtomicU64 = AtomicU64::new(0);

// --- FILL THESE on Windows from a disassembler pass on YOUR eldenring.exe build (STEP-A-RUNBOOK.md) -
/// LookupEntry RVA (module-relative). 0 => refuse install (inert).
const LOOKUP_ENTRY_RVA: usize = 0x0;
/// Leading prologue bytes at that RVA — the install guard (like `ADD_ITEM_FUNC_SIG`). Empty => refuse.
const LOOKUP_ENTRY_SIG: &[u8] = &[];

// Diagnostic throttle: log the first N calls verbatim (reveals arity/arg ranges), then 1-in-SAMPLE.
const PROBE_FIRST_N: u64 = 200;
const SAMPLE_EVERY: u64 = 251;

/// Resolve LookupEntry, verify its prologue signature, and install the logging detour. Idempotent.
/// Inert (returns Ok without installing) until the RVA + signature are pinned.
pub fn install() -> Result<(), Box<dyn std::error::Error>> {
    if HOOK.get().is_some() {
        return Ok(());
    }
    if LOOKUP_ENTRY_RVA == 0 || LOOKUP_ENTRY_SIG.is_empty() {
        super::breadcrumb("LE-probe: LOOKUP_ENTRY_RVA/SIG unset; NOT installing (fill them, see STEP-A-RUNBOOK.md)");
        return Ok(()); // inert: nothing pinned yet, so nothing to hook
    }
    let target_addr = current_module_base().ok_or("LE-probe: no module base")? + LOOKUP_ENTRY_RVA;
    // Guard: refuse a wrong/stale address — detouring the wrong bytes would crash.
    if !signature_matches(target_addr) {
        super::breadcrumb("LE-probe: SIGNATURE MISMATCH at LookupEntry RVA; NOT installing");
        return Err(format!(
            "LE-probe: LookupEntry signature mismatch @ {target_addr:#x} — pinned RVA is stale for this build"
        )
        .into());
    }
    // SAFETY: target_addr is the resolved LookupEntry; the detour fn matches the (over-declared) ABI.
    let target: LookupEntryFn = unsafe { std::mem::transmute::<usize, LookupEntryFn>(target_addr) };
    let detour = unsafe { GenericDetour::<LookupEntryFn>::new(target, lookup_entry_detour)? };
    unsafe {
        detour.enable()?;
    }
    let _ = HOOK.set(detour);
    super::breadcrumb("LE-probe: LookupEntry logging detour installed + enabled");
    tracing::info!("LE-probe: LookupEntry diagnostic detour @ {target_addr:#x}");
    Ok(())
}

/// Call the original LookupEntry via the trampoline (never re-enters the detour).
fn call_original(this: *mut c_void, group: u32, category: i32, entry_id: i32) -> *const u16 {
    match HOOK.get() {
        // SAFETY: routes through retour's trampoline with the (over-declared) ABI.
        Some(h) => unsafe { h.call(this, group, category, entry_id) },
        None => std::ptr::null(),
    }
}

/// The detour body: pass through unchanged, log a throttled sample of `(this, args, return)`.
unsafe extern "C" fn lookup_entry_detour(
    this: *mut c_void,
    group: u32,
    category: i32,
    entry_id: i32,
) -> *const u16 {
    let n = CALLS.fetch_add(1, Ordering::Relaxed);
    let ret = call_original(this, group, category, entry_id);
    // First N calls verbatim (learn arity/arg order/ranges), then a 1-in-SAMPLE_EVERY trickle so an
    // open shop's GoodsName lookups show up without flooding the (non-blocking) log sink.
    if n < PROBE_FIRST_N || n % SAMPLE_EVERY == 0 {
        tracing::info!(
            "LE-probe #{n}: this={:p} a1(group?)={group} a2(cat?)={category} a3(id?)={entry_id} -> ret={:p}",
            this,
            ret
        );
    }
    ret
}

/// Base address of the host module (`eldenring.exe`) — same resolution as `detour.rs`.
fn current_module_base() -> Option<usize> {
    use windows::Win32::System::LibraryLoader::GetModuleHandleW;
    let hmodule = unsafe { GetModuleHandleW(None) }.ok()?;
    Some(hmodule.0 as usize)
}

/// True iff the bytes at `addr` start with the pinned LookupEntry prologue signature.
/// SAFETY: reads `LOOKUP_ENTRY_SIG.len()` bytes from `addr`; caller passes a module .text address.
fn signature_matches(addr: usize) -> bool {
    let actual = unsafe { std::slice::from_raw_parts(addr as *const u8, LOOKUP_ENTRY_SIG.len()) };
    actual == LOOKUP_ENTRY_SIG
}
