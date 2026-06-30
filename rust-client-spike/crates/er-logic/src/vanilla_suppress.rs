//! Pure decision for the pure-runtime MVP: should an item the game is about to add to the
//! player's bag be SUPPRESSED because it is the vanilla contents of an AP check location?
//!
//! In vanilla-placement (no item randomizer) the lot at a check still carries its real vanilla
//! item. The acquisition FLAG is set by the ItemLot/EMEVD path (that's what `location_check.rs`
//! polls) — independently of `AddItemFunc`. So we can null the bag-add (`AddItemFunc` -> 0)
//! without losing detection. This module owns *which ids* to null; `detour.rs` owns the I/O.
//!
//! Two fidelities, selected by how the table is built:
//!   * id-set         — suppress every copy of a check item id (correct for UNIQUE check items;
//!                      over-suppresses stackable generics that also drop off-check).
//!   * flag-gated     — suppress a check item id ONLY while one of its guarding flags is still
//!                      unset (the completing pickup). Later copies pass through. Recommended.

use std::collections::{HashMap, HashSet};

/// Suppression table, built once at connect from slot_data.
pub struct VanillaSuppressor {
    /// Category-tagged FullIDs (`item_id | category`) that are the vanilla contents of a check.
    check_item_ids: HashSet<i32>,
    /// FullID -> guarding acquisition flags. Empty map => pure id-set mode (always suppress a
    /// known check id). Non-empty => flag-gated (suppress only while a guarding flag is unset).
    item_to_flags: HashMap<i32, Vec<u32>>,
}

impl VanillaSuppressor {
    /// id-set mode: suppress every copy of a check item id. Simplest; correct for unique items.
    pub fn id_set(check_item_ids: HashSet<i32>) -> Self {
        VanillaSuppressor { check_item_ids, item_to_flags: HashMap::new() }
    }

    /// flag-gated mode: suppress a check id only while one of its guarding flags is still unset.
    /// `item_to_flags` is derived from the vanilla placement + `locationFlags`.
    pub fn flag_gated(item_to_flags: HashMap<i32, Vec<u32>>) -> Self {
        let check_item_ids = item_to_flags.keys().copied().collect();
        VanillaSuppressor { check_item_ids, item_to_flags }
    }

    /// Pick the suppression mode from the two parsed slot_data tables (see `crate::slot_data`).
    /// Returns `None` => install NO suppressor (the detour behaves exactly as on the bake path).
    /// Precedence mirrors the connect path in `net.rs`: flag-gated (richest) > id-set > none.
    pub fn from_slot_data(
        check_item_flags: HashMap<i32, Vec<u32>>,
        check_item_ids: HashSet<i32>,
    ) -> Option<Self> {
        if !check_item_flags.is_empty() {
            Some(Self::flag_gated(check_item_flags))
        } else if !check_item_ids.is_empty() {
            Some(Self::id_set(check_item_ids))
        } else {
            None
        }
    }

    /// The decision, called from the detour with the inbound `entry+0x04` FullID.
    ///
    /// `get_flag` reads a live event flag (the same closure `location_check::poll` takes). Pure:
    /// no game types, fully host-testable. Returns true => detour should `return 0` (suppress).
    pub fn should_suppress(&self, full_id: i32, get_flag: &dyn Fn(u32) -> bool) -> bool {
        if !self.check_item_ids.contains(&full_id) {
            return false; // not a check item — never touch it
        }
        match self.item_to_flags.get(&full_id) {
            // id-set mode (no flag data): always suppress a known check id.
            None => true,
            // flag-gated: suppress only if SOME guarding flag is still unset (check not yet
            // completed). Once every guarding flag is set, later copies pass through.
            Some(flags) => flags.iter().any(|&f| !get_flag(f)),
        }
    }

    /// Diagnostic: how many distinct check item ids are in the table.
    pub fn len(&self) -> usize {
        self.check_item_ids.len()
    }
    pub fn is_empty(&self) -> bool {
        self.check_item_ids.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn set(v: &[i32]) -> HashSet<i32> {
        v.iter().copied().collect()
    }

    const GOODS: i32 = 0x4000_0000u32 as i32;

    #[test]
    fn id_set_suppresses_known_check_item() {
        let s = VanillaSuppressor::id_set(set(&[GOODS | 8_000]));
        assert!(s.should_suppress(GOODS | 8_000, &|_| false));
    }

    #[test]
    fn id_set_passes_unknown_item() {
        let s = VanillaSuppressor::id_set(set(&[GOODS | 8_000]));
        assert!(!s.should_suppress(GOODS | 9_999, &|_| true));
    }

    #[test]
    fn flag_gated_suppresses_while_flag_unset() {
        // FullID 8000 guarded by flag 110260; flag still unset => suppress the completing pickup.
        let mut m = HashMap::new();
        m.insert(GOODS | 8_000, vec![110260u32]);
        let s = VanillaSuppressor::flag_gated(m);
        assert!(s.should_suppress(GOODS | 8_000, &|_| false));
    }

    #[test]
    fn flag_gated_passes_after_check_completed() {
        // Same id, but its guarding flag is now SET => the check already fired; a later copy of
        // this (possibly generic) item must pass through to the bag.
        let mut m = HashMap::new();
        m.insert(GOODS | 8_000, vec![110260u32]);
        let s = VanillaSuppressor::flag_gated(m);
        assert!(!s.should_suppress(GOODS | 8_000, &|f| f == 110260));
    }

    #[test]
    fn flag_gated_multi_flag_suppresses_until_all_set() {
        // Multi-item lot: id guarded by two flags; suppress while ANY is still unset.
        let mut m = HashMap::new();
        m.insert(GOODS | 8_000, vec![400148u32, 400149u32]);
        let s = VanillaSuppressor::flag_gated(m);
        assert!(s.should_suppress(GOODS | 8_000, &|f| f == 400148)); // 400149 still unset
        assert!(!s.should_suppress(GOODS | 8_000, &|f| f == 400148 || f == 400149));
    }

    #[test]
    fn non_check_item_never_suppressed_even_with_flag_data() {
        let mut m = HashMap::new();
        m.insert(GOODS | 8_000, vec![110260u32]);
        let s = VanillaSuppressor::flag_gated(m);
        assert!(!s.should_suppress(GOODS | 7_777, &|_| false));
    }

    // --- from_slot_data mode selection (Extraction 2) --------------------------------------------
    #[test]
    fn from_slot_data_picks_flag_gated_when_flags_present() {
        let mut m = HashMap::new();
        m.insert(GOODS | 8_000, vec![110260u32]);
        let s = VanillaSuppressor::from_slot_data(m, set(&[GOODS | 9_999])).unwrap();
        // flag-gated: known id suppresses while its flag is unset, passes once set.
        assert!(s.should_suppress(GOODS | 8_000, &|_| false));
        assert!(!s.should_suppress(GOODS | 8_000, &|f| f == 110260));
    }

    #[test]
    fn from_slot_data_falls_back_to_id_set_when_only_ids() {
        let s = VanillaSuppressor::from_slot_data(HashMap::new(), set(&[GOODS | 8_000])).unwrap();
        // id-set: always suppress a known id regardless of flags.
        assert!(s.should_suppress(GOODS | 8_000, &|_| true));
    }

    #[test]
    fn from_slot_data_none_when_both_empty() {
        assert!(VanillaSuppressor::from_slot_data(HashMap::new(), HashSet::new()).is_none());
    }

    #[test]
    fn from_slot_data_flags_win_when_both_present() {
        let mut m = HashMap::new();
        m.insert(GOODS | 8_000, vec![110260u32]);
        let s = VanillaSuppressor::from_slot_data(m, set(&[GOODS | 8_000])).unwrap();
        // flag-gated mode chosen => id passes once its flag is set (id-set mode would NOT).
        assert!(!s.should_suppress(GOODS | 8_000, &|f| f == 110260));
    }
}
