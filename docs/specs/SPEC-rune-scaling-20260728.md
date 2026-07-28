# SPEC — make rune yield track enemy scaling

**Status:** root cause MEASURED, implementation path clear, **one design call outstanding and it is
Alaric's.** Written 2026-07-28 from a player report.

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

## 2. Which field — `haveSoulRate`, and the data says so

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
