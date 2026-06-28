//! Grace-flag flush with holder-not-ready retry, extracted from `features.rs::flush_grace_flags`.
//! The queue + the per-session "already set" set are passed in (the live code keeps them as module
//! statics) so each test gets fresh state.

use crate::hook::GameHook;
use std::collections::{HashSet, VecDeque};

/// Drain pending grace flags: skip ones already set this session; set each via `try_set_event_flag`;
/// flags whose holder isn't ready are retained for the next tick (never dropped).
pub fn flush_grace_flags(
    hook: &mut dyn GameHook,
    queue: &mut VecDeque<u32>,
    session: &mut HashSet<u32>,
) {
    let mut retry = VecDeque::new();
    while let Some(flag) = queue.pop_front() {
        if session.contains(&flag) {
            continue;
        }
        if hook.try_set_event_flag(flag, true) {
            session.insert(flag);
        } else {
            retry.push_back(flag);
        }
    }
    *queue = retry;
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::hook::fake::FakeGame;

    #[test]
    fn holder_not_ready_retries_then_lands() {
        let mut g = FakeGame::new();
        g.set_flag_holder_ready(false);
        let mut q: VecDeque<u32> = [76971, 76972].into_iter().collect();
        let mut session = HashSet::new();

        flush_grace_flags(&mut g, &mut q, &mut session);
        assert!(g.set_flags().is_empty());
        assert_eq!(q.iter().copied().collect::<Vec<_>>(), vec![76971, 76972]);
        assert!(session.is_empty());

        g.set_flag_holder_ready(true);
        flush_grace_flags(&mut g, &mut q, &mut session);
        assert_eq!(g.set_flags(), vec![76971, 76972]);
        assert!(q.is_empty());
        assert!(session.contains(&76971) && session.contains(&76972));
    }

    #[test]
    fn partial_readiness_drains_only_successes() {
        let mut g = FakeGame::new();
        g.script_flag_holder_ready(vec![true, false]); // 1st lands, 2nd not ready
        let mut q: VecDeque<u32> = [76971, 76972].into_iter().collect();
        let mut session = HashSet::new();

        flush_grace_flags(&mut g, &mut q, &mut session);
        assert_eq!(g.set_flags(), vec![76971]);
        assert_eq!(q.iter().copied().collect::<Vec<_>>(), vec![76972]);
        assert!(session.contains(&76971) && !session.contains(&76972));
    }

    #[test]
    fn already_set_this_session_is_skipped() {
        let mut g = FakeGame::new();
        let mut q: VecDeque<u32> = [76971].into_iter().collect();
        let mut session: HashSet<u32> = [76971].into_iter().collect();
        flush_grace_flags(&mut g, &mut q, &mut session);
        assert!(g.set_flags().is_empty()); // skipped, nothing re-set
        assert!(q.is_empty());
    }
}
