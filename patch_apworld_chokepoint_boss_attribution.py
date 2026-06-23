#!/usr/bin/env python3
"""
patch_apworld_chokepoint_boss_attribution.py  --  run on Windows from anywhere.

Make the chokepoint BEFORE-half attribute to the CHOKE boss in bosses-mode sweep.

Background
----------
extra_region_locks: chokepoint_locks already carves a legacy dungeon's BEFORE-half
onto its mid-boss chokepoint in the apworld dungeon_sweeps (Farum Azula before-half ->
Godskin Duo drop; Miquella's Haligtree -> Loretta drop). That works for the CLIENT
dungeonSweeps path. BUT in bosses mode (dungeon_sweep == bosses) the static randomizer's
geometric BossAttribution lumps the WHOLE legacy area onto its single lowest-id boss:

    Farum Azula  (m13) lowest-id Boss = Maliketh  13000800  -> sweeps ALL Farum Azula
    Haligtree    (m15) lowest-id Boss = Malenia   15000800  -> sweeps ALL Haligtree

So in bosses mode the END boss (Maliketh / Malenia) would sweep the before-half that the
chokepoint is supposed to hand to the mid-boss -- defeating the split.

This patch ships the before-half check ids keyed by the CHOKE boss DefeatFlag so the baker
can re-home them onto the choke boss. Choke boss DefeatFlags (verified in diste/Base/enemy.txt,
NOT the 510140/510190 the old spec guessed):

    Godskin Duo                       -> 13000850   (Farum Azula Main)
    Loretta, Knight of the Haligtree  -> 15000850   (Elphael, Brace of the Haligtree)

Companion patch (static randomizer): patch_baker_chokepoint_sweep_override.py applies the
re-home in ArchipelagoForm.cs (bosses mode only).

Scope when chokepoint_locks is OFF, or dungeon_sweep is off: ZERO behavioural change
(chokepointSweeps emitted empty; the baker ignores it outside bosses mode anyway).

Edits (string-anchored + idempotent; aborts without writing if any anchor is missing):
  region_spine.py  1) add CHOKEPOINT_BOSS_FLAGS dict right before compute_godrick_scope()
  __init__.py      2) build chokepoint_sweeps after dungeon_sweeps in fill_slot_data
                   3) emit it as slot_data["chokepointSweeps"] (after the dungeonSweeps key)

NOTE: apworld files are CRLF -- this preserves the file's newline + any BOM. Needs a
gen-test (extra_region_locks: [chokepoint_locks] + dungeon_sweep: bosses) and a rebake.
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
        if (os.path.exists(os.path.join(c, "__init__.py"))
                and os.path.exists(os.path.join(c, "region_spine.py"))):
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
    """Insert new_block_lines on the line AFTER the first line containing `contains`.
    Returns (status, text); status in ok/skip/missing."""
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


def insert_before(text, contains, new_block_lines, skip_marker):
    """Insert new_block_lines on the line(s) BEFORE the first line containing `contains`."""
    nl = nl_of(text)
    if skip_marker in text:
        return ("skip", text)
    lines = text.split(nl)
    hits = [i for i, l in enumerate(lines) if contains in l]
    if not hits:
        return ("missing", text)
    i = hits[0]
    lines[i:i] = new_block_lines
    return ("ok", nl.join(lines))


# ---- edit specs ---------------------------------------------------------------------------
# Each: (op, filename, anchor_contains, [inserted lines], skip_marker)
EDITS = [
    # 1) region_spine.py: choke boss DefeatFlags, inserted right before compute_godrick_scope().
    ("before", "region_spine.py", "def compute_godrick_scope(", [
        "# Choke boss DefeatFlags (diste/Base/enemy.txt) for the v1 chokepoints above. Used to",
        "# re-home each dungeon's BEFORE-half onto its mid-boss in bosses-mode sweep (the geometric",
        "# attribution otherwise lumps the whole legacy area onto its lowest-id boss = the END boss).",
        "# Keyed by after_region (same key as CHOKEPOINTS). See patch_apworld_chokepoint_boss_attribution.py.",
        "CHOKEPOINT_BOSS_FLAGS: Dict[str, int] = {",
        "    \"Farum Azula Main\": 13000850,                # Godskin Duo (m13)",
        "    \"Elphael, Brace of the Haligtree\": 15000850,  # Loretta, Knight of the Haligtree (m15)",
        "}",
        "",
        "",
    ], "CHOKEPOINT_BOSS_FLAGS"),

    # 2) __init__.py: compute chokepoint_sweeps right after the dungeon_sweeps line.
    ("after", "__init__.py",
     "        dungeon_sweeps, _ = self._compute_dungeon_sweeps()", [
        "",
        "        # Chokepoint boss attribution (extra_region_locks: chokepoint_locks): in bosses mode the",
        "        # static randomizer's geometric sweep lumps a whole legacy dungeon onto its single",
        "        # lowest-id boss (all Farum Azula -> Maliketh, all Haligtree -> Malenia), which would let",
        "        # the END boss sweep the BEFORE-half the chokepoint hands to the mid-boss. Ship the",
        "        # before-half check ids keyed by the choke boss DefeatFlag so the baker re-homes them onto",
        "        # the choke boss (Godskin Duo 13000850 / Loretta 15000850). Empty unless chokepoint_locks",
        "        # AND a sweep are on; the baker only consumes it in bosses mode. Static randomizer only.",
        "        chokepoint_sweeps: Dict[str, List[int]] = {}",
        "        if (\"chokepoint_locks\" in self.options.extra_region_locks.value",
        "                and self.options.dungeon_sweep != 0):",
        "            _cp_r2l: Dict[str, List[ERLocation]] = {}",
        "            for _cpl in self._get_our_locations():",
        "                if _cpl.address is None:",
        "                    continue",
        "                _cp_r2l.setdefault(_cpl.parent_region.name, []).append(_cpl)",
        "            for _cp_after, (_cp_bef, _cp_trig) in region_spine.CHOKEPOINTS.items():",
        "                _cp_flag = region_spine.CHOKEPOINT_BOSS_FLAGS.get(_cp_after)",
        "                # only when the dungeon is actually split this seed (after-region present)",
        "                if not _cp_flag or _cp_after not in _cp_r2l:",
        "                    continue",
        "                _cp_ids = sorted({l.address for r in _cp_bef",
        "                                  for l in _cp_r2l.get(r, []) if l.address is not None})",
        "                if len(_cp_ids) > 1:",
        "                    chokepoint_sweeps[str(_cp_flag)] = _cp_ids",
     ], "chokepoint_sweeps: Dict[str, List[int]] = {}"),

    # 3) __init__.py: emit the slot_data key right after the dungeonSweeps key.
    ("after", "__init__.py", '            "dungeonSweeps": dungeon_sweeps,', [
        "            # Chokepoint boss attribution (extra_region_locks: chokepoint_locks):",
        "            # { chokeBossDefeatFlag : [before-half apLocId,...] }. The baker re-homes these off",
        "            # the end-boss lump onto the choke boss in bosses mode. Empty unless chokepoint_locks",
        "            # + dungeon_sweep are on. Consumed by the static randomizer (sweep_flags), not the client.",
        '            "chokepointSweeps": chokepoint_sweeps,',
     ], '"chokepointSweeps"'),
]


def main():
    # group edits per file so all edits to a file accumulate on one text
    per_file = {}
    order = []
    for op, fname, anchor, block, skip in EDITS:
        if fname not in per_file:
            per_file[fname] = []
            order.append(fname)
        per_file[fname].append((op, anchor, block, skip))

    plan = {}
    report = []
    abort = False
    for fname in order:
        path = os.path.join(WORLD, fname)
        if not os.path.exists(path):
            report.append("MISSING FILE: %s" % path)
            abort = True
            continue
        text = read(path)
        for op, anchor, block, skip in per_file[fname]:
            fn = insert_before if op == "before" else insert_after
            status, text = fn(text, anchor, block, skip)
            report.append("  [%-7s] %s :: %s" % (status, fname, skip))
            if status == "missing":
                abort = True
        plan[path] = text

    print("=== patch_apworld_chokepoint_boss_attribution plan (world: %s) ===" % WORLD)
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
        bak = path + ".bak_chokeattr_" + stamp
        with open(bak, "w", encoding="utf-8", newline="") as f:
            f.write(read(path))
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(new_text)
        print("WROTE %s  (backup: %s)" % (path, os.path.basename(bak)))

    print("\nDone. Next:")
    print("  1) py_compile worlds/eldenring/__init__.py + region_spine.py")
    print("  2) apply patch_baker_chokepoint_sweep_override.py + rebuild SoulsRandomizers (Release)")
    print("  3) gen-test  extra_region_locks: [chokepoint_locks]  +  dungeon_sweep: bosses")
    print("  4) rebake; confirm ap_sweep_diag shows Godskin Duo (flag 13000850) / Loretta (15000850)")
    print("     own the before-half checks and Maliketh/Malenia no longer do.")


if __name__ == "__main__":
    main()
