//! Phase 4 — Archipelago networking. Rust port of `ArchipelagoInterface.cpp`'s protocol layer onto
//! nex3's `archipelago_rs` (the crate fswap's DS3/Sekiro clients use). The crate is POLL-based
//! (`Connection::update()` returns the events since the last poll), so it needs no async runtime —
//! it runs on this worker thread (the one `game::init()` parks), strictly off the game thread.
//!
//! Scope = SPEC §4 phase 4 MVP (goods-only end-to-end): connect, read the minimal slot_data, push
//! received items onto the `grant` queue, drain our collected-location queue into `mark_checked`,
//! and report GOAL (ec 0/1 boss flag via the game tick, ec>=2 via goalLocations). The large slot_data
//! feature surface (region graces, natural keys, progressive bells, DLC auto-entry, …) is Phase 5
//! (see PHASE5-PORT-PLAN.md), so we read slot_data out of a `serde_json::Value` field-by-field with
//! defaults — a malformed/extra/unexpected field can never fail the CONNECTION (a typed slot_data
//! struct would: e.g. `enable_dlc` ships as an int 0/1, not a JSON bool).

#![allow(dead_code)] // signal_goal()/persisted_index() are wired ahead of their Phase-5 callers

use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, AtomicU32, Ordering};
use std::time::Duration;

use archipelago_rs as ap;
use serde::Deserialize;

use super::{deathlink, features, flags, grant, progressive, scout_proof, upgrades};

/// `apconfig.json` (next to the game exe, or $ER_AP_CONFIG). The console-prompt flow the C++ used is
/// replaced by a config file for the spike (SPEC §6 lists this as an accepted option). This is OUR
/// file with a fixed shape, so a typed struct is fine here (unlike server slot_data).
#[derive(Debug, Default, Deserialize)]
struct ApConfig {
    /// `host:port`, e.g. "archipelago.gg:38281".
    url: String,
    #[serde(default)]
    slot: Option<String>,
    #[serde(default)]
    password: Option<String>,
    /// AP location id (stringified) -> guarding event flag. Polled each tick to catch checks whose
    /// acquisition bypasses the AddItemFunc detour (shop buys, NPC gifts, offline pickups). Emitted
    /// by the ER bake INTO apconfig (NOT slot_data). (`location_flags` in CCore::LoadConfigFile.)
    #[serde(default)]
    location_flags: HashMap<String, u32>,
    /// Boss/grace attribution sweep: event flag (stringified) -> AP location ids it clears.
    /// Present only when the apworld's dungeon_sweep == bosses. (`sweep_flags`.)
    #[serde(default)]
    sweep_flags: HashMap<String, Vec<i64>>,
    /// DeathLink hint: the `DeathLink` Connect tag must be advertised at CONNECT (before slot_data
    /// arrives), so it's sourced from apconfig. slot_data `options.death_link` is the source of truth
    /// once connected and corrects `is_enabled()`; this only makes the tag right on the first connect.
    #[serde(default)]
    death_link: bool,
}

static GOAL_REACHED: AtomicBool = AtomicBool::new(false);
/// Boss DEFEAT flag for ending_condition 0/1 (0 = none / ec>=2 uses goalLocations). Set at slot_data
/// parse; the GAME tick polls it (event-flag reads must run on the game thread).
static GOAL_FLAG: AtomicU32 = AtomicU32::new(0);

/// Phase 5 will call this from the game tick when the slot's ending condition is detected; the net
/// loop turns it into one `set_status(Goal)`.
pub fn signal_goal() {
    GOAL_REACHED.store(true, Ordering::Relaxed);
}

/// The ending_condition 0/1 boss flag the game tick should poll (0 = none).
pub fn goal_flag() -> u32 {
    GOAL_FLAG.load(Ordering::Relaxed)
}

/// Worker-thread entry. Loads apconfig, then connect-and-serve in a reconnect loop. Never returns
/// (keeps the FrameBegin task handle in `init()` alive).
pub fn run() {
    let cfg = match load_apconfig() {
        Some(c) if !c.url.is_empty() => c,
        _ => return, // load_apconfig already logged where it looked
    };
    tracing::info!("AP: config loaded; target {}", cfg.url);
    // DeathLink tag must be known at Connect time (before slot_data); seed it from apconfig. slot_data
    // corrects it once connected. (See deathlink.rs / DEATHLINK-WIRING.md.)
    deathlink::set_enabled(cfg.death_link);

    loop {
        connect_and_serve(&cfg);
        tracing::warn!("AP: connection closed; reconnecting in 5s");
        std::thread::sleep(Duration::from_secs(5));
    }
}

/// One connection lifecycle: build a `Connection`, poll it, and pump items/checks until it drops.
fn connect_and_serve(cfg: &ApConfig) {
    let slot = cfg.slot.clone().unwrap_or_default();

    let mut opts = ap::ConnectionOptions::new().receive_items(ap::ItemHandling::OtherWorlds {
        own_world: true,        // echo self-found items (shop buys bypass the detour) — C++ 0b111
        starting_inventory: true,
    });
    if let Some(pw) = &cfg.password {
        if !pw.is_empty() {
            opts = opts.password(pw.clone());
        }
    }
    // DeathLink (Wave D): tags() REPLACES the set, and the server reads tags only at Connect — so add
    // it here, before slot_data. `ap::tags::DEATH_LINK` = "DeathLink". (DEATHLINK-WIRING.md §2a.)
    if deathlink::is_enabled() {
        opts = opts.tags([ap::tags::DEATH_LINK]);
    }

    // slot_data read as serde_json::Value (the default S), so no field-type assumption can fail the
    // connection. &str satisfies Into<String>/Into<Ustr> without relying on &String coercions.
    let mut conn: ap::Connection<serde_json::Value> =
        ap::Connection::new(cfg.url.as_str(), slot.as_str(), Some("EldenRing"), opts);

    let mut configured = false;
    let mut pushed_through: i64 = 0; // highest received index already pushed to the GRANT queue
    let mut dispatched_through: i64 = 0; // highest index whose NAME-dispatch (flags/sets) has run.
    // Starts at 0 EACH connect (not the persisted index): the name-keyed effects (grace flags,
    // received-name set for natural keys) are idempotent and must replay the FULL items_received
    // stream on reconnect, unlike the grant path which resumes at the persisted index.
    let mut goal_sent = false;
    let mut deathlink_tag_synced = false; // Wave D: ConnectUpdate-correct the DeathLink tag once/connect
    let mut item_map: HashMap<i64, i64> = HashMap::new(); // AP item id -> ER FullID
    let mut item_counts: HashMap<i64, i64> = HashMap::new();
    let mut goal_locations: Vec<i64> = Vec::new();
    let mut goal_via_locations = false;
    // STEP 0 pre-scout proof: issued once after slot_data parse, polled each tick (result arrives on a
    // later conn.update()). Loop-scoped so it resets each connect/reconnect like the watermarks above.
    let mut scout: Option<scout_proof::ScoutProof> = None;

    loop {
        // 1) Drain server events (owned Vec, so the &mut borrow on conn ends here).
        for ev in conn.update() {
            match ev {
                ap::Event::Connected => tracing::info!("AP: connected to {} as {}", cfg.url, slot),
                ap::Event::ReceivedItems(first) => {
                    tracing::debug!("AP: ReceivedItems from index {first}")
                }
                ap::Event::Print(p) => tracing::info!("AP: {}", p),
                ap::Event::Error(e) => {
                    tracing::error!("AP: connection error: {e}");
                    return;
                }
                ap::Event::DeathLink { source, cause, .. } => {
                    // Wave D: latch a kill for the game tick (deathlink::tick); self-source echoes are
                    // suppressed inside the handler. (DEATHLINK-WIRING.md §2c.)
                    deathlink::on_death_link_event(&source, cause.as_deref(), slot.as_str());
                }
                _ => {}
            }
        }

        // 2) On first sight of the connected client, read slot_data (field-by-field, all optional).
        if !configured {
            if let Some(client) = conn.client() {
                let sd = client.slot_data(); // &serde_json::Value
                item_map = i64_map(sd.get("apIdsToItemIds"));
                item_counts = i64_map(sd.get("itemCounts"));

                if let Some(range) = sd.get("versions").and_then(|v| v.as_str()) {
                    if !crate::contract_satisfies(range) {
                        tracing::warn!(
                            "AP: contract {} not in server range {} — update one side",
                            crate::CONTRACT_VERSION,
                            range
                        );
                    }
                }

                let seed = sd.get("seed").and_then(|v| v.as_str()).unwrap_or("");
                let sd_slot = sd.get("slot").and_then(|v| v.as_str()).unwrap_or("");
                let slot_name = if sd_slot.is_empty() { slot.as_str() } else { sd_slot };
                let save_path = save_path_for(seed, slot_name);
                let start_index = load_last_index(&save_path);
                grant::configure(save_path, start_index);
                pushed_through = start_index;

                // Goal config (ec 0/1 boss flag vs ec>=2 goalLocations). enable_dlc ships as int 0/1.
                let ec = sd.pointer("/options/ending_condition").and_then(|v| v.as_i64()).unwrap_or(1);
                let dlc = sd
                    .pointer("/options/enable_dlc")
                    .map(|v| v.as_bool().unwrap_or_else(|| v.as_i64().unwrap_or(0) != 0))
                    .unwrap_or(false);
                if ec >= 2 {
                    goal_locations = sd
                        .get("goalLocations")
                        .and_then(|v| v.as_array())
                        .map(|a| a.iter().filter_map(|x| x.as_i64()).collect())
                        .unwrap_or_default();
                    goal_via_locations = !goal_locations.is_empty();
                    GOAL_FLAG.store(0, Ordering::Relaxed);
                    tracing::info!("AP: goal = all {} goal location(s) checked (ec {})", goal_locations.len(), ec);
                } else {
                    let flag: u32 = if ec == 0 && dlc { 20_012_802 } else { 19_000_800 };
                    GOAL_FLAG.store(flag, Ordering::Relaxed);
                    tracing::info!("AP: goal = boss defeat flag {} (ec {}, dlc {})", flag, ec, dlc);
                }

                // Phase 5: build the feature config (region-lock ecosystem, warp latches, map
                // reveal, sweeps) from slot_data + apconfig and install it. configure() RESETS the
                // per-session queues, so start graces/items are enqueued AFTER it.
                let feat = build_slot_config(sd, dlc, cfg);
                features::configure(feat);

                // Pure-runtime (no-baker) check detection + vanilla suppression. slot_data now emits
                // `locationFlags` (location_id -> acquisition flag), `checkItemIds` (category-packed
                // FullIDs that are the vanilla contents of a check), and `checkItemFlags` (FullID ->
                // guarding flags). Build the host-tested decision tables (er-logic) and install them
                // where the game tick + detour reach them. Every field is optional/tolerant, so a
                // bake-path seed that omits them leaves both tables inert (no-op).
                let location_flags = i64_to_u32_map(sd.get("locationFlags"));
                // [shop-detect] shopRowFlags: ShopLineupParam row id -> AP tracking flag. The client
                // writes each row's eventFlag_forStock so a vanilla shop purchase sets the flag the
                // poller already watches. Only configure when the KEY IS PRESENT (the apworld patch
                // always emits it, empty {} when shop_checks is off); a pre-patch seed omits the key
                // entirely, so we leave shop_flags on its embedded fallback. Keyed/valued as u32.
                if let Some(srf) = sd.get("shopRowFlags") {
                    let shop_row_flags = i64_to_u32_map(Some(srf));
                    super::shop_flags::configure(
                        shop_row_flags.into_iter().map(|(r, f)| (r as u32, f)).collect(),
                    );
                }
                // [shop-preview] shopPreviewGoods: AP location id -> the vanilla good id that shop slot
                // displays. The client overwrites that good's GoodsName/Caption with the scouted AP item.
                if let Some(spg) = sd.get("shopPreviewGoods") {
                    let m = i64_to_u32_map(Some(spg));
                    super::shop_preview::configure(
                        m.into_iter().map(|(loc, g)| (loc, g as i32)).collect(),
                    );
                }
                // STEP 0: build (don't issue) the pre-scout proof from the seed's check locations.
                // Construct-only here (conn.client() is borrowed immutably in this block); pump() issues
                // and polls below where conn.client_mut() is free. See PRE-SCOUT-PROOF.md.
                scout = Some(scout_proof::ScoutProof::new(location_flags.keys().copied().collect()));
                if !location_flags.is_empty() {
                    let lc = er_logic::location_check::LocationChecks::from_location_flags(&location_flags);
                    // Prime from the server's already-checked locations so a reconnect mid-run
                    // doesn't re-report. The only ids LocationChecks tracks are the keys of
                    // locationFlags, so query those (is_local_location_checked is per-id; net.rs
                    // already uses it for the ec>=2 goal path).
                    let mut checked: std::collections::HashSet<i64> = std::collections::HashSet::new();
                    for &loc in location_flags.keys() {
                        if client.is_local_location_checked(loc) {
                            checked.insert(loc);
                        }
                    }
                    tracing::info!(
                        "AP: pure-runtime location detection: {} flag(s), {} already checked",
                        lc.flag_count(),
                        checked.len()
                    );
                    flags::configure_location_checks(lc, &checked);
                }

                // Vanilla suppressor: pick the mode from slot_data (flag-gated > id-set > none) via
                // the host-tested constructor (er_logic). Installed where add_item_detour reaches it.
                if let Some(sup) = er_logic::vanilla_suppress::VanillaSuppressor::from_slot_data(
                    i32_to_u32vec_map(sd.get("checkItemFlags")),
                    i32_set(sd.get("checkItemIds")),
                ) {
                    tracing::info!("AP: vanilla suppressor: {} check item(s)", sup.len());
                    super::detour::configure_suppressor(sup);
                }

                // Phase 5 parallel tracks, configured off the same slot_data:
                progressive::configure(progressive::parse(sd)); // Wave C tier tables
                deathlink::configure_from_slot_data(sd); // Wave D: corrects is_enabled() from options.death_link
                upgrades::set_auto_upgrade(
                    sd.pointer("/options/auto_upgrade").and_then(|v| v.as_i64()).unwrap_or(0) as i32,
                );
                upgrades::set_global_scadu_blessing(
                    sd.pointer("/options/global_scadutree_blessing").and_then(|v| v.as_i64()).unwrap_or(0) as i32,
                );
                if let Some(arr) = sd.get("startGraces").and_then(|v| v.as_array()) {
                    let mut n = 0;
                    for f in arr {
                        if let Some(fl) = f.as_u64() {
                            features::enqueue_start_grace(fl as u32);
                            n += 1;
                        }
                    }
                    if n > 0 {
                        tracing::info!("AP: queued {} Limgrave start grace(s)", n);
                    }
                }
                if let Some(arr) = sd.get("startItems").and_then(|v| v.as_array()) {
                    let mut n = 0;
                    for e in arr {
                        if let Some(pair) = e.as_array() {
                            let id = pair.first().and_then(|x| x.as_i64()).unwrap_or(0) as i32;
                            let ct = pair.get(1).and_then(|x| x.as_i64()).unwrap_or(1) as i32;
                            if id != 0 {
                                features::enqueue_start_item(id, ct);
                                n += 1;
                            }
                        } else if let Some(id) = e.as_i64() {
                            features::enqueue_start_item(id as i32, 1);
                            n += 1;
                        }
                    }
                    if n > 0 {
                        tracing::info!("AP: queued {} once-per-save start item(s)", n);
                    }
                }
                dispatched_through = 0; // replay name-dispatch from the start on this connect

                tracing::info!(
                    "AP: slot_data parsed ({} item-map entries); resuming at received index {}",
                    item_map.len(),
                    start_index
                );
                configured = true;
            }
        }

        // 2c) Wave D: make the DeathLink Connect tag authoritative from slot_data. The server
        // reads tags only at the Connect handshake; the tag was seeded from apconfig.death_link
        // (which the baker doesn't write -> defaults false), so without this the server never
        // routes DeathLinks to us. slot_data.options.death_link is the source of truth but arrives
        // AFTER Connect. If the seed disagreed, send a ConnectUpdate to set/clear the tag. Once per
        // connect (deathlink_tag_synced resets because connect_and_serve re-runs on reconnect).
        if configured && !deathlink_tag_synced {
            if cfg.death_link == deathlink::is_enabled() {
                deathlink_tag_synced = true; // tag already correct from Connect; nothing to send
            } else if let Some(client) = conn.client_mut() {
                let tags: Vec<&str> = if deathlink::is_enabled() {
                    vec![ap::tags::DEATH_LINK]
                } else {
                    vec![]
                };
                match client.update_connection(None, Some(tags)) {
                    Ok(()) => {
                        deathlink_tag_synced = true;
                        tracing::info!(
                            "AP: corrected DeathLink tag via ConnectUpdate (apconfig={}, slot_data={})",
                            cfg.death_link,
                            deathlink::is_enabled()
                        );
                    }
                    Err(e) => tracing::warn!("AP: DeathLink tag ConnectUpdate failed: {e}"),
                }
            }
        }

        // 3) Process received items. NAME-dispatch (idempotent grace flags / region-lock effects /
        // received-name set) runs over the FULL replay each connect (idx >= dispatched_through);
        // the GRANT enqueue resumes at the persisted index (idx >= pushed_through) to avoid
        // re-granting. Both watermarks advance independently. (set_items_received_handler split.)
        if configured {
            if let Some(client) = conn.client() {
                for ri in client.received_items() {
                    let idx = ri.index() as i64;
                    let name = ri.item().name().to_string();
                    let mut is_progressive = false;

                    if idx >= dispatched_through {
                        features::on_item_received(&name);
                        // Progressive (Wave C): advances its own tier (persisted index-deduped) and
                        // returns true for progressive items, which carry their OWN grant queue —
                        // so the normal grant below is SKIPPED (mirrors the C++ handler's `continue`).
                        is_progressive = progressive::on_item_received(&name, idx);
                        dispatched_through = idx + 1;
                    }

                    if idx >= pushed_through {
                        if !is_progressive {
                            let ap_item_id = ri.item().id();
                            match item_map.get(&ap_item_id) {
                                Some(&full_id) => {
                                    let qty = item_counts.get(&ap_item_id).copied().unwrap_or(1).max(1);
                                    grant::enqueue(grant::GrantMsg {
                                        full_id: full_id as i32,
                                        qty: qty as i32,
                                        ap_index: idx,
                                        name,
                                    });
                                }
                                None => tracing::warn!(
                                    "AP: received item id {} not in apIdsToItemIds; skipping (check seed options)",
                                    ap_item_id
                                ),
                            }
                        }
                        pushed_through = idx + 1;
                    }
                }
            }
        }

        // 4) Send our collected locations (filled by the AddItemFunc detour via flags::report_location).
        let checks = flags::drain_reported();
        if !checks.is_empty() {
            if let Some(client) = conn.client_mut() {
                let n = checks.len();
                if let Err(e) = client.mark_checked(checks) {
                    tracing::warn!("AP: mark_checked failed ({e}); {n} check(s) dropped");
                } else {
                    tracing::debug!("AP: sent {n} location check(s)");
                }
            } else {
                for c in checks {
                    flags::report_location(c); // re-queue; not connected yet
                }
            }
        }

        // 5a) ending_condition 2/3 goal: all goalLocations checked (server-truth, retroactive on
        // reconnect). ec 0/1 boss-flag goals are detected on the game tick, which calls signal_goal().
        if goal_via_locations && !goal_sent {
            if let Some(client) = conn.client() {
                if goal_locations.iter().all(|&g| client.is_local_location_checked(g)) {
                    signal_goal();
                }
            }
        }

        // 5b) Send CLIENT_GOAL once GOAL_REACHED is set (by 5a or the game tick's flag poll).
        if !goal_sent && GOAL_REACHED.load(Ordering::Relaxed) {
            if let Some(client) = conn.client_mut() {
                if client.set_status(ap::ClientStatus::Goal).is_ok() {
                    tracing::info!("AP: sent GOAL");
                    goal_sent = true;
                }
            }
        }

        // 6) Wave D: if the local player died this session, originate a DeathLink (rising-edge latched
        // on the game tick by deathlink::poll_outgoing_death). (DEATHLINK-WIRING.md §2d.)
        if deathlink::take_pending_outgoing() {
            if let Some(client) = conn.client_mut() {
                let opts = ap::DeathLinkOptions::new()
                    .cause("Slain in the Lands Between.".to_string())
                    .source(slot.clone());
                match client.death_link(opts) {
                    Ok(()) => tracing::info!("AP: sent DeathLink"),
                    Err(e) => tracing::warn!("AP: death_link send failed: {e}"),
                }
            } else {
                tracing::debug!("AP: DeathLink to send but client not ready; dropping");
            }
        }

        // 7) STEP 0 pre-scout proof: issue the scout on its first pump, poll/log on later ticks. Runs
        // after this tick's conn.update() drain (step 1) so a LocationInfo that just arrived is already
        // routed into the receiver, and where a conn.client_mut() borrow is free.
        if let Some(sp) = scout.as_mut() {
            if !sp.is_done() {
                if let Some(client) = conn.client_mut() {
                    sp.pump(client);
                }
            }
        }

        if conn.is_disconnected() {
            return;
        }
        std::thread::sleep(Duration::from_millis(50));
    }
}

/// Build an `i64 -> i64` map from a slot_data JSON object whose keys are stringified ints (the AP
/// convention for `apIdsToItemIds` / `itemCounts`). Tolerant: skips any entry that doesn't parse.
fn i64_map(v: Option<&serde_json::Value>) -> HashMap<i64, i64> {
    let mut m = HashMap::new();
    if let Some(serde_json::Value::Object(o)) = v {
        for (k, val) in o {
            if let (Ok(ki), Some(vi)) = (k.parse::<i64>(), val.as_i64()) {
                m.insert(ki, vi);
            }
        }
    }
    m
}

/// `{ "<i64>": <u32> }` slot_data object -> `i64 -> u32` map (the pure-runtime `locationFlags`:
/// AP location id -> vanilla acquisition flag). Tolerant: skips any entry that doesn't parse.
fn i64_to_u32_map(v: Option<&serde_json::Value>) -> HashMap<i64, u32> {
    let mut m = HashMap::new();
    if let Some(serde_json::Value::Object(o)) = v {
        for (k, val) in o {
            if let (Ok(ki), Some(vi)) = (k.parse::<i64>(), val.as_u64()) {
                m.insert(ki, vi as u32);
            }
        }
    }
    m
}

/// `[ <i32>, ... ]` slot_data array -> `HashSet<i32>` (the pure-runtime `checkItemIds`:
/// category-packed FullIDs that are the vanilla contents of a check). Tolerant: skips non-ints.
fn i32_set(v: Option<&serde_json::Value>) -> std::collections::HashSet<i32> {
    let mut s = std::collections::HashSet::new();
    if let Some(arr) = v.and_then(|x| x.as_array()) {
        for x in arr {
            if let Some(n) = x.as_i64() {
                s.insert(n as i32);
            }
        }
    }
    s
}

/// `{ "<i32>": [<u32>, ...] }` slot_data object -> `i32 -> Vec<u32>` map (the pure-runtime
/// `checkItemFlags`: check FullID -> guarding acquisition flags). Tolerant: skips non-numeric.
fn i32_to_u32vec_map(v: Option<&serde_json::Value>) -> HashMap<i32, Vec<u32>> {
    let mut m = HashMap::new();
    if let Some(serde_json::Value::Object(o)) = v {
        for (k, val) in o {
            if let (Ok(ki), Some(arr)) = (k.parse::<i32>(), val.as_array()) {
                m.insert(ki, arr.iter().filter_map(|x| x.as_u64().map(|n| n as u32)).collect());
            }
        }
    }
    m
}

/// Build the Phase-5 feature config from slot_data (`sd`) + apconfig (`apcfg`). Every field is
/// optional/tolerant so an older seed that omits a key leaves that feature inert. Mirrors the
/// slot_data parse spread across `set_data_package_handler` / `set_slot_connected_handler` and the
/// apconfig `location_flags` / `sweep_flags` load in `CCore::LoadConfigFile`.
fn build_slot_config(sd: &serde_json::Value, dlc: bool, apcfg: &ApConfig) -> features::SlotConfig {
    let mut c = features::SlotConfig {
        enable_dlc: dlc,
        ..Default::default()
    };

    c.region_graces = str_to_u32vec(sd.get("regionGraces"));
    c.grace_items = str_to_u32(sd.get("graceItems"));
    c.region_open_flags = str_to_u32(sd.get("regionOpenFlags"));
    c.lock_reveal_flags = str_to_u32vec(sd.get("lockRevealFlags"));
    c.lock_notify_items = str_to_i32(sd.get("lockNotifyItems"));
    c.natural_key_triggers = parse_natural_keys(sd.get("naturalKeyTriggers"));

    c.dlc_entry_warp_flag = sd.get("dlcEntryWarpFlag").and_then(|v| v.as_u64()).unwrap_or(0) as u32;
    c.dlc_start_area_id = sd.get("dlcStartAreaId").and_then(|v| v.as_i64()).unwrap_or(0) as i32;
    c.random_start_warp_flag = sd.get("randomStartWarpFlag").and_then(|v| v.as_u64()).unwrap_or(0) as u32;
    c.random_start_area_id = sd.get("randomStartAreaId").and_then(|v| v.as_i64()).unwrap_or(0) as i32;
    c.random_start_done_flag = sd.get("randomStartDoneFlag").and_then(|v| v.as_u64()).unwrap_or(0) as u32;

    c.area_lock_flags = sd
        .get("areaLockFlags")
        .and_then(|v| v.as_array())
        .map(|outer| {
            outer
                .iter()
                .filter_map(|row| row.as_array())
                .filter(|r| r.len() >= 3)
                .map(|r| {
                    [
                        r[0].as_i64().unwrap_or(0) as i32,
                        r[1].as_i64().unwrap_or(0) as i32,
                        r[2].as_i64().unwrap_or(0) as i32,
                    ]
                })
                .collect()
        })
        .unwrap_or_default();

    c.reveal_all_maps = sd.get("reveal_all_maps").and_then(|v| v.as_bool()).unwrap_or(false);

    // dungeonSweeps: { "<trigger location id>": [members...] } (slot_data).
    if let Some(serde_json::Value::Object(o)) = sd.get("dungeonSweeps") {
        for (k, v) in o {
            if let (Ok(ki), Some(arr)) = (k.parse::<i64>(), v.as_array()) {
                c.dungeon_sweeps
                    .insert(ki, arr.iter().filter_map(|x| x.as_i64()).collect());
            }
        }
    }

    // apconfig-side maps (keys are stringified ints in the JSON object).
    for (k, &flag) in &apcfg.location_flags {
        if let Ok(loc) = k.parse::<i64>() {
            c.location_flags.insert(loc, flag);
        }
    }
    for (k, locs) in &apcfg.sweep_flags {
        if let Ok(flag) = k.parse::<u32>() {
            c.sweep_flags.insert(flag, locs.clone());
        }
    }

    c
}

/// `{ "name": <u32> }` slot_data object -> name->flag map. Tolerant: skips non-numeric values.
fn str_to_u32(v: Option<&serde_json::Value>) -> HashMap<String, u32> {
    let mut m = HashMap::new();
    if let Some(serde_json::Value::Object(o)) = v {
        for (k, val) in o {
            if let Some(n) = val.as_u64() {
                m.insert(k.clone(), n as u32);
            }
        }
    }
    m
}

/// `{ "name": <i32> }` slot_data object -> name->FullID map (signed; FullIDs carry the category nibble).
fn str_to_i32(v: Option<&serde_json::Value>) -> HashMap<String, i32> {
    let mut m = HashMap::new();
    if let Some(serde_json::Value::Object(o)) = v {
        for (k, val) in o {
            if let Some(n) = val.as_i64() {
                m.insert(k.clone(), n as i32);
            }
        }
    }
    m
}

/// `{ "name": [<u32>, ...] }` slot_data object -> name->flags map.
fn str_to_u32vec(v: Option<&serde_json::Value>) -> HashMap<String, Vec<u32>> {
    let mut m = HashMap::new();
    if let Some(serde_json::Value::Object(o)) = v {
        for (k, val) in o {
            if let Some(arr) = val.as_array() {
                m.insert(k.clone(), arr.iter().filter_map(|x| x.as_u64().map(|n| n as u32)).collect());
            }
        }
    }
    m
}

/// `{ "LockName": { "anyOf": [ {"items":[..],"flags":[..]}, ... ] } }` -> region->clause disjunction.
fn parse_natural_keys(v: Option<&serde_json::Value>) -> HashMap<String, Vec<features::NkClause>> {
    let mut m = HashMap::new();
    if let Some(serde_json::Value::Object(o)) = v {
        for (region, body) in o {
            let mut clauses = Vec::new();
            if let Some(any_of) = body.get("anyOf").and_then(|x| x.as_array()) {
                for c in any_of {
                    let items = c
                        .get("items")
                        .and_then(|x| x.as_array())
                        .map(|a| a.iter().filter_map(|s| s.as_str().map(String::from)).collect())
                        .unwrap_or_default();
                    let flags = c
                        .get("flags")
                        .and_then(|x| x.as_array())
                        .map(|a| a.iter().filter_map(|s| s.as_u64().map(|n| n as u32)).collect())
                        .unwrap_or_default();
                    clauses.push(features::NkClause { items, flags });
                }
            }
            m.insert(region.clone(), clauses);
        }
    }
    m
}

/// Find apconfig.json: $ER_AP_CONFIG, then next to the game exe (`<Game>\apconfig.json`), then CWD.
/// Logs every path tried so it's obvious where to drop the file.
fn load_apconfig() -> Option<ApConfig> {
    let mut candidates: Vec<PathBuf> = Vec::new();
    if let Ok(p) = std::env::var("ER_AP_CONFIG") {
        candidates.push(PathBuf::from(p));
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            candidates.push(dir.join("apconfig.json")); // <Game>\apconfig.json (ME2 / next to exe)
            candidates.push(dir.join("mods").join("apconfig.json")); // <Game>\mods\apconfig.json (EML, next to the DLL)
        }
    }
    candidates.push(PathBuf::from("apconfig.json")); // CWD fallback

    for path in &candidates {
        match std::fs::read_to_string(path) {
            Ok(text) => match serde_json::from_str::<ApConfig>(&text) {
                Ok(c) => {
                    tracing::info!("AP: loaded config from {}", path.display());
                    return Some(c);
                }
                Err(e) => tracing::error!("AP: found {} but failed to parse it: {e}", path.display()),
            },
            Err(_) => tracing::debug!("AP: no config at {}", path.display()),
        }
    }
    tracing::error!(
        "AP: no usable apconfig.json (looked at: {}). Create one next to the game exe: \
         {{\"url\":\"host:port\",\"slot\":\"Name\"}}. Networking disabled.",
        candidates.iter().map(|p| p.display().to_string()).collect::<Vec<_>>().join(", ")
    );
    None
}

/// `archipelago/<seed>_<slot>.json` relative to CWD (mirrors CCore::InitSavePath). Filename parts are
/// sanitised so an exotic seed/slot can't escape the directory.
fn save_path_for(seed: &str, slot: &str) -> PathBuf {
    let _ = std::fs::create_dir_all("archipelago");
    let safe = |s: &str| -> String {
        s.chars()
            .map(|c| if c.is_ascii_alphanumeric() || c == '-' || c == '_' { c } else { '_' })
            .collect()
    };
    PathBuf::from("archipelago").join(format!("{}_{}.json", safe(seed), safe(slot)))
}

fn load_last_index(path: &PathBuf) -> i64 {
    match std::fs::read_to_string(path) {
        Ok(t) => serde_json::from_str::<serde_json::Value>(&t)
            .ok()
            .and_then(|v| v.get("last_received_index").and_then(|x| x.as_i64()))
            .unwrap_or(0),
        Err(_) => 0,
    }
}
