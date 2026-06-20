#!/usr/bin/env python3
r"""
patch_apworld_numregions_chain_rolled_start.py  (run on Windows from repo root)

THE feature: under a num_regions Capital run with num_regions_chain ON, make the player physically
SPAWN in the chain's link-0 region (a randomly-rolled overworld region whose lock pre_fill already
precollects) instead of at the fixed Roundtable hub.

How: the num_regions pool re-root currently hardcodes `self._random_start_region = "Roundtable Hold"`.
When chain is engaged, resolve link 0 (`_num_regions_chain_order[0]`) to its canonical overworld
region via region_spine.SPINE[step-1]["name"] (NOT by inverting REGION_LOCK_ITEM -- Caelid Lock maps
to both "Caelid" and "Sellia Crystal Tunnel"; SPINE gives the right one), require it be grace-mapped,
and point `_random_start_region` at it. Roundtable stays the logic root / services hub / KICK fallback
(every re-root keys on `_random_start_region` being TRUTHY, not on its value). Link 0's lock is already
precollected in pre_fill, so the region is warp-reachable in sphere 1; patch_apworld_start_emission.py
then lights its graces and emits startRegion/startWarpGrace so the baker warps the player in.

Fallback to "Roundtable Hold" when chain is off or link 0 isn't grace-mapped (never breaks gen).

DEPENDS ON: patch_apworld_start_emission.py (emits startRegion/startWarpGrace from _random_start_region)
and patch_apworld_random_start_warpflags.py (latch flags). Run those first.
Idempotent. Binary I/O preserves CRLF. Asserts anchor (no write on mismatch).
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


ANCHOR = b'            self._random_start_region = "Roundtable Hold"\r\n'
REPLACEMENT = _crlf('''\
            # num_regions_chain: SPAWN in the chain's link-0 region (a randomly-rolled overworld
            # region whose lock pre_fill precollects) rather than at the Roundtable hub. Roundtable
            # stays the logic root / services hub / KICK fallback (the re-root keys on the flag being
            # truthy, not its value). Resolve link 0 via SPINE (canonical region name); require it be
            # grace-mapped so the start-grace bundle + WarpPlayer target resolve. Fall back to the
            # Roundtable spawn when chain is off or link 0 isn't grace-mapped. SPEC + HANDOFF-num-regions-random-start.md.
            _ns_start = "Roundtable Hold"
            _chain_ord = getattr(self, "_num_regions_chain_order", None)
            if getattr(self, "_num_regions_chain", False) and _chain_ord:
                _step0 = _chain_ord[0]
                if 1 <= _step0 <= len(region_spine.SPINE):
                    _cand = region_spine.SPINE[_step0 - 1].get("name")
                    if _cand in REGION_GRACE_POINTS:
                        _ns_start = _cand
            self._random_start_region = _ns_start
''')


def main():
    if not os.path.isfile(INIT):
        raise SystemExit(f"[FAIL] not found: {INIT}")
    data = _read(INIT)
    if b"_ns_start = \"Roundtable Hold\"" in data:
        print("[skip] chain rolled-start already applied.")
        return
    if data.count(ANCHOR) != 1:
        raise SystemExit(f"[FAIL] anchor x{data.count(ANCHOR)} (want 1). No write.")
    _write(INIT, data.replace(ANCHOR, REPLACEMENT, 1))
    print("[ok] num_regions_chain now spawns in the link-0 region (Roundtable stays the hub).")


if __name__ == "__main__":
    main()
