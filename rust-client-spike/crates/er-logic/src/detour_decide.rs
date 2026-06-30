//! Pure decision for the `AddItemFunc` detour body, lifted out of the `#[cfg(windows)]`
//! `eldenring-ap::game::detour::add_item_detour` so the branch ordering runs under `cargo test`.
//!
//! The detour reads the inbound FullID, then has to choose one of three outcomes. The unsafe I/O —
//! reading `entry+0x04`, the `params` row fetch, calling the trampoline, enqueuing the report — stays
//! in `detour.rs`. This module owns only the *decision*, expressed over closures so it's host-testable
//! (mirrors how `should_suppress` / `LocationChecks::poll` already take a `get_flag` closure).
//!
//! Ordering is load-bearing and matches `detour.rs`: pure-runtime vanilla suppression is checked
//! FIRST and short-circuits — a vanilla check item is nulled here and reported via flag-polling
//! (`location_check`), never through the synthetic path.

use crate::vanilla_suppress::VanillaSuppressor;

/// What the detour should do with an inbound `AddItemFunc` call.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DetourAction {
    /// `return 0` — drop the bag-add. Vanilla contents of an AP check (pure-runtime suppression);
    /// detection happens independently via the acquisition flag poll.
    Suppress,
    /// Call the original `AddItemFunc` via the trampoline — an ordinary item, not ours.
    PassThrough,
    /// Report this AP location id, then `return 0`. A synthetic carrier (bake path): the real item
    /// is granted by the server echo, not locally.
    ReportThenSuppress(i64),
}

/// Decide the detour outcome for `raw_id` (the `entry+0x04` FullID, category nibble included).
///
/// * `suppressor` — the connect-built table, or `None` on the bake path (no suppression configured).
/// * `get_flag` — live event-flag read (same closure `should_suppress` takes).
/// * `resolve_synthetic` — wraps the I/O of `is_synthetic_goods` + the `params` goods-row read +
///   `decode_synthetic`, returning the AP location id, or `None` when the id is NOT a synthetic
///   carrier OR its row can't be resolved. Both `None` cases pass through, matching `detour.rs`.
pub fn decide_detour_action(
    raw_id: i32,
    suppressor: Option<&VanillaSuppressor>,
    get_flag: &dyn Fn(u32) -> bool,
    resolve_synthetic: &dyn Fn(i32) -> Option<i64>,
) -> DetourAction {
    // Pure-runtime vanilla suppression short-circuits BEFORE any synthetic handling.
    if suppressor.map_or(false, |s| s.should_suppress(raw_id, get_flag)) {
        return DetourAction::Suppress;
    }
    match resolve_synthetic(raw_id) {
        Some(loc) => DetourAction::ReportThenSuppress(loc),
        None => DetourAction::PassThrough,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;

    const GOODS: i32 = 0x4000_0000u32 as i32;

    fn id_set(v: &[i32]) -> VanillaSuppressor {
        VanillaSuppressor::id_set(v.iter().copied().collect::<HashSet<i32>>())
    }

    // bake path: no suppressor, ordinary item -> pass through.
    #[test]
    fn no_suppressor_non_synthetic_passes_through() {
        let act = decide_detour_action(GOODS | 1234, None, &|_| false, &|_| None);
        assert_eq!(act, DetourAction::PassThrough);
    }

    // bake path: no suppressor, synthetic carrier resolves -> report + suppress.
    #[test]
    fn no_suppressor_synthetic_reports_and_suppresses() {
        let act = decide_detour_action(GOODS | 1234, None, &|_| false, &|_| Some(7001091));
        assert_eq!(act, DetourAction::ReportThenSuppress(7001091));
    }

    // synthetic id but its goods row can't be resolved -> pass through (matches detour.rs warn+orig).
    #[test]
    fn synthetic_unresolved_passes_through() {
        let act = decide_detour_action(GOODS | 1234, None, &|_| true, &|_| None);
        assert_eq!(act, DetourAction::PassThrough);
    }

    // pure-runtime: a configured check item with its flag unset -> suppress.
    #[test]
    fn suppressor_hit_suppresses() {
        let sup = id_set(&[GOODS | 8000]);
        let act = decide_detour_action(GOODS | 8000, Some(&sup), &|_| false, &|_| None);
        assert_eq!(act, DetourAction::Suppress);
    }

    // ORDERING GUARD: suppression wins even when the same id would ALSO resolve as synthetic — it
    // must short-circuit before resolve_synthetic, so the result is Suppress, NOT ReportThenSuppress.
    #[test]
    fn suppressor_short_circuits_before_synthetic() {
        let sup = id_set(&[GOODS | 8000]);
        let act = decide_detour_action(
            GOODS | 8000,
            Some(&sup),
            &|_| false,
            &|_| panic!("resolve_synthetic must not run once suppression fires"),
        );
        assert_eq!(act, DetourAction::Suppress);
    }

    // a configured suppressor does NOT block normal synthetic handling of a DIFFERENT id.
    #[test]
    fn suppressor_present_but_unmatched_still_handles_synthetic() {
        let sup = id_set(&[GOODS | 8000]);
        let act = decide_detour_action(GOODS | 9999, Some(&sup), &|_| false, &|_| Some(7000838));
        assert_eq!(act, DetourAction::ReportThenSuppress(7000838));
    }
}
