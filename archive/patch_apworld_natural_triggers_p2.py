#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
patch_apworld_natural_triggers_p2.py

P2 of the natural-key-triggers feature. Adds region-lock APPARATUS (graces / dedicated
open-flag / map-reveal / notify token) for TWO MORE natural-key regions -- Raya Lucaria
Academy and Volcano Manor -- and EXTENDS the slot_data table `naturalKeyTriggers` so the
runtime client blooms each region's apparatus on a vanilla disjunctive trigger (a key
ITEM received and/or a world FLAG set), with NO synthetic AP lock item required.

REQUIRES P1 FIRST. P1 (patch_apworld_natural_triggers.py) is already applied to the live
source: it inserted, in fill_slot_data, an apparatus block bounded by
    # === NATURAL_KEY_TRIGGERS_PATCH: ...
    # === end NATURAL_KEY_TRIGGERS_PATCH ===
that creates `natural_key_triggers = {...}` and mutates `region_graces`,
`region_open_flags`, `region_lock_sd["lockRevealFlags"]`, `lock_notify_items` for
Mountaintops/Snowfield/Altus, plus a `"naturalKeyTriggers": natural_key_triggers,` key in
the return dict. This patch anchors on the P1 END-MARKER line and inserts the P2 block
IMMEDIATELY AFTER it, so all of those names already exist and we EXTEND them (never
overwrite). We assert the P1 marker is present and error out telling the user to apply P1
first if it is missing.

CLIENT: NO CHANGE NEEDED. The client's CCore::EvaluateNaturalKeyTriggers iterates EVERY
naturalKeyTriggers entry generically:
    for (const auto& nk : naturalKeyTriggers) { ... regionOpenFlags.find(name) ... }
It blooms any entry whose name has matching regionGraces/regionOpenFlags/lockRevealFlags/
lockNotifyItems -- there is no hardcoded set of lock names. So adding two more entries +
their apparatus is purely an apworld change.

------------------------------------------------------------------------------------------
RECONCILIATION (investigated against the live source):

* "Raya Lucaria Lock": DOES NOT EXIST as a lock item. Raya Lucaria Academy is gated in
  __init__.py by the vanilla ITEM "Academy Glintstone Key" (entrance rule at ~:1883), with
  an alternate entry via "Academy Glintstone Key (Thops)" (~:2712). There is no
  REGION_LOCK_ITEM entry, no REGION_GRACE_POINTS entry, no REGIONS entry, so the standard
  apparatus loops mint NOTHING for it. => MINT FRESH apparatus under the name
  "Raya Lucaria Lock" (the trigger key) so the client has something to bloom. This mirrors
  the P1 Mountaintops/Snowfield fresh-mint case (NOT the additive Altus case).

* "Volcano Lock": EXISTS as a lock ITEM in items.py (lock=True) and is used by entrance
  rules ("Volcano Manor Entrance"/"Volcano Manor Dungeon", ~:2178-2179). BUT it is NOT a
  value in grace_data.REGION_LOCK_ITEM, NOT in REGION_GRACE_POINTS, and "Volcano Manor"
  is NOT a key in map_region_data.REGIONS. Therefore:
    - region_graces       : has NO "Volcano Lock" entry (the REGION_GRACE_POINTS loop never
                            sees it).
    - region_open_flags   : has NO "Volcano Lock" entry (build_region_lock_slot_data only
                            mints open flags for REGION_LOCK_ITEM values via REGIONS).
    - lock_notify_items   : DOES contain "Volcano Lock" (the loop over item_table lock=True
                            items adds it with the 2900 fallback token).
  So "Volcano Lock" has a logic item + a notify token but NO grace/open apparatus. Without
  an open flag the client's bloom guard skips it. => MINT FRESH grace bundle + open flag +
  (empty) reveal for "Volcano Lock". lock_notify_items already has it (setdefault leaves
  the existing 2900 token in place). This is fresh-mint of the MISSING apparatus, matching
  the requirement "exists only as a logic item with NO apparatus -> mint fresh".

------------------------------------------------------------------------------------------
APPARATUS minted here (gated on world_logic < 3, same scope as P1):

* Open-flags (grace-tail gap, confirmed free across the whole apworld .py tree):
    "Raya Lucaria Lock": 76962
    "Volcano Lock":      76963
  (76961 Snowfield, 76996 Mountaintops, 76997 Morne, 76998 Godrick already used; 76962/
  76963 are unused anywhere.)

* Grace lists (from elden_ring_artifacts/grace_flags.tsv warpUnlockFlag, interior local
  coords):
    Raya Lucaria Academy  m14_00_00 -> 71400, 71401, 71402, 71403  (all four; no boss/
        border tile in this set; "Raya Lucaria Crystal Tunnel" is a SEPARATE dungeon
        (liurnia_tunnel) with no m14_00 grace, so nothing to exclude). HIGH confidence.
    Volcano Manor         m16_00_00 -> 71601, 71602, 71603, 71604, 71605, 71606, 71607
        EXCLUDING 71600: 71600 (rowId 160000) is ALREADY committed to
        grace_data.BUNDLE_LOCK_GRACES["Spelunker's Torch"] (limgrave_underground bundle,
        labelled "Murkwater Cave"). Both Volcano Manor and Murkwater Cave share the m16_00
        overworld-container map id, so 71600's true owner is ambiguous; rather than
        double-assign it we drop it and keep the 7 unambiguous manor graces. MEDIUM-HIGH
        confidence (the 7 kept flags appear nowhere else in the tree).

* Reveal flags: EMPTY for both. Raya Lucaria Academy and Volcano Manor are interior
  dungeons with NO dedicated world-map pillar / map fragment (there is no
  "Map: Raya Lucaria" or "Map: Volcano Manor" item; they're covered by the Liurnia / Altus
  overworld maps). So there is nothing to reveal -- we add no lockRevealFlags entry.

* Notify token: FALLBACK 2900 (Golden Rune [1], the apworld's _NOTIFY_TOKEN for map-less
  locks), packed with 0x40000000, via setdefault. "Volcano Lock" already has this token
  from the P1-era lock_notify_items loop (setdefault is a no-op there); "Raya Lucaria Lock"
  has no item so we add it here.

------------------------------------------------------------------------------------------
NATURAL TRIGGERS added (EXTEND natural_key_triggers, never overwrite):

  "Raya Lucaria Lock": {"anyOf": [
      {"items": ["Academy Glintstone Key"]},
      {"items": ["Academy Glintstone Key (Thops)"]},
  ]}
  "Volcano Lock": {"anyOf": [
      {"flags": [400072]},                       # Drawing-Room Key obtained-flag (join VM)
      {"items": ["Academy Glintstone Key"]},      # Abductor Virgin route via Raya Lucaria
      {"items": ["Mt. Gelmir Lock"]},             # walk-down from Mt. Gelmir
  ]}

Both confirmed against the live source:
  - "Academy Glintstone Key" (items.py:1611) and "Academy Glintstone Key (Thops)"
    (items.py:1651) both exist.
  - 400072 = Drawing-Room Key obtained-flag (locations.py:3366, "join volcano manor").
  - "Mt. Gelmir Lock" is the exact REGION_LOCK_ITEM value for 'Mt. Gelmir' (grace_data.py
    :27) and the exact item name (items.py:2171).

WARP-LOOP: "Raya Lucaria Lock" is NOT in REGION_LOCK_ITEM nor _EXTRA_LOCK_KEYS, so the
warp-access loop never adds a state.has rule for it (no item exists). "Volcano Lock" is an
existing logic item with its own entrance rules; we do NOT change its logic or REGION_LOCK_
ITEM membership (it has none), so no warp-loop interaction changes. Apparatus + slot_data
only.

CONVENTIONS: CRLF-safe (read bytes/decode, replace, encode/write), backs up to
<file>.bak_naturaltriggersp2, idempotent via the NATURAL_KEY_TRIGGERS_P2 marker, asserts
every anchor present (raises if missing). Requires the P1 marker to be present.

Run on Windows:  python patch_apworld_natural_triggers_p2.py
"""

import os
import sys

TAG = "naturaltriggersp2"
MARKER = "NATURAL_KEY_TRIGGERS_P2"          # idempotency sentinel embedded in inserted code
P1_MARKER = "NATURAL_KEY_TRIGGERS_PATCH"    # P1 must be applied first
APWORLD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "Archipelago", "worlds", "eldenring")
INIT = os.path.join(APWORLD, "__init__.py")

# The P1 end-marker line. We insert the P2 block IMMEDIATELY AFTER this line, so the P1
# apparatus (natural_key_triggers, region_graces, region_open_flags, region_lock_sd,
# lock_notify_items mutations) is all in place and we extend it.
P1_END_MARKER = (
    "        # === end NATURAL_KEY_TRIGGERS_PATCH ================================================================"
)


# ---------------------------------------------------------------------------------------
# Inserted P2 block. Indented at 8 spaces (method-body level, same as the P1 block) and
# self-guarded by `if self.options.world_logic < 3:` to match the P1 scope. Placed right
# after the P1 end-marker, so it EXTENDS the dicts P1 built. natural_key_triggers always
# exists (P1 initialises it to {} before its own `if`), so .update() is always safe.
# ---------------------------------------------------------------------------------------
P2_BLOCK = '''
        # === {marker}: natural-key apparatus + triggers (Raya Lucaria + Volcano Manor) =======
        # Two more natural-key regions, EXTENDING the P1 apparatus above (natural_key_triggers,
        # region_graces, region_open_flags, region_lock_sd["lockRevealFlags"], lock_notify_items
        # all already exist). Raya Lucaria Academy has NO lock item (gated by vanilla Academy
        # Glintstone Key); Volcano Manor's "Volcano Lock" is a logic item with NO grace/open
        # apparatus. Both need fresh apparatus so the client (generic EvaluateNaturalKeyTriggers)
        # can bloom them; the triggers are vanilla key items / the Drawing-Room obtained-flag.
        # Gated to region-gating modes (world_logic < 3), same as P1.
        if self.options.world_logic < 3:
            _NK2_GRACES = {{
                # Raya Lucaria Academy interior (m14_00_00 grace_flags.tsv warpUnlockFlags).
                "Raya Lucaria Lock": [71400, 71401, 71402, 71403],
                # Volcano Manor interior (m16_00_00); 71600 EXCLUDED -- already owned by
                # BUNDLE_LOCK_GRACES["Spelunker's Torch"] (Murkwater Cave shares the m16 tile id).
                "Volcano Lock":      [71601, 71602, 71603, 71604, 71605, 71606, 71607],
            }}
            _NK2_OPEN = {{"Raya Lucaria Lock": 76962, "Volcano Lock": 76963}}
            for _n2k, _n2fs in _NK2_GRACES.items():
                region_graces[_n2k] = sorted(set(region_graces.get(_n2k, []) + list(_n2fs)))
            for _n2k, _n2of in _NK2_OPEN.items():
                region_open_flags[_n2k] = _n2of
            # No map pillars: Raya/Volcano are interiors with no dedicated map fragment, so no
            # lockRevealFlags are added. Notify falls back to the map-less token (2900, packed),
            # matching the apworld's _NOTIFY_TOKEN; setdefault leaves any existing token in place
            # (Volcano Lock already has the 2900 token from the lock_notify_items loop above).
            for _n2k in ("Raya Lucaria Lock", "Volcano Lock"):
                lock_notify_items.setdefault(_n2k, 2900 | 0x40000000)
            # Disjunctive natural triggers (EXTEND, do not overwrite). A clause = ALL items
            # received AND ALL flags set; ANY clause fires the bloom.
            natural_key_triggers.update({{
                "Raya Lucaria Lock": {{"anyOf": [
                    {{"items": ["Academy Glintstone Key"]}},
                    {{"items": ["Academy Glintstone Key (Thops)"]}},
                ]}},
                "Volcano Lock": {{"anyOf": [
                    {{"flags": [400072]}},                  # Drawing-Room Key obtained-flag (join Volcano Manor)
                    {{"items": ["Academy Glintstone Key"]}},  # Abductor Virgin route via Raya Lucaria
                    {{"items": ["Mt. Gelmir Lock"]}},         # walk-down from Mt. Gelmir
                ]}},
            }})
        # === end {marker} ===================================================================
'''.format(marker=MARKER)


def _read(path):
    with open(path, "rb") as f:
        return f.read().decode("utf-8")


def _write(path, text):
    with open(path, "wb") as f:
        f.write(text.encode("utf-8"))


def _backup(path):
    bak = path + ".bak_" + TAG
    if not os.path.exists(bak):
        with open(bak, "wb") as f:
            f.write(_read(path).encode("utf-8"))
        print("  backup -> %s" % os.path.basename(bak))
    else:
        print("  backup already exists: %s" % os.path.basename(bak))


def main():
    if not os.path.exists(INIT):
        print("ERROR: %s not found" % INIT)
        return 1
    src = _read(INIT)

    # Idempotency.
    if MARKER in src:
        print("already applied (marker %r present in __init__.py)" % MARKER)
        return 0

    # P1 must be applied first.
    if P1_MARKER not in src:
        print("ERROR: P1 marker %r not found in __init__.py." % P1_MARKER)
        print("       Apply patch_apworld_natural_triggers.py (P1) FIRST, then re-run this.")
        return 1

    # Anchor must be present and unique. We match on either CRLF or LF line endings by
    # normalising the search (the file is read/decoded to text, so newlines are '\n' here).
    anchor = P1_END_MARKER
    if anchor not in src:
        print("ERROR: P1 end-marker anchor not found:")
        print("       %r" % anchor)
        return 1
    if src.count(anchor) != 1:
        print("ERROR: P1 end-marker anchor not unique (count=%d)" % src.count(anchor))
        return 1

    # Insert the P2 block immediately AFTER the P1 end-marker line. P2_BLOCK begins with a
    # newline, so it slots cleanly onto the next line.
    new_src = src.replace(anchor, anchor + P2_BLOCK, 1)
    if new_src == src:
        print("ERROR: replace() made no change despite anchor match.")
        return 1

    _backup(INIT)
    _write(INIT, new_src)
    print("patched __init__.py")
    print("  + P2 apparatus (Raya Lucaria Lock / Volcano Lock graces + open flags 76962/76963)")
    print("  + naturalKeyTriggers extended (Raya Lucaria Lock + Volcano Lock)")
    print("\nNOTE: client needs NO change -- EvaluateNaturalKeyTriggers iterates every entry.")
    print("DONE. Regen on Windows to emit the extended slot_data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
