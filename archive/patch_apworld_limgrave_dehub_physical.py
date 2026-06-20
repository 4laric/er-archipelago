#!/usr/bin/env python3
"""
patch_apworld_limgrave_dehub_physical.py -- finish de-hubbing Limgrave (physical enforcement).

CONTEXT: the Roundtable-hub re-root LOGIC is already done + gen-tested (New Game roots at Roundtable,
"Limgrave Lock" injects when a start rolls, Limgrave demotes to a pool region). But Limgrave was never
added to the region-lock SLOT_DATA tables, so it was logic-locked yet physically OPEN, and the baker's
Roundtable KICK-retarget (which only fires `if regionOpenFlags.ContainsKey("Limgrave Lock")`) never
engaged -> the playtest kick fell through to First Step. build_region_lock_slot_data() builds the
enforcement tables from map_region_data.REGIONS x region_lock_item, and Limgrave is in NEITHER.

THIS PATCH closes that gap (no baker/client code needed -- both already handle these tables generically):

  map_region_data.py (LF):
    1. Add a "Limgrave" entry to REGIONS: area_ids [(61000,61001)] (61000 CONFIRMED in-game = First Step;
       61001 = Limgrave East, VERIFY; Weeping = 61002) + reveal_flags [62010]. SAFE/inert for normal
       seeds: build_region_lock_slot_data only emits enforcement for a region if region_lock_item maps it.
    2. Add "Limgrave": 8600 to REGION_MAP_ITEM (Map: Limgrave, West) for the unlock notification.

  __init__.py (CRLF):
    3. At the build call, pass an augmented lock map (_rli) that adds Limgrave -> "Limgrave Lock" ONLY
       when a random start rolled AND freebie == hub_only (value 0). Under to_limgrave (1) Limgrave stays
       OPEN (services freebie), and ordinary seeds are untouched (NOT added to static REGION_LOCK_ITEM).
    4. Use _rli for the lock->notify loop too, so Limgrave gets its "Map: Limgrave" ticker.

  Result under random_start + hub_only: Limgrave emits areaLockFlags [61000,61001,openflag] (physical
  KICK while locked) + lockOpenFlags["Limgrave Lock"] (-> regionOpenFlags -> baker retargets KICK to
  Roundtable, since RegionFogGates already keys off that) + lockRevealFlags (map reveal on unlock).

PREREQ: the re-root patch (patch_apworld_random_start_roundtable_hub.py) is already applied (provides
the "Limgrave Lock" item + _random_start_region). Idempotent, per-file line endings preserved.
Run on Windows (gen). __init__.py is large -- if the sandbox couldn't test-apply it, the count==1
anchor guards still make it safe; verify on the real tree.

VERIFY in playtest (hub_only, e.g. Liurnia start): you can't walk into Limgrave (61xxx) without the
lock; tripping it warps you to Roundtable (NOT First Step); Chapel/Stranded Graveyard (m10 ~18000) is
NOT in 61xxx so the tutorial start checks aren't kicked before the random-start warp moves you out.
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
MRD = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "map_region_data.py")
INIT = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "__init__.py")


def _read(p):
    with open(p, "rb") as f:
        return f.read()


def _write(p, d):
    with open(p, "wb") as f:
        f.write(d)


def _lf(t):
    return t.encode("utf-8")


def _crlf(t):
    return t.replace("\n", "\r\n").encode("utf-8")


def _ins_before(data, anchor, insert, label):
    if data.count(anchor) != 1:
        raise SystemExit(f"[FAIL] {label}: anchor x{data.count(anchor)} (want 1). No write.")
    return data.replace(anchor, insert + anchor, 1)


def _replace(data, anchor, repl, label):
    if data.count(anchor) != 1:
        raise SystemExit(f"[FAIL] {label}: anchor x{data.count(anchor)} (want 1). No write.")
    return data.replace(anchor, repl, 1)


# ---------------- map_region_data.py (LF) ----------------

MRD_REGIONS_ANCHOR = _lf('    "Weeping Peninsula":    {"area_ids": [(61002, 61002)], "reveal_flags": [62011]},\n')
MRD_REGIONS_INS = _lf(
    '    # de-hub (Roundtable re-root): area=61000 CONFIRMED in-game (First Step); 61001 = Limgrave East\n'
    '    # (VERIFY via area log); Weeping = 61002. ONLY enforced when region_lock_item maps Limgrave\n'
    '    # (random-start hub_only) -> inert for normal seeds AND for to_limgrave.\n'
    '    "Limgrave":             {"area_ids": [(61000, 61001)], "reveal_flags": [62010]},\n'
)

MRD_MAPITEM_ANCHOR = _lf('    "Weeping Peninsula": 8601,\n')
MRD_MAPITEM_INS = _lf('    "Limgrave": 8600,                    # Map: Limgrave, West -- de-hub unlock notification\n')

# ---------------- __init__.py (CRLF) ----------------

INIT_BUILD_OLD = _crlf(
    '        region_lock_sd = {"areaLockFlags": [], "lockOpenFlags": {}, "lockRevealFlags": {}}\n'
    '        if self.options.world_logic < 3:\n'
    '            region_lock_sd = build_region_lock_slot_data(REGION_LOCK_ITEM)\n'
)
INIT_BUILD_NEW = _crlf(
    '        region_lock_sd = {"areaLockFlags": [], "lockOpenFlags": {}, "lockRevealFlags": {}}\n'
    '        # Roundtable-hub re-root: when a random start rolled with the hub_only freebie, Limgrave is a\n'
    '        # normal LOCKED region. Add it to the lock map HERE (scoped -- NOT in the static\n'
    '        # REGION_LOCK_ITEM, so ordinary seeds never lock Limgrave). Under to_limgrave (freebie==1)\n'
    '        # Limgrave stays OPEN. This emits Limgrave areaLockFlags (physical KICK) +\n'
    '        # lockOpenFlags["Limgrave Lock"] (-> regionOpenFlags -> baker retargets the KICK to\n'
    '        # Roundtable) + map reveal on unlock. See [[er-random-start-roundtable-hub]].\n'
    '        _rli = dict(REGION_LOCK_ITEM)\n'
    '        if getattr(self, "_random_start_region", None) and self.options.start_region_freebie.value != 1:\n'
    '            _rli["Limgrave"] = "Limgrave Lock"\n'
    '        if self.options.world_logic < 3:\n'
    '            region_lock_sd = build_region_lock_slot_data(_rli)\n'
)

INIT_NOTIFY_OLD = _crlf('            for _region, _lock in REGION_LOCK_ITEM.items():\n')
INIT_NOTIFY_NEW = _crlf('            for _region, _lock in _rli.items():\n')


def patch_mrd(data):
    if b'"Limgrave":             {"area_ids"' in data:
        print("[skip] map_region_data.py already patched.")
        return data, False
    data = _ins_before(data, MRD_REGIONS_ANCHOR, MRD_REGIONS_INS, "MRD REGIONS Limgrave")
    data = _ins_before(data, MRD_MAPITEM_ANCHOR, MRD_MAPITEM_INS, "MRD REGION_MAP_ITEM Limgrave")
    return data, True


def patch_init(data):
    if b'_rli["Limgrave"] = "Limgrave Lock"' in data:
        print("[skip] __init__.py already patched.")
        return data, False
    data = _replace(data, INIT_BUILD_OLD, INIT_BUILD_NEW, "INIT build-call augment")
    data = _replace(data, INIT_NOTIFY_OLD, INIT_NOTIFY_NEW, "INIT notify loop")
    return data, True


def main():
    for p in (MRD, INIT):
        if not os.path.isfile(p):
            raise SystemExit(f"[FAIL] not found: {p}")
    m = _read(MRD)
    m2, mc = patch_mrd(m)
    i = _read(INIT)
    i2, ic = patch_init(i)
    if mc:
        _write(MRD, m2)
        print("[ok] patched map_region_data.py (Limgrave in REGIONS + REGION_MAP_ITEM)")
    if ic:
        _write(INIT, i2)
        print("[ok] patched __init__.py (scoped Limgrave lock-map augment + notify)")
    if not (mc or ic):
        print("[done] nothing to do.")
    else:
        print("[done] Limgrave physical de-hub applied. gen-test a random_start_region + "
              "start_region_freebie=hub_only seed; confirm areaLockFlags/regionOpenFlags include "
              "'Limgrave Lock'. Rebuild eldenring.apworld if you distribute it.")


if __name__ == "__main__":
    main()
