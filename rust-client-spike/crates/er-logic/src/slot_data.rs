//! Pure, tolerant slot_data JSON -> typed-map parsers, lifted out of the `#[cfg(windows)]`
//! `eldenring-ap::game::net` connect path so they run under `cargo test` on any host.
//!
//! Every parser is TOLERANT by design: a malformed / extra / wrong-typed entry is skipped, never
//! an error — a bad slot_data field must not fail the CONNECTION (the connect handler reads the
//! whole blob field-by-field with defaults). The regression these guard against is the one that ate
//! the first pure-runtime walk-up: a parser silently returning an empty map => detection or
//! suppression has nothing to work with.
//!
//! Signatures take `Option<&serde_json::Value>` so call sites stay `f(sd.get("key"))` verbatim.

use std::collections::{HashMap, HashSet};

use serde_json::Value;

/// `{ "<i64>": <i64> }` object -> `i64 -> i64` (the AP convention for `apIdsToItemIds` /
/// `itemCounts`; keys are stringified ints). Tolerant: skips any entry that doesn't parse.
pub fn i64_map(v: Option<&Value>) -> HashMap<i64, i64> {
    let mut m = HashMap::new();
    if let Some(Value::Object(o)) = v {
        for (k, val) in o {
            if let (Ok(ki), Some(vi)) = (k.parse::<i64>(), val.as_i64()) {
                m.insert(ki, vi);
            }
        }
    }
    m
}

/// `{ "<i64>": <u32> }` object -> `i64 -> u32` (the pure-runtime `locationFlags`: AP location id ->
/// vanilla acquisition flag). Tolerant: skips any entry that doesn't parse.
pub fn i64_to_u32_map(v: Option<&Value>) -> HashMap<i64, u32> {
    let mut m = HashMap::new();
    if let Some(Value::Object(o)) = v {
        for (k, val) in o {
            if let (Ok(ki), Some(vi)) = (k.parse::<i64>(), val.as_u64()) {
                m.insert(ki, vi as u32);
            }
        }
    }
    m
}

/// `[ <i32>, ... ]` array -> `HashSet<i32>` (the pure-runtime `checkItemIds`: category-packed
/// FullIDs that are the vanilla contents of a check). Tolerant: skips non-ints.
pub fn i32_set(v: Option<&Value>) -> HashSet<i32> {
    let mut s = HashSet::new();
    if let Some(arr) = v.and_then(|x| x.as_array()) {
        for x in arr {
            if let Some(n) = x.as_i64() {
                s.insert(n as i32);
            }
        }
    }
    s
}

/// `{ "<i32>": [<u32>, ...] }` object -> `i32 -> Vec<u32>` (the pure-runtime `checkItemFlags`:
/// check FullID -> guarding acquisition flags). Tolerant: skips a non-array value or unparseable
/// key, and filters non-numeric elements out of an otherwise-good list.
pub fn i32_to_u32vec_map(v: Option<&Value>) -> HashMap<i32, Vec<u32>> {
    let mut m = HashMap::new();
    if let Some(Value::Object(o)) = v {
        for (k, val) in o {
            if let (Ok(ki), Some(arr)) = (k.parse::<i32>(), val.as_array()) {
                m.insert(ki, arr.iter().filter_map(|x| x.as_u64().map(|n| n as u32)).collect());
            }
        }
    }
    m
}

/// `{ "<name>": <u32> }` object -> `String -> u32` (e.g. `graceItems` / `regionOpenFlags`).
/// Tolerant: skips non-numeric values.
///
/// NOTE: reconstructed from its contract + the identical sibling pattern above because the sandbox
/// truncated the tail of net.rs at this function — diff against the real `net::str_to_u32` body when
/// wiring on Windows (it is the same shape).
pub fn str_to_u32(v: Option<&Value>) -> HashMap<String, u32> {
    let mut m = HashMap::new();
    if let Some(Value::Object(o)) = v {
        for (k, val) in o {
            if let Some(vi) = val.as_u64() {
                m.insert(k.clone(), vi as u32);
            }
        }
    }
    m
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    // --- i64_to_u32_map (locationFlags) -----------------------------------------------------------
    #[test]
    fn loc_flags_happy_path() {
        let v = json!({ "7001091": 110260, "7000838": 62050 });
        let m = i64_to_u32_map(Some(&v));
        assert_eq!(m.len(), 2);
        assert_eq!(m[&7001091], 110260u32);
        assert_eq!(m[&7000838], 62050u32);
    }

    #[test]
    fn loc_flags_skips_non_numeric_value_and_key() {
        // good entry kept; non-numeric value dropped; non-int key dropped — tolerance, not failure.
        let v = json!({ "7001091": 110260, "7000838": "nope", "notanint": 5 });
        let m = i64_to_u32_map(Some(&v));
        assert_eq!(m.len(), 1);
        assert!(m.contains_key(&7001091));
    }

    #[test]
    fn loc_flags_missing_or_wrong_shape_is_empty() {
        assert!(i64_to_u32_map(None).is_empty()); // key absent in slot_data
        assert!(i64_to_u32_map(Some(&json!([1, 2, 3]))).is_empty()); // not an object
        assert!(i64_to_u32_map(Some(&json!("x"))).is_empty());
    }

    // --- i32_set (checkItemIds) -------------------------------------------------------------------
    #[test]
    fn check_item_ids_happy_path() {
        let v = json!([1073741824, -8000, 42]);
        let s = i32_set(Some(&v));
        assert_eq!(s.len(), 3);
        assert!(s.contains(&1073741824));
        assert!(s.contains(&-8000));
    }

    #[test]
    fn check_item_ids_skips_non_int_elements() {
        let v = json!([8000, "nope", null, 9000]);
        let s = i32_set(Some(&v));
        assert_eq!(s, HashSet::from([8000, 9000]));
    }

    #[test]
    fn check_item_ids_missing_or_non_array_is_empty() {
        assert!(i32_set(None).is_empty());
        assert!(i32_set(Some(&json!({ "a": 1 }))).is_empty());
    }

    // --- i32_to_u32vec_map (checkItemFlags) -------------------------------------------------------
    #[test]
    fn check_item_flags_happy_path() {
        let v = json!({ "8000": [110260], "9000": [400148, 400149] });
        let m = i32_to_u32vec_map(Some(&v));
        assert_eq!(m[&8000], vec![110260u32]);
        assert_eq!(m[&9000], vec![400148u32, 400149u32]);
    }

    #[test]
    fn check_item_flags_skips_non_array_value_and_bad_key() {
        let v = json!({ "8000": [110260], "9000": 5, "xx": [1] });
        let m = i32_to_u32vec_map(Some(&v));
        assert_eq!(m.len(), 1);
        assert!(m.contains_key(&8000));
    }

    #[test]
    fn check_item_flags_filters_non_numeric_elements_within_a_list() {
        // a good list that contains junk keeps the numeric members (empty vec if all junk, NOT dropped).
        let v = json!({ "8000": [110260, "x", null, 400149] });
        let m = i32_to_u32vec_map(Some(&v));
        assert_eq!(m[&8000], vec![110260u32, 400149u32]);
    }

    #[test]
    fn check_item_flags_missing_is_empty() {
        assert!(i32_to_u32vec_map(None).is_empty());
    }

    // --- i64_map (apIdsToItemIds / itemCounts) ----------------------------------------------------
    #[test]
    fn i64_map_happy_and_tolerant() {
        let v = json!({ "100": 7, "200": -3, "bad": 1, "300": "no" });
        let m = i64_map(Some(&v));
        assert_eq!(m.len(), 2);
        assert_eq!(m[&100], 7);
        assert_eq!(m[&200], -3);
    }

    #[test]
    fn i64_map_missing_is_empty() {
        assert!(i64_map(None).is_empty());
    }

    // --- str_to_u32 (graceItems / regionOpenFlags) ------------------------------------------------
    #[test]
    fn str_to_u32_happy_and_tolerant() {
        let v = json!({ "Roundtable": 71190, "FirstStep": 60100, "bad": "x" });
        let m = str_to_u32(Some(&v));
        assert_eq!(m.len(), 2);
        assert_eq!(m["Roundtable"], 71190u32);
        assert_eq!(m["FirstStep"], 60100u32);
    }

    #[test]
    fn str_to_u32_missing_is_empty() {
        assert!(str_to_u32(None).is_empty());
    }
}
