#!/usr/bin/env python3
"""
patch_apworld_limgrave_lock_graces.py -- bundle the Limgrave/Stormhill warp-unlock graces onto the
Limgrave Lock so the random-start hub_only re-root makes Limgrave fast-travelable on lock receipt.

WHY: Under world_logic=region_lock + random_start_region + start_region_freebie != to_limgrave,
Limgrave is demoted to a normal LOCKED region (Roundtable becomes the hub) and "Limgrave Lock" is a
real injected progression item that gates Limgrave's warp-access (__init__.py L2470). BUT Limgrave has
NO entry in REGION_GRACE_POINTS -- its graces normally ride the free-hub start grant via
LIMGRAVE_START_GRACES, which is imported into __init__.py and then NEVER consumed. So the region_graces
bundling loop grants nothing to "Limgrave Lock": receiving it opens Limgrave but warp-unlocks ZERO
graces, leaving the player to walk in and re-discover every Site of Grace by hand.

FIX: in the region_graces builder (after the geographic-bundle dedup loop), bundle LIMGRAVE_START_GRACES
onto "Limgrave Lock", gated on the SAME condition as the _rli["Limgrave"] = "Limgrave Lock" injection
(random start + freebie != to_limgrave). LIMGRAVE_START_GRACES is already curated safe (boss graces +
the Caelid-border grace 73207 excluded, so none warp into a locked play-region). Inert on every other
seed (condition false => key never added). Mirrors how every other region lock gets its graces.

Target: Archipelago/worlds/eldenring/__init__.py (CRLF). Byte-level replace to preserve CRLF (the Edit
tool truncates CRLF source). Idempotent; verifies on disk. Run on Windows, then re-gen + re-bake.
No client build needed (slot_data shape unchanged -- just another lock in regionGraces).

NOTE: this only takes effect once the Roundtable-hub re-root actually injects Limgrave Lock at gen
time. The grace wiring is ready regardless; it stays inert until then.
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "__init__.py")

OLD = (
    "            for _lock in region_graces:\r\n"
    "                region_graces[_lock] = sorted(set(region_graces[_lock]))"
)
NEW = (
    "            for _lock in region_graces:\r\n"
    "                region_graces[_lock] = sorted(set(region_graces[_lock]))\r\n"
    "            # Limgrave Lock (random-start hub_only re-root): Limgrave is a normal LOCKED region but\r\n"
    "            # has NO REGION_GRACE_POINTS entry -- its graces normally ride the free-hub start grant\r\n"
    "            # (LIMGRAVE_START_GRACES, otherwise unused). Bundle those curated Limgrave/Stormhill warp-\r\n"
    "            # unlock graces onto Limgrave Lock so receiving it makes the region fully fast-travelable,\r\n"
    "            # same as every other region lock. Same gate as the _rli[\"Limgrave\"] injection below.\r\n"
    "            if getattr(self, \"_random_start_region\", None) and self.options.start_region_freebie.value != 1:\r\n"
    "                region_graces[\"Limgrave Lock\"] = sorted(set(\r\n"
    "                    region_graces.get(\"Limgrave Lock\", []) + list(LIMGRAVE_START_GRACES)))"
)

SENTINEL = b'region_graces["Limgrave Lock"] = sorted(set('


def main():
    if not os.path.isfile(TARGET):
        sys.exit("ERROR: not found: %s" % TARGET)

    with open(TARGET, "rb") as f:
        data = f.read()

    if SENTINEL in data:
        print("Already patched (Limgrave Lock graces); nothing to do.")
        return

    old_b = OLD.encode("utf-8")
    new_b = NEW.encode("utf-8")
    n = data.count(old_b)
    if n != 1:
        sys.exit("ERROR: anchor found %d times (expected 1). Aborting; no write." % n)

    before = len(data)
    out = data.replace(old_b, new_b, 1)
    if len(out) != before - len(old_b) + len(new_b):
        sys.exit("ERROR: unexpected length after replace. Aborting; no write.")

    with open(TARGET, "wb") as f:
        f.write(out)

    # Verify on disk.
    with open(TARGET, "rb") as f:
        chk = f.read()
    assert SENTINEL in chk, "VERIFY FAILED: sentinel missing"
    assert chk.count(b"LIMGRAVE_START_GRACES") == 2, \
        "VERIFY FAILED: expected LIMGRAVE_START_GRACES x2 (import + use), got %d" % chk.count(b"LIMGRAVE_START_GRACES")
    print("Patched + verified on disk: %s" % TARGET)
    print("Next: re-gen + re-bake. No client build needed.")


if __name__ == "__main__":
    main()
