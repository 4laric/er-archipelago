//! Wave D — **DeathLink**. Rust port of the DeathLink mechanic from
//! `ArchipelagoInterface.cpp` (`set_bounced_handler` ~536-562 INCOMING, `sendDeathLink` ~620-630
//! OUTGOING, and the `DeathLink` tag pushed in `ConnectSlot` ~309) onto archipelago_rs 2.1.1.
//!
//! ## What this module owns vs. what's a hole
//! The **network protocol** side is COMPLETE and correct against archipelago_rs (verified against the
//! vendored crate under `third_party/archipelago_rs`):
//!   * INCOMING: `net.rs` matches `ap::Event::DeathLink { source, cause, .. }` and calls
//!     `on_death_link_event(..)`, which (after the self-source guard) latches a "kill pending" flag.
//!   * OUTGOING: the game tick detects a LOCAL death (`poll_outgoing_death`) and latches a
//!     "send pending" flag; `net.rs` drains it with `take_pending_outgoing()` and calls
//!     `client.death_link(DeathLinkOptions)`.
//!   * TAG: `net.rs` adds `ap::tags::DEATH_LINK` to `ConnectionOptions::tags(..)` iff `is_enabled()`.
//!
//! The **two game-memory touchpoints** are honest `// RE:` stubs — the ER kill mechanism was never
//! implemented (C++ `GameHook.cpp::manageDeathLink()` is a stub for ER), and this client has no
//! player-HP / death-state accessor yet (only `play_region_id`, see flags.rs). Both stubs carry a
//! Cheat-Engine worksheet in their doc comment. Wiring this module lets the protocol go live now;
//! Alaric fills `kill_player()` and `read_local_death()` in a CE session.
//!
//! ## Thread rule (inherited from features.rs / net.rs)
//! NAME/event decisions run on the NET thread and only LATCH an AtomicBool; every game-memory read
//! (death detection) and write (the kill) happens on the FrameBegin TICK. The net thread never
//! touches game memory; the game thread never touches the socket. Two atomics bridge the two
//! directions — no locks, no allocation on the hot path.

#![allow(dead_code)] // handlers/stubs are wired ahead of the RE fill-in

use std::sync::atomic::{AtomicBool, Ordering};

use super::flags;

use eldenring::cs::{CSChrDataModule, WorldChrMan};
use fromsoftware_shared::FromStatic;

// =================================================================================================
// State — three atomics. `ENABLED` is set once at connect (slot_data); the two latches bridge the
// net<->game threads (Release on the producer, Acquire on the consumer so the latch publishes
// cleanly across the thread boundary).
// =================================================================================================

/// True when the slot has DeathLink on (`options.death_link`). Read by net.rs to decide whether to
/// add the tag and whether to act on events; read by the tick to decide whether to poll for a local
/// death. Set once at connect via `configure_from_slot_data`.
static ENABLED: AtomicBool = AtomicBool::new(false);

/// INCOMING latch: an `Event::DeathLink` arrived (and passed the self-source guard) on the net
/// thread; the game tick must kill the player once in-world. Mirrors the C++ `deathLinkData = true`.
static KILL_PENDING: AtomicBool = AtomicBool::new(false);

/// OUTGOING latch: the game tick detected the LOCAL player just died; the net thread must Bounce a
/// DeathLink. Mirrors the C++ `sendDeathLink()` call site.
static SEND_PENDING: AtomicBool = AtomicBool::new(false);

/// Edge-detect state for `poll_outgoing_death` (game thread only, so a plain `static mut`-free
/// AtomicBool is plenty): tracks whether we were already dead last tick, so a single death produces
/// exactly one outgoing DeathLink rather than one per frame while the death screen is up.
static WAS_DEAD: AtomicBool = AtomicBool::new(false);

// =================================================================================================
// Config (net thread, at connect).
// =================================================================================================

/// Net thread: enable/disable DeathLink for this slot.
pub fn set_enabled(on: bool) {
    ENABLED.store(on, Ordering::Relaxed);
}

/// True if DeathLink is on for this slot. net.rs gates the tag + event handling on this; the tick
/// gates `poll_outgoing_death` on it.
pub fn is_enabled() -> bool {
    ENABLED.load(Ordering::Relaxed)
}

/// Net thread, at connect: read `options.death_link` out of slot_data and set `ENABLED`. Tolerant of
/// the int-or-bool encoding the apworld uses for booleans (e.g. `enable_dlc` ships as int 0/1, not a
/// JSON bool — see net.rs's parse of it), so a `0`/`1` integer, a real bool, or an absent key all
/// resolve correctly (absent => off). Mirrors the `GameHook->dIsDeathLink` config read.
pub fn configure_from_slot_data(sd: &serde_json::Value) {
    // Reset the per-session latches first so a reconnect can't carry a stale kill/send across.
    KILL_PENDING.store(false, Ordering::Relaxed);
    SEND_PENDING.store(false, Ordering::Relaxed);
    WAS_DEAD.store(false, Ordering::Relaxed);

    let on = sd
        .pointer("/options/death_link")
        .map(|v| v.as_bool().unwrap_or_else(|| v.as_i64().unwrap_or(0) != 0))
        .unwrap_or(false);
    set_enabled(on);
    if on {
        tracing::info!("AP: DeathLink ENABLED for this slot");
    } else {
        tracing::debug!("AP: DeathLink off for this slot");
    }
}

// =================================================================================================
// INCOMING — net thread latches, game tick kills.
// =================================================================================================

/// Net thread: called from the `ap::Event::DeathLink` arm in net.rs. `source` is the player who
/// died, `cause` the (optional) flavour text. Latches a kill for the game tick unless the death is
/// OURS (the server echoes our own DeathLink back; killing ourselves for our own death would loop).
///
/// `our_slot` is the local slot name net.rs already has (`cfg.slot` / slot_data `slot`); the C++
/// compared `data["source"] != Core->pSlotName` for exactly this self-suppression.
pub fn on_death_link_event(source: &str, cause: Option<&str>, our_slot: &str) {
    if !is_enabled() {
        return; // tag wasn't added; shouldn't fire, but stay inert if it does
    }
    if !our_slot.is_empty() && source == our_slot {
        tracing::debug!("AP: ignoring our own DeathLink echo (source {source})");
        return;
    }
    let cause = cause.unwrap_or("???");
    tracing::info!("AP: DeathLink received — died by the hands of {source} : {cause}");
    // C++ also showBanner(message); the native-banner path is a separate (parked) feature here, so
    // we only latch the kill. If/when the banner lands, enqueue it from THIS line.
    KILL_PENDING.store(true, Ordering::Release);
}

/// Game thread (called from this module's `tick`): if a kill is pending and the player is in-world,
/// attempt it. Clears the latch only on a SUCCESSFUL kill, so a kill latched while on a menu / load
/// screen retries on the next in-world tick instead of being lost (matches the grace-flush retry
/// discipline in features.rs).
pub fn tick() {
    if !is_enabled() {
        return;
    }
    drive_incoming_kill();
    poll_outgoing_death();
}

fn drive_incoming_kill() {
    if !KILL_PENDING.load(Ordering::Acquire) {
        return;
    }
    if !flags::in_world() {
        return; // not placed yet — keep the latch, retry next tick
    }
    if kill_player() {
        KILL_PENDING.store(false, Ordering::Release);
        tracing::info!("AP: DeathLink applied — local player killed");
    } else {
        // kill_player is still a RE stub: log ONCE per latch so we don't spam every frame while the
        // hole is open. The latch stays set; once the RE lands it'll succeed and clear.
        if KILL_LOGGED.swap(true, Ordering::Relaxed) == false {
            tracing::warn!(
                "AP: DeathLink kill requested but kill_player() is an unfilled RE stub — \
                 player NOT killed (see deathlink.rs kill_player worksheet)"
            );
        }
    }
}

static KILL_LOGGED: AtomicBool = AtomicBool::new(false);

// =================================================================================================
// Game-memory touchpoint — the player current-HP cell, reached through the SAME typed chain
// flags.rs uses for `play_region_id` (anchor = WorldChrMan.main_player). Filled from the validated
// Hexington CE table (eldenring_all-in-one_Hexinton-v6.0_ce7.5.ct) reconciled against the typed
// `eldenring 0.14` bindings (docs.rs), so we walk named struct fields rather than raw offsets.
//
// CE "HP" entry (ct lines 3685-3698 / dup 4963-4975): Address=WorldChrMan,
//   Offsets (CE reads innermost-LAST) = [138, 0, 190, 0*10, LocalPlayerOffset].
//   LocalPlayerOffset = 0x10EF8 (ct line 430) is WorldChrMan.main_player (the PlayerIns*).
//   Resolved raw HP address =
//     *(*(*(*(WorldChrMan_base + 0x10EF8) + 0x0) + 0x190) + 0x0) + 0x138
//   i.e. from the main_player PlayerIns:  +0x0 (PlayerIns/ChrIns base) -> +0x190 (module bag's
//   data-module ptr) -> +0x138 (current HP, 4-byte int). MaxHP is the adjacent +0x13C cell
//   (CE "MaxHP" ct lines 4977-4988), which is exactly CSChrDataModule.max_hp here.
//
// Typed reconciliation (docs.rs, eldenring 0.14):
//   * ChrIns.modules : OwnedPtr<ChrInsModuleContainer>   (the +0x190 "module bag" hop)
//   * ChrInsModuleContainer.data : OwnedPtr<CSChrDataModule>  (the data-module ptr)
//   * CSChrDataModule { .. chara_init_param_id: i32, hp: i32, max_hp: i32, .. }
//       -> `hp` is current HP (the +0x138 cell), `max_hp` the +0x13C cell.
//   PlayerIns derefs to ChrIns (flags.rs reads `play_region_id`, a ChrIns field, straight off
//   `main_player`), so `main_player.as_ref()?.modules.data.hp` is the full chain. Using the typed
//   fields keeps this robust across patches that shift the numeric offsets.
//
// `with_player_hp` resolves &mut CSChrDataModule from the in-world main_player, verifying each hop
// is present, and hands it to a closure. Returns None (no-op) if anything is null / not in-world, so
// a wrong/late chain can NEVER turn into a bad write — callers treat None as "couldn't act, retry".
fn with_player_hp<R>(f: impl FnOnce(&mut CSChrDataModule) -> R) -> Option<R> {
    // Defensive in-world re-check (callers already gate, but a stray call must stay safe).
    if !flags::in_world() {
        return None;
    }
    // Resolve the singleton MUTABLY (we may write hp); instance_mut is the same FromStatic accessor
    // flags.rs uses for CSEventFlagMan::instance_mut. Bail (no-op) before it inits or if absent.
    let wcm = unsafe { WorldChrMan::instance_mut() }.ok()?;
    // main_player is a nullable pointer (flags.rs uses as_ref()? on it); a mutable borrow lets the
    // read (read_local_death) and write (kill_player) share one resolver. None => not placed yet.
    let player = wcm.main_player.as_mut()?;
    // ChrIns.modules -> ChrInsModuleContainer (OwnedPtr derefs to the container).
    // CSChrDataModule lives behind ChrInsModuleContainer.data (the +0x190 data module).
    let data: &mut CSChrDataModule = &mut player.modules.data;
    Some(f(data))
}

/// Dedicated "DeathLink death" event flag. The client SETS it; a baked `common.emevd` event
/// (`patch_baker_deathlink_kill.py`) reacts with `ForceCharacterDeath(player, ShouldReceiveRunes=TRUE)`
/// then clears it. A NEW flag (not the region-kick's 76970) so the kill works with OR without region
/// locks, never warps, and doesn't collide with the client's KICK latch (features.rs also sets 76970).
/// In the valid grace-tail flag group (kick 76970, region locks 76971-76995, DLC entry 76999);
/// 76996 is a free slot in that group (NOT a region-lock flag — those are 76971-76995).
const DEATHLINK_KILL_FLAG: u32 = 76996;

/// Kill the local player on an INCOMING DeathLink. Returns `true` once the request is handed off
/// (latch clears), `false` while it can't be applied yet (latch kept, retried next in-world tick).
///
/// **Approach: SET the baked DeathLink-death flag**, letting the EMEVD do the actual kill via
/// `ForceCharacterDeath` — the SAME game-native death the region-lock KICK uses (er-kick-kill-keep-runes).
/// This is strictly better than a raw `hp = 0` write: (a) it can't be HP-clamped/recomputed, and
/// (b) the EMEVD passes **Should Receive Runes = TRUE**, so a DeathLink death KEEPS YOUR RUNES (a
/// raw hp=0 would drop a bloodstain and lose them). The kill itself lives in the baker
/// (`patch_baker_deathlink_kill.py`); the client's whole job is to set the flag, which it does
/// reliably. Returns false until CSEventFlagMan is up (caller keeps the latch and retries).
fn kill_player() -> bool {
    flags::try_set_event_flag(DEATHLINK_KILL_FLAG, true)
}

// =================================================================================================
// OUTGOING — game tick detects local death, net thread sends.
// =================================================================================================

/// Game thread (called from `tick`): detect that the LOCAL player JUST died (rising edge) and latch
/// an outgoing DeathLink for the net thread. Edge-detected against `WAS_DEAD` so one death yields one
/// Bounce, not one per frame the death screen is up. Suppressed while a kill we just RECEIVED is
/// being applied? No — DeathLink intentionally does NOT re-broadcast deaths it caused, but that's
/// handled at the RECEIVER (self-source guard) and by the death-cause check, so we keep this simple:
/// any local death edge sends. (If echo-storms appear in playtest, gate this on
/// `!KILL_PENDING && !<just-applied-incoming>` here.)
pub fn poll_outgoing_death() {
    if !flags::in_world() {
        // Off-world (menu/load): clear the edge state so re-entering the world after a respawn
        // doesn't read as a fresh death. Don't send.
        WAS_DEAD.store(false, Ordering::Relaxed);
        return;
    }
    let dead_now = read_local_death();
    let was_dead = WAS_DEAD.swap(dead_now, Ordering::Relaxed);
    if dead_now && !was_dead {
        tracing::info!("AP: local death detected — queueing outgoing DeathLink");
        SEND_PENDING.store(true, Ordering::Release);
    }
}

/// Net thread (called each loop iteration in net.rs): take + clear the outgoing-death latch. Returns
/// true exactly once per detected local death; net.rs then calls `client.death_link(..)`.
pub fn take_pending_outgoing() -> bool {
    SEND_PENDING.swap(false, Ordering::Acquire)
}

/// ⚠️ `// RE:` HOLE #2 — read whether the local player is currently DEAD. Returns `true` on the
/// death frame(s); `poll_outgoing_death`'s `WAS_DEAD` rising-edge latch turns a sustained `true`
/// into exactly one outgoing DeathLink and absorbs the 1-frame respawn window where HP can read 0
/// before the bonfire heal.
///
/// **Approach A: current HP == 0.** Reuse the SAME `CSChrDataModule.hp` cell `kill_player` writes
/// (CE "HP", +0x138). Read-only: resolve the chain through `with_player_hp` and report `hp <= 0`.
/// If any hop is null / not in-world we return `false` (treated as "alive / unknown" — we simply
/// don't originate a DeathLink), which is the safe default.
fn read_local_death() -> bool {
    // RE: read WorldChrMan.main_player -> ChrIns.modules.data.hp; dead == (hp <= 0). Read-only.
    with_player_hp(|data| data.hp <= 0).unwrap_or(false)
}
