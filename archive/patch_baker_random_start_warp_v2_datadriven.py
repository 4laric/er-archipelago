#!/usr/bin/env python3
"""
patch_baker_random_start_warp_v2_datadriven.py -- upgrade the random-start warp baker to DATA-DRIVEN.

Supersedes the table-based ApplyRandomStartEntry (RANDOM_START_DEST) already committed. Replaces just
the method in RegionFogGates.cs with a version that derives the warp destination at bake time from
BonfireWarpParam, keyed by the grace eventflagId the apworld emits as startWarpGrace -- so NO per-region
capture / table is needed. ArchipelagoForm wiring is unchanged (same call signature), so it is untouched.

Proven by data-mining your ap_grace_flags dump: GetMapParts(row) -> [areaNo,gridXNo,gridZNo,0] yields
61/46/40/0 for Gravesite (= the old hardcoded ApplyDlcEntry constants) and 60/42/36 for The First Step.
dest entity = bonfireEntityId. VERIFY in-game: the DLC warp used a player-warp POINT entity, not
bonfireEntityId; if warping to bonfireEntityId no-ops, mine the spawn point from the tile's MSB.

Replaces the span between two stable anchors, so it is robust to the old body. Idempotent (skips if
the data-driven marker is already present). RegionFogGates.cs is LF. Run on Windows; rebuild SoulsRandomizers.
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
RFG = os.path.join(ROOT, "SoulsRandomizers", "RandomizerCommon", "RegionFogGates.cs")

START = b'        // Random starting region (SPEC-random-starting-region.md): generalises the DLC entry warp to\n'
END = b'        // On-warp "sealed area" notice (2026-06-17): the play-region KICK warps the player out\n'
MARKER = b'BonfireWarpParam'  # present only in the data-driven version's method

NEW = (
'''        // Random starting region (SPEC-random-starting-region.md): generalises the DLC entry warp to
        // drop a fresh save into the ROLLED start region. DATA-DRIVEN -- the destination is read from
        // BonfireWarpParam at bake time, keyed by the grace eventflagId the apworld emits as
        // startWarpGrace (no capture, no table). Map = GetMapParts(row) (Gravesite -> 61/46/40/0,
        // matching ApplyDlcEntry); dest entity = bonfireEntityId. Gated on RANDOM_START_FLAG (the
        // client sets it once in the Chapel). VERIFY: the DLC warp used a player-warp POINT entity,
        // not bonfireEntityId; if this no-ops, mine the spawn point from the tile's MSB instead.
        public const uint RANDOM_START_FLAG = 76969;  // free grace-tail flag (KICK 76970, locks 76971+, DLC entry 76999)
        public static void ApplyRandomStartEntry(GameData game, string startRegion, int startWarpGrace)
        {
            if (string.IsNullOrEmpty(startRegion) || startWarpGrace <= 0) return;
            if (!game.Emevds.TryGetValue("common", out EMEVD common))
            {
                Console.WriteLine("RandomStartEntry: 'common' emevd not loaded -- entry warp NOT authored");
                return;
            }
            PARAM.Row row = game.Params["BonfireWarpParam"].Rows.Find(r => (int)r["eventflagId"].Value == startWarpGrace);
            if (row == null)
            {
                Console.WriteLine($"RandomStartEntry: no BonfireWarpParam row for grace flag {startWarpGrace} ({startRegion}) -- skipping forced warp (granted graces still allow manual fast-travel).");
                return;
            }
            List<byte> mp = game.GetMapParts(row);   // [areaNo, gridXNo, gridZNo, 0]
            while (mp.Count < 4) mp.Add(0);
            uint destEntity = (uint)row["bonfireEntityId"].Value;
            int evId = game.GetUniqueEventId();
            var ev = new EMEVD.Event(evId, EMEVD.Event.RestBehaviorType.Default);
            var ins = ev.Instructions;
            ins.Add(new EMEVD.Instruction(3, 0, new List<object> { (sbyte)0, (byte)1, (byte)0, RANDOM_START_FLAG }));
            ins.Add(new EMEVD.Instruction(2003, 14, new List<object> { mp[0], mp[1], mp[2], mp[3], destEntity, (int)0 }));
            ins.Add(new EMEVD.Instruction(2003, 66, new List<object> { (byte)0, (uint)startWarpGrace, (byte)1 }));
            ins.Add(new EMEVD.Instruction(2003, 66, new List<object> { (byte)0, RANDOM_START_FLAG, (byte)0 }));
            ins.Add(new EMEVD.Instruction(1001, 0, new List<object> { 2.0f }));
            ins.Add(new EMEVD.Instruction(1000, 4, new List<object> { (byte)1 }));
            common.Events.Add(ev);
            if (common.Events.Count == 0 || common.Events[0].ID != 0)
                common.Events.Insert(0, new EMEVD.Event(0, EMEVD.Event.RestBehaviorType.Default));
            common.Events[0].Instructions.Add(new EMEVD.Instruction(2000, 0, new List<object> { (int)0, (uint)evId, (uint)0 }));
            game.WriteEmevds.Add("common");
            string mapId = GameData.FormatMap(mp);
            Console.WriteLine($"RandomStartEntry: warp to {startRegion} @ {mapId} entity {destEntity} (grace {startWarpGrace}); client sets /setflag {RANDOM_START_FLAG} 1 once in the Chapel.");
        }

''').encode("utf-8")


def main():
    if not os.path.isfile(RFG):
        raise SystemExit(f"[FAIL] not found: {RFG}")
    with open(RFG, "rb") as f:
        data = f.read()
    s = data.find(START)
    e = data.find(END)
    if s < 0 or e < 0 or e <= s:
        raise SystemExit(f"[FAIL] anchors not found/ordered (start={s}, end={e}). No write.")
    region = data[s:e]
    if MARKER in region:
        print("[skip] RegionFogGates.cs ApplyRandomStartEntry already data-driven.")
        return
    out = data[:s] + NEW + data[e:]
    with open(RFG, "wb") as f:
        f.write(out)
    print("[ok] upgraded ApplyRandomStartEntry to data-driven (BonfireWarpParam lookup). Rebuild SoulsRandomizers.")


if __name__ == "__main__":
    main()
