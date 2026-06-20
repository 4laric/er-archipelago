# SPEC — Godrick fog wall (skip-proof, step 2)

Goal: make the Godrick Lock physically enforced — a real impassable fog wall on the approach to
Godrick that drops when the player receives Godrick Lock. Pairs with step 1 (the open flag).

## What's already done
- **Step 1 (apworld):** `patch_godrick_fogflag.py` mints **open flag 76998** for `Godrick Lock`
  (godrick-scoped; emitted in `regionOpenFlags`, NOT in `areaLockFlags`, so no KICK / no non-godrick
  effect). The client already sets a lock's open flag on receipt by item name
  (`ArchipelagoInterface.cpp` `regionOpenFlags` path), so receiving Godrick Lock will set 76998.
- **Breakthrough facts (m10_00 = Stormveil, Godrick's own map):** fog walls are `Part.Asset` model
  `AEG099_xxx` (the model *is* the fog; `AssetSfxParamRelativeID = -1`); impassability is a paired
  hkx collision hull linked via `UnkPartNames[0]`; toggle = `2005[3] Change Asset Enable State`
  (0 = gone, 1 = present), and disabling the asset drops its linked collision. This is the same
  primitive the vanilla Godrick fight uses (`DisableAsset`/`EnableAsset`).

## Why REUSE beats place-new here
hkx collision hulls don't clone to new coordinates — that's why the generic `RegionFogGates`
fog-wall path defaults to HYBRID (visual + KICK). But Godrick is **inside m10_00**, where fog walls
**with collision already exist**. So instead of placing a new asset (and porting an hkx hull), we
**gate an existing in-tile wall's enable-state** on flag 76998. No MSB part added, no hkx move — just
one EMEVD event. This is the cheap hard wall.

## Pick the approach wall (your geography call)
The 6 Stormveil fog walls that already carry an EntityID (directly addressable; the other 9 have
EntityID 0 and would need one assigned):

| Asset | Entity | Pos (X, Y, Z) | Yaw | Collision |
|---|---|---|---|---|
| AEG099_052_9000 | 10001106 | (-263.1, 77.9, 348.0) | 165   | h014000 |
| AEG099_053_9000 | 10001104 | (-221.4, 66.8, 209.4) | -70   | h013500 |
| AEG099_053_9002 | 10001102 | (-168.6, 34.0, 54.2)  | -25   | h008700 |
| AEG099_090_9004 | 10001740 | (-241.2, 14.0, 100.5) | -80   | h012500 |
| AEG099_423_9000 | 10001730 | (-187.7, 73.2, 211.9) | 0     | h010200 |
| AEG099_635_9000 | 10001698 | (-242.4, 66.4, 210.3) | -77   | h008000 |

Choose the one that sits on the **Liftside Chamber → Secluded Cell (Godrick) approach** — i.e. the
chokepoint a player must cross to reach the boss fog. Confirm in-game it's otherwise inert (not a
wall vanilla needs for some other progression) before gating it. Two checks to make on your side:
1. Is the chosen wall normally **enabled** in vanilla at that spot? (If yes, our event just keeps it
   enabled until unlock — clean. If vanilla disables it after some event, our event would fight that.)
2. Does disabling it actually drop the linked collision (so the player can pass)? (Breakthrough says
   yes; verify.)

If none of the 6 sits exactly at the approach, fall back to: pick one of the 9 zero-entity walls
there, assign it a free m10_00 entity (10001xxx namespace) via an MSB edit, then gate that — still no
hkx move.

## The EMEVD event (reuse variant) — drop into RegionFogGates
Author once when `regionOpenFlags` contains `Godrick Lock` (auto-scopes to godrick seeds). Replace
`WALL_ENTITY` with the chosen entity above.

```csharp
// Godrick fog wall: keep the wall present until Godrick Lock (flag 76998) is received, then drop it.
const uint GODRICK_WALL_ENTITY = 10001106;   // <-- the approach wall you picked
if (regionOpenFlags.TryGetValue("Godrick Lock", out uint godrickFlag))
{
    int ev = game.GetUniqueEventId();
    var e  = new EMEVD.Event(ev, EMEVD.Event.RestBehaviorType.Default);
    var k  = e.Instructions;
    k.Add(new EMEVD.Instruction(2005, 3, new List<object> { (uint)GODRICK_WALL_ENTITY, (byte)1 }));  // wall ON at load
    k.Add(new EMEVD.Instruction(3, 0, new List<object> { (sbyte)0, (byte)1, (byte)0, godrickFlag })); // IF flag 76998 ON
    k.Add(new EMEVD.Instruction(2005, 3, new List<object> { (uint)GODRICK_WALL_ENTITY, (byte)0 }));  // wall OFF (drops collision)
    k.Add(new EMEVD.Instruction(1000, 4, new List<object> { (byte)0 }));                              // End (one-shot, no restart)
    EMEVD m10 = game.Emevds["m10_00_00_00"];
    m10.Events.Add(e);
    if (m10.Events.Count == 0 || m10.Events[0].ID != 0)
        m10.Events.Insert(0, new EMEVD.Event(0, EMEVD.Event.RestBehaviorType.Default));
    m10.Events[0].Instructions.Add(new EMEVD.Instruction(2000, 0, new List<object> { (int)0, (uint)ev, (uint)0 }));
    game.WriteEmevds.Add("m10_00_00_00");
    Log($"RegionFogGates[godrick]: wall {GODRICK_WALL_ENTITY} gated on flag {godrickFlag} in m10_00_00_00");
}
```

## Open items
1. **Which entity** is the approach wall (table above) — your in-game pick.
2. **Enabled-at-load assumption** — if vanilla starts that wall disabled, the `2005[3] ...,1` at load
   forces it on; confirm that's the desired look (a fresh fog plane appears) and doesn't collide with
   a vanilla event that also drives it.
3. **Save/reload** — the event re-runs on load (event-0 init), re-asserting wall state from flag 76998
   (which is save-persisted client-side), so a save inside Stormveil restores correctly.
4. If the chosen wall's collision doesn't drop on disable, fall back to also warping (Tier-2 hybrid)
   behind it as a backstop.
```
