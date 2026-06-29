//! `er-logic` — pure + seam-based, host-compiled, unit-tested decision logic lifted out of the
//! Windows-gated `eldenring-ap` game modules. No `eldenring` / `windows` / `archipelago_rs` / socket
//! deps, so CI runs every test on any host (alongside `er-codec` / `er-semver`).
//!
//! PURE modules (no game at all): [`receive`], [`version`], [`save_state`], [`progressive`],
//! [`region_lock`], [`options`].
//! SEAM modules (game side effects via the [`hook::GameHook`] trait + `FakeGame` mock): [`deathlink`],
//! [`grace`], [`grants`], [`upgrades`]. The real `EldenRingHook` impl lives in `eldenring-ap`
//! (`#[cfg(windows)]`).
//!
//! See SHARED-CONVERGENCE-PLAN.md.

pub mod deathlink;
pub mod detour_decide;
pub mod grace;
pub mod grants;
pub mod hook;
pub mod location_check;
pub mod name_override;
pub mod options;
pub mod progressive;
pub mod receive;
pub mod region_lock;
pub mod save_state;
pub mod slot_data;
pub mod upgrades;
pub mod vanilla_suppress;
pub mod version;
