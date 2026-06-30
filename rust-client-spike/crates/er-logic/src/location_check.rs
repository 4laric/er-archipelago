//! Pure location-check detection for the pure-runtime (no-baker) loop.
//!
//! The decision half only, in the `region_lock.rs` mould: poll vanilla acquisition flags
//! via a `get_flag` closure and return the AP location ids newly completed this tick. The
//! Windows side (`eldenring-ap`) ticks this against the live `GameHook` and sends the
//! returned ids over the AP client. Suppressing the vanilla item grant is a SEPARATE
//! concern (the item-acquisition detour) — detection never depends on it.
//!
//! Data source: the apworld now emits `locationFlags` in slot_data (location_id -> flag),
//! sourced from the static vanilla acquisition-flag table. No SoulsRandomizers at runtime.

use std::collections::{HashMap, HashSet};

/// Detection table + per-session fired set. Built once at connect from `locationFlags`.
pub struct LocationChecks {
    /// flag -> location ids that complete when it sets. >1 entry = a multi-item lot
    /// (one pickup sets one flag and completes all its checks at once).
    by_flag: HashMap<u32, Vec<i64>>,
    /// flags already observed set this session, so each reports exactly once.
    fired: HashSet<u32>,
}

impl LocationChecks {
    /// Build from slot_data `locationFlags` (location_id -> acquisition flag).
    pub fn from_location_flags(location_flags: &HashMap<i64, u32>) -> Self {
        let mut by_flag: HashMap<u32, Vec<i64>> = HashMap::new();
        for (&loc, &flag) in location_flags {
            by_flag.entry(flag).or_default().push(loc);
        }
        LocationChecks { by_flag, fired: HashSet::new() }
    }

    /// Seed the fired set from the server's already-checked locations (sent at connect) so a
    /// reconnect mid-run doesn't re-report. A flag counts as fired only once ALL its locations
    /// are already checked (a partially-checked multi-item lot can still report the rest).
    pub fn prime_checked(&mut self, checked: &HashSet<i64>) {
        for (&flag, locs) in &self.by_flag {
            if locs.iter().all(|l| checked.contains(l)) {
                self.fired.insert(flag);
            }
        }
    }

    /// One tick. Returns AP location ids newly completed since the last poll. Off-world the
    /// flag holder is unreliable, so report nothing (matches the in-world gating elsewhere).
    pub fn poll(&mut self, in_world: bool, get_flag: &dyn Fn(u32) -> bool) -> Vec<i64> {
        if !in_world {
            return Vec::new();
        }
        let mut out = Vec::new();
        let mut newly = Vec::new();
        for (&flag, locs) in &self.by_flag {
            if !self.fired.contains(&flag) && get_flag(flag) {
                newly.push(flag);
                out.extend(locs.iter().copied());
            }
        }
        for f in newly {
            self.fired.insert(f);
        }
        out
    }

    /// Total distinct flags polled (diagnostic / sanity).
    pub fn flag_count(&self) -> usize {
        self.by_flag.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn lf(pairs: &[(i64, u32)]) -> HashMap<i64, u32> {
        pairs.iter().copied().collect()
    }
    fn set(v: &[i64]) -> HashSet<i64> {
        v.iter().copied().collect()
    }

    #[test]
    fn fires_location_when_its_flag_sets() {
        let mut lc = LocationChecks::from_location_flags(&lf(&[(7000578, 110260)]));
        assert!(lc.poll(true, &|_| false).is_empty());
        assert_eq!(lc.poll(true, &|f| f == 110260), vec![7000578]);
    }

    #[test]
    fn fires_once_only() {
        let mut lc = LocationChecks::from_location_flags(&lf(&[(7000578, 110260)]));
        assert_eq!(lc.poll(true, &|f| f == 110260), vec![7000578]);
        assert!(lc.poll(true, &|f| f == 110260).is_empty());
    }

    #[test]
    fn shared_flag_reports_all_its_locations() {
        // multi-item lot: one flag (400148) -> 3 checks, all fire together.
        let mut lc = LocationChecks::from_location_flags(&lf(&[
            (7003910, 400148),
            (7003911, 400148),
            (7003912, 400148),
        ]));
        let mut got = lc.poll(true, &|f| f == 400148);
        got.sort();
        assert_eq!(got, vec![7003910, 7003911, 7003912]);
    }

    #[test]
    fn off_world_reports_nothing() {
        let mut lc = LocationChecks::from_location_flags(&lf(&[(7000578, 110260)]));
        assert!(lc.poll(false, &|_| true).is_empty());
    }

    #[test]
    fn primed_checked_locations_do_not_refire() {
        let mut lc = LocationChecks::from_location_flags(&lf(&[(7000578, 110260)]));
        lc.prime_checked(&set(&[7000578]));
        assert!(lc.poll(true, &|f| f == 110260).is_empty());
    }

    #[test]
    fn partially_checked_lot_still_reports_the_rest() {
        let mut lc = LocationChecks::from_location_flags(&lf(&[
            (7003910, 400148),
            (7003911, 400148),
        ]));
        lc.prime_checked(&set(&[7003910])); // only one of the two pre-checked
        let mut got = lc.poll(true, &|f| f == 400148);
        got.sort();
        assert_eq!(got, vec![7003910, 7003911]); // flag wasn't fully fired, so reports both
    }
}
