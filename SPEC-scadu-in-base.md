# SPEC: Scadutree blessing during main-game DLC-boss fights

Status: FUTURE PROJECT, not started. (Alaric, 2026-06-13)
Context: enemy rando / DLC-unstrip puts DLC bosses into the base game (see the DLC enemy
rando work). Those bosses are tuned for the DLC's Scadutree scaling system, which is gated
to the Land of Shadow maps and does not apply in the base game. This spec covers applying
the relevant scaling so a transplanted DLC boss fights the way it was designed to.

## The system, as it actually exists in params

Two distinct speffect families (Paramdex/ER/Names/SpEffectParam.txt), both normally
applied by the DLC's own region/map events and therefore inactive in the base game:

- **Player blessing:** `20000100`..`20000120` = "Scadutree Fragment: 0" .. "...: 20".
  One speffect per blessing level (0-20). This is the player-side buff: more damage dealt,
  less damage taken. Effect is map-agnostic; only its *application* is Land-of-Shadow-gated.
- **Enemy area scaling:** `20007040`+ = "SOTE - Area Scaling: <subregion>" (Scadu Altus,
  Scadutree Base, Scaduview / Ancient Ruins of Rauh, ...), with parallel "Human-NPC",
  "NG+", and "DLC Completion NG+" variants (`200072xx`, `200074xx`, `200076xx`,
  `200084xx`, `200086xx`). These scale the *enemy* up to the power the DLC expects it to be
  fought at for its zone.

DLC balance is the interaction of the two: a de-/up-scaled enemy vs a blessing-buffed
player. Transplanting a boss into the base game drops **both** halves.

## Why "just buff the player" is wrong

If only the player blessing (`20000100+N`) is applied during a base-game fight, the player
keeps full base-game power (RL + weapon upgrades, un-touched by any area scaling) AND gains
blessing on top, while the boss is at its raw DLC stats with no area-scaling speffect. Net:
the fight is *easier* than the real DLC, not equivalent. Faithful emulation needs the
enemy-side speffect too.

## Two implementation tiers

- **Tier 1 — "not obviously broken" (minimal):** apply only the player blessing speffect
  `20000100+N` for the current blessing level N, scoped to the arena. Fixes the worst case
  (a blessing-0 player meeting a boss balanced for blessing 10+). Skews easy; cheap.
- **Tier 2 — DLC-accurate:** apply blessing to the player AND the boss's intended
  area-scaling speffect to the boss NPC (pick the subregion tier matching where the boss
  lives in the DLC). Faithful; more bookkeeping (per-boss tier mapping + applying to the
  enemy entity, not just the player).

Recommend shipping Tier 1 first (it's the 80%), leave Tier 2 as a follow-up once boss→zone
tier mappings are worth maintaining.

## Scoping — never global

Applying blessing globally would buff the player across the entire base game and trivialize
it. Scope strictly to the transplanted-DLC-boss encounter:

- **Apply** on boss-arena entry / fog-gate cross (or on the boss entity loading/activating).
- **Remove** on boss death OR arena exit, so the buff never persists into open-world play.

This is the same trigger shape the runtime client already uses for flag-gated state pokes
(the `PollLocationFlags` / `dungeonSweeps` tick). The client is the natural home: it
already watches flags and manipulates game state, and it avoids editing common EMEVD.

## The leveling-gate problem (the actual blocker)

You cannot raise blessing level outside the DLC. Leveling is the "Revere Scadutree
Fragment" / "Increase Scadutree Blessing" option, and that menu is **only available at a
Land of Shadow Site of Grace**. A base-game-focused run can *hold* Scadutree Fragments and
Revered Spirit Ashes but has no way to spend them, so the game's stored blessing level
stays **0**. This guts the obvious design ("apply the player's current blessing level"):
current level is always 0, so the buff is always nothing.

So the feature can't read the in-game blessing level — it has to **own** the level itself.
Two ways out:

### Route A — client-derived blessing (recommended)

Decouple blessing from the grace ritual entirely. The AP layer already delivers Scadutree
Fragments / Revered Spirit Ashes as items (or could), and the client already tracks what's
been granted. So:

1. Count fragments the player has **received** (via the AP grant log the client maintains,
   not the in-game revered level). Two independent tracks — goods `2010000` Scadutree
   Fragment (combat) and `2010100` Revered Spirit Ash (summon).
2. Convert count → level N per track via a fragment→level cost table (non-linear: each
   level costs progressively more fragments). Bake the table into the client or ship it in
   slot_data so it tracks any param edits, OR define a custom curve — Route A owns the
   level, so it does NOT have to replicate vanilla. See "Confirmed IDs" for sourcing.
3. Apply the matching speffect per track during the scoped encounter:
   combat = `20000100 + N_combat` (N 0-20), summon = `20000200 + N_summon` (N 0-10),
   Torrent = `20000300 + N_summon`. Base IDs confirmed in GameSystemCommonParam.

Net: fragments become "DLC-boss difficulty offset" items whose power only manifests against
transplanted DLC bosses. Coherent, and it sidesteps menus/graces completely. This is the
recommended path because it lives entirely in the client (where the rest of this feature
already lives) and needs no EMEVD/menu modding.

### Route B — unlock revering at base-game graces

Keep the vanilla ritual but make the "Increase Scadutree Blessing" option appear at all
graces, so the player spends held fragments normally and the game tracks N itself. More
faithful to vanilla feel, but requires menu/grace-event modding to expose the option
outside the DLC, and the player still has to manually revere. Reading N afterward becomes
trivial (it's the real stored level). Heavier and less self-contained than Route A.

### N-sourcing once Route A is chosen

With Route A the level is client-owned, so "read the game's blessing level" is moot. The
only read needed is the fragment **grant count**, which the client already has from the AP
item stream — no game-memory hook required. (If you instead need to read held-inventory
fragment counts, that's a GameDataMan inventory read; confirm the goods IDs first.)

## Confirmed IDs and values (verified 2026-06-13 against the vanilla param dump at
## elden_ring_artifacts/vanilla_er/, Paramdex/ER, + randomizer diste)

**The game stores base IDs and adds the level as an offset** — authoritative, from
GameSystemCommonParam (single row):

- `baseScaduBlessingSpEffectId = 20000100`            → combat, `20000100 + N`, N 0..20
- `baseReveredSpiritAshBlessingSpEffectId = 20000200` → summons, `20000200 + N`, N 0..10
- `baseReveredSpiritTorrentBlessingSpEffectId = 20000300` → Torrent/mounted, `20000300 + N`

So there are **three** tracks, not two. Scadutree Fragments drive the combat track;
Revered Spirit Ashes drive BOTH the summon (`20000200+N`) and Torrent (`20000300+N`)
tracks off the same summon-blessing level. Apply the matching speffect(s) per track.

**Player combat buff is a flat damage-correction speffect (map-agnostic — works anywhere,
which is what makes this whole feature possible).** From SpEffectParam.csv, fields
`atkPlayerDmgCorrectRate_*` (outgoing) and `*DamageCutRate` (incoming):

| Scadutree level | outgoing dmg ×  | incoming dmg × (lower = tankier) |
|-----------------|-----------------|----------------------------------|
| 0 (`20000100`)  | 1.00            | 1.00                             |
| 10 (`20000110`) | 1.65            | 0.606                            |
| 20 (`20000120`) | 2.05            | 0.488                            |

Summon track (`20000200+N`) uses attack-rate fields instead: level 5 ≈ ×1.4, level 10 ≈
×1.89. (Magnitudes scale roughly linearly between the sampled points; pull the exact
per-level row from SpEffectParam.csv if precise tuning is needed.)

Fragment goods (EquipParamGoods) and world totals (randomizer iteminfo.txt):

- Scadutree Fragment `2010000` — 50 placed in the world → supports combat level 20.
- Revered Spirit Ash `2010100` — 25 placed in the world → supports summon level 10.

**Cost curve — RESOLVED (source: Fextralife, post-patch; cross-checked against the param
dump).** Not in any regulation param (it's grace-menu EMEVD), but the datamined curve is
known. Cumulative Scadutree Fragments required to REACH each combat level:

```
level:      0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20
cumulative: 0  1  3  5  7  9 11 13 15 17 20 23 26 29 32 35 38 41 44 47 50
```

Per-level cost = 1, then +2 per level through L9, then +3 per level through L20. The
client mapping is the inverse: `N_combat = max N such that cumulative[N] <= fragments_recvd`.
Implement as a 21-entry threshold array and binary-search / linear-scan it.

Validation: Fextra's post-patch damage multipliers match SpEffectParam exactly — L10
1.65× out / 0.606× in, L20 2.05× out / 0.487× in — so this is the live curve, and the
"pre-patch" column in that table is stale (ignore it).

Summon (Revered Spirit Ash) curve (source: Fextralife, cross-checked against SpEffectParam —
L5 1.400x / L10 1.890x summon damage match `20000205` / `20000210`). Cumulative Revered
Spirit Ashes to REACH each summon level:

```
level:      0  1  2  3  4  5  6  7  8  9 10
cumulative: 0  1  2  3  5  7 10 13 16 20 25
```

Per-level cost = 1,1,1,2,2,3,3,3,4,5. Same inverse mapping as combat:
`N_summon = max N such that cumulative[N] <= ashes_recvd`. Drives both the summon
(`20000200+N`) and Torrent (`20000300+N`) speffects.

## Edge cases

- **Boss dies / player flees, speffect lingers:** must remove on both death and exit; a
  watchdog on the arena flag is safer than relying on a single death event.
- **Multiple transplanted DLC bosses active at once** (e.g. open-world field placement):
  apply per-encounter; don't stack. Prefer arena/fog bosses for Tier 1; open-world DLC
  bosses are messier to scope and can wait.
- **Player already in NG+:** there are NG+ / DLC-completion area-scaling variants — Tier 2
  must pick the matching variant or accept base-NG scaling.
- **Stacking with base-game difficulty options:** document that this is additive to any
  enemy-rando difficulty knobs; don't double-scale.

## Work items

1. Pick Route A vs B for leveling (recommend A: client-owned level from AP fragment grant
   count + vanilla cost table). This unblocks everything; the in-game blessing level is
   unusable because it can't be raised outside the DLC.
2. DONE: both cost curves transcribed above — combat cumulative [0,1,3,5,7,9,11,13,15,17,
   20,23,26,29,32,35,38,41,44,47,50]; summon cumulative [0,1,2,3,5,7,10,13,16,20,25]. All
   speffect/goods IDs, buff magnitudes, and curves are confirmed. No remaining data unknowns.
3. Client: on transplanted-DLC-boss arena entry, apply `20000100 + N_combat`,
   `20000200 + N_summon`, and `20000300 + N_summon` to the player; remove on death/exit.
   (Tier 1.)
4. Identify which placements count as "transplanted DLC boss" — needs a marker the bake
   emits (boss is DLC-origin AND placed in a base-game map), analogous to how dungeonSweeps
   ships a client-only map in slot_data.
5. Tier 2 (later): per-boss zone→area-scaling-speffect map (`20007040`+ families); apply the
   enemy-side speffect to the boss entity; handle NG+ variants.
6. Test: blessing-0 save vs a transplanted DLC boss — confirm buff applies in-arena, damage
   numbers shift, buff is gone on the other side of the fog gate, no persistence in the
   open world.

## Open questions

- Should Tier 1 buff be capped (e.g. min(N, some_cap)) so a maxed-blessing late save doesn't
  faceroll an early transplanted boss? Probably tie the cap to the boss's intended zone tier
  — which is really Tier 2 creeping in.
- Do we want the inverse for the symmetric case (a BASE-game boss transplanted INTO the DLC
  via the same enemy rando)? That boss would get area-scaled as an enemy automatically and
  may need de-scaling. Out of scope here; note it exists.
