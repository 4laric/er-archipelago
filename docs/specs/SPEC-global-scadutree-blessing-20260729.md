# SPEC — Global Scadutree Blessing

**Date:** 2026-07-29 · **Status:** DRAFT, needs Alaric's call on §9 · **Supersedes:** the 2026-06-20
root-level `SPEC-global-scadutree-blessing.md` (no longer in the tree)
**Depends on:** `docs/specs/RECON-scadutree-blessing-speffect-20260729.md` (the ladder is
`20000100 + level`, stride 1, one scalar, `cut = 1/attack` exactly)

---

## 1. The problem this spec exists to fix

`global_scadutree_blessing` ships today. Its own option help says:

> "The stored blessing byte is **DLC-area-gated by the engine**, so NONE of these modes touch
> base-game balance."
> — `greenfield/eldenring/features/scaling.py`, `GlobalScadutreeBlessing`

That sentence is the whole feature's load-bearing assumption, and **nobody has ever verified it.**
It is asserted in shipped user-facing help text. Two ways it can be wrong, and they fail in opposite
directions:

- **If it is TRUE:** the option named "global" is structurally incapable of being global. Both live
  modes are DLC-scoped conveniences. There is no global blessing and never was.
- **If it is FALSE:** every seed that has ever set `player_only` or `scaled` has been silently
  buffing the player across the base game, and the option help told the user it wouldn't.

The recon settles the param half: the blessing rows carry **nothing spatial** — 19 fields, all rate
multipliers plus one category tag (`stateInfo = 472`). So the gate, if it exists, lives in whatever
*decides to apply* the row, not in the row. That is why the current design can't reach past it, and
what this spec changes.

**Scope of this spec:** make the blessing a genuine game-wide power axis that works in a base-game
seed with no DLC installed, without breaking the DLC behaviour that already ships.

## 2. What actually ships today (verified, not remembered)

| Piece | Where | State |
|---|---|---|
| Option `GlobalScadutreeBlessing` (0 off / 1 player_only / 2 scaled) | `features/scaling.py` | `default = 0` |
| Frozen OFF in the v0.2 option slim | `defaults.py:119` | no default seed sets it |
| `options.global_scadutree_blessing` INT, required | `contract.py:366`, `core.py:832` | live |
| Legacy top-level duplicate `global_scadutree_blessing` | `contract.py:708` | live, redundant |
| `dlcScadutreeFloorRanges` TRIPLE_LIST | `contract.py:443` | emitted **only** when mode == 2 |
| `DLC_BLESSING_FLOORS` (13 regions, 1–15) | `features/scaling.py:202` | live, playtest-feel values |
| `tick_global_scadu()` — counts held frags → raises `pgd.scadutree_blessing` | `upgrades.rs:314` | live, 1s throttle, raise-only, `in_world()` gated |
| `blessing_target(mode, frags, floor)` + replay harness | `er-logic/upgrades.rs`, `scadu_blessing_replay.rs` | host-tested |

Three defects in the current state, all worth naming before designing on top:

1. **The power source doesn't exist in a base-game seed.** `held_scadu_fragments()` counts goods
   `2010000`. Scadutree Fragments are ~50 DLC checks (`data.py`); a no-DLC seed contains zero. The
   feature is a no-op there *regardless* of the map-gate question.
2. **`scadu_blessing_replay.rs` header is stale.** It says "The option now ships at its declared
   default (2 = scaled), so this decision is LIVE for every DLC seed." It does not — `default = 0`
   and `defaults.py` freezes it. The floor path it exists to protect is still dead code in practice.
3. **Lever A mutates a save-persisted field.** `pgd.scadutree_blessing` is written into the save. An
   AP run permanently raises that character's blessing even after the client is uninstalled. That is
   a save-integrity cost the current design pays silently.

Two smaller drifts to sweep while in here, both found by the verification pass:

- `upgrades.rs:297-300` — the doc comment "Cumulative Scadutree Fragments required to REACH each
  combat-blessing level… Verbatim from C++ `kScaduCum`" is now attached to `const SCADU_MAX_LEVEL`.
  The array it describes moved to `er-logic/upgrades.rs:78`. Stale doc on a constant this spec touches.
- `er-logic/upgrades.rs:124` defines `raise_stored_blessing(hook, level)` and
  `eldenring-archipelago/upgrades.rs:406` defines a different `raise_stored_blessing`. Two functions,
  one name, two crates — name the new applier so it doesn't add a third.

## 3. Design

Keep the three-mode shape — it already encodes the right fork (convenience vs rebalance). Change
what each mode *means* and how it is delivered.

| Mode | Meaning after this spec |
|---|---|
| `off` | Vanilla. Nothing applied, nothing injected, no contract keys beyond the echo. |
| `player_only` | The blessing is a **game-wide** power curve driven by AP progress. Player-side only — enemies untouched. Explicitly a power fantasy; says so in the help text. |
| `scaled` | `player_only` **plus** the enemy-side counterweight: the DLC region floor that exists today, and (later) the C3 lift of base-game enemies. Net difficulty roughly neutral. |

### 3.1 Applier — Lever B, not Lever A

Stop writing the stored byte as the primary mechanism. Apply the SpEffect ourselves:

```rust
// repo: SoloParamRepository. The generic is the TABLE type; the result is the ROW struct --
// same shape as params.rs:19 `repo.get::<EquipParamGoods>(id) -> &EQUIP_PARAM_GOODS_ST`.
let cfg: &GAME_SYSTEM_COMMON_PARAM_ST = repo.get::<GameSystemCommonParam>(0)?;
let base = cfg.base_scadu_blessing_sp_effect_id();
let want = base + level;                    // stride 1, levels 0..=20
// remove any other rung we previously applied, then apply the one we want
for e in chr.special_effect.entries() { /* collect ours in base..=base+20, != want */ }
chr.apply_speffect(want, false);
```

🛑 **First use of an unproven API.** Neither `GameSystemCommonParam` / `GAME_SYSTEM_COMMON_PARAM_ST`
nor `base_scadu_blessing_sp_effect_id()` is called anywhere in this repo today — they come from
`eldenring 0.14`'s docs, not from working code here. The exact type name, generic shape and return
type must be confirmed against a real build before this snippet is treated as anything but intent
(`er-crate-param-naming`: ask, don't guess). Step 1 of implementation is a one-line compile of the
`repo.get` call, nothing else.

Why this and not the byte:

- **Map-agnostic by construction.** If the gate is in the applier, we *are* the applier.
- **Non-persistent.** Nothing is written to the save. Uninstall the client and the character is
  exactly as it was — fixes defect 3.
- **Exact.** We choose the rung; we don't hope the engine re-derives it.
- Already-proven idiom: `no_equip_load.rs:85-91`, `no_fall_damage.rs:87-89`.

🛑 **Death guard is mandatory.** `no_equip_load.rs:78-83` (comment 78-80, guard 81-83): `chr_ins` and
its `special_effect` list tear down at the death-cam transition, and iterating or mutating them there
**CTDs**. Gate on `player.chr_ins.modules.data.hp > 0`. Copy the whole block verbatim —
`no_equip_load.rs:84-91` and `no_fall_damage.rs:83-90` are the two shipped instances. We already have
an open 🟠 CTD on the boss-sweep payout path; a second unguarded speffect walk makes that one harder
to triage, not easier.

**Lever A is retained for DLC seeds only**, unchanged, so the in-DLC experience stays native (the
menu number, the grace UI, NG+ carry-over). The two must never both raise the same rung — see §3.4.

### 3.1b Lever D — don't use the vanilla row at all. Clone it onto a no-op row.

*(Alaric, 2026-07-29: "even if the engine restricts the actual blessing to DLC, can we fake it with
some other speffect in base-game regions?" Yes — and it is strictly more robust than Lever B.
**Recommended over Lever B.**)*

Take a vetted no-op vanilla `SpEffectParam` row, write the blessing's rate fields into it at runtime,
and apply *that* to the player. This is **the pattern already shipping twice** in this client:
`no_equip_load.rs` repurposes row `20012080` (`allItemWeightChangeRate → 0`), `no_fall_damage.rs`
repurposes `20010827` (`fallDamageRate → 0`). Both already use `repo.get_mut::<SpEffectParam>(id)`.

Copy the 18 rate fields, and **not** `stateInfo`:

```
atkEnemyDmgCorrectRate_{Physics,Magic,Fire,Thunder,Dark}          <- A(N)
atkPlayerDmgCorrectRate_{Physics,Magic,Fire,Thunder,Dark}         <- A(N)
{neutral,slash,blow,thrust,magic,fire,thunder,dark}DamageCutRate  <- 1/A(N)
```

Why this beats Lever B: it is immune to **every** mechanism by which the engine could be scoping the
vanilla blessing, without our needing to know which one is real.

- Strips by `stateInfo == 472`? Our clone leaves `stateInfo` at 0.
- Strips or skips by id range `20000100..=20000120`? Our clone isn't in that range.
- Re-derives from the stored byte on map load? Ours isn't derived from anything.

That means **Lever D does not depend on the answer to A1.** A1 stops being a blocker and becomes a
question about whether we can use the *nicer* path, not whether the feature is possible at all.

**Read the source values at runtime; do not hardcode the curve.**
`repo.get::<SpEffectParam>(20000100 + N)` → copy its 18 fields into the clone. The curve self-updates
across game patches and we never carry a table of FromSoft's numbers.

**Composition with a real DLC blessing is exact — this is what makes Lever D clean.** Because the
ladder is one scalar with `cut = 1/attack`, if the vanilla row for level `k` is already active and we
want effective level `t`, the clone carries the *ratio*:

```
clone attack = A(t) / A(k)          clone cut = A(k) / A(t)
```

`k = 0` (nothing active) gives the full `A(t)`, so **one formula covers base game and DLC** and there
is no double-dip to special-case. Compare Lever A + B, which need a `max` rule plus a "never both
live" invariant (§3.4). Under Lever D, §3.4 collapses to "read `k`, apply the ratio".

Costs and caveats:

- 18 float writes on level *change*, not per tick. Negligible.
- Invisible to the game's own blessing UI — a `player_only` base-game run shows no blessing in any
  menu. Arguably correct for a base seed; it argues for keeping Lever A as the in-DLC path.
- 🛑 The vetted-safe-row set is a **shared resource**. Two rows are spoken for. Whichever row this
  takes must be added to that documented set in the same commit, or the next feature silently
  reuses it and the two fight.
- 🛑 **Do not just set `effectEndurance = -1` on the vanilla rungs and be done.** It works (that is
  how A2/A2b were measured) but inside the DLC the engine still re-applies that row every tick, and
  a permanent effect under a per-tick re-apply is untested — it may refresh harmlessly or it may
  stack. Cloning onto our own row leaves the vanilla refresh path completely untouched, which is the
  entire reason to clone rather than patch in place.

**Clone field set, final:** the 18 rate fields from §2, plus `effectEndurance = -1` (float at row
`+0x8`), and explicitly *not* `stateInfo` (leave 0).
- Determining `k` requires reading the active-speffect list — the same walk Lever B needs, under the
  same death guard. Lever D removes the *dependency* on A1, not the need for the walk.

### 3.2 Power source — fragments stay the currency, and base seeds get fragments

One currency, one curve, both seed types. `player_only`/`scaled` on a seed with no DLC region in
play injects Scadutree Fragments into the filler pool, forced `useful`. Count is derived from the
target cap, not hand-picked: `SCADU_CUM[cap]` fragments (`er-logic/upgrades.rs:78-79`, verified —
`SCADU_CUM[20] = 50`, `SCADU_CUM[12] = 26`), spread across the seed.

Where the injection actually goes: `features/filler_curation.py::displaceable_filler(world, name)`
is a **pure name predicate** (junk consumable ∧ not progression), not machinery — it is the right
*gate* for §4's "is there filler to give up" check and nothing more. The injector belongs alongside
the existing displacement in `features/pool_builder.py:365-378` / `features/filler_budget.py:249-263`.

(Resolved 2026-07-29, Alaric: some lots grant more than one fragment, so the 46 `Scadutree Fragment`
check strings in `data.py` do reach `SCADU_CUM[20] = 50`. Injection for a base seed must therefore
count **fragments granted**, not checks placed — a 1:1 check→fragment injection would land short of
the cap.)

Rejected alternative — a bespoke `Progressive Scadutree Blessing` AP item. It is cleaner on the wire
but it forks the curve (two things that mean "blessing level"), breaks the double-dip rule in §3.4,
and would not stack with real DLC fragments in a mixed seed. Not worth it for a cosmetic win.

### 3.3 Cap

`player_only`: flat cap 20 (`SCADU_MAX_LEVEL`), which is A = 2.05.

`scaled`: **tier-aware.** Clamp the level to the completion-scaling tier of the region the player is
standing in, so the curve can't outrun the enemy lift. Reuses the bucket space
(`play_region_id / 100`) that `dlcScadutreeFloorRanges` and `dlcRegionBuckets` already speak.

### 3.4 The double-dip rule

In a DLC seed both levers can be live: we apply a rung, and the player also reveres for real at a
DLC grace. These must compose as `max`, never as a sum.

- Lever B applies exactly one rung and removes any other rung of ours before applying.
- The effective level is `max(curve(held fragments), region floor, stored blessing)` — the same
  composition `blessing_target` already implements, extended by one term.
- Lever A stays raise-only. It never lowers a blessing the player earned.

This is a timeline, not a tick — fragments arrive, regions change under the player, the bag walk
fails transiently, reconnect re-runs everything. `scadu_blessing_replay.rs` already models exactly
that and is the right place to extend, not to rewrite.

## 4. World side

- `GlobalScadutreeBlessing` help text: **delete the DLC-gate claim**. It is unverified and, after
  this spec, wrong by design. Replace with what each mode does.
- **Unfreezing is a four-site edit, not a one-line delete** (`er-unfreezing-an-option-needs-the-class-default`):
  1. remove from `defaults.FROZEN_OPTIONS` (`defaults.py:119`),
  2. move the class `default` to the frozen value — here they already agree
     (`FROZEN_OPTIONS` = `(0, "off")`, `GlobalScadutreeBlessing.default = 0`), so **verify that and
     pin it with a test** rather than assume it stays true,
  3. align any module-level fallback constant,
  4. add the option to `wizard/options-metadata.json` — it is absent today precisely *because* the
     freeze removes it from `GFOptions`, so unfreezing without this ships a knob the wizard can't set.

  Do this only after §8/A1 passes. Default stays `off` either way; a template that pins the value
  hides the default's drift, so test the default, not `release/EldenRing.yaml`.
- Emit `dlcScadutreeFloorRanges` when mode == 2 (unchanged).
- **New:** emit `scaduBlessingCap` (INT) — the tier-aware cap, or 20 for `player_only`. Lets the
  client clamp without re-deriving the tier model.
- **New:** fragment injection for no-DLC seeds when mode != 0, gated on the pool having displaceable
  filler to give up. If it doesn't, fail at options-validation time naming both options — do not
  generate a seed whose blessing can never rise (CONTRIBUTING's headline gate).
- Retire the legacy top-level `global_scadutree_blessing` duplicate (`contract.py:708`). Nothing
  reads it — the only consumer is `core.rs:677` via `sd.pointer("/options/global_scadutree_blessing")`.
  **Three files, not one:** `contract.py:708`, the generated
  `crates/eldenring-archipelago/src/contract_gen.rs:86`, and
  `crates/er-logic/tests/fixtures/slot_data_fixture.json:5246`.

## 5. Client side

- `upgrades.rs`: `tick_global_scadu()` keeps its throttle, `in_world()` gate, and raise-only rule.
  After computing `level`, it now *also* drives the Lever B applier.
- New module `scadu_blessing.rs` (sibling of `no_equip_load.rs`, same shape): resolve base id from
  `GAME_SYSTEM_COMMON_PARAM_ST` once per connect, cache it, apply/remove rungs on the player
  `ChrIns`, death-guarded.
- `er-logic`: extend `blessing_target` with the cap term and the stored-blessing term. **The decision
  stays in `er-logic`** so it is host-testable — the applier in `eldenring-archipelago` is a dumb
  actuator (`er-tracker-regions-now-slotdata`: put the logic where CI can run it, not in code that
  only builds on Windows).
- Never hardcode `20000100`. Read `base_scadu_blessing_sp_effect_id()` at runtime.

## 6. Contract

| Key | Shape | When | Note |
|---|---|---|---|
| `options.global_scadutree_blessing` | INT | always | unchanged |
| `dlcScadutreeFloorRanges` | TRIPLE_LIST | mode == 2 ∧ ≥1 DLC region | unchanged |
| `scaduBlessingCap` | INT | mode != 0 | **new** |
| `global_scadutree_blessing` (top-level) | INT | — | **retire** |

Additive + contains-guarded, so `CONTRACT_HASH` behaviour follows the existing rule and old apworlds
still pair (`er-version-lockstep-semver`).

## 7. Tests

Per `gf-semantic-test-tiers`:

- **Pure/host (er-logic):** extend `scadu_blessing_replay.rs` with a third `Policy` — the cap term
  and the stored-blessing term. The failing-without / passing-with pair is a timeline where the
  player reveres for real at a DLC grace while holding fragments; pre-fix it double-counts.
- **Pure (world):** injection count is a function of the cap; a no-DLC seed at mode 1 contains
  ≥ `SCADU_CUM[cap]` fragments; a DLC seed injects none.
- **Contract:** `scaduBlessingCap` emitted exactly when mode != 0; the retired top-level key is gone
  from `contract.json` and the fixture.
- **Options validation:** mode != 0 on a seed with no displaceable filler raises naming both options.
- 🛑 A guard the corpus never triggers is untested (`guard-absent-from-corpus-needs-a-direct-call`).
  The death guard and the "row absent from `SpEffectParam`" path must be called directly with
  synthetic input, not assumed covered.

## 8. Acceptance tests (in-game — none of this is real until these run)

🛑 **Not via the equipment menu.** Scadutree moves `atk*DmgCorrectRate` — damage-pipeline correction
rates applied against a target — not `*AttackRate`. There is no reason to expect them in menu AR, and
a "number didn't move" reading would not distinguish "not applied" from "not displayed". Observe the
speffect list, or measure damage. (RECON §6 has the full reasoning.)

**Instrument: the Hexinton CE table already has this.** `SpecialEffect → Active Effects → 00..15`
(`elden_ring_artifacts/eldenring_all-in-one_Hexinton-v6.1_ce7.5.ct.ct:12336`). Each slot is a 4-byte
**speffect param id** with `Duration` / `Interval` / `Total Duration` children, walked
`WorldChrMan → LocalPlayerOffset → +0x178 → node`, successive nodes stepping `+0x30`. No new RE, no
client build.

🛑 **The list is only 16 slots deep, so a NEGATIVE is weak.** A geared player in combat can carry
more than 16 active speffects, and slot 16+ simply isn't rendered. "I don't see `200001xx`" is only
evidence of absence if **fewer than 16 slots are populated** at the moment you look. Strip to bare
fists and no talismans first. (This is the same trap as the menu-AR mistake above: an instrument that
can't represent the negative.)

**A1 — does the engine gate on map? ✅ ANSWERED 2026-07-29, in-game, Alaric on CE. YES, IT GATES.**

Stored byte set to 20, rested at a DLC grace. Active speffects **in the Land of Shadow**:

```
20004271 · 100620 · 503045 · 20000120  <<< SCADUTREE lv 20 · 20004211
```

Warped to **Limgrave**, same character, byte still reading **20**:

```
9530 · 84 · 100620 · 4650 · 4600 · 503045          -- blessing rungs: NONE
```

Five and six entries respectively, far below any display cap, so the negative is clean.

**Findings, now facts rather than inference:**

1. The chain is confirmed live — `20000100 + level`, stride 1, `20000120` at level 20.
2. **The engine gates the apply on map.** The stored byte survives the warp untouched; the engine
   simply declines to apply the rung outside the DLC.
3. Therefore **`player_only` and `scaled` have never done anything outside the Land of Shadow.**
   Lever A is a silent no-op in the base game. §1's dilemma resolves to the first horn: the option's
   docstring was *right*, and the option named "global" is structurally incapable of being global as
   built. Everything in this spec that depends on §3.1/§3.1b is now load-bearing, not optional.
4. `20004271` and `20004211` vanished along with the blessing, so the rung rides in a set of DLC-area
   effects applied and stripped together on map transition. Consistent with the `stateInfo = 472`
   category-tag hypothesis; not proof of it.

**A2 — direct apply outside the DLC. ✅ MECHANISM SETTLED 2026-07-29, in-game.**

Measured, in Limgrave:

| step | result |
|---|---|
| `applyEffect(20000120)`, rung at stock `effectEndurance = 0.05` | present immediately, **gone seconds later** |
| `setEndurance(20000120, -1)` then apply | **present, still present after 10s** |

**There is no strip.** Every rung ships with `effectEndurance = 0.05` — 50 ms, three frames. The
engine *refreshes* the rung every tick while you are in the Land of Shadow; outside the DLC that
refresh loop simply doesn't run, and a manually applied rung expires on its own. FromSoft's own
permanent-case pattern is visible one ladder over: `20000220` (Revered companion) is
`effectEndurance = -1` with `invocationConditionsStateChange1 = 501`, cycled into by the short-lived
`20000200` via `cycleOccurrenceSpEffectId`.

Consequences for §3:

- 🛑 **Lever B as specced is dead.** A 0.05 s effect against the client's 1 s tick is active ~5% of
  the time. "Re-apply on map load" is not remotely enough.
- ✅ **Lever D (§3.1b) is correct, and now for a concrete reason** rather than as insurance against
  unknown scoping: the clone must carry `effectEndurance = -1`. That field is a float at **row + 0x8**
  (offsets from the CE table's own SpEffectParam class: `iconId` 0x0, `conditionHp` 0x4,
  `effectEndurance` 0x8, `motionInterval` 0xC).
- The three scoping mechanisms §3.1b was defending against turn out to be one benign one. Lever D
  still wins, because a permanent clone is the *only* shape that survives without us reimplementing a
  per-tick refresher.

**A2b — does the damage pipeline honour it outside the DLC? ✅ YES. 2026-07-29, in-game.**

Tree Sentinel, Limgrave. Rung `20000120` applied with `effectEndurance = -1`: damage taken drops to
**roughly half**, against a predicted `×0.4878`. The scoping is *only* in the refresh loop — the
damage pipeline applies the rates wherever the effect is active.

**The feature is therefore proven end-to-end in vanilla with zero client code.** A global Scadutree
Blessing is achievable today by (a) making a blessing row permanent and (b) applying it. Everything
remaining is engineering, not discovery.

Remaining small gap: only the *damage taken* half was measured. `atkEnemyDmgCorrectRate_*` (damage
dealt, predicted `×2.05`) is untested. Both live on the same row so a split would be surprising, but
it is worth one confirming hit — count hits to kill something fixed, at rung vs no rung.

**A3 — no double-dip.** DLC seed. Hold 50 fragments (client raises to 20), then revere for real at a
DLC grace. Blessing reads 20, not 40; Attack Power matches the Lv20 row exactly.

**A4 — no save contamination.** Run a `player_only` seed, disconnect the client, load the save
vanilla. Blessing byte unchanged from its pre-run value.

**A5 — death guard.** Die repeatedly with the applier live, in and out of the DLC. No CTD.

## 9. Decisions I need from you

1. **Is `player_only` allowed to make base-game seeds easier?** As specced it is an explicit power
   fantasy — +105% damage and −51% damage taken at cap, enemies untouched. That is a big lever to
   hand a player under a name that sounds like a scope toggle. Alternative: fold `player_only` into
   `scaled` and ship only the rebalanced version.
2. **Injection budget.** `SCADU_CUM[20]` = 50 fragments is a lot of filler to displace in a base seed.
   Cap at 12 (A = 1.85, ≈3.4× budget, 26 fragments) instead?
3. **Does `scaled` need the C3 base-game enemy lift in v1, or is the DLC floor enough?** Shipping
   `scaled` without the base-game lift means it is identical to `player_only` outside the DLC — the
   same "mode 2 is an alias of mode 1" bug the replay harness was written to catch.
4. **Lever D instead of Lever B?** (§3.1b, added after your question.) I now recommend D: it works
   regardless of A1's answer, composes exactly with a real DLC blessing via the ratio, and reuses a
   pattern that already ships twice. The cost is that the blessing becomes invisible to the game's
   own UI outside the DLC. If that invisibility bothers you, the answer is Lever A in the DLC + Lever
   D everywhere else, which is what §3.1b assumes.

## 10. Risks

- **A1 comes back "doesn't move" and the CTD budget matters.** Lever B adds a second per-tick
  speffect-list walk while a CTD is already open on the boss-sweep path. Land it behind the mode
  gate so `off` seeds carry zero new game-memory access.
- **Early-economy floor is one seed thick** (`er-economy-floor-is-one-seed-thick`). Injecting 50
  forced-`useful` fragments displaces filler and any new progression bar reddens the fill gate.
  Baseline against pristine main before and after.
- **The floors are playtest-feel numbers**, flagged for review in `SPEC-region-spine-v2`. This spec
  inherits them; it does not validate them.
- **`stateInfo = 472`.** If the engine strips by that tag on map transition, Lever B's applied rung
  may be stripped too — A2 is what proves it isn't. If it is stripped, the fallback is re-applying
  on the tick (we already tick at 1s) and accepting a visible flicker on load.
