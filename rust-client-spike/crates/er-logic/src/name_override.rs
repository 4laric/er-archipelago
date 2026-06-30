//! Pure half of the shop/item name-preview feature: the table the `MsgRepositoryImp::LookupEntry`
//! hook consults to decide what text to show for a given lookup id. The hook itself (the AOB scan +
//! detour + returning a UTF-16 pointer) is game I/O and lives in `eldenring-ap`; this module owns the
//! *decision* so it's host-tested.
//!
//! Technique adapted from VirusAlex/ERR-MapForGoblins-DLL (MIT) — its `goblin_messages.cpp` hooks
//! LookupEntry and redirects a marker's text id to an existing item-name FMG entry, getting all 14
//! languages for free. We generalize: an override is EITHER a redirect to an existing FMG id (use for
//! own-world AP items that are real ER items — free localization) OR a custom string (foreign items /
//! "Item (Player)"), built from AP `LocationScouts` results.

use std::collections::HashMap;

/// What the hook should return for a looked-up text id.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Override {
    /// Return the existing in-game FMG string for this other id (localized for free). Use when the AP
    /// item is a real ER item — point at its real name id.
    Redirect(i32),
    /// Return this exact string (the hook owns a UTF-16 buffer for it). Use for foreign items or when
    /// an owner suffix is wanted, e.g. "Moonveil (Yenix4)".
    Custom(String),
}

/// Lookup-id -> override. Keyed by whatever id the hook sees for an AP-check shop slot (e.g. a
/// per-slot carrier item's name id, assigned the way MapForGoblins assigns unique marker ids). Built
/// once after scouting, replaced on reconnect.
#[derive(Debug, Default, Clone)]
pub struct NameTable {
    map: HashMap<i32, Override>,
}

impl NameTable {
    pub fn new() -> Self {
        Self { map: HashMap::new() }
    }

    pub fn insert(&mut self, lookup_id: i32, ov: Override) {
        self.map.insert(lookup_id, ov);
    }

    /// The hook's decision: `Some(override)` => substitute; `None` => pass through to the real text.
    pub fn resolve(&self, lookup_id: i32) -> Option<&Override> {
        self.map.get(&lookup_id)
    }

    pub fn len(&self) -> usize {
        self.map.len()
    }
    pub fn is_empty(&self) -> bool {
        self.map.is_empty()
    }
}

/// Format the display string for a scouted AP item. Own-world items that are real ER items should use
/// `Override::Redirect` instead (free localization); this is for the `Custom` cases — foreign items,
/// or when you want the owner shown. `owner = None` (or your own slot) => no suffix.
pub fn display_name(item_name: &str, owner: Option<&str>) -> String {
    match owner {
        Some(o) if !o.is_empty() => format!("{item_name} ({o})"),
        _ => item_name.to_string(),
    }
}

/// How an AP item is classified by the server's item flags — shown on the GoodsCaption (lore box)
/// line so a shop check is a routing decision, not a blind buy. Mirrors AP's `NetworkItemFlags`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ItemKind {
    Progression,
    Useful,
    Filler,
    Trap,
}

impl ItemKind {
    /// Derive the single label from the three `LocatedItem` flag bits
    /// (`is_progression` / `is_useful` / `is_trap`). The bits can co-occur, so this picks ONE by
    /// precedence: **Trap > Progression > Useful > Filler**. Trap wins because it's the deceptive,
    /// player-relevant warning; a pure trap (only the trap bit) still resolves to `Trap` under any
    /// precedence. Flip the order here if you'd rather surface Progression over a trap masquerade.
    pub fn from_flags(is_progression: bool, is_useful: bool, is_trap: bool) -> Self {
        if is_trap {
            ItemKind::Trap
        } else if is_progression {
            ItemKind::Progression
        } else if is_useful {
            ItemKind::Useful
        } else {
            ItemKind::Filler
        }
    }

    pub fn label(self) -> &'static str {
        match self {
            ItemKind::Progression => "Progression",
            ItemKind::Useful => "Useful",
            ItemKind::Filler => "Filler",
            ItemKind::Trap => "Trap",
        }
    }
}

/// Build the GoodsCaption (big lore box) text for a scouted AP item: the receiving player's game,
/// the owner (alias + slot), and the item classification — one per line (`\n`, which ER renders as a
/// line break in the caption panel). Pure + host-tested so the `eldenring-ap` FMG-inject layer only
/// has to UTF-16-encode the result and swap it into the caption MsgData. Built from the SAME scout
/// result that feeds the name: `receiver().game()`, `receiver().alias()`, `receiver().slot()`,
/// `is_progression()/is_useful()/is_trap()`.
pub fn description(game: &str, owner: &str, slot: u32, kind: ItemKind) -> String {
    format!("{game}\nFor: {owner} (slot {slot})\n{}", kind.label())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn resolve_hit_and_miss() {
        let mut t = NameTable::new();
        t.insert(9_000_001, Override::Redirect(110000)); // -> a real WeaponName id
        t.insert(9_000_002, Override::Custom("Moonveil (Yenix4)".into()));
        assert_eq!(t.resolve(9_000_001), Some(&Override::Redirect(110000)));
        assert_eq!(t.resolve(9_000_002), Some(&Override::Custom("Moonveil (Yenix4)".into())));
        assert_eq!(t.resolve(123), None); // not an override -> hook passes through
        assert_eq!(t.len(), 2);
    }

    #[test]
    fn display_name_with_owner() {
        assert_eq!(display_name("Moonveil", Some("Yenix4")), "Moonveil (Yenix4)");
    }

    #[test]
    fn display_name_without_owner() {
        assert_eq!(display_name("Golden Seed", None), "Golden Seed");
        assert_eq!(display_name("Golden Seed", Some("")), "Golden Seed"); // empty owner = no suffix
    }

    #[test]
    fn empty_table_passes_everything_through() {
        let t = NameTable::new();
        assert!(t.is_empty());
        assert_eq!(t.resolve(9_000_001), None);
    }

    #[test]
    fn item_kind_precedence() {
        // pure classes
        assert_eq!(ItemKind::from_flags(true, false, false), ItemKind::Progression);
        assert_eq!(ItemKind::from_flags(false, true, false), ItemKind::Useful);
        assert_eq!(ItemKind::from_flags(false, false, false), ItemKind::Filler);
        assert_eq!(ItemKind::from_flags(false, false, true), ItemKind::Trap);
        // precedence: Trap > Progression > Useful
        assert_eq!(ItemKind::from_flags(true, true, true), ItemKind::Trap);
        assert_eq!(ItemKind::from_flags(true, true, false), ItemKind::Progression);
    }

    #[test]
    fn description_three_lines() {
        let d = description("Hollow Knight", "Yenix4", 3, ItemKind::Progression);
        assert_eq!(d, "Hollow Knight\nFor: Yenix4 (slot 3)\nProgression");
        assert_eq!(d.lines().count(), 3);
    }

    #[test]
    fn description_filler_and_trap() {
        assert_eq!(
            description("Elden Ring", "Alaric", 1, ItemKind::Filler),
            "Elden Ring\nFor: Alaric (slot 1)\nFiller"
        );
        assert_eq!(
            description("Super Metroid", "Bob", 2, ItemKind::Trap),
            "Super Metroid\nFor: Bob (slot 2)\nTrap"
        );
    }
}
