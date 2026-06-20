#!/usr/bin/env python3
"""
patch_baker_random_start_warp_fix_cast.py -- hotfix for ApplyRandomStartEntry (RegionFogGates.cs).

Bug: BonfireWarpParam.eventflagId is boxed as UInt32; `(int)r["eventflagId"].Value` throws
InvalidCastException (can't unbox uint -> int directly). Use Convert.ToInt64, which unboxes any
boxed numeric type, then compare to startWarpGrace (int -> long). One-line replace. Idempotent.
RegionFogGates.cs is LF. Run on Windows; rebuild SoulsRandomizers.
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
RFG = os.path.join(ROOT, "SoulsRandomizers", "RandomizerCommon", "RegionFogGates.cs")

OLD = b'            PARAM.Row row = game.Params["BonfireWarpParam"].Rows.Find(r => (int)r["eventflagId"].Value == startWarpGrace);'
NEW = b'            PARAM.Row row = game.Params["BonfireWarpParam"].Rows.Find(r => Convert.ToInt64(r["eventflagId"].Value) == startWarpGrace);'


def main():
    if not os.path.isfile(RFG):
        raise SystemExit(f"[FAIL] not found: {RFG}")
    with open(RFG, "rb") as f:
        data = f.read()
    if b"Convert.ToInt64(r[\"eventflagId\"]" in data:
        print("[skip] already fixed.")
        return
    if data.count(OLD) != 1:
        raise SystemExit(f"[FAIL] anchor x{data.count(OLD)} (want 1). No write.")
    with open(RFG, "wb") as f:
        f.write(data.replace(OLD, NEW, 1))
    print("[ok] fixed eventflagId cast (uint -> Convert.ToInt64). Rebuild SoulsRandomizers + re-bake.")


if __name__ == "__main__":
    main()
