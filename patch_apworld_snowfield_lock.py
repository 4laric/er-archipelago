#!/usr/bin/env python3
"""
patch_apworld_snowfield_lock.py  --  run on Windows from anywhere.

Split "Consecrated Snowfield" off as its own dedicated, opt-in region lock.

Today Snowfield is a NATURAL-KEY region: it has no pool lock item and is gated
only by the vanilla Haligtree Secret Medallions (via Hidden Path to the Haligtree),
sharing the Rold/Mountaintops cluster. This adds an opt-in "Snowfield Lock"
(extra_region_locks: "snowfield") so Snowfield seals/opens on its own key.

Scope when the option is OFF: ZERO behavioural change (item not injected, no rule
added, natural trigger untouched).

Edits (all string-anchored + idempotent; aborts without writing if any anchor is missing):
  items.py     1) construct "Snowfield Lock" AFTER _dlc_items (no ap_code shift) and
                  append it to _vanilla_items (base-game item, is_dlc stays False).
  __init__.py  2) _EXTRA_LOCK_KEYS["Snowfield Lock"] = "snowfield"  (inject only when opted in)
               3) gate "Consecrated Snowfield" on "Snowfield Lock" inside an opt-in block
               4) drop the Snowfield natural_key_triggers entry when opted in
                  (item-receipt bloom replaces the medallion bloom; grace apparatus already exists)
  options.py   5) add "snowfield" to extra_region_locks valid_keys
               6) document it in the option docstring

NOTE: Snowfield is NOT in region_spine.SPINE (spine stops at Mt. Gelmir), so this
does not affect num_regions sealing. The grace/open/reveal apparatus keyed by
"Snowfield Lock" already exists in the natural-key block, so the item-receipt
warp/bloom works with no client change. Needs a gen-test.
"""
import os, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))

def find_world_dir():
    cands = [
        os.path.join(HERE, "Archipelago", "worlds", "eldenring"),
        os.path.join(HERE, "worlds", "eldenring"),
        HERE,
    ]
    for c in cands:
        if os.path.exists(os.path.join(c, "__init__.py")) and os.path.exists(os.path.join(c, "items.py")):
            return c
    print("ERROR: could not locate worlds/eldenring (looked in: %s)" % cands)
    sys.exit(1)

WORLD = find_world_dir()

def read(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()

def nl_of(text):
    return "\r\n" if "\r\n" in text else "\n"

def insert_after(text, contains, new_block_lines, skip_marker):
    """Insert new_block_lines (list of str, no newline) on the line AFTER the first
    line containing `contains`. Returns (status, text). status in ok/skip/missing."""
    nl = nl_of(text)
    if skip_marker in text:
        return ("skip", text)
    lines = text.split(nl)
    hits = [i for i, l in enumerate(lines) if contains in l]
    if not hits:
        return ("missing", text)
    i = hits[0]
    lines[i + 1:i + 1] = new_block_lines
    return ("ok", nl.join(lines))

# ---- edit specs: (filename, anchor_contains, [inserted lines], skip_marker) -------------
EDITS = {
    "items.py": [
        (
            "item.is_dlc = True",
            [
                "",
                "# Snowfield Lock: dedicated lock to split Consecrated Snowfield off the Mountaintops/Rold",
                "# cluster (opt-in via extra_region_locks: \"snowfield\"). Constructed AFTER _dlc_items so no",
                "# other item's auto ap_code shifts; appended to _vanilla_items so it is a BASE-game item.",
                "_snowfield_lock = ERItemData(\"Snowfield Lock\", 99999, ERItemCategory.GOODS, classification=ItemClassification.progression, lock=True)",
                "_vanilla_items.append(_snowfield_lock)",
            ],
            'ERItemData("Snowfield Lock"',
        ),
    ],
    "__init__.py": [
        (
            '_EXTRA_LOCK_KEYS["Spelunker\'s Ghostflame Torch"] = "liurnia_caves"',
            [
                '            _EXTRA_LOCK_KEYS["Snowfield Lock"] = "snowfield"  # opt-in: split Consecrated Snowfield off (dedicated lock)',
            ],
            '_EXTRA_LOCK_KEYS["Snowfield Lock"]',
        ),
        (
            'self._add_entrance_rule("Yelough Anix Tunnel", "Spelunker\'s Beast-Repellent Torch")',
            [
                '            if "snowfield" in self.options.extra_region_locks.value:',
                "                # Split Consecrated Snowfield off as its own dedicated lock. It was a natural-key",
                "                # region (gated only by the Haligtree Secret Medallions, shared with the Rold /",
                "                # Mountaintops cluster); this adds a dedicated 'Snowfield Lock' on top of the",
                "                # medallion route so Snowfield seals and opens independently. The natural-key",
                "                # bloom trigger is dropped (see natural_key_triggers) so the in-game grace bloom",
                "                # follows the lock item rather than the medallions.",
                '                self._add_entrance_rule("Consecrated Snowfield", "Snowfield Lock")',
            ],
            'self._add_entrance_rule("Consecrated Snowfield", "Snowfield Lock")',
        ),
        (
            "# === end NATURAL_KEY_TRIGGERS_P2",
            [
                '        # snowfield split (extra_region_locks: "snowfield"): once Snowfield is a dedicated',
                "        # lock, drop its Haligtree-medallion natural trigger so the item-receipt bloom (using",
                '        # the grace/open apparatus already keyed by "Snowfield Lock") drives the in-game bloom.',
                '        if self.options.world_logic < 3 and "snowfield" in self.options.extra_region_locks.value:',
                '            natural_key_triggers.pop("Snowfield Lock", None)',
            ],
            'natural_key_triggers.pop("Snowfield Lock"',
        ),
    ],
    "options.py": [
        (
            'valid_keys = valid_keys | {"chokepoint_locks"}',
            [
                '    valid_keys = valid_keys | {"snowfield"}',
            ],
            '{"snowfield"}',
        ),
        (
            "Pure logic; see SPEC-chokepoint-locks.md",
            [
                "      snowfield -- split Consecrated Snowfield (101 overworld checks / 130 with its minor",
                "                   dungeons) out of the Mountaintops/Rold cluster behind its own dedicated",
                "                   'Snowfield Lock', so it seals and opens independently (still reached via",
                "                   the Haligtree Secret Medallion route)",
            ],
            "snowfield -- split Consecrated Snowfield",
        ),
    ],
}

def main():
    plan = {}      # filename -> new_text
    report = []
    abort = False
    for fname, edits in EDITS.items():
        path = os.path.join(WORLD, fname)
        if not os.path.exists(path):
            report.append("MISSING FILE: %s" % path); abort = True; continue
        text = read(path)
        for anchor, block, skip in edits:
            status, text = insert_after(text, anchor, block, skip)
            report.append("  [%-7s] %s :: %s" % (status, fname, skip))
            if status == "missing":
                abort = True
        plan[path] = text

    print("=== patch_apworld_snowfield_lock plan (world: %s) ===" % WORLD)
    for line in report:
        print(line)

    if abort:
        print("\nABORT: one or more anchors missing. NOTHING written. "
              "(Check that you are on the live Windows tree, not a stale copy.)")
        sys.exit(2)

    if all("skip" in l for l in report):
        print("\nAll edits already present -- nothing to do (idempotent).")
        return

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    for path, new_text in plan.items():
        bak = path + ".bak_snowfieldlock_" + stamp
        with open(bak, "w", encoding="utf-8", newline="") as f:
            f.write(read(path))
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(new_text)
        print("WROTE %s  (backup: %s)" % (path, os.path.basename(bak)))

    print("\nDone. Next: compile-check, then gen-test a region_lock seed with")
    print("  extra_region_locks: [snowfield]   (verify Snowfield Lock lands reachable;")
    print("  confirm Snowfield graces bloom on receiving the lock).")

if __name__ == "__main__":
    main()
