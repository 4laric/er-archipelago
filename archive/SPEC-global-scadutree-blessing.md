# SPEC: Global Scadutree Blessing — fragments as a game-wide AP power curve

Status: DRAFT, not started. (Alaric, 2026-06-20)

Sibling/prereq reading: [[er-scadu-in-base]] = `SPEC-scadu-in-base.md`. That spec emulates DLC
balance for DLC bosses **transplanted into the base game** and is emphatic that blessing must be
**arena-scoped, never global**. This spec deliberately does the opposite: it makes Scadutree
Fragments a *global, game-wide* power-progression currency in any seed. The two are not in
conflict — they're different products. The in-base spec asks "how do I make one transplanted
boss fight like the DLC?"; this spec asks "what if collecting fragments is the whole run's power
curve, everywhere?" Where they overlap (IDs, curves, the level-sourcing mechanism), this spec
reuses the in-base spec rather than re-deriving, and that prior work is what makes this cheap.

## Why fragments are a near-ideal AP item (the motivation)

Scadutree Fragments and Revered Spirit Ashes are unusually well-shaped for Archipelago:

- **Numerous and granular.** 50 combat fragments + 25 revered ashes = 75 power tokens in a
  full DLC seed. That's a lot of individually-meaningful checks/items, each a small "ding".
- **Incremental, non-binary power.** Unlike a Great Rune or a key, a fragment is never "the one
  that unlocks X". Each one nudges a smooth curve. That's exactly the texture AP filler wants:
  always-welcome, never-bricking.
- **Zero logic-gating risk.** Because no fragment is ever *required* to reach a location, they
  classify as `useful` (or even `filler`), and the fill never has to reason about them. They can
  be sprinkled anywhere — early, late, in another player's world — with no plando/reachability
  consequences. This is the safest possible progression-feeling item.
- **A built-in difficulty dial.** The fragment economy is literally a tuning knob FromSoft already
  balanced. AP gets to redistribute *when* the player gets power, which is the core AP fantasy.
- **The buff is map-agnostic.** The player blessing speffect (`20000100+N`) applies anywhere; only
  its *application* is normally Land-of-Shadow-gated (confirmed in the in-base spec). Remove the
  gate and the buff Just Works in Limgrave. This single fact is what makes a global feature
  buildable at all.

The catch — and the whole reason this is a spec and not a one-liner — is **scaling**. A global
player buff on top of un-touched base-game power trivializes the base game. Making fragments
*matter* without making the game a faceroll is the actual engineering problem. See "Three modes".

## Relationship to existing work

- **[[er-completion-scaling]]** already re-tiers regions by `region_order` and scales enemies
  (geographic + sphere-basis baker bridge). That feature is the natural *enemy-side* counterweight
  to a global blessing: completion-scaling makes enemies tougher by depth; global blessing is the
  player-side currency that keeps pace. Mode C below leans on this directly instead of inventing a
  second enemy-scaling system.
- **[[er-scadu-frontload]]** (`patch_scadu_frontload.py`, option `scadu_frontload`) already biases
  fragments into sphere 1 for `dlc_only` starts. Its pool/fill machinery (early_items, value-aware
  counting, x2 fragments) is reusable for injecting fragments into a **base-game** pool, which has
  none natively.
- **[[er-dlc-only-spec]]**: in `dlc_only` the player is genuinely in the Land of Shadow, so vanilla
  revering works and the stored level is real. The global feature is for *base-game* (or mixed)
  seeds where the leveling gate otherwise pins blessing at 0. The two must not double-apply — see
  "Interactions".

## Three deployment modes (the design fork)

`global_scadutree_blessing`: `off` | `player_only` | `scaled`

- **`off` (default):** current behavior. Fragments only matter in `dlc_only` / the arena-scoped
  in-base feature. No change.
- **`player_only` ("power fantasy / accessibility"):** apply the client-owned blessing globally to
  the player; enemies untouched. The base game gets progressively easier as you collect fragments.
  Cheap (client-only, no bake), great as a casual/accessibility knob, and a complete shippable Tier
  1. Honest downside: it trivializes vanilla balance by design.
- **`scaled` ("the real ask"):** apply the player blessing globally AND scale base-game enemies up
  so net difficulty is tunable rather than free. This is where "worth investing time figuring out
  scaling" lives. Two sub-strategies for the enemy side:
    - **C1 — reuse completion-scaling.** Let [[er-completion-scaling]]'s region-tier enemy scaling
      provide the upward pressure; global blessing is the matching player counterweight. No new
      enemy-scaling system; the two features ship as a paired "DLC-style scaling run" preset.
    - **C2 — apply DLC area-scaling to base enemies.** Bake the DLC's own `20007000+` "SOTE - Area
      Scaling" speffects onto base-game enemies (mapped base-region → DLC zone tier). Most faithful
      to the DLC's tuning, but heaviest: 12 zone rows × 4 variant families (base / Human-NPC / NG+ /
      DLC-completion NG+), and you must pick a base-region→zone mapping. See the in-base spec's
      quantified scaling table for the multipliers.

Recommendation: ship `player_only` first (proves the global-application + persistence machinery,
which is the hard part), then `scaled` via **C1** (reuses validated work), and treat **C2** as a
"maximum faithfulness" stretch. The scaling curve is the open design question, not the plumbing.

## The load-bearing technical problem: making the level *persist*

This is the crux and the main reason to spec carefully. From the in-base spec's addendum:

> the game recomputes the blessing speffect from STORED level on every map load, so a client
> force-applying `20000100+N` can get stomped on a zone transition.

For an arena-scoped feature that's fine (re-apply on arena entry). For a **global, persistent**
feature it's the central issue: a one-shot SpEffect poke will be silently cleared the next time
the player loads a map, fast-travels, or dies. Three ways to beat it, increasing robustness:

### P1 — watchdog re-application (Tier-1, client-only)

Re-apply `20000100+N_combat` (+ summon/Torrent) on the existing client tick (the
`PollLocationFlags` / `dungeonSweeps` cadence) and on detected map-load / respawn. Simple, no new
RE, composes with everything. Risk: a brief window each load where the buff is absent, and you're
fighting the engine every frame-ish. Acceptable for `player_only`; good enough to validate the
feature.

### P2 — write the *stored* blessing level (Tier-2, recommended end-state)

Find and write the game's stored blessing-level field — the same value the DLC grace ritual
("Increase Scadutree Blessing") writes. If we own that field, the engine itself recomputes and
re-applies the correct `20000100+N` on every map load, death, and NG+ transition. The buff becomes
**native and durable** with no per-frame fighting. This is the clean global solution.

**De-risked (research 2026-06-20):** the runtime client *already* resolves the
`GameDataMan → PlayerGameData` pointer chain and edits player-data structs in place — that's how
`removeFromInventory` (TODO #6) and `auto_upgrade` work today (`er_gamehook_win.cpp`:
`g_gameDataManPtrLoc`, `GAMEDATAMAN_PGD_OFF`, the EquipInventoryData edit path). So P2 is **not** new
plumbing; it's "find one offset" — the byte offset of the stored combat (and, if used, summon)
blessing level inside PlayerGameData / the SOTE save block — then write it.

**RESOLVED (2026-06-20, from the local Hexinton all-in-one CE table at
`elden_ring_artifacts/eldenring_all-in-one_Hexinton-v6.0_ce7.5.ct`, mirrored by TGA v1.12.0
"Scadutree/Revered Blessing pointers to Statistics"):** both levels are single bytes in
PlayerGameData, adjacent:

| Field                         | CE pointer (base → offsets)        | Resolved address     | Type        |
|-------------------------------|------------------------------------|----------------------|-------------|
| Scadutree Blessing (combat)   | `GameDataMan → +0x08 → +0xFC`       | `*(pgd + 0xFC)`      | signed Byte |
| Revered Spirit Ash (summon)   | `GameDataMan → +0x08 → +0xFD`       | `*(pgd + 0xFD)`      | signed Byte |

(`GameDataMan + 0x08` is the PlayerGameData pointer in the table's convention — the same branch that
holds Humanity `+0x64`, Arcane `+0x58`, etc.) The client *already* resolves a PlayerGameData pointer
(`pgd`, via `GAMEDATAMAN_PGD_OFF`) for inventory work, so the implementation is literally
`read/write byte at pgd + 0xFC`. v1 writes only `+0xFC` (combat; Alaric runs summons off). Clamp to
0..20 (no speffect row beyond `20000120`). One reconciliation to verify on Windows (below): confirm
the client's resolved `pgd` equals the table's `[GameDataMan+0x08]` base, since `GameDataMan`'s named
struct member sits at `+0x10` in the client header — if the client dereferences a different base, the
`0xFC` is measured from whatever base the client's `pgd` actually points at.

### Verification procedure (Windows, ~5 min)

1. Load the Hexinton/TGA CE table on the same `eldenring.exe 2.6.2.0` the mod targets (offline, EAC
   off). Find Statistics → "Scadutree Blessing Level -- DLC".
2. In the DLC, revere once at a Land-of-Shadow grace; confirm the CE value ticks 0→1 (and matches the
   in-game blessing). This proves `pgd+0xFC` is the live stored level.
3. Note CE's resolved PlayerGameData address; compare to the client's logged `pgd`. Equal ⇒ use
   `+0xFC` directly. Different ⇒ re-base the offset off the client's `pgd`.
4. From the client, write the byte and trigger a recompute (map load or grace rest); confirm the
   `20000100+N` speffect applies in the base game and the damage numbers shift.

This is the single highest-value research item, and it's now down to a 5-minute on-Windows confirm.

### P2′ — write the stored level *on grace rest* (RECOMMENDED synthesis)

This is the "something clever for leveling at main-game graces" Alaric asked for, and it's strictly
better than both P2-always and P3. The client owns the AP fragment grant count (Route A); it watches
for a **grace rest** (already a detectable event) and, on rest, writes the stored blessing level =
`curve(grant_count)`. Net effect:

- It *feels* like revering — your blessing goes up when you sit at a grace, anywhere in the base game.
- The engine then re-applies `20000100+N` natively on every load/death/NG+ (the P2 durability win).
- **No EMEVD/menu modding** (the expensive part of the old P3) and **no manual fragment spend** — the
  AP grant count is the source of truth; the grace rest is just the diegetic apply trigger.
- Re-asserting on rest also self-heals if anything ever clobbers the stored value.

So P2′ = P2's durable native apply + a grace-rest trigger for diegesis, with Route-A as the level
source. Recommended end-state. (P1 watchdog remains the no-RE fallback until the offset is found.)

### P3 — unlock real revering at base-game graces (heaviest, not recommended)

EMEVD/menu mod so the vanilla "Increase Scadutree Blessing" option appears at all graces and the
player spends held fragments manually. Most faithful to vanilla feel, but requires menu/grace-event
modding AND fights AP-driven delivery (two sources of truth for the level). P2′ delivers the same
"level up at a grace" experience without the menu work or the double-bookkeeping.

## Level sourcing — REUSE the in-base spec (already resolved)

No new work here; this is why the in-base spec was worth doing first. Use **Route A**: client-owned
level derived from the AP fragment **grant count**, not the in-game revered level (which is pinned
at 0 outside the DLC). Three tracks off `GameSystemCommonParam` base IDs:

- combat  = `20000100 + N_combat`  (N 0–20), driven by Scadutree Fragment grants (goods `2010000`)
- summon  = `20000200 + N_summon`  (N 0–10), driven by Revered Spirit Ash grants (goods `2010100`)
- Torrent = `20000300 + N_summon`  (same summon level)

Cost curves (cumulative grants to REACH each level), transcribed/validated in the in-base spec:

```
combat (0..20): 0 1 3 5 7 9 11 13 15 17 20 23 26 29 32 35 38 41 44 47 50
summon (0..10): 0 1 2 3 5 7 10 13 16 20 25
```

Mapping is the inverse: `N = max level s.t. cumulative[level] <= grants_received`. Implement as a
threshold array + linear scan (same as in-base). Under P2 the client converts grant-count → N and
writes N to the stored field; under P1 it converts and pokes the speffect directly.

## Pool injection — base-game seeds have NO fragments natively

Scadutree Fragments / Revered Spirit Ashes are DLC items; a base-game (non-DLC) seed contains
zero of them. So `global_scadutree_blessing != off` must **inject** fragments into the pool as
added/replacement items (apworld fill change, mirroring [[er-filler-replacement]] /
[[er-scadu-frontload]] mechanics). Knobs:

- `global_scadu_count` — how many combat fragments to inject (cap the *reachable* level; 50 = full
  level-20 curve, fewer = a lower ceiling). Count by fragment VALUE (x2 fragment = 2, one slot).
- whether to also inject Revered Spirit Ashes (summon/Torrent tracks) or run combat-only.
- distribution: reuse `scadu_frontload`'s early/uniform bias so the global curve can ramp fast or
  stay "sicko". For `scaled` mode the distribution should roughly track the enemy-scaling curve so
  the player's power and the enemies' power rise together.
- classification: force `useful` (never `progression`) after create_item so fragments never gate
  fill. Count-neutral injection (swap filler) keeps pool size stable — same pattern as the
  filler-replacement / furnace-pot work.

In a `dlc_only` (or DLC-enabled) seed the fragments already exist in the pool; injection must NOT
double-add. Detect and either no-op the injection or just adjust counts.

## Enemy-scaling design (the `scaled` mode meat)

### The key insight — "DLC-elevation" (C3, RECOMMENDED) (Alaric, 2026-06-20)

Don't hand-tune a bespoke counterweight. Instead **assume the gap between base-game endgame scaling
(Haligtree / Mohgwyn) and DLC scaling IS the Scadutree blessing budget** — which is literally how
FromSoft balanced the DLC: the player arrives with full base-game power and the blessing is the extra
budget that makes the DLC's elevated enemies fightable. So:

1. **Lift the base game up to DLC-comparable elevation** so base endgame sits where the DLC sits.
2. **Apply global blessing on top** as the player's budget — and inherit the DLC's *own* enemy↔blessing
   calibration wholesale instead of inventing one.

This is strictly smarter than the earlier C1 (tune blessing to offset completion-scaling by hand) and
C2 (per-region DLC-zone mapping): it reuses a calibration FromSoft already shipped and the baker
already has wired in.

### Why the baker makes this nearly free (research 2026-06-20, `ScalingEffects.cs`)

The randomizer's enemy scaling is a **single unified 35-tier ladder**, and the DLC tiers are already
grafted onto the top of it:

- Base game = tiers 1–20, SpEffect `7000 + 10·i`. Tier 20 (Malenia-class) `maxHpRate` ≈ **7.42**.
- DLC SOTE area scaling = SpEffect `20007000 + 10·i` → tiers **21–35**, `maxHpRate` **7.84 … 16.64**.
- **`20007000` (DLC Gravesite, the first DLC zone) exactly equals base tier 17.** The DLC curve is
  grafted at tier 17 and climbs to tier 35 (~2.2× base endgame HP).

So "bring base endgame up to DLC elevation" is not new scaling code — it's **pushing
completion_scaling's tier ceiling up into the existing DLC band**. Concretely: instead of mapping base
regions across tiers ~1–20, map them across (roughly) tiers ~5–35 with a high ceiling, so the deepest
base regions land in the DLC tier band (21–35) and *are* DLC-comparable. The per-tier rates at those
tiers are the real DLC area-scaling rates already, so the blessing — built against exactly those
rates — is the correct budget by construction. The completion_scaling **steep** curve (concave, climbs
fast; `option_steep = 3`) still shapes the within-run ramp; we're shifting the whole band upward, not
changing its shape. The **floor** knob (`completion_scaling_floor`, % of MaxTier) keeps early Limgrave
low so a fresh, blessing-0, low-upgrade character isn't one-shot at the start — exactly the same
early-game protection the `dlc_only` addendum needed.

The design hypothesis to playtest: `DLC_enemy_tier − base_endgame_tier ≈ blessing_budget`. The numbers
are at least plausible — ~15 tiers of DLC headroom (20→35) against 20 blessing levels (~2.05× out /
~0.49× in at L20). Whether it nets out across a full run is a feel question, not a theory one.

### Default for `scaled` (Alaric's call): **sphere basis + steep + blessing on top**

`completion_scaling_basis = sphere`, `completion_scaling = steep`, ceiling lifted into the DLC band,
global blessing ramping alongside. Alaric runs sphere-gentle today and likes it; the working
hypothesis is that **steep + the lifted ceiling + blessing** is the right shape for a DLC-elevated
base game. Expose the curve/ceiling so it stays tunable; this default is the playtest starting point,
not a fixed truth.

Note this is **additive** to enemy-rando difficulty and NG+ — `scaled` requires `enemy_rando` on
(completion_scaling already does) and must not double-scale.

(C2 — per-region transplant of `20007000+` onto specific base regions — is now redundant: C3 gets DLC
rates via the existing tier ladder without maintaining a base-region→zone map. Keep C2 only as a note.)

## Options summary (proposed)

- `global_scadutree_blessing`: off | player_only | scaled  (default off)
  - `player_only` = blessing globally, enemies untouched (power fantasy / accessibility).
  - `scaled` = C3 DLC-elevation: lift completion_scaling ceiling into the DLC tier band + blessing.
- `global_scadu_count`: Range, **combat** fragments to inject (default e.g. 30; 50 = full L20).
- `global_scadu_distribution`: early | uniform (reuse `scadu_frontload` semantics; for `scaled`,
  bias so blessing ramps roughly with the enemy ceiling).
- `global_scadu_ceiling`: (`scaled` only) how high to push the completion_scaling tier ceiling into
  the DLC band — i.e. how DLC-elevated base endgame gets. Pairs with `completion_scaling` /
  `_floor` / `_basis`.
- `global_scadu_cap`: **tier-aware** clamp (Alaric's call) — cap effective blessing N to the region's
  completion-scaling tier so a late stash can't faceroll an early (low-tier) region. Flat-clamp
  rejected. Implementation: client reads the region's tier (it already consumes the completion-scaling
  tier table / `ER_SPHERE_TIERS.txt` machinery) and clamps `N ≤ f(tier)`.
- **No** Revered Spirit Ash / summon-Torrent option in v1 — Alaric plays summons off, so v1 is
  **combat-track only** (`20000100+N`). Summon/Torrent tracks are a later add if wanted.

## Phasing / work items

1. **P1 + `player_only`, client-only. — DRAFTED 2026-06-20 (default off), needs Windows build+test.**
   `patch_apworld_global_scadu_blessing.py` adds the `global_scadutree_blessing` option
   (off/player_only/scaled, default off) + slot_data emission. `patch_client_global_scadu_blessing.py`
   ticks the feature in the in-world poll: counts held Scadutree Fragments (goods 2010000 stack qty),
   maps to a combat level via the cost curve, and **writes the stored byte `pgd+0xFC`** (the P2′
   mechanism — chosen over a raw SpEffect poke since the offset is known and byte-write survives map
   loads). Safety: only ever RAISES the level (never stomps a real DLC revere / never down-flickers);
   reuses the auto_upgrade inventory walk + in-world settle gate. CAVEAT: it reads HELD fragments, so
   a pure no-DLC base seed (no fragments in pool) won't ramp until fragment **pool injection** is added
   — for now validate on a DLC-enabled seed where fragments exist, or add injection next. No bake.
2. **P2′ — stored-level write on grace rest (the one RE task).** Find the stored combat-blessing
   offset (client already has the `GameDataMan → PlayerGameData` chain), write `curve(grant_count)`
   on grace rest; engine then re-applies natively across loads/death/NG+. Replaces the P1 watchdog
   and delivers the "level at a grace" feel. Highest-value item; everything else is known.
3. **`scaled` mode = C3 DLC-elevation.** Push `completion_scaling` ceiling into the DLC tier band
   (21–35) so base endgame is DLC-comparable; default sphere + steep; blessing rides on top with the
   native DLC calibration. Add the tier-aware `global_scadu_cap`. Ship as the "DLC-elevated base game"
   preset.
4. **Tune + validate (playtest).** Confirm the `DLC_tier − base_endgame ≈ blessing` hypothesis holds
   across a run; adjust ceiling / curve / fragment count + distribution to taste.
5. **Test matrix:** blessing ramps with grants in base game; buff persists across fast-travel / death
   / NG+ (P2′); damage numbers shift as designed; early Limgrave stays survivable at blessing 0 (floor
   working); deepest base regions feel DLC-tier; tier-aware cap prevents early-region faceroll; no fill
   dependence on fragments; no double-apply in `dlc_only`.

## Interactions & edge cases

- **`dlc_only` / DLC-enabled seeds:** vanilla revering works and the stored level is real, so the
  global feature is redundant there and must not double-apply — no fragment double-injection, and pick
  ONE source of truth for the level (prefer the AP grant curve; don't let manual revering outrun it).
- **In-base arena feature ([[er-scadu-in-base]]):** if global blessing is on, the arena-scoped apply
  is moot (blessing is already global). Make the two mutually aware so they don't stack.
- **`early_leveling` / rune-level systems:** global blessing is an *additional* power axis; combining
  both can overshoot. The C3 model already assumes normal base-game RL/upgrade progression underneath
  (that's the point — DLC balance assumes full base power + blessing), so don't also nerf RL.
- **NG+:** P2′ (native stored level) handles NG+ for free; the P1 fallback must re-apply after the NG+
  transition. C3 enemy scaling already has NG+ variants in the tier ladder.
- **Early-game floor is load-bearing:** because C3 lifts the ceiling, the `completion_scaling_floor`
  must keep sphere-1 regions low or a fresh character is one-shot before any fragments land. Pair the
  early fragment distribution with a sane floor.
- **Status/poise:** the player blessing speffect is damage-correction only (out/in multipliers); it
  does not offset the enemy ×2.5 status or poise scaling, so `scaled` can still feel statusy at depth —
  note it, don't try to "fix" it in v1.

## Open questions (post-2026-06-20 research; most resolved)

- **RESOLVED — cap:** tier-aware, clamped to the region's completion-scaling tier (Alaric).
- **RESOLVED — tracks:** combat-only for v1; summons off in Alaric's runs (Alaric).
- **RESOLVED — `scaled` default:** sphere basis + steep + lifted ceiling + blessing (Alaric;
  playtest starting point).
- **RESOLVED — enemy model:** C3 DLC-elevation via the existing 35-tier ladder, not bespoke C1/C2.
- **RESOLVED — P2′ field offset.** `pgd + 0xFC` (combat, signed byte), `pgd + 0xFD` (revered), from
  `GameDataMan → +0x08 → +0xFC/FD` (Hexinton/TGA CE table). Down to a 5-min Windows confirm + the
  `pgd`-base reconciliation noted in P2.
- **OPEN (playtest) — ceiling height + curve.** How far to push the tier ceiling (top out at 35? lower?)
  and whether steep is right once the ceiling is lifted; does the `DLC_tier − base_endgame ≈ blessing`
  hypothesis actually net out. Feel, not theory.
- **OPEN — fragment count vs ceiling.** `global_scadu_count` (and its distribution) must let blessing
  ramp roughly in step with the lifted enemy ceiling; tune together.
