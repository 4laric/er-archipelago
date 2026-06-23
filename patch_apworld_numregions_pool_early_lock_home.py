#!/usr/bin/env python3
r"""patch_apworld_numregions_pool_early_lock_home.py

Fix the seed-dependent  Fill.FillError: No more spots to place 1 items  thrown by
num_regions  num_regions_rune_source: pool  whenever the failing roll SEALS Limgrave.

ROOT CAUSE (Archipelago/worlds/eldenring/__init__.py)
-----------------------------------------------------
"Limgrave Lock" (items.py: a real lock=True item) is the ONE region lock that is
NEVER owned by a SPINE step (region_spine.SPINE[0] / Limgrave has locks=set()), so it
is never in the kept-lock set (_kept_l) and is always in _spine_sealed_locks. The
generic lock-injection block therefore sets it inject=False -- correct.

But the num_regions POOL Roundtable re-root block then force-flips it back ON,
UNCONDITIONALLY:

        self._random_start_region = _ns_start
        if "Limgrave Lock" in item_table:
            item_table["Limgrave Lock"].inject = True      # <-- the bug

This injects Limgrave Lock into the random progression pool EVEN ON ROLLS WHERE
Limgrave (pool step 1) was NOT picked -- i.e. Limgrave is SEALED. A sealed region's
checks are turned into locked-vanilla EVENTS and its locked items downgraded to
filler (create_regions), so a sealed Limgrave opens NO real, reachable checks. The
injected Limgrave Lock is then a progression item whose only "destination" region is
sealed: receiving it unlocks nothing new, so fill_restrictive can only ever seat it in
an already-reachable slot. The hub is Roundtable Hold, and almost all its checks are
missable (-> EXCLUDED from progression under the default missable_location_behavior =
forbid_useful) or shops; the handful of real sphere-0 slots get consumed by the other
region locks + the pool-injected great runes first. On seed 2110896624565121995 that
left Limgrave Lock with no valid early home -- the only OPEN locations were Golden
Seed / Sacred Tear slots in still-locked LATER regions (Altus / Leyndell / Capital
Outskirts) -- hence "No more spots to place 1 items".

Limgrave Lock is UNIQUELY exposed to this: every other lock is injected only when its
region is kept (it rides _kept_l), so it always opens real content; only Limgrave Lock
is re-injected after the sealed-lock sweep, regardless of whether Limgrave is kept.

THE FIX (minimal, count-neutral, reuses existing machinery)
-----------------------------------------------------------
Inject Limgrave Lock ONLY when the Limgrave REGION is actually KEPT this roll. When
Limgrave is sealed, leave it inject=False (already set by the sealed-lock sweep) so it
never enters the pool -- there is nothing for it to open. Count stays neutral: one
fewer mandatory injectable means the create_items demand-drop frees one fewer filler
slot, so that filler simply stays in the pool (the same slot-free machinery, run a
notch less). When Limgrave IS kept, behaviour is byte-for-byte unchanged.

This matches the pool design intent ("pool exists to ADD flexibility"): it removes a
dead progression item that pool mode was forcing in, rather than switching rune_source.
The slot-data side is unaffected -- _rli["Limgrave"] = "Limgrave Lock" still emits the
physical KICK so a sealed Limgrave stays barred (its lock is simply unobtainable, the
correct state for a sealed region), exactly like every other sealed region.

CHANGE
------
    if "Limgrave Lock" in item_table:                                  (12-space indent)
becomes
    if "Limgrave Lock" in item_table and "Limgrave" not in getattr(self, "_spine_sealed_regions", set()):

The anchor is the 12-space-indented condition line, which (verified) is UNIQUE in the
file -- the other "Limgrave Lock" inject lines are at 8-space (the inject=False reset)
and 20-space (the YAML random_start_region path) indents. The anchor contains NO
newline, so it is line-ending agnostic (the source is CRLF on Windows; some mounts
serve it as LF). Does NOT touch the ~L584 pool resolver log line (owned by a parallel
task).

USAGE (Windows, from the repo root):
    python patch_apworld_numregions_pool_early_lock_home.py
    .\build.ps1 -Apworld
    .\gen_sweep.ps1 -Seeds 2110896624565121995      # must now PASS
    .\gen_sweep.ps1 -Count 80                        # want 100%
"""
import os, sys

REPO = os.path.dirname(os.path.abspath(__file__))

# Canonical world slot. If a gen_sweep is mid-run it may have renamed the dir aside
# (eldenring.__apsweep_aside_*); target the canonical path, else fall back to the most
# recent aside copy so the patch still lands on the live source.
_WORLDS = os.path.join(REPO, "Archipelago", "worlds")
_CANON = os.path.join(_WORLDS, "eldenring", "__init__.py")


def _resolve_target():
    if os.path.isfile(_CANON):
        return _CANON
    # mid-sweep fallback: newest eldenring.__apsweep_aside_* with an __init__.py
    try:
        asides = sorted(
            (d for d in os.listdir(_WORLDS)
             if d.startswith("eldenring.__apsweep_aside_")
             and os.path.isfile(os.path.join(_WORLDS, d, "__init__.py"))),
            reverse=True,
        )
    except OSError:
        asides = []
    if asides:
        print("WARNING: canonical worlds/eldenring not found (gen_sweep mid-run?); "
              f"patching the aside copy {asides[0]} instead.")
        return os.path.join(_WORLDS, asides[0], "__init__.py")
    return _CANON  # report the canonical miss below


# 12-space indent => unique to the num_regions pool Roundtable re-root block (the
# 8-space reset and the 20-space YAML path are distinct). No newline => CRLF/LF safe.
ANCHOR  = b'            if "Limgrave Lock" in item_table:'
REPLACE = (b'            if "Limgrave Lock" in item_table'
           b' and "Limgrave" not in getattr(self, "_spine_sealed_regions", set()):')
ALREADY = b'"Limgrave" not in getattr(self, "_spine_sealed_regions", set()):'  # idempotency marker

TAIL_SYMBOL = b"interpret_slot_data"   # EOF anchor: prove we read the whole file


def main():
    target = _resolve_target()
    if not os.path.isfile(target):
        sys.exit(f"ERROR: not found: {target}")
    size = os.path.getsize(target)
    with open(target, "rb") as f:
        data = f.read()

    # read-truncation guard (a short / stale mount read must NOT be written back)
    if len(data) != size:
        sys.exit(f"ERROR: short read ({len(data)} != {size} bytes) -- I/O truncation; aborting, no write.")
    if TAIL_SYMBOL not in data:
        sys.exit(f"ERROR: tail symbol {TAIL_SYMBOL!r} missing -- source looks truncated; aborting, no write.")

    if ALREADY in data:
        print("Already patched -- Limgrave Lock injection is already guarded on a kept Limgrave. No change.")
        return

    n = data.count(ANCHOR)
    if n != 1:
        sys.exit(f"ERROR: expected exactly 1 anchor occurrence, found {n}. Aborting (no write). "
                 f"(Anchor = the 12-space-indented `if \"Limgrave Lock\" in item_table:`.)")

    new = data.replace(ANCHOR, REPLACE, 1)
    expected = len(data) + (len(REPLACE) - len(ANCHOR))
    if len(new) != expected or ALREADY not in new or TAIL_SYMBOL not in new or new.count(REPLACE) != 1:
        sys.exit("ERROR: post-replace sanity check failed. Aborting (no write).")

    bak = target + ".bak_poolearlylockhome"
    with open(bak, "wb") as f:
        f.write(data)
    with open(target, "wb") as f:
        f.write(new)

    # verify the bytes that actually landed on disk
    with open(target, "rb") as f:
        chk = f.read()
    if ALREADY not in chk or TAIL_SYMBOL not in chk or len(chk) != expected:
        sys.exit(f"ERROR: verification AFTER write FAILED. Restore from {bak}")

    print("OK: Limgrave Lock now injected into the pool only when the Limgrave region is KEPT.")
    print(f"  target : {target}")
    print(f"  backup : {bak}")
    print(f"  size   : {size} -> {len(chk)} (+{len(chk) - size} bytes)")
    print("Next: .\\build.ps1 -Apworld  (repackage), then")
    print("      .\\gen_sweep.ps1 -Seeds 2110896624565121995   (must PASS)")
    print("      .\\gen_sweep.ps1 -Count 80                     (want 100%)")


if __name__ == "__main__":
    main()
