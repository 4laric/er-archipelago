//! Phase 5 — ER feature surface ported onto the Phase-4 net/grant plumbing.
//!
//! Almost every C++ feature is the same three-step pattern (PHASE5-PORT-PLAN.md):
//!   1. RECEIVE (net thread, keyed by item NAME): look the AP item name up in a table and QUEUE an
//!      effect (a grace/open/reveal event flag, or a one-off item grant).
//!   2. TICK (game thread): drain those queues with `flags::set_event_flag` / `detour::grant_full_id`,
//!      and poll game state (`play_region_id`, event flags) for warp latches / location sweeps.
//!   3. PERSIST: a couple of features extend the Phase-4 save (`start_items_granted`, `notify_granted`).
//!
//! Thread rule (inherited from Phase 4): NAME-keyed decisions run on the NET thread and only QUEUE;
//! every event-flag write / grant / flag read happens on the FrameBegin TICK. Never touch game memory
//! from the net thread.
//!
//! This module is the Rust port of: `CCore::FlushPendingGraceFlags`, the `pendingNotifyGrants` /
//! `pendingStartItems` drains, `CCore::PollLocationFlags`, `CCore::EvaluateNaturalKeyTriggers`, the
//! warp-latch / region-lock-KICK block in `CCore::Run`, `CGameHook::revealAllMaps`, and the
//! `set_items_received_handler` name-dispatch in `ArchipelagoInterface.cpp`.

#![allow(dead_code)] // handlers are wired ahead of every caller while Phase 5 lands

use std::collections::{HashMap, HashSet, VecDeque};
use std::sync::atomic::{AtomicBool, AtomicI32, Ordering};
use std::sync::{Mutex, OnceLock};

use super::{detour, flags, grant};

// =================================================================================================
// Slot config (parsed once at connect on the net thread; read every tick on the game thread).
// =================================================================================================

/// A natural-key trigger clause: satisfied when ALL `items` were received (by name) AND ALL `flags`
/// are set. ANY clause for a region blooms it. (`Core::NKClause`.)
#[derive(Clone, Default)]
pub struct NkClause {
    pub items: Vec<String>,
    pub flags: Vec<u32>,
}

/// Everything the server (slot_data) and apconfig tell the client to do, beyond the goods-only MVP.
/// Built by `net.rs` at connect, handed to `configure()`. All fields default-empty so an older seed
/// that omits a key is simply inert (never wrong).
#[derive(Default)]
pub struct SlotConfig {
    // --- name-keyed region-lock ecosystem (item NAME -> effect) ---
    pub region_graces: HashMap<String, Vec<u32>>, // lock item -> grace warp-unlock flags
    pub grace_items: HashMap<String, u32>,        // grace item -> one warp flag
    pub region_open_flags: HashMap<String, u32>,  // lock item -> one physical region-open flag
    pub lock_reveal_flags: HashMap<String, Vec<u32>>, // lock item -> map-reveal/open flags
    pub lock_notify_items: HashMap<String, i32>,  // lock item -> FullID granted as the unlock notice
    pub natural_key_triggers: HashMap<String, Vec<NkClause>>, // region -> clause disjunction

    // --- warp latches (game-state -> set a baked warp flag once) ---
    pub dlc_entry_warp_flag: u32,
    pub dlc_start_area_id: i32,
    pub random_start_warp_flag: u32,
    pub random_start_area_id: i32,
    pub random_start_done_flag: u32,

    // --- region-lock physical enforcement (KICK) ---
    pub area_lock_flags: Vec<[i32; 3]>, // [lo, hi, open_flag] inclusive subregion ranges

    // --- map reveal (map_option=give: no map items granted) ---
    pub reveal_all_maps: bool,
    pub enable_dlc: bool,

    // --- check polling (acquisitions that bypass the AddItemFunc detour) ---
    pub location_flags: HashMap<i64, u32>,  // apconfig: AP location id -> guarding event flag
    pub sweep_flags: HashMap<u32, Vec<i64>>, // apconfig: event flag -> AP location ids
    pub dungeon_sweeps: HashMap<i64, Vec<i64>>, // slot_data: trigger location -> member locations
}

fn config() -> &'static Mutex<SlotConfig> {
    static C: OnceLock<Mutex<SlotConfig>> = OnceLock::new();
    C.get_or_init(|| Mutex::new(SlotConfig::default()))
}

// =================================================================================================
// Cross-thread queues + per-session sets (Step 0 plumbing).
// =================================================================================================

/// Event flags queued (net thread) for the tick to SET via FlushPendingGraceFlags. Grace warp
/// flags, region-open flags, map-reveal flags, companion/key-item obtained flags, natural-key blooms.
fn pending_grace_flags() -> &'static Mutex<VecDeque<u32>> {
    static Q: OnceLock<Mutex<VecDeque<u32>>> = OnceLock::new();
    Q.get_or_init(|| Mutex::new(VecDeque::new()))
}

/// FullIDs queued (net thread) for the tick to GRANT once-per-save as an unlock notice / great-rune
/// restore (`pendingNotifyGrants`). Granted via `grant::notify_already_granted` dedup.
fn pending_notify_grants() -> &'static Mutex<VecDeque<i32>> {
    static Q: OnceLock<Mutex<VecDeque<i32>>> = OnceLock::new();
    Q.get_or_init(|| Mutex::new(VecDeque::new()))
}

/// (FullID, count) start items queued at connect (Torrent, flasks, quick_start runes), granted
/// EXACTLY ONCE per save (`pendingStartItems`).
fn pending_start_items() -> &'static Mutex<VecDeque<(i32, i32)>> {
    static Q: OnceLock<Mutex<VecDeque<(i32, i32)>>> = OnceLock::new();
    Q.get_or_init(|| Mutex::new(VecDeque::new()))
}

/// AP item NAMES received this session (rebuilt from the items_received replay on reconnect, so no
/// persistence). Drives natural-key trigger evaluation. (`Core->receivedItemNames`.)
fn received_names() -> &'static Mutex<HashSet<String>> {
    static S: OnceLock<Mutex<HashSet<String>>> = OnceLock::new();
    S.get_or_init(|| Mutex::new(HashSet::new()))
}

/// Grace flags already set THIS session — suppresses redundant SetEventFlag + log noise.
fn grace_set_this_session() -> &'static Mutex<HashSet<u32>> {
    static S: OnceLock<Mutex<HashSet<u32>>> = OnceLock::new();
    S.get_or_init(|| Mutex::new(HashSet::new()))
}

/// AP locations already reported by flag polling — dedup across ticks/sessions.
fn flag_sent_locations() -> &'static Mutex<HashSet<i64>> {
    static S: OnceLock<Mutex<HashSet<i64>>> = OnceLock::new();
    S.get_or_init(|| Mutex::new(HashSet::new()))
}

/// reveal_all_maps one-shot, re-armed each connect (`revealAllMapsPending`).
static REVEAL_MAPS_PENDING: AtomicBool = AtomicBool::new(false);

// =================================================================================================
// Const tables (client-owned, NOT slot_data). Ported verbatim from ArchipelagoInterface.cpp /
// GameHook.cpp so the same vanilla flags / restored rows fire as the C++ client.
// =================================================================================================

/// Companion items whose possession is gated by a vanilla "obtained" EVENT FLAG a raw goods-grant
/// never trips (summon tutorial, Twin Maiden dup-sale stop, whetblade affinities).
const COMPANION_ACQUIRE_FLAGS: &[(&str, &[u32])] = &[
    ("Spirit Calling Bell", &[60110]),
    ("Whetstone Knife", &[60130]),
    ("Iron Whetblade", &[65610]),
    ("Red-Hot Whetblade", &[65640]),
    ("Sanctified Whetblade", &[65660]),
    ("Glintstone Whetblade", &[65680]),
    ("Black Whetblade", &[65720]),
];

/// Vanilla KEY ITEMS whose progression gate reads an obtained EVENT FLAG, not inventory.
const KEY_ITEM_ACQUIRE_FLAGS: &[(&str, &[u32])] = &[
    ("Rold Medallion", &[400001]),   // Grand Lift of Rold
    ("Drawing-Room Key", &[400072]), // Volcano Manor drawing-room transition
];

/// Great runes arrive UNRESTORED under num_regions_rune_source=pool; granting the matching ER
/// "(Restored)" EquipParamGoods row (191-196) is the same state the Divine Tower confers, so the
/// player can equip + Rune-Arc immediately. Granted ADDITIVELY (the raw rune still grants too).
const GREAT_RUNE_RESTORE_GOODS: &[(&str, u32)] = &[
    ("Godrick's Great Rune", 191),
    ("Radahn's Great Rune", 192),
    ("Morgott's Great Rune", 193),
    ("Rykard's Great Rune", 194),
    ("Mohg's Great Rune", 195),
    ("Malenia's Great Rune", 196),
];

/// GOODS category nibble (a FullID is `id | (category << 28)`; goods = 0x4). Restored great runes +
/// map fragments are granted as goods-packed FullIDs, identical to the C++ `| 0x40000000`.
const GOODS_FULLID: i32 = 0x4000_0000u32 as i32;

/// Map fragment goods id -> its map-REVEAL event flag. The goods item only fills inventory; the
/// region map stays fogged until this separate flag is set (vanilla pickup events set both).
/// Base ids < 2_000_000; DLC (Land of Shadow) pieces are the `2008600..` block (skipped when DLC off).
const MAP_UNLOCK_FLAGS: &[(i32, u32)] = &[
    (8600, 62010), (8601, 62011), (8602, 62012), // Limgrave W, Weeping, Limgrave E
    (8603, 62020), (8604, 62021), (8605, 62022), // Liurnia E/N/W
    (8606, 62030), (8607, 62031), (8608, 62032), // Altus, Leyndell, Gelmir
    (8609, 62040), (8610, 62041),                // Caelid, Dragonbarrow
    (8611, 62050), (8612, 62051), (8618, 62052), // Mountaintops W/E, Snowfield
    (8613, 62060), (8614, 62061), (8616, 62062), // Ainsel, Lake of Rot, Mohgwyn
    (8615, 62063), (8617, 62064),                // Siofra, Deeproot
    (2008600, 62080), // Gravesite Plain  (WorldMapPieceParam 1000)
    (2008601, 62081), // Scadu Altus      (1001)
    (2008602, 62082), // Southern Shore   (1002)
    (2008603, 62083), // Rauh Ruins       (1003)
    (2008604, 62084), // Abyss            (1004)
    (2008605, 82001), // + DLC map page-unlock (synthetic key carries 82001)
];

/// KICK event flag (76970): set when the player is inside a locked region whose open-flag is off; the
/// baked common.emevd reactor warps them out to a safe Limgrave grace.
const KICK_FLAG: u32 = 76970;
/// "DLC entered" flag (62002) — guards the DLC auto-entry latch so it fires once, not on a revisit.
const DLC_ENTERED_FLAG: u32 = 62002;

// =================================================================================================
// NET THREAD — config install + name-keyed receive dispatch.
// =================================================================================================

/// Net thread, at (re)connect: install the parsed slot/apconfig tables and RESET per-session state
/// (so a fresh connect re-blooms / re-polls cleanly; persisted dedup lives in `grant`).
pub fn configure(cfg: SlotConfig) {
    REVEAL_MAPS_PENDING.store(cfg.reveal_all_maps, Ordering::Relaxed);
    *config().lock().unwrap() = cfg;
    received_names().lock().unwrap().clear();
    grace_set_this_session().lock().unwrap().clear();
    flag_sent_locations().lock().unwrap().clear();
    pending_grace_flags().lock().unwrap().clear();
    pending_notify_grants().lock().unwrap().clear();
    pending_start_items().lock().unwrap().clear();
    queue_start_items();
    queue_start_graces();
}

/// Net thread: queue the Limgrave start graces parsed at connect (drained like the on-receipt bundle).
fn queue_start_graces() {
    // start graces live in region_graces under the reserved key "" (see net.rs parse); plus any
    // dedicated startGraces vector is folded into the same queue there. Nothing to do here unless
    // we later separate them — kept as a hook so the call site reads symmetrically with start items.
}

/// Net thread: move the parsed start items onto the once-per-save queue. Called from `configure`.
fn queue_start_items() {
    // start items are parsed straight into the queue by net.rs via `enqueue_start_item`, so this is
    // a no-op hook kept for symmetry with `queue_start_graces`.
}

/// Net thread: parse-time helper so net.rs can push a Limgrave start grace flag.
pub fn enqueue_start_grace(flag: u32) {
    pending_grace_flags().lock().unwrap().push_back(flag);
}

/// Net thread: parse-time helper so net.rs can push a once-per-save start item (FullID, count).
pub fn enqueue_start_item(full_id: i32, count: i32) {
    pending_start_items().lock().unwrap().push_back((full_id, count.max(1)));
}

/// Net thread: dispatch ONE received item by NAME (idempotent — safe to call for the full replay on
/// every reconnect). Pushes effects onto the grace / notify queues; the game tick applies them.
///
/// Mirrors `set_items_received_handler`. NOTE: the caller dispatches over ALL received items (not
/// just those past the grant watermark) so the received-NAME set + idempotent flags rebuild on
/// reconnect — the GRANT path is what's deduped by `last_received_index`, not this.
pub fn on_item_received(name: &str) {
    received_names().lock().unwrap().insert(name.to_string());

    let cfg = config().lock().unwrap();
    let mut graces = pending_grace_flags().lock().unwrap();
    let mut notify = pending_notify_grants().lock().unwrap();

    // Region-fusion grace bundle: lock item -> grace warp-unlock flags.
    if let Some(fs) = cfg.region_graces.get(name) {
        for &f in fs {
            graces.push_back(f);
        }
        tracing::info!("Region lock '{}' received: queued {} grace flag(s)", name, fs.len());
    }
    // Grace rando: grace item -> one warp flag.
    if let Some(&f) = cfg.grace_items.get(name) {
        graces.push_back(f);
        tracing::info!("Grace item '{}' received: queued warp flag {}", name, f);
    }
    // Region-open (physical fog gate): lock item -> one open flag.
    if let Some(&f) = cfg.region_open_flags.get(name) {
        graces.push_back(f);
        tracing::info!("Region lock '{}' received: queued region-open flag {}", name, f);
    }
    // Generalized reveal/open: lock item -> map-reveal + enforcement-open flags.
    if let Some(fs) = cfg.lock_reveal_flags.get(name) {
        for &f in fs {
            graces.push_back(f);
        }
        tracing::info!("Region lock '{}' received: queued {} reveal/open flag(s)", name, fs.len());
    }
    // Unlock notification item (map fragment / token) -> once-per-save grant queue.
    if let Some(&addr) = cfg.lock_notify_items.get(name) {
        notify.push_back(addr);
    }

    // Companion acquisition flags.
    if let Some(fs) = lookup(COMPANION_ACQUIRE_FLAGS, name) {
        for &f in fs {
            graces.push_back(f);
        }
        tracing::info!("Companion item '{}' received: queued {} acquisition flag(s)", name, fs.len());
    }
    // Key-item acquisition flags.
    if let Some(fs) = lookup(KEY_ITEM_ACQUIRE_FLAGS, name) {
        for &f in fs {
            graces.push_back(f);
        }
        tracing::info!("Key item '{}' received: queued {} obtained-flag(s)", name, fs.len());
    }
    // Great-rune restore: ADDITIONALLY grant the "(Restored)" goods row (once per save via notify).
    if let Some(goods) = GREAT_RUNE_RESTORE_GOODS.iter().find(|(n, _)| *n == name).map(|(_, g)| *g) {
        notify.push_back((goods as i32) | GOODS_FULLID);
        tracing::info!("Great rune '{}' received: also granting restored goods {} (usable now)", name, goods);
    }
}

fn lookup(table: &'static [(&'static str, &'static [u32])], name: &str) -> Option<&'static [u32]> {
    table.iter().find(|(n, _)| *n == name).map(|(_, f)| *f)
}

// =================================================================================================
// GAME THREAD — the settled-in-world tick. Every event-flag read/write + grant happens here.
// =================================================================================================

/// Game-thread tick (called from `game::tick`). No-op until the player is settled in-world; then it
/// drains the grace/notify/start queues, reveals maps, evaluates natural keys, polls location flags,
/// and runs the warp / region-lock latches. Mirrors the in-world poll block of `CCore::Run`.
pub fn tick() {
    if !settled_in_world() {
        return;
    }
    drain_notify_grants();
    drain_start_items();
    reveal_maps_if_pending();
    flush_grace_flags();
    evaluate_natural_key_triggers();
    poll_location_flags();
    warp_and_lock_latches();
}

/// Require a real `play_region_id` for a couple of consecutive ticks before granting/setting flags —
/// the C++ `s_inWorldStableTicks >= 2` crash-fix: `InventoryInstance()!=0` goes true DURING load-in,
/// before the player is placed, and AddItem faults then.
fn settled_in_world() -> bool {
    const SETTLE_TICKS: i32 = 2;
    static STABLE: AtomicI32 = AtomicI32::new(0);
    if flags::in_world() {
        let n = STABLE.load(Ordering::Relaxed);
        if n < SETTLE_TICKS {
            STABLE.store(n + 1, Ordering::Relaxed); // saturate; never overflows on a long session
        }
        STABLE.load(Ordering::Relaxed) >= SETTLE_TICKS
    } else {
        STABLE.store(0, Ordering::Relaxed);
        false
    }
}

/// Grant queued unlock-notify items (map fragment / token) + great-rune restores, EXACTLY ONCE per
/// save. `grant::notify_already_granted` is the persisted dedup; the lock EFFECTS run separately via
/// idempotent flags, so a skipped replay needs no re-application. (`pendingNotifyGrants` drain.)
fn drain_notify_grants() {
    let mut q = pending_notify_grants().lock().unwrap();
    if q.is_empty() {
        return;
    }
    let mut granted = 0;
    let mut requeue: VecDeque<i32> = VecDeque::new();
    while let Some(addr) = q.pop_front() {
        if grant::notify_already_granted(addr) {
            continue;
        }
        if !detour::grant_full_id(addr, 1) {
            requeue.push_back(addr); // no inventory pointer captured yet; retry next tick
            continue;
        }
        grant::note_notify_granted(addr);
        granted += 1;
    }
    *q = requeue;
    drop(q);
    if granted > 0 {
        tracing::info!("Region-lock: granted {} new unlock-notify item(s)", granted);
        grant::persist();
    }
}

/// Grant the start items (Torrent, flasks, quick_start runes) EXACTLY ONCE per save. They are NOT
/// replayed through the received-item stream, so re-queuing on every reconnect would duplicate them;
/// the persisted `start_items_granted` flag gates the whole queue. (`pendingStartItems` drain.)
fn drain_start_items() {
    let mut q = pending_start_items().lock().unwrap();
    if q.is_empty() {
        return;
    }
    if grant::start_items_granted() {
        // Connect filled the queue before the persisted flag was loaded; this save already has them.
        tracing::info!("Start items: already granted this save; dropping {} re-queued item(s)", q.len());
        q.clear();
        return;
    }
    // Need an inventory pointer to grant; if not captured yet, leave the queue and retry next tick.
    let snapshot: Vec<(i32, i32)> = q.iter().copied().collect();
    let mut any = false;
    for &(id, ct) in &snapshot {
        if detour::grant_full_id(id, ct) {
            any = true;
        } else {
            return; // retry whole queue next tick (no partial once-per-save state)
        }
    }
    if any {
        tracing::info!("Start items: granted {} once-per-save item(s)", snapshot.len());
        q.clear();
        grant::set_start_items_granted();
        grant::persist();
    }
}

/// Map reveal under map_option=give: set every region's reveal flag directly (no map items granted).
/// One-shot per connect, retried until the flag holder is ready. (`revealAllMaps`.)
fn reveal_maps_if_pending() {
    if !REVEAL_MAPS_PENDING.load(Ordering::Relaxed) {
        return;
    }
    let include_dlc = config().lock().unwrap().enable_dlc;
    let mut any = false;
    for &(map_id, flag) in MAP_UNLOCK_FLAGS {
        if !include_dlc && map_id >= 2_000_000 {
            continue; // DLC map; skip when DLC off
        }
        if !flags::try_set_event_flag(flag, true) {
            return; // holder not ready; retry next tick (one shared holder for all)
        }
        any = true;
        tracing::info!("reveal_all_maps: map {} reveal flag {} SET", map_id, flag);
    }
    if any {
        REVEAL_MAPS_PENDING.store(false, Ordering::Relaxed);
    }
}

/// Set any queued grace warp-unlock / region-open / map-reveal / acquisition flags. SetEventFlag is
/// idempotent + save-persisted, so re-applying on reconnect/replay is harmless; a flag whose holder
/// isn't ready is re-queued. (`CCore::FlushPendingGraceFlags`.)
fn flush_grace_flags() {
    let mut q = pending_grace_flags().lock().unwrap();
    if q.is_empty() {
        return;
    }
    let mut session = grace_set_this_session().lock().unwrap();
    let mut retry: VecDeque<u32> = VecDeque::new();
    let mut set_count = 0;
    while let Some(flag) = q.pop_front() {
        if session.contains(&flag) {
            continue; // already set this session
        }
        if flags::try_set_event_flag(flag, true) {
            session.insert(flag);
            set_count += 1;
            tracing::info!("Region grace flag {} SET", flag);
        } else {
            retry.push_back(flag); // holder not ready; try next tick
        }
    }
    *q = retry;
    if set_count > 0 {
        tracing::info!("Region fusion: set {} grace flag(s) ({} pending)", set_count, q.len());
    }
}

/// Bloom regions whose vanilla-trigger DISJUNCTION is now satisfied. A clause is satisfied when all
/// its items were received AND all its flags are set; ANY clause fires. The region open flag doubles
/// as the once-latch. Reads event flags, so it MUST run on the settled tick.
/// (`CCore::EvaluateNaturalKeyTriggers`.)
fn evaluate_natural_key_triggers() {
    let cfg = config().lock().unwrap();
    if cfg.natural_key_triggers.is_empty() {
        return;
    }
    let names = received_names().lock().unwrap();
    let mut graces = pending_grace_flags().lock().unwrap();
    let mut notify = pending_notify_grants().lock().unwrap();

    for (name, clauses) in &cfg.natural_key_triggers {
        // Guard: needs an open flag, and that flag not already set (latch).
        let open_flag = match cfg.region_open_flags.get(name) {
            Some(&f) => f,
            None => continue,
        };
        if flags::get_event_flag(open_flag) {
            continue; // already bloomed
        }
        // Any clause satisfied?
        let fired = clauses.iter().any(|cl| {
            cl.items.iter().all(|nm| names.contains(nm))
                && cl.flags.iter().all(|&fl| flags::get_event_flag(fl))
        });
        if !fired {
            continue;
        }
        // BLOOM: queue grace + open + reveal flags (+ notify item).
        let mut queued = 0;
        if let Some(fs) = cfg.region_graces.get(name) {
            for &f in fs {
                graces.push_back(f);
                queued += 1;
            }
        }
        graces.push_back(open_flag);
        queued += 1;
        if let Some(fs) = cfg.lock_reveal_flags.get(name) {
            for &f in fs {
                graces.push_back(f);
                queued += 1;
            }
        }
        if let Some(&addr) = cfg.lock_notify_items.get(name) {
            notify.push_back(addr);
        }
        tracing::info!("Natural-key '{}' satisfied: bloomed region ({} flag(s) queued)", name, queued);
    }
}

/// Detect checks whose acquisition bypassed the AddItemFunc detour (shop buys, NPC gifts, offline
/// pickups) by polling each AP location's guarding event flag, plus dungeon + boss/grace sweeps.
/// (`CCore::PollLocationFlags`.) Reports via `flags::report_location` (the net thread sends).
fn poll_location_flags() {
    let cfg = config().lock().unwrap();
    if cfg.location_flags.is_empty() && cfg.sweep_flags.is_empty() {
        return;
    }
    let mut sent = grace_sent_guard();

    // Per-location flag poll.
    let mut n = 0;
    for (&loc, &flag) in &cfg.location_flags {
        if sent.contains(&loc) {
            continue;
        }
        if !flags::get_event_flag(flag) {
            continue;
        }
        sent.insert(loc);
        flags::report_location(loc);
        n += 1;
    }
    if n > 0 {
        tracing::info!("Flag polling: sent {} location check(s)", n);
    }

    // Dungeon sweep: when a dungeon's trigger (boss-drop) flag fires, send every remaining member.
    for (trigger, members) in &cfg.dungeon_sweeps {
        let flag = match cfg.location_flags.get(trigger) {
            Some(&f) => f,
            None => continue,
        };
        if !flags::get_event_flag(flag) {
            continue;
        }
        let mut swept = 0;
        for &m in members {
            if sent.insert(m) {
                flags::report_location(m);
                swept += 1;
            }
        }
        if swept > 0 {
            tracing::info!("Dungeon sweep: trigger {} cleared {} remaining check(s)", trigger, swept);
        }
    }

    // Boss/grace attribution sweep: sweep_flags is keyed by the event flag itself. Skip graces the
    // CLIENT force-lit this session (start graces / region bundles) — sweeping those dumps checks at
    // spawn; boss DefeatFlags are never client-set, so the boss sweep is unaffected.
    let session = grace_set_this_session().lock().unwrap();
    for (&flag, members) in &cfg.sweep_flags {
        if session.contains(&flag) {
            continue;
        }
        if !flags::get_event_flag(flag) {
            continue;
        }
        let mut swept = 0;
        for &m in members {
            if sent.insert(m) {
                flags::report_location(m);
                swept += 1;
            }
        }
        if swept > 0 {
            tracing::info!("Boss/grace sweep: flag {} cleared {} check(s)", flag, swept);
        }
    }
}

/// Borrow the flag-sent set; split out so `poll_location_flags` reads naturally.
fn grace_sent_guard() -> std::sync::MutexGuard<'static, HashSet<i64>> {
    flag_sent_locations().lock().unwrap()
}

/// Warp latches + region-lock KICK enforcement. Reads the player's area id and, once per entry, sets
/// the baked DLC/random-start warp flags and the KICK flag for a locked region. (`CCore::Run` block.)
fn warp_and_lock_latches() {
    static KICK_LATCHED: AtomicBool = AtomicBool::new(false);
    static DLC_LATCHED: AtomicBool = AtomicBool::new(false);
    static START_LATCHED: AtomicBool = AtomicBool::new(false);

    let pr = match flags::play_region_id() {
        Some(p) => p,
        None => return,
    };
    let cfg = config().lock().unwrap();

    // --- region-lock KICK (76970) ---
    // Normalize: overworld sub-areas report a 7-digit id (subregion*100); the major area reports the
    // 5-digit subregion. Reduce to the 5-digit subregion for the range match.
    let sub = if pr >= 1_000_000 { pr / 100 } else { pr };
    let locked = cfg.area_lock_flags.iter().any(|e| {
        sub >= e[0] && sub <= e[1] && !flags::get_event_flag(e[2] as u32)
    });
    if !locked {
        KICK_LATCHED.store(false, Ordering::Relaxed);
    } else if !KICK_LATCHED.load(Ordering::Relaxed) {
        // Warp-miss fallback (durable region-lock enforcement). We only reach this branch when
        // `locked` is true. The kick is normally guarded on a random-start seed until the start warp
        // sets random_start_done_flag, so the player isn't ejected from the intro spawn before
        // relocation. But if that warp never fires (Chapel not seen while connected, warp not baked
        // for this seed, continued save, area-id mismatch, ...), the guard would stay shut forever
        // and the region lock would be silently unenforced. Being in a locked region past the intro
        // area means the warp has demonstrably failed -> force the guard open. The KICK reactor warps
        // to the always-open Roundtable fallback, so this can never strand the player; and on a
        // successful warp you'd be in your OPEN start region (never locked), so it never mis-fires.
        // (Mirrors er_logic::region_lock::warp_miss_should_arm, which carries the unit tests.)
        if cfg.random_start_done_flag != 0
            && pr != cfg.random_start_area_id
            && !flags::get_event_flag(cfg.random_start_done_flag)
        {
            flags::set_event_flag(cfg.random_start_done_flag, true);
            tracing::info!(
                "RegionLock: locked area={} with start-warp guard still closed -> arming guard (warp-miss fallback)",
                pr
            );
        }
        // Start-window guard: on a random-start seed the player transiently spawns in (locked)
        // Limgrave before the baked warp pulls them out; don't arm KICK until the random-start warp
        // has fired. Non-random seeds (done flag 0) => guard always true => unchanged.
        let guard_ok = cfg.random_start_done_flag == 0
            || flags::get_event_flag(cfg.random_start_done_flag);
        if guard_ok {
            KICK_LATCHED.store(true, Ordering::Relaxed);
            flags::set_event_flag(KICK_FLAG, true);
            tracing::info!("RegionLock: area={} LOCKED -> KICK", pr);
        }
    }

    // --- DLC auto-entry: on the intro Chapel, set the baked entry flag ONCE -> warp to Gravesite ---
    if cfg.dlc_entry_warp_flag != 0
        && cfg.dlc_start_area_id != 0
        && pr == cfg.dlc_start_area_id
        && !flags::get_event_flag(DLC_ENTERED_FLAG)
        && !DLC_LATCHED.swap(true, Ordering::Relaxed)
    {
        flags::set_event_flag(cfg.dlc_entry_warp_flag, true);
        tracing::info!("DLC auto-entry: in start area {} -> set flag {}", pr, cfg.dlc_entry_warp_flag);
    }

    // --- Random starting region: same latch, for the rolled start region ---
    if cfg.random_start_warp_flag != 0
        && cfg.random_start_area_id != 0
        && cfg.random_start_done_flag != 0
        && pr == cfg.random_start_area_id
        && !flags::get_event_flag(cfg.random_start_done_flag)
        && !START_LATCHED.swap(true, Ordering::Relaxed)
    {
        flags::set_event_flag(cfg.random_start_done_flag, true);
        flags::set_event_flag(cfg.random_start_warp_flag, true);
        tracing::info!("Random start: in area {} -> set flag {}", pr, cfg.random_start_warp_flag);
    }
}

/// Called from `grant.rs` after granting an INDEX-STREAM item (the received-item queue, not the
/// notify queue): if it's a map fragment, also set its map-reveal flag. (`GiveNextItem` map branch.)
pub fn on_index_grant(full_id: i32) {
    if (full_id & 0xF000_0000u32 as i32) != GOODS_FULLID {
        return;
    }
    let base = full_id & 0x0FFF_FFFF;
    if let Some(&(_, flag)) = MAP_UNLOCK_FLAGS.iter().find(|(id, _)| *id == base) {
        let ok = flags::try_set_event_flag(flag, true);
        tracing::info!("Map fragment {}: reveal flag {} {}", base, flag, if ok { "SET" } else { "FAILED (holder not ready)" });
    }
}
