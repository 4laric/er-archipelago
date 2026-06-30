//! shop_sell.rs — runtime "mini-baker" for OWN-WORLD shop slots: rewrite each slot's
//! `ShopLineupParam.equipId`/`equipType` to its actual AP reward so the slot NATIVELY sells (and thus
//! displays) the real item — correct icon + name + description for ANY supported type (weapon, armor,
//! talisman, goods), with NO global-FMG collision (each row edited independently). Foreign items have no
//! ER counterpart, and gem/custom rewards aren't in `er_codec`'s categories, so both stay on the
//! `shop_preview`/`shop_icon` flower override.
//!
//! Field encoding (confirmed against the vanilla ShopLineupParam dump): `equipId` is the RAW item id
//! (no category nibble) and `equipType` selects the param table — 0 Weapon, 1 Protector, 2 Accessory,
//! 3 Goods (4 Gem, 5 CustomWeapon, not handled here). So equipId = `row_id_of(FullID)`, equipType =
//! FullID category.
//!
//! Because the slot now hands the player the real reward R on purchase, R is registered for suppression
//! gated on the slot's stock flag (`should_suppress_sold`, consulted by detour.rs): the bag-add at buy
//! is nulled exactly like the vanilla ware was, so the AP grant delivers the single copy. Same flag +
//! timing the vanilla suppressor already uses for the original ware. Runs once in-world after
//! shop_flags (stock flags final) + scout-ready.

#![allow(dead_code)]

use eldenring::cs::{ShopLineupParam, SoloParamRepository};
use fromsoftware_shared::FromStatic;
use std::collections::HashMap;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;

/// slot_data `locationFlags` (AP location id -> guarding event flag). Inverted at run to map a row's
/// `eventFlag_forStock` back to its AP location (-> scout reward). Set by net.rs.
static CONFIGURED: Mutex<Option<HashMap<i64, u32>>> = Mutex::new(None);
static DONE: AtomicBool = AtomicBool::new(false);

/// FullID of a reward we rewrote a slot to SELL -> the slot's stock flag. The detour suppresses the
/// bag-add of these while the flag is unset, so the buy doesn't double with the AP grant.
static SOLD_SUPPRESS: Mutex<Option<HashMap<i32, u32>>> = Mutex::new(None);

pub fn configure(location_flags: HashMap<i64, u32>) {
    tracing::info!("shop-sell: configured {} location flag(s)", location_flags.len());
    *CONFIGURED.lock().unwrap() = Some(location_flags);
}

/// Detour hook: suppress the bag-add of `full_id` if it's a reward a rewritten slot now sells AND the
/// slot's stock flag is still unset (check not yet completed). False until `run` populates the map.
pub fn should_suppress_sold(full_id: i32, get_flag: &dyn Fn(u32) -> bool) -> bool {
    let g = SOLD_SUPPRESS.lock().unwrap();
    match g.as_ref().and_then(|m| m.get(&full_id)) {
        Some(&flag) => !get_flag(flag),
        None => false,
    }
}

/// FullID category -> ShopLineupParam `equipType`. `None` for gem/custom (not natively sellable here).
fn equip_type_for(fid: i64) -> Option<u8> {
    match er_codec::item_category_of(fid as u32) {
        er_codec::CATEGORY_WEAPON => Some(0),
        er_codec::CATEGORY_PROTECTOR => Some(1),
        er_codec::CATEGORY_ACCESSORY => Some(2),
        er_codec::CATEGORY_GOODS => Some(3),
        _ => None,
    }
}

/// Run once in-world + scout-ready (after shop_flags): rewrite each own-world check row to sell its
/// reward natively. Returns false (retry) until slot_data + the scout cache + the param repo are up.
pub fn run() -> bool {
    if DONE.load(Ordering::Relaxed) {
        return true;
    }
    let loc_flags = {
        let g = CONFIGURED.lock().unwrap();
        match g.as_ref() {
            Some(m) => m.clone(),
            None => return false, // wait for slot_data parse (net.rs)
        }
    };
    if !super::scout_proof::cache_ready() {
        return false; // need the rewards
    }
    // invert: stock flag -> AP location
    let mut flag_to_loc: HashMap<u32, i64> = HashMap::with_capacity(loc_flags.len());
    for (&loc, &flag) in loc_flags.iter() {
        if flag != 0 {
            flag_to_loc.insert(flag, loc);
        }
    }
    // SAFETY: FD4 singleton; game thread, in-world (caller gates). rows/get_mut on the live RW table.
    let repo = match unsafe { SoloParamRepository::instance_mut() } {
        Ok(r) => r,
        Err(_) => return false, // repo not up yet — retry next tick
    };

    // Scan immutably -> plan the rewrites, then apply (avoids holding a row borrow across get_mut).
    let mut plan: Vec<(u32, i32, u8)> = Vec::new(); // (row id, new equipId, equipType)
    let mut sold: HashMap<i32, u32> = HashMap::new(); // reward FullID -> stock flag
    for (id, row) in repo.rows::<ShopLineupParam>() {
        let f = row.event_flag_for_stock();
        if f == 0 {
            continue;
        }
        let Some(&loc) = flag_to_loc.get(&f) else { continue };
        let Some(s) = super::scout_proof::lookup(loc) else { continue };
        let Some(fid) = s.er_sell_id else { continue }; // own-world sellable category only
        let Some(etype) = equip_type_for(fid) else { continue };
        let new_eid = er_codec::row_id_of(fid as u32) as i32;
        if row.equip_id() != new_eid {
            plan.push((id, new_eid, etype));
        }
        sold.insert(fid as i32, f); // suppress the sold ware whether or not we had to rewrite
    }
    let n = plan.len();
    for (id, eid, etype) in &plan {
        if let Some(row) = repo.get_mut::<ShopLineupParam>(*id) {
            row.set_equip_id(*eid);
            row.set_equip_type(*etype);
        }
    }
    let sold_count = sold.len();
    *SOLD_SUPPRESS.lock().unwrap() = Some(sold);
    tracing::info!(
        "shop-sell: rewrote {n} own-world slot(s) to natively sell their reward ({sold_count} suppress-registered)"
    );
    DONE.store(true, Ordering::Relaxed);
    true
}
