//! The test seam: one trait abstracting every live-game verb the decision logic uses, plus a
//! host-side `FakeGame` mock (test builds only). The real `EldenRingHook` impl lives in the
//! Windows `eldenring-ap` crate (`#[cfg(windows)]`) and forwards each method to today's
//! `flags::` / `detour::` / `deathlink::` / `upgrades::` bodies; here we only need the trait + mock
//! so the logic in `grace` / `grants` / `deathlink` / `upgrades` is unit-testable on any host.

/// Dedicated event flag a baked EMEVD reacts to with a keep-runes ForceCharacterDeath. Used for
/// incoming DeathLink kills so they never strip runes and never collide with region-lock flags.
pub const DEATHLINK_KILL_FLAG: u32 = 76996;

/// Every live-game verb the host-testable decision logic needs. No `eldenring`/`windows` types
/// appear here, so `FakeGame` can implement the whole surface on a non-Windows host.
pub trait GameHook {
    fn get_event_flag(&self, flag: u32) -> bool;
    fn set_event_flag(&mut self, flag: u32, on: bool);
    /// `false` = the flag holder (CSEventFlagMan) isn't ready yet; caller should retry next tick.
    fn try_set_event_flag(&mut self, flag: u32, on: bool) -> bool;

    fn in_world(&self) -> bool;
    fn play_region_id(&self) -> Option<i32>;

    /// Grant a FullID x qty in-game; `false` = no inventory pointer captured yet (caller requeues).
    fn grant_full_id(&mut self, full_id: i32, qty: i32) -> bool;

    /// Current player HP, or None if not in-world / unresolvable.
    fn player_hp(&self) -> Option<i32>;

    /// True on a death frame. Default = `hp <= 0`, gated on in-world (returns false off-world).
    fn read_local_death(&self) -> bool {
        if !self.in_world() {
            return false;
        }
        self.player_hp().map(|hp| hp <= 0).unwrap_or(false)
    }

    /// Kill the local player for an INCOMING DeathLink by setting the dedicated kill flag (NOT a raw
    /// HP write — the baked EMEVD does the keep-runes kill). `true` once the flag is placed.
    fn kill_player(&mut self) -> bool {
        self.try_set_event_flag(DEATHLINK_KILL_FLAG, true)
    }

    // --- auto_upgrade + scadu (upgrades.rs) ---

    /// `(reinforce cap, is_somber)` for a weapon base row, or None if not upgradeable / repo down.
    fn weapon_track_and_cap(&self, base: i32) -> Option<(i32, bool)>;

    /// Highest +N held on the given smithing track (`true` = somber). None if the bag is unresolvable.
    fn highest_held_level(&self, somber: bool) -> Option<i32>;

    /// Current stored scadutree blessing level, or None if PlayerGameData is unreachable.
    fn scadutree_blessing(&self) -> Option<i32>;

    /// Write the stored scadutree blessing (caller has already clamped/compared).
    fn set_scadutree_blessing(&mut self, level: i32);
}

#[cfg(test)]
pub mod fake {
    //! Host-side mock: preset game state, run the logic through `&mut dyn GameHook`, assert on the
    //! recorded transcript.
    use super::*;
    use std::collections::{HashMap, VecDeque};

    #[derive(Default)]
    pub struct FakeGame {
        pub flags: HashMap<u32, bool>,
        pub in_world: bool,
        pub region: Option<i32>,
        pub hp: Option<i32>,
        /// Steady-state flag-holder readiness (default true once `new()` runs).
        pub flag_ready: bool,
        /// Per-call readiness script (consumed front-to-back; overrides `flag_ready` while non-empty).
        pub flag_ready_script: VecDeque<bool>,
        /// Whether `grant_full_id` can place items this tick (inventory pointer captured).
        pub inventory_ready: bool,
        /// base row -> (reinforce cap, is_somber).
        pub track_cap: HashMap<i32, (i32, bool)>,
        /// Highest +N held on the normal track.
        pub held_level_normal: Option<i32>,
        /// Highest +N held on the somber track.
        pub held_level_somber: Option<i32>,
        /// Stored scadutree blessing (None => PlayerGameData unreachable).
        pub scadu: Option<i32>,
        /// Last value written via `set_scadutree_blessing` (None => never written).
        pub last_scadu_write_v: Option<i32>,
        /// Ordered transcript of every flag write that LANDED: (flag, on).
        pub flags_set: Vec<(u32, bool)>,
        /// Ordered transcript of every grant that LANDED: (full_id, qty).
        pub grants: Vec<(i32, i32)>,
    }

    impl FakeGame {
        pub fn new() -> Self {
            FakeGame {
                flag_ready: true,
                inventory_ready: true,
                ..Default::default()
            }
        }
        pub fn set_in_world(&mut self, v: bool) {
            self.in_world = v;
        }
        pub fn set_region(&mut self, r: Option<i32>) {
            self.region = r;
        }
        pub fn set_hp(&mut self, hp: Option<i32>) {
            self.hp = hp;
        }
        pub fn set_flag(&mut self, flag: u32, on: bool) {
            self.flags.insert(flag, on);
        }
        pub fn set_flag_holder_ready(&mut self, v: bool) {
            self.flag_ready = v;
        }
        pub fn script_flag_holder_ready(&mut self, v: Vec<bool>) {
            self.flag_ready_script = v.into();
        }
        pub fn set_inventory_ready(&mut self, v: bool) {
            self.inventory_ready = v;
        }
        pub fn set_track_cap(&mut self, base: i32, v: Option<(i32, bool)>) {
            match v {
                Some(x) => {
                    self.track_cap.insert(base, x);
                }
                None => {
                    self.track_cap.remove(&base);
                }
            }
        }
        pub fn set_held_level(&mut self, somber: bool, lvl: Option<i32>) {
            if somber {
                self.held_level_somber = lvl;
            } else {
                self.held_level_normal = lvl;
            }
        }
        pub fn set_stored_blessing(&mut self, v: Option<i32>) {
            self.scadu = v;
        }
        pub fn last_scadu_write(&self) -> Option<i32> {
            self.last_scadu_write_v
        }
        /// Flags that were set to `true`, in order.
        pub fn set_flags(&self) -> Vec<u32> {
            self.flags_set
                .iter()
                .filter(|&&(_, on)| on)
                .map(|&(f, _)| f)
                .collect()
        }
        /// FullIDs granted, in order.
        pub fn grant_ids(&self) -> Vec<i32> {
            self.grants.iter().map(|&(id, _)| id).collect()
        }
    }

    impl GameHook for FakeGame {
        fn get_event_flag(&self, flag: u32) -> bool {
            self.flags.get(&flag).copied().unwrap_or(false)
        }
        fn set_event_flag(&mut self, flag: u32, on: bool) {
            self.flags.insert(flag, on);
            self.flags_set.push((flag, on));
        }
        fn try_set_event_flag(&mut self, flag: u32, on: bool) -> bool {
            let ready = self.flag_ready_script.pop_front().unwrap_or(self.flag_ready);
            if !ready {
                return false;
            }
            self.flags.insert(flag, on);
            self.flags_set.push((flag, on));
            true
        }
        fn in_world(&self) -> bool {
            self.in_world
        }
        fn play_region_id(&self) -> Option<i32> {
            self.region
        }
        fn grant_full_id(&mut self, full_id: i32, qty: i32) -> bool {
            if !self.inventory_ready {
                return false;
            }
            self.grants.push((full_id, qty));
            true
        }
        fn player_hp(&self) -> Option<i32> {
            if !self.in_world {
                return None;
            }
            self.hp
        }
        fn weapon_track_and_cap(&self, base: i32) -> Option<(i32, bool)> {
            self.track_cap.get(&base).copied()
        }
        fn highest_held_level(&self, somber: bool) -> Option<i32> {
            if somber {
                self.held_level_somber
            } else {
                self.held_level_normal
            }
        }
        fn scadutree_blessing(&self) -> Option<i32> {
            self.scadu
        }
        fn set_scadutree_blessing(&mut self, level: i32) {
            self.scadu = Some(level);
            self.last_scadu_write_v = Some(level);
        }
    }
}
