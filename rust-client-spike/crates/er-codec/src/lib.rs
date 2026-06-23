//! ER Archipelago runtime-client decode core — Rust port of `er_item_decode.h` + `er_goods_row.h`.
//!
//! Portable, Windows-free, unit-testable. Encodes the LOCKED decode contract (decisions A–F):
//!  - Goods-only routing: every synthetic placeholder is an `EquipParamGoods` row. Detection =
//!    goods category + row id > 3,780,000 (Decision D).
//!  - Location id = `vagrantItemLotId` (low 32) + `vagrantBonusEneDropItemLotId` (high 32), each
//!    stored SIGNED `i32` in the ER paramdef -> the recombine MUST cast through `u32` (see
//!    [`recombine_location_id`]).
//!  - Local replacement = `basicPrice` (real item id; 0 = no local item) + `sellValue` (qty).
//!  - Foreign-remove = the `disableUseAtOutOfColiseum` bit (ER paramdef spelling, capital O-F).
//!
//! This crate is the *transform + offset* layer only. Resolving the in-memory row pointer (the
//! `ParamBase` walk) lives in the in-process `eldenring-ap` crate; this layer takes a `&[u8]` row
//! so it stays host-testable against synthetic rows (see tests).

// ---- category nibble (top 4 bits of a "gib" item id; ER scheme, inherited from DS3) ------------

pub const CATEGORY_WEAPON: u32 = 0x0000_0000;
pub const CATEGORY_PROTECTOR: u32 = 0x1000_0000;
pub const CATEGORY_ACCESSORY: u32 = 0x2000_0000;
pub const CATEGORY_GOODS: u32 = 0x4000_0000;
pub const CATEGORY_MASK: u32 = 0xF000_0000;
pub const ROW_ID_MASK: u32 = 0x0FFF_FFFF;

/// Decision D, post goods-only: a synthetic placeholder is a goods row whose category-stripped id
/// exceeds this. Bounds vanilla goods comfortably (max real vanilla goods id = 2,220,010).
pub const SYNTHETIC_GOODS_MIN_ID: u32 = 3_780_000;

#[inline]
pub fn item_category_of(q_item_id: u32) -> u32 {
    q_item_id & CATEGORY_MASK
}

#[inline]
pub fn row_id_of(q_item_id: u32) -> u32 {
    q_item_id & ROW_ID_MASK
}

/// True iff a picked-up gib id is one of our synthetic placeholders. Goods-only: a real item in any
/// other category is never synthetic, regardless of how large its id is (e.g. the ~99M NPC weapons).
#[inline]
pub fn is_synthetic_goods(q_item_id: u32) -> bool {
    item_category_of(q_item_id) == CATEGORY_GOODS && row_id_of(q_item_id) > SYNTHETIC_GOODS_MIN_ID
}

/// Recombine the `i64` AP location id from the two vagrant carrier fields.
///
/// CRITICAL: `vagrantItemLotId` / `vagrantBonusEneDropItemLotId` are SIGNED `i32` in the ER
/// paramdef (vanilla stores -1, which an unsigned field can't hold). The `as u32` casts are
/// load-bearing: the naive signed widen `((low as i64) | ((high as i64) << 32))` sign-extends any
/// half whose bit 31 is set and clobbers the other half. ER's live ids are all in
/// `[7_000_000, 7_004_362]` (bit-31 clear, high word zero), so there is no live corruption today
/// and a byte-diff is blind to this — the fix is validated only by the bit-31 vectors below.
#[inline]
pub fn recombine_location_id(vagrant_low: i32, vagrant_high: i32) -> i64 {
    (vagrant_low as u32 as i64) | ((vagrant_high as u32 as i64) << 32)
}

/// Field values read off a synthetic `EquipParamGoods` row.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct GoodsRowFields {
    /// location id, low 32
    pub vagrant_item_lot_id: i32,
    /// location id, high 32
    pub vagrant_bonus_ene_drop_item_lot_id: i32,
    /// local real item id; 0 => no local item (foreign)
    pub basic_price: i32,
    /// local quantity
    pub sell_value: i32,
    /// foreign-remove flag
    pub disable_use_at_out_of_coliseum: bool,
}

/// Decoded synthetic placeholder.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SyntheticItem {
    pub ap_location_id: i64,
    /// 0 => no local grant
    pub local_item_id: i32,
    pub local_quantity: i32,
    /// report the check, remove the placeholder, grant nothing locally
    pub foreign_remove: bool,
}

#[inline]
pub fn decode_synthetic(f: &GoodsRowFields) -> SyntheticItem {
    SyntheticItem {
        ap_location_id: recombine_location_id(
            f.vagrant_item_lot_id,
            f.vagrant_bonus_ene_drop_item_lot_id,
        ),
        local_item_id: f.basic_price,
        local_quantity: f.sell_value,
        foreign_remove: f.disable_use_at_out_of_coliseum,
    }
}

/// What the detour should do with a confirmed synthetic placeholder (port of `PickupAction`).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PickupAction {
    /// foreign / no-local: drop the placeholder, report the check only
    Suppress,
    /// local: drop the placeholder, grant (local_item_id, local_quantity)
    SuppressAndGrant,
}

#[inline]
pub fn decide_pickup(s: &SyntheticItem) -> PickupAction {
    if !s.foreign_remove && s.local_item_id != 0 {
        PickupAction::SuppressAndGrant
    } else {
        PickupAction::Suppress
    }
}

// ---- EquipParamGoods row offsets (port of er_goods_row.h) ---------------------------------------
//
// Offsets computed from ER Paramdex EquipParamGoods.xml (EQUIP_PARAM_GOODS_ST, FormatVersion 203,
// little-endian) and validated three ways (row size 176, Smithbox CSV ordinals, type-preserving
// name diffs). A paramdef bump touches only this block.

pub const EQG_ROW_SIZE: usize = 176; // 0xB0
pub const EQG_OFF_BASIC_PRICE: usize = 0x10; // i32, ordinal 6
pub const EQG_OFF_SELL_VALUE: usize = 0x14; // i32, ordinal 7
pub const EQG_OFF_DISABLE_USE_AT_OUT_OF_COLISEUM: usize = 0x4A; // u8 bitfield byte, ordinal 54
pub const EQG_BIT_DISABLE_USE_AT_OUT_OF_COLISEUM: u8 = 0x20; // bit 5 of that byte
pub const EQG_OFF_VAGRANT_ITEM_LOT_ID: usize = 0x54; // i32, ordinal 60
pub const EQG_OFF_VAGRANT_BONUS_ENE_DROP_ITEM_LOT_ID: usize = 0x58; // i32, ordinal 61

/// Alignment-safe little-endian `i32` load (the param blob is LE, matching the x64 host). Returns
/// `None` if the offset would read past the slice — the C++ raw-pointer version can't express this,
/// so the Rust port hardens the boundary instead of trusting the caller.
#[inline]
pub fn read_i32(row: &[u8], off: usize) -> Option<i32> {
    let bytes = row.get(off..off + 4)?;
    Some(i32::from_le_bytes(bytes.try_into().unwrap()))
}

/// Pull the synthetic-carrier fields out of a raw `EquipParamGoods` row. Returns `None` if `row`
/// is shorter than the highest offset touched.
pub fn read_goods_row(row: &[u8]) -> Option<GoodsRowFields> {
    Some(GoodsRowFields {
        vagrant_item_lot_id: read_i32(row, EQG_OFF_VAGRANT_ITEM_LOT_ID)?,
        vagrant_bonus_ene_drop_item_lot_id: read_i32(
            row,
            EQG_OFF_VAGRANT_BONUS_ENE_DROP_ITEM_LOT_ID,
        )?,
        basic_price: read_i32(row, EQG_OFF_BASIC_PRICE)?,
        sell_value: read_i32(row, EQG_OFF_SELL_VALUE)?,
        disable_use_at_out_of_coliseum: (row.get(EQG_OFF_DISABLE_USE_AT_OUT_OF_COLISEUM)?
            & EQG_BIT_DISABLE_USE_AT_OUT_OF_COLISEUM)
            != 0,
    })
}

/// Convenience: raw row bytes -> decoded synthetic item.
pub fn decode_synthetic_row(row: &[u8]) -> Option<SyntheticItem> {
    Some(decode_synthetic(&read_goods_row(row)?))
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Frozen golden vectors auto-generated from spec-2's `vagrant_codec.py`
    /// (mirror of tests/codec_vectors_generated.h). (name, ap, low, high).
    const CODEC_VECTORS: &[(&str, i64, i32, i32)] = &[
        ("small id", 1000, 0x0000_03E8u32 as i32, 0x0000_0000u32 as i32),
        ("low32 bit-31 set", 2_147_483_648, 0x8000_0000u32 as i32, 0x0000_0000u32 as i32),
        ("low32 all-ones (reads as -1)", 4_294_967_295, 0xFFFF_FFFFu32 as i32, 0x0000_0000u32 as i32),
        ("just over 2^32 (high=1)", 4_294_967_296, 0x0000_0000u32 as i32, 0x0000_0001u32 as i32),
        ("high bit-31 set", 4_611_686_018_427_392_564, 0x0000_1234u32 as i32, 0x4000_0000u32 as i32),
        ("plausible AP base+index", 11_000_003_704, 0x8FA6_BC78u32 as i32, 0x0000_0002u32 as i32),
        ("max int64", 9_223_372_036_854_775_807, 0xFFFF_FFFFu32 as i32, 0x7FFF_FFFFu32 as i32),
    ];

    #[test]
    fn recombine_matches_golden_vectors() {
        for &(name, ap, low, high) in CODEC_VECTORS {
            let got = recombine_location_id(low, high);
            assert_eq!(got, ap, "vector {name:?}");
            // Document where the naive signed widen would diverge.
            let naive = (low as i64) | ((high as i64) << 32);
            if low < 0 || high < 0 {
                assert_ne!(naive, ap, "naive form should corrupt vector {name:?}");
            }
        }
    }

    #[test]
    fn recombine_inline_cases() {
        // Mirrors tests.cpp::test_recombine.
        assert_eq!(recombine_location_id(18_007_000, 0), 18_007_000);
        assert_eq!(recombine_location_id(101_898, 0), 101_898);
        assert_eq!(recombine_location_id(0, 2), 8_589_934_592);
        assert_eq!(recombine_location_id(i32::MIN, 0), 2_147_483_648);
        assert_eq!(recombine_location_id(i32::MIN, 1), 6_442_450_944);
        assert_eq!(recombine_location_id(-1, i32::MAX), 0x7FFF_FFFF_FFFF_FFFF);
    }

    #[test]
    fn detection_boundaries() {
        // Mirrors tests.cpp::test_detection.
        assert!(is_synthetic_goods(CATEGORY_GOODS | 4_000_000));
        assert!(is_synthetic_goods(CATEGORY_GOODS | 3_780_001));
        assert!(!is_synthetic_goods(CATEGORY_GOODS | 3_780_000)); // strictly greater
        assert!(!is_synthetic_goods(CATEGORY_GOODS | 2_220_010)); // max real vanilla goods id
        // goods-only payoff: other categories never misdetect regardless of magnitude
        assert!(!is_synthetic_goods(CATEGORY_WEAPON | 99_060_000));
        assert!(!is_synthetic_goods(CATEGORY_PROTECTOR | 5_330_000));
        assert!(!is_synthetic_goods(CATEGORY_ACCESSORY | 4_000_000));
        assert_eq!(item_category_of(CATEGORY_GOODS | 7_004_362), CATEGORY_GOODS);
        assert_eq!(row_id_of(CATEGORY_GOODS | 7_004_362), 7_004_362);
    }

    #[test]
    fn decode_fields() {
        // Mirrors tests.cpp::test_decode.
        let local = GoodsRowFields {
            vagrant_item_lot_id: 18_007_000,
            vagrant_bonus_ene_drop_item_lot_id: 0,
            basic_price: 1_000_000,
            sell_value: 5,
            disable_use_at_out_of_coliseum: false,
        };
        let s = decode_synthetic(&local);
        assert_eq!(s.ap_location_id, 18_007_000);
        assert_eq!(s.local_item_id, 1_000_000);
        assert_eq!(s.local_quantity, 5);
        assert!(!s.foreign_remove);
        assert_eq!(decide_pickup(&s), PickupAction::SuppressAndGrant);

        let foreign = GoodsRowFields {
            vagrant_item_lot_id: 7_004_362,
            vagrant_bonus_ene_drop_item_lot_id: 0,
            basic_price: 0,
            sell_value: 0,
            disable_use_at_out_of_coliseum: true,
        };
        let f = decode_synthetic(&foreign);
        assert_eq!(f.ap_location_id, 7_004_362);
        assert_eq!(f.local_item_id, 0);
        assert!(f.foreign_remove);
        assert_eq!(decide_pickup(&f), PickupAction::Suppress);
    }

    fn put_i32(row: &mut [u8], off: usize, v: u32) {
        row[off..off + 4].copy_from_slice(&v.to_le_bytes());
    }

    #[test]
    fn read_raw_row_local_replacement() {
        // Mirrors row_test.cpp: local-replacement synthetic, bit-31-set low + high=1.
        let mut row = [0u8; EQG_ROW_SIZE];
        put_i32(&mut row, EQG_OFF_VAGRANT_ITEM_LOT_ID, 0x8FA0_E6B8);
        put_i32(&mut row, EQG_OFF_VAGRANT_BONUS_ENE_DROP_ITEM_LOT_ID, 0x0000_0001);
        put_i32(&mut row, EQG_OFF_BASIC_PRICE, 100_100);
        put_i32(&mut row, EQG_OFF_SELL_VALUE, 3);

        let fields = read_goods_row(&row).unwrap();
        assert_eq!(fields.vagrant_item_lot_id, 0x8FA0_E6B8u32 as i32);
        assert_eq!(fields.basic_price, 100_100);
        assert_eq!(fields.sell_value, 3);
        assert!(!fields.disable_use_at_out_of_coliseum);

        let s = decode_synthetic_row(&row).unwrap();
        assert_eq!(s.ap_location_id, 0x1_8FA0_E6B8); // sign-safe recombine straight off the row
        assert_eq!(s.local_item_id, 100_100);
        assert_eq!(s.local_quantity, 3);
        assert!(!s.foreign_remove);
    }

    #[test]
    fn bit5_isolation_and_foreign_remove() {
        // neighbor bits 4 and 6 set, NOT bit 5 -> foreignRemove false
        let mut row = [0u8; EQG_ROW_SIZE];
        row[EQG_OFF_DISABLE_USE_AT_OUT_OF_COLISEUM] = 0x10 | 0x40;
        assert!(!read_goods_row(&row).unwrap().disable_use_at_out_of_coliseum);

        // bit 5 set, no local item -> foreign remove
        let mut row = [0u8; EQG_ROW_SIZE];
        put_i32(&mut row, EQG_OFF_VAGRANT_ITEM_LOT_ID, 7_004_362);
        row[EQG_OFF_DISABLE_USE_AT_OUT_OF_COLISEUM] = EQG_BIT_DISABLE_USE_AT_OUT_OF_COLISEUM;
        let g = decode_synthetic_row(&row).unwrap();
        assert_eq!(g.ap_location_id, 7_004_362);
        assert!(g.foreign_remove);
        assert_eq!(g.local_item_id, 0);
    }

    #[test]
    fn short_row_is_rejected_not_ub() {
        // The C++ raw-pointer reader would read OOB; the Rust port returns None.
        assert!(read_goods_row(&[0u8; 16]).is_none());
        assert!(read_i32(&[0u8; 3], 0).is_none());
    }
}
