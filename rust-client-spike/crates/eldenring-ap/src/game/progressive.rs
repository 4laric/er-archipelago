//! Phase 5 (Wave C) — progressive grants ported onto the Phase-4 net/grant plumbing.
//!
//! "Progressive" AP items ship MORE copies than they have tiers (e.g. `progressive_stone_bell`,
//! `progressive_physick`): the Kth copy received resolves tier K-1, which sets that tier's shop /
//! affinity EVENT FLAGS and grants that tier's GOODS, and every copy PAST the last tier is converted
//! into one Lord's Rune so the surplus copies aren't dead no-ops. This is the Rust port of the
//! `progressiveGrants` block of `ArchipelagoInterface.cpp` (parse ~216-236, receive ~448-488) and the
//! `progressive_counter` / `progressive_high_index` persistence in `Core.cpp` (LoadSaveFile ~906-910,
//! WriteSaveFile ~1069-1089).
//!
//! Three-step pattern, IDENTICAL to features.rs:
//!   1. RECEIVE (net thread, keyed by item NAME): `on_item_received` resolves the tier (index-deduped
//!      against the persisted `progressive_high_index`), then QUEUES that tier's flags + goods (or one
//!      overflow Lord's Rune). It returns `true` so the caller SKIPS the normal grant (the C++
//!      `continue`).
//!   2. TICK (game thread): `tick` drains the goods queue via `detour::grant_full_id` and the flag
//!      queue via `flags::try_set_event_flag`, requeuing anything whose holder isn't ready yet —
//!      exactly like `features::drain_notify_grants` / `flush_grace_flags`.
//!   3. PERSIST: `progressive_counter` + `progressive_high_index` round-trip through the per-seed save
//!      OWNED BY grant.rs. This module never writes a save file: it exposes `snapshot()` for
//!      `grant::write_save` to serialize and `restore()` for `grant::configure` to load, and calls
//!      `grant::persist()` when a tier advances (see PROGRESSIVE-WIRING.md).
//!
//! Thread rule (inherited, CRITICAL): the NAME-keyed tier decision + queueing run on the NET thread
//! and ONLY touch our own queues + the persisted high-index/counter; every `grant_full_id` and every
//! event-flag write happens on the FrameBegin TICK. Never touch game memory from the net thread.

#![allow(dead_code)] // wired ahead of every caller while Phase 5 lands

use std::collections::{HashMap, VecDeque};
use std::sync::atomic::{AtomicI64, Ordering};
use std::sync::{Mutex, OnceLock};

use super::{detour, flags, grant};

// =================================================================================================
// Parsed config (built once at connect on the net thread; read on every receive on the net thread).
// =================================================================================================

/// One rung of a progressive item: the GOODS (bare EquipParamGoods ids, goods-packed at grant time)
/// and the EVENT FLAGS (shop / affinity unlocks) that this tier confers. Mirrors the C++
/// `std::pair<std::vector<uint32_t> goods, std::vector<uint32_t> flags>`.
#[derive(Clone, Default)]
pub struct ProgTier {
    pub goods: Vec<u32>,
    pub flags: Vec<u32>,
}

/// GOODS category nibble (a FullID is `id | (category << 28)`; goods = 0x4). Tier goods + the overflow
/// Lord's Rune are granted as goods-packed FullIDs, identical to the C++ `| 0x40000000`. Kept in sync
/// with the same constant in features.rs.
const GOODS_FULLID: i32 = 0x4000_0000u32 as i32;

/// EquipParamGoods id of a single Lord's Rune (50,000 runes). Granted for every overflow copy past the
/// last tier — one acquisition popup, like the cosmetic bell. (`ArchipelagoInterface.cpp` ~482.)
const LORDS_RUNE_GOODS: u32 = 2919;

/// Installed config: progressive item NAME -> ordered tiers. `OnceLock<Mutex<..>>` so the net thread
/// installs it at connect and reads it on every receipt, matching features.rs's `config()`.
fn config() -> &'static Mutex<HashMap<String, Vec<ProgTier>>> {
    static C: OnceLock<Mutex<HashMap<String, Vec<ProgTier>>>> = OnceLock::new();
    C.get_or_init(|| Mutex::new(HashMap::new()))
}

// =================================================================================================
// Persisted state (round-trips through grant.rs's per-seed save; see snapshot/restore below).
// =================================================================================================

/// Per-name tier counter: how many copies of each progressive item have ALREADY advanced a tier.
/// The Kth advance reads `tiers[K]` then increments (post-increment, like the C++ `[name]++`).
/// Persisted via `snapshot`/`restore` so reconnects don't recompute tiers from 0.
fn counter() -> &'static Mutex<HashMap<String, i32>> {
    static C: OnceLock<Mutex<HashMap<String, i32>>> = OnceLock::new();
    C.get_or_init(|| Mutex::new(HashMap::new()))
}

/// Highest AP `item.index` already applied to a progressive tier. Only a copy whose `index` exceeds
/// this advances a tier; replayed copies (reconnect / new session) are skipped. Default -1 so the
/// first real item (index 0) advances. (`Core->progressiveHighIndex`, default -1.)
static HIGH_INDEX: AtomicI64 = AtomicI64::new(-1);

// =================================================================================================
// Cross-thread queues (net thread QUEUES; game tick DRAINS — Step-0 plumbing, same as features.rs).
// =================================================================================================

/// Goods-packed FullIDs queued (net thread) for the tick to GRANT — tier goods + overflow Lord's
/// Runes. Drained via `detour::grant_full_id`, requeued on failure (like `drain_notify_grants`).
fn pending_grants() -> &'static Mutex<VecDeque<i32>> {
    static Q: OnceLock<Mutex<VecDeque<i32>>> = OnceLock::new();
    Q.get_or_init(|| Mutex::new(VecDeque::new()))
}

/// Event flags queued (net thread) for the tick to SET — tier shop/affinity unlocks. SetEventFlag is
/// idempotent + save-persisted, so a skipped replay needs no re-application (like the grace queue).
fn pending_flags() -> &'static Mutex<VecDeque<u32>> {
    static Q: OnceLock<Mutex<VecDeque<u32>>> = OnceLock::new();
    Q.get_or_init(|| Mutex::new(VecDeque::new()))
}

// =================================================================================================
// NET THREAD — parse, install, name-keyed receive.
// =================================================================================================

/// Net thread, at parse time: tolerantly parse slot_data `progressiveGrants` into name -> tiers.
///
/// Shape: an OBJECT mapping each progressive item NAME to an ARRAY of tiers; each tier is an object
/// with `flags` (array of u32) and EITHER `goodsList` (array of u32) OR `goods` (a scalar u32). A tier
/// with NEITHER goods key is SKIPPED — never panics. This is the deliberate fix for the C++
/// "key goods not found" bug, where a throw in the parse aborted the whole slot_data handler and
/// silently killed ALL item grants. Anything missing/mis-typed is treated as empty, never fatal.
pub fn parse(sd: &serde_json::Value) -> HashMap<String, Vec<ProgTier>> {
    let mut out: HashMap<String, Vec<ProgTier>> = HashMap::new();
    let obj = match sd.get("progressiveGrants").and_then(|v| v.as_object()) {
        Some(o) => o,
        None => return out, // absent / wrong type -> no progressive items (older seed = inert)
    };
    for (name, tiers_val) in obj {
        let arr = match tiers_val.as_array() {
            Some(a) => a,
            None => continue, // tier list isn't an array -> skip this name, don't panic
        };
        let mut tiers: Vec<ProgTier> = Vec::with_capacity(arr.len());
        for t in arr {
            let mut tier = ProgTier::default();
            // flags: optional array of u32.
            if let Some(fs) = t.get("flags").and_then(|f| f.as_array()) {
                for f in fs {
                    if let Some(n) = f.as_u64() {
                        tier.flags.push(n as u32);
                    }
                }
            }
            // goods: prefer the `goodsList` array (e.g. progressive_physick = a tear family per step),
            // else a single scalar `goods` (bells / consumables). A tier with NEITHER is kept only if
            // it still carries flags; a fully empty tier is dropped (matches "skipped, never thrown").
            if let Some(gl) = t.get("goodsList").and_then(|g| g.as_array()) {
                for g in gl {
                    if let Some(n) = g.as_u64() {
                        tier.goods.push(n as u32);
                    }
                }
            } else if let Some(g) = t.get("goods").and_then(|g| g.as_u64()) {
                tier.goods.push(g as u32);
            }
            if tier.goods.is_empty() && tier.flags.is_empty() {
                continue; // nothing to do for this rung -> skip (the C++ "neither key" tolerance)
            }
            tiers.push(tier);
        }
        out.insert(name.clone(), tiers);
    }
    out
}

/// Net thread, at (re)connect: install the parsed tier table and RESET per-session queues (so a fresh
/// connect re-queues cleanly). The persisted counter + high-index are NOT reset here — they are
/// restored from the save by `restore()` (called from grant.rs) and carry across reconnects, which is
/// what makes the replayed item stream skip already-applied tiers.
pub fn configure(map: HashMap<String, Vec<ProgTier>>) {
    *config().lock().unwrap() = map;
    pending_grants().lock().unwrap().clear();
    pending_flags().lock().unwrap().clear();
    let n: usize = config().lock().unwrap().len();
    if n > 0 {
        tracing::info!("Progressive: {} progressive item(s) loaded", n);
    }
}

/// Net thread: handle ONE received item by NAME. Returns `true` if `name` is a progressive item, so
/// the caller must SKIP its normal grant enqueue (the C++ `continue`); `false` lets the caller grant
/// it normally.
///
/// Index dedup (CRITICAL): only a copy whose `ap_index` exceeds the persisted `HIGH_INDEX` advances a
/// tier. Replayed copies on a reconnect / new session are below the high-index and are skipped, so the
/// persisted counter stays correct across sessions. The shop/affinity flags are ER event flags that
/// persist in the game save, so a skipped replay needs no re-application. (`ArchipelagoInterface.cpp`
/// ~448-488.)
pub fn on_item_received(name: &str, ap_index: i64) -> bool {
    // Is this a progressive item at all? Clone the tier list so we hold no config lock while touching
    // the queues (mirrors the lock discipline in features.rs).
    let tiers = match config().lock().unwrap().get(name) {
        Some(t) => t.clone(),
        None => return false, // not progressive -> caller grants normally
    };

    // Dedup against the persisted high-index. A replayed copy (index <= high) is "handled" (we still
    // return true to skip the normal grant, exactly like the C++ which `continue`s inside the find)
    // but advances NO tier.
    if ap_index <= HIGH_INDEX.load(Ordering::Relaxed) {
        return true;
    }

    // Advance the per-name counter: read tier K, then increment (post-increment `[name]++`).
    let k = {
        let mut c = counter().lock().unwrap();
        let slot = c.entry(name.to_string()).or_insert(0);
        let k = *slot;
        *slot += 1;
        k
    };

    if (k as usize) < tiers.len() {
        let tier = &tiers[k as usize];
        let mut flagq = pending_flags().lock().unwrap();
        for &f in &tier.flags {
            flagq.push_back(f);
        }
        drop(flagq);
        let mut grantq = pending_grants().lock().unwrap();
        for &g in &tier.goods {
            grantq.push_back((g as i32) | GOODS_FULLID);
        }
        drop(grantq);
        tracing::info!(
            "Progressive '{}' #{}: {} goods + {} shop flag(s)",
            name,
            k + 1,
            tier.goods.len(),
            tier.flags.len()
        );
    } else {
        // Overflow copy past the last tier: every shop rung this item unlocks is already live, so this
        // copy would be a dead no-op. Convert it into one Lord's Rune (goods-packed FullID), one
        // acquisition popup. The index dedup means each REAL overflow copy grants exactly once.
        pending_grants()
            .lock()
            .unwrap()
            .push_back((LORDS_RUNE_GOODS as i32) | GOODS_FULLID);
        tracing::info!(
            "Progressive '{}' #{}: max tier reached -> queued 1 Lord's Rune",
            name,
            k + 1
        );
    }

    HIGH_INDEX.store(ap_index, Ordering::Relaxed);
    true
}

// =================================================================================================
// GAME THREAD — drain queues (grants + flags), persist when a tier advanced.
// =================================================================================================

/// Game-thread tick (called from `game::tick`, next to `features::tick`). Drains the progressive goods
/// queue via `detour::grant_full_id` (requeue on failure, no inventory pointer yet) and the flag queue
/// via `flags::try_set_event_flag` (requeue if the holder isn't up). When anything landed, persists
/// the counter + high-index through grant.rs's save (`grant::persist`). No-op until settled in-world
/// is enforced by the grant/flag holders returning false, exactly like features.rs's drains.
pub fn tick() {
    let mut advanced = false;
    advanced |= drain_grants();
    advanced |= drain_flags();
    if advanced {
        grant::persist();
    }
}

/// Drain the goods queue. Mirrors `features::drain_notify_grants`: grant each FullID via the detour;
/// if the inventory pointer isn't captured yet (`grant_full_id` returns false), requeue and retry next
/// tick. Returns true if at least one item was granted (so the tick persists the updated high-index).
fn drain_grants() -> bool {
    let mut q = pending_grants().lock().unwrap();
    if q.is_empty() {
        return false;
    }
    let mut granted = 0;
    let mut requeue: VecDeque<i32> = VecDeque::new();
    while let Some(addr) = q.pop_front() {
        if !detour::grant_full_id(addr, 1) {
            requeue.push_back(addr); // no inventory pointer yet; retry next tick
            continue;
        }
        granted += 1;
    }
    *q = requeue;
    drop(q);
    if granted > 0 {
        tracing::info!("Progressive: granted {} queued goods item(s)", granted);
    }
    granted > 0
}

/// Drain the flag queue. Mirrors `features::flush_grace_flags`: set each flag via `try_set_event_flag`;
/// if the holder (`CSEventFlagMan`) isn't up yet, requeue and retry next tick. SetEventFlag is
/// idempotent + save-persisted. Returns true if at least one flag landed.
fn drain_flags() -> bool {
    let mut q = pending_flags().lock().unwrap();
    if q.is_empty() {
        return false;
    }
    let mut set_count = 0;
    let mut retry: VecDeque<u32> = VecDeque::new();
    while let Some(flag) = q.pop_front() {
        if flags::try_set_event_flag(flag, true) {
            set_count += 1;
            tracing::info!("Progressive shop flag {} SET", flag);
        } else {
            retry.push_back(flag); // holder not ready; try next tick
        }
    }
    *q = retry;
    drop(q);
    if set_count > 0 {
        tracing::info!("Progressive: set {} shop flag(s)", set_count);
    }
    set_count > 0
}

// =================================================================================================
// PERSISTENCE — owned by grant.rs's per-seed save; we only snapshot / restore the two fields.
// =================================================================================================

/// Snapshot the persisted state for grant.rs to serialize INTO the per-seed save file alongside
/// `last_received_index`. Returns `(progressive_counter as a JSON object {name: int}, high_index)`,
/// matching the C++ `k["progressive_counter"]` / `k["progressive_high_index"]` keys.
pub fn snapshot() -> (serde_json::Value, i64) {
    let c = counter().lock().unwrap();
    let map: serde_json::Map<String, serde_json::Value> = c
        .iter()
        .map(|(k, &v)| (k.clone(), serde_json::Value::from(v)))
        .collect();
    (serde_json::Value::Object(map), HIGH_INDEX.load(Ordering::Relaxed))
}

/// Restore the persisted state from the per-seed save at (re)connect — called BY grant.rs's
/// `configure` after it reads the file. `counter` is the `progressive_counter` object ({name: int});
/// `high_index` is `progressive_high_index` (default -1 if the key was absent). Tolerant: a missing /
/// mis-typed entry is ignored, never fatal. (`Core.cpp` LoadSaveFile ~906-910.)
pub fn restore(counter_json: &serde_json::Value, high_index: i64) {
    let mut c = counter().lock().unwrap();
    c.clear();
    if let Some(obj) = counter_json.as_object() {
        for (name, v) in obj {
            if let Some(n) = v.as_i64() {
                c.insert(name.clone(), n as i32);
            }
        }
    }
    HIGH_INDEX.store(high_index, Ordering::Relaxed);
}
