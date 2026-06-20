#!/usr/bin/env python3
r"""
patch_apworld_start_emission.py  (run on Windows from repo root)

Restores the physical-spawn slot_data keys that the baker's ApplyRandomStartEntry reads but that are
MISSING from HEAD (lost in the 2026-06-19 __init__.py truncation; the original SG/SD blocks in
patch_apworld_random_start.py never re-applied because that script self-skips once the roll block
exists). Adds, inside fill_slot_data:

  * a start-grace bundle for the rolled `_random_start_region` (its graces minus boss/border graces,
    + Roundtable 71190, + the region's open flag), and `self._rsr_warp_grace` = the centroid grace
    (the baked WarpPlayer target).
  * slot_data keys "startRegion" + "startWarpGrace".

CORRECTION vs the old SG_BLOCK: does NOT light The First Step (76101). Under the Roundtable re-root
Limgrave is a LOCKED region, so 76101 would offer free fast-travel into it. Limgrave graces are lit
only under start_region_freebie == to_limgrave (LIMGRAVE_START_GRACES), unchanged.

"Roundtable Hold" as the start region (pool mode, chain OFF) -> no region graces, warp grace 0 ->
the baker skips the forced warp (player stays at the Roundtable New-Game root). Only a rolled
overworld region (chain ON, see patch_apworld_numregions_chain_rolled_start.py) yields a forced warp.

Idempotent. Binary I/O preserves CRLF. Asserts anchors (no write on mismatch).
Run order: this -> patch_apworld_random_start_warpflags.py -> patch_apworld_numregions_chain_rolled_start.py
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


# --- SG block: insert immediately BEFORE `start_items: List[int] = []` (fill_slot_data; start_graces
#     and region_open_flags are already in scope by then). ---------------------------------------
SG_ANCHOR = b"        start_items: List[int] = []\r\n"
SG_BLOCK = _crlf('''\
        # Random/rolled starting region: grant the rolled region's grace bundle at load (minus
        # boss-arena/border graces) + Roundtable (71190) + the region's open flag, and record the
        # centroid grace as the baked WarpPlayer target (_rsr_warp_grace). NO First Step (76101):
        # Limgrave is LOCKED under the Roundtable re-root. "Roundtable Hold" -> empty bundle, warp
        # grace 0 -> baker skips the forced warp. SPEC-random-start-roundtable-hub.md.
        _rsr = getattr(self, "_random_start_region", None)
        _rsr_warp_grace = 0
        if _rsr and self.options.world_logic < 3:
            _RS_SKIP = frozenset({71240, 76422, 76508, 76509, 76852, 76853, 76930, 76931,
                                  73204, 73207, 76209, 76229, 76301, 76350, 76351, 76356})
            _rs_pts = [p for p in REGION_GRACE_POINTS.get(_rsr, []) if p[0] not in _RS_SKIP]
            _rs_g = [int(p[0]) for p in _rs_pts]
            _rs_g += [71190]  # Roundtable hub only -- Limgrave is LOCKED, do NOT light First Step 76101
            _rs_of = region_open_flags.get(REGION_LOCK_ITEM.get(_rsr))
            if _rs_of:
                _rs_g.append(int(_rs_of))
            if self.options.start_region_freebie.value == 1:  # to_limgrave
                _rs_g += [int(f) for f in LIMGRAVE_START_GRACES]
            start_graces = sorted(set(start_graces + _rs_g))
            if _rs_pts:
                _cx = sum(p[1] for p in _rs_pts) / len(_rs_pts)
                _cz = sum(p[2] for p in _rs_pts) / len(_rs_pts)
                _rsr_warp_grace = int(min(_rs_pts, key=lambda p: (p[1] - _cx) ** 2 + (p[2] - _cz) ** 2)[0])
        self._rsr_warp_grace = _rsr_warp_grace
''')

# --- SD block: insert immediately AFTER the "startGraces" slot_data key. ------------------------
SD_ANCHOR = b'            "startGraces": start_graces,\r\n'
SD_BLOCK = _crlf('''\
            # Random/rolled starting region: rolled hub region name + its central warp grace, for the
            # baked WarpPlayer (ApplyRandomStartEntry). "" / 0 when off (-> baker skips the warp).
            "startRegion": getattr(self, "_random_start_region", None) or "",
            "startWarpGrace": getattr(self, "_rsr_warp_grace", 0),
''')


def main():
    if not os.path.isfile(INIT):
        raise SystemExit(f"[FAIL] not found: {INIT}")
    data = _read(INIT)
    if b'"startRegion":' in data or b"_rsr_warp_grace = 0" in data:
        print("[skip] start emission already present.")
        return
    if data.count(SG_ANCHOR) != 1:
        raise SystemExit(f"[FAIL] SG anchor x{data.count(SG_ANCHOR)} (want 1). No write.")
    if data.count(SD_ANCHOR) != 1:
        raise SystemExit(f"[FAIL] SD anchor x{data.count(SD_ANCHOR)} (want 1). No write.")
    data = data.replace(SG_ANCHOR, SG_BLOCK + SG_ANCHOR, 1)
    data = data.replace(SD_ANCHOR, SD_ANCHOR + SD_BLOCK, 1)
    _write(INIT, data)
    print("[ok] start-grace bundle + startRegion/startWarpGrace emitted.")


if __name__ == "__main__":
    main()
