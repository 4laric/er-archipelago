#!/usr/bin/env python3
"""
patch_apworld_gelmir_border_graces.py -- REBUCKET the Mt. Gelmir grace bundle onto the Altus lock.

(REPLACES the earlier piecemeal "_BORDER exclude" version of this file. If you already ran that
exclusion version, git-restore Archipelago/worlds/eldenring/__init__.py first so we start clean --
this patch expects the ORIGINAL 8-flag _BORDER set and an un-redirected grace loop.)

WHY: All seven graces in REGION_GRACE_POINTS['Mt. Gelmir'] sit on m60_3x_5x tiles -- the Altus
overworld grid -- so every one of them reports the ALTUS play-region (63xxx). Mt. Gelmir has no
enforced area_ids of its own (map_region_data REGIONS['Mt. Gelmir'].area_ids == []). So holding only
the Mt. Gelmir Lock and warping to ANY Gelmir grace lands you in the still-locked Altus play-region and
the region-lock poll kicks you. Alaric confirmed this for Ninth Mt. Gelmir Campsite (76352), Road of
Iniquity (76353), Seethewater River (76354), Seethewater Terminus (76355), and Primeval Sorcerer Azur
(76357); the other two (73204, 76351) were already excluded as Gelmir/Altus border graces. In short:
the WHOLE region reads as Altus, so excluding them one by one would leave the Gelmir Lock with zero warp
graces.

FIX: in the region_graces bundling loop, redirect Mt. Gelmir's grace points to the ALTUS Lock instead
of the Mt. Gelmir Lock. They then warp-unlock when the player holds the Altus Lock -- by which point
they're standing in an open Altus play-region, so no kick. The Mt. Gelmir Lock remains a pure AP-logic
gate on the region's CHECKS (it never provided physical enforcement, area_ids being empty). The
existing _SKIP_GRACE_FLAGS filter still drops 73204 / 76351, so those two stay un-warped (conservative;
they're the only Gelmir graces in the pre-existing _BORDER set).

Target: Archipelago/worlds/eldenring/__init__.py (CRLF). Byte-level replace to preserve CRLF (the Edit
tool truncates CRLF source). Idempotent; verifies on disk. Run on Windows, then re-gen + re-bake.
No client build needed (slot_data shape unchanged -- the same flags, under a different lock key).
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "__init__.py")

OLD = (
    "                _lock = REGION_LOCK_ITEM.get(_region)\r\n"
    "                _points = [p for p in _points if p[0] not in _SKIP_GRACE_FLAGS]"
)
NEW = (
    "                _lock = REGION_LOCK_ITEM.get(_region)\r\n"
    "                # Mt. Gelmir REBUCKET: all its grace tiles are m60_3x_5x -> they report the Altus\r\n"
    "                # play-region (63xxx) and Mt. Gelmir has no enforced area_ids, so they must ride the\r\n"
    "                # ALTUS Lock -- under the Gelmir Lock alone, warping to them kicks you out of locked\r\n"
    "                # Altus. The Gelmir Lock stays a pure logic gate on Gelmir's checks. (Alaric 2026-06-20)\r\n"
    "                if _region == \"Mt. Gelmir\" and REGION_LOCK_ITEM.get(\"Altus Plateau\"):\r\n"
    "                    _lock = REGION_LOCK_ITEM[\"Altus Plateau\"]\r\n"
    "                _points = [p for p in _points if p[0] not in _SKIP_GRACE_FLAGS]"
)

SENTINEL = b"Mt. Gelmir REBUCKET"
EXCLUSION_MARK = b"76353, 76354, 76355"  # left behind by the superseded exclusion version


def main():
    if not os.path.isfile(TARGET):
        sys.exit("ERROR: not found: %s" % TARGET)

    with open(TARGET, "rb") as f:
        data = f.read()

    if SENTINEL in data:
        print("Already patched (Mt. Gelmir rebucket); nothing to do.")
        return

    if EXCLUSION_MARK in data:
        sys.exit("ERROR: the superseded _BORDER-exclusion version was already applied. "
                 "git-restore __init__.py first, then run this rebucket patch. Aborting; no write.")

    old_b = OLD.encode("utf-8")
    new_b = NEW.encode("utf-8")
    n = data.count(old_b)
    if n != 1:
        sys.exit("ERROR: loop anchor found %d times (expected 1). Aborting; no write." % n)

    before = len(data)
    out = data.replace(old_b, new_b, 1)
    if len(out) != before - len(old_b) + len(new_b):
        sys.exit("ERROR: unexpected length after replace. Aborting; no write.")

    with open(TARGET, "wb") as f:
        f.write(out)

    with open(TARGET, "rb") as f:
        chk = f.read()
    assert SENTINEL in chk, "VERIFY FAILED: sentinel missing"
    assert chk.count(b'_lock = REGION_LOCK_ITEM["Altus Plateau"]') == 1, "VERIFY FAILED: redirect missing"
    print("Patched + verified on disk: %s" % TARGET)
    print("Next: re-gen + re-bake. No client build needed.")


if __name__ == "__main__":
    main()
