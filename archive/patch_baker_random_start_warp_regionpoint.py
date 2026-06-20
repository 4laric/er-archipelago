#!/usr/bin/env python3
"""
patch_baker_random_start_warp_regionpoint.py -- robust fix for random-start OoB spawn.

SYMPTOM (playtest 2026-06-19): random_start rolled Liurnia, warp dropped the player OUT OF BOUNDS in
Liurnia -> instant death. (Earlier Caelid/First Step worked.)

ROOT CAUSE: the warp used bonfireEntityId-1 as the destination ("the bonfire's player-warp point"),
which exists for SOME overworld graces (First Step 1042361950, Caelid) but NOT others (Liurnia). When
the entity doesn't exist, WarpPlayer (2003[14]) falls back to map origin = OoB. So bonfireEntityId-1 is
NOT a universal convention -- the prior fix (patch_baker_random_start_warp_fix_spawnpoint.py) only
happened to work for the graces that have that point.

ROBUST FIX: BonfireWarpParam carries the grace's real position (posX/posY/posZ -- the same source
EldenCoordinator.GetPos(row,"pos") reads). Read it, and CREATE a warp-target region at that position in
the start tile's MSB -- the exact Region.Other clone the region-lock fog code already uses for its
RETURN warp (proven to work as a WarpPlayer destination in-engine). Then warp to that fresh entity
instead of the unreliable bonfireEntityId-1. Falls back to bonfireEntityId-1 only if the start tile MSB
isn't loaded at bake (logged), so no regression for the graces that already worked.

Edits RegionFogGates.cs (LF). One anchored replace (the destEntity line). Idempotent, count==1 guard.
Run on Windows; rebuild SoulsRandomizers + re-bake a random_start_region seed.

TEST NOTE: the one in-engine unknown is whether WarpPlayer (2003[14], cross-map) accepts a created
Region.Other as its destination (the fog RETURN warp proved it for the in-map 2004[41] path). If Liurnia
STILL lands OoB after this, the created region is being ignored by 2003[14] -> next step is to make the
target a Player part (clone c0000) instead of a region; the position-mining here stays the same. The
bake log prints the created entity + position per start so you can confirm the region was authored.
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
RFG = os.path.join(ROOT, "SoulsRandomizers", "RandomizerCommon", "RegionFogGates.cs")

OLD = (b'            uint destEntity = (uint)row["bonfireEntityId"].Value - 1u;  '
       b'// -1 = the bonfire\'s player-warp point; the asset itself is OoB. Matches KICK '
       b'(1042361950 = First Step bonfire 1042361951-1) and DLC entry (2046402020).')

NEW = (
    b'            // Warp DEST: bonfireEntityId-1 (the bonfire\'s player-warp point) exists only for SOME\n'
    b'            // graces (First Step/Caelid) but NOT others (Liurnia) -> WarpPlayer falls back to map\n'
    b'            // origin = OoB death. ROBUST FIX: read the grace\'s real position from BonfireWarpParam\n'
    b'            // (posX/Y/Z -- same source as EldenCoordinator.GetPos(row,"pos")) and CREATE a warp-target\n'
    b'            // region there in the start tile\'s MSB (the same proven Region.Other clone the region-lock\n'
    b'            // fog RETURN warp uses), then warp to it. Fall back to bonfireEntityId-1 only if the tile\n'
    b'            // MSB isn\'t loaded at bake (no regression for graces that already worked).\n'
    b'            uint destEntity = (uint)row["bonfireEntityId"].Value - 1u;\n'
    b'            string startTileMap = GameData.FormatMap(mp);\n'
    b'            if (game.Maps.TryGetValue(startTileMap, out IMsb startImsb) && startImsb is MSBE startMsb)\n'
    b'            {\n'
    b'                MSBE.Region startTmpl = startMsb.Regions.Others.FirstOrDefault()\n'
    b'                    ?? startMsb.Regions.GetEntries().FirstOrDefault(r => r.EntityID != 0)\n'
    b'                    ?? startMsb.Regions.GetEntries().FirstOrDefault();\n'
    b'                if (startTmpl != null)\n'
    b'                {\n'
    b'                    var startRegions = startMsb.Regions.GetEntries();\n'
    b'                    uint warpEntity = NextFreeEntity(startMsb, (uint)row["bonfireEntityId"].Value + 100u);\n'
    b'                    int warpRid = startRegions.Count == 0 ? 1 : startRegions.Max(r => r.RegionID) + 1;\n'
    b'                    var startPos = new System.Numerics.Vector3(\n'
    b'                        (float)row["posX"].Value, (float)row["posY"].Value + 1f, (float)row["posZ"].Value);\n'
    b'                    var warpReg = (MSBE.Region)startTmpl.DeepCopy();\n'
    b'                    warpReg.Name = $"AP RandomStart Spawn {startRegion}";\n'
    b'                    warpReg.EntityID = warpEntity;\n'
    b'                    warpReg.Position = startPos;\n'
    b'                    warpReg.Rotation = System.Numerics.Vector3.Zero;\n'
    b'                    warpReg.Shape = new MSB.Shape.Box { Width = 4f, Depth = 4f, Height = 4f };\n'
    b'                    warpReg.RegionID = warpRid;\n'
    b'                    warpReg.ActivationPartName = null;\n'
    b'                    startMsb.Regions.Add(warpReg);\n'
    b'                    game.WriteMSBs.Add(startTileMap);\n'
    b'                    destEntity = warpEntity;\n'
    b'                    Console.WriteLine($"RandomStartEntry: created spawn region ent {warpEntity} @ {startTileMap} "\n'
    b'                        + $"pos ({startPos.X:F1},{startPos.Y:F1},{startPos.Z:F1}) RegionID {warpRid} for {startRegion}");\n'
    b'                }\n'
    b'                else\n'
    b'                {\n'
    b'                    Console.WriteLine($"RandomStartEntry: {startTileMap} has no region template -- "\n'
    b'                        + $"falling back to bonfireEntityId-1 ({destEntity})");\n'
    b'                }\n'
    b'            }\n'
    b'            else\n'
    b'            {\n'
    b'                Console.WriteLine($"RandomStartEntry: start tile {startTileMap} not loaded at bake -- "\n'
    b'                    + $"falling back to bonfireEntityId-1 ({destEntity}); if this lands OoB, the tile MSB must be loaded.");\n'
    b'            }'
)


def main():
    if not os.path.isfile(RFG):
        raise SystemExit(f"[FAIL] not found: {RFG}")
    with open(RFG, "rb") as f:
        data = f.read()
    if b"AP RandomStart Spawn" in data:
        print("[skip] already patched (region-point spawn).")
        return
    if data.count(OLD) != 1:
        raise SystemExit(f"[FAIL] anchor x{data.count(OLD)} (want 1). "
                         "Expected the bonfireEntityId-1 line from patch_baker_random_start_warp_fix_spawnpoint.py. No write.")
    with open(RFG, "wb") as f:
        f.write(data.replace(OLD, NEW, 1))
    print("[ok] random-start warp now creates a Region.Other at the grace's real param position. "
          "Rebuild SoulsRandomizers + re-bake; check the 'created spawn region' log line per start.")


if __name__ == "__main__":
    main()
