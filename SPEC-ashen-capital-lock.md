# SPEC-ashen-capital-lock — the Erdtree burn becomes a synthetic item

**Status: PROPOSED, build-ready except for ONE in-game probe (§ The probe that gates the build).
Not an option — this is the behaviour. Supersedes the `FINALE_REQUIRES` half of
`features/finale.py` and the `elden_beast` row of `GOAL_CHOICES`.**

Written against world `main` @ `441e2cd`, client `main` @ `208df96`.

## Decisions (Alaric, 2026-08-06)

1. **The item model IS the behaviour.** No `capital_burn: vanilla|item` toggle — two shapes to
   support forever, and narrowing a Choice later is a compat break. The reconciler already made
   Royal non-losable, which was the only reason to keep the vanilla one-way burn as a fallback.
2. **The Ashen Capital does NOT become a region.** It stays out of `REGIONS` and `SPINE`, is never
   drawn by `num_regions`, is never counted in the kept set, and can never be the start anchor.
   It is ten checks and a gauntlet, not a place you play. `describe_kept` is untouched.
3. **`goal: auto` = the Elden Beast, always.** The finale is a fixed gauntlet — Gideon into
   Godfrey/Hoarah Loux into Radagon/Elden Beast — and that shape plays well as a capstone under
   rando no matter what the draw kept.

## PROBE RESULTS — 2026-08-06 (Alaric, in game, ~2h)

Run per `PROBE-PLAN-ashen-capital.md` on a fresh seed + locally hosted room, `goal: elden_beast`,
`leyndell_runes_required: 0`, Leyndell Lock sent from the server console. Instrument was the shipped
`!flag` / `!setflag` / `!warp` overlay commands (`core.rs:231`), NOT a debug build.

| step | result |
|---|---|
| Leyndell Lock receipt: open flag 76980 + 6 graces | ✅ no kick in buckets 11050 / 19000 |
| 118 alone → reconciler armed, no cutscene, Royal warps intact | ✅ |
| Ashen graces map-selectable with 9116 OFF | ✅ (71120–71125 lit by hand) |
| warp intercept sets 9116 ON from the target before load | ✅ `readback STUCK` |
| m11_05 loads, Gideon (510060) spawns and fights | ✅ check 7773906 sent |
| Godfrey / Hoarah Loux (510070) spawns, both phases | ✅ check 7770755 sent |
| m19_00 reachable | ✅ `play_region 1900001` |
| **Radagon / Elden Beast arena** | ❌ **VOID — fell in and died**, until flag 300 was set by hand |
| flag 300 set → geometry present | ✅ |
| flag 300 CLEARED → normal Roundtable returns | ✅ reversible, not one-way |
| Royal round-trip: 9116 OFF → East Capital Rampart | ✅ m11_00 normal, Morgott live, 71100–71109 intact |

**The decisive question is answered YES, with a correction, not a caveat:** the finale is fully
playable from a synthetic burn state provided the world-state flags come with it. See the corrected
mechanism above.

STILL OPEN after this run: the Elden Beast kill itself (the void blocked it and the session ended on
the Royal round-trip instead); the Shinmon-elevator reachability audit; and the NPC surface, which
one session was never going to clear.

## What this changes, in one paragraph

Today flag 9116 has exactly one setter in the whole game (Maliketh), so the finale can only exist
on seeds that kept Farum Azula *and* Leyndell, and `goal: elden_beast` has to force-keep both —
which is why `num_regions: 1` produced four regions. After this spec, an **Ashen Capital Lock**
item arms the burn state, the finale exists on every base-game seed, `FINALE_REQUIRES` empties,
and Farum Azula stops being mandatory. `num_regions: 1` rolling Mountaintops means you play
Mountaintops, find the Ashen Capital Lock, and warp to the end of the game.

## Ground truth reused — do NOT re-derive

From `SPEC-capital-reconciler.md` (Alaric in-game + EMEVD, 2026-07-14) and this session's reads:

* **9116 is the map-version selector.** OFF → Leyndell, Royal Capital `m11_00` (play_region 11000,
  Morgott + ~152 checks). ON → Ashen Capital `m11_05` + Elden Throne `m19_00` (11050, 19000).
* **Sole vanilla setter of 9116:** `m13_00_00_00.emevd:409`, on Maliketh's death.
* **`common.emevd $Event(900)`** waits solely on 9116 → burn cutscene → warps the player into
  `m11_05` at region 11052010 → `BatchSetEventFlags(71100, 71110, OFF)` (wipes the Royal grace warp
  points) → latches **118** as its last step. 118 is monotonic, is $Event(900)'s own entry check,
  and m13's setter event `13002800` ends itself once 118 is on.
* **Grace sets are disjoint** (BonfireWarpParam): Royal `11001950-11001959`, warp flags
  71100-71109 → bucket 11000. Ashen `11051950-11051955`, warp flags 71120-71125 → 11050. Throne
  `19001950`, warp flag 71900 → 19000.
* **The finale's ten checks** live in `data.LOCATIONS['Ashen Capital']`. The two majors are
  `7770755` (Hoarah Loux, f510070) and `7770764` (Elden Beast, f510230), both tagged
  `Remembrance, MajorBoss, Boss, LegacyBoss`. **Gideon (`7773906`) carries NO tags**, so
  `goalLocations` stays exactly the pair — verified, not assumed.

## The mechanism (CORRECTED 2026-08-06 by the probe): replay `$Event(900)`'s body

The first draft of this section said "pre-latch 118, then let the reconciler own 9116." **That was
wrong, and the probe proved it in the most literal way available: a void where the Elden Beast's
arena should have been, and a death falling into it.**

`common.emevd $Event(900)` — 天変地異_世界樹炎上, "Natural disaster: World Tree in flames" — does far
more than latch 118:

```
GotoIf(L0, !EventFlag(9116));   // 9116 off -> wait for it
GotoIf(L1, !EventFlag(118));    // 118 off  -> run the body
EndEvent();                     // BOTH already on -> do nothing at all
L1:
    SetEventFlagID(300, ON);    SetEventFlagID(301, ON);    SetEventFlagID(302, OFF);
    SetEventFlagID(71300, ON);  BatchSetEventFlags(71100, 71110, OFF);
    PlayCutsceneToPlayerAndWarp(13000050, ..., 11052010, 11050000, 10000, 13000, true);
    SetEventFlagID(118, ON);
```

**Flag 300 is the world's post-burn state, and `common.emevd:1293` is its SOLE setter in the game** —
589 files checked, including every `BatchSetEventFlags` range that could have covered it. Readers sit
in at least five maps: `m11_00:421/432/883` (Royal Leyndell's elevators, incl. 神門エレベータ封鎖
"Shinmon elevator blocked" → `DisableObjAct(11001531)`), `m11_10:150`, `m12_03:187/204/230`,
`m35_00:453`, `m60_42_32:92`. 301 is set alongside and has ZERO readers in the corpus (params or
engine, not events). 302 is the *opposite* state — set by `$Event(901)` 天変地異_メリナ炎上, the
Melina/Forge ceremony, alongside flag 110 — and the arrival clears it.

Pre-latching 118 makes `$Event(900)` short-circuit to `EndEvent()`, so **300 never gets set and every
map keeps its pre-burn geometry** — m19_00's Radagon arena included.

So the lock's first-open grant IS the burn's side-effect set, in this order:

1. `300 ON`, `301 ON`, `302 OFF`, `71300 ON` — the world state. Without 300 the finale is unplayable.
2. The Ashen grace bundle 71120–71125 (NOT 71900: the Fractured Marika bonfire only spawns after the
   Elden Beast dies, `m19_00:19002502` waiting on 9123, so it is warp-useless as an entry).
3. The region open flag.
4. `118 ON` **last** — it is the suppressor, and setting it first is exactly what skipped the body.
5. 9116 — still left to the reconciler (warp intercept + per-tick latch), as before.

Deliberately NOT replayed: `BatchSetEventFlags(71100, 71110, OFF)` (the Royal grace-warp wipe — the
whole reason the reconciler exists) and the cutscene warp itself.

**Wire:** the existing lock-grant path — `region.rs` sets `regionGraces` + the open flag +
`lockRevealFlags` on receipt. The world-state flags ride `lockRevealFlags`; 118 needs to be ordered
after them, which is the one thing the current client wiring does not guarantee and the client half
must.

## 🛑 Flag 300 is GLOBAL, MONOTONIC and IRREVERSIBLE — the open design question

Confirmed in game 2026-08-06: with 300 set, **the Roundtable Hold is in its burnt state**. This is
not a capital-local version swap like 9116 — it is a world-wide state change that no event clears,
and under this spec it fires **the moment the Ashen Capital Lock is received**, which fill may place
in sphere 0.

⭐ **MEASURED THE SAME SESSION: writing `300 = 0` restores the normal Roundtable.** So the flag is
monotonic only by *convention* — the maps re-read it, and the state is reversible from our side. That
kills the worst version of this problem (an irreversible one-way world flip on lock receipt) and puts
a reconciler-style hold-by-position squarely on the table.

Known consequences, one measured and one derived:

* **Royal Leyndell keeps its burnt-elevator state permanently.** `m11_00:431` disables ObjAct
  11001531 and pops a dialog; `:883` skips that lift's common-event registration entirely. In vanilla
  this never mattered because burning meant never returning to Royal. Under the lock model you do
  return, so this is a NOVEL degradation of the ~152 Royal checks' on-foot reachability. Needs an
  audit: does that lift gate any check that the granted grace bundle cannot otherwise reach?
* **Melina is alive in a burnt world.** `$Event(901)` sets flag 110 at the Forge; we skip the whole
  middle chapter, so 110 is never set. That is a state vanilla cannot produce, and it is a more
  likely misbehaviour than the 9116-conditioned quest lines already on the risk list.

🛑 **STILL NOT DECIDED HERE, but the empirical half is settled.** The choice is now purely a design
one: does the lock LATCH 300 once (simple, and the whole world reads post-burn for the rest of the
run), or does the reconciler HOLD it by position alongside 9116 (the world stays vanilla outside the
capital and the finale, at the cost of extending a per-tick write to a flag whose readers span five
maps plus the hub, and of a state — 300 off while standing in m19 — that would strand the player in a
void if the timing ever slipped)? That ruling belongs to a Fable review with this section attached,
not to the implementer. Note the asymmetry that should weigh on it: a mistimed 9116 costs you the
wrong Leyndell, a mistimed 300 costs you the floor.


## World-side changes

1. **`features/finale.py`** — the region is built unconditionally (base game in play; see §
   dlc_only). Entrance rule changes from `has_all(FINALE_REQUIRES locks)` to
   `has("Ashen Capital Lock")`, and the host moves from Leyndell to `HUB`: you reach the Ashen
   Capital by warping to its own graces, never through the capital's rune gate. The foreign-bar
   `item_rule` block stays exactly as is.
2. **`data.FINALE_REQUIRES` → `()`**, `FINALE_HOST_REGION` → `HUB`. `coverage.py`'s finale scope
   predicate and its `delegation: data.FINALE_REQUIRES` provenance follow.
3. **`region_play_ids`**: `Leyndell: [11000, 11050, 19000]` splits into `Leyndell: [11000]` and
   `Ashen Capital: [11050, 19000]`. 🛑 **The reconciler derives `capitalAshenPlayRegions` /
   `capitalRoyalPlayRegions` by partitioning *Leyndell's* bucket list, and hard-fails gen
   (ContractError) on an unclaimed bucket or an empty side.** Re-point that derivation in the same
   commit or generation dies the moment the split lands.
4. **`region_open_flags` + `region_graces`** gain an `'Ashen Capital'` entry (§ mechanism).
   `core._lockless_host` loses its only member and can go — Ashen now has a real open flag, so the
   KICK enforces it in its own right instead of borrowing Leyndell's.
5. **`core.create_items`**: mint one `Ashen Capital Lock` unconditionally, alongside the per-kept
   region locks and **before `pool_builder`**, so count-exactness holds by construction (the builder
   fills the remainder). It is progression, it is never the precollected anchor.
6. 🛑 **`core.create_items:585` — the `start_regions` clamp must count MINTED LOCKS, not kept
   regions.** It currently reads `if _n_start >= len(kept): raise OptionError(...)`.
   `start_with_region_lock` is frozen ON in `defaults.FROZEN_OPTIONS`, so a `kept == 1` seed at the
   default `start_regions: 1` raises and **Alaric's motivating case — `num_regions: 1` rolls
   Mountaintops — dies at generation.** The clamp has never been wrong because `kept == 1` is
   currently unreachable (auto force-keeps Leyndell, whose parent closure adds Altus, floor 2);
   this spec makes it reachable for the first time.
7. **`features/goal_locations`**: `GOAL_CHOICES['elden_beast'] = ('Ashen Capital', ())` — nothing
   forced. Tier 0 keys on the finale being built rather than on `finale_active(kept)`, and `auto`
   resolves to it unconditionally (decision 3).
8. **`goalRequiredItems`** picks up the Ashen lock via `kept_lock_names()`. Strictly redundant —
   you cannot kill either goal boss without it — but the two terminal conditions are supposed to
   read one list, and a lock missing from that list is exactly the drift the 2026-07-30 alignment
   fixed.

## Where the old ladder still lives: dlc_only

Under `dlc_only` the base game is sealed, so there is no Ashen Capital, no lock, and no tier 0.
The terminus-first spine walk (tiers 1/2, including the 2026-08-05 Bayle fix) is **still the goal
derivation there** and must not be deleted — it just stops being reachable on any seed with the
base game in play.

⚠️ **A vacuous guard to avoid.** `core._resolve_goal_choice` validates a named goal by checking
that `forced_regions(chosen)` are all eligible. With `elden_beast`'s forced set now empty, that
check passes **vacuously** under `dlc_only` and would pin an unbuildable region. The guard has to
become an explicit "base game must be in play" test, not a quantifier over an empty tuple.

## natural_progression

`natural_progression` mints no Lock items at all, so there is nothing to receive and nothing to arm.
Under it, **keep the vanilla burn**: don't pre-latch 118, let Maliketh's death set 9116 the way the
game does. `kept_lock_names()` already returns `[]` there, so `goalRequiredItems` stays omitted.

## Consequences accepted

* Every seed with the base game in play ends on the Elden Beast. Terminal-region variety under
  `auto` is gone by choice.
* The Ashen Capital's ten checks exist on every such seed rather than on the ~fraction that kept
  Farum Azula + Leyndell.
* A player can reach the game's real ending as soon as fill gives them the lock. Under decision 3
  that *is* the goal, so it is not a footgun — but it does mean the Ashen Capital Lock is the single
  most sphere-sensitive item in the pool, and `goalRequiredItems` (hold every kept lock) is the only
  thing stopping a one-lock seed from ending the moment it opens.

## The probe that gated the build — RUN, see PROBE RESULTS above

Kept for the record. Item 1 ("do Gideon, Godfrey and the Elden Beast spawn in an m11_05 reached
without the cutscene") is answered YES once flag 300 is part of the synthetic state. Item 2 (Ashen
graces selectable at 9116 OFF) is answered YES, so no client-driven warp affordance is needed. The
remaining items — 13002800's disarm on a real Maliketh kill, the NPC surface under long-lived
118-without-burn, and now the Shinmon elevator — stay open and belong on the playtest list.
