#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_msb_mapversions.py -- RECON ONLY. Dump what the MSB tree actually looks like.

WHY THIS DOES NOT SEARCH FOR ANYTHING YET
-----------------------------------------
The 2026-07-25 handoff (§5.5) lists FIVE structural guesses about the MSB -- `Parts/Asset`, `Parts/`,
asset-approximately-lot numbering, `StartDisabled` marks gated pickups, treasure parts might be
Enemies -- and every one produced a confident EMPTY result that reads as "the data is not there".
So this tool's ONLY job is to report the layout. It proposes no shape and asserts no schema.

THE QUESTION IT IS SCOUTING FOR
-------------------------------
`f67050` (Limgrave :: Nomadic Warrior's Cookbook [7], near Stormhill Shack) is a treasure CORPSE
(宝死体000, map m60_40_39, lot 1040390000) whose pickup does not EXIST until Roderika departs. We have
now ruled out both scripted mechanisms by measurement:
  * EMEVD: the flag and its lot appear NOWHERE in all 589 decompiled files, and only 32 of 1824
    corpse flags (1.8%) appear anywhere in the EMEVD at all -- the least script-visible pickup class.
  * ESD: the 2408-flag NPC-state vocabulary is DISJOINT from pickup acquisition flags (0 of 2803).
That leaves MSB MAP VERSIONS as the live hypothesis: the corpse exists in one version of the tile and
not another, which is invisible to every script grep. This probe checks whether the tree even HAS
multiple versions of a tile before anyone builds on that idea.

USAGE (Windows, PowerShell):
    python tools\\probe_msb_mapversions.py --root <the MSB dir>
    # writes msb_probe_report.txt (UTF-8) next to it; paste that back.
If --root is omitted it tries a few likely paths under elden_ring_artifacts and REPORTS which exist
rather than assuming one. Read-only: opens nothing for writing except the report.
"""
import argparse
import collections
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

import artifacts_root                          # noqa: E402  -- THE --path argument, not a copy

ART = artifacts_root.default_root(REPO)
CANDIDATES = ["map", "msb", "mapstudio", "map/mapstudio", "MapStudio", "map/MapStudio"]
TILE = "m60_40_39"
MARK = "宝死体"          # 宝死体 -- treasure corpse
CAP_WALK = 400000                     # hard cap: this tree is reportedly huge; never walk forever


def human(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return "%.1f%s" % (n, u)
        n /= 1024.0
    return "%.1fTB" % n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", help="the MSB directory (omit to auto-detect and report). Wins "
                                   "over --path, which only moves where auto-detection looks.")
    artifacts_root.add_path_argument(
        ap, artifacts_alias=False,
        extra_help="auto-detection then tries its usual subdirectories under DIR")
    ap.add_argument("--tile", default=TILE)
    ap.add_argument("--out", default=os.path.join(REPO, "msb_probe_report.txt"))
    ap.add_argument("--max-dump", type=int, default=40, help="max matching lines to quote")
    a = ap.parse_args()

    L = []
    def say(s=""):
        L.append(s)
        try:
            print(s)
        except UnicodeEncodeError:      # Windows console is not UTF-8; the FILE still is.
            print(s.encode("ascii", "replace").decode("ascii"))

    _art = artifacts_root.resolve(a.path) or ART
    roots = [a.root] if a.root else [os.path.join(_art, c) for c in CANDIDATES]
    say("=== ROOT DETECTION ===")
    found = []
    for r in roots:
        ok = os.path.isdir(r)
        say("  %-60s %s" % (r, "EXISTS" if ok else "-"))
        if ok:
            found.append(r)
    if not found:
        say("\nNo candidate root found. Re-run with --root <path to the MSB dir>.")
        io.open(a.out, "w", encoding="utf-8").write("\n".join(L))
        return 2
    root = found[0]
    say("\nusing: %s" % root)

    # ---- Phase 1: layout, no assumptions ----
    say("\n=== PHASE 1: LAYOUT ===")
    byext, bydepth, total, nbytes, names = collections.Counter(), collections.Counter(), 0, 0, []
    truncated = False
    for dirpath, _dirnames, filenames in os.walk(root):
        depth = dirpath[len(root):].count(os.sep)
        for fn in filenames:
            total += 1
            if total > CAP_WALK:
                truncated = True
                break
            ext = "".join(os.path.splitext(fn)[1:]) or "(none)"
            if fn.count(".") > 1:
                ext = "." + ".".join(fn.split(".")[1:])
            byext[ext] += 1
            bydepth[depth] += 1
            if len(names) < 12:
                names.append(os.path.join(dirpath[len(root):].lstrip(os.sep), fn))
            try:
                nbytes += os.path.getsize(os.path.join(dirpath, fn))
            except OSError:
                pass
        if truncated:
            break
    say("files: %d%s   bytes: %s" % (total, " (CAPPED)" if truncated else "", human(nbytes)))
    say("extensions:")
    for e, n in byext.most_common(12):
        say("   %7d  %s" % (n, e))
    say("depth histogram: %s" % dict(sorted(bydepth.items())))
    say("sample paths:")
    for n in names:
        say("   %s" % n)

    # ---- Phase 2: does the tile have MULTIPLE VERSIONS? ----
    say("\n=== PHASE 2: TILE %s ===" % a.tile)
    hits = []
    for dirpath, _d, filenames in os.walk(root):
        for fn in filenames:
            if fn.startswith(a.tile):
                hits.append(os.path.join(dirpath, fn))
    say("files whose name starts with %s: %d" % (a.tile, len(hits)))
    for h in sorted(hits)[:40]:
        try:
            say("   %-58s %s" % (os.path.basename(h), human(os.path.getsize(h))))
        except OSError:
            say("   %s" % os.path.basename(h))
    if not hits:
        say("   NONE -- the tile naming in this tree differs from the expectation. That is itself")
        say("   the answer to report; do NOT guess a different pattern.")

    # ---- Phase 3: is the corpse marker readable as text? ----
    say("\n=== PHASE 3: IS 5b9d/6b7b/4f53 (treasure-corpse marker) READABLE IN THESE FILES? ===")
    for h in sorted(hits)[:8]:
        try:
            raw = open(h, "rb").read()
        except OSError as e:
            say("   %s: unreadable (%s)" % (os.path.basename(h), e))
            continue
        kind = "DCX/packed" if raw[:4] in (b"DCX\x00", b"DCP\x00") else (
               "XML" if raw.lstrip()[:5].lower().startswith(b"<?xml") else "other/binary")
        enc_hits = []
        for enc in ("utf-8", "utf-16-le", "shift_jis"):
            try:
                if MARK.encode(enc) in raw:
                    enc_hits.append(enc)
            except Exception:
                pass
        say("   %-58s %-12s marker in: %s" % (os.path.basename(h), kind, enc_hits or "NOT FOUND"))
        if enc_hits:
            enc = enc_hits[0]
            txt = raw.decode(enc, "replace")
            n = 0
            for i, line in enumerate(txt.splitlines()):
                if MARK in line:
                    say("        L%-7d %s" % (i + 1, line.strip()[:200]))
                    n += 1
                    if n >= a.max_dump:
                        say("        ... capped at %d" % a.max_dump)
                        break

    io.open(a.out, "w", encoding="utf-8").write("\n".join(L) + "\n")
    say("\nwrote %s -- paste that file back." % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
