//! ER Archipelago runtime client — Rust spike (Phase 1 / 3 of SPEC-rust-client-port.md).
//!
//! This crate is the in-process, injected DLL. It is intentionally a thin shell over two pure,
//! host-tested crates:
//!   * [`er_codec`]  — synthetic detection, sign-safe location-id recombine, EquipParamGoods read.
//!   * [`er_semver`] — the node-semver lockstep gate.
//!
//! Everything that needs the live game (singleton resolution, the `AddItemFunc` detour, event-flag
//! reporting) lives under `#[cfg(windows)]` and builds on `fromsoftware-rs` + `retour`. On a
//! non-Windows host this whole module compiles out, so the workspace still builds and `cargo test`s
//! in CI; only the pure logic is exercised there.
//!
//! Scope of THIS spike (SPEC §4 phase 1): prove the single biggest assumption — that the
//! `fromsoftware-rs` `eldenring` crate exposes what we need — by resolving `SoloParamRepository`
//! and logging the EquipParamGoods rowCount, then decoding one synthetic pickup end-to-end. The
//! large ER feature surface (region fusion, natural keys, progressive bells, sweeps, …) is NOT in
//! this crate yet; see SPEC §4 phase 5.

/// The client's own lockstep contract version. Must sit inside the band the apworld emits over the
/// `versions` slot_data (checked at connect via [`er_semver::version_satisfies`]). Keep in step with
/// the apworld range and the randomizer bake constant — do NOT bump during the port.
pub const CONTRACT_VERSION: &str = "0.1.0-beta.2";

/// Re-exported so the in-process layer and tests share one decision function.
pub use er_codec::{decide_pickup, decode_synthetic_row, is_synthetic_goods, PickupAction};

/// Check our contract version against a server-supplied range. Thin wrapper kept here so callers
/// don't need to know which semver crate backs it.
pub fn contract_satisfies(range: &str) -> bool {
    er_semver::version_satisfies(CONTRACT_VERSION, range).unwrap_or(false)
}

/// Format a UNIX-epoch second count as `YYYYMMDD_HHMMSS` (UTC) for log file names. Pure + host-
/// tested (Hinnant civil-from-days), so the timestamp the in-process logger stamps into the file
/// name is verified off Windows. Saturates to "00000000_000000" only if called with secs=0.
#[allow(dead_code)] // used by log_timestamp() (Windows) and the tests (any host)
pub(crate) fn fmt_utc_compact(secs: u64) -> String {
    let days = (secs / 86_400) as i64;
    let tod = secs % 86_400;
    let (hh, mm, ss) = (tod / 3600, (tod % 3600) / 60, tod % 60);
    let z = days + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = z - era * 146_097;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = if m <= 2 { y + 1 } else { y };
    format!("{:04}{:02}{:02}_{:02}{:02}{:02}", y, m, d, hh, mm, ss)
}

/// Current UTC time as `YYYYMMDD_HHMMSS` (for the per-launch log file name).
#[cfg(windows)]
pub(crate) fn log_timestamp() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    fmt_utc_compact(secs)
}

// =================================================================================================
// In-process layer (Windows only). Everything below requires the live game + fromsoftware-rs.
// =================================================================================================
//
// Lives under `#[cfg(windows)]` so the workspace still builds/tests on Linux/macOS (the modules
// below pull `eldenring` / `retour` / `windows`, which are target-gated in Cargo.toml).
#[cfg(windows)]
mod game;

/// DLL entry point.
///
/// Signature matches the me3 / libraryloader convention used across the fromsoftware-rs examples
/// (`reason == 1` is PROCESS_ATTACH). This is the loader we're converging on; for a raw OS
/// `LoadLibrary` / ModEngine2 path the 3-arg Win32 `DllMain` is needed instead — keep both behind a
/// feature if EML/ME2 support is still required (the C++ client's `StandaloneInit`-from-DllMain
/// design did exactly this; see SPEC §6).
///
/// We never do real work on the loader lock: spawn a worker thread and return immediately.
///
/// # Safety
/// Exposed for the loader to call. Do not call this yourself.
#[cfg(windows)]
// DllMain MUST be `no_mangle` + `unsafe extern "C"` so the loader can find and call it by name —
// expected here, not a code smell, so allow it on this one item (the rest of the shell stays strict).
#[allow(unsafe_code)]
#[unsafe(no_mangle)]
pub unsafe extern "C" fn DllMain(_hmodule: u64, reason: u32) -> bool {
    const DLL_PROCESS_ATTACH: u32 = 1;
    if reason == DLL_PROCESS_ATTACH {
        std::thread::spawn(|| game::init());
    }
    true
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn timestamp_format_matches_reference() {
        // Reference values cross-checked against Python datetime.utcfromtimestamp.
        assert_eq!(fmt_utc_compact(0), "19700101_000000");
        assert_eq!(fmt_utc_compact(1_700_000_000), "20231114_221320");
        assert_eq!(fmt_utc_compact(1_750_700_000), "20250623_173320");
        assert_eq!(fmt_utc_compact(253_402_300_799), "99991231_235959");
    }

    #[test]
    fn contract_version_is_in_its_own_band() {
        // The lockstep band SYNC-RUNBOOK.md documents; our CONTRACT_VERSION must satisfy it.
        assert!(contract_satisfies(">=0.1.0-beta.2 <0.1.0-beta.3"));
        assert!(!contract_satisfies(">=0.1.0 <0.2.0")); // pre-release rejected by graduated band
    }

    #[test]
    fn end_to_end_decode_through_reexport() {
        // A synthetic local-replacement goods placeholder decodes + routes to SuppressAndGrant.
        let mut row = [0u8; er_codec::EQG_ROW_SIZE];
        row[er_codec::EQG_OFF_VAGRANT_ITEM_LOT_ID..][..4].copy_from_slice(&7_004_362i32.to_le_bytes());
        row[er_codec::EQG_OFF_BASIC_PRICE..][..4].copy_from_slice(&1_000_000i32.to_le_bytes());
        row[er_codec::EQG_OFF_SELL_VALUE..][..4].copy_from_slice(&1i32.to_le_bytes());
        let item = decode_synthetic_row(&row).unwrap();
        assert_eq!(item.ap_location_id, 7_004_362);
        assert_eq!(decide_pickup(&item), PickupAction::SuppressAndGrant);
        assert!(is_synthetic_goods(er_codec::CATEGORY_GOODS | 4_000_000));
    }
}
