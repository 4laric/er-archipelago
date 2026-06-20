#!/usr/bin/env python3
"""
patch_baker_random_start_warp.py -- C# baker layer for Random Starting Region (idea #1), warp half.
SPEC: SPEC-random-starting-region.md. Pairs with patch_apworld_random_start.py.

Generalises the DLC-only entry warp (RegionFogGates.ApplyDlcEntry) to drop a fresh save into the
ROLLED start region. Same WarpPlayer-into-common pattern, gated on RANDOM_START_FLAG (the runtime
client sets it once in the Chapel -- a CLIENT follow-up, mirroring dlcEntryWarpFlag).

RegionFogGates.cs (LF): add ApplyRandomStartEntry + RANDOM_START_FLAG + RANDOM_START_DEST table.
ArchipelagoForm.cs (LF): call it after the dlc_only ApplyDlcEntry block, reading startRegion.

DATA DEPENDENCY (blocks runnability): RANDOM_START_DEST maps each region -> (map tile + warp-point
entity), which must be CAPTURED in-game per region (cf. REGIONLOCK-areaid-capture.md). Until a
region's dest is filled the warp is SKIPPED with a log line -- safe no-op; the apworld-granted start
graces still let the player fast-travel in manually. See CAPTURE-random-start-warp.md.

Run on Windows; rebuild SoulsRandomizers. Idempotent. Per-file line endings preserved (both LF).
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
RFG = os.path.join(ROOT, "SoulsRandomizers", "RandomizerCommon", "RegionFogGates.cs")
AF = os.path.join(ROOT, "SoulsRandomizers", "RandomizerCommon", "ArchipelagoForm.cs")


def _read(p):
    with open(p, "rb") as f:
        return f.read()


def _write(p, d):
    with open(p, "wb") as f:
        f.write(d)


def _lf(t):
    return t.encode("utf-8")


def _ins_before(data, anchor, insert, label):
    if data.count(anchor) != 1:
        raise SystemExit(f"[FAIL] {label}: anchor x{data.count(anchor)} (want 1). No write.")
    return data.replace(anchor, insert + anchor, 1)


def _ins_after(data, anchor, insert, label):
    if data.count(anchor) != 1:
        raise SystemExit(f"[FAIL] {label}: anchor x{data.count(anchor)} (want 1). No write.")
    return data.replace(anchor, anchor + insert, 1)


RFG_ANCHOR = _lf('        // On-warp "sealed area" notice (2026-06-17): the play-region KICK warps the player out\n')
RFG_METHOD = _lf('''\
        // Random starting region (SPEC-random-starting-region.md): generalises the DLC entry warp to
        // drop a fresh save into the ROLLED start region. Gated on RANDOM_START_FLAG (the client sets
        // it once in the Chapel). DESTINATION is per-region (map tile + warp-point entity) and must be
        // CAPTURED in-game -- see CAPTURE-random-start-warp.md. Until a region's dest is filled the
        // warp is skipped (granted start graces still allow manual fast-travel).
        public const uint RANDOM_START_FLAG = 76969;  // free grace-tail flag (KICK 76970, locks 76971+, DLC entry 76999)
        // region name -> (area, block, region, index, destEntity). CAPTURE-PENDING. Gravesite is shown
        // as the worked example (= ApplyDlcEntry's constants). Fill overworld majors after capture.
        private static readonly Dictionary<string, (byte area, byte block, byte region, byte index, uint entity)> RANDOM_START_DEST =
            new Dictionary<string, (byte, byte, byte, byte, uint)>
        {
            // worked example (DLC hub; not a base-game roll target):
            // ["Gravesite Plain"]      = (61, 46, 40, 0, 2046402020u),
            // CAPTURE these in-game (warp-point entity in the spawn tile's MSB):
            // ["Caelid"]               = (60, ?, ?, 0, ?u),
            // ["Liurnia of The Lakes"] = (60, ?, ?, 0, ?u),
            // ["Altus Plateau"]        = (60, ?, ?, 0, ?u),
            // ["Weeping Peninsula"]    = (60, ?, ?, 0, ?u),
        };
        public static void ApplyRandomStartEntry(GameData game, string startRegion, int startWarpGrace)
        {
            if (string.IsNullOrEmpty(startRegion)) return;
            if (!RANDOM_START_DEST.TryGetValue(startRegion, out var d))
            {
                Console.WriteLine($"RandomStartEntry: no captured warp dest for '{startRegion}' -- skipping forced warp (granted graces still allow manual fast-travel). See CAPTURE-random-start-warp.md.");
                return;
            }
            if (!game.Emevds.TryGetValue("common", out EMEVD common))
            {
                Console.WriteLine("RandomStartEntry: 'common' emevd not loaded -- entry warp NOT authored");
                return;
            }
            int evId = game.GetUniqueEventId();
            var ev = new EMEVD.Event(evId, EMEVD.Event.RestBehaviorType.Default);
            var ins = ev.Instructions;
            ins.Add(new EMEVD.Instruction(3, 0, new List<object> { (sbyte)0, (byte)1, (byte)0, RANDOM_START_FLAG }));   // IF EventFlag(MAIN, ON, RANDOM_START_FLAG)
            ins.Add(new EMEVD.Instruction(2003, 14, new List<object> { d.area, d.block, d.region, d.index, d.entity, (int)0 }));  // WarpPlayer -> start region
            if (startWarpGrace > 0)
                ins.Add(new EMEVD.Instruction(2003, 66, new List<object> { (byte)0, (uint)startWarpGrace, (byte)1 })); // SetEventFlag(startWarpGrace, ON) -- mark the spawn grace
            ins.Add(new EMEVD.Instruction(2003, 66, new List<object> { (byte)0, RANDOM_START_FLAG, (byte)0 }));        // SetEventFlag(RANDOM_START_FLAG, OFF) -- one-shot
            ins.Add(new EMEVD.Instruction(1001, 0, new List<object> { 2.0f }));                                        // Wait 2s
            ins.Add(new EMEVD.Instruction(1000, 4, new List<object> { (byte)1 }));                                     // End Unconditionally(Restart)
            common.Events.Add(ev);
            if (common.Events.Count == 0 || common.Events[0].ID != 0)
                common.Events.Insert(0, new EMEVD.Event(0, EMEVD.Event.RestBehaviorType.Default));
            common.Events[0].Instructions.Add(new EMEVD.Instruction(2000, 0, new List<object> { (int)0, (uint)evId, (uint)0 }));
            game.WriteEmevds.Add("common");
            Console.WriteLine($"RandomStartEntry: authored common event {evId} -> warp to {startRegion} (entity {d.entity}); client sets /setflag {RANDOM_START_FLAG} 1 once in the Chapel.");
        }

''')

AF_ANCHOR = _lf('                        RegionFogGates.ApplyDlcEntry(game);\n                    }\n')
AF_WIRING = _lf('''\
                    // Random starting region (SPEC-random-starting-region.md): if the apworld rolled a
                    // start region, bake its entry warp (generalised DLC entry). Dest capture-pending
                    // per region (no-op + log until filled). startWarpGrace = the spawn grace flag.
                    if (slotData.TryGetValue("startRegion", out var srObj) && srObj != null
                        && !string.IsNullOrEmpty(srObj.ToString()))
                    {
                        int srGrace = (slotData.TryGetValue("startWarpGrace", out var swgObj)
                            && swgObj != null && int.TryParse(swgObj.ToString(), out var swg)) ? swg : 0;
                        RegionFogGates.ApplyRandomStartEntry(game, srObj.ToString(), srGrace);
                    }
''')


def patch_rfg(data):
    if b"ApplyRandomStartEntry" in data:
        print("[skip] RegionFogGates.cs already patched.")
        return data, False
    data = _ins_before(data, RFG_ANCHOR, RFG_METHOD, "RegionFogGates method")
    return data, True


def patch_af(data):
    if b"ApplyRandomStartEntry" in data:
        print("[skip] ArchipelagoForm.cs already patched.")
        return data, False
    data = _ins_after(data, AF_ANCHOR, AF_WIRING, "ArchipelagoForm wiring")
    return data, True


def main():
    for p in (RFG, AF):
        if not os.path.isfile(p):
            raise SystemExit(f"[FAIL] not found: {p}")
    r = _read(RFG)
    r2, rc = patch_rfg(r)
    a = _read(AF)
    a2, ac = patch_af(a)
    if rc:
        _write(RFG, r2)
        print("[ok] patched RegionFogGates.cs")
    if ac:
        _write(AF, a2)
        print("[ok] patched ArchipelagoForm.cs")
    if not (rc or ac):
        print("[done] nothing to do.")
    else:
        print("[done] random-start warp baker scaffold applied. CAPTURE per-region dests + add the "
              "client RANDOM_START_FLAG latch, then rebuild.")


if __name__ == "__main__":
    main()
