// ============================================================================
// DRAFT — fog-wall enforcement path for RegionFogGates.cs  (2026-06-17)
// ----------------------------------------------------------------------------
// Drop-in for RegionFogGates: a third enforcement mode that places a REAL,
// baked, flag-gated impassable fog wall at a region border, instead of the
// invisible-trigger warp/kill (DIAG) or the client-poll KICK.
//
// Mode precedence in Apply():  USE_FOG_WALL  >  USE_PLAY_REGION_KICK  >  per-border DIAG.
//
// EVERYTHING marked  >>> WITCHY <<<  is a value to read off an unpacked vanilla
// fog-wall tile (MSB for the Asset/Collision fields, EMEVD for the toggle
// opcodes). Until those are filled, this path no-ops with a clear log line.
// ============================================================================

// ---- mode switch (put alongside USE_PLAY_REGION_KICK) ----------------------
private const bool USE_FOG_WALL = false;   // flip on once the WITCHY constants are filled

// ---- asset/sfx constants — CONFIRMED from m10_00_00_00 (Stormveil) dump -----
// FACTS established 2026-06-17 by unpacking m10_00_00_00.msb:
//   * Fog walls are Part.Asset with model AEG099_xxx. The MODEL *is* the fog
//     visual — AssetSfxParamRelativeID = -1 on every one (no separate SFX).
//   * Impassability comes from a PAIRED Collision part (an hkx hull h0xxxx,
//     its own model + EntityID, HitFilterID=Standard) linked via the asset's
//     UnkPartNames[0]. e.g. AEG099_052_9000 (ent 10001106) -> h014000 (ent 10003840).
//   * Stormveil walls with a collision hull: AEG099_052/053/090_9004/423/635.
//   * EntityID namespace here is 10001xxx (m10_00 = "10" "00" "1xxx").
// AEG099 is a GLOBAL shared asset (loaded in every map), so registering the
// model name in a target tile's ModelParam is enough — no per-map asset files.
private const string FOGWALL_ASSET_MODEL = "AEG099_052";  // has a wall collision in vanilla; pick size per border
private const short  FOGWALL_SFX_RELATIVE = -1;           // model is the fog; no SFX param
private static readonly Vector3 FOGWALL_SCALE = new Vector3(1f, 1f, 1f);  // tune per border

// THE ONE REAL COMPLICATION (decided by this constant):
//   The vanilla wall is an hkx Collision hull (h014000-style geometry). hkx hulls
//   are baked geometry — they do NOT clone cleanly into a different tile (the
//   target map needs the hkx model + a Collision part referencing it). Two paths:
//
//   false = HYBRID (recommended first): place ONLY the AEG099 Asset as a VISUAL
//           fog wall at the border, and keep the existing play-region KICK /
//           trigger as the actual block. Turns the "mystery teleport" into
//           "you see a wall and bounce off it" — the legibility win, low risk,
//           no hkx. Player may clip a step into the fog before the kick fires;
//           a generous trigger box just in front hides that.
//   true  = HARD WALL: also bring an hkx collision hull into the tile and link it
//           in UnkPartNames[0]. Genuinely fiddly (hkx model port); do only if the
//           hybrid's slight overshoot proves unacceptable in playtest.
private const bool FOGWALL_NEEDS_COLLISION = false;       // start HYBRID

// ---- EMEVD toggle opcode — CONFIRMED from er-common.emedf.json ---------------
// 2005[03] "Change Asset Enable State"  args: (Target Asset Entity ID : u32, State : u8)
//   State enum "Disabled/Enabled": 0 = Disabled (wall GONE), 1 = Enabled (wall PRESENT).
// This is DarkScript's EnableAsset/DisableAsset — the exact primitive the vanilla Godrick
// event uses (DisableAsset(10001870); EnableAsset(10001871); ...). Disabling the asset also
// drops its linked collision (UnkPartNames[0]) — VERIFY in playtest, but that's the vanilla
// behavior. No SFX instruction needed: the AEG099 model IS the fog (AssetSfxParamRelativeID -1).

// ===========================================================================
// Border gets two extra fields for the wall (add to the existing Border class):
//   public Vector3 WallRot;     // Y-yaw to face the wall across the chokepoint
//   public uint    WallEntity;  // free asset EntityID in Map (reuse BaseEntity+2)
// TrigPos is reused as the wall position; ReturnPos is unused in this mode.
// ===========================================================================

// Call this from inside Apply(), BEFORE the USE_PLAY_REGION_KICK block:
private static bool ApplyFogWalls(GameData game, IReadOnlyDictionary<string, uint> regionOpenFlags,
                                  Action<string> Log)
{
    if (!USE_FOG_WALL) return false;
    if (FOGWALL_ASSET_MODEL.Contains("XXX"))
    {
        Log("RegionFogGates[fogwall]: FOGWALL_ASSET_MODEL still stubbed — fill the WITCHY constants. No wall authored.");
        return true;  // handled (intentional no-op) so we don't fall through to KICK
    }

    foreach (Border b in Borders)
    {
        if (!regionOpenFlags.TryGetValue(b.DestLockItem, out uint openFlag))
        { Log($"RegionFogGates[fogwall]: no open flag for '{b.DestLockItem}', skip {b.Name}"); continue; }
        if (openFlag < 50_000_000)
        { Log($"RegionFogGates[fogwall]: open flag {openFlag} below 50M floor, refuse {b.Name}"); continue; }
        if (!(game.Maps.TryGetValue(b.Map, out IMsb imsb) && imsb is MSBE msb))
        { Log($"RegionFogGates[fogwall]: MSB {b.Map} not loaded, skip {b.Name}"); continue; }
        if (!game.Emevds.TryGetValue(b.Map, out EMEVD emevd))
        { Log($"RegionFogGates[fogwall]: emevd {b.Map} not loaded, skip {b.Name}"); continue; }

        // 1) ensure the asset MODEL exists in this tile's ModelParam ----------
        if (!msb.Models.Assets.Any(m => m.Name == FOGWALL_ASSET_MODEL))
        {
            // Clone a model row if any asset model exists (inherits valid fields), else construct.
            var tmplModel = msb.Models.Assets.FirstOrDefault();
            MSBE.Model.Asset model = tmplModel != null
                ? (MSBE.Model.Asset)tmplModel.DeepCopy()
                : new MSBE.Model.Asset();
            model.Name = FOGWALL_ASSET_MODEL;
            // >>> WITCHY: confirm SibPath convention for assets, or leave null and let the writer fill.
            msb.Models.Assets.Add(model);
            Log($"RegionFogGates[fogwall]: added model {FOGWALL_ASSET_MODEL} to {b.Map}");
        }

        // 2) place the fog Asset at the chokepoint ---------------------------
        uint wallEntity = NextFreePartEntity(msb, b.BaseEntity + 2);
        var tmplAsset = msb.Parts.Assets.FirstOrDefault();          // clone to inherit valid Unk structs
        MSBE.Part.Asset wall = tmplAsset != null
            ? (MSBE.Part.Asset)tmplAsset.DeepCopy()
            : new MSBE.Part.Asset();
        wall.Name      = $"AP FogWall {b.Name}";
        wall.ModelName = FOGWALL_ASSET_MODEL;
        wall.Position  = b.TrigPos;
        wall.Rotation  = b.WallRot;
        wall.Scale     = FOGWALL_SCALE;
        wall.EntityID  = wallEntity;
        wall.AssetSfxParamRelativeID = FOGWALL_SFX_RELATIVE;
        wall.MapStudioLayer = 0;
        // >>> WITCHY: clear any UnkPartNames / UnkT54PartName that point at parts not in this tile,
        //             or the writer will throw on a dangling name reference.
        msb.Parts.Assets.Add(wall);

        // 2b) optional invisible collision block -----------------------------
        if (FOGWALL_NEEDS_COLLISION)
        {
            // >>> WITCHY: collisions need an hkx Model.Collision; cloning across tiles is the risky
            //             part. Prefer reusing the asset's own collision (FOGWALL_NEEDS_COLLISION=false).
            Log($"RegionFogGates[fogwall]: TODO collision part for {b.Name} (needs hkx model plan)");
        }

        game.WriteMSBs.Add(b.Map);

        // 3) flag-gated EMEVD: wall present while openFlag OFF; gone once ON --
        int eventId = game.GetUniqueEventId();
        var ev  = new EMEVD.Event(eventId, EMEVD.Event.RestBehaviorType.Default);
        var ins = ev.Instructions;

        // If the region is ALREADY open at load, just disable the wall and end.
        //   END IF Event Flag(End, ON, type 0, openFlag)  (1003,2) — proven in this file.
        // Otherwise show the wall, then wait for the flag, then tear it down.
        AddWallEnable (ins, wallEntity);                                   // >>> WITCHY opcodes
        ins.Add(new EMEVD.Instruction(3, 0, new List<object> { (sbyte)0, (byte)1, (byte)0, openFlag })); // IF flag ON
        AddWallDisable(ins, wallEntity);                                   // >>> WITCHY opcodes
        ins.Add(new EMEVD.Instruction(1000, 4, new List<object> { (byte)0 }));  // End Unconditionally(End) — one-shot, do NOT restart

        emevd.Events.Add(ev);
        if (emevd.Events.Count == 0 || emevd.Events[0].ID != 0)
            emevd.Events.Insert(0, new EMEVD.Event(0, EMEVD.Event.RestBehaviorType.Default));
        emevd.Events[0].Instructions.Add(new EMEVD.Instruction(2000, 0, new List<object> { (int)0, (uint)eventId, (uint)0 }));
        game.WriteEmevds.Add(b.Map);

        Log($"RegionFogGates[fogwall]: AUTHORED wall {b.Name} -> asset {wallEntity}, event {eventId}, " +
            $"openFlag {openFlag}, model {FOGWALL_ASSET_MODEL} in {b.Map}");
    }
    return true;
}

// Smallest part EntityID >= start not used by any part in the map.
private static uint NextFreePartEntity(MSBE msb, uint start)
{
    var used = new HashSet<uint>();
    foreach (var p in msb.Parts.GetEntries()) used.Add(p.EntityID);
    uint id = start; while (used.Contains(id)) id++; return id;
}

// ---- real opcodes (er-common.emedf.json 2005[03]) --------------------------
// Change Asset Enable State (assetEntity:u32, state:u8 0=Disabled/1=Enabled).
private static void AddWallEnable(List<EMEVD.Instruction> ins, uint assetEntity)
    => ins.Add(new EMEVD.Instruction(2005, 3, new List<object> { (uint)assetEntity, (byte)1 }));  // wall ON
private static void AddWallDisable(List<EMEVD.Instruction> ins, uint assetEntity)
    => ins.Add(new EMEVD.Instruction(2005, 3, new List<object> { (uint)assetEntity, (byte)0 }));  // wall OFF
