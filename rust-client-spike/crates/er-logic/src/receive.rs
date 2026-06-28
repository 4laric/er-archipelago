//! Pure AP receive-loop decision core, extracted from the Windows-gated `net.rs`.
//!
//! No socket, no `archipelago_rs`, no game deps — so it compiles and `cargo test`s on any host.
//! The net loop maps each `archipelago_rs` received item into a [`RecvItem`], calls
//! [`process_received_item`], and translates the [`GrantAction`] into the real `grant::enqueue` /
//! warn. The two-watermark split is the reconnect-safety invariant this module locks down.

use std::collections::HashMap;

/// A received item, mirrored out of `archipelago_rs`'s `received_items()` so this logic never
/// touches the wire type. The net loop builds one per item from `index()`, `item().id()`,
/// `item().name()`.
#[derive(Clone, Debug, PartialEq)]
pub struct RecvItem {
    pub index: i64,
    pub ap_item_id: i64,
    pub name: String,
}

/// What the loop should do with one received item after the watermark split.
#[derive(Clone, Debug, PartialEq)]
pub enum GrantAction {
    /// Enqueue this FullID x qty (ap_index carried for persistence dedup).
    Enqueue {
        full_id: i32,
        qty: i32,
        ap_index: i64,
        name: String,
    },
    /// Progressive item — carries its own grant queue; the normal grant is skipped
    /// (mirror of the C++ client's `continue`).
    SkipProgressive,
    /// AP item id not in `apIdsToItemIds` — `net.rs` warns and skips.
    SkipUnmapped { ap_item_id: i64 },
    /// Below the `pushed_through` watermark — already granted on a previous connect; do nothing.
    AlreadyPushed,
}

/// The two NAME-keyed side effects the replay path drives. The real impl forwards to
/// `features::on_item_received` / `progressive::on_item_received`; the test mock records them.
pub trait NetHook {
    /// Idempotent grace / region / natural-key name dispatch.
    fn on_item_received(&mut self, name: &str);
    /// Advance the progressive tier; returns `true` for progressive items (which then SKIP the
    /// normal grant).
    fn progressive_on_item_received(&mut self, name: &str, ap_index: i64) -> bool;
}

/// Process ONE received item exactly as `net.rs` does:
///
///  - **NAME-dispatch** when `idx >= dispatched_through` (which resets to 0 each connect), so the
///    full `items_received` stream re-dispatches every connect — safe because the name effects
///    (grace flags / received-name set / progressive's own index dedup) are idempotent.
///  - **GRANT-enqueue** when `idx >= pushed_through` (which resumes at the persisted
///    `last_received_index`), so already-granted items are NOT re-granted on reconnect.
///
/// The two watermarks advance independently; that asymmetry is the bug-prone invariant.
pub fn process_received_item(
    ri: &RecvItem,
    dispatched_through: &mut i64,
    pushed_through: &mut i64,
    item_map: &HashMap<i64, i64>,
    item_counts: &HashMap<i64, i64>,
    hook: &mut dyn NetHook,
) -> GrantAction {
    let idx = ri.index;
    let mut is_progressive = false;

    // NAME-dispatch: replays the FULL stream each connect (dispatched_through starts at 0).
    if idx >= *dispatched_through {
        hook.on_item_received(&ri.name);
        is_progressive = hook.progressive_on_item_received(&ri.name, idx);
        *dispatched_through = idx + 1;
    }

    // GRANT-enqueue: resumes at the persisted index (pushed_through) — no re-grant on reconnect.
    if idx >= *pushed_through {
        let action = if is_progressive {
            GrantAction::SkipProgressive
        } else {
            match item_map.get(&ri.ap_item_id) {
                Some(&full_id) => {
                    let qty = item_counts.get(&ri.ap_item_id).copied().unwrap_or(1).max(1);
                    GrantAction::Enqueue {
                        full_id: full_id as i32,
                        qty: qty as i32,
                        ap_index: idx,
                        name: ri.name.clone(),
                    }
                }
                None => GrantAction::SkipUnmapped {
                    ap_item_id: ri.ap_item_id,
                },
            }
        };
        *pushed_through = idx + 1;
        action
    } else {
        GrantAction::AlreadyPushed
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Records name-dispatch order and decides progressiveness from a preset name set.
    #[derive(Default)]
    struct MockHook {
        dispatched: Vec<String>,
        progressed: Vec<(String, i64)>,
        progressive_names: std::collections::HashSet<String>,
    }
    impl NetHook for MockHook {
        fn on_item_received(&mut self, name: &str) {
            self.dispatched.push(name.to_string());
        }
        fn progressive_on_item_received(&mut self, name: &str, ap_index: i64) -> bool {
            self.progressed.push((name.to_string(), ap_index));
            self.progressive_names.contains(name)
        }
    }

    fn item(index: i64, ap_item_id: i64, name: &str) -> RecvItem {
        RecvItem {
            index,
            ap_item_id,
            name: name.to_string(),
        }
    }

    fn maps() -> (HashMap<i64, i64>, HashMap<i64, i64>) {
        // apIdsToItemIds: AP item id -> ER FullID; itemCounts: AP item id -> qty.
        let mut item_map = HashMap::new();
        item_map.insert(7777, 0x4000_2710i64);
        item_map.insert(8888, 0x4000_0001i64);
        let mut counts = HashMap::new();
        counts.insert(8888, 3);
        (item_map, counts)
    }

    #[test]
    fn first_connect_dispatches_and_enqueues_in_order() {
        let (im, ic) = maps();
        let mut hook = MockHook::default();
        let mut dispatched = 0i64;
        let mut pushed = 0i64;

        let a = process_received_item(
            &item(0, 7777, "Lordsworn's Greatsword"),
            &mut dispatched,
            &mut pushed,
            &im,
            &ic,
            &mut hook,
        );
        let b = process_received_item(
            &item(1, 8888, "Golden Rune [1]"),
            &mut dispatched,
            &mut pushed,
            &im,
            &ic,
            &mut hook,
        );

        assert_eq!(
            a,
            GrantAction::Enqueue {
                full_id: 0x4000_2710u32 as i32,
                qty: 1,
                ap_index: 0,
                name: "Lordsworn's Greatsword".into(),
            }
        );
        assert_eq!(
            b,
            GrantAction::Enqueue {
                full_id: 0x4000_0001u32 as i32,
                qty: 3, // qty pulled from itemCounts
                ap_index: 1,
                name: "Golden Rune [1]".into(),
            }
        );
        assert_eq!(hook.dispatched, vec!["Lordsworn's Greatsword", "Golden Rune [1]"]);
        assert_eq!(dispatched, 2);
        assert_eq!(pushed, 2);
    }

    #[test]
    fn reconnect_replays_name_dispatch_but_grants_do_not_refire() {
        // THE watermark-split test. Reconnect after 2 items were granted:
        //   dispatched_through resets to 0 (replay all names) ...
        //   ... pushed_through resumes at the persisted index (2) -> no re-enqueue.
        let (im, ic) = maps();
        let mut hook = MockHook::default();
        let mut dispatched = 0i64;
        let mut pushed = 2i64;

        let stream = [
            item(0, 7777, "Lordsworn's Greatsword"),
            item(1, 8888, "Golden Rune [1]"),
        ];
        let actions: Vec<_> = stream
            .iter()
            .map(|ri| {
                process_received_item(ri, &mut dispatched, &mut pushed, &im, &ic, &mut hook)
            })
            .collect();

        assert_eq!(hook.dispatched, vec!["Lordsworn's Greatsword", "Golden Rune [1]"]);
        assert_eq!(dispatched, 2);
        assert_eq!(
            actions,
            vec![GrantAction::AlreadyPushed, GrantAction::AlreadyPushed]
        );
        assert_eq!(pushed, 2);
    }

    #[test]
    fn reconnect_grants_only_the_new_tail() {
        let (im, ic) = maps();
        let mut hook = MockHook::default();
        let mut dispatched = 0i64;
        let mut pushed = 1i64;

        let a0 = process_received_item(&item(0, 7777, "A"), &mut dispatched, &mut pushed, &im, &ic, &mut hook);
        let a1 = process_received_item(&item(1, 8888, "B"), &mut dispatched, &mut pushed, &im, &ic, &mut hook);
        let a2 = process_received_item(&item(2, 7777, "C"), &mut dispatched, &mut pushed, &im, &ic, &mut hook);

        assert_eq!(a0, GrantAction::AlreadyPushed);
        assert!(matches!(a1, GrantAction::Enqueue { ap_index: 1, .. }));
        assert!(matches!(a2, GrantAction::Enqueue { ap_index: 2, .. }));
        assert_eq!(hook.dispatched, vec!["A", "B", "C"]);
        assert_eq!(pushed, 3);
    }

    #[test]
    fn progressive_item_skips_grant_but_still_dispatches() {
        let (im, ic) = maps();
        let mut hook = MockHook::default();
        hook.progressive_names
            .insert("Progressive Crimson Tear".to_string());
        let mut dispatched = 0i64;
        let mut pushed = 0i64;

        let a = process_received_item(
            &item(0, 7777, "Progressive Crimson Tear"),
            &mut dispatched,
            &mut pushed,
            &im,
            &ic,
            &mut hook,
        );

        assert_eq!(a, GrantAction::SkipProgressive);
        assert_eq!(hook.dispatched, vec!["Progressive Crimson Tear"]);
        assert_eq!(hook.progressed, vec![("Progressive Crimson Tear".to_string(), 0)]);
        assert_eq!(pushed, 1);
    }

    #[test]
    fn unmapped_item_id_is_skipped_with_watermark_advance() {
        let (im, ic) = maps();
        let mut hook = MockHook::default();
        let mut dispatched = 0i64;
        let mut pushed = 0i64;

        let a = process_received_item(&item(0, 9999, "Mystery"), &mut dispatched, &mut pushed, &im, &ic, &mut hook);

        assert_eq!(a, GrantAction::SkipUnmapped { ap_item_id: 9999 });
        assert_eq!(pushed, 1);
        assert_eq!(hook.dispatched, vec!["Mystery"]);
    }
}
