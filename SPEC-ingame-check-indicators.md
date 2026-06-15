# SPEC — In-game check indicators

Status: DRAFT 2026-06-15. Bake-side only, contract-free (param + EMEVD output; no apworld/client
contract bump). Companion to the AP-check pickup glow (#12, `er-bake-polish-glow-doublegrant`) and
the `enemydrop` data tag (TODO §17).

## Motivation

A player shouldn't need encyclopedic game knowledge to know which enemies / scarabs carry an AP
check. Give non-intrusive in-world cues so "kill this, it's a check" and "a check is nearby" are
legible without a wiki. Two cue channels:

- **Visual** — a ghost/spectral edge-glow SpEffect on check-carrying *enemies* (the "Golden Vow
  guy" case).
- **Audio** — the scarab scuttle SFX, made into a reliable 1:1 "nearby check" tell.

Same philosophy as the pickup glow (legendary `rarity=3` on AP item pillars): a small, reversible
bake-side polish, no contract impact.

---

## Part A — Enemy check marker (visual)

### A.1 The effect — reuse existing code

`EnemyRandomizer.cs:1003-1020` already mints a Siofra-follower spectral chain to tint duplicate
bosses:

```
PhantomParam (260 base)  ->  SpEffectVfxParam (51508)  ->  SpEffectParam (13177)
  alpha=1, edgePower=0.5, glowScale=0, edgeColorR/G/B
```

Clone this once to mint a dedicated **AP-marker SpEffect** with a distinct, *unused* color. The
dupe-boss set already claims blue / red / white / orange / purple, so use **gold (~255,200,0)** to
read as "loot here." Keep `alpha = 1` (enemy stays solid, just gains a glowing edge) and
`glowScale = 0` (their own perf note). One SpEffect id, created at bake.

### A.2 Which enemies get it

Drive off the `enemydrop` set (TODO §17): any location whose itemslots source matches
`/ enemy c\d{4}_\d{4}/`. Two flavors, both eligible:

- **Pure enemy-lot drops** — Golden Vow (Godrick Knight `c4351_9000`, entity `id 1043390280`),
  Gravitas (Onyx Lord `c3600_9000`).
- **Event-enemy drops** — Lion's Claw (Elder Lion), Bloody Slash (Godrick Knight @ Fort Haight),
  Flame Spear (Fire Knight).

The `id MMM` in the annotation is the placed **entity id** — that's the `SetSpEffect` target.

Scope toggle: mark *all* enemy-drop checks, or only the curated "fun"/on-path ones. Under
trimmed/lean, **skip enemies whose location was trimmed out** (don't glow a non-check). Consider
excluding bosses/named enemies (already obvious) and marking only non-obvious overworld carriers.

### A.3 Apply mechanism — EMEVD, NOT NpcParam

`NpcParam.spEffectIdNN` is shared across every instance of a model, so setting the marker there
would glow **every** Godrick Knight, not just the Golden Vow one. Instead emit a baked per-map
**EMEVD `NewEvent`** that runs on map load and calls `SetSpEffect(entityId, markerSpEffect)` for
each tagged entity id. This is the same baker-owned EMEVD pattern used for region-lock fog walls
(`er-region-lock-physical-enforcement`). Running on map load also reapplies the marker after a
rest/reload.

### A.4 Caveats / open items

- Entities without a unique EntityID (generator/group spawns) need one assigned at bake first; the
  randomizer already edits MSBs, so doable but extra work.
- Verify the marker SpEffect is permanent/looping (base `13177` is the followers' constant look) so
  it doesn't time out mid-fight.
- Visual confusion: the spectral look resembles co-op phantoms / spirit summons. Gold edge + solid
  alpha should distinguish; playtest, dial back if too noisy.

---

## Part B — Scarab audio cue (audio)

### B.1 Current state (grounded in the data)

- **98** `scarab=True` checks; **all** drop Ash of War / Somber Smithing Stone / spell — every
  scarab is a real check.
- Crystal Tears (physick "flask") are tagged **`basin`**, NOT `scarab`. So in this randomizer the
  crystal-tear / "flask" scarabs the player is thinking of are handled separately, and the scarab
  scuttle SFX already correlates with AoW/stone checks.

So the scuttle sound is *almost* a clean "nearby check" tell already. The work is closing the gaps
that make it a false positive.

### B.2 Goal — make the scuttle SFX 1:1 with checks

Suppress / alter the sound where it would mislead:

- **Trimmed/lean false positives:** scarab checks dropped from the pool (e.g. far somber-stone
  scarabs cut by the surgical somber trim) still scuttle in-world → suppress their SFX when their
  location is trimmed out, so a sound always means a live check.
- **Type discrimination (optional):** if the player specifically wants the sound to mean
  "AoW/smithing-stone scarab," and physick/crystal-tear scarabs exist as scarab entities with the
  same SFX, alter their cue. (Verify first — tears are `basin`-tagged here, so tear scarabs may not
  be in the scarab set at all.)

### B.3 Mechanism (to investigate)

Identify what triggers the scuttle SFX on scarab entities — likely an NpcParam SFX/SoundEvent field
or a looping sound on the enemy. Then null it on the targeted scarabs at bake (param edit) or via
EMEVD. **TBD:** locate the exact SFX/sound id and the param/field that fires it.

---

## Build / test

- Bake-side only (params + EMEVD). Windows-only: `build.ps1 -Randomizer` then `-Bake -Deploy`.
  CRLF+BOM files patched via Python (`crlf-edit-truncation`).
- Add a kill-switch env var mirroring the glow step (`AP_SYNTH_DIAG=noglow`) — e.g. `AP_MARKER=off`.
- Tests: load near the Golden Vow Godrick Knight → only that knight glows gold (not other Godrick
  Knights); kill it → check confirmed. In a trimmed seed, confirm a trimmed-out scarab is silent.

## Relation to other work

- `enemydrop` data tag (TODO §17) supplies the entity list for Part A.
- `SPEC-check-trim.md` supplies which locations are dropped (false-positive suppression, both parts).
- Pickup glow (#12, `er-bake-polish-glow-doublegrant`) is the item-side analog of this.
