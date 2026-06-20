# SPEC: chokepoint locks + choke-boss sweep

Status: **v1 IMPLEMENTED 2026-06-18** (apworld, opt-in) — `patch_apworld_chokepoint_locks.py`.
Builds on `ANALYSIS-legacy-dungeon-chokepoints.md`, `ANALYSIS-dlc-progression-map.md`,
`SPEC-dungeon-sweep.md`, and `SPEC-boss-attribution.md`.

## Implementation status (v1)

One opt-in `extra_region_locks` key, `chokepoint_locks`, drives BOTH the lock and the sweep split.
Shipped via `patch_apworld_chokepoint_locks.py` (idempotent; apply on Windows — the apworld files
are CRLF):

- `region_spine.py` — new `CHOKEPOINTS` table: `after_region -> (before_regions, trigger_locations)`.
- `options.py` — `chokepoint_locks` added to `ExtraRegionLocks.valid_keys` + docstring.
- `__init__.py` — (a) LOCK: in `_region_lock()`, gate each after-region's entrance on
  `_can_get(<choke boss drop>)`; (b) SWEEP: in the `legacy_groups` sweep builder, carve each
  chokepoint's before-regions onto the choke boss drop trigger, leaving the after-half on the
  mainboss remembrance.

**Key simplification vs. the original sketch:** the sweep trigger is the choke boss's DROP
*location*, whose guarding event flag (= the boss DefeatFlag) the client already watches via
`location_flags` — so **no raw DefeatFlag capture is needed** for any boss that drops a check, and
the lock anchors on `_can_get(drop)` (pure logic, no new item, no open-flag), mirroring
Nokron-gated-on-Radahn. This makes the two clean base cases fully build-ready today.

v1 ships exactly the two cleanly region-split base chokepoints (drops + flags already in the data):

| Dungeon | Choke boss | After-region locked + before-half swept on the drop |
|---|---|---|
| Crumbling Farum Azula | Godskin Duo (510140) | `Farum Azula Main` gated; `Farum Azula` (44) sweeps on `FA/DTT: Ash of War: Black Flame Tornado` |
| Miquella's Haligtree → Elphael | Loretta, Knight of the Haligtree (510190) | `Elphael, Brace of the Haligtree` gated; `Miquella's Haligtree` (41) sweeps on `MH/HTP: Loretta's War Sickle` |

**Deferred (each needs a trigger that doesn't exist in the data yet — add a `CHOKEPOINTS` row once
captured):**

- **Leyndell / Golden Godfrey shade** — the shade has NO randomized drop, so there's no location to
  `_can_get` and AP logic can't reference a raw flag. Needs either a synthetic anchor or a
  client-side flag gate; left out of v1.
- **Raya Lucaria / Red Wolf** — needs the back half (Schoolhouse/Debate Parlor/Grand Library) carved
  into its own region first; Red Wolf DOES have a drop (Memory Stone), so once carved it's a
  one-row add.
- **Shadow Keep church-drain** and **Jagged Peak / Ancient Dragon-Man** — DLC env-state /
  unnamed-boss triggers needing an in-game flag (drain) or region+flag (Dragon-Man) capture.

**Pending (Alaric, Windows):** build the apworld, then gen-test with
`extra_region_locks: [chokepoint_locks]` (base seed; DLC optional) and in-game verify: (1) the fill
never strands progression past Godskin Duo / Loretta; (2) killing Godskin Duo sweeps the Farum Azula
before-checks while Maliketh still sweeps Farum Azula Main (likewise Loretta vs. Malenia/Elphael).

> Original sketch below (retained for the deferred cases and the wiring rationale).

---

## Concept

A *chokepoint* is the point partway through a dungeon that the player must clear to reach its back
half. Two things hang off it:

1. **Lock** — gate the dungeon's **after-region** entrance on the chokepoint's trigger, so the fill
   never strands required progression in the back half before the player can clear the choke. Reuses
   the existing region-lock entrance-rule machinery.
2. **Sweep** — when the chokepoint trigger fires, auto-send **all the before-checks** (your idea:
   "the sweep gives all the checks before the choke boss on kill"). This subdivides the current
   whole-dungeon sweep into `[before → choke]` + `[after → mainboss]`, making the choke a real
   sub-reward instead of folding everything onto the end boss.

The **trigger** is a single event flag, and it comes in two flavours:

- **Boss DefeatFlag** — the base-game mid-boss chokepoints (Red Wolf, Loretta-Haligtree, Godskin
  Duo, Golden Godfrey).
- **Environmental state flag** — the DLC pattern (drain the water, open the gate, raise the
  platform). Same plumbing; the trigger is just a world-state flag rather than a boss death.

Mechanically the two are identical to the lock and the sweep — only the flag source differs.

---

## Base game — boss chokepoints

Drawn from the analysis doc. Lock = `_add_entrance_rule(<after_region>, lambda state:
self._can_get(state, "<choke boss drop>"))` (same pattern already used for Nokron gated on Radahn's
remembrance, `__init__.py` ~1848). Sweep trigger = the choke boss DefeatFlag; sweep members = the
before-checks.

| Dungeon | Choke boss | Before (sweep on choke) | After (gated + swept on mainboss) | Lock cleanliness |
|---|---|---|---|---|
| Crumbling Farum Azula | Godskin Duo (flag ~510140) | `Farum Azula` (44) | `Farum Azula Main` (58 → Maliketh/Placidusax) | region split = choke ✓ |
| Miquella's Haligtree | Loretta, Knight of the Haligtree (flag ~510190) | `Miquella's Haligtree` (41) | `Elphael, Brace of the Haligtree` (66 → Malenia) | region split = choke ✓ |
| Leyndell | Golden Godfrey (shade; **no drop** → use its DefeatFlag) | `Leyndell, Royal Capital` + `…Unmissable` (144) | `Leyndell, Royal Capital Throne` (12 → Morgott) | region split = choke ✓ |
| Raya Lucaria | Red Wolf of Radagon (drop via item flag 060440 → use DefeatFlag) | MAG+CC (~42) | SC+DB+RLGL+Rennala (~69) | **needs a sub-area→region carve** (back half isn't its own region) |

Three are gateable straight off existing region boundaries; Raya Lucaria needs the back half
(Schoolhouse/Debate Parlor/Grand Library) split into its own region first. Godfrey and Red Wolf have
no usable boss-drop check, so their gate/sweep trigger must reference the boss DefeatFlag directly
(pull from the `BossAttribution` enumeration, not a `_can_get` on a drop location).

---

## DLC legacy dungeons — different by design

Confirmed: the DLC legacy dungeons **do not have the base-game mid-boss-chokepoint shape**. Each is a
single region cluster that sweeps on **one** mainboss remembrance (current `legacy_groups`,
`__init__.py` ~3958):

- **Belurat** (`Belurat` + `Belurat Swamp`) → Dancing Lion remembrance. One boss for the lot.
- **Castle Ensis** (`Castle Ensis`) → Rellana remembrance. Single region, single boss.
- **Shadow Keep** (6 sub-regions) → Messmer remembrance (the whole cluster sweeps on one drop).
- **Enir Ilim** → Promised Consort Radahn.

So a "beat the mid-boss, back half opens" lock has nothing to bite on in most DLC dungeons — there's
no mid-boss. **The other distinction is environmental/state chokepoints.**

### Shadow Keep — the worked example (state-flag chokepoint)

Shadow Keep is the one DLC dungeon with real internal structure, and its chokepoint is the
**church-basement drain**, not a boss. The regions already encode it:

```
Shadow Keep, Church District (15)  --drain-->  Shadow Keep, Church District Lower (19)  -->  Scadutree Base
```

- **Before drain:** `Shadow Keep, Church District` (15 checks).
- **After drain:** `Shadow Keep, Church District Lower` (19) → `Scadutree Base` beyond.
- **Trigger:** the drain event flag (**TODO: capture the flag** — it's a world-state flag set when
  you drain; not currently modeled, the `Church District → Church District Lower` connection has no
  entrance rule today). This is the "another distinction": gate `Church District Lower` on the drain
  flag, and sweep the Church District checks when it fires.

Other Shadow Keep internal candidate (flag TODO):
- **Golden Hippopotamus** — surfaces as `SK/SKMG: Aspects of the Crucible: Thorns - boss drop` (Main
  Gate). A genuine boss inside Shadow Keep; could gate the Storehouse interior. (This is the closest
  thing Shadow Keep has to a base-style boss choke.)

General DLC rule of thumb: where a DLC *legacy* dungeon lacks a mid-boss, look for a **state flag**
(drain, gate, lift, beacon) as the chokepoint trigger. Same lock + sweep plumbing, env flag instead
of a DefeatFlag.

### Jagged Peak / Bayle — a DLC area that DOES have a boss chokepoint

Unlike the legacy dungeons, the Jagged Peak (Bayle) climb is a linear boss progression and behaves
like the base-game cases. The chain:

```
Dragon's Pit (8)  -->  Jagged Peak Foot (19)  -->  Jagged Peak (16, summit = Bayle)
```

- **Ancient Dragon-Man** is the mid-climb miniboss (its drops show as the `JP/DPT` / `JP/FJP`
  "Dragon Heart - boss drop" entries in `Jagged Peak Foot`) — the chokepoint to the summit.
- **Bayle the Dread** is the area end-boss at the summit (`JP/JPS: Heart of Bayle - mainboss drop`,
  flag **510630**), in `Jagged Peak`.
- **Lock:** gate `Jagged Peak` (summit) on the Ancient Dragon-Man DefeatFlag → before = `Dragon's
  Pit` + `Jagged Peak Foot` (~27), after = `Jagged Peak` (16, Bayle). Region boundary `Jagged Peak
  Foot → Jagged Peak` ≈ the choke. (TODO: capture the Ancient Dragon-Man DefeatFlag; the Dragon
  Heart drops are at DPT/FJP but the boss isn't named in the description.)

---

## Wiring sketch

A small per-chokepoint table drives both halves:

```python
# region_spine.py (or a new chokepoints.py)
# after_region -> (trigger_flag, before_regions)
CHOKEPOINTS = {
    "Farum Azula Main":                 (FLAG_GODSKIN_DUO,  ["Farum Azula"]),
    "Elphael, Brace of the Haligtree":  (FLAG_LORETTA_HALI, ["Miquella's Haligtree"]),
    "Leyndell, Royal Capital Throne":   (FLAG_GODFREY_SHADE,["Leyndell, Royal Capital",
                                                             "Leyndell, Royal Capital Unmissable"]),
    "Shadow Keep, Church District Lower":(FLAG_SK_DRAIN,     ["Shadow Keep, Church District"]),
    # Raya Lucaria after a back-half carve:
    # "Raya Lucaria Academy Back":      (FLAG_RED_WOLF,     ["<MAG+CC regions>"]),
}
```

**Lock** (only meaningful under region gating; opt-in like the bundle locks via an
`extra_region_locks` key, e.g. `chokepoint_locks`):

```python
for after, (flag, befores) in CHOKEPOINTS.items():
    if after in self.created_regions:
        # boss drop available -> _can_get on it; otherwise reference the flag via a state helper
        self._add_entrance_rule(after, lambda state, f=flag: self._has_flag_progress(state, f))
```

**Sweep** (refine the existing whole-dungeon legacy_groups sweep into two triggers): in the
`dungeon_sweeps` builder (`__init__.py` ~3918), where a dungeon has a chokepoint, emit
`{choke_flag: [before-check ids]}` in addition to `{mainboss_flag: [after-check ids]}`, instead of
one `{mainboss_flag: [all ids]}`. The client already watches arbitrary trigger flags, so an env
flag (drain) works identically to a boss DefeatFlag.

This is purely additive to `SPEC-dungeon-sweep.md` — same `dungeonSweeps` slot_data, just finer
triggers — and the lock half reuses the region-lock entrance-rule path verbatim.

---

## Open items
1. **Flags to capture:** Red Wolf DefeatFlag, Golden Godfrey shade DefeatFlag, Godskin Duo (~510140
   confirm), Loretta-Haligtree (~510190 confirm), **Shadow Keep church-drain state flag**, Golden
   Hippopotamus DefeatFlag. Boss flags from the `BossAttribution` enumeration; the drain flag needs
   an EMEVD/in-game capture.
2. **Raya Lucaria back-half carve:** split SC+DB+RLGL into a region so it can be locked, and confirm
   the CC↔SC boundary around Red Wolf.
3. **Should the lock be its own item or pure logic?** Pure-logic (gate on the trigger flag /
   `_can_get` the boss) keeps it itemless and is the natural fit; an item-lock would double-gate.
4. **DLC scope:** likely Shadow Keep (drain) only for v1; Belurat/Ensis/Enir Ilim have no internal
   chokepoint to gate.
5. **"Gaol area" / Ancient Dragon-Man:** pin the region + flag before including.
