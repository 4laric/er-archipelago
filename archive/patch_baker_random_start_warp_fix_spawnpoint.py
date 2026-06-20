#!/usr/bin/env python3
"""
patch_baker_random_start_warp_fix_spawnpoint.py -- fix OoB spawn in ApplyRandomStartEntry.

Symptom: random start warped the player into Caelid but OUT OF BOUNDS (instant death).
Cause: we warped to BonfireWarpParam.bonfireEntityId, which is the bonfire ASSET part -- its
transform is the flame pivot, not a valid standing spot, so WarpPlayer drops you OoB. The grace's
actual player-warp/spawn point sits at bonfireEntityId - 1. This matches the PROVEN warps already in
this file: the play-region KICK uses WARP_DEST_ENTITY 1042361950 = First Step bonfire 1042361951 - 1,
and the DLC entry uses 2046402020 = Gravesite bonfire 2046402021 - 1. (map coords + last=0 unchanged.)

One-line replace on RegionFogGates.cs (LF). Idempotent. Run on Windows; rebuild SoulsRandomizers + re-bake.
NOTE: -1 is the overworld bonfire->warp-point convention (verified on m60 First Step; the random-start
candidates are overworld majors). If a future non-overworld start spawns oddly, re-check that grace's layout.
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
RFG = os.path.join(ROOT, "SoulsRandomizers", "RandomizerCommon", "RegionFogGates.cs")

OLD = b'            uint destEntity = (uint)row["bonfireEntityId"].Value;'
NEW = (b'            uint destEntity = (uint)row["bonfireEntityId"].Value - 1u;  '
       b'// -1 = the bonfire\'s player-warp point; the asset itself is OoB. Matches KICK '
       b'(1042361950 = First Step bonfire 1042361951-1) and DLC entry (2046402020).')


def main():
    if not os.path.isfile(RFG):
        raise SystemExit(f"[FAIL] not found: {RFG}")
    with open(RFG, "rb") as f:
        data = f.read()
    if b'bonfireEntityId"].Value - 1u' in data:
        print("[skip] already fixed.")
        return
    if data.count(OLD) != 1:
        raise SystemExit(f"[FAIL] anchor x{data.count(OLD)} (want 1). No write.")
    with open(RFG, "wb") as f:
        f.write(data.replace(OLD, NEW, 1))
    print("[ok] warp dest now bonfireEntityId-1 (player-warp point). Rebuild SoulsRandomizers + re-bake.")


if __name__ == "__main__":
    main()
