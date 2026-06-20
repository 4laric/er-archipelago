#!/usr/bin/env python3
"""
patch_baker_completion_scaling_diag.py -- add an observability log line to the completion-scaling
reshape in EnemyRandomizer.cs, so a bake CONFIRMS it ran and shows which way it pushed difficulty.

The reshape was silent; this prints (Console.WriteLine, same channel as the RegionFogGates logs that
already show up in the bake output):
  CompletionScaling: mode=3 floor=0% MaxTier=35 -> retiered enemies up=812 down=14 same=190
Reading it: flat => up=down=0 (identity); steep => up >> down (mid pushed up); gentle => down >> up.
If you DON'T see this line at all, the reshape didn't run -> completion_scaling was off OR enemy_rando
was off (the pass only runs inside the enemy randomizer).

CRLF file. Idempotent. Run on Windows; rebuild SoulsRandomizers + re-bake with enemy_rando + steep.
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
ER = os.path.join(ROOT, "SoulsRandomizers", "RandomizerCommon", "EnemyRandomizer.cs")


def _crlf(t):
    return t.replace("\n", "\r\n").encode("utf-8")


ANCHOR = _crlf("                    targetScalingSections[compTarget] = compNew;\n                }\n")
INS = _crlf(
    "                int csUp = 0, csDown = 0, csSame = 0;\n"
    "                foreach (KeyValuePair<int, int> csE in ann.ScalingSections)\n"
    "                    if (csE.Value > 0 && targetScalingSections.TryGetValue(csE.Key, out int csNv))\n"
    "                    { if (csNv > csE.Value) csUp++; else if (csNv < csE.Value) csDown++; else csSame++; }\n"
    "                Console.WriteLine($\"CompletionScaling: mode={CompletionScaleMode} floor={CompletionScaleFloorPct}% \"\n"
    "                    + $\"MaxTier={compMaxTier} -> retiered enemies up={csUp} down={csDown} same={csSame}\");\n"
)


def main():
    if not os.path.isfile(ER):
        raise SystemExit(f"[FAIL] not found: {ER}")
    with open(ER, "rb") as f:
        data = f.read()
    if b"CompletionScaling: mode=" in data:
        print("[skip] diag already present.")
        return
    if data.count(ANCHOR) != 1:
        raise SystemExit(f"[FAIL] anchor x{data.count(ANCHOR)} (want 1). No write.")
    with open(ER, "wb") as f:
        f.write(data.replace(ANCHOR, ANCHOR + INS, 1))
    print("[ok] added CompletionScaling diag log. Rebuild SoulsRandomizers + re-bake.")


if __name__ == "__main__":
    main()
