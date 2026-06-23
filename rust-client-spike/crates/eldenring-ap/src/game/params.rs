//! DECODE layer — resolve a synthetic placeholder's `EquipParamGoods` row and turn it into the
//! pure [`er_codec::GoodsRowFields`].
//!
//! This is the single biggest "delete the binding layer" win. The C++ client hand-walked
//! `repo -> +idx*0x48+0x88 -> +0x80 -> +0x80 -> rowCount @ +0x0A -> 24-byte index entries -> row`
//! (er_hooks.h / er_gamehook.h) and then read raw byte offsets (er_goods_row.h). All of that is
//! replaced by the `eldenring` crate's typed `EQUIP_PARAM_GOODS_ST` + the `ParamDef` "safe param
//! lookup" trait. We read named fields off a typed struct; the row stride / offsets / blob walk are
//! the crate's problem (and patch-tracked upstream).
//!
//! ⚠️ COMPILE-TARGET SKETCH (not yet built). Lookup symbols RESOLVED against eldenring 0.14
//! — see the spike root's VERIFY-RESOLUTION.md. This is the Phase-1 spike payoff.

use er_codec::GoodsRowFields;

// RESOLVED (eldenring 0.14.0; see the spike root's VERIFY-RESOLUTION.md): the row STRUCT is
// `eldenring::param::EQUIP_PARAM_GOODS_ST`, but the turbofish marker for a typed lookup is the
// zero-sized `eldenring::cs::EquipParamGoods` (impl SoloParam, INDEX 3, StructType =
// EQUIP_PARAM_GOODS_ST). `ParamDef` is NOT a lookup API — it only carries { NAME, INDEX }. Rows
// come off the `SoloParamRepository` FD4 singleton via `get` / `rows`.
use eldenring::cs::{EquipParamGoods, SoloParamRepository};
use eldenring::param::EQUIP_PARAM_GOODS_ST;
use fromsoftware_shared::FromStatic;

/// Phase-1 spike: confirm the crate reaches the goods param, and split the count by vanilla vs
/// synthetic — our injected AP placeholders ARE EquipParamGoods rows with id > SYNTHETIC_GOODS_MIN_ID
/// (Decision D), so this confirms the ~3795-vs-3571 delta is our own rows. Iterates the table ONCE.
///
/// Returns `true` once it has logged a real count (repo reachable), `false` if the param repo isn't
/// up yet so the caller can retry on a later tick. MUST be called in-world (from tick()), NOT at
/// PROCESS_ATTACH: the SoloParamRepository global is uninitialized during boot, so touching it that
/// early faults and (with panic=abort) crashes the game.
pub fn spike_log_goods_rowcount() -> bool {
    // SAFETY: FD4 singleton accessor (FromStatic). Returns Err until SoloParamRepository is built.
    // Caller gates on in-world so the tables are populated. Breadcrumbs localize any residual fault.
    super::breadcrumb("  param: before SoloParamRepository::instance()");
    let repo = match unsafe { SoloParamRepository::instance() } {
        Ok(r) => r,
        Err(_) => return false,
    };
    super::breadcrumb("  param: instance() Ok; before rows() iterate");

    let mut total = 0usize;
    let mut synthetic = 0usize;
    let mut first_id = None;
    for (id, _row) in repo.rows::<EquipParamGoods>() {
        if first_id.is_none() {
            first_id = Some(id);
        }
        total += 1;
        // is_synthetic_goods wants a full gib id (category | row); these are goods rows already.
        if er_codec::is_synthetic_goods(er_codec::CATEGORY_GOODS | id) {
            synthetic += 1;
        }
    }
    super::breadcrumb("  param: rows() iterate Ok");

    tracing::info!(
        "EquipParamGoods rowCount = {total} (vanilla {} + synthetic {synthetic} AP placeholders, id>{}), firstRowId = {:?}",
        total - synthetic,
        er_codec::SYNTHETIC_GOODS_MIN_ID,
        first_id
    );
    true
}

/// Look up a goods row by its (category-stripped) row id and project the carrier fields into the
/// pure decode struct. `None` if the param repo isn't ready or the id is absent.
///
/// The five fields are the locked decode contract (er_item_decode.h): the two vagrant halves carry
/// the AP location id, `basicPrice`/`sellValue` the local replacement, `disableUseAtOutOfColiseum`
/// bit the foreign-remove flag.
pub fn goods_row_fields(row_id: i32) -> Option<GoodsRowFields> {
    // SAFETY: FD4 singleton; on the game thread. `get::<EquipParamGoods>(id: u32)` returns
    // `Option<&EQUIP_PARAM_GOODS_ST>` (None if the id is absent) — the typed lookup that replaces
    // the entire manual ParamBase walk.
    let repo = unsafe { SoloParamRepository::instance() }.ok()?;
    let row: &EQUIP_PARAM_GOODS_ST = repo.get::<EquipParamGoods>(row_id as u32)?;
    Some(GoodsRowFields {
        // RESOLVED: snake_case getter METHODS on EQUIP_PARAM_GOODS_ST (not public fields); the
        // disableUseAtOutOfColiseum bitfield is exposed as a typed bool getter.
        vagrant_item_lot_id: row.vagrant_item_lot_id(),
        vagrant_bonus_ene_drop_item_lot_id: row.vagrant_bonus_ene_drop_item_lot_id(),
        basic_price: row.basic_price(),
        sell_value: row.sell_value(),
        disable_use_at_out_of_coliseum: row.disable_use_at_out_of_coliseum(),
    })
}

// Fallback path (only if the crate does NOT expose the goods rows): keep er_codec's raw byte reader
// (`er_codec::read_goods_row`) over a `*const u8` row pointer obtained from a manual ParamBase walk
// resolved by AOB. That's the er_hooks.h behavior, ported. Prefer the typed path above.
