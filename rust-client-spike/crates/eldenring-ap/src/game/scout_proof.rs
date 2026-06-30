//! STEP 0 — the "pre-scout proof" for the shop-name-preview feature. ZERO reverse-engineering: it
//! proves the *data half* of shop previews end-to-end (ask AP what items sit at the seed's check
//! locations, get back real item names + owning player, log them) without touching the game at all.
//! If the log shows correct names, only the in-game UI hook (`MsgRepositoryImp::LookupEntry`, a
//! separate effort — see `er_logic::name_override`) remains. See PRE-SCOUT-PROOF.md.
//!
//! ── How the scout API works (verified against third_party/archipelago_rs) ────────────────────────
//! `Client::scout_locations(locations, CreateAsHint) -> oneshot::Receiver<Result<Vec<LocatedItem>,
//! Error>>` (client.rs:587). It is NOT synchronous and does NOT return the Vec directly: it sends a
//! `LocationScouts` packet and hands back a receiver. The server's `LocationInfo` reply arrives LATER
//! on a normal `conn.update()` poll — `Client::handle_message` hydrates each entry into a
//! `LocatedItem` and fulfils the oneshot. So the proof: (1) issues the scout once after slot_data is
//! parsed, (2) relies on net.rs's serve loop continuing to pump `conn.update()`, (3) polls the
//! receiver each tick until it yields a value, then logs.
//!
//! ── oneshot 0.2.1 try_recv (verified against the crate source) ──────────────────────────────────
//! `Receiver::try_recv(&mut self) -> Result<T, TryRecvError>` with
//! `TryRecvError::{ Empty (still pending), Disconnected (sender dropped / already taken) }`.
//! (NOT `Result<Option<T>, _>`.)
//!
//! ── Accessor chain (verified: data/located_item.rs, data/item.rs, data/player.rs) ────────────────
//!   LocatedItem::location() -> Location ; .id() -> i64
//!   LocatedItem::item()     -> Item     ; .name() -> ustr::Ustr (Display / AsRef<str>)
//!   LocatedItem::receiver() -> &Player  ; .alias() -> &str  (the owning player)

use archipelago_rs as ap;
use ap::CreateAsHint; // re-exported at crate root via `pub use protocol::*`.
use oneshot::TryRecvError;
use std::collections::HashMap;
use std::sync::Mutex;

/// One scouted AP item, cached by AP location id, consumed by the FMG name/caption inject
/// (`fmg_inject::resolve_synth_injects`): a synthetic goods row -> its vagrant-recombined location id
/// -> this -> real GoodsName + GoodsCaption (game / owner / class).
#[derive(Clone)]
pub struct ScoutedItem {
    pub name: String,
    pub game: String,
    pub owner: String,
    pub slot: u32,
    pub kind: er_logic::name_override::ItemKind,
    /// True if this location's item goes to a DIFFERENT player (foreign) — i.e. checking it SENDS the
    /// item out. Computed from sender (always us, since the location is in our world) vs receiver slot.
    pub foreign: bool,
    /// For an OWN-WORLD reward whose category `shop_sell` can natively sell (weapon / protector /
    /// accessory / goods), the reward's ER FullID — so the slot's ShopLineupParam.equipId can be
    /// rewritten to sell the real item (correct icon + name + lore, any type). `None` for foreign items
    /// (no ER counterpart) and gem/custom rewards (left to the shop_preview/shop_icon flower override).
    pub er_sell_id: Option<i64>,
}

/// AP location id -> scouted item. `None` until the first LocationScouts reply lands; `Some` (even if
/// empty) once it has, so fmg_inject can tell "not scouted yet" from "scouted, no hit".
static CACHE: Mutex<Option<HashMap<i64, ScoutedItem>>> = Mutex::new(None);

/// `apIdsToItemIds` (AP item id -> ER FullID), set by net.rs at slot_data parse. Lets `store` resolve
/// an own-world reward's real ER good id for the shop icon/description borrow.
static AP_ITEM_TO_FULLID: Mutex<Option<HashMap<i64, i64>>> = Mutex::new(None);

/// Called by net.rs with slot_data `apIdsToItemIds` so own-world goods rewards can be resolved to their
/// real ER good id. Safe to call before the scout reply (store reads it when the reply lands).
pub fn configure_item_map(map: HashMap<i64, i64>) {
    *AP_ITEM_TO_FULLID.lock().unwrap() = Some(map);
}

/// True once the scout reply has populated the cache. Lets fmg_inject wait for real names instead of
/// latching AP#<id> placeholders.
pub fn cache_ready() -> bool {
    CACHE.lock().unwrap().is_some()
}

/// Look up a scouted item by AP location id.
pub fn lookup(location_id: i64) -> Option<ScoutedItem> {
    CACHE.lock().unwrap().as_ref()?.get(&location_id).cloned()
}

fn store(items: &[ap::LocatedItem]) {
    use er_logic::name_override::ItemKind;
    let item_map = AP_ITEM_TO_FULLID.lock().unwrap();
    let mut map = HashMap::with_capacity(items.len());
    for li in items {
        let foreign = li.sender().slot() != li.receiver().slot();
        // OWN-WORLD reward -> its ER FullID (apIdsToItemIds), but only for the categories shop_sell can
        // natively sell as a shop ware (weapon/protector/accessory/goods). Foreign -> None; gem/custom ->
        // None (those fall back to the flower display-override).
        let er_sell_id = if foreign {
            None
        } else {
            item_map
                .as_ref()
                .and_then(|m| m.get(&li.item().id()))
                .copied()
                .filter(|&fid| {
                    let q = fid as u32;
                    !er_codec::is_synthetic_goods(q)
                        && matches!(
                            er_codec::item_category_of(q),
                            er_codec::CATEGORY_WEAPON
                                | er_codec::CATEGORY_PROTECTOR
                                | er_codec::CATEGORY_ACCESSORY
                                | er_codec::CATEGORY_GOODS
                        )
                })
        };
        map.insert(
            li.location().id(),
            ScoutedItem {
                name: li.item().name().to_string(),
                game: li.receiver().game().to_string(),
                owner: li.receiver().alias().to_string(),
                slot: li.receiver().slot(),
                kind: ItemKind::from_flags(li.is_progression(), li.is_useful(), li.is_trap()),
                foreign,
                er_sell_id,
            },
        );
    }
    *CACHE.lock().unwrap() = Some(map);
}

/// State for the in-flight scout. Lives across serve-loop iterations because the result arrives on a
/// later poll, not inline. Construct after slot_data is parsed; drive `pump()` every loop tick.
pub struct ScoutProof {
    /// `Some` until the scout has been issued (we only scout once for the proof).
    pending_request: Option<Vec<i64>>,
    /// The receiver for the scout result; `None` before issue and after the result is logged.
    rx: Option<oneshot::Receiver<Result<Vec<ap::LocatedItem>, ap::Error>>>,
    /// Latches true once we've logged (success or failure) so we don't re-scout on reconnect-replay.
    done: bool,
}

impl ScoutProof {
    /// `locations` = the check locations to scout. For the PROOF this is the keys of slot_data
    /// `locationFlags` (already parsed in net.rs via `i64_to_u32_map`; pass `map.keys().copied()
    /// .collect()`). The REAL feature scouts only the shop-slot locations once the apworld emits a
    /// shop-slot -> location map; the proof just needs a known-good set.
    pub fn new(locations: Vec<i64>) -> Self {
        Self { pending_request: Some(locations), rx: None, done: false }
    }

    /// Already finished (logged once)? Lets the caller skip on reconnect.
    pub fn is_done(&self) -> bool {
        self.done
    }

    /// Call once per serve-loop iteration, where a live `&mut Client` is free (`conn.client_mut()`).
    /// First call issues the `LocationScouts`; later calls poll the receiver and, when the reply
    /// lands, log `location <id> -> <display_name>` for each entry.
    pub fn pump(&mut self, client: &mut ap::Client<serde_json::Value>) {
        if self.done {
            return;
        }

        // 1) Issue the scout exactly once. CreateAsHint::No => no player-visible hints, no hint-point
        //    spend; we only want the item info echoed back to the client.
        if let Some(locations) = self.pending_request.take() {
            if locations.is_empty() {
                tracing::info!("AP scout-proof: no locations to scout (locationFlags empty); skipping");
                self.done = true;
                return;
            }
            tracing::info!("AP scout-proof: scouting {} location(s) (CreateAsHint::No)", locations.len());
            self.rx = Some(client.scout_locations(locations, CreateAsHint::No));
            return; // the reply can't be here yet; poll on the next tick.
        }

        // 2) Poll the receiver for the server's LocationInfo reply (routed by Client::handle_message).
        let Some(rx) = self.rx.as_mut() else {
            return;
        };
        match rx.try_recv() {
            Ok(result) => {
                self.rx = None;
                self.done = true;
                match result {
                    Ok(items) => {
                        store(&items); // populate the cache fmg_inject reads (names + captions)
                        tracing::info!("AP scout-proof: received info for {} location(s) ===", items.len());
                        for li in &items {
                            let loc_id = li.location().id();
                            let item_name = li.item().name(); // ustr::Ustr (Display / AsRef<str>)
                            let owner = li.receiver().alias(); // owning player's alias
                            let line = er_logic::name_override::display_name(
                                item_name.as_str(),
                                Some(owner),
                            );
                            tracing::info!("AP scout-proof: location {loc_id} -> {line}");
                        }
                        tracing::info!("AP scout-proof: === data path PROVEN (names above) ===");
                    }
                    Err(e) => {
                        tracing::warn!("AP scout-proof: server returned an error for the scout: {e}");
                    }
                }
            }
            Err(TryRecvError::Empty) => { /* still pending; try again next tick */ }
            Err(TryRecvError::Disconnected) => {
                // Sender dropped: the connection went away before the reply arrived. Latch done so we
                // don't spin; the reconnect path constructs a fresh ScoutProof.
                self.rx = None;
                self.done = true;
                tracing::warn!("AP scout-proof: scout receiver dropped before a reply (connection lost?)");
            }
        }
    }
}
