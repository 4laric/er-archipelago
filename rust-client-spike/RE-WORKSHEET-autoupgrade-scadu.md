# RE-WORKSHEET — auto_upgrade + global_scadutree_blessing

Cheat Engine shopping list + struct chains for the TWO ER-AP client features still needing
game-memory RE. Do the CE work on Windows; this worksheet is the map. Scaffold lives in
`crates/eldenring-ap/src/game/upgrades.rs` (every `// RE:` hole there cites a section here).

**Status:** both features are INERT in the Rust client — `apply_auto_upgrade` returns its input
unchanged and `tick_global_scadu` returns early until the holes below are filled. The pure id-math
and the Scadutree cost curve are already ported and unit-tested; what is missing is the typed/RE'd
game-memory access (weapon param walk, inventory walk, PlayerGameData stored-blessing byte).

**Source of truth (C++, this repo):**
- `Dark-Souls-III-Archipelago-client/archipelago-client/er_gamehook_win.cpp`
  - auto_upgrade: `AutoUpgradeWeaponIdImpl` ~666, `RefreshAutoUpgradeTargets` ~609, `WeaponInfo` ~542,
    `ResolveWeaponParams` ~488, `CalibrateOffset` ~505, `CapForRT` ~530, the `Detour` rewrite ~177,
    the `GrantItem` rewrite ~201.
  - scadu: `TickGlobalScaduBlessing` ~720, `SetGlobalScaduBlessing` ~715, `kScaduCum`/`kScaduCombatLevelOff` ~704.
- `archipelago-client/ArchipelagoInterface.cpp` ~92-100: slot_data `options.auto_upgrade` (int) and
  `options.global_scadutree_blessing` (int) feed `SetAutoUpgrade(int)` / `SetGlobalScaduBlessing(int)`.

**Rust resolution context (already wired in this client):** `VERIFY-RESOLUTION.md` + `params.rs`
show the typed param path: `unsafe { SoloParamRepository::instance() }.ok()?.get::<EquipParamGoods>(id)`
returns `Option<&EQUIP_PARAM_GOODS_ST>`; fields are snake_case getter methods. `flags.rs` shows the
in-world gate (`WorldChrMan.main_player.play_region_id`). `detour.rs`/`grant.rs` show the grant path.

---

## Slot_data wiring (no RE — net.rs, do when implementing)

In `net.rs` `feature_config(...)` / the slot-connected handler (alongside `enable_dlc` / `ending_condition`):

```rust
// after `use super::upgrades;` (and `mod upgrades;` in mod.rs behind the net/detour feature)
upgrades::set_auto_upgrade(
    sd.pointer("/options/auto_upgrade").and_then(|v| v.as_i64()).unwrap_or(0) as i32,
);
upgrades::set_global_scadu_blessing(
    sd.pointer("/options/global_scadutree_blessing").and_then(|v| v.as_i64()).unwrap_or(0) as i32,
);
```

These are int options (0/1 for auto_upgrade; 0/1/2 for scadu), parsed exactly like `ending_condition`
(`net.rs:154`). DO NOT edit net.rs as part of this worksheet task — this is the plan for later.

---

# FEATURE A — auto_upgrade

**Goal (one line):** every REAL weapon you acquire arrives pre-reinforced to your current highest
+N on the same smithing track (normal vs somber), clamped to that weapon's cap.

**Exact C++ behaviour matched:** `er_gamehook_win.cpp:666` `AutoUpgradeWeaponIdImpl`:
1. Decode the inbound id: `base = id - id%100`, `level = id%100` (ER bakes +N into the id; one
   EquipParamWeapon row per weapon, id = base + N). Reject non-weapons / out of `[1_000_000, 90_000_000)`.
2. `EquipParamWeapon[base].reinforceTypeId` → `ReinforceParamWeapon`: `cap` = count of consecutive
   ReinforceParamWeapon rows starting at `reinforceTypeId` (`CapForRT` ~530). `cap > 10` ⇒ normal
   track (max +25); `cap` in `1..=10` ⇒ somber (max +10). `somber = (cap <= 10)`.
3. `target` = highest +N currently HELD on that track (walk inventory, `RefreshAutoUpgradeTargets`
   ~609), clamped to `cap`. If `target <= level`, return unchanged (only ever raise).
4. Rewrite the id to `base + target`. In `Detour` (~177) the descriptor's id at `entry+0x04` is
   overwritten; in `GrantItem` (~201) the id-with-category is replaced before the standalone AddItem.

The C++ also self-calibrates the `reinforceTypeId` byte offset at runtime (anchors: normal rows read
0, somber rows read 2200) — see §A.2. With the typed `eldenring` binding this should be a NAMED FIELD
instead, eliminating the calibration entirely (verify on docs.rs).

## §A.1 — Confirm the WEAPON category & id math (mostly done; verify in CE)
- ER weapon FullID = `(row) | (category_nibble << 28)`. Weapon row ids live in `[1_000_000, 90_000_000)`.
- A +N weapon's row id = base + N, `base % 100 == 0`, `N in 0..=25` (normal) or `0..=10` (somber).
- **CE check:** equip/inventory a known weapon (e.g. a +3 Longsword). Its base is a round-100 id.
  Confirm the in-bag item id = base + 3. This validates `decode_weapon_id` (already ported in
  upgrades.rs); the `er_codec` CATEGORY_WEAPON nibble spelling is the only Rust-side `RE-A1` to confirm.

## §A.2 — EquipParamWeapon → reinforceTypeId, ReinforceParamWeapon → cap  (RE-A2)
- **Preferred (no CE):** check docs.rs for `eldenring::cs::EquipParamWeapon` (marker, like
  `EquipParamGoods`) + `EQUIP_PARAM_WEAPON_ST::reinforce_type_id()`, and a `ReinforceParamWeapon`
  marker. If present: `repo.get::<EquipParamWeapon>(base as u32)?.reinforce_type_id()`, then loop
  `repo.get::<ReinforceParamWeapon>((rt + k) as u32)` for k in 0..=25 to count the cap. NO CE NEEDED.
- **Fallback (CE, only if the binding is missing):** find the param-repo blob for EquipParamWeapon by
  content fingerprint (rows 2000000 & 1000000 exist) and ReinforceParamWeapon (rows 0,25,2200,2210,9010)
  exactly as `ResolveWeaponParams` ~488 does, then calibrate the `reinforceTypeId` s16 offset: scan
  offsets 0..1024 in an EQW row until the four normal anchors `{2000000,1000000,9000000,11010000}`
  read 0 and the four somber anchors `{9060000,9040000,3090000,3140000}` read 2200 (`CalibrateOffset` ~505).
- **AOB/RVA pin:** none needed if the binding exists — `SoloParamRepository::instance()` is already a
  resolved FD4 singleton (params.rs). The fingerprint walk is self-anchoring (no version-fragile RVA).

## §A.3 — Highest held +N per track (inventory walk)  (RE-A3)
- Struct chain: `GameDataMan` (singleton) → `PlayerGameData` (`GAMEDATAMAN_PGD_OFF`, was +0x08) →
  the embedded `EquipInventoryData` container → primary array (+ overflow array). Each entry: item id
  at `+0x04` (resolved base+level), qty at the qty offset. C++ `RefreshAutoUpgradeTargets` ~609
  auto-discovers the container by shape (slotCount sane, primary ptr aligned, first entry's qty in
  0..9999), walks it, and records `max(level)` for the normal track and the somber track separately.
  Throttle to ~1500ms; cache the discovered container offset.
- **Preferred (no CE):** `eldenring::cs` exposes `game_data_man` + `player_game_data` + `item` +
  `gaitem` + `item_id` (PORT-GAP-MAP.md §"Coverage"). Find the inventory-container field on
  `PlayerGameData` and the per-row item-id accessor on docs.rs. If a typed iterator over held items
  exists, this whole walk becomes a `.filter(is_weapon).map(level).max()` per track. NO CE.
- **Fallback (CE):** in CE, hold several upgraded weapons, scan for the bag array: find PlayerGameData
  (GameDataMan+0x08), then scan PlayerGameData+0x000..0x600 in steps of 8 for the container shape
  (slotCount int + aligned primary pointer whose first entry is a sane id/qty). Confirm entry id @ +0x04,
  qty @ the qty offset, by eyeballing a known stack. Reuse `INV_*` constants from `er_hooks.h`.

## Rust touchpoint (scaffold signature, upgrades.rs)
```rust
pub fn apply_auto_upgrade(full_id: i32) -> i32      // detour.rs real-weapon branch + grant.rs grant_full_id
fn weapon_track_and_cap(base: i32) -> Option<(i32,bool)>   // §A.2
fn highest_held_level(somber: bool) -> Option<i32>          // §A.3
```
Call sites (described, NOT edited by this task):
- `detour.rs` `add_item_detour`, in the `!is_synthetic_goods(raw_id)` branch: before
  `call_original(...)`, do `let up = upgrades::apply_auto_upgrade(raw_id as i32); if up != raw_id as i32 { write_i32(entry, ITEMBUF_ENTRY_ID_OFF, up); }` (mirrors C++ `Detour` ~177).
- `grant.rs` `grant_full_id` (server-pushed weapons bypass the detour): `let id = upgrades::apply_auto_upgrade(full_id);` before constructing the itembuf (mirrors C++ `GrantItem` ~201).

## Validation (in-game)
- Manually reinforce a weapon to your account-max on each track (e.g. a normal weapon to +12, a
  somber to +6). Then acquire a fresh BASE weapon of each track (chest, vendor, or `!getitem`/AP grant).
  It must arrive at +12 (normal) / +6 (somber), clamped to that weapon's own cap (e.g. a somber weapon
  caps at +10). The log line `auto_upgrade: weapon 0x... (+0) -> +N (track, cap +M)` should print.
- Negative: acquiring a weapon already at/above your max must NOT downgrade it.

---

# FEATURE B — global_scadutree_blessing

**Goal (one line):** in the BASE game (no DLC revere needed), holding N Scadutree Fragments grants a
stored Scadutree Blessing level via the vanilla cost curve, so the combat buff applies everywhere.

**Exact C++ behaviour matched:** `er_gamehook_win.cpp:720` `TickGlobalScaduBlessing` (per-tick, ~1s throttle):
1. Walk the player inventory for the Scadutree Fragment stack: goods row `2010000`, FullID =
   `2010000 | CATEGORY_GOODS`. Read its qty = total fragments. (Both AP fragment variants share goods
   id 2010000, so it's ONE stack.)
2. `level` = highest L in 0..20 with `frag_qty >= kScaduCum[L]`, where
   `kScaduCum = {0,1,3,5,7,9,11,13,15,17,20,23,26,29,32,35,38,41,44,47,50}` (cumulative-to-reach).
3. Read the stored combat-blessing byte at `PlayerGameData + 0xFC` (signed). Only RAISE it
   (`if cur >= level: skip` — never stomp a real DLC revere, never down-flicker). Write the new byte.
   The engine recomputes the speffect from this byte on the next map load / grace rest.

`SetGlobalScaduBlessing(mode)` (~715) is a tri-state: 0=off, 1=player_only, 2=scaled (the client
currently treats 1 and 2 the same — both just enable; the scaled variant is a future apworld concern).

## §B.0 — mode plumbing (no RE)
Already in the scaffold: `set_global_scadu_blessing(mode)` clamps to {0,1,2}; `tick_global_scadu`
returns early on 0. Gate the body on `super::flags::in_world()` (flags.rs:107) — same gate the param
probe uses (mod.rs `tick()`), so the inventory/PlayerGameData reads only fire when loaded.

## §B.1 — Held Scadutree Fragment count  (RE-B1)
- SAME inventory chain as §A.3 (GameDataMan → PlayerGameData → EquipInventoryData). Scan for FullID
  `2010000 | CATEGORY_GOODS`, read its qty. C++ `TickGlobalScaduBlessing` reuses the §A.3 container
  discovery + the cached container offset — implement ONE shared inventory helper and use it for both
  features (highest-weapon-level AND fragment-qty).
- **CE check:** hold a known number of Scadutree Fragments, find the bag (per §A.3), and confirm the
  entry with id `2010000|GOODS` has qty == the count you hold. Goods carry the category nibble in the bag.

## §B.2 / §B.3 — Stored combat-blessing byte at PlayerGameData + 0xFC  (RE-B2 / RE-B3)
- **CE recipe:** in the base game, get the DLC's Scadutree Blessing to a known level via a Revered
  Spirit Ash / a fragment (or just read it at 0). Find `PlayerGameData` (GameDataMan + 0x08), then
  scan a signed byte near `+0xFC` whose value == your current blessing level. Confirm by changing the
  level in game (rest at a Scadutree-blessed site / use a fragment) and next-scanning the new value.
  **Caveat from C++ comment (~700):** 0xFC was relative to the Hexinton/TGA CE table's
  `[GameDataMan+0x08]`. This client must confirm its resolved `PlayerGameData` == that pointer. If the
  buff never applies, verify THAT first (the offset may be relative to a different base).
- **Preferred (no raw offset):** check docs.rs for a NAMED field on the `eldenring::cs` PlayerGameData
  struct for the stored Scadutree/combat blessing level. If it exists, read/write it via the binding
  and skip the +0xFC RE entirely. If not, RE the offset in CE and read/write it raw (guarded write).
- **AOB/RVA pin:** none — anchors off the already-resolved GameDataMan singleton (no version-fragile RVA).
- Write only on raise; use a page-validated/guarded write (C++ uses SEH `SehWriteU8`). Throttle ~1s.

## Rust touchpoint (scaffold signature, upgrades.rs)
```rust
pub fn tick_global_scadu()                  // call from mod.rs tick() (in-world feature neighbourhood)
fn held_scadu_fragments() -> Option<i32>    // §B.1  (shares the §A.3 inventory walk)
fn read_stored_blessing() -> Option<i32>    // §B.2
fn write_stored_blessing(level: i32) -> bool // §B.3
```
Call site (described, NOT edited by this task): `mod.rs` `tick()`, in the `#[cfg(feature = "net")]`
block next to `features::tick();`, add `upgrades::tick_global_scadu();` (and `mod upgrades;` under the
net/detour cfg). It self-gates on mode + (recommended) `flags::in_world()`.

## Validation (in-game)
- In a BASE-game (DLC-off or non-Shadow-Realm) session, hold e.g. 3 Scadutree Fragments → blessing
  level 2 (per `kScaduCum`). Rest at a grace / reload the map and confirm the Scadutree damage/defence
  buff is active and scales as you hold more (1→L1, 3→L2, 50→L20). Log: `global_scadu_blessing:
  frags=N -> blessing level L (PlayerGameData+0xFC, was C)`.
- Negative: a real DLC blessing higher than the fragment-derived level must NOT be lowered.

---

# One-session CE shopping list

**auto_upgrade**
- [ ] (Rust-only) Confirm `er_codec` CATEGORY_WEAPON nibble spelling for `decode_weapon_id` (RE-A1).
- [ ] EquipParamWeapon row → `reinforceTypeId`: prefer `eldenring::cs::EquipParamWeapon` typed field on
      docs.rs; else CE-fingerprint the param blob + calibrate the s16 offset (anchors in §A.2). (RE-A2)
- [ ] ReinforceParamWeapon → cap (count consecutive rows from reinforceTypeId; >10 normal/+25, ≤10 somber/+10). (RE-A2)
- [ ] Inventory walk: GameDataMan → PlayerGameData(+0x08) → EquipInventoryData container; entry id @ +0x04,
      qty offset; highest +N per track. Prefer a typed `eldenring::cs` inventory iterator; else CE the container shape. (RE-A3)

**global_scadutree_blessing**
- [ ] Held Scadutree Fragment qty: same inventory chain; entry FullID `2010000|GOODS` → qty (shared helper with RE-A3). (RE-B1)
- [ ] Stored blessing byte: `PlayerGameData + 0xFC` (signed) — CONFIRM the client's PlayerGameData ==
      the CE table's `[GameDataMan+0x08]` base; prefer a named docs.rs field over the raw offset. Read + guarded raise-only write. (RE-B2/B3)

**Already done (no CE):** weapon base/level id math, the ReinforceParam cap rule, the Scadutree cost
curve `kScaduCum`, the raise-only / no-down-flicker logic, mode plumbing — all ported + unit-tested in upgrades.rs.
