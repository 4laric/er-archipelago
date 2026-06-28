#!/usr/bin/env python3
# patch_apworld_chain_freelink_startgraces_20260621.py
#
# FIX: num_regions_chain precollected FIRST link strands the start region.
# The first chain link's lock is push_precollected() as a START item; it arrives
# name-UNRESOLVED ("Unknown from Server"), so the client's on-receipt
# regionGraces / regionOpenFlags handler never fires. Result: the start region
# spawns with NO warp graces and NO region-open flag.
# Observed live 2026-06-20 (archipelago_client_sync_620.log): Mt. Gelmir was the
# precollected first link and was stranded ~67 min until the Altus Lock arrived.
#
# This mirrors the EXISTING random-start fold (__init__.py ~4945-4958): light the
# free link's grace bundle + open flag into start_graces at load.
# Special case Mt. Gelmir: its graces were REBUCKETED onto the Altus Lock (its
# tiles read as the 63xxx Altus play-region), so its own bundle is empty. As the
# START link it must carry its own graces -> pull Gelmir's grace points (minus
# border skips 73204/76351), add open flag 76985, AND the Altus open flag 76972 so
# warping onto the 63xxx Gelmir tiles doesn't trip the Altus kick.
#
# RUN ON WINDOWS from the repo root:  python patch_apworld_chain_freelink_startgraces_20260621.py
# (or pass an explicit path to __init__.py). Idempotent; aborts if the anchor moved.

import sys, io, os

DEFAULT = os.path.join("Archipelago", "worlds", "eldenring", "__init__.py")
MARKER  = "chain_freelink_startgraces"
ANCHOR  = ("        self._rsr_warp_grace = _rsr_warp_grace\n"
           "        start_items: List[int] = []")

BLOCK = '''        self._rsr_warp_grace = _rsr_warp_grace
        # num_regions_chain free-link start graces (patch chain_freelink_startgraces): the FIRST
        # chain link's lock is PRECOLLECTED (start item) and arrives name-UNRESOLVED, so the
        # on-receipt regionGraces/regionOpenFlags path never fires -- the start region spawns with
        # no warp graces + no open flag (observed sync 2026-06-20: Mt. Gelmir start link stranded
        # ~67 min). Mirror the random-start fold: light the free link's bundle + open flag here.
        _free_lock = getattr(self, "_num_regions_chain_free_lock", None)
        if getattr(self, "_num_regions_chain", False) and _free_lock and self.options.world_logic < 3:
            _fl_g = list(region_graces.get(_free_lock, []))
            if _free_lock == "Mt. Gelmir Lock":
                # Gelmir REBUCKET escape: its graces ride the Altus Lock (Gelmir tiles read as the
                # 63xxx Altus play-region), so its own bundle is empty. As the START link it must
                # carry its own graces: Gelmir grace points (minus border skips 73204/76351) + open
                # flag 76985 + Altus open flag 76972 (suppress the 63xxx Altus kick on Gelmir tiles).
                # Opens Altus enforcement early; Altus CHECKS stay Lock-gated in fill.
                _gelmir_skip = frozenset({73204, 76351})
                _fl_g += [int(p[0]) for p in REGION_GRACE_POINTS.get("Mt. Gelmir", [])
                          if p[0] not in _gelmir_skip]
                for _ofk in ("Mt. Gelmir Lock", "Altus Lock"):
                    _ofv = region_open_flags.get(_ofk)
                    if _ofv:
                        _fl_g.append(int(_ofv))
            else:
                _fl_of = region_open_flags.get(_free_lock)
                if _fl_of:
                    _fl_g.append(int(_fl_of))
            start_graces = sorted(set(start_graces + [int(_f) for _f in _fl_g]))
        start_items: List[int] = []'''


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    if not os.path.isfile(path):
        print("ERROR: file not found:", path)
        return 2
    with io.open(path, "r", encoding="utf-8", newline="") as f:
        src = f.read()
    nl = "\r\n" if "\r\n" in src else "\n"
    body = src.replace("\r\n", "\n")
    if MARKER in body:
        print("ALREADY APPLIED (marker present) -- no change made.")
        return 0
    c = body.count(ANCHOR)
    if c != 1:
        print("ERROR: anchor found %d time(s) (expected 1). File may have changed; aborting." % c)
        return 3
    body = body.replace(ANCHOR, BLOCK, 1)
    out = body.replace("\n", nl) if nl == "\r\n" else body
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    with io.open(path, "r", encoding="utf-8", newline="") as f:
        chk = f.read().replace("\r\n", "\n")
    ok = (MARKER in chk) and (chk.count("start_items: List[int] = []") == 1)
    print("APPLIED." if ok else "WROTE FILE but verification FAILED -- inspect manually.")
    print("  marker present :", MARKER in chk)
    print("  newline style  :", "CRLF" if nl == "\r\n" else "LF")
    print("  bytes written  :", len(out))
    return 0 if ok else 5


if __name__ == "__main__":
    raise SystemExit(main())
