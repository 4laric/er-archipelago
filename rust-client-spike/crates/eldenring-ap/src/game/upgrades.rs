//! AUTO_UPGRADE + GLOBAL_SCADUTREE_BLESSING — RE holes filled via typed `eldenring` 0.14 bindings.
//!
//! Two slot_data features whose game-memory touchpoints were originally RE-stubbed. The RE is now
//! resolved entirely against the `eldenring` 0.14 typed bindings (NO raw CE offsets are used — every
//! field that the C++ client reached with a hand-walked offset chain is a NAMED field on a typed
//! struct here). Every game read/write is read-then-act, raise-only, bounds-checked, and gated on
//! `super::flags::in_world()` so a mis-resolution degrades to a no-op rather than corrupting a save.
//!
//! C++ source of truth (the exact behaviour these port):
//!   - er_gamehook_win.cpp `AutoUpgradeWeaponIdImpl` (~666) / `RefreshAutoUpgradeTargets` (~609) /
//!     `WeaponInfo` (~542) / `CapForRT` (~530) (auto_upgrade), and `TickGlobalScaduBlessing` (~720) /
//!     `SetGlobalScaduBlessing` (~715) / `kScaduCum` (~706) (scadu).
//!   - ArchipelagoInterface.cpp ~92-100: slot_data `options.auto_upgrade` (int) and
//!     `options.global_scadutree_blessing` (int) drive `SetAutoUpgrade(int)` / `SetGlobalScaduBlessing(int)`.
//!
//! TYPED-BINDING MAP (what replaced each C++ raw-offset hole; see RE-WORKSHEET-autoupgrade-scadu.md):
//!   - GameDataMan singleton .............. `GameDataMan::instance()` / `::instance_mut()` (FromStatic).
//!   - PlayerGameData ..................... `gdm.main_player_game_data` (OwnedPtr, `.as_ref()?`/`.as_mut()?`).
//!                                          (Replaces C++ `*(GameDataMan + 0x08)`.)
//!   - stored Scadutree blessing .......... `pgd.scadutree_blessing: u8` NAMED field.
//!                                          (Replaces the raw `PlayerGameData + 0xFC` signed byte.)
//!   - held-item inventory iterator ....... `pgd.equipment.equip_inventory_data.items_data.items()`
//!                                          -> `&EquipInventoryDataListEntry` (skips empty slots).
//!                                          (Replaces the C++ EquipInventoryData container shape-scan.)
//!   - per-entry item id / category ....... `entry.item_id.param_id() -> u32` + `.category() -> ItemCategory`.
//!   - per-entry quantity ................. `entry.quantity: u32`.
//!   - weapon -> reinforceTypeId .......... `repo.get::<EquipParamWeapon>(base).reinforce_type_id() -> i16`.
//!                                          (Replaces the C++ self-calibrated s16 offset.)
//!   - reinforce cap ...................... count consecutive `repo.get::<ReinforceParamWeapon>(rt+k)`.
//!
//! WIRING (already done elsewhere — do not edit those files):
//!   - net.rs slot_data parse calls `set_auto_upgrade(..)` / `set_global_scadu_blessing(..)` at connect.
//!   - detour.rs `grant_full_id` calls `apply_auto_upgrade(full_id) -> i32` on every granted item.
//!   - mod.rs `tick()` calls `tick_global_scadu()` in the in-world `#[cfg(feature = "net")]` neighbourhood.

#![allow(dead_code)]

use std::sync::atomic::{AtomicI32, Ordering};
use std::sync::Mutex;
use std::time::{Duration, Instant};

use eldenring::cs::{
    EquipParamWeapon, GameDataMan, ItemCategory, ReinforceParamWeapon, SoloParamRepository,
};
use fromsoftware_shared::FromStatic;

// ---- config (set from slot_data by net.rs; see module doc + worksheet) --------------------------

/// auto_upgrade mode/level from slot_data. The C++ treats it as a simple on/off int
/// (`g_autoUpgrade = on ? 1 : 0`); we keep the raw int so a future "cap at +N" variant has room.
/// 0 = off (default). Non-zero = on.
static AUTO_UPGRADE: AtomicI32 = AtomicI32::new(0);

/// global_scadutree_blessing mode from slot_data: 0 = off, 1 = player_only, 2 = scaled.
/// (Matches the C++ `g_globalScaduBlessing` tri-state.)
static GLOBAL_SCADU: AtomicI32 = AtomicI32::new(0);

/// net.rs: `set_auto_upgrade(sd.pointer("/options/auto_upgrade").and_then(|v| v.as_i64()).unwrap_or(0) as i32)`.
pub fn set_auto_upgrade(level_or_flag: i32) {
    AUTO_UPGRADE.store(level_or_flag, Ordering::Relaxed);
    tracing::info!(
        "auto_upgrade: {}",
        if level_or_flag != 0 { "ENABLED" } else { "off" }
    );
}

/// net.rs: `set_global_scadu_blessing(sd.pointer("/options/global_scadutree_blessing").and_then(|v| v.as_i64()).unwrap_or(0) as i32)`.
pub fn set_global_scadu_blessing(mode: i32) {
    let m = if mode == 1 || mode == 2 { mode } else { 0 };
    GLOBAL_SCADU.store(m, Ordering::Relaxed);
    tracing::info!(
        "global_scadu_blessing: {}",
        if m != 0 { "ENABLED" } else { "off" }
    );
}

fn auto_upgrade_on() -> bool {
    AUTO_UPGRADE.load(Ordering::Relaxed) != 0
}
fn scadu_mode() -> i32 {
    GLOBAL_SCADU.load(Ordering::Relaxed)
}

// ================================================================================================
// auto_upgrade
// ================================================================================================
//
// GOAL: when a REAL weapon is acquired, bump it to the player's current highest reinforce level on
// the same smithing track (normal vs somber) before the game adds it.
//
// C++ (er_gamehook_win.cpp `AutoUpgradeWeaponIdImpl`, ~666):
//   id math: base = id - (id % 100); level = id % 100. ER bakes +N into the id (id = base + N).
//   track/cap: EquipParamWeapon row(base).reinforceTypeId -> ReinforceParamWeapon; cap = number of
//     consecutive ReinforceParamWeapon rows from reinforceTypeId; cap>10 => normal (max +25),
//     cap in 1..=10 => somber (max +10).
//   target: highest +N currently HELD on that track (walk inventory), clamped to the weapon's cap;
//     only ever RAISES (returns input if already at/above target).
//
// Worksheet §A.

const REINFORCE_STEP: i32 = 100; // ER id stride per smithing level (base = id - id%100)
const NORMAL_CAP: i32 = 25; // normal smithing track tops out at +25
const SOMBER_CAP: i32 = 10; // somber smithing track tops out at +10

/// Cached "highest +N held" per track, refreshed on a throttle (C++ used 1500ms + a cached
/// container offset; the typed iterator removes the container scan, so we just cache the targets
/// to avoid re-walking the bag on every back-to-back grant in a reconnect replay burst).
struct UpgradeTargets {
    normal: i32,
    somber: i32,
    last_refresh: Option<Instant>,
}
static UPGRADE_TARGETS: Mutex<UpgradeTargets> = Mutex::new(UpgradeTargets {
    normal: 0,
    somber: 0,
    last_refresh: None,
});
const REFRESH_THROTTLE: Duration = Duration::from_millis(1500);

/// Given a granted weapon FullID (real item id | category nibble), return the upgraded FullID, or
/// the input unchanged if it is not an upgradeable weapon / auto_upgrade is off / it can't be
/// resolved safely. Mirrors the C++ `AutoUpgradeWeaponIdImpl`.
///
/// CALL SITE: detour.rs `grant_full_id` (every AP-granted item funnels through it). Returns the
/// input unchanged for non-weapons and whenever any read can't be done safely (raise-only by
/// construction: never lowers an already-higher granted weapon).
pub fn apply_auto_upgrade(full_id: i32) -> i32 {
    if !auto_upgrade_on() {
        return full_id;
    }
    // Only touch game memory in-world (params + inventory loaded). Mirrors the param-probe gate;
    // before the world is up the SoloParamRepository / GameDataMan singletons fault.
    if !super::flags::in_world() {
        return full_id;
    }
    // Decode base/level + category guard (pure). Only WEAPON-category FullIDs proceed.
    let Some((base, level)) = decode_weapon_id(full_id) else {
        return full_id;
    };

    // EquipParamWeapon row(base) -> reinforceTypeId, then ReinforceParamWeapon consecutive-row cap.
    let Some((cap, somber)) = weapon_track_and_cap(base) else {
        return full_id; // not an upgradeable weapon (no param row / cap 0) -> inert
    };

    // Highest +N held on this track. None => couldn't resolve the bag safely -> inert (no guess).
    let Some(target_raw) = highest_held_level(somber) else {
        return full_id;
    };

    let mut target = target_raw;
    if target > cap {
        target = cap;
    }
    if target <= level {
        return full_id; // already at/above target — return unchanged (C++ returns false)
    }
    let up = base + target;
    tracing::info!(
        "auto_upgrade: weapon {:#x} (+{}) -> +{} ({} track, cap +{})",
        base,
        level,
        target,
        if somber { "somber" } else { "normal" },
        cap
    );
    // Re-attach the category nibble. WEAPON category is 0x0, so for a weapon this is a no-op, but we
    // keep the mask symmetric with decode_weapon_id (C++ rewrites base+target with category 0).
    (full_id & !(ROW_ID_MASK as i32)) | (up & ROW_ID_MASK as i32)
}

/// ER category nibble mask / weapon-category constant (er_codec mirror; weapons are category 0x0).
const ROW_ID_MASK: u32 = er_codec::ROW_ID_MASK;

/// Pure id-math decode: returns (base_row_id, level) for an upgradeable WEAPON FullID, else None.
/// base = row - row%100; level = row%100. Category guard mirrors C++ `WeaponInfo`:
///   `(uint32(itemId) & CATEGORY_MASK) != CATEGORY_WEAPON` rejects non-weapons; row range
///   `[1_000_000, 90_000_000)` skips system/NPC ids. Weapons are er_codec::CATEGORY_WEAPON (0x0).
fn decode_weapon_id(full_id: i32) -> Option<(i32, i32)> {
    // RE-A1 RESOLVED: category test via er_codec constants (CATEGORY_WEAPON == 0x0, CATEGORY_MASK).
    if er_codec::item_category_of(full_id as u32) != er_codec::CATEGORY_WEAPON {
        return None;
    }
    let row = (full_id as u32 & ROW_ID_MASK) as i32;
    if !(1_000_000..90_000_000).contains(&row) {
        return None;
    }
    let base = row - (row % REINFORCE_STEP);
    let level = row % REINFORCE_STEP;
    Some((base, level))
}

/// RE-A2 RESOLVED (typed binding): resolve a weapon base id -> (reinforce cap, is_somber).
/// `repo.get::<EquipParamWeapon>(base).reinforce_type_id() -> i16`; then cap = max k in [0,25] s.t.
/// `repo.get::<ReinforceParamWeapon>(rt + k)` exists. somber = cap <= 10. Mirrors C++ `CapForRT` /
/// `WeaponInfo`. None (no upgrade) if the repo isn't up, the row is absent, or cap <= 0.
fn weapon_track_and_cap(base: i32) -> Option<(i32, bool)> {
    // SAFETY: FD4 singleton; on the game thread, gated in-world by the caller. Err until built.
    let repo = unsafe { SoloParamRepository::instance() }.ok()?;
    let weapon = repo.get::<EquipParamWeapon>(base as u32)?;
    let rt = weapon.reinforce_type_id() as i32;
    // Count consecutive ReinforceParamWeapon rows from rt. C++: `while (k<=25 && row(rt+k)) ++k;
    // cap = k-1`. rt can be negative for non-upgradeable junk; get() just returns None then.
    let mut k = 0;
    while k <= NORMAL_CAP && repo.get::<ReinforceParamWeapon>((rt + k) as u32).is_some() {
        k += 1;
    }
    let cap = k - 1;
    if cap <= 0 {
        return None; // not upgradeable
    }
    let somber = cap <= SOMBER_CAP;
    Some((cap, somber))
}

/// RE-A3 RESOLVED (typed binding): highest +N currently held on the given smithing track
/// (true = somber). Walks `GameDataMan -> main_player_game_data -> equipment.equip_inventory_data
/// .items_data.items()` (the typed iterator skips empty slots). Caches the per-track maxima behind a
/// 1500ms throttle so a reconnect replay burst doesn't re-walk the bag per grant (mirrors C++
/// `RefreshAutoUpgradeTargets`). Returns None only if the bag can't be resolved AND nothing is
/// cached yet (so the caller leaves the weapon unchanged rather than guessing).
fn highest_held_level(somber: bool) -> Option<i32> {
    let mut targets = UPGRADE_TARGETS.lock().ok()?;
    let stale = match targets.last_refresh {
        Some(t) => t.elapsed() >= REFRESH_THROTTLE,
        None => true,
    };
    if stale {
        if let Some((normal, somber_max)) = walk_inventory_targets() {
            targets.normal = normal;
            targets.somber = somber_max;
            targets.last_refresh = Some(Instant::now());
        } else if targets.last_refresh.is_none() {
            // Never resolved the bag and nothing cached -> can't supply a target yet.
            return None;
        }
        // else: walk failed transiently but we have a cached value -> use it (no down-flicker).
    }
    Some(if somber { targets.somber } else { targets.normal })
}

/// One full typed inventory walk: returns (highest normal +N, highest somber +N) across all held
/// weapons, or None if the bag isn't reachable this tick. Pure read; no writes. Each weapon entry's
/// `param_id()` is the resolved row (base + level); we re-classify its track via the same param cap
/// rule so a weapon's level is only counted toward the track it actually belongs to.
fn walk_inventory_targets() -> Option<(i32, i32)> {
    // SAFETY: FD4 singleton (read-only walk). Err/None before the player is placed.
    let gdm = unsafe { GameDataMan::instance() }.ok()?;
    let pgd = gdm.main_player_game_data.as_ref();
    let mut normal = 0i32;
    let mut somber = 0i32;
    for entry in pgd.equipment.equip_inventory_data.items_data.items() {
        if entry.item_id.category() != ItemCategory::Weapon {
            continue;
        }
        // param_id() strips the category nibble -> the resolved weapon row (base + level).
        let row = entry.item_id.param_id() as i32;
        if !(1_000_000..90_000_000).contains(&row) {
            continue;
        }
        let level = row % REINFORCE_STEP;
        let base = row - level;
        // Classify the held weapon by its OWN track (a somber weapon can never reach +25, so its
        // level must not raise the normal target, and vice-versa). Mirrors C++ WeaponInfo per entry.
        match weapon_track_and_cap(base) {
            Some((_, true)) => {
                if level > somber {
                    somber = level;
                }
            }
            Some((_, false)) => {
                if level > normal {
                    normal = level;
                }
            }
            None => {}
        }
    }
    Some((normal, somber))
}

// ================================================================================================
// global_scadutree_blessing
// ================================================================================================
//
// GOAL: count held Scadutree Fragments, map to a blessing level via the vanilla cost curve, and
// write the stored combat-blessing field on PlayerGameData so the base game applies the buff.
//
// C++ (er_gamehook_win.cpp `TickGlobalScaduBlessing`, ~720):
//   fragments: ONE inventory stack, goods id 2010000 (FullID = 2010000 | CATEGORY_GOODS); qty = total.
//   curve: kScaduCum[0..20] cumulative-fragments-to-reach-level table -> level 0..20.
//   write: PlayerGameData + 0xFC, signed byte (the stored combat blessing). Only ever RAISE. Engine
//     recomputes the speffect from this byte on next map load / grace rest. Throttled to once/second.
//   The raw `PlayerGameData + 0xFC` offset is replaced here by the NAMED typed field
//   `PlayerGameData::scadutree_blessing: u8` (eldenring 0.14) — same datum, version-robust.
//
// Worksheet §B.

/// Scadutree Fragment goods row id (no category nibble). FullID = SCADU_FRAGMENT_GOODS | category.
const SCADU_FRAGMENT_GOODS: u32 = 2_010_000;

/// Cumulative Scadutree Fragments required to REACH each combat-blessing level (index = level 0..20).
/// Verbatim from C++ `kScaduCum`. Pure data — no RE needed.
const SCADU_CUM: [i32; 21] = [
    0, 1, 3, 5, 7, 9, 11, 13, 15, 17, 20, 23, 26, 29, 32, 35, 38, 41, 44, 47, 50,
];

/// Maximum stored blessing level the game's combat-blessing curve defines (caps the raise-only write).
const SCADU_MAX_LEVEL: i32 = 20;

/// Map a held-fragment count to a blessing level (0..20). Pure; highest L with frags >= SCADU_CUM[L].
fn level_for_fragments(frag_qty: i32) -> i32 {
    let mut level = 0;
    for l in (0..=20).rev() {
        if frag_qty >= SCADU_CUM[l as usize] {
            level = l;
            break;
        }
    }
    level
}

/// Scadu writer throttle (~1s, mirrors C++ `s_lastTick`). A stored-byte watchdog doesn't need to run
/// every frame; this also keeps the bag walk cheap.
static SCADU_LAST_TICK: Mutex<Option<Instant>> = Mutex::new(None);
const SCADU_THROTTLE: Duration = Duration::from_millis(1000);

/// Per-tick stored-blessing writer. Call from the in-world feature tick (mod.rs `tick()`).
/// Self-gates: returns immediately when the mode is off or out-of-world. Throttled to ~1s. Reads the
/// held Scadutree Fragment count, maps it to a level, and raises `PlayerGameData::scadutree_blessing`
/// (never lowers a real/higher DLC value). mode 1 (player_only) and mode 2 (scaled) behave the same
/// here — exactly as the C++ `TickGlobalScaduBlessing` does (it gates on `g_globalScaduBlessing`
/// being non-zero and applies the player byte for both; the "scaled" variant is a future apworld
/// concern with no extra client write, so mode 2 is a documented no-extra-op alias of mode 1).
pub fn tick_global_scadu() {
    if scadu_mode() == 0 {
        return;
    }
    // GATE: only touch game memory in-world (params + inventory loaded). Same gate the param probe
    // uses (mod.rs `tick()` gates `spike_log_goods_rowcount` on `flags::in_world()`).
    if !super::flags::in_world() {
        return;
    }
    // Throttle (~1s). Cheap watchdog cadence; keeps the bag walk off the hot path.
    {
        let mut last = match SCADU_LAST_TICK.lock() {
            Ok(g) => g,
            Err(_) => return,
        };
        if let Some(t) = *last {
            if t.elapsed() < SCADU_THROTTLE {
                return;
            }
        }
        *last = Some(Instant::now());
    }

    // Read total held Scadutree Fragments (goods 2010000). None => bag not reachable this tick ->
    // inert (never writes a transient 0; avoids flicker if the walk raced a realloc, like the C++).
    let Some(frag_qty) = held_scadu_fragments() else {
        return;
    };

    let level = level_for_fragments(frag_qty);

    // Read the current stored blessing, then ONLY raise it (never stomp a higher real DLC revere,
    // never down-flicker). The read+write share one mutable PlayerGameData borrow inside
    // `raise_stored_blessing` so the value can't change between the compare and the store.
    match raise_stored_blessing(level) {
        Some(Some((was, now))) => {
            tracing::info!(
                "global_scadu_blessing: frags={} -> blessing level {} (PlayerGameData.scadutree_blessing, was {})",
                frag_qty,
                now,
                was
            );
        }
        Some(None) => {} // already >= target; nothing written
        None => {}       // PlayerGameData unreachable this tick; retry next throttle window
    }
}

/// RE-B1 RESOLVED (typed binding): total held Scadutree Fragments (goods 2010000). Walks the same
/// typed inventory iterator as auto_upgrade and sums the quantity of every goods entry whose
/// `param_id()` is the fragment row. (Both AP fragment variants share goods id 2010000, so this is
/// effectively one stack; summing is safe even if the game ever splits it.) None if the bag isn't
/// reachable this tick. Read-only.
fn held_scadu_fragments() -> Option<i32> {
    // SAFETY: FD4 singleton (read-only walk). None before the player is placed.
    let gdm = unsafe { GameDataMan::instance() }.ok()?;
    let pgd = gdm.main_player_game_data.as_ref();
    let mut total: i64 = 0;
    for entry in pgd.equipment.equip_inventory_data.items_data.items() {
        if entry.item_id.category() != ItemCategory::Goods {
            continue;
        }
        if entry.item_id.param_id() == SCADU_FRAGMENT_GOODS {
            total += entry.quantity as i64;
        }
    }
    // ER stacks cap well under i32; clamp defensively.
    if total > i32::MAX as i64 {
        total = i32::MAX as i64;
    }
    Some(total as i32)
}

/// RE-B2 / RE-B3 RESOLVED (typed binding): read the current stored combat-blessing level and RAISE
/// it to `level` if higher. Returns:
///   - `Some(Some((was, now)))` — wrote a new (raised) value,
///   - `Some(None)`             — current was already >= target; left untouched,
///   - `None`                   — PlayerGameData not reachable this tick.
/// Uses `PlayerGameData::scadutree_blessing: u8` (named field; replaces the raw `PGD + 0xFC` byte).
/// Read + write share one `instance_mut()` borrow so nothing can change between compare and store.
fn raise_stored_blessing(level: i32) -> Option<Option<(i32, i32)>> {
    // Clamp the computed target into the valid stored range before any write.
    let mut target = level;
    if target < 0 {
        target = 0;
    }
    if target > SCADU_MAX_LEVEL {
        target = SCADU_MAX_LEVEL;
    }
    // SAFETY: FD4 singleton accessed MUTABLY (we may write the byte); same idiom as
    // deathlink.rs `WorldChrMan::instance_mut()`. Err/None before the player is placed -> no-op.
    let gdm = unsafe { GameDataMan::instance_mut() }.ok()?;
    let pgd = gdm.main_player_game_data.as_mut();
    let cur = pgd.scadutree_blessing as i32;
    if cur >= target {
        return Some(None); // already >= target; never lower
    }
    pgd.scadutree_blessing = target as u8;
    Some(Some((cur, target)))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn scadu_curve_matches_cpp_table() {
        // Boundary checks against kScaduCum.
        assert_eq!(level_for_fragments(0), 0);
        assert_eq!(level_for_fragments(1), 1);
        assert_eq!(level_for_fragments(2), 1); // 2 frags still level 1 (next is 3)
        assert_eq!(level_for_fragments(3), 2);
        assert_eq!(level_for_fragments(49), 19);
        assert_eq!(level_for_fragments(50), 20);
        assert_eq!(level_for_fragments(999), 20); // capped at 20
    }

    #[test]
    fn weapon_id_math() {
        // base/level split for a +7 weapon row (category 0x0 weapon; row 1000007 -> base 1000000, level 7).
        assert_eq!(decode_weapon_id(1_000_007), Some((1_000_000, 7)));
        // a weapon at +0 decodes to (base, 0).
        assert_eq!(decode_weapon_id(2_000_000), Some((2_000_000, 0)));
        // out-of-range weapon row ids decode to None.
        assert_eq!(decode_weapon_id(500), None);
        // a GOODS-category id (category nibble 0x4) is NOT a weapon -> None even if row is in range.
        assert_eq!(
            decode_weapon_id((er_codec::CATEGORY_GOODS | 2_010_000) as i32),
            None
        );
        // a PROTECTOR-category id (nibble 0x1) is rejected too.
        assert_eq!(
            decode_weapon_id((er_codec::CATEGORY_PROTECTOR | 1_000_000) as i32),
            None
        );
    }

    #[test]
    fn apply_auto_upgrade_off_is_identity() {
        // With the feature off, apply_auto_upgrade is a pure identity (no game access).
        set_auto_upgrade(0);
        assert_eq!(apply_auto_upgrade(1_000_007), 1_000_007);
        assert_eq!(apply_auto_upgrade((er_codec::CATEGORY_GOODS | 2_010_000) as i32),
                   (er_codec::CATEGORY_GOODS | 2_010_000) as i32);
    }

    #[test]
    fn scadu_mode_clamp() {
        // set_global_scadu_blessing clamps to {0,1,2}.
        set_global_scadu_blessing(0);
        assert_eq!(scadu_mode(), 0);
        set_global_scadu_blessing(1);
        assert_eq!(scadu_mode(), 1);
        set_global_scadu_blessing(2);
        assert_eq!(scadu_mode(), 2);
        set_global_scadu_blessing(7); // out of range -> off
        assert_eq!(scadu_mode(), 0);
        set_global_scadu_blessing(0);
    }
}
