# SPEC: Auto-Equip (true "use what you get")

Status: SCOPED (2026-06-17). DECISIONS LOCKED for v1: **weapons only**, **always
right-hand slot 1 (RH1)**, **clean game-call only** (no direct-ChrAsm-write fallback).
Pairs with `auto_upgrade` as the level mitigation — received weapon arrives upgraded,
then gets equipped. Related: `er-auto-upgrade-noop` (the infra this reuses),
`er-client-inventory-removal`, `er-client-load-crash-poll-gate` (the load-race lesson).

## TL;DR of the audit

- **apworld half is already DONE.** `AutoEquipOption(Toggle)` exists in `options.py`
  ("Automatically equips any received armor or left/right weapons"), it's wired into
  `EROptions` (`auto_equip: AutoEquipOption`), and `fill_slot_data` already emits
  `"auto_equip": self.options.auto_equip.value` in the `options` block. **No apworld work.**
- **The entire gap is client-side**, and it is real. `CGameHook::equipItem` is a stub
  (`// Auto-equip is out of scope for the goods-only MVP`, args `(void)`'d).
- `AutoEquip.cpp` / `AutoEquip.h` / `GameTypes.h` are **DS3 leftovers from the fork
  origin**, NOT ER: DS3 `EquipSlot` indices, `>>0x1C` type decode, hardcoded
  `0x470/0x1B8/0x38` offsets, DS3 protector-id tables, DS3 `WorldChrMan`/`SPlayerIns`
  layout (`unk00[0x1F90]`). Treat them as a design reference, not portable code.
- `er_singletons.h` notes **WorldChrMan is not yet resolved on ER** ("accessor is not
  the uniform shape — resolve separately"), so the DS3 equip-anim unlock
  (`actionModule->chrEquipAnimFlags`) has no ER backing today.

So: auto_upgrade gave us the receipt + inventory-read halves for free. The equip call
itself is unbuilt for ER and is the only hard work item.

## Goal

When `auto_equip == 1`, any **weapon** you acquire (world loot, chest, NPC gift, craft,
or AP grant) is immediately equipped to **right-hand armament slot 1**, replacing
whatever is there. Combined with `auto_upgrade` on, you fight with whatever the seed
hands you, at your current track level — a true "use what you get" run.

v1 is deliberately narrow: weapons only (no armor/talismans/ammo), one slot, one path.

## 1. What we reuse from auto_upgrade (no new RE)

All in `er_gamehook_win.cpp` / `er_gamehook.h`, proven in-game:

- **Receipt hook points**: the `AddItem` Detour (`g_addItemOrig`) and the `GrantItem`
  path. Both already fire on every weapon acquired.
- **Inventory walk**: `g_gameDataManPtrLoc → GAMEDATAMAN_PGD_OFF (PlayerGameData) →
  containers (INV_SCAN_OFF_LO/HI)`, with the slot layout from the readid fix:
  `+0x00` = **GaItemHandle**, `+0x04` = **resolved item id** (base+level). The equip
  call needs that handle — we already read it.
- **Classification**: `er_item_decode.h` `CATEGORY_WEAPON` mask + `WeaponInfo` decode
  (base / level / track) tell us "is this an equippable weapon" cheaply.
- **Safety pattern**: `SafeRead`, `InventoryInstance()` gating, the SEH wrap, and the
  "don't touch state mid-load" discipline (the auto_upgrade Load-Game crash).

## 2. The crux — the ER equip call (the only real RE)

ER equips by writing the armament into the player's `ChrAsm` and triggering a recalc
(weight / equip-load, stat-requirement penalty, weapon model + moveset). We do **not**
hand-write `ChrAsm` (locked decision: clean-call-only) because that skips the recalc and
leaves weight/model stale — strictly worse than auto_upgrade's risk profile.

Instead, find and call the routine the equip menu invokes. The DS3 stub signature is the
shape hint: `equipItem(EquipSlot slot, inventoryIndex/handle)`.

**RE work item (Windows + CE/Ghidra against eldenring.exe 2.6.2.0,
sha256 34102b1c…):**

1. Find ER's `ChrAsm`/`EquipGameData` equip-weapon function — the one the equip menu
   calls when you assign an armament to a hand slot. Candidate handles: the function
   that takes a `PlayerGameData`/`EquipGameData`/`EquipMagicData` `this`, an equip-slot
   index, and a `GaItemHandle` (or inventory index). CE "weapon swap" / equip scripts in
   the ER table community are the fast path to the AOB.
2. Pin its **ABI** (this-ptr source, arg order, whether it wants the GaItemHandle vs the
   inventory list index, return value). Record the AOB + RVA in `er_singletons.h`-style
   comments, the way `g_addItemOrig` / GameDataMan are documented.
3. Decide the **equip-anim gate**: confirm whether the function self-handles the
   equip-animation lock or whether ER needs the `chrEquipAnimFlags` analog set first
   (DS3 did `|= 1`). If needed, resolve WorldChrMan on ER first (currently unresolved).
   Hypothesis: the menu-level equip call handles it internally — verify before adding
   WorldChrMan as a dependency.

**The one ER constant to confirm for v1**: the equip-slot index for **right-hand
armament 1**. DS3's enum had `rightHand1 = 0x01`; ER's ChrAsm slot indexing differs and
must be confirmed against the live exe — but we only need this single value for v1, so
the surface area is tiny.

## 3. Hook point & ordering with auto_upgrade

auto_upgrade rewrites the inbound id **inside** the `AddItem` Detour (so the item lands
in the bag already at +N). Therefore auto_equip must run **after the add completes**, not
inside the Detour, so it equips the upgraded copy:

- Fire on the **next safe tick** (or immediately post-`g_addItemOrig`), then walk live
  inventory, find the most-recently-added weapon's GaItemHandle (`+0x00`) whose id
  (`+0x04`) matches the upgraded id, and call the equip routine with `(RH1, handle)`.
- This is the same live-inventory read auto_upgrade's `RefreshAutoUpgradeTargets` already
  does — auto_equip rides the same walk, just grabbing the handle instead of the level.
- Net synergy: equip reads the post-upgrade inventory, so it equips at the correct level
  with zero ordering fight.

"True UWYG": equip **whatever just arrived** (even a side-grade/down-grade), not
"equip-if-better". auto_upgrade is the level mitigation; auto_equip does no quality
judgement.

## 4. Safety (mirror auto_upgrade)

- **Self-gate**: no-op unless `auto_equip == 1` AND `InventoryInstance() != 0` (in-world,
  not title/load). Never equip during the Load-Game inventory rebuild — same race that
  crashed auto_upgrade; SEH-wrap the equip path (`->Impl + __try/__except`).
- **Idempotent / no spam**: only act on a genuine new receipt, not on every tick. Reuse
  the `last_received_index` discipline already in the grant path so reconnect storms
  don't re-equip in a loop.
- **Main thread only**: equip routines commonly assert off-thread — call from the same
  context the grant/Detour already runs in, not the network thread.
- **Fail closed**: if the equip function/slot index doesn't resolve or calibrate, stay
  idle and log once (`auto_equip: equip routine unresolved; idle this session`). Never
  corrupt ChrAsm.

## 5. Implementation plan (client only)

Patch script `patch_client_autoequip.py`, same shape as `patch_client_autoupgrade.py`
(idempotent, EOL-preserving, anchor-checked). Touches three files:

1. **`er_gamehook.h`** — declarations:
   ```cpp
   void SetAutoEquip(int on);
   bool EquipReceivedWeapon(int32_t itemId);   // find handle, equip to RH1; true => equipped
   ```
2. **`er_gamehook_win.cpp`** — impl:
   - `g_autoEquip` flag + `SetAutoEquip`.
   - `g_equipFn` resolved via AOB at Init (alongside the existing GameDataMan resolve),
     `g_rh1SlotIndex` constant (confirmed value from §2).
   - `EquipReceivedWeapon(id)`: `Ready()`-style gate → walk live inventory for the
     GaItemHandle whose `+0x04` == `id` → SEH-wrapped call
     `g_equipFn(equipGameData, g_rh1SlotIndex, handle)`.
   - Call site: post-`g_addItemOrig` in the Detour **and** in `GrantItem` (AP grants
     bypass the Detour), gated on `WeaponInfo(id)` so only weapons trigger it. Run after
     the auto_upgrade id-rewrite so the upgraded id is what's in the bag.
3. **`ArchipelagoInterface.cpp`** — slot_data parse, exact mirror of the auto_upgrade
   block (the apworld already emits the key):
   ```cpp
   if (data.at("options").contains("auto_equip"))
       er_ap::game::SetAutoEquip(data.at("options").at("auto_equip").get<int>());
   else
       er_ap::game::SetAutoEquip(0);
   ```

The DS3 `AutoEquip.cpp/.h` + `GameTypes.h` stay untouched/dead for v1 (don't try to port
the armor-id tables — those are post-v1 and ER should classify by `CATEGORY_PROTECTOR` +
sub-slot field, not hardcoded id lists).

## 6. Validation on Windows

1. Build client (sandbox can't compile it). Connect a seed with `auto_equip: true`,
   `auto_upgrade: true`: log shows `auto_equip: ENABLED`.
2. Receive / pick up a weapon → it appears equipped in RH1 at the auto-upgraded level;
   attack power, weight, and the held model all update (proves the clean call recalc'd).
3. Receive a second weapon → RH1 swaps to it (true UWYG, even if "worse").
4. **Load-Game stress**: receive a weapon, hard-reload the save mid-grant → no crash
   (the SEH + in-world gate hold).
5. Reconnect storm → no re-equip loop (the `last_received_index` gate holds).
6. Negative: `auto_equip: false` → no equipping; non-weapon receipts → ignored.

## 7. Reference: equip-slot map (from fm rando CharaInitParam)

thefifthmatt's randomizer (`SoulsRandomizers/RandomizerCommon/CharacterWriter.cs`) does
**bake-time** starting-loadout seeding by writing weapon ids into `CharaInitParam` slot
fields — it never makes a runtime equip call (no `ChrAsm`, no `GaItemHandle`, no hooks),
so it is **not** a blueprint for our runtime path and rules out any "edit a param"
shortcut for mid-run equipping. It IS a useful confirmation of slot semantics. The
`CharaInitParam` field names map to the armament slots as:

| CharaInit field      | Slot                          | v1?  |
|----------------------|-------------------------------|------|
| `equip_Wep_Right`    | **Right-hand armament 1 (RH1)** | **yes** |
| `equip_Subwep_Right` | Right-hand armament 2 (RH2)   | post |
| `equip_Subwep_Right3`| Right-hand armament 3 (RH3)   | post |
| `equip_Wep_Left`     | Left-hand armament 1 (LH1)    | post |
| `equip_Subwep_Left`  | Left-hand armament 2 (LH2)    | post |
| `equip_Subwep_Left3` | Left-hand armament 3 (LH3)    | post |
| `equip_Arrow` / `equip_Subarrow` | Arrow slots 1 / 2 | post |
| `equip_Bolt` / `equip_Subbolt`   | Bolt slots 1 / 2  | post |
| `equip_Helm/Armer/Gaunt/Leg`     | Armor head/chest/arms/legs | post |
| `equip_Accessory01..04`          | Talisman slots 1–4 | post |

v1 only needs `equip_Wep_Right` → **RH1**. Caveat: this names the *semantics*; the
runtime ChrAsm equip-slot **index** the equip function takes still must be confirmed
against the exe (§2), because the CharaInit field order is not guaranteed to equal the
live ChrAsm index.

**Licensing**: fm's randomizer is a known landmine for forks (`er-ecosystem-upstreams`).
The param field names and slot ordering above are facts and safe to reference; do **not**
copy any C# code or structure from that tree into the client.

## 8. Post-v1 backlog (out of scope now)

- Armor (`CATEGORY_PROTECTOR` → head/chest/arms/legs via the protector sub-slot field;
  the apworld option text already promises armor).
- Talismans (`CATEGORY_ACCESSORY` → next free talisman slot).
- Left-hand routing for shields/staves/bows; two-handing; ammo to arrow/bolt slots.
- "Equip-if-better" mode as an alternative to true UWYG.
- **Cross-track upgrade conversion (UWYG smoother — NOT decided).** Today auto_upgrade
  keeps `g_normalTarget` / `g_somberTarget` independent, so a received somber weapon
  arrives at +0 if you've only ever invested in the normal track (and vice versa). A
  UWYG run might feel smoother if the received weapon came in at the *equivalent* of your
  highest investment on the other track. Rough in-game equivalence: `somber ≈
  round(smithing × 10/25)`, i.e. smithing×0.4 (and the inverse ×2.5), clamped to the
  track cap. No precedent in fm's randomizer — his bake-time "cheat"
  (`CharacterWriter.cs`) only maxes each weapon to *its own* track cap (+25 / +10) with no
  cross-track mapping, which actually argues for keeping the tracks separate. Flagging as
  an option to consider, not a commitment.
