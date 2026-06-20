# SPEC: Dungeon Sweep — boss kill auto-clears the dungeon's remaining checks

Status: IMPLEMENTED 2026-06-11 (opt-in, default none). Deviation from the original spec:
no apconfig/randomizer changes were needed — the sweep TRIGGER is the mainboss drop
location's own guarding flag, which is already in apconfig's location_flags, so slot_data
carries {trigger ap loc id: [member ap loc ids]} ("dungeonSweeps") and the client does the
rest. apworld: options.py DungeonSweep + __init__.py fill_slot_data; client: Core.h/cpp
(dungeonSweeps + PollLocationFlags extension), ArchipelagoInterface.cpp (parse).
Untested in-game; legacy-group region lists are best-effort (verify Volcano Manor and
Shadow Keep region coverage on first use).

## Concept

When the player defeats a dungeon's main boss, the client automatically sends every
remaining AP location check inside that dungeon. Applies to legacy dungeons (Stormveil,
Raya Lucaria, ...) and optionally minidungeons (catacombs, caves, tunnels, divine towers,
evergaols). Beating the boss = "you've conquered this place; loot it all."

## Is it against the spirit of Archipelago?

Mostly no, with caveats. AP's norm is that check **granularity and difficulty are slot
options**: worlds routinely ship options that collapse or skip check classes (excluded
locations, "remote items", goal shortcuts). A sweep is the same family — it changes how
*your* world surrenders its checks, which is your YAML's business.

Where it rubs against the grain:

- **Exploration deflation.** ER's identity in a multiworld is its enormous check density;
  sweeping turns dungeon exploration into "rush the boss." For a casual/solo-ish run
  that's the point (less tedium); in a race or group setting it's a pacing distortion.
- **Burst sends.** One boss kill can dump 30-80 checks at once, flooding other players
  with items and making progression spheres "lumpy." AP handles this fine technically
  (collect/release do the same), but it changes the feel for everyone else.
- **Economy skip.** Swept shop checks are "purchased" for free; swept quest checks skip
  their questlines. (The latter is arguably a FEATURE: it un-missables NPC quest checks.)

Verdict: fine as an **opt-in, default-off** YAML option, clearly labeled. Don't make it
the implicit behavior.

## Option surface (apworld)

```yaml
dungeon_sweep:
  none: 50            # current behavior
  minidungeons: 0     # catacombs/caves/tunnels/heroes' graves/divine towers/evergaols
  all: 0              # minidungeons + legacy dungeons
```

Implementation note: the option only needs to reach **slot_data** (the client does the
sweeping); generation logic does NOT need to model it (see Logic).

## Data flow (mirrors the existing location_flags design)

1. **Bake (PermutationWriter / ArchipelagoForm):** we already compute
   `ApLocationFlags[apLocId] = guardingEventFlag` per placed location, and the enemy
   config gives every boss a `DefeatFlag` plus map/area identity. Build a second map:

   ```
   "dungeon_sweeps": { "<bossDefeatFlag>": [apLocId, apLocId, ...], ... }
   ```

   keyed by the area's MAIN boss defeat flag, valued by every AP location id whose
   location annotation falls inside that area. Emit into apconfig.json next to
   location_flags. Area membership comes from the randomizer's annotation Areas (the
   same scoping the scrape uses), not guesswork.

2. **Client (Core):** extend the existing 2s flag-poll tick. For each sweep entry whose
   boss flag is set, enqueue all of its location ids through the same
   `flagSentLocations` dedupe used by PollLocationFlags. No new netcode: location checks
   are idempotent server-side, and own-world items arrive via the normal echo path
   (items_handling=7), so the player also *receives* everything of theirs that was
   stashed in the dungeon — which is exactly the promised behavior.

3. **apworld:** ships the option; gates whether the bake emits sweep entries (slot_data
   flag the randomizer reads, same pattern as enable_dlc).

## Logic (generation) — deliberately untouched

Each location keeps its normal access rule. The sweep only makes some items arrive
EARLIER than logic's conservative estimate, which is always safe (logic that's too
conservative can't brick a seed; logic that's too optimistic can). Don't add
`OR can_beat_boss(dungeon)` disjunctions — the boss is nearly always deeper than the
checks it would unlock, so the modeling win is ~zero and the bug surface is real.

## Scope definitions

- **Legacy dungeon:** the named-area annotation groups for SV, RLA, VM, LRC/LAC, MS,
  CFA, EI (+ DLC: Belurat, Shadow Keep, Enir-Ilim, ...). Sweep triggers on the area's
  MAINBOSS defeat flag only (Godrick, not Margit).
- **Minidungeon:** catacombs/caves/tunnels/graves/towers — these have exactly one boss
  with a DefeatFlag; unambiguous.
- **Open-world regions: explicitly OUT.** Sweeping Limgrave on Godrick (or region-lock
  "bosses") guts the game. Field bosses sweep nothing.

## Edge cases

- **Multi-boss dungeons** (Stormveil has Margit AND Godrick): mainboss only.
- **Shops inside dungeons** (e.g. Patches, Hermit Merchant siblings): included in the
  sweep (free). Acceptable; note it in the option description.
- **Quest/NPC checks inside dungeons** (Rogier, Nepheli): included — this conveniently
  un-missables them.
- **Boss already dead at install time** (mid-run option adoption): first poll tick
  sweeps retroactively. Harmless; same semantics as the existing retroactive flag sync.
- **Checks the player already sent:** dedupe via flagSentLocations + server idempotency.
- **Areas with no clean boundary** (Leyndell bleeding into the Subterranean
  Shunning-Grounds): follow the annotation area, accept imperfection, document.
- **DLC dungeons:** identical mechanism; nothing special.

## Work items (when/if implemented)

1. apworld: add `dungeon_sweep` option + slot_data passthrough (regen required).
2. Randomizer: emit `dungeon_sweeps` map into apconfig.json (area → mainboss DefeatFlag
   → contained AP location ids).
3. Client: parse map; extend poll tick; reuse flagSentLocations dedupe.
4. Test: kill a catacomb boss with 2+ unchecked locations behind; verify burst send +
   own-item echo grants; reconnect and verify no resend.

## Open questions

- Should swept checks that are *logically unreachable without a key item* (e.g. behind
  an imp statue the player never opened) still send? Current design: yes (sweep means
  sweep). Alternative: only sweep checks whose own guarding flag region was visited —
  rejected as overcomplex.
- Per-class sweep granularity (legacy vs catacombs as separate toggles) — the 3-value
  enum above covers the realistic asks; expand only if someone actually wants it.
