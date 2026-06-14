# SPEC: Custom Archipelago icon for synthetic items

Status: FUTURE PROJECT, not started. (Alaric, 2026-06-11)
Current behavior: all synthetic AP items (foreign items, own-item vouchers, lock tokens)
borrow the Telescope's icon, resolved from params at bake time (PermutationWriter
AddSyntheticItem). Goal: replace with the actual Archipelago logo (the six-circle
flower) so AP items are unmistakable in shops and inventory.

## How ER icons work (vs DS3's atlas pages)

ER stores item icons one-texture-per-icon inside menu TPF bundles:
`menu/hi/00_solo.tpfbnd.dcx` (and a `menu/lo/` low-res sibling), each entry a tiny TPF
named by icon id (`MENU_Knowledge_#####`). Param rows reference icons by numeric
`iconId` (u16-sized field — VERIFY against the def; id must fit). This is why ER icon
modding is much easier than DS3: no atlas repacking or layout files — just insert one
more TPF entry into the bnd.

## Design

1. **Asset (one-time, offline):**
   - Recreate the AP logo on TRANSPARENT background (the reference image has solid
     black; vanilla icon art is the object alone on alpha — the UI draws the frame).
   - Author at 1024x1024, downscale to the dimensions of a sibling goods icon (inspect
     one — likely 160x160 hi / smaller lo).
   - Encode DDS matching a sibling's exact format (expect BC7_UNORM with mips; copy
     whatever a vanilla `MENU_Knowledge_*` entry uses, including TPF format/flag bytes).
   - COMMIT the finished `.dds` (or fully wrapped `.tpf`) under
     `SoulsRandomizers/diste/Archipelago/` so the bake never needs an encoder at
     runtime. Tooling for the one-time encode: texconv (DirectXTex) or Paint.NET BC7.

2. **Pick an icon id (one-time):**
   - Scan all `iconId` fields across EquipParam{Goods,Weapon,Protector,Accessory,Gem}
     AND the existing `MENU_Knowledge` entries in 00_solo; choose a comfortably free id
     (suggest something in a high unused band; must fit the param field width).
   - Define as a constant: `public const uint ApIconId = <chosen>;`

3. **Bake/deploy step (small code):**
   - In GameData.SaveEldenRing (or a dedicated step in the AP path): open the
     UXM-unpacked `menu/hi/00_solo.tpfbnd.dcx` (game root — same place the deploy
     reads/writes other overrides), insert/replace the `MENU_Knowledge_<ApIconId>`
     entry with the committed TPF bytes, write to the output `menu/hi/` dir. Repeat for
     `menu/lo/` if sibling icons ship a lo variant.
   - BND4 entry details (ID numbering, name/path format) must mirror an existing
     sibling entry exactly — copy-modify, don't construct from scratch.
   - build.ps1 -Deploy: add `menu` to the deployed dirs list.

4. **Wire-up (trivial):**
   - PermutationWriter's telescope-borrow branch returns `ApIconId` instead, with the
     telescope read as FALLBACK if the menu bnd step is disabled/missing (keep the
     param-derived path so a bad icon never ships an invalid id again).

## Gotchas

- **regulation-only re-bakes:** the icon lives in menu files, not regulation.bin —
  deploy must ship `menu/` or items fall back to the empty ICON frame. The fallback
  ordering above means: only switch ids to ApIconId when the menu output was written.
- **UXM root:** we read the vanilla 00_solo from the unpacked game root; if the user
  re-verifies/Steam-repairs, the unpacked file may revert — re-deploy fixes it.
- **Seamless/other UI mods** that also edit 00_solo will conflict (last write wins);
  out of scope, note in README.
- **Logo rights:** the AP logo belongs to the Archipelago project (open-source
  community, MIT-licensed repo). Fine for a personal fork; if this ever ships publicly,
  ask in the AP Discord about logo-use norms like every other AP world does.

## Work items

1. Asset: transparent-bg AP logo → DDS matching sibling format; commit under diste/.
2. Survey free icon ids + sibling TPF format details; pin constants.
3. Implement the 00_solo insert step + deploy `menu/`.
4. Switch AddSyntheticItem to ApIconId with telescope fallback.
5. In-game check: shop list, inventory grid, pickup popup, low-res contexts.

Effort: an evening; 80% of it is the one-time asset/format archaeology in steps 1-2.
