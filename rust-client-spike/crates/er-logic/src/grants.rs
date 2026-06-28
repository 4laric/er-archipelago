//! Once-per-save grant drains, extracted from `features.rs` `drain_start_items` / `drain_notify_grants`.
//! The persisted guards live on a passed-in [`SaveState`] (the live code keeps them as `grant.rs`
//! statics) so tests get fresh state.

use crate::hook::GameHook;
use crate::save_state::SaveState;
use std::collections::VecDeque;

/// Grant the start-items queue exactly once per save. If already granted, clear the queue. If any
/// grant can't place (no inventory pointer yet), abort the whole tick with NO state change (retry).
pub fn drain_start_items(
    hook: &mut dyn GameHook,
    queue: &mut VecDeque<(i32, i32)>,
    save: &mut SaveState,
) {
    if queue.is_empty() {
        return;
    }
    if save.start_items_granted {
        queue.clear();
        return;
    }
    let snapshot: Vec<(i32, i32)> = queue.iter().copied().collect();
    for &(id, qty) in &snapshot {
        if !hook.grant_full_id(id, qty) {
            return; // not ready -> retry next tick, no partial state
        }
    }
    queue.clear();
    save.start_items_granted = true;
}

/// Grant each notify item once per save (dedup via `save.notify_granted`); requeue ones that can't
/// place yet.
pub fn drain_notify_grants(
    hook: &mut dyn GameHook,
    queue: &mut VecDeque<i32>,
    save: &mut SaveState,
) {
    let mut retry = VecDeque::new();
    while let Some(id) = queue.pop_front() {
        if save.notify_granted.contains(&id) {
            continue;
        }
        if hook.grant_full_id(id, 1) {
            save.notify_granted.insert(id);
        } else {
            retry.push_back(id);
        }
    }
    *queue = retry;
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::hook::fake::FakeGame;

    #[test]
    fn start_items_granted_once_then_not_regranted() {
        let mut g = FakeGame::new();
        let mut save = SaveState::default();
        let mut q: VecDeque<(i32, i32)> = [(130, 1), (2008021, 5)].into_iter().collect();

        drain_start_items(&mut g, &mut q, &mut save);
        assert_eq!(g.grants, vec![(130, 1), (2008021, 5)]);
        assert!(save.start_items_granted);
        assert!(q.is_empty());

        // Replay re-queues on reconnect; the persisted flag drops it.
        let mut q2: VecDeque<(i32, i32)> = [(130, 1)].into_iter().collect();
        drain_start_items(&mut g, &mut q2, &mut save);
        assert_eq!(g.grants, vec![(130, 1), (2008021, 5)]); // unchanged
        assert!(q2.is_empty());
    }

    #[test]
    fn start_items_no_inventory_keeps_whole_queue() {
        let mut g = FakeGame::new();
        g.set_inventory_ready(false);
        let mut save = SaveState::default();
        let mut q: VecDeque<(i32, i32)> = [(130, 1), (2008021, 5)].into_iter().collect();

        drain_start_items(&mut g, &mut q, &mut save);
        assert!(g.grants.is_empty());
        assert!(!save.start_items_granted); // all-or-nothing
        assert_eq!(q.len(), 2);
    }

    #[test]
    fn notify_granted_once_then_dedup() {
        let mut g = FakeGame::new();
        let mut save = SaveState::default();
        let rune = 191i32 | 0x4000_0000u32 as i32; // a restored great-rune notify FullID
        let mut q: VecDeque<i32> = [rune].into_iter().collect();

        drain_notify_grants(&mut g, &mut q, &mut save);
        assert_eq!(g.grants, vec![(rune, 1)]);
        assert!(save.notify_granted.contains(&rune));
        assert!(q.is_empty());

        let mut q2: VecDeque<i32> = [rune].into_iter().collect();
        drain_notify_grants(&mut g, &mut q2, &mut save);
        assert_eq!(g.grants, vec![(rune, 1)]); // unchanged
    }

    #[test]
    fn notify_no_inventory_requeues() {
        let mut g = FakeGame::new();
        g.set_inventory_ready(false);
        let mut save = SaveState::default();
        let mut q: VecDeque<i32> = [12345].into_iter().collect();
        drain_notify_grants(&mut g, &mut q, &mut save);
        assert!(g.grants.is_empty());
        assert!(!save.notify_granted.contains(&12345));
        assert_eq!(q.iter().copied().collect::<Vec<_>>(), vec![12345]);
    }
}
