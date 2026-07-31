# IMPL sketch — Global Scadutree Blessing

**Date:** 2026-07-29 · **Reads with:** `SPEC-global-scadutree-blessing-20260729.md` (design +
decisions) and `RECON-scadutree-blessing-speffect-20260729.md` (the param facts)

Everything here rests on facts measured in-game 2026-07-29, not inference:

- ladder = `20000100 + level`, stride 1, levels 0..20, one scalar, `cut = 1/attack` exactly
- every rung has `effectEndurance = 0.05` and is **refreshed per-tick by a loop that only runs in the
  Land of Shadow**. Nothing strips anything.
- a rung with `effectEndurance = -1`, applied in Limgrave, **persists and halves damage taken**

So the feature is: *clone a rung onto our own row, make it permanent, apply it.* The rest is
plumbing.

---

## Phase 0 — compile probe. Do this first, it is 20 minutes and it de-risks everything else.

Three APIs this design needs have **never been called in this repo**. Do not write Phase 1 against
guessed names (`er-crate-param-naming`: ask, don't guess).

```rust
// throwaway - does it compile, and what are the real names?
let repo = SoloParamRepository::instance()?;                       // shape already used in params.rs
let cfg  = repo.get::<GameSystemCommonParam>(0)?;                  // ?? type name unverified
let base = cfg.base_scadu_blessing_sp_effect_id();                 // ?? accessor unverified
let row  = repo.get_mut::<SpEffectParam>(20000100u32)?;            // shape IS used (no_equip_load.rs:61)
let _    = row.atk_enemy_dmg_correct_rate_physics();               // ?? 18 accessor names unverified
let _    = row.effect_endurance();                                 // ??
```

What you need out of it: the exact type for `GAME_SYSTEM_COMMON_PARAM_ST`'s table, and the exact
snake_case accessor names for the 18 rate fields + `effect_endurance`. Write them down; Phase 1 is
mechanical once you have them.

If the generated bindings *don't* expose these fields, fall back to raw offsets — we know
`effectEndurance` is a float at row `+0x8` (`iconId` 0x0, `conditionHp` 0x4, `motionInterval` 0xC),
and the rate offsets can be read out of `param_headers/param_columns.tsv` ordinals. Prefer named
accessors; the offsets are the escape hatch, not the plan.

## Phase 0b — pick the clone row, and give the safe set a home

`20012080` (no_equip_load) and `20010827` (no_fall_damage) are taken. The "vetted safe set" they cite
**does not exist as a list anywhere** — it is prose in two module docstrings. Before taking a third
row, create `crates/eldenring-archipelago/src/safe_speffect_rows.rs`:

```rust
//! Vanilla SpEffectParam rows we repurpose. A row here is: no-op in vanilla (every field at its
//! neutral value), silent (no vfx/icon), and claimed by exactly ONE feature.
pub const NO_EQUIP_LOAD:  i32 = 20012080;
pub const NO_FALL_DAMAGE: i32 = 20010827;
pub const SCADU_BLESSING: i32 = 200128xx;   // <- pick, then PROVE no-op (below)
```

Proving a candidate is no-op, without a game: `tools/probe_scadu_blessing.py --show <id>` already
dumps absolute fields; extend `--show-fields` to the full column list and confirm every field is at
its neutral value. Do this rather than trusting that a nearby id is spare.

## Phase 1 — client: the blessing itself

New `crates/eldenring-archipelago/src/scadu_blessing.rs`, structurally a copy of `no_equip_load.rs`.

```
tick():
  if mode == 0 -> return
  if !flags::in_world() -> return
  throttle (~1s, reuse the SCADU_LAST_TICK pattern)

  target = er_logic::upgrades::blessing_target(mode, held_frags, floor)   // existing
  target = target.min(cap)                                                // new: scaduBlessingCap

  // 1. keep our clone row in sync with the target level
  if target != last_written_level {
      src   = repo.get::<SpEffectParam>(base + target)     // base from GameSystemCommonParam
      dst   = repo.get_mut::<SpEffectParam>(SCADU_BLESSING)
      copy the 18 rate fields src -> dst
      dst.set_effect_endurance(-1.0)                       // THE load-bearing line
      // do NOT copy stateInfo; leave dst at 0
      last_written_level = target
  }

  // 2. keep it applied
  DEATH GUARD: if player.chr_ins.modules.data.hp <= 0 { return }
  if !chr.special_effect.entries().any(|e| e.param_id == SCADU_BLESSING) {
      chr.apply_speffect(SCADU_BLESSING, false);
  }
```

Two properties worth being explicit about:

**Level changes need no re-apply.** The row is already applied and permanent; rewriting its fields
changes the live effect. That is exactly how `no_equip_load` mutates `allItemWeightChangeRate` under
an already-applied row. So a level-up is 18 float writes and nothing else.

**The death guard is not optional.** `no_equip_load.rs:78-83` — `chr_ins` and its `special_effect`
list tear down at the death-cam and iterating there CTDs. Copy the block verbatim.

## Phase 2 — DLC composition (the ratio)

In a DLC seed the engine is refreshing a real rung every tick. Our clone must supply only the
*difference*, or the player double-dips.

```
k = the vanilla rung currently active, if any:
    chr.special_effect.entries().find(|e| (base..=base+20).contains(&e.param_id))
      .map(|e| e.param_id - base).unwrap_or(0)

attack_clone = A(t) / A(k)
cut_clone    = A(k) / A(t)          // == 1 / attack_clone, by the ladder's own identity
```

with `A(n)` read from row `base + n` rather than any table we carry. `k = 0` gives the full `A(t)`,
so **one code path covers base game and DLC** and the spec's double-dip rule (§3.4) reduces to this
formula. Put the arithmetic in `er-logic` as a pure fn over two floats so CI can test it:

```rust
// er-logic/src/upgrades.rs
pub fn clone_rates(a_target: f32, a_active: f32) -> (f32, f32)
```

Edge cases that must be tested directly, not assumed reachable from a corpus
(`guard-absent-from-corpus-needs-a-direct-call`): `a_active == 0.0`, `a_active > a_target` (player's
real blessing already exceeds our target → clone must be 1.0/1.0, never <1), NaN.

## Phase 3 — world side

1. **Option help text** — delete the "DLC-area-gated by the engine, so NONE of these modes touch
   base-game balance" sentence. After this change it is false by design.
2. **`scaduBlessingCap`** (INT, emitted when mode != 0) — new contract key. Additive + contains-guarded.
3. **Fragment injection** for seeds with no DLC region: count **fragments granted**, not checks
   placed (some lots grant >1 — Alaric, 2026-07-29). Gate on `displaceable_filler` having something
   to give up; if not, fail at options-validation naming both options.
4. **Retire the legacy top-level key** — 3 files: `contract.py:708`, `contract_gen.rs:86`,
   `slot_data_fixture.json:5246`.
5. **Unfreezing is a 4-site edit** — `defaults.py:119`, the class `default`, module-level fallbacks,
   and `wizard/options-metadata.json` (absent today *because* the freeze removes it from `GFOptions`).

## Tests

| Tier | What |
|---|---|
| pure / er-logic | `clone_rates` incl. the three edge cases above; `blessing_target` extended with the cap term |
| replay | third `Policy` in `scadu_blessing_replay.rs`: timeline where the player reveres for real mid-run — pre-fix double-counts |
| pure / world | injection counts fragments granted not checks placed; no-DLC seed at mode 1 reaches the cap; DLC seed injects none |
| contract | `scaduBlessingCap` emitted iff mode != 0; legacy key gone from all 3 files |
| options validation | mode != 0 with no displaceable filler raises naming both options |
| direct-call | death guard; "row absent from SpEffectParam"; `a_active > a_target` |

## Order, and where it can go wrong

Phase 0 → 0b → 1 → **playtest** → 2 → **playtest** → 3.

Phase 1 alone is shippable and testable in a base-game seed: that is the motivating case, so it is
the acceptance test (Rule 11). Do not build Phase 2 before Phase 1 is confirmed in-game — the ratio
logic is only meaningful once the simple case is known good.

Risks, in the order I'd worry about them:

- 🟠 **CTD budget.** We already have an open CTD on the boss-sweep payout path. This adds a second
  per-tick speffect-list walk. Gate everything on `mode != 0` so `off` seeds carry zero new game
  access, and land it separately from any other client change so a new crash has one suspect.
- 🛑 **Do not patch the vanilla rung in place.** Setting `-1` on `20000100+N` works — it is how A2b
  was measured — but inside the DLC the engine still re-applies that row every tick, and permanent
  under per-tick-reapply is untested (refresh vs stack). Cloning leaves the vanilla path untouched.
- **Early-economy floor is one seed thick.** Injecting forced-`useful` fragments displaces filler.
  Baseline the fill gate against pristine main before and after.
- **`atkEnemyDmgCorrectRate` (damage dealt) is still unmeasured** — only the defence half was
  confirmed in-game. Same row, so a split would be surprising, but confirm it during the Phase 1
  playtest rather than shipping on the assumption.

## Still Alaric's call (SPEC §9)

1. Is `player_only` allowed to make base seeds easier at all, or does it fold into `scaled`?
2. Injection budget — cap 20 (`SCADU_CUM[20] = 50`) or cap 12 (`= 26`)?
3. Does `scaled` ship without the C3 base-game enemy lift? Without it, `scaled` == `player_only`
   outside the DLC — the exact "mode 2 is an alias of mode 1" bug the replay harness exists to catch.
