# SPEC — region-lock fog walls (FogMod-derived)

Referenced by `SoulsRandomizers/RandomizerCommon/RegionFogGates.cs` header. This is the "hard wall"
alternative to the current play-region KICK (client polls FieldArea id, sets `KICK_FLAG`, a baked
COMMON event warps/kills). FogMod proves a **real, baked, flag-gated impassable wall** is doable from
MSB + EMEVD + param edits alone — no map editor, no client poll.

Pulled from `thefifthmatt/FogMod` (DS1/DS3 source, public) + the ER Fog Gate Randomizer (Nexus 3295,
binary-only). Same author/lineage as our SoulsRandomizers base.

---

## 1. What FogMod gives us (and what it doesn't)

**Open-sourced (FogMod repo, DS1/DS3):** the *schema* and the *technique*.
- `FogMod/AnnotationData.cs` — the data model.
- `FogMod/GameDataWriter3.cs` — the DS3 writer; the MSB/EMEVD/param edits we'd mirror for ER.
- `fogdist/fog.txt` — the DS3 fog catalog (read in full; ER's is structurally identical).

**NOT open-sourced:** the ER fog-gate **catalog** (asset IDs, MSB names, per-side flags). The ER Fog
Gate Randomizer ships only as a binary on Nexus 3295. Its data is a plain-text `fogdist/fog.txt`
(plus `events.txt`, `locations.txt`, `Names/`) inside the download, in the SAME YAML schema as the
DS3 file below — so it's **extractable from a local install**, just not on GitHub. That extraction is
the one manual step; everything else is portable from the open source.

**Licensing caveat (standing landmine):** thefifthmatt forks carry a licensing risk we already
flagged. Lift the *technique* (our own code), and treat the extracted `fog.txt` as data we read at
bake time from the user's own mod install — do not redistribute his files in our repo.

---

## 2. The FogMod data schema (from `AnnotationData.cs` + `fog.txt`)

A fog gate is an `Entrance`:

```yaml
- Name: o000400_0000     # MSB Part.Object name
  ID: 3001780            # EntityID of the fog object in the MSB
  Area: highwall
  ASide: { Area: highwall_postdancer }   # one logical side
  BSide: { Area: highwall_garden }       # the other
  Tags: pvp              # <-- THE MULTIPLAYER-ONLY BARRIER ("walls off the open world")
```

Tags that matter:
- `pvp` — the **multiplayer-only confinement barriers**. These are the "co-op fog walls" — ordinary
  MSB objects with an EntityID, addressable like any other. This is the thing you remembered.
- `boss` — boss mist (has `DefeatFlag` / `TrapFlag` / `BossTrigger`).
- `small` / `trivial` — area nodes, not walls.

Each `Side` (`AnnotationData.Side`) carries the levers we need: `Flag`, `EntryFlag`, `WarpFlag`,
`TrapFlag`, `Col` (collision name), `ActionRegion`, `Cutscene`, `CustomWarp`.

## 3. The technique (from `GameDataWriter3.cs`) — three layers

1. **MSB** — the fog object is `msb.Parts.Objects.Find(o => o.Name == e.Name)`. Collision is the
   `CollisionName` field on that object (`fog.CollisionName = null` makes a gate *passable*; keeping
   a collision makes it a *wall*). The fog visual is a SFX driven by a `FogEdit` (`CreateSfx`, `Sfx`).
   → For us: keep/clone a fog object **with** its collision at the chokepoint = a real impassable wall.
2. **EMEVD** — a `common_func`-style template that, per the writer's own comment, does:
   *"show sfx, set trigger flag on entering region, press A on fog gate and warp to region."* Gate
   logic lives here via `EntryFlag` / `WarpFlag`. → For us: condition the wall's existence on our
   open flag (END IF flag ON), exactly like the existing per-border event in `RegionFogGates.Apply`.
3. **`PlayRegionParam`** — `GameDataWriter3.cs:450` "Rewrite collision flags in PlayRegionParam, read
   from base params, write to modified params." This is the **multiplayer play-region boundary param**
   — the same play-region space our `areaLockFlags` (FieldArea id ranges) already keys off. FogMod
   edits it so confinement matches the new connectivity. → This is the deepest hook and the most
   promising: it's the actual vanilla machinery for "you can't leave this region."

Key realization: **both systems already revolve around PlayRegion IDs.** Our `areaLockFlags` =
`(lo, hi, open_flag)` over FieldArea ids; FogMod's deepest layer rewrites `PlayRegionParam` collision
flags. They're the same coordinate space — which is why FogMod is a natural fit, not a bolt-on.

---

## 4. Mapping onto our region-lock data

Our side (`map_region_data.py`, `__init__.py` `build_region_lock_slot_data`):

| Our concept | Value / source | FogMod analogue |
|---|---|---|
| open-state flag | `lockOpenFlags[lock]`, base `OPEN_FLAG_BASE = 76971` | `Side.Flag` / `EntryFlag` (gate-open flag) |
| locked-region detection | `areaLockFlags = [lo,hi,open_flag]` over FieldArea id | `PlayRegionParam` collision-flag rewrite |
| open-on-receipt | client sets `lockRevealFlags` (62xxx) + open flag | gate becomes passable when flag set |
| chokepoint geometry | `RegionFogGates.Border` (TrigPos/Box per tile) | MSB fog `Object` position + its `Col` |
| enforcement event | baked COMMON/per-tile EMEVD (warp/kill) | FogMod's per-gate `common_func` template |

Concrete swap (replaces the client-poll KICK with a baked wall):

1. For each `Border` (extend `RegionFogGates.Borders` to one per locked region), place a fog
   **Object + Collision** at the chokepoint instead of an invisible area trigger. Reuse an existing
   ER fog asset's model/SFX (pull the asset id from the extracted ER `fog.txt`; pick a `pvp`-tagged
   one near that border so the visual reads as a multiplayer-style wall).
2. EMEVD per border, gated on `lockOpenFlags[lock]` (≥ 76971, already validated free): while the flag
   is OFF the collision is enabled (wall present); on flag ON, `EndIfEventFlag(openFlag)` tears it
   down for good — same control flow already in `Apply()`.
3. Client change: nothing new to *poll*. The client already sets the open flag on lock receipt via
   `lockRevealFlags` — that one flag-set now removes a physical wall instead of stopping a kick loop.
   The `areaLockFlags` poll + `KICK_FLAG` path can be retired (or kept as a belt-and-suspenders
   backstop for regions where we can't site a clean chokepoint, e.g. open overworld borders).

Why this is better than the current KICK: no per-tick FieldArea polling, no silent teleport that
"feels like a bug" (the very reason `SEALED_MSG_TEXT` was added), and it's all in the bake where you
already decided enforcement belongs.

---

## 5. What to lift vs reimplement

- **Reimplement (ours):** the MSB-object-with-collision placement + the flag-gated EMEVD. We already
  have 90% of this in `RegionFogGates.cs` (region cloning, `GetUniqueEventId`, init-in-event-0,
  WriteMSBs/WriteEmevds). Swap "clone Region.Other trigger" → "clone/place a fog `Part.Object` +
  keep its Collision," and "warp/kill on enter" → "collision present while flag OFF."
- **Lift as reference only (DS3 → ER):** `GameDataWriter3.cs` lines ~195-330 (per-side fog handling),
  ~440-470 (PlayRegionParam rewrite — port to ER `PlayRegionParam` via Paramdex), ~1119+ (`FogEdit`
  SFX creation).
- **Extract as data (local mod install):** ER `fogdist/fog.txt` for the asset-id catalog + which
  gates are `pvp` vs `boss`.

## 6. Open questions / TODO before first bake

1. **Get the ER catalog.** Locate the Nexus 3295 install (`fogdist/fog.txt`) on the Windows box and
   dump the `pvp`/`boss` entries with their `ID` + `Area`. (Confirm whether you already have it; the
   workspace only has the *item/enemy* randomizer 428.)
2. **ER `PlayRegionParam` layout** — confirm the field that FogMod's "collision flags" map to in ER
   (Paramdex `PlayRegionParam`). Decide whether to go full param-rewrite (closest to vanilla coop) or
   stay with MSB-collision + EMEVD (simpler, no param risk).
3. **Asset reuse** — can a `pvp` fog object's collision be left always-on in single-player, or does
   vanilla gate it on netplay state? If the latter, we site our own collision and only borrow the SFX.
4. **Chokepoint siting** — overworld borders (Limgrave↔Weeping bridge already scoped) are clean;
   open borders may still need the KICK backstop. Enumerate which regions have a true chokepoint.
5. **DLC (m61)** — separate map layer; defer (the DLC entry already has its own `DLC_ENTRY_FLAG` warp).

---

## Sources
- `thefifthmatt/FogMod` — `AnnotationData.cs`, `GameDataWriter3.cs`, `fogdist/fog.txt` (DS3).
- Elden Ring Fog Gate Randomizer — Nexus mods/3295 (binary; ER `fog.txt` same schema).
- Seamless Co-op — Nexus mods/510 (reference for the multiplayer-barrier set).
- Ours — `RegionFogGates.cs`, `map_region_data.py`, `__init__.py` `build_region_lock_slot_data`.
