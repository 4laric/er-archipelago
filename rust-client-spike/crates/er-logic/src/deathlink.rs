//! DeathLink side-effect logic, extracted from `deathlink.rs`. Latches lifted into a passed-in
//! `DeathLatch` (the live code keeps them as module statics) so each test gets fresh state.

use crate::hook::GameHook;

/// Cross-tick DeathLink state (replaces the `static AtomicBool`s `KILL_PENDING`/`SEND_PENDING`/
/// `WAS_DEAD`).
#[derive(Default)]
pub struct DeathLatch {
    pub kill_pending: bool,
    pub send_pending: bool,
    pub was_dead: bool,
}

/// Apply an INCOMING DeathLink: once in-world, set the kill flag; clear the latch only on success
/// (retry next tick while the holder isn't ready).
pub fn drive_incoming_kill(hook: &mut dyn GameHook, latch: &mut DeathLatch) {
    if latch.kill_pending && hook.in_world() && hook.kill_player() {
        latch.kill_pending = false;
    }
}

/// Detect an OUTGOING death edge (alive -> dead) and mark a send. Off-world clears the edge so a
/// respawn isn't read as a fresh death.
pub fn poll_outgoing_death(hook: &mut dyn GameHook, latch: &mut DeathLatch) {
    if !hook.in_world() {
        latch.was_dead = false;
        return;
    }
    let dead = hook.read_local_death();
    if dead && !latch.was_dead {
        latch.send_pending = true;
    }
    latch.was_dead = dead;
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::hook::{fake::FakeGame, DEATHLINK_KILL_FLAG};

    #[test]
    fn incoming_kill_sets_dedicated_flag_not_hp() {
        let mut g = FakeGame::new();
        g.set_in_world(true);
        g.set_hp(Some(1000)); // alive; HP must be untouched
        let mut latch = DeathLatch { kill_pending: true, ..Default::default() };
        drive_incoming_kill(&mut g, &mut latch);
        assert_eq!(g.set_flags(), vec![DEATHLINK_KILL_FLAG]);
        assert_eq!(g.player_hp(), Some(1000));
        assert!(!latch.kill_pending);
    }

    #[test]
    fn incoming_kill_retries_until_holder_ready() {
        let mut g = FakeGame::new();
        g.set_in_world(true);
        g.set_flag_holder_ready(false);
        let mut latch = DeathLatch { kill_pending: true, ..Default::default() };
        drive_incoming_kill(&mut g, &mut latch);
        assert!(latch.kill_pending);
        assert!(g.set_flags().is_empty());

        g.set_flag_holder_ready(true);
        drive_incoming_kill(&mut g, &mut latch);
        assert!(!latch.kill_pending);
        assert_eq!(g.set_flags(), vec![DEATHLINK_KILL_FLAG]);
    }

    #[test]
    fn incoming_kill_not_attempted_off_world() {
        let mut g = FakeGame::new();
        g.set_in_world(false);
        let mut latch = DeathLatch { kill_pending: true, ..Default::default() };
        drive_incoming_kill(&mut g, &mut latch);
        assert!(latch.kill_pending);
        assert!(g.set_flags().is_empty());
    }

    #[test]
    fn read_local_death_true_only_when_hp_le_zero_in_world() {
        let mut g = FakeGame::new();
        g.set_in_world(true);
        g.set_hp(Some(0));
        assert!(g.read_local_death());
        g.set_hp(Some(-5));
        assert!(g.read_local_death());
        g.set_hp(Some(1));
        assert!(!g.read_local_death());
    }

    #[test]
    fn read_local_death_false_off_world_even_if_hp_zero() {
        let mut g = FakeGame::new();
        g.set_in_world(false);
        g.set_hp(Some(0));
        assert!(!g.read_local_death());
    }

    #[test]
    fn outgoing_death_reported_once_per_death() {
        let mut g = FakeGame::new();
        g.set_in_world(true);
        g.set_hp(Some(0)); // dead, sustained
        let mut latch = DeathLatch::default();
        poll_outgoing_death(&mut g, &mut latch);
        assert!(latch.send_pending);
        latch.send_pending = false; // net thread drained it
        poll_outgoing_death(&mut g, &mut latch);
        assert!(!latch.send_pending); // no second send while death screen up
    }

    #[test]
    fn respawn_then_redeath_sends_again() {
        let mut g = FakeGame::new();
        g.set_in_world(true);
        let mut latch = DeathLatch::default();
        g.set_hp(Some(0));
        poll_outgoing_death(&mut g, &mut latch);
        assert!(latch.send_pending);
        latch.send_pending = false;
        g.set_hp(Some(1000)); // respawn
        poll_outgoing_death(&mut g, &mut latch);
        assert!(!latch.send_pending);
        g.set_hp(Some(0)); // new death
        poll_outgoing_death(&mut g, &mut latch);
        assert!(latch.send_pending);
    }

    #[test]
    fn off_world_clears_edge() {
        let mut g = FakeGame::new();
        g.set_in_world(true);
        g.set_hp(Some(0));
        let mut latch = DeathLatch::default();
        poll_outgoing_death(&mut g, &mut latch);
        latch.send_pending = false;
        g.set_in_world(false);
        poll_outgoing_death(&mut g, &mut latch);
        assert!(!latch.was_dead);
        assert!(!latch.send_pending);
    }
}
