#!/usr/bin/env python3
"""
patch_baker_kick_to_roundtable.py -- retarget the play-region KICK fallback to Roundtable Hold when
Limgrave is in the locked set (random-start Roundtable-hub model, SPEC-random-start-roundtable-hub.md).

Today the KICK warps the player to First Step (WARP_DEST_ENTITY 1042361950, inside Limgrave's play-
region). Once Limgrave can itself be locked (random-start re-root), First Step would re-kick -> loop.
Fix: if regionOpenFlags contains "Limgrave Lock" (i.e. Limgrave is a locked region this seed), resolve
the KICK dest from BonfireWarpParam grace 71190 -> Roundtable Hold (m11_10 interior, always open),
entity = bonfireEntityId-1 (the player-warp point, same convention as the start warp). Self-scoping:
no "Limgrave Lock" flag => unchanged First Step behaviour (zero impact on existing seeds). Falls back
to First Step on any lookup failure. Convert.ToInt64 unboxes the uint eventflagId (see the cast bug note).

RegionFogGates.cs (LF). Idempotent. Run on Windows; rebuild SoulsRandomizers.
NOTE: inert until the apworld re-root emits a "Limgrave Lock" open flag; safe to apply now.
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
RFG = os.path.join(ROOT, "SoulsRandomizers", "RandomizerCommon", "RegionFogGates.cs")


def _lf(t):
    return t.encode("utf-8")


RESOLVE_ANCHOR = _lf("                    if (KICK_WARP)\n")
RESOLVE = _lf(
    "                    // KICK fallback dest: default First Step (Limgrave; open in normal seeds).\n"
    "                    // Under random-start Limgrave itself can be locked -> First Step would re-kick,\n"
    "                    // so if the Limgrave lock is in the locked set, retarget to Roundtable Hold\n"
    "                    // (interior, always open) via BonfireWarpParam grace 71190. Loop-proof.\n"
    "                    byte kwArea = WARP_AREA, kwBlock = WARP_BLOCK, kwRegion = WARP_REGION, kwIndex = WARP_INDEX;\n"
    "                    uint kwEnt = WARP_DEST_ENTITY;\n"
    "                    try {\n"
    "                        if (regionOpenFlags != null && regionOpenFlags.ContainsKey(\"Limgrave Lock\")) {\n"
    "                            var rtRow = game.Params[\"BonfireWarpParam\"].Rows.Find(r => Convert.ToInt64(r[\"eventflagId\"].Value) == 71190);\n"
    "                            if (rtRow != null) {\n"
    "                                var rtMp = game.GetMapParts(rtRow);\n"
    "                                while (rtMp.Count < 4) rtMp.Add(0);\n"
    "                                kwArea = rtMp[0]; kwBlock = rtMp[1]; kwRegion = rtMp[2]; kwIndex = rtMp[3];\n"
    "                                kwEnt = (uint)rtRow[\"bonfireEntityId\"].Value - 1u;\n"
    "                                Log($\"RegionFogGates: KICK fallback -> Roundtable (m{kwArea}_{kwBlock:D2}_{kwRegion:D2} ent {kwEnt}); Limgrave locked\");\n"
    "                            }\n"
    "                        }\n"
    "                    } catch (Exception kwEx) { Console.WriteLine(\"KICK Roundtable retarget failed, using First Step: \" + kwEx.Message); }\n"
)

ARGS_OLD = _lf("                            WARP_AREA, WARP_BLOCK, WARP_REGION, WARP_INDEX, WARP_DEST_ENTITY, (int)0 }));")
ARGS_NEW = _lf("                            kwArea, kwBlock, kwRegion, kwIndex, kwEnt, (int)0 }));")


def main():
    if not os.path.isfile(RFG):
        raise SystemExit(f"[FAIL] not found: {RFG}")
    with open(RFG, "rb") as f:
        data = f.read()
    if b"kwEnt = WARP_DEST_ENTITY" in data:
        print("[skip] already patched.")
        return
    for a, lbl in ((RESOLVE_ANCHOR, "KICK_WARP anchor"), (ARGS_OLD, "warp args")):
        if data.count(a) != 1:
            raise SystemExit(f"[FAIL] {lbl} x{data.count(a)} (want 1). No write.")
    data = data.replace(RESOLVE_ANCHOR, RESOLVE + RESOLVE_ANCHOR, 1)
    data = data.replace(ARGS_OLD, ARGS_NEW, 1)
    with open(RFG, "wb") as f:
        f.write(data)
    print("[ok] KICK fallback retargets to Roundtable when Limgrave is locked. Rebuild SoulsRandomizers.")


if __name__ == "__main__":
    main()
