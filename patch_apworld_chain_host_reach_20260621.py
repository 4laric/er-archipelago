#!/usr/bin/env python3
# patch_apworld_chain_host_reach_20260621.py  (run on Windows from repo root)
#
# Make the num_regions_chain breadcrumb HOST selection reachability-aware. _num_regions_chain_host
# picks the most prominent boss in a step's host regions, but those host regions can include gated
# INTERIORS (Volcano Manor inside Mt. Gelmir, Raya Lucaria inside Liurnia) that the player can't
# reach just by warping into the outer region -- so the next chain lock parked there is stranded and
# the chain snaps (FillError: "Could not access required locations for accessibility check. Missing:
# [<host boss>]"). Fix: keep only candidate hosts reachable under the chain placed SO FAR
# (precollected + already-placed breadcrumbs, via CollectionState + sweep_for_advancements). If none
# are reachable, return None so the caller precollects the lock (chain stays intact, loses one ramp
# sphere). Idempotent; aborts if the anchor moved. Repackage the apworld + gen-test.

import sys, io, os
DEFAULT = os.path.join("Archipelago", "worlds", "eldenring", "__init__.py")
MARKER  = "chain_host_reach"

ANCHOR = (
'        if not cands:\n'
'            return None\n'
'\n'
'        def _missable(l):'
)
BLOCK = (
'        if not cands:\n'
'            return None\n'
'\n'
'        # Reachability-aware host (patch chain_host_reach): a breadcrumb lock must be parked where\n'
'        # the player can actually reach it with the chain placed SO FAR -- not in a gated interior\n'
'        # (Volcano Manor, Raya Lucaria) needing a questline item the warp does not grant, which would\n'
'        # strand the lock and snap the chain (accessibility-check FillError on the host location).\n'
'        # Filter to hosts reachable under precollected + already-placed breadcrumbs; if none are\n'
'        # reachable, return None so the caller precollects the lock (chain stays intact).\n'
'        try:\n'
'            _cs = CollectionState(self.multiworld)\n'
'            _cs.sweep_for_advancements()\n'
'            cands = [l for l in cands if l.can_reach(_cs)]\n'
'        except Exception as _e:\n'
'            warning(f"{self.player_name}: chain-host reach filter skipped ({_e}).")\n'
'        if not cands:\n'
'            return None\n'
'\n'
'        def _missable(l):'
)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    if not os.path.isfile(path):
        print("ERROR: file not found:", path); return 2
    with io.open(path, "r", encoding="utf-8", newline="") as f:
        src = f.read()
    nl = "\r\n" if "\r\n" in src else "\n"
    body = src.replace("\r\n", "\n")
    if MARKER in body:
        print("ALREADY APPLIED -- no change."); return 0
    if body.count(ANCHOR) != 1:
        print("ERROR: anchor found %d (expected 1). Aborting." % body.count(ANCHOR)); return 3
    body = body.replace(ANCHOR, BLOCK, 1)
    out = body.replace("\n", nl) if nl == "\r\n" else body
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    chk = out.replace("\r\n", "\n")
    ok = (MARKER in chk and "sweep_for_advancements" in chk
          and chk.count("        if not cands:\n            return None") == 2)
    print("APPLIED." if ok else "WROTE but verify FAILED -- inspect.")
    return 0 if ok else 5

if __name__ == "__main__":
    raise SystemExit(main())
