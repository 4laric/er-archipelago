#!/usr/bin/env python3
r"""
Cleanup: remove the ap_shopbind diagnostic + the (no-op) full-member fallback from
ArchipelagoForm.cs, restoring the original 2-statement placement/removal call site.

The real Moore-shop fixes stay untouched:
  - FindMatchingSlotKey quantity-strip + enriched ambiguous warning (patch_moore_shop_namematch)
  - diste\Names DLC-name merge (patch_dlc_names_merge)
  - AnnotationData dup-config-name skip (patch_annotation_dupconfig_skip)
  - Permutation DLC key-item skip (patch_permutation_dlc_keyitem_skip)

This only reverts the scaffolding from patch_moore_grocery_candidates: the fullMembers/
placeCandidates fallback (which proved to be a no-op once names were the real fix) and the
ap_shopbind_*.txt dump. Restores:

    var targetSlotKey = FindMatchingSlotKey(
        session, game, data.Location(targetScope), info);
    AddMulti(itemsToRemove, targetSlotKey, FindMatchingSlotKey(
        session, game, data.Locations[targetScope], info));

CRLF + UTF-8-BOM safe, range-based, idempotent. Needs a -Randomizer rebuild.
"""
import io, os, sys

CS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                  "SoulsRandomizers", "RandomizerCommon", "ArchipelagoForm.cs")

J = "                "  # 16-space indent
NEW = [
    J + 'var targetSlotKey = FindMatchingSlotKey(',
    J + '    session, game, data.Location(targetScope), info);',
    J + 'AddMulti(itemsToRemove, targetSlotKey, FindMatchingSlotKey(',
    J + '    session, game, data.Locations[targetScope], info));',
]

START_NEEDLE = "// data.Location(targetScope) is the *filtered* base-target list"
END_NEEDLE = "session, game, fullMembers, info));"


def main():
    raw = io.open(CS, "r", encoding="utf-8-sig", newline="").read()
    nl = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.split(nl)

    if "ap_shopbind" not in raw and "fullMembers" not in raw:
        print("Already clean (no scaffolding present). No change.")
        return 0

    start = end = None
    for i, ln in enumerate(lines):
        if start is None and START_NEEDLE in ln:
            start = i
        elif start is not None and END_NEEDLE in ln:
            end = i
            break
    if start is None or end is None:
        print("ABORT: scaffolding block boundaries not found (no change).")
        return 2

    out = lines[:start] + NEW + lines[end + 1:]
    tmp = CS + ".tmp"
    io.open(tmp, "w", encoding="utf-8-sig", newline="").write(nl.join(out))
    os.replace(tmp, CS)
    print(f"Removed scaffolding (lines {start + 1}-{end + 1}); restored original call site.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
