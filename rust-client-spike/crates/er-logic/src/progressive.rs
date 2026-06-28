//! Pure progressive-item tier logic, extracted from `progressive.rs` `on_item_received`.
//!
//! Tier-by-receipt with post-increment; a replay (`ap_index <= high_index`) is `handled` but
//! advances no tier; overflowing past the last tier queues one Lord's Rune. `handled == true`
//! tells the receive loop to SKIP the normal grant. The slot_data `parse` step (config build) is
//! deferred to PR-B, where it's lifted from the real `progressive::parse`.

use std::collections::HashMap;

/// Goods category nibble, packed into a FullID so the grant path routes it as `EquipParamGoods`.
pub const GOODS_FULLID: i32 = 0x4000_0000u32 as i32;
/// Lord's Rune goods row, granted once per overflow copy past the last tier.
pub const LORDS_RUNE_GOODS: u32 = 2919;

/// One progressive tier: the goods to grant and the flags to set when this tier lands.
#[derive(Debug, Clone, PartialEq)]
pub struct ProgTier {
    pub goods: Vec<u32>,
    pub flags: Vec<u32>,
}

/// The effects of receiving one progressive item. `handled` => caller skips the normal grant.
#[derive(Debug, PartialEq)]
pub struct ProgEffects {
    pub flags: Vec<u32>,
    pub grants: Vec<i32>,
    pub handled: bool,
}

/// Per-name tier counter + the index-dedup watermark, instance-scoped (no statics) so tests get
/// fresh state.
pub struct ProgressiveState {
    config: HashMap<String, Vec<ProgTier>>,
    counter: HashMap<String, i32>,
    high_index: i64,
}

impl ProgressiveState {
    pub fn new(config: HashMap<String, Vec<ProgTier>>) -> Self {
        Self {
            config,
            counter: HashMap::new(),
            high_index: -1,
        }
    }

    pub fn restore(&mut self, counter: HashMap<String, i32>, high_index: i64) {
        self.counter = counter;
        self.high_index = high_index;
    }

    pub fn snapshot(&self) -> (HashMap<String, i32>, i64) {
        (self.counter.clone(), self.high_index)
    }

    /// Mirror of `on_item_received`: returns the queued effects rather than mutating queues.
    pub fn on_item_received(&mut self, name: &str, ap_index: i64) -> ProgEffects {
        let tiers = match self.config.get(name) {
            Some(t) => t.clone(),
            None => {
                return ProgEffects {
                    flags: vec![],
                    grants: vec![],
                    handled: false,
                }
            }
        };
        if ap_index <= self.high_index {
            // Replay of an already-applied copy: skip the normal grant, advance no tier.
            return ProgEffects {
                flags: vec![],
                grants: vec![],
                handled: true,
            };
        }
        let k = {
            let slot = self.counter.entry(name.to_string()).or_insert(0);
            let k = *slot;
            *slot += 1;
            k
        };
        let mut eff = ProgEffects {
            flags: vec![],
            grants: vec![],
            handled: true,
        };
        if (k as usize) < tiers.len() {
            let tier = &tiers[k as usize];
            eff.flags.extend(tier.flags.iter().copied());
            eff.grants
                .extend(tier.goods.iter().map(|&g| (g as i32) | GOODS_FULLID));
        } else {
            eff.grants.push((LORDS_RUNE_GOODS as i32) | GOODS_FULLID);
        }
        self.high_index = ap_index;
        eff
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn bell() -> HashMap<String, Vec<ProgTier>> {
        let mut m = HashMap::new();
        m.insert(
            "progressive_stone_bell".into(),
            vec![
                ProgTier { goods: vec![8101], flags: vec![70001] },
                ProgTier { goods: vec![8102], flags: vec![70002] },
            ],
        );
        m
    }

    #[test]
    fn tier_advances_once_per_matching_receipt() {
        let mut p = ProgressiveState::new(bell());

        let e0 = p.on_item_received("progressive_stone_bell", 0);
        assert!(e0.handled, "progressive item -> caller skips normal grant");
        assert_eq!(e0.grants, vec![8101 | GOODS_FULLID]);
        assert_eq!(e0.flags, vec![70001]);

        let e1 = p.on_item_received("progressive_stone_bell", 1);
        assert_eq!(e1.grants, vec![8102 | GOODS_FULLID]);
        assert_eq!(e1.flags, vec![70002]);

        // Overflow past the last tier -> exactly one Lord's Rune, no flags.
        let e2 = p.on_item_received("progressive_stone_bell", 2);
        assert!(e2.handled);
        assert_eq!(e2.grants, vec![(LORDS_RUNE_GOODS as i32) | GOODS_FULLID]);
        assert!(e2.flags.is_empty());

        let (counter, high) = p.snapshot();
        assert_eq!(counter["progressive_stone_bell"], 3);
        assert_eq!(high, 2);
    }

    #[test]
    fn non_progressive_item_is_not_handled() {
        let mut p = ProgressiveState::new(bell());
        let e = p.on_item_received("Crimson Tear", 0);
        assert!(!e.handled, "unknown item -> caller grants it normally");
        assert!(e.grants.is_empty() && e.flags.is_empty());
    }

    #[test]
    fn restored_counter_resumes_tiers_and_skips_replay() {
        let mut p = ProgressiveState::new(bell());
        let mut restored = HashMap::new();
        restored.insert("progressive_stone_bell".to_string(), 1);
        p.restore(restored, /*high_index*/ 0);

        // Replayed copy idx 0 (<= high) is handled but advances NO tier.
        let replay = p.on_item_received("progressive_stone_bell", 0);
        assert!(replay.handled);
        assert!(
            replay.grants.is_empty() && replay.flags.is_empty(),
            "replay must NOT re-grant an already-applied tier"
        );

        // The next genuinely-new copy (idx 1) resumes at tier 1, not tier 0.
        let next = p.on_item_received("progressive_stone_bell", 1);
        assert_eq!(next.grants, vec![8102 | GOODS_FULLID], "resumes at tier 1 after restore");
        assert_eq!(p.snapshot().1, 1);
    }
}
/// Parse `progressiveGrants` slot_data into the per-name tier config. Tolerant: a tier may carry
/// `goodsList` (array) or `goods` (single), plus optional `flags`; a fully-empty tier is dropped
/// (the deliberate fix for the C++ "key goods not found" abort). Absent key -> empty config.
pub fn parse(slot_data: &serde_json::Value) -> HashMap<String, Vec<ProgTier>> {
    let mut out = HashMap::new();
    let Some(obj) = slot_data.get("progressiveGrants").and_then(|v| v.as_object()) else {
        return out;
    };
    for (name, tiers_v) in obj {
        let Some(arr) = tiers_v.as_array() else { continue };
        let mut tiers = Vec::new();
        for t in arr {
            let goods = t
                .get("goodsList")
                .and_then(|v| v.as_array())
                .map(|a| a.iter().filter_map(|n| n.as_u64().map(|n| n as u32)).collect::<Vec<_>>())
                .or_else(|| t.get("goods").and_then(|v| v.as_u64()).map(|g| vec![g as u32]))
                .unwrap_or_default();
            let flags = t
                .get("flags")
                .and_then(|v| v.as_array())
                .map(|a| a.iter().filter_map(|n| n.as_u64().map(|n| n as u32)).collect::<Vec<_>>())
                .unwrap_or_default();
            if goods.is_empty() && flags.is_empty() {
                continue; // drop empty tier
            }
            tiers.push(ProgTier { goods, flags });
        }
        if !tiers.is_empty() {
            out.insert(name.clone(), tiers);
        }
    }
    out
}

#[cfg(test)]
mod parse_tests {
    use super::*;

    #[test]
    fn parse_is_tolerant_and_drops_empty_tiers() {
        let sd = serde_json::json!({ "progressiveGrants": {
            "progressive_physick": [
                { "goodsList": [1001, 1002], "flags": [60001] },
                { "goods": 1003 },
                { "flags": [60002] },
                { "junk": true }
            ]
        }});
        let map = parse(&sd);
        let tiers = &map["progressive_physick"];
        assert_eq!(tiers.len(), 3, "the fully-empty tier is dropped, not fatal");
        assert_eq!(tiers[0].goods, vec![1001, 1002]);
        assert_eq!(tiers[0].flags, vec![60001]);
        assert_eq!(tiers[1].goods, vec![1003]);
        assert!(tiers[2].goods.is_empty() && tiers[2].flags == vec![60002]);
    }

    #[test]
    fn parse_absent_key_is_empty() {
        assert!(parse(&serde_json::json!({ "seed": "x" })).is_empty());
    }
}
