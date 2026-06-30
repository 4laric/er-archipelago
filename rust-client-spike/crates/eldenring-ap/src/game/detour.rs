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
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::OnceLock;

use retour::GenericDetour;

use er_codec::{decode_synthetic, is_synthetic_goods, row_id_of};
use er_logic::vanilla_suppress::VanillaSuppressor;
use er_logic::detour_decide::{decide_detour_action, DetourAction};

use super::{flags, params};

/// Raw target ABI: AddItemFunc(rcx = inventory, rdx = &itembuf entry, r8 = &itembuf, r9 = 0).
type AddItemFn = unsafe extern "C" fn(*mut c_void, *mut c_void, *mut c_void, u64) -> u64;

/// The installed detour. `GenericDetour<T>` is `Send + Sync` (docs.rs/retour 0.3.1), so a `static`
/// `OnceLock` is its home; we keep it for the process lifetime and call `.call(..)` on it to reach
/// the original function from inside the hook.
static HOOK: OnceLock<GenericDetour<AddItemFn>> = OnceLock::new();

/// Live inventory instance pointer (rcx) captured from the most recent AddItemFunc detour call.
/// Phase 4 reuses it to grant SERVER-pushed items (which never trigger a pickup) without a
/// separate InventoryAccessor AOB scan — the detour already holds the pointer the game uses.
static LAST_INVENTORY: AtomicUsize = AtomicUsize::new(0);

/// Pure-runtime (no-baker) vanilla-suppression table. In vanilla placement the lot at an AP check
/// still carries its real vanilla item; the acquisition FLAG is set by the ItemLot/EMEVD path
/// (polled by `flags::poll_location_checks`), independently of `AddItemFunc`. So we can null the
/// bag-add for a check item without losing detection. The *decision* lives in pure `er-logic`
/// (`VanillaSuppressor`, host-tested); this holder is set once at connect via `configure_suppressor`.
/// `None` until configured -> the detour behaves exactly as before (no suppression).
static SUPPRESSOR: OnceLock<VanillaSuppressor> = OnceLock::new();

/// Called from the connect path (net.rs), beside the `LocationChecks` setup: install the vanilla
/// suppression table. Idempotent (`OnceLock::set` ignores a second call) — built once per process.
#[allow(dead_code)]
pub fn configure_suppressor(sup: VanillaSuppressor) {
    let _ = SUPPRESSOR.set(sup);
}

// --- AddItemFunc binding (er_hooks.h, eldenring.exe 2.6.2.0) --------------------------------------
const ADD_ITEM_FUNC_RVA: usize = 0x0056_05B0;
// Leading concrete bytes of the prologue (wildcard tail dropped) — the install guard.
const ADD_ITEM_FUNC_SIG: &[u8] = &[
    0x40, 0x55, 0x56, 0x57, 0x41, 0x54, 0x41, 0x55, 0x41, 0x56, 0x41, 0x57, 0x48, 0x8D, 0xAC, 0x24,
];

// Pinned static slot that holds the live inventory instance pointer (eldenring.exe 2.6.2.0). Ported
// from the C++ client's `Inventory_PtrLoc_RVA` (which it resolved from `InventoryAccessor_AOB`):
// `*(module_base + this)` is the SAME pointer AddItemFunc receives as rcx — but readable WITHOUT
// waiting for a pickup to capture it. Build cross-checked: the C++ `AddItemFunc_RVA` (0x005605B0)
// equals our `ADD_ITEM_FUNC_RVA`, so the inventory slot RVA below is valid for this same build.
const INVENTORY_PTRLOC_RVA: usize = 0x03D6_7A50;

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
    // Phase 4: cache the live inventory pointer on EVERY pickup (vanilla or synthetic) so the
    // server-pushed grant path has a valid inventory instance soon after the first pickup.
    LAST_INVENTORY.store(inventory as usize, Ordering::Relaxed);

    // SAFETY: `entry` is the descriptor the game passes (rdx); id at entry+0x04.
    let raw_id = read_i32(entry, ITEMBUF_ENTRY_ID_OFF) as u32;

    // Pure-runtime decision (host-tested in er_logic::detour_decide). `resolve` wraps the synthetic
    // check + params row read + decode, returning the AP location id or None (not-synthetic OR
    // unresolved both pass through). Suppression short-circuits before any synthetic handling.
    let resolve = |id: i32| -> Option<i64> {
        if !is_synthetic_goods(id as u32) {
            return None;
        }
        let fields = params::goods_row_fields(row_id_of(id as u32) as i32)?;
        Some(decode_synthetic(&fields).ap_location_id)
    };
    match decide_detour_action(raw_id as i32, SUPPRESSOR.get(), &flags::get_event_flag, &resolve) {
        DetourAction::Suppress => 0,
        DetourAction::PassThrough => call_original(inventory, entry, itembuf, r9),
        DetourAction::ReportThenSuppress(loc) => {
            tracing::info!("AP check: synthetic goods {raw_id:#x} -> location {loc}");
            flags::report_location(loc);
            0
        }
    }
}

/// Phase 4: grant a SERVER-pushed item by constructing a fresh itembuf and calling the original
/// AddItemFunc through the trampoline. Local self-found pickups are granted by the in-place
/// descriptor rewrite in the detour; server/foreign items never pass through a pickup, so we
/// build the 0x50-byte buffer the game expects (port of er_gamehook GrantItem) and reuse the
/// inventory pointer captured by the detour. Returns false if the hook isn't installed or no
/// inventory pointer has been captured yet (no pickup this session) — caller keeps the item
/// queued. MUST run on the game thread (the FrameBegin tick).
pub fn grant_full_id(full_id: i32, qty: i32) -> bool {
    if HOOK.get().is_none() {
        return false;
    }
    // auto_upgrade (Phase 5, RE-gated): every AP-received item — local self-found (echo), foreign,
    // notify, start — funnels through here, so this is the single choke point to raise a granted
    // weapon to the player's current max reinforce level. INERT until the RE holes in upgrades.rs are
    // filled (returns full_id unchanged); non-weapons pass through. `net`-only (lean detour build has
    // no upgrades module). Mirrors the C++ GrantItem AutoUpgradeWeaponId site.
    #[cfg(feature = "net")]
    let full_id = super::upgrades::apply_auto_upgrade(full_id);
    // Prefer the pointer the detour captured (proven live for THIS session). If no pickup has
    // happened yet this session, fall back to the pinned static inventory slot so the FIRST grant
    // doesn't stall until a self-found pickup primes LAST_INVENTORY — this is the fix for "the client
    // doesn't do anything until you pick up an item". Cache the resolved pointer so later grants
    // (and any reader of LAST_INVENTORY) reuse it.
    let mut inv = LAST_INVENTORY.load(Ordering::Relaxed);
    if inv < 0x10000 {
        inv = inventory_from_static();
        if inv >= 0x10000 {
            LAST_INVENTORY.store(inv, Ordering::Relaxed);
        }
    }
    if inv < 0x10000 {
        return false; // not in-game yet (slot unpopulated); retry on the next tick
    }
    // Reuse the existing constructed-descriptor grant (port of the C++ GrantItem) with the live
    // inventory pointer the detour captured. goods->goods; full_id already carries the category nibble.
    grant_item(inv as *mut c_void, full_id, qty);
    true
}

/// Read the live inventory instance from the pinned static slot (`INVENTORY_PTRLOC_RVA`), the
/// pickup-INDEPENDENT primer for `grant_full_id`. Returns 0 if the module base is unavailable or the
/// slot isn't populated yet (not in-game). Port of the C++ `InventoryInstance()`: read one pointer,
/// apply the game's own `>= 0x10000` validity guard.
fn inventory_from_static() -> usize {
    let base = match current_module_base() {
        Some(b) => b,
        None => return 0,
    };
    let ptr_loc = base + INVENTORY_PTRLOC_RVA;
    // SAFETY: `ptr_loc` = module base + a pinned data RVA inside the loaded eldenring.exe image;
    // reads exactly one usize (the inventory instance pointer the game stores there). A value
    // < 0x10000 means the slot isn't populated yet (not in-world) — the same guard the C++ used.
    let inst = unsafe { (ptr_loc as *const usize).read_unaligned() };
    if inst >= 0x10000 {
        inst
    } else {
        0
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
