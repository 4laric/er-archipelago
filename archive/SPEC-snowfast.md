# SPEC — snowfast (Fast Mountaintops) as a default-on QoL pass

**Status:** spec only — implementation HELD pending go-ahead.
**Approach:** A — full C# port of thefifthmatt's `snowfast` into the fork baker as a default-on, toggleable pass.
**Owner of build/playtest:** Alaric (Windows). Claude writes, does not run.

---

## 0. What this is

`snowfast` is the **Convenience**-group option in Item & Enemy Randomizer (Nexus 428), label *"Add shortcuts in
Mountaintops for faster traversal."* Authoritative behavior (from the release's own
`diste/Messages/*.json` → `EldenForm_snowfast.explanation`):

> "edits the map in Mountaintops of the Giants to allow skipping large amounts of it. Adds several spirit
> springs for Torrent and adds warp gates between near Castle Sol and near Fire Giant. The shortcuts allow
> going from the Grand Lift of Rold to Fire Giant in around 2 minutes."

It is **logic-neutral**: it does not move items and does not change the Rold-Medallion / Great-Rune gate
into Mountaintops. It is purely map + asset + EMEVD surgery on overworld tiles. That makes it safe to ship
default-on.

## 1. Why a port is needed (not a binary diff / overlay)

The feature lives only in the newest closed binary (`Elden Ring Randomizer-428-v0-11-4-1763103112/.../EldenRingRandomizer.exe`,
.NET6 single-file bundle). It is **not** in thefifthmatt's public GitHub, nor in our fork. The supporting
helpers it calls (`AddOverworldMountJump`, `AddOverworldSendingGate`, `AddDerivativeAsset`,
`AddOverworldAsset`, `AddAssetModel`, `SetAssetName`, `NewPartName`, `AddInit`) were added in that newer
version and are **absent from our fork**. So approach A = port those helpers + replay the exact data.

Good news from the feasibility check:
- The underlying **SoulsFormats data model is already present** in our `SoulsFormats/.../MSBE/PointParam.cs`:
  `Region.MountJump` (RegionType 46, has `JumpHeight`), `Region.MountJumpFall` (52), plus
  `LockedMountJump`/`LockedMountJumpFall`. Asset `PartsParam.cs` has `DisableTorrent` and
  `AssetSfxParamRelativeID`. Nothing in SoulsFormats needs upgrading.
- `ParseMap` and the `EldenMaps` accessor already exist in the fork (`EldenCoordinator.cs`, `GameData.cs`).
- We already have close analogues of the MSB/EMEVD surgery in `RegionFogGates.cs` (region cloning,
  `GetUniqueEventId`, init-in-event-0, `WriteMSBs`/`WriteEmevds`) and `EnemyRandomizer.cs` (adding
  Parts + models). Reuse those patterns; do not invent new machinery.

Source of all constants below: IL of `EldenRingRandomizer.dll` method `EldenCommonPass`
(snowfast block, IL offsets ~2632–4163) + helpers rid 408/410/411. Extraction technique and the carved DLL
recipe are recorded in memory (`er-snowfast-feature`).

## 2. Helpers to reimplement

Signatures inferred from IL; match the fork's existing style (the `game`/`EldenMaps`/`WriteMSBs`/`Emevds`
fields already exist on the relevant class — same ones `RegionFogGates` uses).

### 2.1 `AddDerivativeAsset(string map, string nearName, string newModel, Vector3 pos, Vector3 rot)`
- Find an existing `Parts.Assets` asset whose name matches `nearName` in `EldenMaps[map]` (predicate
  `b__0`); throw "Missing asset {nearName} in {map}, needed to create …" if absent.
- `DeepCopy()` it, `SetAssetName(...)` (new unique part name via `NewPartName`), set `Position`,
  `Rotation`, `ModelName` (= `newModel`), `EntityID`; add to `Parts.Assets`; `AddAssetModel(...)` to
  register the model row; add `map` to `WriteMSBs`.

### 2.2 `AddOverworldAsset(string map, string modelName, …)` (used by 2.3)
- Lighter form of 2.1: place a fresh `Part.Asset` of `modelName` (e.g. `AEG099_510`) at a position;
  register model; return the asset so the caller can set `EntityID` etc.

### 2.3 `AddOverworldMountJump(string map, Vector3 pos, BoxDims dims, Vector3 rot, float jumpHeight, …)`
- `EldenMaps[map].Regions.MountJumps`: new `Region.MountJump` with `Shape` (a Box from `dims`),
  `UnkE08 = 255`, `MapID` (from `map`), `UnkS0C`, `Position = pos`, `Rotation = rot` (`GetValueOrDefault`),
  `JumpHeight = jumpHeight`, `UnkT04`. Add.
- Paired landing: new `Region.MountJumpFall` in `Regions.MountJumpFalls`, same Shape/UnkE08=255/MapID/UnkS0C,
  `Position = pos - offset`, `Rotation`. Add. (Engine pairs launch↔fall by proximity/shape.)
- Add `map` to `WriteMSBs`.

### 2.4 `AddOverworldSendingGate(uint entityId, MapBase srcBase, int srcAreaArg, string destMap, int destEntity, …)`
- `AddOverworldAsset(srcMap, "AEG099_510")` → set `EntityID = entityId` (the sending-gate model).
- `ParseMap(destMap)` → build an EMEVD **initializer** that calls common-func **`90005605`** (the
  sending-gate template) with the warp args (dest map block/index, `destEntity`, the source asset entity,
  flags). Emit via `AddInit` (mirror `RegionFogGates` init-in-event-0 pattern). The block in
  `EldenCommonPass` also references asset-activation event **`900005610`** wired through the derivative
  asset (2.5) with args `{2000, 900005610/900005610-entity, 100, 800}`.

### 2.5 Derivative-asset activation (inline in the data block, not a standalone helper)
- `AddDerivativeAsset("AEG099_090" context, "AEG022_020_1002", pos≈(416.6,30.3,-200), rot=(0,90,0))`,
  then `set_EntityID(802212030)`, `set_AssetSfxParamRelativeID(...)`, and append an instruction list to the
  found event's `Instructions` invoking **`900005610`** with `{2000, <entity>, 100, 800}`.

> All five reuse `game`, `EldenMaps`, `WriteMSBs`, `Emevds`, `WriteEmevds` already on the pass class.

## 3. Exact data block to replay (default-on)

Coordinates are `(X, Y, Z)`; shape dims are the box `(W, H, D)`; rotations as captured. Entries flagged
**[non-crawl]** are skipped when Dungeon-Crawl mode is active (mirror the binary's `crawl` branch — for us,
gate on the equivalent region-preset).

Spiritsprings — `AddOverworldMountJump`:

| Tile | Position | Box dims | Rot (captured) | Notes |
|---|---|---|---|---|
| m60_50_53_00 | (-150.735, 1562.571, 89.68) | (72, 10, 85) | (-12.105, 51.044, 0) | also removes 1 collision in this tile |
| m60_51_54_00 | (-16.127, 1694.095, -75.314) | (30, 10, 30) | (0, 10.587, 7.972) | |
| m60_51_56_00 | (-18.043, 1579.316, -92.892) | (30, 10, 30) | (0, 0, 0) | rotation defaulted (initobj, no rot passed) |
| m60_51_57_00 | (-0.156, 1597.957, 23.891) | (70, 15, 70) | (0, 0, 0) | **[non-crawl]** Castle Sol approach; rotation defaulted |
| m60_51_57_00 | (103.862, 1611.682, 71.715) | (54, 15, 60) | (0, 0, 4.945) | **[non-crawl]** |

**Five spiritsprings total** (the first three always; the two `m60_51_57` springs are skipped under
Dungeon-Crawl). The `crawl` test is `brtrue` past the entire `m60_51_57` group, so both 57-tile springs are
non-crawl; the warp gates below are added regardless of crawl.

Warp gates — `AddOverworldSendingGate` — a **bidirectional Castle Sol ↔ Fire Giant pair**. The gate's own
position/rotation is where the sending-gate asset is placed; it warps to `(destMap, destEntity)`:

| Gate | Entity | Placed in — pos / rot | Warps to map / entity |
|---|---|---|---|
| A (Castle Sol → Fire Giant) | 802212020 | m60_51_57_00 — (119.45, 1670.06, -48.398) / (0, -7.397, -2.999) | m60_52_53_00 / 1052530980 |
| B (Fire Giant → Castle Sol) | 802212021 | m60_52_53_00 — (-81.921, 1801.741, -38.394) / (0, -179.998, -8.119) | m60_51_57_00 / 1051570980 |

> Both use `EldenRingBase` with source area arg `2020`, model `AEG099_510`, and the EMEVD sending-gate
> common-func `90005605` (see §2.4). Gate A's placement was misread as a 6th spiritspring in the first
> draft — it is a gate, not a MountJump. Spiritsprings = 5; gates = 2.

Derivative asset (the visible warp structure / SFX, near the forge): clone `AEG022_020_1002` (sending-gate
model) near `AEG099_090`, pos ≈ (416.6, 30.3, -200), rot (0, 90, 0), `EntityID = 802212030`, set
`AssetSfxParamRelativeID`, activation via event `900005610` with args `{2000, <entity>, 100, 800}`.

Other edits:
- `m60_50_53_00`: `RemoveAll` matching collision predicate `b__53_3` (removes a wall that blocks a spring path).
- Collisions `h000200` / `h000110` (in the m34_14 / forge area): set `DisableTorrent` appropriately.
- Register `m34_14_00_00` into `WriteMSBs` and `WriteEmevds`.

> All MountJump/gate/asset values above are now fully resolved from IL — no remaining truncations.

## 4. Integration, option plumbing, mode gating

1. **Hook point:** `RandomizerCommon/ArchipelagoForm.cs` → `EldenCommonPass` (the fork already has this
   method; the binary checks `opt["snowfast"]` here). Add a `Snowfast(...)` call gated on the option.
2. **Option (default ON):** expose as a yaml/AP option (e.g. `mountaintops_shortcuts`, default `true`),
   threaded into the baker the same way other bake-side toggles are. Bake-side only — no apworld logic
   change, no slot-data, no client change. Keep an off switch for purists.
3. **Mode gating — required:** auto-disable when the Mountaintops overworld is sealed or deleted:
   - region-lock / bundle-lock seeds where Mountaintops tiles (m60_51_xx) are locked,
   - Oops-All-Legacy-Dungeons (open world deleted),
   - any preset that strips/seals m60.
   In those modes the spiritsprings/warps land in dead space. Skip the pass (or skip per-tile if the tile
   isn't live). Cross-ref `er-region-fusion`, `er-oops-all-legacy-dungeons`, `er-fogmod-region-lock-direction`.
4. **Dungeon-Crawl branch:** the three `m60_51_57` springs are `[non-crawl]`; replicate that condition.

## 5. Verification plan

- **Pre-build static checks:** confirm common-func templates `90005605` and `900005610` exist in the ER
  common emevd the fork ships (if not, port the templates first); confirm entity IDs `802212020/021/030`
  and the dest entities `1052530980` / `1051570980` are unused; confirm all six tiles + `m34_14` resolve in
  `EldenMaps`. (Task #6.)
- **Build:** Release (Archipelago) on Windows per `er-randomizer-build-recipe`.
- **Playtest (Task #7):** Grand Lift of Rold → Fire Giant in ~2 min; each spiritspring launches Torrent and
  the paired fall lands safely; both sending gates warp and are repeatable; no `?EventTextForMap?` banner
  (clean redeploy); Torrent enable/disable correct around the forge.
- **Coexistence:** run with enemy rando ON and with a region-lock seed where Mountaintops is unlocked —
  confirm snowfast MSB/region additions merge with (don't clobber) enemy placements and region edits on
  m60_51 tiles (this is the whole reason for A over a static overlay).

## 6. Out of scope / deferred
- DLC (m61) traversal shortcuts — snowfast is base-game Mountaintops only.
- `LockedMountJump`/`LockedMountJumpFall` variants (seal-on-flag springs) — not used by snowfast; possible
  future tie-in with region-lock reveal flags.

## Sources
- `EldenRingRandomizer.dll` (carved from the v0.11.4.1 single-file bundle): `EldenCommonPass` snowfast block;
  helpers `AddDerivativeAsset`/`AddOverworldMountJump`/`AddOverworldSendingGate` (rid 408/410/411).
- Release `diste/Messages/de.json` → `EldenForm_snowfast` explanation text.
- Fork: `SoulsFormats/.../MSBE/PointParam.cs` (MountJump/MountJumpFall), `PartsParam.cs`
  (DisableTorrent/AssetSfxParamRelativeID), `RandomizerCommon/RegionFogGates.cs`, `EnemyRandomizer.cs`,
  `ArchipelagoForm.cs` (`EldenCommonPass`).
- Memory: `er-snowfast-feature`.
