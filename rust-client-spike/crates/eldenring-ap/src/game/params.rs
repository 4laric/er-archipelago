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
//! ⚠️ COMPILE-TARGET SKETCH. `// VERIFY:` marks the exact lookup-call spelling to confirm.

use er_codec::GoodsRowFields;

// VERIFY: the param struct is `eldenring::param::EQUIP_PARAM_GOODS_ST` (confirmed present in
// docs.rs/eldenring 0.14). The lookup entry point is the `ParamDef` trait ("Trait to perform safe
// param lookups"); confirm whether the call is `EQUIP_PARAM_GOODS_ST::get(id)` /
// `SoloParamRepository`-driven iteration / an index map. Pseudo-import kept so intent is clear:
use eldenring::param::EQUIP_PARAM_GOODS_ST;

/// Phase-1 spike: confirm the crate reaches the goods param at all. Should log a rowCount that
/// matches tools/NOTES.md (the live scan found goods rowCount 3571, firstRowId 0). If this works,
/// Strategy B's central assumption holds and the manual ParamBase walk is dead.
pub fn spike_log_goods_rowcount() {
    match goods_row_count() {
        Some(n) => tracing::info!("EquipParamGoods rowCount = {n} (expect ~3571 per NOTES.md)"),
        None => tracing::warn!("EquipParamGoods not resolvable yet (param repo not initialized?)"),
    }
}

/// Number of rows in EquipParamGoods, or `None` if the param repository isn't up yet.
fn goods_row_count() -> Option<usize> {
    // VERIFY: replace with the crate's param iteration/length. Sketch intent:
    //   Some(EQUIP_PARAM_GOODS_ST::iter().count())
    // or via SoloParamRepository::instance()? -> table -> len.
    None
}

/// Look up a goods row by its (category-stripped) row id and project the carrier fields into the
/// pure decode struct. `None` if the param repo isn't ready or the id is absent.
///
/// The five fields are the locked decode contract (er_item_decode.h): the two vagrant halves carry
/// the AP location id, `basicPrice`/`sellValue` the local replacement, `disableUseAtOutOfColiseum`
/// bit the foreign-remove flag.
pub fn goods_row_fields(row_id: i32) -> Option<GoodsRowFields> {
    let row: &EQUIP_PARAM_GOODS_ST = lookup_goods(row_id)?;
    Some(GoodsRowFields {
        // VERIFY: field names on EQUIP_PARAM_GOODS_ST. Paramdef spellings (the C++ used these exact
        // names): vagrantItemLotId, vagrantBonusEneDropItemLotId, basicPrice, sellValue,
        // disableUseAtOutOfColiseum. Rust bindings usually snake_case them.
        vagrant_item_lot_id: row.vagrant_item_lot_id,
        vagrant_bonus_ene_drop_item_lot_id: row.vagrant_bonus_ene_drop_item_lot_id,
        basic_price: row.basic_price,
        sell_value: row.sell_value,
        // VERIFY: bitfield accessor. er_goods_row.h used byte 0x4A bit5 (mask 0x20); the crate
        // likely exposes a typed bool or a bitfield getter.
        disable_use_at_out_of_coliseum: row.disable_use_at_out_of_coliseum(),
    })
}

/// VERIFY: the actual safe lookup. Placeholder so the shape compiles in review; real impl uses the
/// `ParamDef` trait. Returns a reference into the live (decrypted) param table.
fn lookup_goods(_row_id: i32) -> Option<&'static EQUIP_PARAM_GOODS_ST> {
    None
}

// Fallback path (only if the crate does NOT expose the goods rows): keep er_codec's raw byte reader
// (`er_codec::read_goods_row`) over a `*const u8` row pointer obtained from a manual ParamBase walk
// resolved by AOB. That's the er_hooks.h behavior, ported. Prefer the typed path above.
