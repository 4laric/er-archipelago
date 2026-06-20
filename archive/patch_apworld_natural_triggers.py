#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
patch_apworld_natural_triggers.py

Add region-lock APPARATUS (graces / open-flag / map-reveal / notify token) for two NEW
natural-key regions -- Mountaintops of the Giants and Consecrated Snowfield -- and emit a
new slot_data table `naturalKeyTriggers` that the runtime client uses to BLOOM each region's
apparatus on vanilla disjunctive triggers (medallion receipt AND/OR a world flag) instead of
on receiving a synthetic lock item.

These regions add NO pool items, do NOT inject, are NOT in _EXTRA_LOCK_KEYS, and the existing
AP fill LOGIC gates for Mountaintops/Snowfield (Rold / Haligtree medallions + soft-logic
Morgott) are left untouched. This patch is apparatus + slot_data only.

WARP-LOOP EXCLUSION: the warp-access loop (_region_lock_warp_access, ~__init__.py:2042)
iterates grace_data.REGION_LOCK_ITEM and adds add_rule(warp, state.has("<lock>")). We do NOT
add "Mountaintops Lock"/"Snowfield Lock" to REGION_LOCK_ITEM (their bloom is client-side off
the natural triggers, with no item to .has), so that loop never sees them -- no exclusion
needed. The bundle-warp sub-loop keys off _EXTRA_LOCK_KEYS, which we also don't touch.

NEW slot_data table (exact schema):
  "naturalKeyTriggers": {
    "Mountaintops Lock": {"anyOf": [ {"items": ["Rold Medallion"], "flags": [11000800]} ]},
    "Snowfield Lock":    {"anyOf": [ {"items": ["Haligtree Secret Medallion (Left)",
                                                "Haligtree Secret Medallion (Right)"],
                                      "flags": [11000800]} ]},
    "Altus Lock":        {"anyOf": [ {"items": ["Dectus Medallion (Left)",
                                                "Dectus Medallion (Right)"]},
                                     {"flags": [39200800]},
                                     {"flags": [400072]} ]}
  }
A clause is satisfied when ALL its "items" are received AND ALL its "flags" are set; the
trigger fires when ANY clause is satisfied. "Altus Lock" is ADDITIVE -- its existing
item-receipt bloom (regionGraces/regionOpenFlags) stays; this only adds natural-route triggers.

APPARATUS minted here (gated on world_logic < 3, the region-gating modes):
  "Mountaintops Lock": open-flag 76996;
      graces = Forbidden Lands [76500,76501,76502]
             + Mountaintops overworld [76503..76510, 76520..76524];
      map reveal = Mountaintops pillars [62050, 62051].
  "Snowfield Lock":    open-flag 76961;
      graces = [76550, 76551, 76652, 76653];
      map reveal = Consecrated Snowfield pillar [62052].

CONVENTIONS: CRLF-safe (bytes, newline-preserving), backs up to <file>.bak_<tag>, asserts
anchors present, idempotent via an applied-marker probe, raises on missing anchor.

Run on Windows:  python patch_apworld_natural_triggers.py
"""

import os
import sys

TAG = "naturaltriggers"
MARKER = "NATURAL_KEY_TRIGGERS_PATCH"   # idempotency sentinel embedded in inserted code
APWORLD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "Archipelago", "worlds", "eldenring")
INIT = os.path.join(APWORLD, "__init__.py")


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


# ---------------------------------------------------------------------------------------
# Inserted code block: builds apparatus for the two natural-key regions + the trigger table.
# Indented at 8 spaces (method-body level). Self-guarded by `if self.options.world_logic < 3:`
# so it only runs in region-gating modes, exactly like the apparatus it extends. Inserted
# AFTER region_graces / region_open_flags / lock_notify_items are all built (anchored on the
# return-dict assembly), so all three dicts exist when we mutate them.
# ---------------------------------------------------------------------------------------
APPARATUS_BLOCK = '''\
        # === {marker}: natural-key region apparatus (Mountaintops + Snowfield) ===========
        # Two regions whose locks have NO pool item; the client blooms their apparatus when a
        # vanilla disjunctive trigger fires (see naturalKeyTriggers in slot_data below). We
        # mint their grace bundle / dedicated open-flag / map-reveal / notify token here so the
        # client has something to bloom. Apparatus only -- AP fill logic (Rold/Haligtree +
        # Morgott) is unchanged. Gated to region-gating modes (world_logic < 3).
        natural_key_triggers = {{}}
        if self.options.world_logic < 3:
            _NK_GRACES = {{
                "Mountaintops Lock": [76500, 76501, 76502,
                                      76503, 76504, 76505, 76506, 76507, 76508, 76509, 76510,
                                      76520, 76521, 76522, 76523, 76524],
                "Snowfield Lock":    [76550, 76551, 76652, 76653],
            }}
            _NK_OPEN = {{"Mountaintops Lock": 76996, "Snowfield Lock": 76961}}
            _NK_REVEAL = {{"Mountaintops Lock": [62050, 62051], "Snowfield Lock": [62052]}}
            for _nlk, _nfs in _NK_GRACES.items():
                region_graces[_nlk] = sorted(set(region_graces.get(_nlk, []) + list(_nfs)))
            for _nlk, _nof in _NK_OPEN.items():
                region_open_flags[_nlk] = _nof
            for _nlk, _nrf in _NK_REVEAL.items():
                lock_reveal = region_lock_sd.get("lockRevealFlags", {{}})
                lock_reveal[_nlk] = sorted(set(lock_reveal.get(_nlk, []) + list(_nrf)))
                region_lock_sd["lockRevealFlags"] = lock_reveal
            # Notify token: GOODS-packed Map fragment so the native ticker names the region on
            # bloom (Mountaintops -> Map: Mountaintops of the Giants, West 8611; Snowfield -> 8618).
            _NK_NOTIFY = {{"Mountaintops Lock": 8611, "Snowfield Lock": 8618}}
            for _nlk, _ncode in _NK_NOTIFY.items():
                lock_notify_items.setdefault(_nlk, _ncode | 0x40000000)
            # Disjunctive natural triggers. Altus Lock is ADDITIVE (its item-receipt bloom from
            # the standard apparatus stays); this adds the medallion / Magma-Wyrm-Makar /
            # Drawing-Room-Key routes. A clause = ALL items received AND ALL flags set; ANY clause fires.
            natural_key_triggers = {{
                "Mountaintops Lock": {{"anyOf": [
                    {{"items": ["Rold Medallion"], "flags": [11000800]}},
                ]}},
                "Snowfield Lock": {{"anyOf": [
                    {{"items": ["Haligtree Secret Medallion (Left)",
                               "Haligtree Secret Medallion (Right)"], "flags": [11000800]}},
                ]}},
                "Altus Lock": {{"anyOf": [
                    {{"items": ["Dectus Medallion (Left)", "Dectus Medallion (Right)"]}},
                    {{"flags": [39200800]}},
                    {{"flags": [400072]}},
                ]}},
            }}
        # === end {marker} ================================================================
'''.format(marker=MARKER)

# Anchor: the start of the slot_data return-dict assembly. We insert the apparatus block
# immediately BEFORE it. By this point region_graces, region_open_flags, lock_notify_items
# and region_lock_sd are all built. The return dict is built via `return self.fill_slot_data_...`
# -- but the actual dict literal begins with the apIdsToItemIds / regionGraces keys. We anchor on
# the first slot_data key line we touch.
RETURN_ANCHOR = '            "regionGraces": region_graces,'

# Anchor inside the return dict where we add the new table (after lockNotifyItems).
NOTIFY_KEY_ANCHOR = '            "lockNotifyItems": lock_notify_items,'

NEW_TABLE_LINE = (
    '            # Natural-key disjunctive triggers ({marker}): lock name -> '
    '{{"anyOf":[{{items,flags}}...]}}.\n'
    '            # Client blooms the region apparatus (graces/open-flag/reveal) when ANY clause '
    'is satisfied\n'
    '            # (ALL items received AND ALL flags set). Apparatus-only regions '
    '(Mountaintops/Snowfield);\n'
    '            # Altus is additive to its item-receipt bloom. Region gating only; empty otherwise.\n'
    '            "naturalKeyTriggers": natural_key_triggers,\n'
).format(marker=MARKER)


def main():
    if not os.path.exists(INIT):
        print("ERROR: %s not found" % INIT)
        sys.exit(1)
    src = _read(INIT)

    if MARKER in src:
        print("already applied (marker %r present in __init__.py)" % MARKER)
        return

    # ---- verify anchors ----
    problems = []
    if APPARATUS_INSERT_ANCHOR not in src:
        problems.append("apparatus-insert anchor (region_open_flags assignment)")
    if NOTIFY_KEY_ANCHOR not in src:
        problems.append('"lockNotifyItems": lock_notify_items, return-dict key')
    if RETURN_ANCHOR not in src:
        problems.append('"regionGraces": region_graces, return-dict key (sanity)')
    if problems:
        print("ERROR: missing anchor(s): %s" % "; ".join(problems))
        sys.exit(1)

    # ---- insert apparatus block before the slot_data return-dict assembly ----
    # We anchor on the region_open_flags assignment line, which is the latest of the three
    # dicts to be created and sits just before lock_notify_items. We place the block AFTER
    # lock_notify_items finishes building, i.e. right before the return-dict's first key we
    # use. Cleanest robust spot: immediately before NOTIFY_KEY_ANCHOR is too late (inside dict
    # literal). Instead insert before the dict assembly start. We detect that start via the
    # unique 'startItems' grant section's predecessor -> use APPARATUS_INSERT_ANCHOR.
    if src.count(APPARATUS_INSERT_ANCHOR) != 1:
        print("ERROR: apparatus-insert anchor not unique (count=%d)"
              % src.count(APPARATUS_INSERT_ANCHOR))
        sys.exit(1)
    new_src = src.replace(APPARATUS_INSERT_ANCHOR,
                          APPARATUS_BLOCK + APPARATUS_INSERT_ANCHOR, 1)

    # ---- add the new slot_data table key after lockNotifyItems ----
    if new_src.count(NOTIFY_KEY_ANCHOR) != 1:
        print("ERROR: lockNotifyItems return-key anchor not unique (count=%d)"
              % new_src.count(NOTIFY_KEY_ANCHOR))
        sys.exit(1)
    new_src = new_src.replace(NOTIFY_KEY_ANCHOR,
                              NOTIFY_KEY_ANCHOR + "\n" + NEW_TABLE_LINE.rstrip("\n"), 1)

    _backup(INIT)
    _write(INIT, new_src)
    print("patched __init__.py")
    print("  + apparatus block (Mountaintops/Snowfield graces+open-flag+reveal+notify)")
    print("  + naturalKeyTriggers slot_data table (Mountaintops/Snowfield/Altus)")
    print("\nWARP-LOOP: not in REGION_LOCK_ITEM nor _EXTRA_LOCK_KEYS -> warp loop never adds a")
    print("           state.has rule for these names; no exclusion needed.")
    print("DUNGEON-SWEEP: dungeonSweeps is keyed trigger-address -> location-address[], not")
    print("           region -> DefeatFlag, so adding Forbidden Lands -> BBK 1049520800 is NOT a")
    print("           straightforward extension; left as a FOLLOW-UP (not forced).")
    print("\nDONE. Regen on Windows to emit the new slot_data.")


# The apparatus block must be inserted at a point where region_graces, region_open_flags,
# lock_notify_items AND region_lock_sd all already exist. lock_notify_items is the last of
# these to be assigned (it closes just before the start_graces section). We anchor on the
# start_graces comment that immediately follows the lock_notify_items build, inserting the
# block before it (still inside fill_slot_data, method-body indent).
APPARATUS_INSERT_ANCHOR = (
    "        # Start graces (load-time, FLAG-based -- not name-keyed): the client sets these at"
)


if __name__ == "__main__":
    main()
