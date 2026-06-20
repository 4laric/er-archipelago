# PROBE: skip-Melina leveling flag

## SOLVED 2026-06-16 -- recipe: event flags **4680 + 951**
- **4680** = Level Up enable. **951** = "Melina first-meeting done" (common.emevd does
  EndIf(EventFlag(951)) before the 60420xxx meeting cutscenes, so 951 ON => no conversation).
- 953 NOT needed. 951 also skips her Torrent hand-off, so co-grant Torrent (goods 130 + flag 60100).
- SHIPPED as apworld option `early_leveling` (default off): options.py EarlyLeveling + EROptions field;
  __init__.py fill_slot_data appends 4680/951(+Torrent) to startGraces. patch_apworld_early_leveling.py.
  Pure slot_data -> NO client rebuild, regen+rebake only.
- The hunt (kept below for method reference) found 4680 via the /dumpflags diff + behavioral bisect.

---


Goal: find the event flag that enables the **Level Up** option at a Site of Grace, so we can grant
leveling at start and never run Melina's accord conversation.

## Status / what we know
- Leveling is granted by the grace/**bonfire menu ESD** (`t000001000`), not by any EMEVD and not by
  Melina's character-talk. Accepting the accord sets a flag; the bonfire menu shows "Level Up" when it's on.
- The flag is **not directly exposed** in the randomizer data (`itemevents.txt` only dumps item-relevant
  talk states: Rold Medallion 400001, Ranni 400394, Spirit Bell 60110).
- **`60150` is NOT it** — only appears as a coincidental item-lot key (`603746,0:0000060150`).
- The one Melina flag that surfaces is **event flag 108**, but its branches pair with Rold Medallion
  (`f15(400001)`), so it looks like a mid-quest Rold/Roundtable flag, not the initial leveling unlock.
  Check it first, don't bank on it.
- Reference: [[er-event-flag-validity]] (set->readback; invented IDs silently no-op).

## FINDINGS (2026-06-16) -- guessing is dead, use the diff
- RULED OUT empirically: Melina dialogue cluster (105-112) reads 0 before AND after the accord.
- RULED OUT: 60xxx grant band -- Torrent **60100 = 1** post-accord (so /getflag WORKS), but
  60140 / 60150 / 60160 / 60101 / 60102 all 0. Leveling is not a neighbor of the Torrent grant.
- => leveling enable is either a flag in some other band, or an ESD-internal gate. Stop guessing;
  DIFF the whole flag space across the accord (see "Method 2" below). New client cmd: `/dumpflags`
  (patch_client_dumpflags.py).

## Probe interface (already in client)
`patch_client_flagcmds.py` -> Core.cpp console commands, routed through
`er_ap::game::SetEventFlag` / `GetEventFlagState`. Must be **loaded in-world** for them to work.
```
/setflag <id> <0|1>
/getflag <id>
/dumpflags <lo> <hi> [label]   # writes every SET flag in range to flagdump_<label>.txt (needs patch_client_dumpflags.py + -Client build)
```

## Method 2 (USE THIS) -- full flag diff across the accord
1. Apply patch + build:  `python patch_client_dumpflags.py` then `.\build.ps1 -Client -Deploy`, restart ER.
2. Fresh base-game probe save, stand at the grace that will trigger Melina, BEFORE you rest/accept:
   `/dumpflags 0 2000000 before`
3. Accept the accord (leveling now works), immediately:
   `/dumpflags 0 2000000 after`
4. Diff (PowerShell):
   `Compare-Object (gc flagdump_before.txt) (gc flagdump_after.txt) | ? SideIndicator -eq '=>'`
   The `=>` lines are flags newly set by the accord. Keep the delta clean by not killing/looting
   between snapshots (dump right before and right after the rest that triggers her).
5. For each newly-set id: fresh save, `/setflag <id> 1`, rest at grace, is "Level Up" there?
6. If 0..2000000 has no winner, widen: `/dumpflags 10000000 12000000 before2` etc. (Melina/NPC quest
   flags can live in the 11xxxxxx band). flagdump_*.txt lands in the client's working dir.

## Step 1 — find the flag (diff across the accord)
Read the low Melina/progression cluster on TWO saves and compare. The flag that is `1` post-accord and
`0` pre-accord is the target.

Save A = vanilla save where leveling already works (accord accepted).
Save B = fresh save, before the 3-grace Melina meeting.

Run on BOTH, note the values:
```
/getflag 108
/getflag 105
/getflag 106
/getflag 107
/getflag 109
/getflag 110
/getflag 111
/getflag 112
```
Target = whichever reads 1 on A and 0 on B. If nothing flips, widen to 102-120.

## Step 2 — validity + behavioral confirm
On the fresh pre-Melina save (B), for the candidate that flipped:
1. `/getflag <id>`        -> expect 0   (read-before: unset, not already occupied)
2. `/setflag <id> 1`
3. `/getflag <id>`        -> expect 1   (read-back: group allocated, not a silent no-op)
4. Rest at the grace      -> does **Level Up** appear in the menu?
   - Yes -> that single flag is the skip-Melina leveling grant. Done.
   - No  -> wrong flag; back to Step 1 (widen range), or see fallback.

## On success
Drop the confirmed ID into the client start-flag map alongside Torrent `60100` / bell `60110` /
whetstone `60130`, set ON at session start. No conversation fires because Melina's spawn is never triggered.

## Fallback (if no event flag works)
If every candidate fails Step 2.4, leveling is gated by an ESD-internal talk condition, not a plain
event flag. Definitive route: decompile the bonfire menu ESD `t000001000` (in m00 talkesdbnd) with
**esdtool**, find the condition wrapping the level-up command — that's the real gate.

## Side note (decompile failure, separate issue)
Deployed `common.emevd.dcx` fails DarkScript with "Unknown instruction event 50: 1014[69]". Confirmed a
**version mismatch**, not corruption: the file parses cleanly (255 events / 8796 instructions, all banks
sane, ZSTD-compressed = DLC/patch-era), it just uses `1014[69]` (zero-arg, control-flow family) which the
stale EMEDF lacks. The rando's bundled `events.txt` EMEDF also lacks it. Fix = upgrade DarkScript to a
current DLC-era ER EMEDF.
