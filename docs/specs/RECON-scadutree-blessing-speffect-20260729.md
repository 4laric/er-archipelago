# RECON — the SpEffect behind Scadutree Blessing

**Date:** 2026-07-29 · **Status:** param side RESOLVED; one in-game question open · **Audience:**
`global_scadutree_blessing` (`off` / `player_only` / `scaled`)

Resolved against `gen_inputs.db` (`vanilla_er/vanilla_er/SpEffectParam.csv`, 11325 rows) via
`tools/probe_scadu_blessing.py`. Everything in §1–§3 is now **CONFIRMED from param rows**, not
inferred. The one thing still open is §4, and it is an in-game question that no amount of param
reading can answer.

---

## 1. The answer

There is no hardcoded id. The game reads a base row out of `GameSystemCommonParam` row 0 and indexes
off it by the player's stored level, **stride 1**:

| Field | Base id | Rows | Levels | What it moves |
|---|---:|---|---|---|
| `baseScaduBlessingSpEffectId` | **20000100** | `20000100–20000120` | 0–20 | player attack **and** damage taken |
| `baseReveredSpiritAshBlessingSpEffectId` | **20000200** | `20000200–20000210` (+ companion `20000220–20000230`) | 0–10 | summon attack + damage taken |
| `baseReveredSpiritTorrentBlessingSpEffectId` | **20000300** | `20000300–20000310` | 0–10 | **damage taken only** |

`base + 0` is in every case the identity row (all rates 1.0), which is why `base + level` works and
why the field is named "base". Level rows are contiguous with no gaps; `base+21..25` are absent for
Scadutree, confirming the ladder ends at 20.

These sit in the same `200xxxxx` space as the DLC enemy-scaling ladder (`20007000+10i`) and the
client's two vetted no-op rows (`20010827`, `20012080`) — same family, same conventions.

## 2. What the Scadutree rows actually set

Every level row `20000100+N` moves exactly 19 fields and nothing else:

- `atkEnemyDmgCorrectRate_{Physics,Magic,Fire,Thunder,Dark}` — damage dealt to enemies
- `atkPlayerDmgCorrectRate_{Physics,Magic,Fire,Thunder,Dark}` — damage dealt **to players**
- `{neutral,slash,blow,thrust,magic,fire,thunder,dark}DamageCutRate` — damage taken
- `stateInfo : 0 → 472`

Two properties worth naming:

**It is a single scalar.** All five attack channels carry the same value; all eight cut channels
carry the same value. There is no elemental or physical-subtype variation anywhere in the ladder.

**`cutRate = 1 / attackRate`, exactly, at every level.** 1/1.425 = 0.7017544, 1/1.85 = 0.5405405,
1/2.05 = 0.4878049 — the probe output matches to the last float digit. This was inferred from
`elden_ring_artifacts/scadufrags_per_level.txt` before; it is now confirmed from the rows, and that
artifact table is confirmed exact (it was merely rounded: 1.42→1.425, 1.87→1.875, 1.92→1.925,
1.97→1.975, 2.02→2.025).

So the whole Scadutree ladder is one number per level:

| Lv | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| A(N) | 1.10 | 1.20 | 1.25 | 1.30 | 1.35 | 1.425 | 1.50 | 1.55 | 1.60 | 1.65 |

| Lv | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 |
|---|---|---|---|---|---|---|---|---|---|---|
| A(N) | 1.75 | 1.85 | 1.875 | 1.90 | 1.925 | 1.95 | 1.975 | 2.00 | 2.025 | 2.05 |

**`atkPlayerDmgCorrectRate_*` moves too**, i.e. the blessing also boosts damage dealt to other
players. Irrelevant while invasions are off, but it is a live consideration if a global blessing ever
meets PvP.

### `stateInfo = 472` — the lead on §4

Level 0 has `stateInfo = 0`; every level 1–20 row has `stateInfo = 472`. A shared, non-zero
`stateInfo` across an entire ladder is a **category tag** — the handle by which engine code finds or
strips a family of effects without knowing individual ids. That makes it the most likely mechanism by
which the game removes the blessing when you leave the Land of Shadow. HYPOTHESIS, not established;
§6/V3 says how to test it.

## 3. The other two ladders are NOT the same shape

**Revered Spirit Ash (`20000200`) is two-layered.** Each level row sets `physics/magic/fire/thunder/
dark AttackRate` *and* `neutral/slash/blow/thrust AttackRate` — and these **diverge from level 5 up**
(Lv6: element channels 1.566, physical-subtype channels 1.45). Each level row also points
`cycleOccurrenceSpEffectId` at a companion row `20000220 + level` — permanent (`effectEndurance = -1`),
gated by `invocationConditionsStateChange1 = 501`, and carrying its own rate set that is a *ratio*
correction on the main row (e.g. companion for Lv5 has attack 0.98214287 = 1.375/1.400 exactly).

Read caveat on those companion numbers: the probe diffed them against `20000200`, not against their
own base `20000220`. That happens to be harmless — `20000220` differs from `20000200` only in
`cycleOccurrenceSpEffectId` / `effectEndurance` / `invocationConditionsStateChange1`, so all its rate
fields are still 1.0 and the printed rates are true absolutes. Worth re-running with an explicit base
before anyone builds on the companion layer.

**Torrent (`20000300`) is defence-only.** Eight `DamageCutRate` fields, zero attack fields — Torrent
takes less damage and deals no more. It is also the *steepest* of the three: Lv10 = 0.46 cut, better
than the player's own Revered Lv10 (0.575).

Do not generalise the clean Scadutree scalar to either of these.

## 4. ✅ SETTLED 2026-07-29: it IS Land-of-Shadow-only, and the gate is in the applier

**Measured in-game** (Alaric, CE, stored byte = 20, rested at a DLC grace). Active speffects in the
Land of Shadow: `20004271 · 100620 · 503045 · **20000120** · 20004211`. Warped to Limgrave, byte still
reading 20: `9530 · 84 · 100620 · 4650 · 4600 · 503045` — **no blessing rung**. 5 and 6 entries, so
nothing was truncated.

- The `base + level` chain is **confirmed live**, stride 1.
- The stored byte **survives** the warp; the engine simply declines to apply outside the DLC.
- `20004271` / `20004211` disappeared too — the rung rides in a set of DLC-area effects
  applied/stripped together on map transition.
- ⇒ **Lever A alone is a no-op in the base game.** See `SPEC-global-scadutree-blessing-20260729.md`.

The original reasoning that predicted this is kept below, because it is still what rules out the
alternative explanations.

### Why the gate has to be in the applier

**Now CONFIRMED from the rows, not just the header index:** the blessing rows carry **nothing
spatial**. Nineteen fields, all of them rate multipliers plus one category tag. No map, area, region
or DLC field — because `SpEffectParam` has no such column at all.

Therefore **the restriction cannot live in the effect. It can only live in whatever decides to apply
it.** Two candidate mechanisms, both untested:

1. Engine-side map check on apply (`EldenRingTool` AOB-scans a native
   `CS::PlayerGameData::GetScadutreeBlessing`, which points this way — weak evidence).
2. A strip-by-`stateInfo`-472 on map transition (§2).

Corroborating behaviour, PLAUSIBLE (single source): the author of
[Remove Scadutree Mechanics](https://www.nexusmods.com/eldenring/mods/8279) asks testers to check
"that your attack power in the menu remains the same number **inside and outside the DLC**" — he
expects it to differ by default.

**Why this outranks everything else.** Our current `player_only` implementation
(`upgrades.rs::tick_global_scadu` → `raise_stored_blessing` → `pgd.scadutree_blessing = target`) is an
**indirect lever**: it sets the input and trusts the engine to apply. If the engine gates the apply on
map, `player_only` **does nothing at all in the base game** — which is the entire feature. It has
never been verified in-game (`er-v02-ingame-validation-debt`).

## 5. Three levers

Everything below is bound in `eldenring 0.14` and every idiom already ships in this client.

**Lever A — stored byte (today).** `pgd.scadutree_blessing = n`. Indirect, native-feeling, free.
Fails silently and completely if the engine gates on map. Keep it; stop treating it as the feature.

**Lever B — apply the row ourselves. Makes `player_only` robust.**

```rust
// idiom already in production: no_equip_load.rs:85-91, no_fall_damage.rs:87-89
let base = repo.get::<GAME_SYSTEM_COMMON_PARAM_ST>(0)?.base_scadu_blessing_sp_effect_id();
let row  = base + level;                       // stride 1, CONFIRMED; levels 0..=20
if !chr.special_effect.entries().any(|e| e.param_id == row) {
    chr.apply_speffect(row, false);            // ChrInsExt::apply_speffect(i32, dont_sync)
}
```

Map-agnostic by construction: if the gate is in the applier (§4), applying it ourselves bypasses the
gate without touching it. `remove_speffect(i32)` exists, so a level change is remove-then-apply.

🛑 **Death guard is mandatory.** `no_equip_load.rs:78-83` carries a comment earned the hard way: the
player's `chr_ins` + `special_effect` list tear down at the death-cam transition, and iterating or
mutating them there **CTDs**. Gate on `player.chr_ins.modules.data.hp > 0`. We already have an open
🟠 CTD on the boss-sweep payout path; a second unguarded speffect walk makes that harder to triage.

Cost: we own re-application across map load and death, and Lever A + Lever B must never both be live
— double-dipping would be silent and would read as a balance bug.

**Lever C — own the ladder. For `scaled`.** `set_base_scadu_blessing_sp_effect_id()` exists, and
`repo.get_mut::<SpEffectParam>(id)` is already used in production to rewrite rows at runtime. Because
the Scadutree ladder is a **single scalar with an exact reciprocal**, we can synthesise any curve we
want with two writes per row and no risk of desyncing attack from defence.

**The number `scaled` needs.** In a damage race, an attack multiplier A and a taken multiplier 1/A
compound: effective power ≈ **A(N)²**. So the full vanilla blessing budget is **2.05² ≈ 4.2×**, and
e.g. Lv12 ≈ 1.85² ≈ 3.4×. That is the quantity the C3 "DLC-elevation" hypothesis is implicitly
claiming equals the gap between base-game endgame and DLC scaling — and it is now a number we can
check against the `70xx` / `20007xxx` enemy ladder instead of a hypothesis we assert.

**Do not hardcode 20000100.** Read `base_scadu_blessing_sp_effect_id()` at runtime: version-proof,
no generated table, and it sidesteps the foreign-list/provenance rule entirely. The ids above are
recon, recorded so nobody re-derives them — not a contract.

## 6. Verification

**V1 — param values. ✅ DONE 2026-07-29.** `python tools\probe_scadu_blessing.py`. Resolved the base
ids, the stride, and the field set. Re-run with an explicit base for the Revered companion block
(§3) if that layer ever matters.

🛑 **Do NOT use the equipment-menu Attack Power number for this.** An earlier draft of this doc did.
Scadutree moves `atkEnemyDmgCorrectRate_*` / `atkPlayerDmgCorrectRate_*` — **damage-pipeline
correction rates applied against a target**, not `*AttackRate` fields. (Revered, by contrast, does use
`physicsAttackRate` etc. — §3.) Menu AR is computed from weapon + stats + attack-rate modifiers, so
there is no reason to expect a correction rate to appear there at all, and a "number didn't move"
result would be indistinguishable between "not applied" and "applied but not displayed". Use V2 or V3.

**V2 — observe the speffect directly. This is the decisive test and it needs no damage math.**
Enumerate the player's active speffects and look for anything in `20000100..=20000120`. Do it twice
at the same stored blessing level: once inside the Land of Shadow, once standing in Limgrave.

- Present in both → the effect is global; Lever A suffices; `player_only` works as designed.
- Present in the DLC, absent in Limgrave → the engine gates on map; **Lever A alone is a no-op in the
  base game**; `player_only` must switch to Lever B.
- Absent in both → the `base + level` chain is wrong and this whole doc needs revisiting.

**The CE table already has the viewer.** `elden_ring_artifacts/eldenring_all-in-one_Hexinton-v6.1_ce7.5.ct.ct:12336`
— `SpecialEffect → Active Effects → 00..15`, each slot a 4-byte speffect param id with
`Duration`/`Interval`/`Total Duration` children, walked `WorldChrMan → LocalPlayerOffset → +0x178 →
node`, successive nodes stepping `+0x30`. The same table also confirms the stored byte at
`GameDataMan → +0x08 → +0xFC` ("Scadutree Blessing Level -- DLC", line 5748) and `+0xFD` for Revered.
Zero code needed.

🛑 **Only 16 slots, so a NEGATIVE is weak.** A geared player in combat can exceed 16 active speffects
and slot 16+ isn't rendered. "I don't see `200001xx`" only means absence if fewer than 16 slots are
populated — strip gear first. Same failure mode as the menu-AR trap above: an instrument that cannot
represent the negative you care about.

**V3 — client diagnostic, one build.** Read-only log on the in-world tick: `pgd.scadutree_blessing`,
plus every `chr.special_effect.entries()` whose `param_id` is in `20000100..=20000120` **and** every
entry whose row has `stateInfo == 472`. Same two locations as V2. This is strictly better than V2
because it also reveals *what else* carries the 472 tag, which is the lead on the gate mechanism —
and it reuses the walk already shipping in `no_equip_load.rs`.

**V4 — damage ratio, as corroboration only.** Same enemy, same attack, blessing 0 vs 20. Expect
**×2.05** dealt and **×0.4878** taken. Noisy (poise, hitzones, timing) and slower than V2/V3, but it
is the only test that confirms the effect is actually *doing* what the row says, not merely present
in a list.

## 7. Do not assume

- Do not assume the Revered or Torrent ladders behave like Scadutree — §3 shows all three differ.
- Do not assume `player_only` currently works. §4 gives a concrete mechanism by which it is a
  complete no-op outside the DLC, and it has never been checked in-game.
- Do not assume `stateInfo = 472` is the gate. It is the best lead, not a finding.
- Do not hardcode any of these ids. Read them at runtime.
- Do not commit the probe output — it is game data.

## Sources

- `gen_inputs.db` → `vanilla_er/vanilla_er/SpEffectParam.csv`, `GameSystemCommonParam.csv`, read via
  `tools/probe_scadu_blessing.py` (run 2026-07-29)
- `param_headers/param_columns.tsv` ordinals 342 / 343 / 355 (field names + the SpEffectParam column list)
- `elden_ring_artifacts/scadufrags_per_level.txt`, `revered_spirit_ash_per_level.txt` — independently
  confirmed exact by the probe
- `from-software-archipelago-clients/crates/eldenring-archipelago/src/upgrades.rs`, `no_equip_load.rs`,
  `no_fall_damage.rs`
- [`eldenring 0.14`](https://docs.rs/eldenring/latest/eldenring/param/index.html):
  [`GAME_SYSTEM_COMMON_PARAM_ST`](https://docs.rs/eldenring/0.14.0/eldenring/param/struct.GAME_SYSTEM_COMMON_PARAM_ST.html),
  [`ChrInsExt`](https://docs.rs/eldenring/0.14.0/eldenring/cs/trait.ChrInsExt.html),
  [`PlayerGameData`](https://docs.rs/eldenring/0.14.0/eldenring/cs/struct.PlayerGameData.html)
- [Remove Scadutree Mechanics — Nexus 8279](https://www.nexusmods.com/eldenring/mods/8279) — behavioural
  corroboration only
