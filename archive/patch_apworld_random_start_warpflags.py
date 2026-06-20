#!/usr/bin/env python3
"""
patch_apworld_random_start_warpflags.py -- follow-up to patch_apworld_random_start.py.

Emits the three latch flags the runtime client needs for the forced entry warp, next to the existing
startRegion / startWarpGrace keys in fill_slot_data:
  randomStartWarpFlag  = 76969  (MUST match RegionFogGates.RANDOM_START_FLAG in the baker)
  randomStartAreaId    = 18000  (Chapel of Anticipation -- the area the client watches; = dlcStartAreaId)
  randomStartDoneFlag  = 76968  (persistent guard so the warp fires once per save)
All 0 when no start region was rolled. Mirrors the dlc_only dlcEntryWarpFlag/dlcStartAreaId pair.

Run on Windows. Idempotent. Binary I/O preserves CRLF.
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
INIT = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "__init__.py")


def _read(p):
    with open(p, "rb") as f:
        return f.read()


def _write(p, d):
    with open(p, "wb") as f:
        f.write(d)


def _crlf(t):
    return t.replace("\n", "\r\n").encode("utf-8")


ANCHOR = b'            "startWarpGrace": getattr(self, "_rsr_warp_grace", 0),\r\n'
INS = _crlf('''\
            # Random-start auto-entry latch (the runtime client mirrors dlcEntryWarpFlag): warp flag
            # (MUST match RegionFogGates.RANDOM_START_FLAG), the Chapel area id the client watches, and
            # a persistent done-guard so it fires once per save. 0 when not a random-start seed.
            "randomStartWarpFlag": 76969 if getattr(self, "_random_start_region", None) else 0,
            "randomStartAreaId": 18000 if getattr(self, "_random_start_region", None) else 0,
            "randomStartDoneFlag": 76968 if getattr(self, "_random_start_region", None) else 0,
''')


def main():
    if not os.path.isfile(INIT):
        raise SystemExit(f"[FAIL] not found: {INIT}")
    data = _read(INIT)
    if b'"randomStartWarpFlag":' in data:
        print("[skip] __init__.py already patched.")
        return
    if data.count(ANCHOR) != 1:
        raise SystemExit(f"[FAIL] anchor x{data.count(ANCHOR)} (want 1). No write.")
    _write(INIT, data.replace(ANCHOR, ANCHOR + INS, 1))
    print("[ok] emitted randomStartWarpFlag/AreaId/DoneFlag in slot_data.")


if __name__ == "__main__":
    main()
