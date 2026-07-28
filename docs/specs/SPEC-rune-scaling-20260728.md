# SPEC — make rune yield track enemy scaling

**Status:** root cause MEASURED and the reported number located EXACTLY. **Two levers, not one** -- see §6, which SUPERSEDES §2-§5's single-lever reading. One design call outstanding and it is
Alaric's. Written 2026-07-28 from a player report; §6 added the same day after exhausting the
static sources.

> **ShadowTL, Nexus, 2026-07-28:** *"Is it also possible to adjust the amount of runes that you get
> from enemies so that it fit the scaling. Its a bit odd that u get 120.000 runes from Adula when
> Liurnia is your first region."*

---

## 1. Root cause — measured, not inferred

Runtime enemy scaling works by applying one of vanilla's own progressive scaling SpEffects,
`7010..7200`, to each loaded enemy (`eldenring-archipelago/src/scaling.rs`). Reading those 20 rows
out of `SpEffectParam.csv` (now in `gen_inputs.db`, so this is checkable in the sandbox):

| rung | maxHpRate | physicsAttackPowerRate | **soulRate** | **haveSoulRate** |
|---|---|---|---|---|
| 7010 | 1.141 | 1.097 | **1** | **1** |
| 7100 | 3.703 | ~3.0 | **1** | **1** |
| 7200 | 7.422 | 3.796 | **1** | **1** |

**Every rung leaves both rune fields at exactly 1.** The ladder scales HP, stamina and damage and
has never touched rune yield. That is the whole defect — nothing is overriding rune values, they are
simply never in scope.

## 2. Which field for ORDINARY ENEMIES — `haveSoulRate`

🛑 This section is right about trash mobs and WRONG about the reported case. Bosses do not pay
from this field at all — §6.

Both candidate columns exist, and they are not interchangeable:

- **`soulRate`** is PLAYER-side (the rate at which *you* gain runes). Evidence: only 27 rows differ
  from 1, and row `3971` is **1.3** — the Gold-Pickled Fowl Foot's +30%. This is the wrong field;
  writing it would boost every rune gain in the run.
- **`haveSoulRate`** is ENEMY-side (how many runes the enemy *carries*). Evidence: 124 rows differ
  from 1, and they cluster in `7400..7600` — vanilla's **NG+ ladder**, which raises HP and rune yield
  *together*.

## 3. Vanilla already answers "how many runes is right for this much HP"

`7400..7600` pairs the two directly, so the mapping does not have to be invented:

| vanilla HP multiplier | vanilla haveSoulRate |
|---|---|
| 1.00 – 1.26 | 2 |
| 1.25 – 1.52 | 3 |
| 1.85 – 2.15 | 4 |
| 2.36 – 3.43 | 5 |

Applied to our ladder (`tools`-checkable, recompute before trusting):

| our rung | maxHpRate | vanilla-implied haveSoulRate |
|---|---|---|
| 7010 | 1.141 | 2 |
| 7030 | 1.656 | 3 |
| 7050 | 1.953 | 4 |
| 7070 | 2.406 | 5 |
| 7100 | 3.703 | 5 (saturated) |
| 7200 | 7.422 | 5 (saturated) |

🛑 **Our ladder outruns vanilla's.** Vanilla tops out at 3.43x HP; ours reaches 7.42x. So the
vanilla-implied mapping SATURATES at 5x for our top twelve rungs — half the ladder gets the same
rune rate. Extrapolating past vanilla's own top is an invention, and inventing past a measured
ceiling is what [`er-scaling-floor-units`] already cost us once.

## 4. 🛑 THE DESIGN CALL — and the report is asking for the OPPOSITE of §3

This is the part to decide before anyone writes code, because §3 solves a different problem than the
one reported.

Our scaling only ever scales enemies **UP** (tier 0 = no effect). Adula is a vanilla LATE-game boss
with a huge vanilla rune payout. Met in a first-region Liurnia she sits at a LOW tier — so she is
barely scaled, and still pays her vanilla 120,000.

So there are two different features here:

**(A) Rune yield rises with the tier.** The §3 mapping. Makes late/high-tier regions pay more.
Does **not** fix the report: a low-tier Adula still pays 120k, only now a high-tier trash mob pays
more too.

**(B) Rune yield is NORMALISED to the region's tier.** What "fit the scaling" actually means: an
enemy's payout is pulled toward what the *region* is worth, so a vanilla-late boss met early pays
early-game runes. This needs `haveSoulRate` **below 1** — vanilla only ships values ≥ 1, but the
field is a float, so 0.2 is writable. It is the honest fix for the complaint and the bigger balance
change.

**They compose** — (B) with a floor of 1.0 and (A) above it is one curve — but (B) is the one that
was asked for, and it is a real difficulty/economy change, so it is Alaric's call, not a derivation.

## 5. Implementation, once the curve is chosen

Small, and on a trodden path:

- **Client already rewrites param rows at runtime** via `SoloParamRepository::instance_mut()` —
  `check_lots.rs` and `enemy_drops.rs` both do it. Writing `haveSoulRate` on 20 `SpEffectParam` rows
  at connect is the same shape.
- **The curve lives in `er-logic`** (host-tested, builds on any host) next to `scaling.rs`'s existing
  tier logic; `eldenring-archipelago` only calls it. Same split as `tracker_tables`, and for the same
  reason: `eldenring-archipelago` does not build off Windows.
- **World side is one option** (`rune_scaling`), defaulting OFF per CONTRIBUTING's "new options
  default to vanilla / no-change", plus its `options` echo. No new slot_data shape needed if the
  client derives the rate from the tier it already has.

### Risks to state plainly
1. **Rewriting vanilla rows `7010..7200` changes them for everything that uses them**, not just our
   sweep. Confirm nothing else in a live game applies these before shipping.
2. `haveSoulRate` is believed enemy-carried-runes from param evidence and NG+ correlation, **not from
   an in-game probe.** Before it ships, one live check: apply a known rate to a known enemy and read
   the payout. This is exactly the "live-game oracle" split — file truth is mine, game truth is
   Alaric's.
3. Rune economy touches the early-game knife edge ([`gf-early-economy-floor-knife-edge`]). Any change
   here wants the same-seed A/B probe that memory already prescribes.

---

## 6. ⭐ CORRECTION — boss runes are a DIFFERENT table, and the reported number is in it

Everything above concerns `NpcParam.getSoul`, which `haveSoulRate` multiplies. **Bosses do not use
it.** Measured:

- **315 `NpcParam` rows carry `isSoulGetByBoss` with `getSoul = 0`.** A boss's runes are paid by the
  boss-reward path, not by the carried-runes field.
- The largest `getSoul` in the entire param is **50,000** — no enemy row can pay 120,000.

Boss runes live in **`GameAreaParam`**, keyed by BOSS ENTITY ID, in `bonusSoul_single` /
`bonusSoul_multi`. 216 rows — the same 216 boss arenas `game_areas.tsv` already knows.

**The reported number is there, exactly:**

| entity id | greenfield's name for it | bonusSoul_single |
|---|---|---|
| `1034420800` | **Glintstone Dragon Adula** | **120000** |
| `1034500800` | Glintstone Dragon Adula (2nd) | 12000 |

Not a coincidental match — the join is general. 195 of the 244 ids in `boss_healthbars.py` resolve
to a `GameAreaParam` row, and the values read exactly as you would expect: Elden Beast 500,000,
Radahn (Consort) 500,000, Bayle 490,000, Malenia 480,000, Mohg 420,000, Godfrey 300,000.
(The 49 non-joining ids want a look before anyone relies on totality — likely shared arenas and
multi-phase entries.)

### What this changes

**There are two levers and they cover disjoint populations:**

| population | lever | reaches the report? |
|---|---|---|
| ordinary enemies | `haveSoulRate` on the applied `70xx` scaling SpEffect (multiplies `getSoul`) | no |
| **bosses** | **`GameAreaParam.bonusSoul_single` / `_multi`, per entity id** | **yes — this is Adula's 120,000** |

So a `haveSoulRate`-only implementation would ship, log green, and leave the exact complaint that
prompted it untouched. Worth stating plainly because it is the shape of bug this repo keeps
catching: the fix works, on a population nobody was complaining about.

### Why the boss lever is the easier one

- It is keyed by **entity id**, which the client already handles (`boss_felled`, the sweep payout).
- It is a **direct value**, not a multiplier — so "what should this boss pay in a tier-2 region" is
  expressible without inventing a curve, and it can go DOWN, which is what normalising an
  early-met late-game boss actually requires (§4's option B).
- Same param-rewrite path as everything else (`SoloParamRepository::instance_mut`).

### Static sources now exhausted

Nothing above needed an in-game probe, and the two claims that would have are settled from data:
`soulRate` is player-side (Gold Scarab, +20% runes, is `soulRate` 1.2), and the `74xx` family is
vanilla's NG+ enemy scaling (`NpcParam.GameClearSpEffectID` references all 21 rows — "GameClear",
applied per-NPC, HP and rune yield raised together). The DLC equivalent is the `20007xxx` ladder,
which appears in the same column.

**The one thing left for the live oracle** is no longer a discovery but a confirmation: that
rewriting `bonusSoul_single` at runtime actually changes the payout, and whether it must be written
before the arena loads. That is a shipping check, not a question about where the number lives.

---

## 7. Branch

The build lands on **`feat/rune-scaling`**, not main (Alaric, 2026-07-28: "split the rune scaling
onto its own branch and ship the rest").

Nothing rune-related has ever been on main except this spec and the playtest sheet — no option, no
slot_data key, no client code — so v0.2.15 ships unaffected by whatever happens here. The branch
exists so the *implementation* has a home while the §4 design call is open, and so a half-built
curve can never ride along in a release.

**Before writing code, in this order:**
1. Alaric's §4 call — scale UP with tier, or NORMALISE toward it. The report wants the second.
2. The `PLAYTEST-rune-scaling-20260728.md` §2 confirmations (Adula 12,000 / 120,000). If those do
   not match, §6's model is wrong and none of the implementation notes survive.
3. Only then §5 — and put the curve in `er-logic`, host-tested, with `eldenring-archipelago` as
   thin wiring. `eldenring-archipelago` does not build off Windows; a curve written there is
   unverifiable until CI.

Rebase on main before starting: this branch was cut at `da1f7cb` (v0.2.15).
