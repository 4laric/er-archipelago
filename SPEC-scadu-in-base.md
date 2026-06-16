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

---

# ADDENDUM: dlc_only early-game balance — "one-shot start" (2026-06-16, Alaric)

Different problem from the main spec above (which is about transplanting DLC bosses INTO the
base game). Here the player is genuinely IN the Land of Shadow (dlc_only), so the vanilla
blessing system works normally — the leveling-gate problem above does NOT apply. The issue is
that a dlc_only run STARTS at Scadutree Blessing 0 with a low rune level and a low weapon
upgrade (base game skipped), against enemies the DLC has already scaled up. Result: you get
one-shot from the first zone.

## Quantified scaling (vanilla param dump, SpEffectParam.csv)

The enemy "SOTE - Area Scaling" speffect (`20007000`+, applied per-zone to every DLC enemy)
multiplies the enemy's UNSCALED base by:

| Zone (speffect)                | Attack | maxHP | Defense | Poise dmg | Status |
|--------------------------------|--------|-------|---------|-----------|--------|
| Gravesite Plain  (20007000)    | ×3.75  | ×7.0  | ×1.22   | ×1.37     | ×2.5   |
| Scadu Altus      (20007040)    | ×3.77  | ×10.0 | ×1.23   | ×1.39     | ×2.5   |
| Scadutree Base   (20007070)    | ×3.80  | ×11.8 | ×1.24   | ×1.40     | ×2.5   |
| Jagged Peak/Enir (20007110)    | ×3.83  | ×14.1 | ×1.25   | ×1.40     | ×2.5   |

KEY INSIGHT: enemy ATTACK is ~×3.75 flat across the whole DLC and barely climbs — that's the
one-shot. What scales with depth is HP (×7 → ×14), i.e. later zones are spongier, not bitier.
Attack scaling lives in `physicsAttackPowerRate` (+ magic/fire/thunder/dark), field [20]; HP in
`maxHpRate` [6]; defense in `physicsDiffenceRate` [28]; poise in `staminaAttackRate` [52].

The intended counterweight is the player blessing speffect `20000100+N` (combat track):

| Blessing N | You deal | You take            |
|------------|----------|---------------------|
| 0          | ×1.00    | ×1.00 (no offset)   |
| 5          | ×1.35    | ×0.74  (−26%)       |
| 10         | ×1.65    | ×0.61  (−39%)       |
| 20         | ×2.05    | even less           |

So at blessing 0 you eat the full ×3.75; at blessing 10 effective incoming ≈ 3.75×0.61 ≈ ×2.3
(survivable). The fix is supplying the blessing the dlc_only start is missing, NOT necessarily
nerfing enemies.

## Two levers — pros / cons

**A. Front-load blessing (recommended).** Place Scadutree Fragments early so blessing ramps
fast (see option design below), and/or seed a baseline.
  + Works WITH the game's curve — enemies keep designed numbers, fights feel like real SOTE.
  + One knob; self-scales as you collect more fragments; hits both offense and defense.
  + Leaves regulation.bin untouched → composes cleanly with enemy rando / NG+ / future bakes.
  + Keeps the fragment checks meaningful (they ARE your power curve).
  + Can be a per-seed slot_data option → player-tunable, reversible.
  − Doesn't touch HP bloat (×7–14); with a low dlc_only weapon upgrade, fights can still be
    spongy even once you stop getting one-shot.
  − Delivery wrinkle: the game recomputes the blessing speffect from STORED level on every map
    load, so a client force-applying `20000100+N` can get stomped on a zone transition. Seeding
    real fragments + revering at a grace (works in dlc_only) is more robust than a SpEffect poke.
  − A fixed starting N stacks with collected fragments → can overshoot late if not tuned.

**B. Nerf the area speffect directly.** Lower `physicsAttackPowerRate` on `20007000`+ (e.g.
3.75 → ~2.75) and/or `maxHpRate` in the regulation bake.
  + Precise control over exactly the bite; can tune attack independently of HP/poise/status.
  + Fixes the brutal EARLY start with no item delivery or revering — works at blessing 0.
  − Global + permanent in the bake: every DLC enemy weaker for the whole run, so the back half
    trivializes once your blessing naturally catches up (double-dip).
  − Fights the game's own system → you maintain a custom curve that drifts if blessing/enemy
    rando change later.
  − ~12 zone rows × 4 variant families (base / Human-NPC / NG+ / DLC-completion NG+) — must edit
    all or NG+/humanoid enemies miss the nerf.
  − Devalues the fragment economy you just turned into checks.

Recommendation: front-load blessing (A) since the symptom is one-shots and attack is flat; if
still spongy, add a light HP-ONLY trim rather than a blanket attack nerf. Use B only if the goal
is a flatter/easier DLC throughout.

## Option design (the actual ask)

Add a Scadutree Fragment DISTRIBUTION option controlling where fragments land in the fill:

- **`early` / sphere-1 (DEFAULT, "loaded into sphere 1"):** force the Scadutree Fragments (and
  likely Revered Spirit Ashes) into the earliest reachable locations so blessing ramps fast and
  the one-shot start is gone. AP mechanism: `self.multiworld.early_items[self.player]["Scadutree
  Fragment"] = <count>` (forces N copies into sphere 1), or priority/early-location placement.
  Possibly pair with a small starting count / baseline blessing.
- **`uniform` ("true sickos"):** leave fragments in the general pool, distributed normally /
  spread across spheres — blessing arrives whenever it arrives, brutal early game intact.

Open sub-questions: how many to front-load (target blessing ~5–8 early?); front-load Revered
Spirit Ashes too or combat-only; whether to also expose a flat `starting_blessing_level`; and
whether `early` should guarantee a fixed number in sphere 1 vs just bias toward early.
Implementation lives in the apworld fill (early_items / placement), not the client or the bake.
Pairs with [[er-dlc-only-spec]], [[er-trimmed-audit]] (Scadu plan).

DRAFT IMPLEMENTED: `patch_scadu_frontload.py` (repo root, 2026-06-16). Adds option
`scadu_frontload` (Range 0..50, default 8) = "front-load N TOTAL fragments into sphere 1" and
wires `multiworld.early_items[player]["Scadutree Fragment" / "...x2"]` in create_items, gated on
enable_dlc; 0 = sicko/normal distribution. Counts by fragment VALUE (x2 = 2 frags, one slot),
singles first. Combat track only (Revered Ashes untouched). Gen-time fill bias, not shipped in
slot_data. Run on Windows: `python patch_scadu_frontload.py` then `.\build.ps1 -Generate`,
gen-test that fragments actually seat early under the region-lock graph.
