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
