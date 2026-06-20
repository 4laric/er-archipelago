# SPEC: Custom Archipelago icon for synthetic items

Status: IN PROGRESS — chosen approach = **override the telescope texture** (decided with
Alaric, 2026-06-14). Implemented as a one-time WitchyBND edit of the icon bundle that the
deploy step re-ships; the remaining steps need the game files and run on Windows.

Current behavior: all synthetic AP items (foreign items, own-item vouchers, lock tokens)
borrow the Telescope's icon, resolved from params at bake time (PermutationWriter
AddSyntheticItem). Goal: replace with the actual Archipelago logo (the six-circle
flower) so AP items are unmistakable in shops and inventory.

## CHOSEN DESIGN (override the telescope texture — no randomizer code change)

Instead of authoring a new icon id, override the *texture* the telescope's `iconId`
already points to. Every synthetic item borrows that same icon id, so swapping the texture
rebrands all AP items at once with **no change to `AddSyntheticItem`** and no new param id.
Accepted tradeoff: the real Telescope key item shows the flower too.

**Mechanism reality check (learned 2026-06-14):** the icon lives inside
`menu/hi/00_solo.tpfbnd.dcx`, which is a **BND4 bundle** of one tiny TPF per icon
(`MENU_Knowledge_#####.tpf`). `MiscSetup.InjectUncompressed` only handles bare
single-`.tpf.dcx` files (it globs `*.tpf.dcx` and does `TPF.Read`), NOT tpf**bnd** bundles
— so it cannot do this. Hence a dedicated BND-aware bake step (Alaric asked for full
automation rather than a hand-edit, 2026-06-14).

### What's already done in the repo (Cowork, 2026-06-14)

1. **`MiscSetup.InjectApItemIcon(game)`** (new) — ER-only bake step, called from the AP
   path right after `InjectUncompressed` (`ArchipelagoForm.cs`). It reads the vanilla
   `menu/hi/00_solo.tpfbnd.dcx` from the UXM-unpacked game root, `BND4.Read`s it, finds the
   `MENU_Knowledge_<telescope iconId>` TPF entry (telescope iconId pulled from
   `EquipParamGoods 2040`, matched by integer so zero-padding doesn't matter), swaps that
   TPF's texture **bytes** with the committed flower DDS (keeping the TPF format byte;
   SoulsFormats re-derives Type/Mipmaps from the new DDS for PC), and writes the loose
   bundle to `menu\hi\00_solo.tpfbnd.dcx` in the bake output dir. Idempotent; no-ops
   cleanly if the game isn't UXM-unpacked or the flower file is missing.
2. It reads the flower from **`diste\Archipelago\ap_telescope_icon.dds`**. When that file is
   absent, it dumps the vanilla telescope DDS to `diste\Archipelago\_telescope_icon_dump.dds`
   and logs how to match it — so producing a correctly-formatted flower needs only `texconv`
   (no WitchyBND, no bundle unpacking).
3. `build.ps1 -Deploy` now copies `menu/` into the game root (added to the deploy dir list,
   alongside event/msg/script/map).
4. Assets staged at `SoulsRandomizers/diste/Archipelago/`: `ap_flower_source_512.png`
   (texconv input, from `Archipelago/data/icon.png`), `ap_flower_candidate_BC3_256.dds`
   (BC3 fallback), and a `README.md` with the full step-by-step.

NOT yet built/tested — the randomizer only compiles on Windows. Watch for: `BND4.Read`
handling the `.dcx` wrapper and `bnd.Write` preserving it (confirmed in SoulsFormats:
`BND4 : SoulsFile<BND4>`, which stores/re-applies `Compression`); the binder entry names
(`bf.Name`) being parseable as `MENU_Knowledge_#####`; and the flower DDS format matching
the telescope's.

### Remaining one-time steps (Windows — full commands in diste/Archipelago/README.md)

- Build the randomizer; `.\build.ps1 -Bake` once → grab `_telescope_icon_dump.dds`.
- `texconv -info` it; encode the flower to the same format/size; save as
  `ap_telescope_icon.dds` in `diste\Archipelago\`.
- `.\build.ps1 -Bake -Deploy`; in-game check shop list, inventory grid, pickup popup,
  low-res item-compare.

### Why not a dedicated icon id

The clean-separation alternative (below) keeps the real telescope unchanged but needs the
bake step to *add* a new TPF/texture to the bundle plus a survey for a free icon id and an
`AddSyntheticItem` edit — more moving parts. Kept as a future option; original design notes
preserved below.

---

## ALTERNATIVE (future): dedicated Archipelago icon id

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
