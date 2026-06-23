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

use super::{flags, grant};

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

    // slot_data read as serde_json::Value (the default S), so no field-type assumption can fail the
    // connection. &str satisfies Into<String>/Into<Ustr> without relying on &String coercions.
    let mut conn: ap::Connection<serde_json::Value> =
        ap::Connection::new(cfg.url.as_str(), slot.as_str(), Some("EldenRing"), opts);

    let mut configured = false;
    let mut pushed_through: i64 = 0; // highest received index already pushed to the grant queue
    let mut goal_sent = false;
    let mut item_map: HashMap<i64, i64> = HashMap::new(); // AP item id -> ER FullID
    let mut item_counts: HashMap<i64, i64> = HashMap::new();
    let mut goal_locations: Vec<i64> = Vec::new();
    let mut goal_via_locations = false;

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

                tracing::info!(
                    "AP: slot_data parsed ({} item-map entries); resuming at received index {}",
                    item_map.len(),
                    start_index
                );
                configured = true;
            }
        }

        // 3) Push newly-received items onto the grant queue.
        if configured {
            if let Some(client) = conn.client() {
                for ri in client.received_items() {
                    let idx = ri.index() as i64;
                    if idx < pushed_through {
                        continue;
                    }
                    let ap_item_id = ri.item().id();
                    match item_map.get(&ap_item_id) {
                        Some(&full_id) => {
                            let qty = item_counts.get(&ap_item_id).copied().unwrap_or(1).max(1);
                            grant::enqueue(grant::GrantMsg {
                                full_id: full_id as i32,
                                qty: qty as i32,
                                ap_index: idx,
                                name: ri.item().name().to_string(),
                            });
                        }
                        None => tracing::warn!(
                            "AP: received item id {} not in apIdsToItemIds; skipping (check seed options)",
                            ap_item_id
                        ),
                    }
                    if idx + 1 > pushed_through {
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
