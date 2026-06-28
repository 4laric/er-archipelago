#!/usr/bin/env python3
"""
patch_baker_chokepoint_sweep_override.py  --  run on Windows from anywhere.

Companion to patch_apworld_chokepoint_boss_attribution.py (apply that first).

In bosses mode the geometric BossAttribution lumps a whole legacy dungeon onto its single
lowest-id boss (all Farum Azula -> Maliketh 13000800, all Haligtree -> Malenia 15000800),
so the END boss would sweep the chokepoint BEFORE-half. This patch re-homes the before-half
check ids -- shipped by the apworld as slot_data["chokepointSweeps"] { chokeFlag : [apLocId] }
-- off the end-boss lump and onto the choke boss DefeatFlag, right after BossAttribution.Compute
returns and before the sweep map is serialised.

Behaviour:
  * Pull the before-half ids off every OTHER boss flag (DefeatFlag >= 1_000_000); the small
    grace flags are LEFT intact so grace_sweep still covers these checks.
  * Add the ids under the choke boss DefeatFlag (deduped).
  * Drop any boss flag whose list emptied out after the move.

The whole block sits inside `if (apWantSweep)` (dungeon_sweep == bosses), so it is a no-op for
every other seed. chokepointSweeps absent (old apworld / chokepoint_locks off) => no-op.

File: SoulsRandomizers/RandomizerCommon/ArchipelagoForm.cs  (CRLF + BOM -- preserved here).
Idempotent + string-anchored; aborts without writing if the anchor is missing or ambiguous.
Needs a SoulsRandomizers Release rebuild + a rebake to take effect.
"""
import os, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))


def find_form():
    cands = [
        os.path.join(HERE, "SoulsRandomizers", "RandomizerCommon", "ArchipelagoForm.cs"),
        os.path.join(HERE, "RandomizerCommon", "ArchipelagoForm.cs"),
        os.path.join(HERE, "ArchipelagoForm.cs"),
    ]
    for c in cands:
        if os.path.exists(c):
            return c
    print("ERROR: could not locate ArchipelagoForm.cs (looked in: %s)" % cands)
    sys.exit(1)


FORM = find_form()

# Anchor = the line that closes the BossAttribution.Compute(...) call; insert right after it.
ANCHOR = "apEntityPos, out var sweepStats, out var sweepFlagNames);"
SKIP_MARKER = "chokepointSweeps"

# 24-space indent = same level as `var sweep = BossAttribution.Compute(...)`.
BLOCK = [
    "                        // Chokepoint re-attribution (extra_region_locks: chokepoint_locks): the apworld",
    "                        // carves a legacy dungeon's BEFORE-half onto its mid-boss chokepoint, but the",
    "                        // geometric tier-1 attribution lumps the whole legacy area onto its single",
    "                        // lowest-id boss (all Farum Azula -> Maliketh, all Haligtree -> Malenia). Re-home",
    "                        // the before-half ids from the end-boss lump onto the choke boss DefeatFlag so",
    "                        // killing the CHOKE boss (not the end boss) sweeps them. Grace flags (< 1e6) are",
    "                        // left intact so grace_sweep still covers them. Source: slot_data chokepointSweeps.",
    "                        if (slotData.TryGetValue(\"chokepointSweeps\", out var chokeObj) && chokeObj is JObject chokeMap)",
    "                        {",
    "                            foreach (var ck in chokeMap)",
    "                            {",
    "                                if (!int.TryParse(ck.Key, out int chokeFlag)) continue;",
    "                                var ids = (ck.Value as JArray)?.Select(t => t.Value<long>()).ToHashSet();",
    "                                if (ids == null || ids.Count == 0) continue;",
    "                                // pull off every OTHER boss flag (>= 1e6); leave grace flags alone",
    "                                foreach (var kv in sweep)",
    "                                    if (kv.Key != chokeFlag && kv.Key >= 1000000)",
    "                                        kv.Value.RemoveAll(id => ids.Contains(id));",
    "                                if (!sweep.TryGetValue(chokeFlag, out var dst)) sweep[chokeFlag] = dst = new List<long>();",
    "                                foreach (var id in ids) if (!dst.Contains(id)) dst.Add(id);",
    "                            }",
    "                            // drop any boss flag whose list emptied out after the move",
    "                            foreach (var _ek in sweep.Where(kv => kv.Value.Count == 0).Select(kv => kv.Key).ToList())",
    "                                sweep.Remove(_ek);",
    "                        }",
]


def main():
    with open(FORM, "rb") as f:
        raw = f.read()
    has_bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    nl = "\r\n" if "\r\n" in text else "\n"

    if SKIP_MARKER in text:
        print("Already patched (found %r) -- nothing to do (idempotent)." % SKIP_MARKER)
        return

    lines = text.split(nl)
    hits = [i for i, l in enumerate(lines) if ANCHOR in l]
    if not hits:
        print("ABORT: anchor not found: %r\n(Check you are on the live Windows tree.)" % ANCHOR)
        sys.exit(2)
    if len(hits) > 1:
        print("ABORT: anchor is ambiguous (%d hits): %r" % (len(hits), ANCHOR))
        sys.exit(2)

    i = hits[0]
    lines[i + 1:i + 1] = BLOCK
    new_text = nl.join(lines)

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = FORM + ".bak_chokeoverride_" + stamp
    with open(bak, "wb") as f:
        f.write(raw)
    out = new_text.encode("utf-8")
    if has_bom:
        out = b"\xef\xbb\xbf" + out
    with open(FORM, "wb") as f:
        f.write(out)

    print("WROTE %s  (backup: %s)" % (FORM, os.path.basename(bak)))
    print("Inserted %d lines after the Compute() call. BOM=%s, newline=%s"
          % (len(BLOCK), has_bom, "CRLF" if nl == "\r\n" else "LF"))
    print("\nNext: rebuild SoulsRandomizers (Release / Archipelago), then rebake a")
    print("  dungeon_sweep: bosses + extra_region_locks:[chokepoint_locks] seed and check")
    print("  ap_sweep_diag: Godskin Duo (13000850) / Loretta (15000850) own the before-half.")


if __name__ == "__main__":
    main()
